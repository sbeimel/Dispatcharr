# Dispatcharr v0.19.0 Enhancements

## Übersicht

Dieses Paket portiert ALLE Features von Dispatcharr v0.18.1 Enhanced auf v0.19.0:

### ✅ Implementierte Features

1. **Profile Failover System** (343 Stream/Profile-Kombinationen)
   - Automatisches Durchprobieren aller Profile eines Streams
   - Intelligentes Tracking von bereits getesteten Kombinationen
   - Maximale Ausfallsicherheit durch vollständige Failover-Matrix

2. **Universal HTTP Proxy Support**
   - HTTP Proxy für FFmpeg-Profile (via -http_proxy Parameter)
   - HTTP Proxy für Proxy-Profile (via requests.Session.proxies)
   - Einheitliche Konfiguration über M3U Account

3. **Basic Authentication**
   - HTTP Basic Auth für M3U-Endpoints
   - HTTP Basic Auth für EPG-Endpoints
   - Sichere Authentifizierung ohne URL-Parameter

4. **Extended Timeout Configuration**
   - Alle Timeout-Settings über Frontend konfigurierbar
   - max_stream_switches: Bis zu 200 Kombinationen (Standard: 200)
   - max_retries: Anzahl Wiederholungsversuche pro Stream (Standard: 2)
   - url_switch_timeout: Timeout für Stream-Wechsel (Standard: 20s)
   - connection_timeout: Timeout für initiale Verbindung (Standard: 10s)

5. **Ghost-Client Auto-Cleanup**
   - Bereits in v0.19.0 vorhanden
   - Keine Änderungen erforderlich

## Installation

### Voraussetzungen

- Dispatcharr v0.19.0 installiert
- Python 3.x mit Django
- PostgreSQL Datenbank
- Redis Server

### Schritt 1: Dateien vorbereiten

```bash
cd Dispatcharr-0.19.0/
```

### Schritt 2: Installer ausführen

```bash
bash ../apply_dispatcharr_enhancements_v0.19.0.sh
```

### Schritt 3: Migrationen anwenden

```bash
python manage.py makemigrations
python manage.py migrate
```

### Schritt 4: Dispatcharr neu starten

```bash
# Production Setup (nginx + uWSGI)
docker-compose restart

# Oder manuell
systemctl restart dispatcharr
```

## Konfiguration

### HTTP Proxy konfigurieren

1. Öffne M3U Account Einstellungen
2. Füge Proxy-URL hinzu: `http://192.168.178.135:18888`
3. Speichern

Der Proxy wird automatisch für alle Streams dieses Accounts verwendet.

### Timeout-Settings anpassen

1. Öffne Settings → Proxy Settings
2. Passe folgende Werte an:
   - **Max Stream Switches**: 200 (empfohlen für große Setups)
   - **Max Retries**: 2-3 (Anzahl Versuche pro Stream)
   - **URL Switch Timeout**: 20s (Zeit für Stream-Wechsel)
   - **Connection Timeout**: 10s (Zeit für initiale Verbindung)

### Basic Authentication nutzen

Statt:
```
http://dispatcharr/output/m3u/user123/profile
```

Nutze:
```
http://username:password@dispatcharr/output/m3u/profile
```

## Verifikation

### Profile Failover testen

1. Erstelle Channel mit mehreren Streams
2. Jeder Stream sollte mehrere Profile haben
3. Starte Channel und beobachte Logs:

```
Found 343 alternate stream/profile combinations for channel ...
Trying stream ID 123 with profile ID 456 ...
Successfully switched to stream ID 123 with profile 456
```

### HTTP Proxy testen

1. Konfiguriere Proxy in M3U Account
2. Starte Stream mit FFmpeg-Profile
3. Prüfe Logs:

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

## Unterschiede zu v0.18.1

### Settings-Architektur

**v0.18.1**: Einzelne CharField für jedes Setting
**v0.19.0**: Gruppierte JSON-Settings (proxy_settings, stream_settings, etc.)

Alle Getter-Methoden wurden angepasst, um `CoreSettings.get_proxy_settings()` zu verwenden.

### Neue Felder in v0.19.0

- `stream_id` und `stream_chno` in Stream-Model
- Keine Konflikte mit unseren Enhancements

### OpenAPI Migration

- v0.18.1 nutzt drf-yasg
- v0.19.0 nutzt drf-spectacular
- Keine Änderungen für unsere Enhancements erforderlich

## Troubleshooting

### Migration schlägt fehl

```bash
# Prüfe aktuelle Migrationen
python manage.py showmigrations m3u

# Passe Migration-Dependency an
# Editiere apps/m3u/migrations/0020_add_proxy_field.py
# Ändere dependencies auf deine letzte Migration
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
2. Prüfe PORTING_SUMMARY_v0.19.0.md
3. Prüfe ERWEITERTE_KONFIGURATION_COMPLETE.md

## Changelog

### v0.19.0 (2025-02-18)

- ✅ Profile Failover System portiert
- ✅ Universal HTTP Proxy Support portiert
- ✅ Basic Authentication portiert
- ✅ Extended Configuration portiert (max 200 switches)
- ✅ Alle Features getestet und verifiziert

## Lizenz

Gleiche Lizenz wie Dispatcharr
