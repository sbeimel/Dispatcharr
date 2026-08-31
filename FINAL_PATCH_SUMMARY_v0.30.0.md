# 🎯 Dispatcharr v0.30.0 - COMPLETE FIX PATCH
## Alle fehlenden v0.27.0 Features + LAST RESORT System

---

## 📋 Zusammenfassung

Dieser Patch fügt **ALLE fehlenden v0.27.0 Features** zu v0.30.0 hinzu und implementiert das **LAST RESORT System** statt des problematischen 60s-Wait Rotation Systems.

---

## ✅ Was wurde gefixt?

### 1️⃣ **LAST RESORT System** (NEU - besser als v0.30.0 Rotation!)
**Problem:** v0.30.0 wartet 60s wenn alle Streams probiert wurden, aber Cooldowns sind dann IMMER NOCH aktiv!

**Lösung:** Wie v0.27.0 - Redis SCAN + DELETE alle Cooldowns → SOFORT retry

```python
# Wenn alle Stream/Profile-Kombinationen probiert wurden:
if not untried_streams:
    logger.warning("[COOLDOWN] LAST RESORT: Clearing all cooldowns")
    
    # Redis SCAN für channel-specific cooldown keys
    keys_to_delete = []
    for stream_id in all_stream_ids:
        pattern = f"live:channel:{channel_id}:stream:{stream_id}:profile:*"
        keys_to_delete.extend(redis_client.scan_iter(match=pattern))
    
    # DELETE alle Cooldowns
    if keys_to_delete:
        redis_client.delete(*keys_to_delete)
        logger.info(f"Cleared {len(keys_to_delete)} cooldown keys")
    
    # Clear tried_combinations und retry SOFORT
    self.tried_combinations.clear()
    # KEIN return False → sofortiger retry!
```

**Vorteile:**
- ✅ Kein schwarzer Bildschirm für User
- ✅ Keine nutzlose Wartezeit wenn Cooldowns eh noch aktiv sind
- ✅ "Instabiler Stream ist besser als GAR KEIN Stream"
- ✅ Max 200 Versuche (konfigurierbar via Frontend)

---

### 2️⃣ **Hourly Reset** (3600s)
**Problem:** `tried_combinations` wurde nie zurückgesetzt → nach ein paar Stunden keine Optionen mehr

**Lösung:**
```python
# In __init__:
self.tried_combinations_reset_time = time.time() + 3600

# In main loop:
if time.time() > self.tried_combinations_reset_time:
    logger.info("Hourly tried_combinations reset")
    self.tried_combinations.clear()
    self.tried_combinations_reset_time = time.time() + 3600
```

**Effekt:** Jede Stunde werden alle Profile wieder verfügbar (unabhängig vom Cooldown)

---

### 3️⃣ **Success-Based Reset** (5 Min stabile Verbindung)
**Problem:** Nach erfolgreichem Stream waren alte fehlgeschlagene Profile immer noch "tried"

**Lösung:**
```python
# In _process_stream_data():
if not stable_streaming_reset_done and len(self.tried_combinations) > 0:
    connection_duration = time.time() - self.connection_start_time
    if connection_duration > 300:  # 5 Minuten
        logger.info(f"Stream stable for {connection_duration:.0f}s - clearing tried_combinations")
        self.tried_combinations.clear()
        stable_streaming_reset_done = True
```

**Effekt:** Nach 5 Min stabilem Stream → alle Profile wieder verfügbar

---

### 4️⃣ **Cleanup on Stop**
**Problem:** `tried_combinations` wurde beim Channel-Stop nicht geleert

**Lösung:**
```python
# In stop():
if hasattr(self, 'tried_combinations') and len(self.tried_combinations) > 0:
    logger.info(f"Clearing {len(self.tried_combinations)} tried combinations on stop")
    self.tried_combinations.clear()
```

**Effekt:** Sauberer Neustart beim nächsten Channel-Start

---

### 5️⃣ **Load current_profile_id from Redis**
**Problem:** Beim Reconnect wusste der Manager nicht welches Profil gerade aktiv war

**Lösung:**
```python
# In __init__:
profile_id_bytes = redis_client.hget(metadata_key, ChannelMetadataField.M3U_PROFILE)
if profile_id_bytes:
    self.current_profile_id = int(profile_id_bytes.decode('utf-8'))
    logger.info(f"Loaded profile ID {self.current_profile_id} from Redis")
```

**Effekt:** Bessere Kontinuität bei Reconnects

---

### 6️⃣ **HTTP Streamer Race Condition Fix**
**Problem:** AttributeError beim Shutdown: `'NoneType' object has no attribute 'read'`

**Lösung:**
```python
except AttributeError as e:
    if "'NoneType' object has no attribute 'read'" in str(e):
        logger.debug("HTTP reader stopped during shutdown (expected race condition)")
    else:
        logger.error(f"HTTP reader attribute error: {e}", exc_info=True)
```

**Effekt:** Keine Error-Logs mehr beim sauberen Shutdown

---

### 7️⃣ **Cooldown-Check bei Stream Start** ⭐ KRITISCH!
**Problem:** v0.30.0 prüfte Cooldowns NICHT beim Start → blockte Profile wurden sofort wieder probiert!

**Lösung:**
```python
# In generate_stream_url() - BEIDE Pfade (Stream Preview + Channel):
cooldown_skip_profiles = set()
if ConfigHelper.stream_cooldown_enabled():
    redis_client = RedisClient.get_client()
    
    # Scan für Cooldown-Keys (channel-specific)
    cooldown_pattern = f"live:channel:{channel_id}:stream:{stream.id}:profile:*"
    for key in redis_client.scan_iter(match=cooldown_pattern):
        parts = key.split(':')
        if len(parts) >= 7:
            profile_id = int(parts[6])
            ttl = redis_client.ttl(key)
            if ttl > 0:
                mins = int(ttl // 60)
                secs = int(ttl % 60)
                logger.info(f"[COOLDOWN] Skipping profile {profile_id} - blocked for {mins}m {secs}s")
                cooldown_skip_profiles.add(profile_id)

# Bei Profile-Auswahl: Skip cooled profiles!
if profile_id in cooldown_skip_profiles:
    logger.info(f"[COOLDOWN] Default profile {profile_id} on cooldown, looking for alternative...")
    # Try other profiles that are NOT cooled
```

**Effekt:** 
- ✅ Cooldown macht jetzt SINN (ohne diesen Check ist Cooldown nutzlos!)
- ✅ Logs zeigen: `[COOLDOWN] Skipping profile X - blocked for Ym Zs more`
- ✅ Automatische Auswahl von nicht-gecoolten Profiles

---

### 8️⃣ **max_stream_switches Default: 200** (statt 10)
**Problem:** v0.30.0 hatte Default 10 → zu wenig Versuche

**Lösung:**
```python
# In config_helper.py:
def max_stream_switches():
    settings = Config.get_proxy_settings()
    return settings.get("max_stream_switches", 200)  # War 10
```

**Effekt:** Mehr Failover-Versuche (wie v0.27.0), aber über Frontend konfigurierbar!

---

## 🔑 Wichtige Infos

### Cooldown-Check nur wenn aktiviert
```python
if ConfigHelper.stream_cooldown_enabled():  # ← Prüft Frontend-Setting!
    # ... Cooldown scanning ...
```
**Ja, der Check passiert nur wenn User im Frontend aktiviert hat!**

### LAST RESORT vs 60s Wait

| Feature | v0.30.0 Original | v0.30.0 mit Patch |
|---------|------------------|-------------------|
| **Alle Streams probiert** | Warte 60s | LAST RESORT |
| **Cooldowns** | Bleiben aktiv | Werden gelöscht |
| **User Experience** | Schwarzer Bildschirm 60s | Sofortiger Retry |
| **Retry-Logik** | Nach 60s mit selben Cooldowns | Sofort mit frischen Optionen |
| **Max Versuche** | 10 (war hardcoded) | 200 (konfigurierbar) |

### Channel-Specific Cooldown Keys (v0.30.0 Format)
```
v0.27.0: live:cooldown:stream:{stream_id}:profile:{profile_id}
         └─ Global für alle Channels

v0.30.0: live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown
         └─ Channel-specific (bessere Isolation)
```

**Patch verwendet v0.30.0 Format!**

---

## 📦 Dateien geändert

1. **apps/proxy/live_proxy/input/manager.py**
   - Zeilen 91-92: `tried_combinations_reset_time`
   - Zeilen 127-136: Load `current_profile_id` from Redis
   - Zeilen 514-519: Hourly reset
   - Zeilen 844-848: Cleanup on stop
   - Zeilen 1493-1508: Success-based reset (5 min)
   - Zeilen 2234-2285: **LAST RESORT System** (ersetzt 60s wait)

2. **apps/proxy/live_proxy/input/http_streamer.py**
   - Zeilen 129-134: Race condition fix

3. **apps/proxy/live_proxy/url_utils.py**
   - Zeilen 73-157: Stream Preview Cooldown-Check
   - Zeilen 178-213: Channel Cooldown-Check

4. **apps/proxy/live_proxy/config_helper.py**
   - Zeile 98: `max_stream_switches` default 200

---

## 🚀 Installation

```bash
# 1. Backup
docker-compose down
cp -r /path/to/dispatcharr /path/to/dispatcharr_backup

# 2. Apply Patch
cd /path/to/dispatcharr
patch -p1 < dispatcharr_v0.30.0_COMPLETE_FIX.patch

# 3. Rebuild & Restart
docker-compose build --no-cache
docker-compose up -d

# 4. Check Logs
docker-compose logs -f --tail=100
```

---

## ✅ Erwartete Log-Meldungen

### Bei Stream Start (wenn Cooldown aktiv):
```
[COOLDOWN] Skipping profile 123 for stream 456 - blocked for 14m 32s more
[COOLDOWN] Default profile 123 on cooldown, looking for non-cooled profile...
[COOLDOWN] Selected non-cooled profile 789 for stream 456
```

### Bei LAST RESORT:
```
[COOLDOWN] LAST RESORT: All 8 stream/profile combinations tried for channel abc123 - clearing cooldowns and retrying (rotation pass 1/200)
[COOLDOWN] LAST RESORT: Cleared 8 cooldown keys for channel abc123
```

### Bei Hourly Reset:
```
Hourly tried_combinations reset for channel abc123 - clearing 5 entries
```

### Bei Success-Based Reset:
```
Stream stable for 300s - clearing 3 tried combinations for channel abc123
```

---

## 🎯 Was ist jetzt besser als v0.30.0?

| Feature | v0.30.0 Original | v0.30.0 + Patch |
|---------|------------------|-----------------|
| Cooldown-Check bei Start | ❌ Fehlt | ✅ Implementiert |
| Failover wenn erschöpft | 60s warten | LAST RESORT (sofort) |
| tried_combinations Reset | ❌ Nie | ✅ 3x (hourly + success + stop) |
| max_stream_switches | 10 | 200 |
| current_profile_id laden | ❌ Fehlt | ✅ Aus Redis |
| HTTP race condition | ❌ Fehlt | ✅ Gefixt |

---

## 🔧 Konfigurierbar via Frontend

- `max_stream_switches`: Settings → Max Stream Switches (Default jetzt 200)
- `stream_cooldown_enabled`: Settings → Stream Cooldown (ON/OFF)
- `stream_cooldown_duration`: Settings → Cooldown Duration (Sekunden)
- `failover_rotation_cooldown`: Wird nicht mehr verwendet (LAST RESORT ist sofort)

---

## 📊 Unterschiede v0.27.0 vs v0.30.0 (nach Patch)

| Feature | v0.27.0 | v0.30.0 + Patch | Unterschied |
|---------|---------|-----------------|-------------|
| LAST RESORT | ✅ | ✅ | Gleich |
| Cooldown bei Start | ✅ | ✅ | Gleich |
| Hourly Reset | ✅ | ✅ | Gleich |
| Success Reset | ✅ | ✅ | Gleich |
| Cleanup on Stop | ✅ | ✅ | Gleich |
| Cooldown Keys | Global | Channel-specific | v0.30.0 besser! |
| Health Monitoring | Events | Booleans | v0.30.0 einfacher |
| Retry Logic | Counter | Time-window | v0.30.0 besser! |

**Fazit:** v0.30.0 mit Patch ist **besser** als v0.27.0! 🎉

---

## 📝 Notizen

1. **LAST RESORT wird nur bei aktiviertem Cooldown ausgeführt**
   - Wenn Cooldown OFF → kein Redis SCAN/DELETE
   - Aber `tried_combinations.clear()` passiert trotzdem

2. **Channel-Specific Cooldown-Keys bleiben**
   - Format: `live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown`
   - Bessere Isolation als v0.27.0 global keys

3. **Max 200 Rotation Passes**
   - Jeder Pass löscht alle Cooldowns → neue Chance
   - Nach Pass 200 → Channel stoppt (keine Endlosschleife)

4. **Frontend-Konfiguration**
   - Alle wichtigen Parameter sind via WebUI änderbar
   - DB-backed → sofort wirksam ohne Code-Änderung

---

## 🐛 Bekannte Limitierungen

1. **Redis Scan Performance**
   - Bei vielen Streams kann LAST RESORT 1-2s dauern
   - Sollte aber selten vorkommen (nur wenn ALLE Optionen erschöpft)

2. **Channel-Specific Keys**
   - Wenn selber Stream in mehreren Channels → separate Cooldowns
   - Gewollt für bessere Isolation

---

## ✅ Getestet

- [ ] Docker Build erfolgreich
- [ ] Channel Start mit Cooldown-Check
- [ ] LAST RESORT Trigger bei erschöpften Streams
- [ ] Hourly Reset nach 1h
- [ ] Success Reset nach 5min stabiler Verbindung
- [ ] Cleanup on Stop
- [ ] max_stream_switches via Frontend änderbar
- [ ] Logs zeigen `[COOLDOWN]` Meldungen

---

**Created:** 2026-06-18  
**Version:** v0.30.0 COMPLETE FIX  
**Patch File:** `dispatcharr_v0.30.0_COMPLETE_FIX.patch`
