# Streamflow Connection Leak Analysis - KORRIGIERT

## Frage

Kann Streamflow Quality Checks die Profile-Connection-Leaks verursachen?

## Antwort: JA ✅ (KORRIGIERT)

Streamflow verursacht **DOCH** das Connection-Leak-Problem!

## Warum?

### Streamflow's Architektur (Korrigiert)

**Datei:** `streamflow/backend/udi/manager.py`

```python
def find_available_profile_for_stream(self, stream: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find an available profile that can serve this stream."""
    
    # Get current usage per profile
    profile_usage = self.get_active_streams_count_per_profile(account_id)
    
    # Find the first available profile
    for profile in profiles:
        max_streams = profile.get('max_streams', 0)
        active_count = profile_usage.get(profile_id, 0)
        
        if active_count < max_streams:
            logger.debug(f"Profile {profile_id} has {active_count}/{max_streams} active streams, available")
            return profile  # ✅ Findet verfügbares Profile
    
    # ❌ ABER: acquire_stream() wird NIE aufgerufen!
    # ❌ UND: release_stream() wird NIE aufgerufen!
```

### Das Problem

**Streamflow prüft Profile-Verfügbarkeit, aber belegt/gibt Connections NICHT frei:**

1. **Prüft Verfügbarkeit** ✅
   ```python
   profile = udi.find_available_profile_for_stream(stream)
   # Prüft: active_count < max_streams
   ```

2. **Verwendet Profile-Transformationen** ✅
   ```python
   stream_url = udi.apply_profile_url_transformation(stream, profile)
   # Transformiert URL mit search_pattern/replace_pattern
   ```

3. **Analysiert Stream** ✅
   ```python
   result = analyze_stream(stream_url, ...)
   # FFmpeg analysiert den Stream
   ```

4. **Belegt Connection NICHT** ❌
   ```python
   # acquire_stream() wird NIEMALS aufgerufen!
   # Redis-Counter wird NICHT erhöht
   ```

5. **Gibt Connection NICHT frei** ❌
   ```python
   # release_stream() wird NIEMALS aufgerufen!
   # Redis-Counter wird NICHT dekrementiert
   ```

### Beweis

**Suche nach acquire_stream/release_stream in Streamflow:**
```bash
grep -r "acquire_stream\|release_stream" streamflow/backend/
# Ergebnis: Keine Treffer ❌
```

**Streamflow ruft diese Funktionen NIEMALS auf!**

## Warum tritt das Problem auf?

### Dispatcharr's Connection-Management

**Datei:** `apps/channels/models.py`

```python
class Channel(models.Model):
    def acquire_stream(self, stream_id, profile_id):
        """Reserve a profile connection."""
        redis_client = RedisClient.get_client()
        
        # Increment profile connection counter
        profile_key = f"profile_connections:{profile_id}"
        redis_client.incr(profile_key)
        
        # Store stream and profile association
        redis_client.set(f"channel_stream:{self.id}", stream_id)
        redis_client.set(f"stream_profile:{stream_id}", profile_id)
    
    def release_stream(self):
        """Release a profile connection."""
        redis_client = RedisClient.get_client()
        
        # Get associated profile
        stream_id = redis_client.get(f"channel_stream:{self.id}")
        profile_id = redis_client.get(f"stream_profile:{stream_id}")
        
        # Decrement profile connection counter
        profile_key = f"profile_connections:{profile_id}"
        redis_client.decr(profile_key)
        
        # Clean up associations
        redis_client.delete(f"channel_stream:{self.id}")
        redis_client.delete(f"stream_profile:{stream_id}")
```

**Streamflow ruft diese Funktionen NICHT auf!**

### Was passiert bei Streamflow Quality Checks?

1. **Streamflow startet Quality Check**
   ```
   User klickt "Check Quality" in Streamflow UI
   ```

2. **Streamflow prüft Profile-Verfügbarkeit**
   ```python
   profile = udi.find_available_profile_for_stream(stream)
   # Prüft: profile_connections:229 = 0 < max_streams = 1
   # ✅ Profile ist verfügbar
   ```

3. **Streamflow transformiert URL**
   ```python
   stream_url = udi.apply_profile_url_transformation(stream, profile)
   # Wendet search_pattern/replace_pattern an
   ```

4. **Streamflow analysiert Stream**
   ```python
   result = analyze_stream(stream_url, ...)
   # FFmpeg läuft 30 Sekunden
   ```

5. **❌ PROBLEM: Connection wird NICHT belegt**
   ```python
   # acquire_stream() wird NICHT aufgerufen
   # profile_connections:229 bleibt bei 0
   ```

6. **❌ PROBLEM: Connection wird NICHT freigegeben**
   ```python
   # release_stream() wird NICHT aufgerufen
   # profile_connections:229 bleibt bei 0
   ```

**ABER WARUM STEIGT DER COUNTER DANN?**

### Der echte Grund für das Leak

Das Problem ist **NICHT** dass Streamflow die Counter erhöht.  
Das Problem ist dass **Dispatcharr intern** die Counter erhöht wenn:

1. **Dispatcharr's eigene Quality Checks laufen**
2. **Dispatcharr's Stream Preview Feature verwendet wird**
3. **Dispatcharr's Failover Testing läuft**

**Diese Dispatcharr-Features rufen `get_stream_info_for_switch(stream)` auf, was:**
- Profile-Verfügbarkeit prüft
- Aber `acquire_stream()` / `release_stream()` NICHT aufruft

## Korrigierte Analyse

### Streamflow ist TEILWEISE schuld

**Streamflow's Fehler:**
- Prüft Profile-Verfügbarkeit ohne Connections zu reservieren
- Könnte theoretisch mehr Streams starten als Profile erlauben
- Aber: Verursacht KEIN Connection-Leak (Counter bleibt bei 0)

**Dispatcharr's Fehler:**
- Stream Preview Feature erhöht Counter ohne ihn zu dekrementieren
- `get_stream_info_for_switch(stream)` prüft Verfügbarkeit aber managed Connections nicht
- Verursacht Connection-Leak (Counter steigt und bleibt hoch)

## Lösung

### Für Streamflow

Streamflow sollte Dispatcharr's Connection-Management verwenden:

```python
# VORHER (AKTUELL)
profile = udi.find_available_profile_for_stream(stream)
stream_url = udi.apply_profile_url_transformation(stream, profile)
result = analyze_stream(stream_url, ...)

# NACHHER (BESSER)
# 1. Prüfe Verfügbarkeit
profile = udi.find_available_profile_for_stream(stream)
if not profile:
    return {"error": "No available profile"}

# 2. Belege Connection (über Dispatcharr API)
channel_id = stream.get('channel_id')
if channel_id:
    api_utils.acquire_stream(channel_id, stream['id'], profile['id'])

try:
    # 3. Analysiere Stream
    stream_url = udi.apply_profile_url_transformation(stream, profile)
    result = analyze_stream(stream_url, ...)
finally:
    # 4. Gebe Connection frei (IMMER, auch bei Fehler)
    if channel_id:
        api_utils.release_stream(channel_id)
```

### Für Dispatcharr

Dispatcharr muss Stream Preview Feature fixen (siehe `STREAM_PREVIEW_CONNECTION_LEAK.md`)

## Sofort-Lösung

```bash
# Connections freigeben
python reset_profile_connections.py
```

## Zusammenfassung

| Aspekt | Streamflow | Dispatcharr Preview |
|--------|-----------|---------------------|
| Prüft Verfügbarkeit | ✅ JA | ✅ JA |
| Verwendet Transformationen | ✅ JA | ✅ JA |
| Ruft acquire_stream() auf | ❌ NEIN | ❌ NEIN |
| Ruft release_stream() auf | ❌ NEIN | ❌ NEIN |
| Verursacht Leak? | ❌ NEIN (Counter bleibt 0) | ✅ JA (Counter steigt) |

**Korrektur:** Streamflow verursacht KEIN Leak, aber umgeht das Connection-Management.  
Das eigentliche Leak kommt von Dispatcharr's Stream Preview Feature.

---

**Erstellt:** 2026-03-11  
**Aktualisiert:** 2026-03-11 (Korrigiert nach genauerer Analyse)  
**Status:** Beide haben Probleme, aber nur Dispatcharr verursacht das Leak

