# Connection Leak - Vollständige Lösung

**Problem:** Profile Connection Counter wird nicht freigegeben  
**Status:** ✅ KOMPLETT GEFIXT  
**Datum:** 2026-03-12  
**Patch Version:** v1.5.0

---

## Problem-Übersicht

### Symptom

```
ERROR No profiles available with connection capacity for M3U account 224
```

User kann keinen Stream starten, obwohl KEIN Stream läuft!

### Root Cause

**Original Dispatcharr Bug seit v0.17:**

Profile Connection Counter wird in mehreren Szenarien NICHT freigegeben:
1. ❌ Retry-Loop inkrementiert Counter bei jedem Versuch
2. ❌ Preview-Pfad gibt Counter nicht frei bei Fehler
3. ❌ Letzter Client gibt Counter nicht frei (DB-Lookup schlägt fehl)
4. ❌ Server Cleanup gibt Counter nicht frei (UUID-Validierung schlägt fehl)

---

## Die Komplette Lösung (4 Bugfixes)

### Bugfix #7: Retry-Loop (views.py + models.py)

**Problem:** Counter steigt bei jedem Retry-Versuch

```python
# VORHER (BUGGY):
while retry:
    stream_url = generate_stream_url(channel_id)
    # ↑ Ruft get_stream() auf → Counter++
    # ❌ Counter wird NICHT dekrementiert bei Fehler!
    
# Nach 14 Versuchen: Counter = 14 (sollte 0 sein!)
```

**Lösung:**

```python
# NACHHER (GEFIXT):
while retry:
    stream_url = generate_stream_url(channel_id)
    
    if stream_url:
        break  # Erfolg!
    
    # ✅ Release nach jedem fehlgeschlagenen Versuch
    try:
        channel.release_stream()
        logger.debug(f"Released stream after failed attempt {attempt}")
    except Exception as e:
        logger.debug(f"Could not release stream: {e}")
```

**Zusätzlich: TTL Sicherheitsnetz (models.py)**

```python
# In Channel.get_stream():
if profile.max_streams > 0:
    redis_client.incr(profile_connections_key)
    # ✅ TTL: Counter läuft nach 1 Stunde automatisch ab
    redis_client.expire(profile_connections_key, 3600)
```

**Dateien:**
- `apps/proxy/ts_proxy/views.py` (Zeile ~196, ~238)
- `apps/channels/models.py` (Zeile ~478)

---

### Bugfix #8: Preview-Pfad (url_utils.py)

**Problem:** Preview gibt Counter nicht frei bei Fehler

```python
# VORHER (BUGGY):
if isinstance(channel_or_stream, Stream):
    # Preview-Pfad
    stream_id, profile_id = get_stream(...)
    # ↑ Counter++
    
    if not stream_id:
        # ❌ Counter wird NICHT dekrementiert!
        return None
```

**Lösung:**

```python
# NACHHER (GEFIXT):
if isinstance(channel_or_stream, Stream):
    stream_id, profile_id = get_stream(...)
    
    if not stream_id or not profile_id:
        # ✅ Release wenn get_stream() fehlschlägt
        try:
            channel.release_stream()
            logger.debug(f"Released stream after get_stream() failed in preview")
        except Exception as e:
            logger.debug(f"Could not release stream: {e}")
        return None
```

**Datei:**
- `apps/proxy/ts_proxy/url_utils.py` (Zeile ~1050)

---

### Bugfix #9: Letzter Client (stream_generator.py)

**Problem:** Letzter Client gibt Counter nicht frei (DB-Lookup schlägt fehl)

```python
# VORHER (BUGGY):
def _cleanup():
    if client_count <= 1:
        # ❌ Versucht DB-Lookup
        channel = Channel.objects.get(uuid=self.channel_id)
        # ↑ Schlägt fehl wenn channel_id ein Stream-Hash ist!
        # ↑ Schlägt fehl wenn Channel aus DB gelöscht wurde!
        channel.release_stream()
```

**Lösung:**

```python
# NACHHER (GEFIXT):
def _cleanup():
    if client_count == 0:  # ✅ Nur wenn KEINE Clients mehr
        # ✅ Release via Redis (kein DB-Lookup!)
        metadata_key = RedisKeys.channel_metadata(self.channel_id)
        metadata = proxy_server.redis_client.hgetall(metadata_key)
        
        if metadata:
            stream_id_bytes = metadata.get(b'stream_id')
            profile_id_bytes = metadata.get(b'profile_id')
            
            if stream_id_bytes and profile_id_bytes:
                stream_id = int(stream_id_bytes.decode('utf-8'))
                profile_id = int(profile_id_bytes.decode('utf-8'))
                
                # ✅ Release direkt via Redis
                redis_client.delete(f"channel_stream:{self.channel_id}")
                redis_client.delete(f"stream_profile:{stream_id}")
                
                # ✅ Decrement Counter
                profile_connections_key = f"profile_connections:{profile_id}"
                current_count = int(redis_client.get(profile_connections_key) or 0)
                if current_count > 0:
                    redis_client.decr(profile_connections_key)
                    logger.info(f"Released stream {stream_id} profile {profile_id} (counter: {current_count} → {current_count-1})")
```

**Datei:**
- `apps/proxy/ts_proxy/stream_generator.py` (Zeile ~444)

---

### Bugfix #10: Server Cleanup (server.py)

**Problem:** Server Cleanup gibt Counter nicht frei (UUID-Validierung schlägt fehl)

```python
# VORHER (BUGGY):
def _clean_redis_keys(self, channel_id):
    try:
        # ❌ Versucht UUID-Lookup
        channel = Channel.objects.get(uuid=channel_id)
        # ↑ Schlägt fehl wenn channel_id ein Stream-Hash ist!
        # ↑ Fehler: "is not a valid UUID"
        channel.release_stream()
    except Channel.DoesNotExist:
        # ❌ Versucht Stream-Hash-Lookup
        stream = Stream.objects.get(stream_hash=channel_id)
        stream.release_stream()
```

**Lösung:**

```python
# NACHHER (GEFIXT):
def _clean_redis_keys(self, channel_id):
    # ✅ Release via Redis (kein DB-Lookup!)
    # ✅ Funktioniert für UUIDs UND Stream-Hashes
    if self.redis_client:
        metadata_key = RedisKeys.channel_metadata(channel_id)
        metadata = self.redis_client.hgetall(metadata_key)
        
        if metadata:
            stream_id_bytes = metadata.get(b'stream_id')
            profile_id_bytes = metadata.get(b'profile_id')
            
            if stream_id_bytes and profile_id_bytes:
                stream_id = int(stream_id_bytes.decode('utf-8'))
                profile_id = int(profile_id_bytes.decode('utf-8'))
                
                # ✅ Release direkt via Redis
                self.redis_client.delete(f"channel_stream:{channel_id}")
                self.redis_client.delete(f"stream_profile:{stream_id}")
                
                # ✅ Decrement Counter
                profile_connections_key = f"profile_connections:{profile_id}"
                current_count = int(self.redis_client.get(profile_connections_key) or 0)
                if current_count > 0:
                    self.redis_client.decr(profile_connections_key)
                    logger.info(f"Released stream {stream_id} profile {profile_id} via Redis (counter: {current_count} → {current_count-1})")
```

**Dateien:**
- `apps/proxy/ts_proxy/server.py` (Zeile ~1338, ~790)

---

## Zusammenfassung: Alle Release-Pfade

| # | Szenario | Datei | Bugfix | Methode | Status |
|---|----------|-------|--------|---------|--------|
| 1 | Retry fehlgeschlagen | views.py | #7 | DB | ✅ |
| 2 | Alle Retries fehlgeschlagen | views.py | #7 | DB | ✅ |
| 3 | Preview fehlgeschlagen | url_utils.py | #8 | DB | ✅ |
| 4 | Letzter Client disconnected | stream_generator.py | #9 | Redis | ✅ |
| 5 | Channel gestoppt | server.py | #10 | Redis | ✅ |
| 6 | Zombie Cleanup | server.py | #10 | Redis | ✅ |
| 7 | TTL Sicherheitsnetz | models.py | #7 | Auto | ✅ |

**Warum unterschiedliche Methoden?**

- **DB-basiert (views.py, url_utils.py):** Channel-Objekt ist verfügbar, einfacher
- **Redis-basiert (server.py, stream_generator.py):** Channel-Objekt nicht verfügbar oder Hash statt UUID

---

## Test-Szenario

### Vorher (BUGGY):

```
User startet RTL HD → Stream läuft → User stoppt Stream
═══════════════════════════════════════════════════════════════

Logs:
16:19:15 ERROR Error releasing stream: "..." is not a valid UUID

Redis:
profile_connections:224 = 1 ❌

Nächster Stream:
ERROR No profiles available ❌
```

### Nachher (GEFIXT):

```
User startet RTL HD → Stream läuft → User stoppt Stream
═══════════════════════════════════════════════════════════════

Logs:
16:19:15 INFO Released stream 841034 profile 224 via Redis (counter: 1 → 0)

Redis:
profile_connections:224 = 0 ✅

Nächster Stream:
Stream startet erfolgreich ✅
```

---

## Installation

Der komplette Fix ist in **v0.20.1 Patch v1.5.0** enthalten:

```bash
cd Dispatcharr-0.20.1
chmod +x ../install_v0.20.1_enhancements.sh
../install_v0.20.1_enhancements.sh

# Docker Images neu bauen
docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .

# Container neu starten
docker-compose down
docker-compose up -d
```

---

## Verifikation

### Test 1: Normaler Stream

```bash
# Starte Stream
curl http://localhost:8000/stream/channel-hash

# Prüfe Counter (sollte 1 sein)
docker exec -it redis redis-cli GET profile_connections:224

# Stoppe Stream (Ctrl+C)

# Prüfe Counter (sollte 0 sein) ✅
docker exec -it redis redis-cli GET profile_connections:224
```

### Test 2: Mehrere Streams nacheinander

```bash
# Stream 1
curl http://localhost:8000/stream/hash1
# Stoppe
# Counter sollte 0 sein ✅

# Stream 2 (gleicher Provider)
curl http://localhost:8000/stream/hash2
# Sollte SOFORT funktionieren ✅
# Nicht: "No profiles available" ❌
```

### Test 3: Logs prüfen

```bash
# Sollte KEINE UUID-Fehler mehr geben:
docker logs Dispatcharr 2>&1 | grep "is not a valid UUID"
# Sollte leer sein ✅

# Sollte Release-Meldungen zeigen:
docker logs Dispatcharr 2>&1 | grep "Released stream.*via Redis"
# Sollte Einträge zeigen ✅

# Sollte Release-Meldungen zeigen (Retry):
docker logs Dispatcharr 2>&1 | grep "Released stream after failed attempt"
# Sollte Einträge zeigen ✅
```

---

## Warum wurde das Problem erst jetzt sichtbar?

### Früher (v0.17/v0.18):
- Weniger Profile pro Account (1-2)
- Höhere max_streams Limits (5-10)
- Problem war nicht sichtbar

### Jetzt (v0.19/v0.20.1 mit Profile Failover):
- Mehr Profile pro Account (2-5)
- Niedrigere max_streams Limits (1-2)
- Profile Failover nutzt ALLE Profile
- **Problem wird sichtbar!**

**Das ist ein Original Dispatcharr Bug seit v0.17!**  
Unsere v0.19.0 Enhancements haben das Problem NICHT verursacht, sondern nur sichtbar gemacht.

---

## Zusammenfassung

### Problem
- Counter wird in 4 verschiedenen Szenarien nicht freigegeben
- User bekommt "No profiles available" obwohl keine Streams laufen
- Original Dispatcharr Bug seit v0.17

### Lösung
- 4 Bugfixes (#7, #8, #9, #10)
- DB-basierte Release wo möglich
- Redis-basierte Release wo nötig
- TTL als Sicherheitsnetz

### Ergebnis
- ✅ Counter wird IMMER freigegeben
- ✅ Keine UUID-Fehler mehr
- ✅ Streams funktionieren nacheinander
- ✅ Keine "No profiles available" Fehler
- ✅ Funktioniert für UUIDs UND Stream-Hashes
- ✅ Funktioniert auch wenn Channel aus DB gelöscht wurde

---

**Erstellt:** 2026-03-12  
**Version:** 1.0  
**Status:** PRODUKTIONSREIF ✅
