# Dispatcharr v0.20.1 Enhancements - Complete Patch

**Version:** v1.5.0  
**Datum:** 2026-03-12  
**Features:** Alle v0.19.0 Features + Bugfixes + Docker Fix

---

## ÜBERSICHT

Dieser Patch integriert alle Features von v0.19.0 in v0.20.1:
1. Profile Failover System (343 Kombinationen)
2. Universal HTTP Proxy Support
3. Basic Authentication
4. Extended Timeout Configuration (10 Settings)
5. Ghost-Client Auto-Cleanup (bereits vorhanden)
6. Migration für Proxy Feld
7. Alle Frontend-Änderungen
8. Docker drf-spectacular Fix

**Zusätzlich:** 10 Bugfixes (5 in url_utils.py + 2 in server.py + 1 in api_views.py + 1 in views.py + 1 in models.py + 1 in stream_generator.py)

---

## GEÄNDERTE DATEIEN (18)

### Backend (12 Dateien)

1. `apps/proxy/config.py` - ✅ IDENTISCH mit v0.19.0
2. `apps/m3u/models.py` - ✅ IDENTISCH mit v0.19.0
3. `core/models.py` - ✅ IDENTISCH mit v0.19.0
4. `apps/proxy/ts_proxy/http_streamer.py` - ✅ IDENTISCH mit v0.19.0
5. `apps/proxy/ts_proxy/config_helper.py` - ✅ IDENTISCH mit v0.19.0
6. `apps/output/views.py` - ✅ IDENTISCH mit v0.19.0
7. `apps/proxy/ts_proxy/stream_manager.py` - ✅ IDENTISCH mit v0.19.0
8. `apps/proxy/ts_proxy/url_utils.py` - ✅ MODIFIZIERT (Bugfixes #1-4 + #8)
9. `apps/proxy/ts_proxy/server.py` - ✅ MODIFIZIERT (Bugfix #5 + #10)
10. `apps/channels/api_views.py` - ✅ MODIFIZIERT (Bugfix #6)
11. `apps/proxy/ts_proxy/views.py` - ✅ MODIFIZIERT (Bugfix #7)
12. `apps/channels/models.py` - ✅ MODIFIZIERT (Bugfix #7 TTL)
13. `apps/proxy/ts_proxy/stream_generator.py` - ✅ MODIFIZIERT (Bugfix #9)

### Frontend (4 Dateien)

10. `frontend/src/constants.js` - ✅ IDENTISCH mit v0.19.0
11. `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js` - ✅ IDENTISCH mit v0.19.0
12. `frontend/src/components/forms/settings/ProxySettingsForm.jsx` - ✅ IDENTISCH mit v0.19.0
13. `frontend/src/components/forms/M3U.jsx` - ✅ IDENTISCH mit v0.19.0

### Migration (1 Datei)

14. `apps/m3u/migrations/0019_add_proxy_field.py` - ✅ NEU

### Docker (1 Datei)

15. `docker/DispatcharrBase` - ✅ MODIFIZIERT (drf-spectacular Fix)

---

## DETAILLIERTE ÄNDERUNGEN

### 1. apps/proxy/config.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
- Alle 10 Settings in `get_proxy_settings()`
- Alle Getter-Methoden
- MAX_RETRIES = 2
- MAX_STREAM_SWITCHES = 200

---

### 2. apps/m3u/models.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
```python
proxy = models.CharField(
    max_length=500,
    blank=True,
    null=True,
    help_text="HTTP Proxy URL (e.g., http://proxy:port)"
)
```

---

### 3. core/models.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
```python
def build_command(self, stream_url, user_agent, proxy=None):
    # ...
    if proxy and self.command == "ffmpeg" and "-http_proxy" not in self.parameters:
        cmd.insert(i_index, proxy)
        cmd.insert(i_index, "-http_proxy")
```

---

### 4. apps/proxy/ts_proxy/http_streamer.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
```python
def __init__(self, url, user_agent=None, chunk_size=8192, proxy=None):
    self.proxy = proxy
    # ...
    if self.proxy:
        self.session.proxies = {
            'http': self.proxy,
            'https': self.proxy
        }
```

---

### 5. apps/proxy/ts_proxy/config_helper.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
- Alle Methoden nutzen `BaseConfig.get_*()` Getter

---

### 6. apps/output/views.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
```python
def get_basic_auth_user(request):
    # ... Basic Auth Extraktion

def require_basic_auth(request):
    # ... 401 Response

# M3U Endpoint
if not user:
    user = get_basic_auth_user(request)
    if not user:
        return require_basic_auth(request)

# EPG Endpoint
if not user:
    user = get_basic_auth_user(request)
    if not user:
        return require_basic_auth(request)
```

---

### 7. apps/proxy/ts_proxy/stream_manager.py

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Datei ist bereits identisch mit v0.19.0

**Enthält:**
- `current_profile_id` Tracking
- `tried_combinations` Set
- Profile ID aus Redis laden
- Proxy Support in `_establish_transcode_connection()`
- Proxy Support in `_establish_http_connection()`
- Profile ID Tracking in `update_url()`
- Profile Failover in `_try_next_stream()`

---

### 8. apps/proxy/ts_proxy/url_utils.py

**Status:** ⚠️ BUGFIXES ERFORDERLICH

#### Bugfix 1: `get_alternate_streams()` erweitern

**VORHER (FALSCH):**
```python
def get_alternate_streams(channel_id: str, current_stream_id: Optional[int] = None) -> List[dict]:
    # ...
    selected_profile = None
    for profile in profiles:
        if profile.max_streams == 0 or effective_connections < profile.max_streams:
            selected_profile = profile
            break  # ❌ Nur ein Profile!
    
    if selected_profile:
        alternate_streams.append({
            'stream_id': stream.id,
            'profile_id': selected_profile.id,
            'name': stream.name
        })
```

**NACHHER (RICHTIG):**
```python
def get_alternate_streams(
    channel_id: str, 
    current_stream_id: Optional[int] = None,
    current_profile_id: Optional[int] = None  # ✅ NEU
) -> List[dict]:
    # ...
    for profile in profiles:
        # Skip current stream+profile combination
        if current_stream_id and stream.id == current_stream_id and current_profile_id and profile.id == current_profile_id:
            continue
        
        if profile.max_streams == 0 or effective_connections < profile.max_streams:
            alternate_streams.append({
                'stream_id': stream.id,
                'profile_id': profile.id,
                'name': stream.name
            })
            # ✅ Kein break - ALLE Profile!
```

#### Bugfix 2: `get_stream_info_for_profile()` hinzufügen

**NEU (FEHLTE KOMPLETT):**
```python
def get_stream_info_for_profile(
    channel_id: str, 
    stream_id: int, 
    m3u_profile_id: int
) -> dict:
    """
    Build URL/User-Agent/Transcode for a fixed combination of Stream + M3U profile.
    Return schema compatible with get_stream_info_for_switch(...).
    """
    try:
        channel = get_stream_object(channel_id)
        if isinstance(channel, Stream):
            logger.error(f"get_stream_info_for_profile: {channel_id} refers to a Stream, not a Channel")
            return {"error": "Invalid channel ID"}
        
        stream = get_object_or_404(Stream, pk=stream_id)
        m3u_profile = get_object_or_404(M3UAccountProfile, pk=m3u_profile_id)
        
        m3u_account = m3u_profile.m3u_account
        user_agent = m3u_account.get_user_agent().user_agent
        
        # Generate URL using the specific profile's transformation
        input_url = stream.url
        stream_url = transform_url(input_url, m3u_profile.search_pattern, m3u_profile.replace_pattern)
        
        # Get transcode info from the channel's stream profile
        stream_profile = channel.get_stream_profile()
        transcode = not (stream_profile.is_proxy() or stream_profile is None)
        profile_value = stream_profile.id
        
        return {
            'url': stream_url,
            'user_agent': user_agent,
            'transcode': transcode,
            'stream_profile': profile_value,
            'stream_id': stream_id,
            'm3u_profile_id': m3u_profile_id
        }
    except Exception as e:
        logger.error(f"Error in get_stream_info_for_profile: {e}", exc_info=True)
        return {'error': f'Error: {str(e)}'}
```

#### Bugfix 8: Connection Leak in Preview (NEU!)

**Problem:** Wenn `get_stream()` in Preview fehlschlägt, wird der Profile Connection Counter nie dekrementiert

**VORHER (BUGGY):**
```python
# Handle channel preview (existing logic)
channel = channel_or_stream

# Get stream and profile for this channel
stream_id, profile_id, error_reason = channel.get_stream()

if not stream_id or not profile_id:
    # ❌ Counter bleibt erhöht!
    logger.error(f"No stream available for channel {channel_id}: {error_reason}")
    return None, None, False, None
```

**NACHHER (GEFIXT):**
```python
# Handle channel preview (existing logic)
channel = channel_or_stream

# Get stream and profile for this channel
stream_id, profile_id, error_reason = channel.get_stream()

if not stream_id or not profile_id:
    # BUGFIX #8: Release stream if get_stream() failed to prevent connection leak
    try:
        channel.release_stream()
        logger.debug(f"Released stream after failed get_stream() in url_utils")
    except Exception as e:
        logger.debug(f"Could not release stream in url_utils: {e}")
    logger.error(f"No stream available for channel {channel_id}: {error_reason}")
    return None, None, False, None
```

**Auswirkung:**
- ✅ Preview gibt Counter frei wenn fehlgeschlagen
- ✅ Verhindert Connection Leak bei Preview
- ✅ Funktioniert zusammen mit Bugfix #7 (views.py)

---

### 10. apps/channels/api_views.py

**Status:** ⚠️ BUGFIX ERFORDERLICH (Original Dispatcharr Bug)

#### Bugfix 6: Logo Fetch Timeout zu kurz

**Problem:** Logo-Downloads von langsamen Servern (z.B. `logos.jesmann.com`) schlagen mit Timeout fehl

**VORHER (ZU KURZ - ORIGINAL CODE):**
```python
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(3, 5),  # ❌ 3s connect, 5s read - zu kurz!
    headers={'User-Agent': user_agent}
)
```

**Logs zeigen:**
```
WARNING apps.channels.api_views Timeout fetching logo from https://logos.jesmann.com/KABEL1H.png
WARNING django.request Not Found: /api/channels/logos/5185/cache/
GET 404 /api/channels/logos/5185/cache/ 3107ms
```

**Problem:**
- Requests dauern ~3000-3100ms (3+ Sekunden)
- Connect Timeout ist nur 3 Sekunden
- Server antwortet zu langsam → Timeout → 404 Error

**NACHHER (GEFIXT):**
```python
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(10, 15),  # ✅ 10s connect, 15s read - ausreichend für langsame Server
    headers={'User-Agent': user_agent}
)
```

**Auswirkung:**
- **Vorher:** Logos von langsamen Servern werden nicht geladen (404)
- **Nachher:** Logos werden korrekt geladen, auch von langsamen Servern

**Hinweis:** Dies ist ein Bug im **Original Dispatcharr v0.20.1**, nicht durch unsere Enhancements verursacht.

---

---

### 9. apps/proxy/ts_proxy/server.py

**Status:** ⚠️ BUGFIX (Original Dispatcharr Bug)

**Bugfix 5:** Exception Handling in `_clean_redis_keys()` verbessert
- Bare `except:` durch spezifische Exception-Behandlung ersetzt
- Redis Keys werden jetzt korrekt gelöscht, auch wenn Channel/Stream nicht in DB existiert
- Verhindert endlose Cleanup-Zyklen

---

### 10. apps/channels/api_views.py

**Status:** ⚠️ BUGFIX (Original Dispatcharr Bug)

**Bugfix 6:** Logo Fetch Timeout erhöht

**Änderung:**
```python
# VORHER
timeout=(3, 5)  # 3s connect, 5s read

# NACHHER
timeout=(10, 15)  # 10s connect, 15s read
```

**Grund:** Langsame Logo-Server (z.B. logos.jesmann.com) brauchen länger als 3-5 Sekunden

---

### 11. apps/proxy/ts_proxy/views.py

**Status:** ⚠️ BUGFIX #7 (Original Dispatcharr Bug seit v0.17)

**Problem:** Profile Connection Leak im Retry-Loop

**Symptome:**
- "No profiles available with connection capacity" Fehler
- Profile erscheinen "voll" obwohl keine Streams laufen
- Counter in Redis steigt bei jedem Retry-Versuch
- Tritt auf bei Accounts mit niedrigen max_streams Limits (1-2)

**Root Cause:**
```python
# VORHER (BUGGY):
while retry:
    stream_url = generate_stream_url(channel_id)  # ❌ Ruft get_stream() auf
    # get_stream() inkrementiert Counter bei JEDEM Versuch!
    # Counter: 0 → 1 → 2 → 3 → ... → 14
    if stream_url:
        break
# Wenn alle Versuche fehlschlagen: Counter bleibt erhöht! ❌
```

**Lösung:**
```python
# NACHHER (GEFIXT):
while retry:
    stream_url = generate_stream_url(channel_id)  # Inkrementiert Counter
    
    if stream_url:
        break  # Erfolg! Counter bleibt erhöht (wird bei Stream-Ende freigegeben)
    
    # FEHLER! Gebe Counter sofort frei
    channel.release_stream()  # ✅ Dekrementiert Counter
    gevent.sleep(retry_interval)

# Wenn alle Versuche fehlschlagen:
channel.release_stream()  # ✅ Finaler Cleanup
```

**Auswirkung:**
- **Vorher:** 14 Retry-Versuche → Counter = 14 → Profile "voll" → Fehler
- **Nachher:** 14 Retry-Versuche → Counter bleibt bei 1 → wird freigegeben → Profile verfügbar

**Hinweis:** Dies ist ein Bug im **Original Dispatcharr seit v0.17**, nicht durch unsere Enhancements verursacht. Das Problem wurde nur durch Profile Failover sichtbar, weil jetzt mehr Profile mit niedrigeren Limits verwendet werden.

---

### 12. apps/channels/models.py

**Status:** ⚠️ BUGFIX #7 TTL (Sicherheitsnetz)

**Problem:** Wenn `release_stream()` nie aufgerufen wird (Crash, Exception), bleibt Counter permanent erhöht

**Lösung:** Redis Keys mit TTL (Time-To-Live) versehen

**Änderung:**
```python
# VORHER:
if profile.max_streams > 0:
    redis_client.incr(profile_connections_key)

# NACHHER:
if profile.max_streams > 0:
    redis_client.incr(profile_connections_key)
    # Set TTL to 1 hour (3600 seconds) as safety net
    redis_client.expire(profile_connections_key, 3600)  # ✅ TTL hinzugefügt
```

**Auswirkung:**
- **Vorher:** Counter bleibt permanent erhöht wenn release_stream() nie aufgerufen wird
- **Nachher:** Counter läuft nach 1 Stunde automatisch ab (Sicherheitsnetz)

**Vorteil:** Selbst bei Server-Crashes oder Exceptions wird der Counter nach 1 Stunde automatisch zurückgesetzt.

---

### 13. apps/proxy/ts_proxy/url_utils.py (Bugfix #8)

**Status:** ⚠️ BUGFIX #8 (Preview Connection Leak)

**Problem:** Preview-Pfad gibt Profile-Connection nicht frei wenn get_stream() fehlschlägt

**Symptome:**
- Preview-Requests belegen Connections permanent
- Counter steigt auch wenn Preview fehlschlägt
- "No profiles available" nach mehreren fehlgeschlagenen Previews

**Root Cause:**
```python
# VORHER (BUGGY):
if isinstance(channel_or_stream, Stream):
    # Preview-Pfad
    stream_id, profile_id = get_stream(...)  # ❌ Inkrementiert Counter
    
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

**Auswirkung:**
- **Vorher:** Preview fehlschlägt → Counter bleibt erhöht → Profile "voll"
- **Nachher:** Preview fehlschlägt → Counter wird freigegeben → Profile verfügbar

**Zeile:** ~1050 in url_utils.py

---

### 14. apps/proxy/ts_proxy/stream_generator.py (Bugfix #9)

**Status:** ⚠️ BUGFIX #9 (Last Client Release via Redis) - KRITISCH!

**Problem:** Letzter Client gibt Profile-Connection nicht frei (DB-Lookup schlägt fehl)

**Symptome:**
- Nach normalem Stream-Stop: "No profiles available"
- Counter bleibt bei 1 obwohl Stream gestoppt wurde
- Logs zeigen KEINE Fehler (weil DB-Lookup fehlschlägt ohne Exception)

**Root Cause:**
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
    # BUGFIX #9: Release stream counter via Redis when last client disconnects
    stream_released = False
    if self.redis_client:
        try:
            metadata_key = RedisKeys.channel_metadata(self.channel_id)
            metadata = proxy_server.redis_client.hgetall(metadata_key)
            
            if metadata:
                stream_id_bytes = metadata.get(b'stream_id')
                profile_id_bytes = metadata.get(b'profile_id')
                
                if stream_id_bytes and profile_id_bytes:
                    stream_id = int(stream_id_bytes.decode('utf-8'))
                    profile_id = int(profile_id_bytes.decode('utf-8'))
                    
                    # Check if we're the last client
                    if self.channel_id in proxy_server.client_managers:
                        client_count = proxy_server.client_managers[self.channel_id].get_total_client_count()
                        
                        # ✅ Only release if NO clients left (client_count == 0)
                        if client_count == 0:
                            from core.utils import RedisClient
                            redis_client = RedisClient.get_client()
                            
                            # ✅ Release directly via Redis - no DB needed!
                            redis_client.delete(f"channel_stream:{self.channel_id}")
                            redis_client.delete(f"stream_profile:{stream_id}")
                            
                            # ✅ Decrement profile counter
                            profile_connections_key = f"profile_connections:{profile_id}"
                            current_count = int(redis_client.get(profile_connections_key) or 0)
                            if current_count > 0:
                                redis_client.decr(profile_connections_key)
                                logger.info(f"Released stream {stream_id} profile {profile_id} (counter: {current_count} → {current_count-1})")
                                stream_released = True
        except Exception as e:
            logger.error(f"Error releasing stream via Redis: {e}")
```

**Auswirkung:**
- **Vorher:** Stream stoppt → Counter bleibt bei 1 → Nächster Stream: "No profiles available"
- **Nachher:** Stream stoppt → Counter wird auf 0 gesetzt → Nächster Stream funktioniert

**Wichtig:** 
- Funktioniert für UUIDs UND Stream-Hashes
- Funktioniert auch wenn Channel aus DB gelöscht wurde
- Verwendet nur Redis (kein DB-Lookup)
- Nur wenn client_count == 0 (nicht <= 1, weil bei 2 Clients einer noch aktiv ist)

**Zeile:** ~444 in stream_generator.py

---

### 15. apps/proxy/ts_proxy/server.py (Bugfix #10)

**Status:** ⚠️ BUGFIX #10 (Server Release via Redis) - KRITISCH!

**Problem:** Server Cleanup gibt Profile-Connection nicht frei (UUID-Validierung schlägt fehl)

**Symptome:**
- Logs zeigen: `Error releasing stream: "..." is not a valid UUID`
- Counter bleibt erhöht nach Channel-Stop
- "No profiles available" nach Server Cleanup

**Root Cause:**
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
    """Clean up all Redis keys for a channel more efficiently"""
    # BUGFIX #10: Release stream counter directly via Redis (no DB lookup)
    # This works for both UUIDs and stream hashes
    if self.redis_client:
        try:
            metadata_key = RedisKeys.channel_metadata(channel_id)
            metadata = self.redis_client.hgetall(metadata_key)
            
            if metadata:
                # Get stream_id and profile_id from Redis metadata
                stream_id_bytes = metadata.get(b'stream_id')
                profile_id_bytes = metadata.get(b'profile_id')
                
                if stream_id_bytes and profile_id_bytes:
                    try:
                        stream_id = int(stream_id_bytes.decode('utf-8'))
                        profile_id = int(profile_id_bytes.decode('utf-8'))
                        
                        # ✅ Release directly via Redis - no DB needed!
                        self.redis_client.delete(f"channel_stream:{channel_id}")
                        self.redis_client.delete(f"stream_profile:{stream_id}")
                        
                        # ✅ Decrement profile counter
                        profile_connections_key = f"profile_connections:{profile_id}"
                        current_count = int(self.redis_client.get(profile_connections_key) or 0)
                        if current_count > 0:
                            self.redis_client.decr(profile_connections_key)
                            logger.info(f"Released stream {stream_id} profile {profile_id} via Redis (counter: {current_count} → {current_count-1})")
                        else:
                            logger.debug(f"Counter already at 0 for profile {profile_id}")
                    except Exception as e:
                        logger.error(f"Error releasing stream via Redis: {e}")
                else:
                    logger.debug(f"No stream/profile metadata found in Redis for {channel_id}")
            else:
                logger.debug(f"No metadata found in Redis for {channel_id}")
        except Exception as e:
            logger.error(f"Error releasing stream for channel {channel_id}: {e}")
    
    # ... rest of Redis cleanup code ...
```

**Zusätzlich:** Zombie Channel Cleanup vereinfacht (Zeile ~790):
```python
# VORHER (BUGGY):
# Clean up Redis keys
self._clean_redis_keys(channel_id)

# Force release resources in the Channel model
try:
    channel = Channel.objects.get(uuid=channel_id)
    channel.release_stream()
except Exception as e:
    try:
        stream = Stream.objects.get(stream_hash=channel_id)
        stream.release_stream()
    except Exception as e:
        logger.error(f"Error releasing stream: {e}")

# NACHHER (GEFIXT):
# Clean up Redis keys (this now includes stream release via Redis)
self._clean_redis_keys(channel_id)
```

**Auswirkung:**
- **Vorher:** UUID-Fehler → Counter bleibt erhöht → "No profiles available"
- **Nachher:** Redis-basierte Freigabe → Counter wird korrekt dekrementiert → Profile verfügbar

**Wichtig:**
- Funktioniert für UUIDs UND Stream-Hashes
- Keine UUID-Validierung mehr (kein DB-Lookup)
- Konsistent mit Bugfix #9 (gleicher Redis-basierter Ansatz)
- Funktioniert auch wenn Channel aus DB gelöscht wurde

**Zeilen:** ~1338 (_clean_redis_keys) und ~790 (Zombie Cleanup) in server.py

---

### 16-19. Frontend-Dateien

**Status:** ✅ KEINE ÄNDERUNGEN ERFORDERLICH  
**Grund:** Dateien sind bereits identisch mit v0.19.0
**Enthält:**
- Alle 10 Settings in constants.js
- Alle Defaults in ProxySettingsFormUtils.js
- Alle Form-Felder in ProxySettingsForm.jsx
- Proxy-Feld in M3U.jsx

---

### 20. apps/m3u/migrations/0019_add_proxy_field.py

**Status:** ✅ NEU (Intelligente Migration)

**Besonderheit:** Diese Migration prüft, ob die `proxy` Spalte bereits existiert, bevor sie hinzugefügt wird.

**Funktionsweise:**
- Bei **frischer Installation**: Spalte wird angelegt
- Bei **Update**: Prüft ob Spalte existiert, überspringt wenn ja
- Verhindert `DuplicateColumn` Fehler bei Updates

```python
from django.db import migrations, models

def add_proxy_field_safe(apps, schema_editor):
    """Add proxy field only if it doesn't exist yet"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
              AND table_name = 'm3u_m3uaccount' 
              AND column_name = 'proxy'
        """)
        
        if not cursor.fetchone():
            # Column doesn't exist, add it
            cursor.execute("""
                ALTER TABLE m3u_m3uaccount 
                ADD COLUMN proxy varchar(500) NULL
            """)

class Migration(migrations.Migration):
    dependencies = [
        ('m3u', '0018_add_profile_custom_properties'),
    ]

    operations = [
        migrations.RunPython(add_proxy_field_safe, reverse_code=migrations.RunPython.noop),
    ]
```

---

### 21. docker/DispatcharrBase

**Status:** ✅ MODIFIZIERT (drf-spectacular Fix)

**Problem:** `ModuleNotFoundError: No module named 'drf_spectacular'` beim Start

**Lösung:** Explizite Installation von drf-spectacular nach uv sync

```dockerfile
# --- Create Python virtual environment and install dependencies ---
WORKDIR /tmp/build
COPY pyproject.toml /tmp/build/
COPY version.py /tmp/build/
COPY README.md /tmp/build/
RUN uv sync --python 3.13 --no-cache --no-install-project --no-dev && \
    uv pip install --python $UV_PROJECT_ENVIRONMENT/bin/python --no-cache drf-spectacular>=0.29.0 && \
    rm -rf /tmp/build
WORKDIR /
```

**Änderung:**
- Zeile hinzugefügt: `uv pip install --python $UV_PROJECT_ENVIRONMENT/bin/python --no-cache drf-spectacular>=0.29.0 && \`
- Stellt sicher, dass drf-spectacular beim Docker Build installiert wird

---

## INSTALLATION

### Automatisch (Empfohlen)

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

### Manuell

```bash
# 1. Dateien kopieren
cp -r Dispatcharr-0.20.1/* /path/to/dispatcharr/

# 2. Migration anwenden
cd /path/to/dispatcharr
python manage.py migrate

# 3. Frontend bauen
cd frontend
npm install
npm run build

# 4. Static Files sammeln
cd ..
python manage.py collectstatic --noinput

# 5. Docker Images neu bauen
docker build -f docker/DispatcharrBase -t dispatcharr:base .
docker build -f docker/Dockerfile --build-arg BASE_TAG=base -t dispatcharr:0.20.1 .

# 6. Server neu starten
docker-compose down
docker-compose up -d
```

---

## VERIFIKATION

### Test 1: Import-Test
```bash
python manage.py shell << EOF
from apps.proxy.ts_proxy.url_utils import get_stream_info_for_profile, get_alternate_streams
print("✅ Import erfolgreich")
EOF
```

### Test 2: Config-Test
```bash
python manage.py shell << EOF
from apps.proxy.config import BaseConfig
settings = BaseConfig.get_proxy_settings()
assert settings['max_retries'] == 2
assert settings['max_stream_switches'] == 200
print("✅ Config korrekt")
EOF
```

### Test 3: Model-Test
```bash
python manage.py shell << EOF
from apps.m3u.models import M3UAccount
assert hasattr(M3UAccount, 'proxy')
print("✅ Model korrekt")
EOF
```

---

## ROLLBACK

Falls Probleme auftreten:

```bash
# 1. Backup wiederherstellen
cp -r backup_YYYYMMDD_HHMMSS/* /path/to/dispatcharr/

# 2. Migration rückgängig machen
python manage.py migrate m3u 0018

# 3. Server neu starten
docker compose restart
```

---

## SUPPORT

Bei Problemen:
1. Logs prüfen: `docker logs dispatcharr`
2. Diagnostics ausführen: `python manage.py check`
3. Tests ausführen: `python manage.py test`

---

## BUGFIXES ZUSAMMENFASSUNG

### Bugfix 1-4: url_utils.py (Profile Failover)
- ✅ `get_alternate_streams()` gibt jetzt ALLE Profile zurück (nicht nur eines)
- ✅ `get_alternate_streams()` akzeptiert `current_profile_id` Parameter
- ✅ `get_stream_info_for_profile()` Funktion hinzugefügt (fehlte komplett)
- ✅ `_establish_transcode_connection()` Proxy-Parameter hinzugefügt

### Bugfix 5: server.py (Orphaned Cleanup)
- ✅ `_clean_redis_keys()` Exception Handling verbessert
- ✅ Redis Keys werden jetzt korrekt gelöscht, auch wenn Channel/Stream nicht in DB existiert
- ✅ Verhindert endlose Cleanup-Zyklen für gelöschte Channels
- ⚠️ **Original Dispatcharr Bug** - nicht durch unsere Enhancements verursacht

### Bugfix 6: api_views.py (Logo Timeout)
- ✅ Logo Fetch Timeout von (3, 5) auf (10, 15) erhöht
- ✅ Logos von langsamen Servern werden jetzt korrekt geladen
- ⚠️ **Original Dispatcharr Bug** - nicht durch unsere Enhancements verursacht

### Bugfix 7: views.py + models.py (Connection Leak) - KRITISCH!
- ✅ Retry-Loop gibt Profile-Connections nach jedem fehlgeschlagenen Versuch frei
- ✅ Verhindert dass Counter bei jedem Retry inkrementiert wird
- ✅ TTL (1 Stunde) als Sicherheitsnetz für vergessene Releases
- ✅ Behebt "No profiles available with connection capacity" Fehler
- ⚠️ **Original Dispatcharr Bug seit v0.17** - existierte vor unseren Enhancements
- ⚠️ **Wurde durch Profile Failover sichtbar** - mehr Profile mit niedrigeren Limits

### Bugfix 8: url_utils.py (Preview Connection Leak)
- ✅ Preview-Pfad gibt Profile-Connection frei wenn get_stream() fehlschlägt
- ✅ Verhindert Connection-Leak bei fehlgeschlagenen Preview-Requests
- ⚠️ **Original Dispatcharr Bug** - nicht durch unsere Enhancements verursacht

### Bugfix 9: stream_generator.py (Last Client Release) - KRITISCH!
- ✅ Letzter Client gibt Profile-Connection via Redis frei (kein DB-Lookup)
- ✅ Funktioniert auch wenn Channel aus DB gelöscht wurde
- ✅ Verwendet Metadata aus Redis (stream_id, profile_id)
- ✅ Behebt "No profiles available" nach normalem Stream-Stop
- ⚠️ **Original Dispatcharr Bug seit v0.17** - existierte vor unseren Enhancements

### Bugfix 10: server.py (Server Release via Redis) - KRITISCH!
- ✅ `_clean_redis_keys()` gibt Profile-Connection via Redis frei (kein DB-Lookup)
- ✅ Funktioniert für UUIDs UND Stream-Hashes (keine UUID-Validierung mehr)
- ✅ Zombie Channel Cleanup vereinfacht (nur noch Redis-basiert)
- ✅ Behebt UUID-Fehler: "is not a valid UUID" beim Stream-Stop
- ✅ Konsistent mit Bugfix #9 (gleicher Redis-basierter Ansatz)
- ⚠️ **Original Dispatcharr Bug seit v0.17** - existierte vor unseren Enhancements

**Alle Bugfixes sind kritisch für die korrekte Funktion des Systems!**

---

**Erstellt:** 2026-03-02  
**Aktualisiert:** 2026-03-12 (Bugfix 7-10 hinzugefügt - Connection Leak Fixes)  
**Version:** 1.5.0  
**Status:** PRODUKTIONSREIF
