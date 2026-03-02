# 📊 FEATURE-VERGLEICH: v0.19.0 vs v0.20.1

**Datum:** 2026-03-02  
**Zweck:** Detaillierter Vergleich unserer Enhancements mit v0.20.1

---

## 🎯 UNSERE ENHANCEMENTS (v0.19.0)

### Feature-Übersicht

| Feature | Beschreibung | Status in v0.20.1 |
|---------|--------------|-------------------|
| Profile Failover System | 343 Stream/Profile-Kombinationen | ⚠️ TEILWEISE (nur Stream-IDs) |
| Universal HTTP Proxy | Proxy für FFmpeg + Proxy-Profile | ❌ FEHLT |
| Basic Authentication | Sichere M3U/EPG Endpoints | ❌ FEHLT |
| Extended Timeout Config | 10 konfigurierbare Settings | ⚠️ TEILWEISE (5 von 10) |
| Ghost-Client Cleanup | Automatische Bereinigung | ✅ VORHANDEN |

---

## 📋 DETAILLIERTER VERGLEICH

### 1. PROFILE FAILOVER SYSTEM

#### v0.19.0 (Unsere Version)
```python
# stream_manager.py
self.current_stream_id = stream_id
self.current_profile_id = None
self.tried_combinations = set()  # (stream_id, profile_id) tuples

# Tracking
self.tried_combinations.add((self.current_stream_id, self.current_profile_id))

# Alternate streams mit Profile-Support
untried = [s for s in alternate_streams 
           if (s['stream_id'], s['profile_id']) not in self.tried_combinations]
```

**Features:**
- ✅ Stream + Profile Kombinationen
- ✅ 343 mögliche Kombinationen
- ✅ Intelligentes Failover
- ✅ Profile-aware Switching

#### v0.20.1 (Aktuell)
```python
# stream_manager.py
self.current_stream_id = stream_id
self.tried_stream_ids = set()  # Nur Stream-IDs

# Tracking
self.tried_stream_ids.add(stream_id)
```

**Features:**
- ✅ Stream-ID Tracking
- ❌ Kein Profile-Support
- ❌ Nur ~10 Kombinationen
- ❌ Kein Profile-aware Switching

**INTEGRATION:** ⚠️ ANPASSUNG NÖTIG
- `tried_stream_ids` → `tried_combinations` umbenennen
- Profile-ID Tracking hinzufügen
- `get_stream_info_for_profile()` implementieren

---

### 2. UNIVERSAL HTTP PROXY SUPPORT

#### v0.19.0 (Unsere Version)

**Backend:**
```python
# models.py (M3UAccount)
proxy = models.CharField(
    max_length=255,
    blank=True,
    null=True,
    help_text="HTTP Proxy URL"
)

# core/models.py (StreamProfile.build_command)
if proxy and self.command == "ffmpeg":
    if "-http_proxy" not in self.parameters:
        cmd.extend(["-http_proxy", proxy])

# http_streamer.py
def __init__(self, url, user_agent=None, chunk_size=8192, proxy=None):
    if self.proxy:
        self.session.proxies = {
            'http': self.proxy,
            'https': self.proxy
        }
```

**Frontend:**
```jsx
// M3U.jsx
<TextField
  label="HTTP Proxy"
  name="proxy"
  placeholder="http://proxy:port"
/>
```

**Features:**
- ✅ Proxy für FFmpeg Streams
- ✅ Proxy für HTTP Proxy-Profile
- ✅ Frontend-Konfiguration
- ✅ Per-Account Proxy

#### v0.20.1 (Aktuell)

**Status:** ❌ NICHT VORHANDEN

**INTEGRATION:** ⚠️ MIGRATION ERFORDERLICH
- M3U Model erweitern
- Migration erstellen
- Frontend Form anpassen
- Proxy-Übergabe implementieren

---

### 3. BASIC AUTHENTICATION

#### v0.19.0 (Unsere Version)

```python
# output/views.py
def get_basic_auth_user(request):
    """Extract user from HTTP Basic Auth"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Basic '):
        try:
            decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = decoded.split(':', 1)
            user = authenticate(username=username, password=password)
            return user
        except Exception:
            return None
    return None

def require_basic_auth(request):
    """Check Basic Auth or Token Auth"""
    # Try token auth first
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    
    # Try basic auth
    user = get_basic_auth_user(request)
    if user:
        return user
    
    # Unauthorized
    response = HttpResponse('Unauthorized', status=401)
    response['WWW-Authenticate'] = 'Basic realm="Dispatcharr"'
    return response

# M3U Endpoint
@api_view(['GET'])
def m3u_output(request, user_id=None):
    user = require_basic_auth(request)
    if isinstance(user, HttpResponse):
        return user
    ...

# EPG Endpoint  
@api_view(['GET'])
def epg_output(request, user_id=None):
    user = require_basic_auth(request)
    if isinstance(user, HttpResponse):
        return user
    ...
```

**Features:**
- ✅ HTTP Basic Authentication
- ✅ M3U Endpoint geschützt
- ✅ EPG Endpoint geschützt
- ✅ Fallback zu Token Auth
- ✅ Standard-konform (RFC 7617)

#### v0.20.1 (Aktuell)

**Status:** ❌ NICHT VORHANDEN

**Aber:** v0.20.1 hat API Key Authentication!
```
Authorization: ApiKey <key>
X-API-Key: <key>
```

**INTEGRATION:** ✅ EINFACH
- Basic Auth Funktionen hinzufügen
- Endpoints anpassen
- Kompatibel mit API Keys

---

### 4. EXTENDED TIMEOUT CONFIGURATION

#### v0.19.0 (Unsere Version) - 10 Settings

| Setting | Default | Beschreibung |
|---------|---------|--------------|
| buffering_timeout | 15s | Puffer-Timeout |
| buffering_speed | 1.0 | Puffer-Geschwindigkeit |
| redis_chunk_ttl | 60s | Redis Chunk TTL |
| channel_shutdown_delay | 0s | Channel Shutdown Delay |
| channel_init_grace_period | 5s | Channel Init Grace |
| **max_retries** | **2** | **Retry-Versuche** |
| **url_switch_timeout** | **20s** | **Stream-Wechsel Timeout** |
| **max_stream_switches** | **200** | **Max Kombinationen** |
| **connection_timeout** | **10s** | **Verbindungs-Timeout** |
| **failover_grace_period** | **20s** | **Failover Grace Period** |

**Backend:**
```python
# config.py
@classmethod
def get_proxy_settings(cls):
    return {
        "buffering_timeout": 15,
        "buffering_speed": 1.0,
        "redis_chunk_ttl": 60,
        "channel_shutdown_delay": 0,
        "channel_init_grace_period": 5,
        "max_retries": 2,
        "url_switch_timeout": 20,
        "max_stream_switches": 200,
        "connection_timeout": 10,
        "failover_grace_period": 20,
    }

# Getter-Methoden
@classmethod
def get_max_retries(cls): ...
@classmethod
def get_url_switch_timeout(cls): ...
@classmethod
def get_max_stream_switches(cls): ...
@classmethod
def get_connection_timeout(cls): ...
@classmethod
def get_failover_grace_period(cls): ...
```

**Frontend:**
```javascript
// constants.js
export const PROXY_SETTINGS_OPTIONS = {
  buffering_timeout: { label: "Buffering Timeout", ... },
  buffering_speed: { label: "Buffering Speed", ... },
  redis_chunk_ttl: { label: "Redis Chunk TTL", ... },
  channel_shutdown_delay: { label: "Channel Shutdown Delay", ... },
  channel_init_grace_period: { label: "Channel Init Grace", ... },
  max_retries: { label: "Max Retries", ... },
  url_switch_timeout: { label: "URL Switch Timeout", ... },
  max_stream_switches: { label: "Max Stream Switches", ... },
  connection_timeout: { label: "Connection Timeout", ... },
  failover_grace_period: { label: "Failover Grace Period", ... },
};
```

#### v0.20.1 (Aktuell) - 5 Settings

| Setting | Default | Status |
|---------|---------|--------|
| buffering_timeout | 15s | ✅ VORHANDEN |
| buffering_speed | 1.0 | ✅ VORHANDEN |
| redis_chunk_ttl | 60s | ✅ VORHANDEN |
| channel_shutdown_delay | 0s | ✅ VORHANDEN |
| channel_init_grace_period | 5s | ✅ VORHANDEN |
| max_retries | - | ❌ FEHLT |
| url_switch_timeout | - | ❌ FEHLT |
| max_stream_switches | - | ❌ FEHLT |
| connection_timeout | - | ❌ FEHLT |
| failover_grace_period | - | ❌ FEHLT |

**Hardcoded in v0.20.1:**
```python
# config.py
MAX_RETRIES = 3  # Wir wollen 2
MAX_STREAM_SWITCHES = 10  # Wir wollen 200
CONNECTION_TIMEOUT = 10  # Wir wollen konfigurierbar
```

**INTEGRATION:** ⚠️ ERWEITERUNG NÖTIG
- 5 neue Settings hinzufügen
- Getter-Methoden implementieren
- Frontend erweitern
- Defaults anpassen

---

### 5. GHOST-CLIENT AUTO-CLEANUP

#### v0.19.0 (Unsere Version)

```python
# client_manager.py
def _heartbeat_thread(self):
    """Background thread for ghost client detection"""
    while self.running:
        try:
            ghost_clients_in_set = set()
            
            # Check Redis SET vs Individual Keys
            set_clients = self.redis_client.smembers(clients_set_key)
            for client_id_bytes in set_clients:
                client_id = client_id_bytes.decode('utf-8')
                client_key = RedisKeys.client_record(self.channel_id, client_id)
                
                if not self.redis_client.exists(client_key):
                    ghost_clients_in_set.add(client_id)
            
            # Remove ghosts atomically
            if ghost_clients_in_set:
                self.redis_client.srem(clients_set_key, *ghost_clients_in_set)
                logger.info(f"Removed {len(ghost_clients_in_set)} ghost clients")
            
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in heartbeat thread: {e}")
```

**Features:**
- ✅ Automatische Ghost-Detection
- ✅ Atomic Operations
- ✅ Heartbeat-Thread
- ✅ Smart Client Count

#### v0.20.1 (Aktuell)

**Status:** ✅ BEREITS VORHANDEN

v0.20.1 hat ähnliche Implementierung in `client_manager.py`

**INTEGRATION:** ✅ KEINE ÄNDERUNG NÖTIG

---

## 🔧 TECHNISCHE UNTERSCHIEDE

### Config-Architektur

#### v0.19.0
```python
# JSON-basiert in CoreSettings
settings = {
    "buffering_timeout": 15,
    "max_retries": 2,
    ...
}

# Getter-Methoden
@classmethod
def get_max_retries(cls):
    settings = cls.get_proxy_settings()
    return settings.get("max_retries", 2)
```

#### v0.20.1
```python
# Teilweise JSON, teilweise Konstanten
class BaseConfig:
    MAX_RETRIES = 3  # Hardcoded
    MAX_STREAM_SWITCHES = 10  # Hardcoded
    
    @classmethod
    def get_proxy_settings(cls):
        return {
            "buffering_timeout": 15,
            # Nur 5 Settings
        }
```

**INTEGRATION:** Unsere Architektur ist besser (mehr konfigurierbar)

---

### Stream Manager

#### v0.19.0
```python
# Profile-aware
self.current_stream_id = stream_id
self.current_profile_id = profile_id
self.tried_combinations = set()  # (stream_id, profile_id)
```

#### v0.20.1
```python
# Nur Stream-aware
self.current_stream_id = stream_id
self.tried_stream_ids = set()  # stream_id only
```

**INTEGRATION:** Unsere Version ist mächtiger

---

## 📊 FEATURE-MATRIX

| Feature | v0.19.0 | v0.20.1 | Integration |
|---------|---------|---------|-------------|
| **Profile Failover** | ✅ Full | ⚠️ Partial | Erweitern |
| **HTTP Proxy** | ✅ Full | ❌ None | Migration |
| **Basic Auth** | ✅ Full | ❌ None | Hinzufügen |
| **10 Settings** | ✅ Full | ⚠️ 5/10 | Erweitern |
| **Ghost Cleanup** | ✅ Full | ✅ Full | Behalten |
| **API Keys** | ❌ None | ✅ Full | Behalten |
| **Integrations** | ❌ None | ✅ Full | Behalten |
| **Cron Scheduling** | ❌ None | ✅ Full | Behalten |
| **drf-spectacular** | ✅ Full | ✅ Full | Kompatibel |

---

## 🎯 INTEGRATIONS-STRATEGIE

### Was behalten wir?
- ✅ Alle v0.20.1 Features (API Keys, Integrations, etc.)
- ✅ Unsere Enhancements (Profile Failover, HTTP Proxy, etc.)

### Was ändern wir?
- ⚠️ Stream Manager: `tried_stream_ids` → `tried_combinations`
- ⚠️ Config: 5 Settings → 10 Settings
- ⚠️ M3U Model: Proxy-Feld hinzufügen

### Was ist neu?
- ✅ Kompatibilität mit API Keys
- ✅ Kompatibilität mit Integrations
- ✅ Kompatibilität mit Cron Scheduling

---

## 📈 VERBESSERUNGEN

### Unsere Enhancements bringen:

1. **Mehr Ausfallsicherheit**
   - 343 statt 10 Failover-Kombinationen
   - Profile-aware Switching

2. **Mehr Flexibilität**
   - HTTP Proxy Support
   - 10 statt 5 konfigurierbare Settings

3. **Mehr Sicherheit**
   - Basic Authentication für M3U/EPG

4. **Bessere Performance**
   - Optimierte Retry-Logik (2 statt 3)
   - Höhere Switch-Limits (200 statt 10)

---

## ✅ FAZIT

**INTEGRATION IST SINNVOLL UND MÖGLICH!**

### Vorteile:
- ✅ Alle v0.20.1 Features bleiben erhalten
- ✅ Unsere Enhancements kommen hinzu
- ✅ Keine fundamentalen Konflikte
- ✅ Bessere Ausfallsicherheit
- ✅ Mehr Konfigurierbarkeit

### Aufwand:
- ⚠️ Migration für Proxy-Feld
- ⚠️ Config System erweitern
- ⚠️ Stream Manager anpassen
- ⚠️ Frontend aktualisieren

### Empfehlung:
**JA, vollständige Integration durchführen!**

Die Kombination aus v0.20.1 Features + unseren Enhancements ergibt die beste Dispatcharr-Version!

---

**Erstellt:** 2026-03-02  
**Version:** 1.0.0  
**Basis:** Detaillierte Code-Analyse beider Versionen
