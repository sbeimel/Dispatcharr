# 🔍 VERIFICATION CHECKLIST - Dispatcharr v0.20.1 Enhancements

**Datum:** 2026-03-02  
**Version:** v0.20.1 mit v0.19.0 Features

---

## 📋 BACKEND VERIFICATION

### 1. Config System (apps/proxy/config.py)

**Zu prüfen:**
```python
from apps.proxy.config import BaseConfig

settings = BaseConfig.get_proxy_settings()
print(settings)
```

**Erwartete Ausgabe:**
```python
{
    'buffering_timeout': 15,
    'buffering_speed': 1.0,
    'redis_chunk_ttl': 60,
    'channel_shutdown_delay': 0,
    'channel_init_grace_period': 5,
    'max_retries': 2,                    # NEU
    'url_switch_timeout': 20,            # NEU
    'max_stream_switches': 200,          # NEU
    'connection_timeout': 10,            # NEU
    'failover_grace_period': 20          # NEU
}
```

**Getter Methoden prüfen:**
```python
from apps.proxy.config import BaseConfig

print(f"max_retries: {BaseConfig.get_max_retries()}")
print(f"url_switch_timeout: {BaseConfig.get_url_switch_timeout()}")
print(f"max_stream_switches: {BaseConfig.get_max_stream_switches()}")
print(f"connection_timeout: {BaseConfig.get_connection_timeout()}")
print(f"failover_grace_period: {BaseConfig.get_failover_grace_period()}")
```

**Erwartete Werte:**
- max_retries: 2
- url_switch_timeout: 20
- max_stream_switches: 200
- connection_timeout: 10
- failover_grace_period: 20

---

### 2. M3U Account Proxy Field (apps/m3u/models.py)

**Zu prüfen:**
```python
from apps.m3u.models import M3UAccount

# Check if field exists
print(hasattr(M3UAccount, 'proxy'))  # Should be True

# Check field properties
field = M3UAccount._meta.get_field('proxy')
print(f"Field type: {field.__class__.__name__}")
print(f"Max length: {field.max_length}")
print(f"Blank: {field.blank}")
print(f"Null: {field.null}")
```

**Erwartete Ausgabe:**
```
True
Field type: CharField
Max length: 255
Blank: True
Null: True
```

---

### 3. StreamProfile build_command (core/models.py)

**Zu prüfen:**
```python
from core.models import StreamProfile

# Get FFmpeg profile
ffmpeg = StreamProfile.objects.get(name='ffmpeg', locked=True)

# Test without proxy
cmd1 = ffmpeg.build_command('http://example.com/stream', 'Mozilla/5.0')
print("Without proxy:", cmd1)

# Test with proxy
cmd2 = ffmpeg.build_command('http://example.com/stream', 'Mozilla/5.0', 'http://proxy:8080')
print("With proxy:", cmd2)

# Check if -http_proxy is in command
has_proxy = any('-http_proxy' in str(arg) for arg in cmd2)
print(f"Has -http_proxy: {has_proxy}")
```

**Erwartete Ausgabe:**
- Without proxy: Kein -http_proxy Parameter
- With proxy: -http_proxy http://proxy:8080 im Command
- Has -http_proxy: True

---

### 4. HTTPStreamReader Proxy Support (apps/proxy/ts_proxy/http_streamer.py)

**Zu prüfen:**
```python
from apps.proxy.ts_proxy.http_streamer import HTTPStreamReader

# Check __init__ signature
import inspect
sig = inspect.signature(HTTPStreamReader.__init__)
params = list(sig.parameters.keys())
print(f"Parameters: {params}")
print(f"Has proxy parameter: {'proxy' in params}")
```

**Erwartete Ausgabe:**
```
Parameters: ['self', 'url', 'user_agent', 'chunk_size', 'proxy']
Has proxy parameter: True
```

---

### 5. ConfigHelper Methods (apps/proxy/ts_proxy/config_helper.py)

**Zu prüfen:**
```python
from apps.proxy.ts_proxy.config_helper import ConfigHelper

print(f"max_retries: {ConfigHelper.max_retries()}")
print(f"url_switch_timeout: {ConfigHelper.url_switch_timeout()}")
print(f"max_stream_switches: {ConfigHelper.max_stream_switches()}")
print(f"connection_timeout: {ConfigHelper.connection_timeout()}")
print(f"failover_grace_period: {ConfigHelper.failover_grace_period()}")
```

**Erwartete Werte:**
- max_retries: 2
- url_switch_timeout: 20
- max_stream_switches: 200
- connection_timeout: 10
- failover_grace_period: 20

---

### 6. Basic Authentication (apps/output/views.py)

**Zu prüfen:**
```bash
# Test M3U endpoint without user parameter (should require Basic Auth)
curl -v http://localhost:8000/m3u/

# Expected: 401 Unauthorized with WWW-Authenticate header

# Test with Basic Auth
curl -v -u username:password http://localhost:8000/m3u/

# Expected: 200 OK with M3U content

# Test EPG endpoint without user parameter
curl -v http://localhost:8000/epg/

# Expected: 401 Unauthorized

# Test with Basic Auth
curl -v -u username:password http://localhost:8000/epg/

# Expected: 200 OK with EPG content
```

**Erwartete Ausgabe:**
- Ohne Auth: 401 Unauthorized
- Mit Auth: 200 OK
- WWW-Authenticate Header vorhanden

---

### 7. StreamManager Profile Tracking (apps/proxy/ts_proxy/stream_manager.py)

**Zu prüfen:**
```python
# Check if StreamManager has new attributes
from apps.proxy.ts_proxy.stream_manager import StreamManager
import inspect

# Get __init__ source
source = inspect.getsource(StreamManager.__init__)

# Check for new attributes
checks = {
    'current_profile_id': 'self.current_profile_id' in source,
    'tried_combinations': 'self.tried_combinations' in source,
    'profile_id_loading': 'm3u_profile' in source
}

for name, present in checks.items():
    print(f"{name}: {'✅' if present else '❌'}")
```

**Erwartete Ausgabe:**
```
current_profile_id: ✅
tried_combinations: ✅
profile_id_loading: ✅
```

---

### 8. URL Utils Functions (apps/proxy/ts_proxy/url_utils.py)

**Zu prüfen:**
```python
from apps.proxy.ts_proxy.url_utils import get_alternate_streams, get_stream_info_for_profile
import inspect

# Check get_alternate_streams signature
sig1 = inspect.signature(get_alternate_streams)
params1 = list(sig1.parameters.keys())
print(f"get_alternate_streams params: {params1}")
print(f"Has current_profile_id: {'current_profile_id' in params1}")

# Check if get_stream_info_for_profile exists
print(f"get_stream_info_for_profile exists: {callable(get_stream_info_for_profile)}")

# Check get_stream_info_for_profile signature
sig2 = inspect.signature(get_stream_info_for_profile)
params2 = list(sig2.parameters.keys())
print(f"get_stream_info_for_profile params: {params2}")
```

**Erwartete Ausgabe:**
```
get_alternate_streams params: ['channel_id', 'current_stream_id', 'current_profile_id']
Has current_profile_id: True
get_stream_info_for_profile exists: True
get_stream_info_for_profile params: ['channel_id', 'stream_id', 'm3u_profile_id']
```

---

## 🎨 FRONTEND VERIFICATION

### 1. Proxy Settings Constants (frontend/src/constants.js)

**Zu prüfen:**
```javascript
// Open browser console on settings page
console.log(PROXY_SETTINGS_OPTIONS);
```

**Erwartete Ausgabe:**
Sollte folgende neue Felder enthalten:
- max_retries
- url_switch_timeout
- max_stream_switches
- connection_timeout
- failover_grace_period

---

### 2. Proxy Settings Form Utils (frontend/src/utils/forms/settings/ProxySettingsFormUtils.js)

**Zu prüfen:**
```javascript
// Check default values
import { getDefaultProxySettings } from './ProxySettingsFormUtils';
const defaults = getDefaultProxySettings();
console.log(defaults);
```

**Erwartete Ausgabe:**
```javascript
{
    buffering_timeout: 15,
    buffering_speed: 1.0,
    redis_chunk_ttl: 60,
    channel_shutdown_delay: 0,
    channel_init_grace_period: 5,
    max_retries: 2,
    url_switch_timeout: 20,
    max_stream_switches: 200,
    connection_timeout: 10,
    failover_grace_period: 20
}
```

---

### 3. Proxy Settings Form (frontend/src/components/forms/settings/ProxySettingsForm.jsx)

**Zu prüfen:**
1. Öffne Settings → Proxy Settings
2. Prüfe ob folgende Felder vorhanden sind:
   - Max Retries
   - URL Switch Timeout
   - Max Stream Switches
   - Connection Timeout
   - Failover Grace Period

**Erwartete Werte:**
- Max Retries: 2 (max: 10)
- URL Switch Timeout: 20 (max: 60)
- Max Stream Switches: 200 (max: 500)
- Connection Timeout: 10 (max: 60)
- Failover Grace Period: 20 (max: 60)

---

### 4. M3U Form (frontend/src/components/forms/M3U.jsx)

**Zu prüfen:**
1. Öffne M3U Accounts → Add/Edit Account
2. Prüfe ob "HTTP Proxy" Feld vorhanden ist
3. Gib einen Proxy ein: http://proxy:8080
4. Speichere
5. Prüfe ob Wert gespeichert wurde

**Erwartete Ausgabe:**
- HTTP Proxy Feld vorhanden
- Wert wird gespeichert
- Wert wird beim Laden angezeigt

---

## 🔄 MIGRATION VERIFICATION

### Migration 0019_add_proxy_field

**Zu prüfen:**
```bash
# Check if migration exists
ls apps/m3u/migrations/0019_add_proxy_field.py

# Check migration status
python manage.py showmigrations m3u

# Should show:
# [X] 0019_add_proxy_field
```

**Erwartete Ausgabe:**
```
apps/m3u/migrations/0019_add_proxy_field.py exists
[X] 0019_add_proxy_field
```

---

## 🧪 INTEGRATION TESTS

### Test 1: Profile Failover

**Setup:**
1. Erstelle Channel mit 2 Streams
2. Jeder Stream hat 2 Profile (insgesamt 4 Kombinationen)
3. Starte Channel

**Test:**
1. Simuliere Stream-Fehler (z.B. ungültige URL)
2. Warte auf automatischen Failover
3. Prüfe Logs

**Erwartete Ausgabe:**
```
Trying stream ID 1 with profile ID 1
Failed, trying stream ID 1 with profile ID 2
Failed, trying stream ID 2 with profile ID 1
Success!
```

---

### Test 2: HTTP Proxy (FFmpeg)

**Setup:**
1. Konfiguriere M3U Account mit Proxy: http://proxy:8080
2. Erstelle Channel mit FFmpeg Stream Profile
3. Starte Channel

**Test:**
1. Prüfe Logs für FFmpeg Command
2. Sollte -http_proxy Parameter enthalten

**Erwartete Ausgabe:**
```
Starting transcode process: ['ffmpeg', '-http_proxy', 'http://proxy:8080', ...]
Using proxy http://proxy:8080 for channel ...
```

---

### Test 3: HTTP Proxy (HTTP Stream)

**Setup:**
1. Konfiguriere M3U Account mit Proxy: http://proxy:8080
2. Erstelle Channel mit Proxy Stream Profile
3. Starte Channel

**Test:**
1. Prüfe Logs für HTTP Connection
2. Sollte Proxy verwenden

**Erwartete Ausgabe:**
```
Using HTTP proxy http://proxy:8080 for channel ...
Successfully started HTTP streamer thread for channel ...
```

---

### Test 4: Basic Authentication

**Setup:**
1. Erstelle User Account
2. Notiere Username und Password

**Test:**
```bash
# Test ohne Auth
curl -v http://localhost:8000/m3u/
# Expected: 401 Unauthorized

# Test mit falschen Credentials
curl -v -u wrong:wrong http://localhost:8000/m3u/
# Expected: 401 Unauthorized

# Test mit korrekten Credentials
curl -v -u username:password http://localhost:8000/m3u/
# Expected: 200 OK
```

---

### Test 5: Extended Configuration

**Setup:**
1. Öffne Admin Panel → Settings → Proxy Settings

**Test:**
1. Ändere max_stream_switches auf 100
2. Speichere
3. Prüfe ob Wert gespeichert wurde
4. Starte Channel
5. Prüfe Logs ob neuer Wert verwendet wird

**Erwartete Ausgabe:**
```
Get max stream switches from config using the helper method
max_stream_switches = ConfigHelper.max_stream_switches()  # Should be 100
```

---

## ✅ VERIFICATION SUMMARY

### Backend Checklist
- [ ] Config System (10 Settings)
- [ ] M3U Account Proxy Field
- [ ] StreamProfile build_command
- [ ] HTTPStreamReader Proxy Support
- [ ] ConfigHelper Methods
- [ ] Basic Authentication
- [ ] StreamManager Profile Tracking
- [ ] URL Utils Functions

### Frontend Checklist
- [ ] Proxy Settings Constants
- [ ] Proxy Settings Form Utils
- [ ] Proxy Settings Form (5 neue Felder)
- [ ] M3U Form (Proxy Feld)

### Migration Checklist
- [ ] Migration 0019 existiert
- [ ] Migration angewendet

### Integration Tests
- [ ] Profile Failover funktioniert
- [ ] HTTP Proxy (FFmpeg) funktioniert
- [ ] HTTP Proxy (HTTP) funktioniert
- [ ] Basic Authentication funktioniert
- [ ] Extended Configuration funktioniert

---

## 🎯 SUCCESS CRITERIA

**Alle Tests bestanden wenn:**
1. ✅ Alle Backend Checks erfolgreich
2. ✅ Alle Frontend Checks erfolgreich
3. ✅ Migration angewendet
4. ✅ Alle Integration Tests bestanden
5. ✅ Keine Fehler in Logs
6. ✅ Server startet ohne Probleme

---

**Erstellt:** 2026-03-02  
**Version:** 1.0.0  
**Status:** READY FOR TESTING
