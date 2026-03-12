# Connection Leak Fix - Bugfix #7

**Problem:** Profile Connection Leak seit Dispatcharr v0.17  
**Status:** ✅ GEFIXT in v0.20.1 Patch v1.3.0  
**Datum:** 2026-03-12

---

## Problem-Beschreibung

### Symptome

```
ERROR ts_proxy.url_utils No profiles available with connection capacity for M3U account 224
```

- Profile erscheinen "voll" obwohl keine Streams laufen
- Neue Stream-Requests bekommen 503 Service Unavailable
- Problem tritt auf bei Accounts mit niedrigen max_streams Limits (1-2)
- Counter in Redis steigt kontinuierlich

### Root Cause

**Retry-Loop ruft `get_stream()` mehrfach auf:**

```python
# VORHER (BUGGY):
while retry:
    stream_url = generate_stream_url(channel_id)
    # ↓ Ruft channel.get_stream() auf
    # ↓ get_stream() inkrementiert Counter: profile_connections:224
    # ↓ Counter: 0 → 1 → 2 → 3 → ... → 14
    
    if stream_url:
        break
    
    # ❌ PROBLEM: Counter wird NICHT dekrementiert!
    gevent.sleep(retry_interval)

# Wenn alle Versuche fehlschlagen:
# ❌ Counter bleibt bei 14 (sollte 0 sein!)
```

### Beispiel-Szenario

```
User startet RTL HD:
═══════════════════════════════════════════════════════════════

Profile: max_streams = 1 (nur 1 Stream gleichzeitig erlaubt)

Versuch 1:
  ├─ get_stream() → Counter: 0 → 1 ✅
  ├─ Versuche zu verbinden... FEHLER! ❌
  └─ Counter bleibt bei 1 ❌

Versuch 2:
  ├─ get_stream() → Counter: 1 → 2 ❌❌
  ├─ Prüft: Counter = 2, max = 1 → "VOLL!"
  └─ Fehler: "No profiles available"

User bekommt Fehler, obwohl KEIN Stream läuft!
Counter = 2, sollte 0 sein!
```

---

## Die Lösung

### Fix 1: Release nach jedem fehlgeschlagenen Versuch

```python
# NACHHER (GEFIXT):
while retry:
    stream_url = generate_stream_url(channel_id)
    # ↓ Ruft channel.get_stream() auf
    # ↓ Counter: 0 → 1
    
    if stream_url:
        # ✅ ERFOLG! Counter bleibt bei 1
        # ✅ Wird später bei Stream-Ende freigegeben
        break
    
    # ❌ FEHLER! Gebe Counter sofort frei
    try:
        channel.release_stream()  # ✅ Counter: 1 → 0
        logger.debug(f"Released stream after failed attempt")
    except Exception as e:
        logger.debug(f"Could not release stream: {e}")
    
    gevent.sleep(retry_interval)

# Wenn alle Versuche fehlschlagen:
try:
    channel.release_stream()  # ✅ Finaler Cleanup
except Exception as e:
    logger.debug(f"Could not release stream: {e}")
```

### Fix 2: TTL als Sicherheitsnetz

```python
# In apps/channels/models.py - Channel.get_stream()

if profile.max_streams > 0:
    redis_client.incr(profile_connections_key)
    # ✅ TTL: Counter läuft nach 1 Stunde automatisch ab
    redis_client.expire(profile_connections_key, 3600)
```

**Vorteil:** Selbst wenn `release_stream()` nie aufgerufen wird (Crash, Exception), wird der Counter nach 1 Stunde automatisch zurückgesetzt.

---

## Vergleich: Vorher vs. Nachher

### Vorher (BUGGY):

```
User startet Stream → 14 Retry-Versuche → Fehler
═══════════════════════════════════════════════════════════════

Counter-Verlauf:
Versuch 1:  Counter 0 → 1
Versuch 2:  Counter 1 → 2
Versuch 3:  Counter 2 → 3
...
Versuch 14: Counter 13 → 14

Ergebnis: Counter = 14 (BLEIBT SO!) ❌
Nächster User: "No profiles available" ❌
```

### Nachher (GEFIXT):

```
User startet Stream → 14 Retry-Versuche → Fehler
═══════════════════════════════════════════════════════════════

Counter-Verlauf:
Versuch 1:  Counter 0 → 1 → 0 (release)
Versuch 2:  Counter 0 → 1 → 0 (release)
Versuch 3:  Counter 0 → 1 → 0 (release)
...
Versuch 14: Counter 0 → 1 → 0 (release)

Ergebnis: Counter = 0 ✅
Nächster User: Stream funktioniert ✅
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

## Betroffene Dateien

### 1. apps/proxy/ts_proxy/views.py

**Änderungen:**
- Release nach jedem fehlgeschlagenen Retry-Versuch
- Finaler Cleanup wenn alle Versuche fehlschlagen
- Try-Except um Fehler zu vermeiden wenn Stream nicht reserviert war

### 2. apps/channels/models.py

**Änderungen:**
- TTL (1 Stunde) für profile_connections Keys
- Automatischer Cleanup bei vergessenen Releases

---

## Sofort-Lösung (Workaround)

Wenn du das Problem JETZT hast (vor dem Patch):

```bash
# Option 1: Python Script
python reset_profile_connections.py

# Option 2: Redis CLI
docker exec -it <redis-container> redis-cli KEYS "profile_connections:*" | xargs docker exec -it <redis-container> redis-cli DEL

# Option 3: Spezifische Profile
docker exec -it <redis-container> redis-cli DEL profile_connections:224 profile_connections:229
```

---

## Installation

Der Fix ist in **v0.20.1 Patch v1.3.0** enthalten:

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

Nach dem Patch sollten keine "No profiles available" Fehler mehr auftreten:

```bash
# Prüfe Redis Counter
docker exec -it <redis-container> redis-cli KEYS "profile_connections:*"

# Prüfe Counter-Werte
docker exec -it <redis-container> redis-cli GET profile_connections:224

# Sollte 0 oder niedrig sein (nicht 14+)
```

---

## Zusammenfassung

✅ **Problem:** Counter steigt bei jedem Retry-Versuch  
✅ **Lösung:** Release nach jedem fehlgeschlagenen Versuch  
✅ **Sicherheitsnetz:** TTL (1 Stunde) für automatischen Cleanup  
✅ **Status:** Gefixt in v0.20.1 Patch v1.3.0  
✅ **Auswirkung:** Keine "No profiles available" Fehler mehr  

---

**Erstellt:** 2026-03-12  
**Version:** 1.0  
**Status:** PRODUKTIONSREIF
