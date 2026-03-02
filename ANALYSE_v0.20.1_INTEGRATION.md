# 🔍 ANALYSE: Integration v0.19.0 Features in v0.20.1

**Datum:** 2026-03-02  
**Ziel:** Prüfung ob unsere v0.19.0 Enhancements in v0.20.1 integriert werden können

---

## 📊 ZUSAMMENFASSUNG

**STATUS:** ✅ **INTEGRATION MÖGLICH MIT ANPASSUNGEN**

Dispatcharr v0.20.1 hat signifikante Änderungen, aber unsere Features können integriert werden.

---

## 🎯 UNSERE FEATURES (v0.19.0 Enhancements)

### 1. Profile Failover System ✅
- **Status:** KANN INTEGRIERT WERDEN
- **Änderungen nötig:** JA - v0.20.1 hat bereits `tried_stream_ids`, wir müssen auf `tried_combinations` erweitern
- **Dateien:** stream_manager.py, url_utils.py

### 2. Universal HTTP Proxy Support ⚠️
- **Status:** KANN INTEGRIERT WERDEN
- **Änderungen nötig:** JA - `proxy` Feld fehlt in M3UAccount Model
- **Dateien:** models.py, http_streamer.py, M3U.jsx
- **Migration:** ERFORDERLICH

### 3. Basic Authentication ✅
- **Status:** KANN INTEGRIERT WERDEN
- **Änderungen nötig:** MINIMAL
- **Dateien:** output/views.py

### 4. Extended Timeout Configuration ⚠️
- **Status:** KANN INTEGRIERT WERDEN
- **Änderungen nötig:** JA - v0.20.1 hat nur 5 Settings, wir haben 10
- **Fehlende Settings:**
  - max_retries
  - url_switch_timeout
  - max_stream_switches
  - connection_timeout
  - failover_grace_period

### 5. Ghost-Client Auto-Cleanup ✅
- **Status:** BEREITS IN v0.20.1 VORHANDEN
- **Änderungen nötig:** KEINE

---

## 🔄 WICHTIGE ÄNDERUNGEN IN v0.20.1

### Neue Features die unsere Integration beeinflussen:

1. **API Key Authentication** - Neue Auth-Methode
2. **Integrations/Webhooks** - Event-System
3. **drf-spectacular statt drf-yasg** - API Dokumentation
4. **Stream Identity Stability** - `stream_id` und `stream_chno` Felder
5. **Cron Scheduling** - Neue Scheduling-Optionen
6. **Channel Numbering Modes** - Erweiterte Auto-Sync

### Kritische Änderungen:

#### 1. Stream Manager (`stream_manager.py`)
**v0.20.1 hat bereits:**
```python
self.current_stream_id = stream_id
self.tried_stream_ids = set()
```

**Wir brauchen:**
```python
self.current_stream_id = stream_id
self.current_profile_id = None  # NEU
self.tried_combinations = set()  # STATT tried_stream_ids
```

#### 2. Config System (`config.py`)
**v0.20.1 hat:**
- `MAX_RETRIES = 3` (wir wollen 2)
- `MAX_STREAM_SWITCHES = 10` (wir wollen 200)
- Nur 5 Settings in get_proxy_settings()

**Wir brauchen:**
- 10 Settings total
- Getter-Methoden für alle Settings

#### 3. M3U Models (`models.py`)
**v0.20.1 fehlt:**
- `proxy` Feld in M3UAccount

**Migration erforderlich!**

---

## 📋 INTEGRATIONS-PLAN

### Phase 1: Backend Core Features

#### 1.1 Config System erweitern
**Datei:** `apps/proxy/config.py`

**Änderungen:**
```python
# Konstanten anpassen
MAX_RETRIES = 2  # von 3 auf 2
MAX_STREAM_SWITCHES = 200  # von 10 auf 200

# get_proxy_settings() erweitern
def get_proxy_settings(cls):
    return {
        "buffering_timeout": 15,
        "buffering_speed": 1.0,
        "redis_chunk_ttl": 60,
        "channel_shutdown_delay": 0,
        "channel_init_grace_period": 5,
        # NEU:
        "max_retries": 2,
        "url_switch_timeout": 20,
        "max_stream_switches": 200,
        "connection_timeout": 10,
        "failover_grace_period": 20,
    }

# Getter-Methoden hinzufügen
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

#### 1.2 Profile Failover System
**Datei:** `apps/proxy/ts_proxy/stream_manager.py`

**Änderungen:**
```python
# In __init__:
self.current_stream_id = stream_id
self.current_profile_id = None  # NEU
self.tried_combinations = set()  # STATT tried_stream_ids

# tried_combinations tracking hinzufügen
self.tried_combinations.add((self.current_stream_id, self.current_profile_id))
```

**Datei:** `apps/proxy/ts_proxy/url_utils.py`

**Neue Funktionen:**
- `get_stream_info_for_profile(channel_id, stream_id, m3u_profile_id)`
- Erweiterte `get_alternate_streams()` mit Profile-Support

#### 1.3 HTTP Proxy Support
**Datei:** `apps/m3u/models.py`

**Migration erstellen:**
```python
# Migration: 0XXX_add_proxy_field.py
proxy = models.CharField(
    max_length=255,
    blank=True,
    null=True,
    help_text="HTTP Proxy URL (e.g., http://proxy:port)"
)
```

**Datei:** `core/models.py` (StreamProfile)

**Änderungen:**
- `build_command()` mit proxy Parameter erweitern
- FFmpeg `-http_proxy` Parameter injection

**Datei:** `apps/proxy/ts_proxy/http_streamer.py`

**Änderungen:**
- `__init__` mit proxy Parameter
- `session.proxies` setzen

#### 1.4 Basic Authentication
**Datei:** `apps/output/views.py`

**Neue Funktionen:**
```python
def get_basic_auth_user(request):
    """Extract user from HTTP Basic Auth header"""
    ...

def require_basic_auth(request):
    """Decorator for Basic Auth"""
    ...
```

**Endpoints anpassen:**
- M3U Endpoint
- EPG Endpoint

### Phase 2: Frontend Integration

#### 2.1 Constants erweitern
**Datei:** `frontend/src/constants.js`

**Änderungen:**
- PROXY_SETTINGS_OPTIONS um 5 neue Settings erweitern

#### 2.2 Proxy Settings Form
**Datei:** `frontend/src/components/forms/settings/ProxySettingsForm.jsx`

**Änderungen:**
- `isNumericField()` erweitern
- `getNumericFieldMax()` erweitern

#### 2.3 Proxy Settings Utils
**Datei:** `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js`

**Änderungen:**
- `getProxySettingDefaults()` um 5 neue Settings erweitern

#### 2.4 M3U Form
**Datei:** `frontend/src/components/forms/M3U.jsx`

**Änderungen:**
- Proxy-Feld hinzufügen
- initialValues erweitern
- Formular-Rendering anpassen

### Phase 3: Testing & Verification

#### 3.1 Backend Tests
- Migration testen
- Config-Getter testen
- Profile Failover testen
- HTTP Proxy testen
- Basic Auth testen

#### 3.2 Frontend Tests
- Settings Form testen
- M3U Form testen
- Proxy-Feld Validierung testen

---

## ⚠️ KONFLIKTE & RISIKEN

### 1. Stream Manager Refactoring
**Problem:** v0.20.1 hat `tried_stream_ids`, wir brauchen `tried_combinations`

**Lösung:** 
- Umbenennen von `tried_stream_ids` zu `tried_combinations`
- Tuple-Tracking statt nur Stream-IDs
- Kompatibilität mit bestehendem Code sicherstellen

### 2. drf-spectacular Migration
**Problem:** v0.20.1 nutzt drf-spectacular statt drf-yasg

**Lösung:**
- Unsere Imports bereits auf drf-spectacular umgestellt
- Keine Konflikte erwartet

### 3. Neue v0.20.1 Features
**Problem:** Integrations/Webhooks könnten mit unserem Code interagieren

**Lösung:**
- Testen ob Events durch unsere Änderungen ausgelöst werden
- Dokumentation der Event-Interaktionen

### 4. requirements.txt
**Problem:** drf-spectacular fehlt in aktueller requirements.txt

**Status:** ✅ BEREITS GEFIXT
- drf-spectacular>=0.27.0 wurde hinzugefügt

---

## 📝 MIGRATIONS-ÜBERSICHT

### Erforderliche Migrations:

1. **M3U Proxy Field**
   ```bash
   python manage.py makemigrations m3u
   # Creates: 0XXX_add_proxy_field.py
   ```

2. **Core Settings Update**
   - Keine Migration nötig (JSON Field)
   - Defaults werden in Code gesetzt

---

## 🎯 EMPFOHLENE VORGEHENSWEISE

### Option A: Vollständige Integration (EMPFOHLEN)
1. Alle Features portieren
2. Neue Migration erstellen
3. Frontend komplett anpassen
4. Umfassende Tests

**Vorteile:**
- Alle Features verfügbar
- Konsistente Codebasis
- Zukunftssicher

**Nachteile:**
- Mehr Aufwand
- Mehr Testing nötig

### Option B: Schrittweise Integration
1. Nur kritische Features (Profile Failover, Config)
2. HTTP Proxy später
3. Basic Auth optional

**Vorteile:**
- Schnellere erste Version
- Weniger Risiko

**Nachteile:**
- Unvollständige Feature-Set
- Mehrere Deployment-Zyklen

---

## ✅ NÄCHSTE SCHRITTE

### 1. Entscheidung treffen
- [ ] Option A oder B wählen
- [ ] Zeitplan festlegen

### 2. Backup erstellen
- [ ] Dispatcharr-0.20.1 Ordner sichern
- [ ] Git Branch erstellen

### 3. Integration starten
- [ ] Phase 1: Backend Core
- [ ] Phase 2: Frontend
- [ ] Phase 3: Testing

### 4. Patch erstellen
- [ ] dispatcharr_enhancements_v0.20.1.patch
- [ ] apply_dispatcharr_enhancements_v0.20.1.sh

### 5. Dokumentation
- [ ] INSTALLATION_COMPLETE_v0.20.1.md
- [ ] PATCH_NOTES_v0.20.1.md
- [ ] VERIFICATION_CHECKLIST_v0.20.1.md

---

## 🎉 FAZIT

**JA, Integration ist möglich!**

v0.20.1 hat viele neue Features, aber keine fundamentalen Konflikte mit unseren Enhancements. Die Hauptarbeit liegt in:

1. ✅ Config System erweitern (5 neue Settings)
2. ✅ Profile Failover anpassen (tried_combinations)
3. ✅ HTTP Proxy Migration erstellen
4. ✅ Frontend Forms aktualisieren
5. ✅ Basic Auth integrieren

**Geschätzter Aufwand:** 4-6 Stunden für vollständige Integration

**Empfehlung:** Option A - Vollständige Integration für maximale Feature-Parity

---

**Erstellt:** 2026-03-02  
**Version:** 1.0.0  
**Basis:** Dispatcharr v0.20.1 + v0.19.0 Enhancements
