# Probleme Analyse v0.30.0

## 1. ❌ M3U Account HTTP Proxy Felder verschwunden (UI Problem)

### Status: **Backend OK, Frontend/Admin Problem**

**Backend (Datenbank):**
✅ `M3UAccount.proxy` Feld existiert (CharField, max_length=255)
✅ `M3UAccount.proxy_for_api` Feld existiert (BooleanField)
✅ `get_proxy_for_api()` Methode implementiert
✅ `get_proxy_for_streaming()` Methode implementiert

**Problem:**
❌ Django Admin zeigt Proxy-Felder NICHT in der UI!
❌ `apps/m3u/admin.py` hat keine `fieldsets` oder `fields` Definition
❌ Proxy-Felder fehlen in `list_display`

**Logs zeigen Proxy funktioniert:**
```
2026-08-31 13:40:00,025 INFO live_proxy.manager Using proxy http://192.168.178.135:18888 for HTTP streaming
2026-08-31 13:40:00,026 INFO live_proxy.http_streamer HTTP reader using proxy: http://192.168.178.135:18888
```

**Fix:** Django Admin muss erweitert werden um Proxy-Felder anzuzeigen

---

## 2. 🐛 http_streamer.py NoneType Race Condition (Shutdown Error)

### Status: **Non-blocking, aber nervend**

**Error Pattern:**
```
ERROR live_proxy.http_streamer HTTP reader unexpected error: 'NoneType' object has no attribute 'read'
File "/app/apps/proxy/live_proxy/input/http_streamer.py", line 93, in read_stream
    for chunk in self.response.iter_content(chunk_size=self.chunk_size):
```

**Root Cause:**
- `stop()` ruft `self.response.close()` auf → setzt intern `_fp = None`
- Gleichzeitig läuft noch `for chunk in self.response.iter_content()`
- Bei nächstem `chunk = self._handle_chunk()` → `self._fp.read(cursize)` → NoneType Error

**Race Condition:**
```python
# Thread 1: read_stream()
for chunk in self.response.iter_content():  # Line 93
    # ... reading chunks ...

# Thread 2: stop()
self.response.close()  # Sets _fp = None

# Thread 1 continues:
chunk = self._handle_chunk()  # Tries to read from _fp → None!
```

**Impact:**
- ⚠️ Passiert NUR beim Channel-Shutdown
- ✅ Stream selbst funktioniert perfekt (118s stable streaming)
- ✅ Failover funktioniert
- ❌ Ugly error messages in logs

**Fix:** Add null check before response operations

---

## 3. ✅ Stream Cooldown - FUNKTIONIERT!

**Evidence from logs:**
```
2026-08-31 13:22:09,269 INFO live_proxy.manager Set 600s cooldown for stream 1187282 with profile 582
2026-08-31 13:22:09,352 INFO live_proxy.url_utils Found 4 untried streams  # 582 gefiltert!
```

**✅ Cooldown System arbeitet korrekt:**
- (stream_id, profile_id) Kombination wird gecooled
- Cooldown Zeit: 600 Sekunden (10 Minuten) default
- Gefilterte Profiles werden nicht nochmal versucht

---

## 4. ❓ Failover bei scheduled EPG Aufnahmen?

**Zu prüfen:** Ob `schedule_recording()` oder `RecordingTask` die gleiche Failover-Logik verwendet.

**Vermutung:** ✅ Sollte funktionieren, da beide durch `StreamManager` laufen

**Test benötigt:**
1. EPG Aufnahme erstellen
2. Source Stream fail lassen
3. Prüfen ob Failover zum nächsten Profile triggert
4. Logs analysieren für Failover-Events während Recording

---

## 5. ⚠️ v0.27.0 vs v0.30.0 Unterschiede

### ✅ Was IST implementiert:
1. ✅ `tried_combinations` mit (stream_id, profile_id) tuples
2. ✅ Direct DB queries (kein `get_stream_info_for_switch()`)
3. ✅ `get_user_agent_string()` statt `.get_user_agent().user_agent`
4. ✅ Stream Cooldown System
5. ✅ Profile Failover

### ❌ Was FEHLT (v0.27.0 hat es):

#### A) Automatic tried_combinations Reset

**v0.27.0 hat 3 Reset-Mechanismen:**

1. **Hourly Reset:**
```python
# Init
self.tried_combinations_reset_time = time.time() + 3600

# Im run() loop
if time.time() > self.tried_combinations_reset_time:
    logger.info(f"Hourly tried_combinations reset - clearing {len(self.tried_combinations)} entries")
    self.tried_combinations.clear()
    self.tried_combinations_reset_time = time.time() + 3600
```

2. **Success-based Reset (5 min stable):**
```python
if not stable_streaming_reset_done and len(self.tried_combinations) > 0:
    connection_duration = self.last_data_time - self.connection_start_time
    if connection_duration > 300:  # 5 minutes
        logger.info(f"Stream stable for {connection_duration:.0f}s - clearing tried combinations")
        self.tried_combinations.clear()
        stable_streaming_reset_done = True
```

3. **Cleanup on Stop:**
```python
if hasattr(self, 'tried_combinations') and len(self.tried_combinations) > 0:
    logger.info(f"Clearing {len(self.tried_combinations)} tried combinations on channel stop")
    self.tried_combinations.clear()
```

**v0.30.0 hat nur:**
- Reset in `_note_stable_connection()` (partial)
- Reset in `reset_failover_rotation_state()`
- ❌ KEIN hourly automatic reset
- ❌ KEIN 5-minute success reset
- ❌ KEIN cleanup on stop

**Problem:** `tried_combinations` wird nie automatisch geleert → nach allen Profiles durchprobiert keine weiteren Versuche mehr möglich!

#### B) current_profile_id Redis Persistence

**v0.27.0:**
```python
# Load from Redis on manager creation
profile_id_bytes = redis_client.hget(metadata_key, ChannelMetadataField.M3U_PROFILE)
if profile_id_bytes:
    self.current_profile_id = int(profile_id_bytes.decode('utf-8'))
    logger.info(f"Loaded profile ID {self.current_profile_id} from Redis")
```

**v0.30.0:**
```python
# Nur initialisiert mit None
self.current_profile_id = None
```

**Problem:** Bei Worker Restart/Crash geht aktuelle Profile-Info verloren!

---

## 6. ⚠️ EPG Source 27 Warning (unrelated)

```
WARNING apps.epg.tasks [build_programme_index] File not found for source 27: /app/media/cached_epg/27.xml
```

**Assessment:** 
- ❌ Unrelated zu Failover
- Wahrscheinlich gelöschte/deaktivierte EPG Source
- Kann ignoriert werden oder EPG Source 27 löschen

---

## Zusammenfassung

| Problem | Status | Impact | Fix Priority |
|---------|--------|--------|--------------|
| M3U Proxy UI fehlt | ❌ Backend OK, Admin broken | LOW (Backend funktioniert) | MEDIUM |
| http_streamer NoneType | 🐛 Race condition | LOW (non-blocking) | LOW |
| Stream Cooldown | ✅ Funktioniert | - | - |
| EPG Recording Failover | ❓ Zu testen | UNKNOWN | MEDIUM |
| tried_combinations Reset fehlt | ❌ Kritisch | HIGH (nach Reset keine Failover mehr!) | **HIGH** |
| current_profile_id Redis | ❌ Fehlt | MEDIUM (Info verloren bei Crash) | MEDIUM |
| EPG Source 27 | ⚠️ Unrelated | LOW | LOW |

---

## Nächste Schritte

### HIGH Priority:
1. ✅ **Implement tried_combinations automatic resets** (hourly + 5-min stable + cleanup)
2. ❓ **Test EPG recording failover**

### MEDIUM Priority:
3. **Load current_profile_id from Redis** on manager init
4. **Fix Django Admin** to show proxy fields

### LOW Priority:
5. **Fix http_streamer shutdown race condition**
6. **Clean up EPG Source 27** warning
