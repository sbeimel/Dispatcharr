# Unterschiede v0.27.0 vs v0.30.0

## ✅ Was IST implementiert (v0.30.0 = v0.27.0)
1. ✅ `tried_combinations` Tracking mit (stream_id, profile_id) Tupeln
2. ✅ Direktes DB-Query für Stream-Info (kein `get_stream_info_for_switch()`)
3. ✅ `get_user_agent_string()` statt `.get_user_agent().user_agent`
4. ✅ Stream Cooldown System (600s default)
5. ✅ Profile Failover funktioniert

## ❌ Was FEHLT in v0.30.0 (aber in v0.27.0 vorhanden)

### 1. Automatisches Reset von `tried_combinations`

**v0.27.0 hat:**
```python
# Zeile ~91-94: Initialisierung
self.tried_combinations = set()
self.tried_combinations_reset_time = time.time() + 3600  # Reset every hour

# Zeile ~XXX: Hourly reset im run() loop
if time.time() > self.tried_combinations_reset_time and len(self.tried_combinations) > 0:
    logger.info(f"Hourly tried_combinations reset for channel {self.channel_id} - clearing {len(self.tried_combinations)} entries")
    self.tried_combinations.clear()
    self.tried_combinations_reset_time = time.time() + 3600

# Zeile ~XXX: Success-based reset (nach 5 Min stabiler Stream)
if not stable_streaming_reset_done and len(self.tried_combinations) > 0:
    connection_duration = self.last_data_time - getattr(self, 'connection_start_time', self.last_data_time)
    if connection_duration > 300:  # 5 minutes
        logger.info(f"Stream stable for {connection_duration:.0f}s - clearing {len(self.tried_combinations)} tried combinations")
        self.tried_combinations.clear()
        stable_streaming_reset_done = True

# Zeile ~XXX: Cleanup on channel stop
if hasattr(self, 'tried_combinations') and len(self.tried_combinations) > 0:
    logger.info(f"Clearing {len(self.tried_combinations)} tried combinations on channel stop")
    self.tried_combinations.clear()
```

**v0.30.0 hat NUR:**
- Reset in `_note_stable_connection()` (wird aber nur bei bestimmten Events aufgerufen)
- Reset in `reset_failover_rotation_state()`
- **KEIN hourly automatic reset!**
- **KEIN success-based 5-minute reset!**
- **KEIN cleanup on stop!**

### 2. current_profile_id wird aus Redis geladen

**v0.27.0 hat:**
```python
# Zeile ~XXX: Load profile_id from Redis on manager creation
profile_id_bytes = redis_client.hget(metadata_key, ChannelMetadataField.M3U_PROFILE)
if profile_id_bytes:
    self.current_profile_id = int(profile_id_bytes.decode('utf-8') if isinstance(profile_id_bytes, bytes) else profile_id_bytes)
    logger.info(f"Loaded profile ID {self.current_profile_id} from Redis for channel {buffer.channel_id}")
else:
    logger.warning(f"No profile ID found in Redis for channel {buffer.channel_id}")
```

**v0.30.0:**
- `current_profile_id` wird nur mit `None` initialisiert
- Wird NICHT aus Redis geladen bei Manager-Erstellung
- **Problem:** Bei Reconnects nach Crash geht Info verloren!

## 🔍 Fehlende Features die du gefragt hast

### M3U Account HTTP Proxy Settings verschwunden?
Das ist ein **separates Problem** - nicht related zu Failover. Lass mich prüfen:
