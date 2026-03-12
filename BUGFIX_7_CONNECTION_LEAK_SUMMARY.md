# Bugfix #7: Connection Leak - Schnellübersicht

**Status:** ✅ GEFIXT  
**Version:** v0.20.1 Patch v1.3.0  
**Datum:** 2026-03-12  
**Kritikalität:** HOCH

---

## Problem in 3 Sätzen

Profile Connection Counter steigt bei jedem Retry-Versuch, wird aber nie dekrementiert. Nach 14 Versuchen ist der Counter bei 14 statt 0. Profile erscheinen "voll" obwohl keine Streams laufen.

---

## Symptom

```
ERROR ts_proxy.url_utils No profiles available with connection capacity for M3U account 224
```

---

## Root Cause

```python
# BUGGY:
while retry:
    generate_stream_url()  # Ruft get_stream() auf → Counter +1
    # Counter: 0 → 1 → 2 → 3 → ... → 14
    # ❌ Wird NIE dekrementiert!
```

---

## Fix

```python
# GEFIXT:
while retry:
    generate_stream_url()  # Counter +1
    if erfolg:
        break
    channel.release_stream()  # ✅ Counter -1
```

**Plus TTL (1 Stunde) als Sicherheitsnetz**

---

## Sofort-Lösung

```bash
# Alle Profile-Counter zurücksetzen
docker exec -it <redis-container> redis-cli KEYS "profile_connections:*" | xargs docker exec -it <redis-container> redis-cli DEL
```

---

## Installation

```bash
cd Dispatcharr-0.20.1
chmod +x ../install_v0.20.1_enhancements.sh
../install_v0.20.1_enhancements.sh
docker-compose down
docker-compose up -d
```

---

## Betroffene Dateien

1. `apps/proxy/ts_proxy/views.py` - Release nach jedem Retry
2. `apps/channels/models.py` - TTL für Counter

---

## Wichtig

- **Original Dispatcharr Bug seit v0.17**
- Nicht durch v0.19.0 Enhancements verursacht
- Wurde nur durch Profile Failover sichtbar
- Betrifft Accounts mit niedrigen max_streams (1-2)

---

**Mehr Details:** `CONNECTION_LEAK_FIX.md`
