# Dispatcharr v0.20.1 Enhancements - Bugfix Summary

**Version:** v1.3.0  
**Datum:** 2026-03-12  
**Bugfixes:** 7 (4 Profile Failover + 1 Orphaned Cleanup + 1 Logo Timeout + 1 Connection Leak)

---

## Übersicht

Dieser Patch enthält 7 kritische Bugfixes:

| # | Datei | Problem | Status |
|---|-------|---------|--------|
| 1-4 | url_utils.py | Profile Failover Bugs | ✅ Gefixt |
| 5 | server.py | Orphaned Cleanup | ✅ Gefixt |
| 6 | api_views.py | Logo Timeout | ✅ Gefixt |
| 7 | views.py + models.py | Connection Leak | ✅ Gefixt |

---

## Bugfix 1-4: Profile Failover (url_utils.py)

### Problem
Profile Failover funktionierte nicht korrekt:
- Nur 1 Profile pro Stream wurde zurückgegeben (statt alle)
- `get_stream_info_for_profile()` Funktion fehlte komplett
- Proxy-Parameter fehlte in Transcode-Connection

### Lösung
```python
# VORHER: Nur 1 Profile
for profile in profiles:
    if available:
        return [{'stream_id': stream.id, 'profile_id': profile.id}]
        break  # ❌ Nur eines!

# NACHHER: ALLE Profile
for profile in profiles:
    if available:
        alternates.append({'stream_id': stream.id, 'profile_id': profile.id})
        # ✅ Kein break - ALLE Profile!
```

### Auswirkung
- **Vorher:** Nur 1 Profile pro Stream → Wenige Failover-Optionen
- **Nachher:** Alle Profile pro Stream → Maximale Failover-Optionen

---

## Bugfix 5: Orphaned Cleanup (server.py)

### Problem
Redis Keys für gelöschte Channels wurden nicht aufgeräumt:
```python
# VORHER:
try:
    channel.release_stream()
except:
    pass  # ❌ Redis Keys bleiben!
```

### Lösung
```python
# NACHHER:
try:
    channel.release_stream()
except Channel.DoesNotExist:
    # ✅ Channel gelöscht - Redis trotzdem aufräumen
    redis_client.delete(f"profile_connections:{profile_id}")
```

### Auswirkung
- **Vorher:** Endlose Cleanup-Zyklen für gelöschte Channels
- **Nachher:** Redis Keys werden korrekt gelöscht

**Hinweis:** Original Dispatcharr Bug (nicht durch unsere Enhancements verursacht)

---

## Bugfix 6: Logo Timeout (api_views.py)

### Problem
Logo-Downloads von langsamen Servern schlugen mit Timeout fehl:
```
WARNING apps.channels.api_views Timeout fetching logo from https://logos.jesmann.com/KABEL1H.png
```

### Lösung
```python
# VORHER:
timeout=(3, 5)  # 3s connect, 5s read - zu kurz!

# NACHHER:
timeout=(10, 15)  # 10s connect, 15s read - ausreichend
```

### Auswirkung
- **Vorher:** Logos von langsamen Servern werden nicht geladen (404)
- **Nachher:** Logos werden korrekt geladen

**Hinweis:** Original Dispatcharr Bug (nicht durch unsere Enhancements verursacht)

---

## Bugfix 7: Connection Leak (views.py + models.py) - KRITISCH!

### Problem
Profile Connection Counter steigt bei jedem Retry-Versuch:

```
ERROR ts_proxy.url_utils No profiles available with connection capacity for M3U account 224
```

**Root Cause:**
```python
# VORHER (BUGGY):
while retry:
    stream_url = generate_stream_url(channel_id)
    # ↓ Ruft get_stream() auf → Counter +1
    # ↓ Counter: 0 → 1 → 2 → 3 → ... → 14
    if stream_url:
        break
    # ❌ Counter wird NICHT dekrementiert!

# Ergebnis: Counter = 14 (sollte 0 sein!)
```

### Lösung

**Fix 1: Release nach jedem fehlgeschlagenen Versuch (views.py)**
```python
# NACHHER (GEFIXT):
while retry:
    stream_url = generate_stream_url(channel_id)
    # ↓ Counter: 0 → 1
    
    if stream_url:
        break  # ✅ Erfolg! Counter bleibt bei 1
    
    # ❌ Fehler! Gebe Counter frei
    channel.release_stream()  # ✅ Counter: 1 → 0
    gevent.sleep(retry_interval)

# Wenn alle Versuche fehlschlagen:
channel.release_stream()  # ✅ Finaler Cleanup
```

**Fix 2: TTL als Sicherheitsnetz (models.py)**
```python
# NACHHER:
if profile.max_streams > 0:
    redis_client.incr(profile_connections_key)
    redis_client.expire(profile_connections_key, 3600)  # ✅ 1 Stunde TTL
```

### Auswirkung
- **Vorher:** 14 Retry-Versuche → Counter = 14 → Profile "voll" → Fehler
- **Nachher:** 14 Retry-Versuche → Counter bleibt bei 1 → wird freigegeben → Profile verfügbar
- **Sicherheitsnetz:** Counter läuft nach 1 Stunde automatisch ab (bei Crashes)

### Warum wurde das Problem erst jetzt sichtbar?

**Früher (v0.17/v0.18):**
- Weniger Profile pro Account (1-2)
- Höhere max_streams Limits (5-10)
- Problem war nicht sichtbar

**Jetzt (v0.19/v0.20.1 mit Profile Failover):**
- Mehr Profile pro Account (2-5)
- Niedrigere max_streams Limits (1-2)
- Profile Failover nutzt ALLE Profile
- **Problem wird sichtbar!**

**Hinweis:** Original Dispatcharr Bug seit v0.17 (nicht durch unsere Enhancements verursacht)

---

## Sofort-Lösung (Workaround)

Wenn du das Problem JETZT hast (vor dem Patch):

```bash
# Option 1: Python Script
python reset_profile_connections.py

# Option 2: Redis CLI - Alle Profile
docker exec -it <redis-container> redis-cli KEYS "profile_connections:*" | xargs docker exec -it <redis-container> redis-cli DEL

# Option 3: Spezifische Profile
docker exec -it <redis-container> redis-cli DEL profile_connections:224 profile_connections:229
```

---

## Installation

```bash
cd Dispatcharr-0.20.1
chmod +x ../install_v0.20.1_enhancements.sh
../install_v0.20.1_enhancements.sh

# Docker Images neu bauen
docker build -f docker/DispatcharrBase -t dispatcharr:base .
docker build -f docker/Dockerfile --build-arg BASE_TAG=base -t dispatcharr:0.20.1 .
docker-compose down
docker-compose up -d
```

---

## Verifikation

### Test 1: Profile Failover
```bash
# Prüfe dass alle Profile zurückgegeben werden
python manage.py shell << EOF
from apps.proxy.ts_proxy.url_utils import get_alternate_streams
alternates = get_alternate_streams('channel-uuid', 123)
print(f"Found {len(alternates)} alternate stream/profile combinations")
EOF
```

### Test 2: Orphaned Cleanup
```bash
# Prüfe dass Redis Keys gelöscht werden
docker logs dispatcharr | grep "Released stream allocation for zombie channel"
```

### Test 3: Logo Timeout
```bash
# Prüfe dass Logos geladen werden
curl -I http://localhost:8000/api/channels/logos/5185/cache/
# Sollte 200 OK sein (nicht 404)
```

### Test 4: Connection Leak
```bash
# Prüfe dass Counter nicht steigt
docker exec -it <redis-container> redis-cli GET profile_connections:224
# Sollte 0 oder niedrig sein (nicht 14+)
```

---

## Zusammenfassung

| Bugfix | Kritikalität | Status | Hinweis |
|--------|--------------|--------|---------|
| 1-4: Profile Failover | Hoch | ✅ Gefixt | Unsere Enhancements |
| 5: Orphaned Cleanup | Mittel | ✅ Gefixt | Original Bug |
| 6: Logo Timeout | Niedrig | ✅ Gefixt | Original Bug |
| 7: Connection Leak | **KRITISCH** | ✅ Gefixt | Original Bug seit v0.17 |

**Alle Bugfixes sind in v0.20.1 Patch v1.3.0 enthalten!**

---

**Erstellt:** 2026-03-08  
**Aktualisiert:** 2026-03-12 (Bugfix 7 hinzugefügt)  
**Version:** 1.3.0  
**Status:** PRODUKTIONSREIF
