# Dispatcharr v0.19.0 Enhancements - Patch Dokumentation

## Übersicht

Dieses Paket enthält alle notwendigen Dateien, um Dispatcharr v0.19.0 mit den Enhanced Features von v0.18.1 zu erweitern.

## Dateien im Paket

### Patch & Installer
- ✅ `dispatcharr_enhancements_v0.19.0.patch` - Hauptpatch-Datei
- ✅ `apply_dispatcharr_enhancements_v0.19.0.sh` - Automatischer Installer
- ✅ `PATCH_NOTES_v0.19.0.md` - Detaillierte Patch-Notizen

### Dokumentation
- ✅ `INSTALLATION_COMPLETE_v0.19.0.md` - Vollständige Installationsanleitung
- ✅ `DISPATCHARR_V0.19.0_ENHANCEMENTS_README.md` - Feature-Dokumentation
- ✅ `PORTING_SUMMARY_v0.19.0.md` - Technische Portierungs-Details
- ✅ `README_PATCH_v0.19.0.md` - Diese Datei

## Schnellstart

### Option 1: Automatische Installation (Empfohlen)

```bash
cd Dispatcharr-0.19.0/
bash ../apply_dispatcharr_enhancements_v0.19.0.sh
```

Das Script führt automatisch aus:
1. Backup erstellen
2. Migrationen anwenden
3. Static Files sammeln
4. Verifikation

### Option 2: Manuelle Patch-Anwendung

```bash
cd Dispatcharr-0.19.0/
patch -p1 < ../dispatcharr_enhancements_v0.19.0.patch
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
docker-compose restart
```

### Option 3: Dateien bereits modifiziert

Falls du die Änderungen bereits direkt in den Dateien vorgenommen hast:

```bash
cd Dispatcharr-0.19.0/
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
docker-compose restart
```

## Was wird geändert?

### Backend (10 Dateien)
1. `apps/proxy/config.py` - Neue Getter-Methoden, MAX_STREAM_SWITCHES=200
2. `apps/m3u/models.py` - Proxy-Feld hinzugefügt
3. `core/models.py` - build_command() mit Proxy-Parameter
4. `apps/m3u/serializers.py` - Proxy-Feld im Serializer
5. `apps/proxy/ts_proxy/stream_manager.py` - Profile Failover + Proxy
6. `apps/proxy/ts_proxy/url_utils.py` - get_alternate_streams() + neue Funktion
7. `apps/proxy/ts_proxy/http_streamer.py` - Proxy-Support
8. `apps/proxy/ts_proxy/config_helper.py` - Datenbankwerte verwenden
9. `apps/output/views.py` - Basic Authentication
10. `apps/m3u/migrations/0020_add_proxy_field.py` - Migration (NEU)

### Frontend (4 Dateien)
1. `frontend/src/components/forms/M3U.jsx` - Proxy-Eingabefeld
2. `frontend/src/components/forms/settings/ProxySettingsForm.jsx` - Neue Felder
3. `frontend/src/constants.js` - Neue Setting-Beschreibungen
4. `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js` - Neue Defaults

## Wichtige Hinweise

### stream_manager.py und url_utils.py

Diese beiden Dateien haben sehr umfangreiche Änderungen (~250 Zeilen). Der Patch enthält die wichtigsten Änderungen, aber für die vollständige Implementierung siehe:

- `PATCH_NOTES_v0.19.0.md` - Detaillierte Änderungen
- `INSTALLATION_COMPLETE_v0.19.0.md` - Schritt-für-Schritt Anleitung

### Migration Dependency

Die Migration `0020_add_proxy_field.py` hängt von `0019_m3uaccount_priority` ab. Falls deine letzte Migration anders heißt:

```python
# Editiere: apps/m3u/migrations/0020_add_proxy_field.py
dependencies = [
    ('m3u', 'DEINE_LETZTE_MIGRATION'),  # Hier anpassen!
]
```

Finde deine letzte Migration:
```bash
ls -la apps/m3u/migrations/ | tail -5
```

## Verifikation

### Nach der Installation prüfen:

```bash
# Django Checks
python manage.py check

# Migration Status
python manage.py showmigrations m3u

# Test Migration (Dry-Run)
python manage.py migrate --plan
```

### Features testen:

1. **Profile Failover**
   ```
   Logs: "Found 343 alternate stream/profile combinations"
   ```

2. **HTTP Proxy**
   ```
   M3U Account → Proxy: http://proxy:8080
   Logs: "Using proxy http://proxy:8080 for channel"
   ```

3. **Basic Auth**
   ```bash
   curl http://user:pass@dispatcharr/output/m3u/profile
   ```

4. **Extended Config**
   ```
   Settings → Proxy Settings
   Max Stream Switches: 200 (max 500)
   ```

## Troubleshooting

### Patch schlägt fehl

```bash
# Prüfe welche Dateien bereits geändert wurden
patch -p1 --dry-run < ../dispatcharr_enhancements_v0.19.0.patch

# Wende nur bestimmte Teile an
patch -p1 < ../dispatcharr_enhancements_v0.19.0.patch --forward
```

### Migration schlägt fehl

```bash
# Prüfe aktuelle Migrationen
python manage.py showmigrations m3u

# Fake Migration (wenn Feld bereits existiert)
python manage.py migrate m3u 0020 --fake

# Oder Migration neu erstellen
rm apps/m3u/migrations/0020_add_proxy_field.py
python manage.py makemigrations m3u
```

### Frontend-Änderungen nicht sichtbar

```bash
# Static Files neu sammeln
python manage.py collectstatic --noinput --clear

# Browser-Cache leeren
# Oder Incognito-Modus verwenden
```

## Rückgängig machen

### Patch rückgängig machen:

```bash
cd Dispatcharr-0.19.0/
patch -p1 -R < ../dispatcharr_enhancements_v0.19.0.patch
```

### Migration rückgängig machen:

```bash
python manage.py migrate m3u 0019
rm apps/m3u/migrations/0020_add_proxy_field.py
```

### Aus Backup wiederherstellen:

```bash
# Backup wurde vom Installer erstellt
ls -la dispatcharr_backup_*

# Wiederherstellen
cp -r dispatcharr_backup_YYYYMMDD_HHMMSS/* .
```

## Support & Dokumentation

### Vollständige Dokumentation:
- `INSTALLATION_COMPLETE_v0.19.0.md` - Installation & Verifikation
- `DISPATCHARR_V0.19.0_ENHANCEMENTS_README.md` - Features & Konfiguration
- `PORTING_SUMMARY_v0.19.0.md` - Technische Details
- `PATCH_NOTES_v0.19.0.md` - Detaillierte Änderungen

### Bei Problemen:

1. Prüfe Logs: `docker-compose logs -f dispatcharr`
2. Prüfe Django: `python manage.py check`
3. Prüfe Migrationen: `python manage.py showmigrations`
4. Siehe Troubleshooting-Sektion oben

## Changelog

### v1.0.0 (2025-02-18)

**Neue Features:**
- ✅ Profile Failover System (343 Kombinationen)
- ✅ Universal HTTP Proxy Support
- ✅ Basic Authentication
- ✅ Extended Configuration (max 200 switches)

**Geänderte Dateien:**
- 10 Backend-Dateien
- 4 Frontend-Dateien
- 1 neue Migration

**Zeilen geändert:**
- ~500 Zeilen hinzugefügt
- ~50 Zeilen entfernt
- ~250 Zeilen modifiziert

## Lizenz

Gleiche Lizenz wie Dispatcharr

## Credits

Basiert auf:
- Dispatcharr v0.19.0 (Original)
- dispatcharr_enhancements_v0.18.1_extended.patch

Portiert und erweitert für v0.19.0 Architektur.
