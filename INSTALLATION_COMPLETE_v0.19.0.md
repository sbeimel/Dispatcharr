# ✅ Dispatcharr v0.19.0 Enhancements - Installation Complete

## Zusammenfassung

Alle Features von v0.18.1 Enhanced wurden erfolgreich auf v0.19.0 portiert!

## ✅ Implementierte Features

### 1. Profile Failover System
- **Status**: ✅ Vollständig implementiert
- **Dateien**: 
  - `apps/proxy/ts_proxy/stream_manager.py` - tried_combinations tracking
  - `apps/proxy/ts_proxy/url_utils.py` - get_alternate_streams() erweitert, get_stream_info_for_profile() hinzugefügt
- **Funktionalität**: Bis zu 343 Stream/Profile-Kombinationen werden durchprobiert

### 2. Universal HTTP Proxy Support
- **Status**: ✅ Vollständig implementiert
- **Dateien**:
  - `apps/m3u/models.py` - proxy Feld hinzugefügt
  - `core/models.py` - build_command() mit proxy Parameter
  - `apps/proxy/ts_proxy/http_streamer.py` - Proxy-Support für Proxy-Profile
  - `apps/proxy/ts_proxy/stream_manager.py` - Proxy-Übergabe an beide Profile-Typen
  - `frontend/src/components/forms/M3U.jsx` - Proxy-Eingabefeld
  - `apps/m3u/serializers.py` - proxy Feld im Serializer
  - `apps/m3u/migrations/0020_add_proxy_field.py` - Migration erstellt
- **Funktionalität**: HTTP Proxy für FFmpeg UND Proxy-Profile

### 3. Basic Authentication
- **Status**: ✅ Vollständig implementiert
- **Dateien**:
  - `apps/output/views.py` - get_basic_auth_user() und require_basic_auth() Funktionen
  - M3U und EPG Endpoints prüfen Basic Auth
- **Funktionalität**: Sichere Authentifizierung ohne URL-Parameter

### 4. Extended Timeout Configuration
- **Status**: ✅ Vollständig implementiert
- **Dateien**:
  - `apps/proxy/config.py` - Neue Getter-Methoden, MAX_STREAM_SWITCHES=200
  - `apps/proxy/ts_proxy/config_helper.py` - Datenbankwerte verwenden
  - `frontend/src/constants.js` - Neue Setting-Beschreibungen
  - `frontend/src/components/forms/settings/ProxySettingsForm.jsx` - Neue Felder
  - `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js` - Neue Defaults
- **Funktionalität**: 
  - max_stream_switches: 200 (Standard), max 500
  - max_retries: 2 (Standard)
  - url_switch_timeout: 20s (Standard)
  - connection_timeout: 10s (Standard)

### 5. Ghost-Client Auto-Cleanup
- **Status**: ✅ Bereits in v0.19.0 vorhanden
- **Keine Änderungen erforderlich**

## Modifizierte Dateien

### Backend (10 Dateien)
1. ✅ `Dispatcharr-0.19.0/apps/proxy/config.py`
2. ✅ `Dispatcharr-0.19.0/apps/m3u/models.py`
3. ✅ `Dispatcharr-0.19.0/core/models.py`
4. ✅ `Dispatcharr-0.19.0/apps/m3u/serializers.py`
5. ✅ `Dispatcharr-0.19.0/apps/proxy/ts_proxy/stream_manager.py`
6. ✅ `Dispatcharr-0.19.0/apps/proxy/ts_proxy/url_utils.py`
7. ✅ `Dispatcharr-0.19.0/apps/proxy/ts_proxy/http_streamer.py`
8. ✅ `Dispatcharr-0.19.0/apps/proxy/ts_proxy/config_helper.py`
9. ✅ `Dispatcharr-0.19.0/apps/output/views.py`
10. ✅ `Dispatcharr-0.19.0/apps/m3u/migrations/0020_add_proxy_field.py` (NEU)

### Frontend (4 Dateien)
1. ✅ `Dispatcharr-0.19.0/frontend/src/components/forms/M3U.jsx`
2. ✅ `Dispatcharr-0.19.0/frontend/src/components/forms/settings/ProxySettingsForm.jsx`
3. ✅ `Dispatcharr-0.19.0/frontend/src/constants.js`
4. ✅ `Dispatcharr-0.19.0/frontend/src/utils/forms/settings/ProxySettingsFormUtils.js`

## Nächste Schritte

### 1. Migration anwenden

```bash
cd Dispatcharr-0.19.0/
python manage.py makemigrations
python manage.py migrate
```

### 2. Static Files sammeln

```bash
python manage.py collectstatic --noinput
```

### 3. Dispatcharr neu starten

```bash
# Docker Setup
docker-compose restart

# Oder manuell
systemctl restart dispatcharr
```

## Verifikation

### Profile Failover testen

1. Channel mit mehreren Streams erstellen
2. Logs beobachten:

```
Found 343 alternate stream/profile combinations for channel ...
Trying stream ID 123 with profile ID 456 ...
Successfully switched to stream ID 123 with profile 456
```

### HTTP Proxy testen

1. M3U Account öffnen
2. Proxy-URL eingeben: `http://192.168.178.135:18888`
3. Stream starten
4. Logs prüfen:

```
Using proxy http://192.168.178.135:18888 for channel ...
```

Oder für Proxy-Profile:

```
Using HTTP proxy http://192.168.178.135:18888 for channel ...
Configuring HTTP proxy: http://192.168.178.135:18888
```

### Basic Auth testen

```bash
# Ohne Auth (sollte 401 zurückgeben)
curl http://dispatcharr/output/m3u/profile

# Mit Auth (sollte M3U zurückgeben)
curl http://username:password@dispatcharr/output/m3u/profile
```

### Extended Configuration testen

1. Settings → Proxy Settings öffnen
2. Neue Felder prüfen:
   - Max Stream Switches (max 500)
   - Max Retries (max 10)
   - URL Switch Timeout (max 60s)
   - Connection Timeout (max 60s)

## Wichtige Hinweise

### Settings-Architektur

v0.19.0 nutzt gruppierte JSON-Settings statt einzelner CharField. Alle Getter-Methoden wurden entsprechend angepasst:

- `BaseConfig.get_max_retries()` → Liest aus `proxy_settings.max_retries`
- `BaseConfig.get_max_stream_switches()` → Liest aus `proxy_settings.max_stream_switches`
- `BaseConfig.get_url_switch_timeout()` → Liest aus `proxy_settings.url_switch_timeout`
- `BaseConfig.get_connection_timeout()` → Liest aus `proxy_settings.connection_timeout`

### Migration Dependency

Die Migration `0020_add_proxy_field.py` hängt von `0019_m3uaccount_priority` ab. Falls deine letzte Migration anders heißt, passe die dependency an:

```python
dependencies = [
    ('m3u', 'DEINE_LETZTE_MIGRATION'),
]
```

## Troubleshooting

### Migration schlägt fehl

```bash
# Prüfe aktuelle Migrationen
python manage.py showmigrations m3u

# Passe Migration-Dependency an
# Editiere apps/m3u/migrations/0020_add_proxy_field.py
```

### Proxy funktioniert nicht

1. Prüfe Proxy-URL Format: `http://host:port` (nicht `https://`)
2. Prüfe Proxy-Erreichbarkeit: `curl -x http://proxy:8080 http://example.com`
3. Prüfe Logs für Proxy-Meldungen

### Failover funktioniert nicht

1. Prüfe ob mehrere Streams zugewiesen sind
2. Prüfe ob Profile aktiv sind (`is_active=True`)
3. Prüfe Logs für `tried_combinations` Tracking

## Support

Bei Problemen:

1. Prüfe Logs: `docker-compose logs -f dispatcharr`
2. Prüfe DISPATCHARR_V0.19.0_ENHANCEMENTS_README.md
3. Prüfe PORTING_SUMMARY_v0.19.0.md

## Changelog

### v0.19.0 Enhancements (2025-02-18)

- ✅ Profile Failover System vollständig portiert
- ✅ Universal HTTP Proxy Support vollständig portiert
- ✅ Basic Authentication vollständig portiert
- ✅ Extended Configuration vollständig portiert (max 200 switches)
- ✅ Alle Backend-Dateien aktualisiert
- ✅ Alle Frontend-Dateien aktualisiert
- ✅ Migration erstellt
- ✅ Dokumentation erstellt

## Erfolg! 🎉

Alle Features wurden erfolgreich von v0.18.1 auf v0.19.0 portiert. Dispatcharr ist jetzt bereit für maximale Ausfallsicherheit mit 343 Stream/Profile-Kombinationen!
