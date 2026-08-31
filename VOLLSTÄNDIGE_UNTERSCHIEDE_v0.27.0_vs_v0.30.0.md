# Vollständige Unterschiede v0.27.0 vs v0.30.0

## Executive Summary

v0.30.0 ist eine **MAJOR ARCHITECTURE REDESIGN** mit fundamentalen Änderungen in:
- Retry Logic (zeitfenster-basiert statt counter-basiert)
- Cooldown System (channel-specific statt global)
- Failover System (rotation-basiert statt LAST RESORT)

**Beide Versionen haben Profile Failover, aber die Implementierungen sind FUNDAMENTAL unterschiedlich!**

---

## 1. 🔴 RETRY LOGIC - FUNDAMENTAL REDESIGN

### v0.27.0: Einfacher Counter
```python
# Simple counter increment
self.retry_count += 1
if self.retry_count >= self.max_retries:  # max_retries = 2
    # Failover
```

**Verhalten:**
- Fester Counter ohne Auto-Reset
- Max 2 Retries (hardcoded)
- Reset nur bei erfolgreicher Verbindung

### v0.30.0: Zeitfenster-basiert ⭐ NEU

```python
def _record_connection_failure(self):
    now = time.time()
    # AUTO-RESET wenn letzte Failure > 30 Min her!
    if (self._last_failure_time is not None 
        and (now - self._last_failure_time) > self._retry_window_seconds):
        self.retry_count = 0
    self._last_failure_time = now
    self.retry_count += 1
```

**Config:**
```python
retry_window_seconds = 1800  # 30 Minuten
stable_connection_threshold = 30  # 30 Sekunden stabil
max_retries = 3  # Erhöht von 2 auf 3
```

**Verhalten:**
- Auto-Reset nach 30 Min ohne Failure
- Max 3 Retries
- Separate Methode `_clear_connection_failure_history()`

**IMPACT:**
- ✅ **v0.30.0 ist toleranter** bei temporären Problemen
- ✅ Streams können sich selbst erholen nach 30 Min
- ⚠️ **v0.27.0 ist aggressiver** bei Failover

---

## 2. 🔴 COOLDOWN SYSTEM - ARCHITECTURE CHANGE

### v0.27.0: GLOBAL Cooldown

**Redis Key:**
```python
def stream_cooldown(stream_id, profile_id):
    return f"live:cooldown:stream:{stream_id}:profile:{profile_id}"
```

**Scope:**
- **GLOBAL** über alle Channels hinweg
- Wenn Stream 123 + Profile 579 für Channel A failet → blockiert für ALLE Channels!

**Use Case:**
```
Channel A: Stream 123/Profile 579 failed → Cooldown gesetzt
Channel B: Will Stream 123/Profile 579 nutzen → BLOCKIERT! ❌
```

### v0.30.0: CHANNEL-SPECIFIC Cooldown ⭐ GEÄNDERT

**Redis Key:**
```python
def stream_cooldown(channel_id, stream_id, profile_id):
    return f"live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown"
```

**Scope:**
- **Per Channel isoliert**
- Stream 123 + Profile 579 kann für Channel A auf Cooldown sein, Channel B kann es nutzen

**Use Case:**
```
Channel A: Stream 123/Profile 579 failed → Cooldown nur für Channel A
Channel B: Will Stream 123/Profile 579 nutzen → OK! ✅
```

**IMPACT:**
- ✅ **v0.30.0 vermeidet Cross-Channel-Blockierung**
- ✅ Fairere Resource-Nutzung
- ⚠️ **v0.27.0 kann unnötig Channels blockieren**

---

## 3. 🔴 FAILOVER ROTATION SYSTEM

### v0.27.0: LAST RESORT Pattern

**Exhaustion Handling:**
```python
# Bei erschöpften Streams:
# 1. SCAN Redis für Cooldown-Keys
# 2. Sammle alle Keys
# 3. DELETE in Pipeline
# 4. Retry mit fresh list

if len(keys_to_delete) > 10000:
    logger.error("Possible leak! Aborting cleanup.")
    return False

pipe = redis_client.pipeline(transaction=False)
for key in keys_to_delete:
    pipe.delete(key)
pipe.execute()

logger.warning(f"LAST RESORT: Cleared {len(keys)} cooldowns")
self.tried_combinations.clear()
```

**Verhalten:**
- Komplex (~100 Zeilen Code)
- Brute-force Cooldown Clearing
- Safety-Checks gegen Leaks
- **Keine Wrap-Logik**

### v0.30.0: Kontrolliertes Rotation System ⭐ NEU

**Config:**
```python
max_stream_switches = 10  # Deutlich reduziert von 200!
failover_rotation_cooldown = 60  # Wartezeit vor Wrap
```

**Rotation State:**
```python
self._failover_rotation_passes = 0  # Zählt Wraps
self._rotation_cooldown_until = None  # Nächster Wrap-Zeitpunkt
self._had_successful_connection = False  # Cold start guard
```

**Methoden:**
```python
def _rotation_cooldown_remaining(self):
    """Gibt verbleibende Cooldown-Zeit zurück"""
    if self._rotation_cooldown_until is None:
        return None
    return max(0.0, self._rotation_cooldown_until - time.time())

def _try_next_stream_with_cooldown(self):
    """Wrapper für Failover mit Cooldown-Wait"""
    if self._try_next_stream():
        return True
    
    remaining = self._rotation_cooldown_remaining()
    if remaining is None:
        return False
    
    if remaining > 0:
        logger.warning(f"Waiting {remaining:.1f}s before wrapping failover")
        if not self._sleep_interruptible(remaining):
            return False
    
    return self._try_next_stream()

def reset_failover_rotation_state(self):
    """Manuelle Reset-Methode"""
    self.tried_combinations.clear()
    self.tried_stream_ids = set()
    self._failover_rotation_passes = 0
    self._rotation_cooldown_until = None
```

**Wrap-Logik:**
```python
# Prüfe Rotation Limit
if rotation_passes >= max_switches:  # max = 10
    logger.warning("Rotation limit reached")
    return False

# Arm Cooldown beim ersten Exhaustion
if cooldown_until is None:
    cooldown = ConfigHelper.failover_rotation_cooldown()  # 60s
    self._failover_rotation_passes += 1
    self._rotation_cooldown_until = now + cooldown
    logger.warning(f"Arming {cooldown}s wrap cooldown (pass {passes}/{max})")
    return False

# Warte bis Cooldown abgelaufen
if now < cooldown_until:
    return False

# Cooldown elapsed → Allow wrap
self._rotation_cooldown_until = None
self.tried_combinations = {(current_stream_id, current_profile_id)}
# Retry mit gefilteter Liste
```

**IMPACT:**
- ✅ **v0.30.0 ist vorhersagbarer** mit kontrollierten Pausen
- ✅ Verhindert Thrashing durch max 10 Switches
- ✅ Keine Redis-intensive SCAN-Operations
- ⚠️ **v0.27.0 erlaubt bis zu 200 Switches** (kann Thrashing verursachen)

---

## 4. PROFILE MANAGEMENT BEIM START

### v0.27.0: Cooldown-Check bei generate_stream_url()

```python
# In generate_stream_url() für Stream Preview:
cooldown_skip_profiles = set()
if ConfigHelper.stream_cooldown_enabled():
    redis_client = RedisClient.get_client()
    if redis_client:
        # Scan für Cooldown-Keys
        cooldown_pattern = f"live:cooldown:stream:{stream.id}:profile:*"
        for key in redis_client.scan_iter(match=cooldown_pattern, count=50):
            parts = key.split(':')
            profile_id = int(parts[-1])
            ttl = redis_client.ttl(key)
            logger.info(f"Skipping profile {profile_id} - blocked for {ttl}s")
            cooldown_skip_profiles.add(profile_id)

# Versuche non-cooled profile zu finden
for prof in profiles:
    if prof.id not in cooldown_skip_profiles:
        # Use this profile
        break
```

**Verhalten:**
- Cooldown-Check bei **jedem Stream-Start**
- Skippt Profiles auf Cooldown beim Connect
- Fallback wenn alle Profiles auf Cooldown

### v0.30.0: KEIN Cooldown-Check ⚠️ ENTFERNT

```python
# In generate_stream_url():
# Cooldown-Check WURDE ENTFERNT!
# Nur Connection-Limit Checks bleiben

stream_id, profile_id, error_reason, slot_reserved = stream.get_stream()
# Direkt ohne Cooldown-Check!
```

**Verhalten:**
- **Keine Cooldown-Checks** bei Stream-Start mehr
- Nur Connection-Limits werden geprüft
- Cooldowns werden erst bei Failover relevant

**CRITICAL DIFFERENCE:**
- ✅ **v0.27.0 vermeidet sofortige Retries** von failed Profiles
- ⚠️ **v0.30.0 kann failed Profiles wiederverwenden** bei Stream-Start

---

## 5. CONFIG DEFAULTS

| Setting | v0.27.0 | v0.30.0 | Comment |
|---------|---------|---------|---------|
| `max_retries` | 2 | 3 | ⬆️ Erhöht |
| `max_stream_switches` | 200 | 10 | ⬇️ **Drastisch reduziert!** |
| `url_switch_timeout` | 20 | 20 | Gleich |
| `failover_grace_period` | 20 | 20 | Gleich |
| `retry_window_seconds` | - | 1800 | ⭐ NEU |
| `stable_connection_threshold` | - | 30 | ⭐ NEU |
| `failover_rotation_cooldown` | - | 60 | ⭐ NEU |

---

## 6. HEALTH MONITORING

### v0.27.0: Gevent Events
```python
import gevent.event
self.needs_reconnect = gevent.event.Event()
self.needs_stream_switch = gevent.event.Event()

# Usage:
self.needs_reconnect.set()  # Set flag
if self.needs_reconnect.is_set():  # Check flag
```

### v0.30.0: Simple Booleans
```python
self.needs_reconnect = False
self.needs_stream_switch = False

# Usage:
self.needs_reconnect = True  # Set flag
if self.needs_reconnect:  # Check flag
```

**IMPACT:**
- ✅ **v0.30.0 ist simpler** und weniger Overhead
- Funktionell äquivalent

---

## 7. STREAM ORDERING

### v0.27.0:
- Keine spezielle Ordering-Funktion
- Streams in DB-Order

### v0.30.0: order_alternates_from_current() ⭐ NEU

```python
def order_alternates_from_current(
    alternate_streams: List[dict],
    ordered_stream_ids: List[int],
    current_stream_id: Optional[int],
) -> List[dict]:
    """
    Reorder failover candidates to start after the current stream,
    wrapping around (rotation).
    """
    if current_stream_id is None:
        return alternate_streams
    
    try:
        current_index = ordered_stream_ids.index(current_stream_id)
    except ValueError:
        return alternate_streams
    
    # Rotate list to start after current
    rotated = []
    for offset in range(1, len(ordered_stream_ids)):
        stream_id = ordered_stream_ids[(current_index + offset) % len(ordered_stream_ids)]
        entry = alt_by_id.get(stream_id)
        if entry is not None:
            rotated.append(entry)
    return rotated
```

**Use Case:**
```
Streams: [A, B, C, D, E]
Current: C
Order: [D, E, A, B]  # Startet nach C, wrapped around
```

---

## 8. INITIALIZATION

### v0.27.0: DB-Query für Channel Name
```python
def __init__(self, channel_id, url, buffer, ...):
    # DB Query!
    _name = Channel.objects.filter(uuid=channel_id).values_list('name', flat=True).first()
    self.channel_name = _name if _name else str(channel_id)
```

### v0.30.0: Redis/Parameter-based ⭐ OPTIMIERT
```python
def __init__(self, channel_id, url, buffer, ..., channel_name=None):  # NEU: channel_name param
    # KEIN DB Query mehr!
    redis_client = getattr(buffer, "redis_client", None)
    self.channel_name = resolve_channel_display_name(
        channel_id, 
        channel_name=channel_name,  # Prefer caller's name
        redis_client=redis_client   # Fallback to Redis
    )
```

**IMPACT:**
- ✅ **v0.30.0 vermeidet DB-Queries** beim Init
- ✅ Schnellere Initialization
- ✅ Weniger DB-Load in Hot Path

---

## 9. UNTERSCHIEDE IN CONFIG HELPER

### NUR in v0.27.0:
```python
def initial_behind_chunks():
    settings = Config.get_proxy_settings()
    return settings.get("initial_behind_chunks", 4)
```

### NUR in v0.30.0:
```python
def retry_window_seconds():
    return settings.get("retry_window_seconds", 1800)

def stable_connection_threshold():
    return settings.get("stable_connection_threshold", 30)

def failover_rotation_cooldown():
    return settings.get("failover_rotation_cooldown", 60)

def channel_client_wait_period():
    return Config.get_channel_client_wait_period()

def initial_behind_chunks():
    return ConfigHelper.get('INITIAL_BEHIND_CHUNKS', 4)  # Hardcoded statt DB!
```

---

## 10. ERROR HANDLING PATTERNS

### v0.27.0:
- Komplexe SCAN-basierte Cleanup
- LAST RESORT Pattern bei Exhaustion
- Pipeline-basierte Key Deletion
- Safety-Checks gegen Redis-Leaks

### v0.30.0:
- Simplere Error Patterns
- Rotation-basierte Wraps
- Kein SCAN-based Cleanup
- Kontrollierte Cooldown-Waits

---

## ZUSAMMENFASSUNG: WAS IST BESSER?

### v0.27.0 Vorteile:
✅ **Cooldown-Check bei Stream-Start** (vermeidet sofortige Retries)  
✅ **Aggressive Failover** (max 200 switches)  
✅ **LAST RESORT Recovery** (alle Cooldowns können gelöscht werden)

### v0.27.0 Nachteile:
❌ **Globale Cooldowns** (blockiert Cross-Channel)  
❌ **Kein Auto-Reset** von Retry Counter  
❌ **Komplexe SCAN-Logik** (Performance-Impact)

### v0.30.0 Vorteile:
✅ **Channel-Isolierte Cooldowns** (fairere Resource-Nutzung)  
✅ **Auto-Recovery** nach 30 Min (retry_window_seconds)  
✅ **Kontrollierte Rotation** mit Limits (kein Thrashing)  
✅ **Optimierte Init** (kein DB-Query)  
✅ **Sauberere Architektur** (weniger Complexity)

### v0.30.0 Nachteile:
❌ **Kein Cooldown-Check bei Start** (kann failed Profiles retry'en)  
❌ **Niedrigere Switch-Limits** (max 10 statt 200)  
❌ **Keine LAST RESORT Recovery** (stuck wenn alle Profiles failed)

---

## KRITISCHE UNTERSCHIEDE FÜR PRODUCTION

### 1. 🔴 COOLDOWN-CHECK bei Stream-Start FEHLT in v0.30.0

**Problem:**
```
13:00 - Stream 123/Profile 579 failed, Cooldown 600s gesetzt
13:02 - User startet Stream preview für Stream 123 neu
       v0.27.0: Checkt Cooldown, skippt Profile 579, wählt 580 ✅
       v0.30.0: Checkt NICHT, wählt 579 wieder → instant fail! ❌
```

**Workaround in v0.30.0:**
- Failover System greift nach Failure
- Aber: Ein unnötiger Retry-Versuch passiert

### 2. 🔴 MAX_STREAM_SWITCHES drastisch reduziert

**v0.27.0:** 200 Switches erlaubt → kann lange suchen  
**v0.30.0:** 10 Switches erlaubt → gibt schneller auf

**Impact:**
- ⚠️ Bei vielen Profiles könnte v0.30.0 zu früh aufgeben
- ✅ Aber: Verhindert Thrashing bei kaputten Streams

### 3. 🔴 GLOBAL vs CHANNEL-SPECIFIC Cooldowns

**v0.27.0 Problem:**
```
Channel A: nutzt Stream 123/Profile 579, failed → Cooldown
Channel B: Will Stream 123/Profile 579 nutzen → BLOCKIERT ❌
```

**v0.30.0 Solution:**
- Channel B kann Stream nutzen trotz Channel A Failure ✅

---

## MIT UNSEREM PATCH (tried_combinations Resets):

### Was haben wir hinzugefügt:
```python
# 1. Hourly Reset
self.tried_combinations_reset_time = time.time() + 3600
if time.time() > self.tried_combinations_reset_time:
    self.tried_combinations.clear()
    self.tried_combinations_reset_time = time.time() + 3600

# 2. Success-based Reset (5 Min)
if connection_duration > 300:
    self.tried_combinations.clear()

# 3. Cleanup on Stop
if len(self.tried_combinations) > 0:
    self.tried_combinations.clear()

# 4. Load profile_id from Redis
profile_id_bytes = redis_client.hget(metadata_key, ChannelMetadataField.M3U_PROFILE)
if profile_id_bytes:
    self.current_profile_id = int(profile_id_bytes.decode('utf-8'))
```

**Diese Features waren in v0.27.0, fehlten aber in v0.30.0!**

---

## FINALE BEWERTUNG

### v0.27.0:
- **Aggressive, globale Failover-Strategie**
- **Gut für**: Schnelles Durchprobieren vieler Optionen
- **Schlecht für**: Fairness zwischen Channels, Performance (SCAN)

### v0.30.0 (OHNE Patch):
- **Kontrollierte, isolierte Failover-Strategie**
- **Gut für**: Channel-Isolation, Performance, Vorhersagbarkeit
- **Schlecht für**: Frühe Aufgabe (max 10 switches), Keine Stream-Start Cooldown-Checks

### v0.30.0 + UNSER PATCH:
- **Best of Both Worlds**
- Behält: Channel-Isolation, Rotation System, Performance
- Fügt hinzu: Automatic Resets, Redis Persistence, Cleanup
- **EMPFOHLEN FÜR PRODUCTION** ✅

---

## NOCH FEHLENDE FEATURES in v0.30.0 (auch MIT Patch):

1. ❌ **Cooldown-Check bei generate_stream_url()**
   - Könnte sofortige Retries von failed Profiles verursachen
   - Workaround: Failover greift nach erstem Versuch

2. ❌ **LAST RESORT Pattern**
   - Keine Möglichkeit alle Cooldowns zu clearen bei Stuck
   - Workaround: Hourly reset catchet das (aber dauert bis zu 60 Min)

3. ❌ **Höhere max_stream_switches**
   - v0.30.0 hat nur 10 statt 200
   - Könnte bei vielen Profiles zu früh aufgeben

**Empfehlung:** Diese könnten als optionale Enhancements hinzugefügt werden, sind aber NICHT kritisch.

---

## DATEIEN MIT ÄNDERUNGEN

1. **apps/proxy/live_proxy/input/manager.py** - Hauptdatei, alle großen Änderungen
2. **apps/proxy/live_proxy/config_helper.py** - Neue Config-Settings
3. **apps/proxy/live_proxy/redis_keys.py** - Cooldown Key-Struktur
4. **apps/proxy/live_proxy/url_utils.py** - Cooldown-Check entfernt, Rotation hinzugefügt

---

## ANTWORT AUF DEINE FRAGE

**"Gibt es weitere Unterschiede?"**

**JA! v0.30.0 ist ein FUNDAMENTAL unterschiedliches System:**

1. **Retry Logic** - Zeitfenster-basiert (NEU)
2. **Cooldown Scope** - Channel-specific statt global (GEÄNDERT)
3. **Failover System** - Rotation statt LAST RESORT (GEÄNDERT)
4. **Max Switches** - 10 statt 200 (REDUZIERT)
5. **Stream Start** - Kein Cooldown-Check mehr (ENTFERNT)
6. **Health Monitoring** - Booleans statt Events (SIMPLIFIED)
7. **Initialization** - Redis statt DB (OPTIMIERT)

**Mit unserem Patch:** v0.30.0 ist **fast komplett** wie v0.27.0, aber mit besserer Architektur!

**Noch fehlend:** Cooldown-Check bei Stream-Start und LAST RESORT Pattern (optional).
