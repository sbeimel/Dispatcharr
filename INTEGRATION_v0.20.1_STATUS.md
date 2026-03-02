# 🚧 INTEGRATION v0.20.1 - STATUS

**Datum:** 2026-03-02  
**Ziel:** Integration aller v0.19.0 Features in Dispatcharr-0.20.1

---

## ⚠️ WICHTIGE ERKENNTNISSE

### 1. v0.20.1 nutzt pyproject.toml statt requirements.txt

**Das ist eine GROSSE Änderung!**

v0.20.1 hat auf `uv` Package Manager umgestellt (siehe CHANGELOG):
```
- Switched to uv for package management
- pyproject.toml statt requirements.txt
- Lockfile-basierte Dependencies
```

**Auswirkung:** Dependencies müssen anders hinzugefügt werden!

### 2. Bereits durchgeführte Änderungen

✅ **apps/proxy/config.py** - KOMPLETT AKTUALISIERT:
- MAX_RETRIES: 3 → 2
- MAX_STREAM_SWITCHES: 10 → 200
- get_proxy_settings() erweitert (10 Settings)
- Alle Getter-Methoden hinzugefügt:
  - get_max_retries()
  - get_url_switch_timeout()
  - get_max_stream_switches()
  - get_connection_timeout()
  - get_failover_grace_period()
- TSConfig.get_failover_grace_period() hinzugefügt

---

## 📋 NOCH ZU IMPLEMENTIEREN

### Backend (Kritisch)

1. ❌ **apps/m3u/models.py**
   - proxy Feld hinzufügen
   - Migration erstellen

2. ❌ **core/models.py**
   - build_command(proxy=None) Parameter
   - FFmpeg -http_proxy injection

3. ❌ **apps/proxy/ts_proxy/http_streamer.py**
   - __init__(proxy=None) Parameter
   - session.proxies Konfiguration

4. ❌ **apps/proxy/ts_proxy/stream_manager.py**
   - tried_combinations statt tried_stream_ids
   - current_profile_id Tracking
   - Proxy-Support in _establish_transcode_connection()
   - Proxy-Support in _establish_http_connection()
   - Profile Failover Logik

5. ❌ **apps/proxy/ts_proxy/url_utils.py**
   - get_alternate_streams() erweitern
   - get_stream_info_for_profile() hinzufügen

6. ❌ **apps/proxy/ts_proxy/config_helper.py**
   - max_retries() aktualisieren
   - max_stream_switches() aktualisieren
   - url_switch_timeout() aktualisieren
   - failover_grace_period() aktualisieren
   - connection_timeout() hinzufügen

7. ❌ **apps/output/views.py**
   - get_basic_auth_user() hinzufügen
   - require_basic_auth() hinzufügen
   - M3U/EPG Endpoints anpassen

8. ❌ **apps/m3u/serializers.py**
   - proxy Feld hinzufügen

### Frontend (Kritisch)

1. ❌ **frontend/src/constants.js**
   - 5 neue Settings zu PROXY_SETTINGS_OPTIONS

2. ❌ **frontend/src/components/forms/settings/ProxySettingsForm.jsx**
   - isNumericField() erweitern
   - getNumericFieldMax() erweitern

3. ❌ **frontend/src/utils/forms/settings/ProxySettingsFormUtils.js**
   - getProxySettingDefaults() erweitern

4. ❌ **frontend/src/components/forms/M3U.jsx**
   - proxy Feld hinzufügen

### Migration

1. ❌ **apps/m3u/migrations/0XXX_add_proxy_field.py**
   - Erstellen

---

## 🤔 EMPFEHLUNG

### Option A: Manuelle Integration (EMPFOHLEN)

**Grund:** v0.20.1 hat signifikante Änderungen:
- Neues Package Management (uv/pyproject.toml)
- Neue Architektur
- Viele neue Features

**Vorgehen:**
1. Jede Datei einzeln anpassen
2. Testen nach jeder Änderung
3. Migration erstellen
4. Frontend anpassen
5. Patch erstellen

**Geschätzter Aufwand:** 3-4 Stunden

### Option B: Automatischer Patch (RISKANT)

**Problem:** 
- v0.19.0 Patch passt nicht direkt auf v0.20.1
- Zu viele Unterschiede
- Hohe Fehlerwahrscheinlichkeit

**Nicht empfohlen!**

---

## 🎯 NÄCHSTE SCHRITTE

### Soll ich fortfahren?

**Frage an dich:**

1. **Soll ich die vollständige Integration durchführen?**
   - Alle Backend-Dateien anpassen
   - Alle Frontend-Dateien anpassen
   - Migration erstellen
   - Patch erstellen

2. **Oder nur Patch erstellen?**
   - Basierend auf aktuellen Änderungen
   - Dokumentation für manuelle Integration

3. **Oder Analyse vertiefen?**
   - Mehr Details zu Unterschieden
   - Risiko-Bewertung
   - Alternative Ansätze

---

## 📊 FORTSCHRITT

**Aktuell:** 1 von 15 Dateien angepasst (6.7%)

**Verbleibend:**
- 7 Backend-Dateien
- 4 Frontend-Dateien
- 1 Migration
- 1 Patch-Datei
- 1 Installer-Script

**Geschätzte Zeit:** 3-4 Stunden für vollständige Integration

---

## ⚠️ RISIKEN

1. **v0.20.1 ist sehr neu** (26.02.2026)
   - Möglicherweise noch Bugs
   - Wenig getestet

2. **Große Architektur-Änderungen**
   - uv statt pip
   - Neue Dependencies
   - Neue Features

3. **Kompatibilität**
   - Unsere Features könnten mit neuen Features kollidieren
   - Integrations/Webhooks System
   - API Key Authentication

---

## 💡 ALTERNATIVE

**Warte auf v0.20.2 oder v0.21.0?**

Vorteile:
- v0.20.1 Bugs werden gefixt
- Stabilere Basis
- Weniger Risiko

Nachteile:
- Längere Wartezeit
- Features nicht sofort verfügbar

---

**Erstellt:** 2026-03-02  
**Version:** 1.0.0  
**Status:** INTEGRATION GESTARTET - WARTET AUF ENTSCHEIDUNG
