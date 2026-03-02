# 🗺️ INTEGRATION ROADMAP: v0.20.1 Enhancements

**Datum:** 2026-03-02  
**Ziel:** Schritt-für-Schritt Plan zur Integration unserer Features in v0.20.1

---

## 📋 ÜBERSICHT

**Geschätzter Aufwand:** 4-6 Stunden  
**Schwierigkeitsgrad:** Mittel  
**Risiko:** Niedrig (keine Breaking Changes)

---

## 🎯 PHASEN

### Phase 1: Vorbereitung (30 Min)
### Phase 2: Backend Core (2 Std)
### Phase 3: Frontend (1.5 Std)
### Phase 4: Testing (1 Std)
### Phase 5: Dokumentation (30 Min)

---

## 📝 PHASE 1: VORBEREITUNG

### 1.1 Backup erstellen
```bash
# Dispatcharr-0.20.1 sichern
cp -r Dispatcharr-0.20.1 Dispatcharr-0.20.1.backup

# Git Branch erstellen (falls Git verwendet)
cd Dispatcharr-0.20.1
git checkout -b feature/enhancements-v0.20.1
```

### 1.2 Dokumentation prüfen
- [x] ANALYSE_v0.20.1_INTEGRATION.md gelesen
- [x] FEATURE_VERGLEICH_v0.19.0_vs_v0.20.1.md gelesen
- [x] Unsere v0.19.0 Patches verstanden

### 1.3 Abhängigkeiten prüfen
```bash
# requirements.txt prüfen
grep drf-spectacular requirements.txt
# Sollte vorhanden sein: drf-spectacular>=0.27.0
```

---

## 🔧 PHASE 2: BACKEND CORE

### 2.1 Config System erweitern (30 Min)

**Datei:** `Dispatcharr-0.20.1/apps/proxy/config.py`

**Änderungen:**
1. Konstanten anpassen
2. get_proxy_settings() erweitern
3. Getter-Methoden hinzufügen

**Checklist:**
- [ ] MAX_RETRIES: 3 → 2
- [ ] MAX_STREAM_SWITCHES: 10 → 200
- [ ] 5 neue Settings in get_proxy_settings()
- [ ] get_max_retries() Methode
- [ ] get_url_switch_timeout() Methode
- [ ] get_max_stream_switches() Methode
- [ ] get_connection_timeout() Methode
- [ ] get_failover_grace_period() Methode
- [ ] TSConfig.get_failover_grace_period() Methode

### 2.2 Profile Failover System (45 Min)

**Datei:** `Dispatcharr-0.20.1/apps/proxy/ts_proxy/stream_manager.py`

**Änderungen:**
1. __init__ erweitern
2. tried_combinations tracking
3. Alternate streams Logik

**Checklist:**
- [ ] self.current_profile_id = None hinzufügen
- [ ] self.tried_combinations = set() statt tried_stream_ids
- [ ] tried_combinations.add() bei Stream-Wechsel
- [ ] get_alternate_streams() mit Profile-Support

**Datei:** `Dispatcharr-0.20.1/apps/proxy/ts_proxy/url_utils.py`

**Checklist:**
- [ ] get_stream_info_for_profile() implementieren
- [ ] get_alternate_streams() erweitern

### 2.3 HTTP Proxy Support (45 Min)

**Datei:** `Dispatcharr-0.20.1/apps/m3u/models.py`

**Checklist:**
- [ ] proxy Feld zu M3UAccount hinzufügen
- [ ] Migration erstellen

**Datei:** `Dispatcharr-0.20.1/core/models.py`

**Checklist:**
- [ ] build_command() mit proxy Parameter
- [ ] FFmpeg -http_proxy injection

**Datei:** `Dispatcharr-0.20.1/apps/proxy/ts_proxy/http_streamer.py`

**Checklist:**
- [ ] __init__ mit proxy Parameter
- [ ] session.proxies setzen

**Datei:** `Dispatcharr-0.20.1/apps/m3u/serializers.py`

**Checklist:**
- [ ] proxy Feld zu Serializer hinzufügen

### 2.4 Basic Authentication (30 Min)

**Datei:** `Dispatcharr-0.20.1/apps/output/views.py`

**Checklist:**
- [ ] get_basic_auth_user() implementieren
- [ ] require_basic_auth() implementieren
- [ ] m3u_output() anpassen
- [ ] epg_output() anpassen

---

## 🎨 PHASE 3: FRONTEND

### 3.1 Constants erweitern (15 Min)

**Datei:** `Dispatcharr-0.20.1/frontend/src/constants.js`

**Checklist:**
- [ ] max_retries zu PROXY_SETTINGS_OPTIONS
- [ ] url_switch_timeout zu PROXY_SETTINGS_OPTIONS
- [ ] max_stream_switches zu PROXY_SETTINGS_OPTIONS
- [ ] connection_timeout zu PROXY_SETTINGS_OPTIONS
- [ ] failover_grace_period zu PROXY_SETTINGS_OPTIONS

### 3.2 Proxy Settings Form (30 Min)

**Datei:** `Dispatcharr-0.20.1/frontend/src/components/forms/settings/ProxySettingsForm.jsx`

**Checklist:**
- [ ] isNumericField() erweitern (5 neue)
- [ ] getNumericFieldMax() erweitern (5 neue)

### 3.3 Proxy Settings Utils (15 Min)

**Datei:** `Dispatcharr-0.20.1/frontend/src/utils/forms/settings/ProxySettingsFormUtils.js`

**Checklist:**
- [ ] getProxySettingDefaults() erweitern (5 neue)

### 3.4 M3U Form (30 Min)

**Datei:** `Dispatcharr-0.20.1/frontend/src/components/forms/M3U.jsx`

**Checklist:**
- [ ] proxy zu initialValues
- [ ] proxy zu setValues
- [ ] Proxy TextField hinzufügen

---

## 🧪 PHASE 4: TESTING

### 4.1 Backend Tests (30 Min)

**Config Tests:**
```bash
cd Dispatcharr-0.20.1
python manage.py shell

# Test Config
from apps.proxy.config import BaseConfig, TSConfig
settings = BaseConfig.get_proxy_settings()
print(settings)  # Sollte 10 Settings haben

# Test Getter
print(BaseConfig.get_max_retries())  # 2
print(BaseConfig.get_max_stream_switches())  # 200
```

**Migration Tests:**
```bash
# Migration erstellen
python manage.py makemigrations m3u

# Migration anwenden
python manage.py migrate

# Prüfen
python manage.py shell
from apps.m3u.models import M3UAccount
M3UAccount._meta.get_field('proxy')  # Sollte existieren
```

### 4.2 Frontend Tests (30 Min)

**Settings Form:**
- [ ] Proxy Settings öffnen
- [ ] Alle 10 Settings sichtbar
- [ ] Defaults korrekt
- [ ] Validierung funktioniert

**M3U Form:**
- [ ] M3U Account erstellen
- [ ] Proxy-Feld sichtbar
- [ ] Proxy speichern
- [ ] Proxy laden

### 4.3 Integration Tests (Optional)

**Profile Failover:**
- [ ] Stream mit mehreren Profilen
- [ ] Failover auslösen
- [ ] Logs prüfen für tried_combinations

**HTTP Proxy:**
- [ ] M3U mit Proxy konfigurieren
- [ ] Stream starten
- [ ] Proxy-Verwendung in Logs

**Basic Auth:**
```bash
# M3U Endpoint
curl -u username:password http://localhost:8000/output/m3u/1/

# EPG Endpoint
curl -u username:password http://localhost:8000/output/epg/1/
```

---

## 📚 PHASE 5: DOKUMENTATION

### 5.1 Patch erstellen (15 Min)

```bash
cd Dispatcharr-0.20.1
git diff > ../dispatcharr_enhancements_v0.20.1.patch
```

### 5.2 Installer Script (15 Min)

**Datei:** `apply_dispatcharr_enhancements_v0.20.1.sh`

Basierend auf v0.19.0 Script anpassen.

### 5.3 Dokumentation erstellen

**Dateien:**
- [ ] INSTALLATION_COMPLETE_v0.20.1.md
- [ ] PATCH_NOTES_v0.20.1.md
- [ ] VERIFICATION_CHECKLIST_v0.20.1.md

---

## ⚠️ TROUBLESHOOTING

### Problem: Migration schlägt fehl
**Lösung:**
```bash
python manage.py migrate --fake m3u zero
python manage.py migrate m3u
```

### Problem: Frontend zeigt Settings nicht
**Lösung:**
- Browser Cache leeren
- npm run build neu ausführen
- collectstatic neu ausführen

### Problem: Proxy funktioniert nicht
**Lösung:**
- Logs prüfen
- Proxy-Format prüfen (http://host:port)
- Netzwerk-Zugriff prüfen

---

## ✅ FINALE CHECKLISTE

### Backend
- [ ] Config System: 10 Settings
- [ ] Profile Failover: tried_combinations
- [ ] HTTP Proxy: Migration + Code
- [ ] Basic Auth: Endpoints geschützt

### Frontend
- [ ] Constants: 10 Settings
- [ ] Proxy Settings Form: Validierung
- [ ] M3U Form: Proxy-Feld

### Testing
- [ ] Config Tests bestanden
- [ ] Migration erfolgreich
- [ ] Frontend funktioniert
- [ ] Integration Tests OK

### Dokumentation
- [ ] Patch erstellt
- [ ] Installer erstellt
- [ ] Docs geschrieben

---

## 🎉 ERFOLG!

Nach Abschluss aller Phasen haben Sie:

✅ Dispatcharr v0.20.1 mit allen v0.19.0 Enhancements  
✅ Alle neuen v0.20.1 Features (API Keys, Integrations, etc.)  
✅ Maximale Ausfallsicherheit (343 Kombinationen)  
✅ Vollständige Konfigurierbarkeit (10 Settings)  
✅ HTTP Proxy Support  
✅ Basic Authentication  

**Dispatcharr v0.20.1 Enhanced ist bereit für den Produktionseinsatz!**

---

**Erstellt:** 2026-03-02  
**Version:** 1.0.0  
**Geschätzter Zeitaufwand:** 4-6 Stunden
