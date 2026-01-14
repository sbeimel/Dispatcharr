# Installation der Enhancements für Dispatcharr 0.17.0

## ✅ Status: Alle Enhancements wurden bereits angewendet!

Dieser Dispatcharr-0.17.0 Ordner enthält bereits alle angewendeten Enhancements. Du musst **keine** Patches mehr anwenden.

## 🎯 Was wurde gemacht?

Alle Features aus folgenden Bereichen wurden direkt in den Code integriert:

1. ✅ **Profile Failover** - Automatischer Wechsel zwischen Stream-Profilen
2. ✅ **HTTP Proxy Support** - Proxy-Unterstützung für FFmpeg
3. ✅ **Configuration Enhancements** - Erweiterte Konfigurationsoptionen
4. ✅ **Basic Authentication** - HTTP Basic Auth für M3U Endpoints

## 🚀 Nächste Schritte

### 1. Datenbank Migration (WICHTIG!)

```bash
cd Dispatcharr-0.17.0
python manage.py makemigrations m3u
python manage.py migrate m3u
```

### 2. Dispatcharr starten

```bash
# Mit systemd
systemctl restart dispatcharr

# Mit Docker
docker-compose restart

# Manuell
python manage.py runserver
```

### 3. Konfiguration

#### HTTP Proxy konfigurieren:
1. Gehe zu M3U Accounts
2. Bearbeite einen Account
3. Füge Proxy URL hinzu (z.B. `http://proxy.example.com:8080`)
4. Speichern

#### Basic Auth testen:
```bash
curl -u username:password http://localhost:9191/output/m3u/
```

## 📋 Vergleich mit Original

### Geänderte Dateien:
- `apps/proxy/config.py` - ✅ Erweitert
- `apps/m3u/serializers.py` - ✅ Proxy-Feld hinzugefügt
- `apps/proxy/ts_proxy/stream_manager.py` - ✅ Profile Failover + Proxy
- `apps/proxy/ts_proxy/url_utils.py` - ✅ Neue Funktionen
- `apps/output/views.py` - ✅ Basic Auth

### Neue Funktionen:
- `get_stream_info_for_profile()` in url_utils.py
- `get_basic_auth_user()` in output/views.py
- `require_basic_auth()` in output/views.py

## 🔍 Überprüfung

### Prüfe ob Enhancements aktiv sind:

```bash
# 1. Prüfe Config
grep "MAX_RETRIES = 2" apps/proxy/config.py

# 2. Prüfe Proxy Support
grep "proxy" apps/m3u/serializers.py

# 3. Prüfe Profile Failover
grep "current_profile_id" apps/proxy/ts_proxy/stream_manager.py

# 4. Prüfe Basic Auth
grep "get_basic_auth_user" apps/output/views.py
```

Alle Befehle sollten Treffer liefern! ✅

## 📚 Dokumentation

Siehe `ENHANCEMENTS_APPLIED.md` für:
- Detaillierte Liste aller Änderungen
- Technische Details
- Tricky Stellen für Updates
- Bekannte Einschränkungen

## 🆘 Support

Bei Problemen:
1. Prüfe `ENHANCEMENTS_APPLIED.md` für Details
2. Schaue in die Original Patch-Datei
3. Prüfe Logs: `tail -f /var/log/dispatcharr/dispatcharr.log`

## ⚠️ Wichtig

- **Backup erstellen** vor dem ersten Start!
- **Datenbank Migration** nicht vergessen!
- **Redis** muss laufen für Profile Failover
- **FFmpeg** muss installiert sein für Proxy Support
