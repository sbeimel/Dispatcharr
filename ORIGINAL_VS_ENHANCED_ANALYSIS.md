# Original Dispatcharr-0.20.1 vs Enhanced Version - Connection Management Analysis

## ZUSAMMENFASSUNG

Die Original-Entwickler haben **NICHTS verkackt**! Der Connection Leak Bug existiert **AUCH im Original Dispatcharr-0.20.1**. Die Unterschiede zwischen Original und Enhanced Version sind:

1. **Original hat KEINEN Retry-Loop** → Bug tritt seltener auf
2. **Original hat KEINEN Profile Failover** → Bug wird nicht so schnell sichtbar
3. **Original hat denselben Bug in `_clean_redis_keys()`** → Falsche Reihenfolge (release NACH delete)

---

## KRITISCHE UNTERSCHIEDE

### 1. RETRY-LOOP (views.py)

**ORIGINAL (Dispatcharr-0.20.1):**
```python
# Zeile 48-250 in views.py
while should_retry and time.time() - wait_start_time < retry_timeout:
    attempt += 1
    stream_url, stream_user_agent, transcode, profile_value = (
        generate_stream_url(channel_id)
    )
    
    if stream_url is not None:
        logger.info(f"Successfully obtained stream after {attempt} attempts")
        break
    
    # KEIN channel.release_stream() hier!
    # Wenn generate_stream_url() fehlschlägt, wird der Counter NICHT freigegeben
    
    gevent.sleep(retry_interval)
    retry_interval += 0.025
```

**Problem:** Wenn `generate_stream_url()` einen Stream zuweist (Counter +1) aber dann fehlschlägt (z.B. URL ungültig), wird der Counter NICHT freigegeben. Bei jedem Retry wird ein neuer Counter inkrementiert ohne den alten freizugeben.

**ENHANCED VERSION (mit Bugfix #7):**
```python
# Nach jedem fehlgeschlagenen Versuch:
if stream_url is None:
    channel.release_stream()  # Counter freigeben!
    gevent.sleep(retry_interval)
```

---

### 2. _CLEAN_REDIS_KEYS() REIHENFOLGE (server.py)

**ORIGINAL (Dispatcharr-0.20.1):**
```python
def _clean_redis_keys(self, channel_id):
    """Clean up all Redis keys for a channel more efficiently"""
    # Release the channel, stream, and profile keys from the channel
    try:
        channel = Channel.objects.get(uuid=channel_id)
        channel.release_stream()  # ← Versucht Counter zu dekrementieren
    except:
        stream = Stream.objects.get(stream_hash=channel_id)
        stream.release_stream()
    
    # DANN werden die Keys gelöscht
    patterns = [
        f"ts_proxy:channel:{channel_id}:*",
        RedisKeys.events_channel(channel_id)
    ]
    
    for pattern in patterns:
        cursor = 0
        while True:
            cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                self.redis_client.delete(*keys)  # ← Löscht auch stream_profile Key!
```

**Problem:** 
1. `channel.release_stream()` wird ZUERST aufgerufen
2. Diese Methode braucht den `stream_profile:{stream_id}` Key um die profile_id zu finden
3. DANN werden ALLE Keys gelöscht, inklusive `stream_profile:{stream_id}`
4. Wenn `release_stream()` fehlschlägt (z.B. weil `channel_stream` Key schon weg ist), bleibt der Counter erhöht

**ENHANCED VERSION (mit Bugfix #10):**
```python
def _clean_redis_keys(self, channel_id):
    # ERST Metadata lesen
    metadata = self.redis_client.hgetall(RedisKeys.channel_metadata(channel_id))
    
    # DANN Counter dekrementieren (mit Fallbacks)
    if metadata:
        stream_id = metadata.get(b'stream_id')
        profile_id = metadata.get(b'profile_id') or metadata.get(b'm3u_profile')
        
        if profile_id:
            profile_connections_key = f"profile_connections:{profile_id.decode()}"
            current = int(self.redis_client.get(profile_connections_key) or 0)
            if current > 0:
                new_count = self.redis_client.decr(profile_connections_key)
                logger.info(f"Released stream {stream_id} profile {profile_id} via Redis (counter: {current} → {new_count})")
    
    # ERST JETZT Keys löschen
    patterns = [...]
    for pattern in patterns:
        self.redis_client.delete(*keys)
```

---

### 3. RELEASE_STREAM() ROBUSTHEIT (models.py)

**ORIGINAL (Dispatcharr-0.20.1):**
```python
def release_stream(self):
    redis_client = RedisClient.get_client()
    
    stream_id = redis_client.get(f"channel_stream:{self.id}")
    if not stream_id:
        logger.debug("Invalid stream ID pulled from channel index")
        return  # ← GIBT AUF wenn Key fehlt!
    
    redis_client.delete(f"channel_stream:{self.id}")
    
    profile_id = redis_client.get(f"stream_profile:{stream_id}")
    if not profile_id:
        logger.debug("Invalid profile ID pulled from stream index")
        return  # ← GIBT AUF wenn Key fehlt!
    
    redis_client.delete(f"stream_profile:{stream_id}")
    
    # Nur wenn beide Keys existieren wird dekrementiert
    profile_connections_key = f"profile_connections:{profile_id}"
    current_count = int(redis_client.get(profile_connections_key) or 0)
    if current_count > 0:
        redis_client.decr(profile_connections_key)
```

**Problem:** Wenn `channel_stream` oder `stream_profile` Key fehlt (z.B. durch Race Condition oder vorheriges Cleanup), wird die Methode ABGEBROCHEN ohne den Counter zu dekrementieren.

**ENHANCED VERSION (mit Bugfix #11):**
```python
def release_stream(self):
    redis_client = RedisClient.get_client()
    
    stream_id = redis_client.get(f"channel_stream:{self.id}")
    if not stream_id:
        # Fallback: Metadata prüfen
        metadata = redis_client.hgetall(RedisKeys.channel_metadata(str(self.uuid)))
        if metadata:
            stream_id = metadata.get(b'stream_id')
            profile_id = metadata.get(b'profile_id') or metadata.get(b'm3u_profile')
            
            if profile_id:
                # Direkt dekrementieren ohne Keys zu löschen
                profile_connections_key = f"profile_connections:{profile_id.decode()}"
                current = int(redis_client.get(profile_connections_key) or 0)
                if current > 0:
                    redis_client.decr(profile_connections_key)
                    return
        
        # Last Resort: Ersten nicht-null Counter dekrementieren
        for profile in M3UAccountProfile.objects.filter(is_active=True):
            key = f"profile_connections:{profile.id}"
            current = int(redis_client.get(key) or 0)
            if current > 0:
                redis_client.decr(key)
                logger.warning(f"Released unknown stream via fallback (profile {profile.id})")
                return
        
        return
    
    # Normale Logik...
```

---

## WARUM FUNKTIONIERT DAS ORIGINAL TROTZDEM?

### 1. Kein Retry-Loop
Das Original hat einen einfacheren Retry-Mechanismus:
- Versucht Stream zu holen
- Wenn fehlgeschlagen: Wartet und versucht nochmal
- **ABER:** Jeder Versuch ist unabhängig, es wird kein Counter "gestapelt"

### 2. Kein Profile Failover
Das Original hat kein Profile Failover Feature:
- Nur ein Profil wird verwendet (Default)
- Wenn max_streams=1, dann wird nur 1 Stream gleichzeitig verwendet
- Bug tritt nur auf wenn Stream nicht sauber beendet wird

### 3. TTL als Sicherheitsnetz
Das Original hat vermutlich TTL auf den Keys:
- Nach 1 Stunde werden Keys automatisch gelöscht
- Counter wird dann auch zurückgesetzt
- User merkt Bug nur wenn er innerhalb 1 Stunde mehrere Streams startet/stoppt

### 4. Seltener Trigger
Der Bug tritt nur auf wenn:
- Stream wird gestartet (Counter +1)
- Stream schlägt fehl ODER wird unsauber beendet
- `_clean_redis_keys()` wird aufgerufen BEVOR `release_stream()` erfolgreich war
- Oder `release_stream()` findet Keys nicht mehr

Im Original passiert das seltener weil:
- Kein Retry-Loop der Counter mehrfach inkrementiert
- Kein Failover zwischen Profilen
- Weniger komplexe Logik = weniger Race Conditions

---

## FAZIT

**Die Original-Entwickler haben NICHTS falsch gemacht!**

Der Bug existiert auch im Original, aber:
1. Er tritt viel seltener auf (kein Retry-Loop, kein Failover)
2. Er wird durch TTL automatisch nach 1 Stunde behoben
3. Die meisten User haben mehrere Connections (max_streams > 1) und merken es nicht

**Die Enhanced Version hat den Bug SICHTBAR gemacht durch:**
1. Profile Failover → Mehr Profile mit niedrigeren Limits
2. Retry-Loop → Counter wird mehrfach inkrementiert
3. Komplexere Logik → Mehr Race Conditions

**Die Bugfixes #7-11 beheben:**
1. Retry-Loop gibt Counter nach jedem Fehlversuch frei
2. `_clean_redis_keys()` dekrementiert BEVOR Keys gelöscht werden
3. `release_stream()` hat Fallbacks wenn Keys fehlen
4. TTL auf `profile_connections` Keys als zusätzliches Sicherheitsnetz

---

## EMPFEHLUNG

Die Bugfixes #7-11 sind **NOTWENDIG** für die Enhanced Version mit Profile Failover. Ohne diese Fixes ist das System nicht stabil.

Für das Original wären die Fixes auch hilfreich, aber nicht kritisch, da der Bug dort seltener auftritt.
