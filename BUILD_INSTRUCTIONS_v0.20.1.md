# Dispatcharr v0.20.1 - Build & Installation Instructions

**Version:** v0.20.1 mit allen v0.19.0 Features  
**Datum:** 2026-03-02

---

## ÜBERSICHT

Diese Anleitung zeigt, wie du Dispatcharr v0.20.1 mit allen integrierten v0.19.0 Features baust und installierst.

**Integrierte Features:**
1. ✅ Profile Failover System (343 Kombinationen)
2. ✅ Universal HTTP Proxy Support (FFmpeg + HTTP Proxy)
3. ✅ Basic Authentication (M3U/EPG Endpoints)
4. ✅ Extended Timeout Configuration (10 Settings)
5. ✅ Ghost-Client Auto-Cleanup
6. ✅ Migration für Proxy Feld
7. ✅ Alle Frontend-Änderungen
8. ✅ Docker drf-spectacular Fix

---

## VORAUSSETZUNGEN

- Docker installiert
- Docker Compose installiert
- Mindestens 4 GB freier Speicher für Images
- Internetverbindung für Dependencies

---

## SCHRITT 1: DOCKER IMAGES BAUEN

### 1.1 Base-Image bauen

Das Base-Image enthält alle Python-Dependencies und System-Pakete.

```bash
cd Dispatcharr-0.20.1

# Base-Image bauen (dauert ca. 10-15 Minuten)
docker build -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .

# Image mit ghcr.io Tag versehen (für Dockerfile-Kompatibilität)
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
```

**Wichtig:** 
- Das Base-Image muss zuerst gebaut werden, da das Haupt-Image darauf aufbaut
- Der `docker tag` Befehl erstellt einen zusätzlichen Namen für das Image, damit das Dockerfile es findet

### 1.2 Haupt-Image bauen

Das Haupt-Image enthält die Anwendung und das Frontend.

```bash
# Haupt-Image bauen (dauert ca. 5-10 Minuten)
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .
```

### 1.3 Build-Argumente Erklärung

- `BASE_TAG=base` - Verwendet das lokal gebaute Base-Image
- `REPO_OWNER=sbeimel` - Dein Docker Hub Username
- `REPO_NAME=dispatcharr` - Repository Name

---

## SCHRITT 2: DOCKER COMPOSE KONFIGURIEREN

### 2.1 docker-compose.yml anpassen

Öffne `docker/docker-compose.yml` und ändere die Image-Referenzen:

```yaml
services:
  web:
    image: sbeimel/dispatcharr:0.20.1  # Geändert von ghcr.io/dispatcharr/dispatcharr:latest
    # ... rest bleibt gleich

  celery:
    image: sbeimel/dispatcharr:0.20.1  # Geändert von ghcr.io/dispatcharr/dispatcharr:latest
    # ... rest bleibt gleich
```

### 2.2 Alternativ: docker-compose.override.yml erstellen

Statt die Original-Datei zu ändern, kannst du eine Override-Datei erstellen:

```bash
cd docker
cat > docker-compose.override.yml << 'EOF'
services:
  web:
    image: sbeimel/dispatcharr:0.20.1
  
  celery:
    image: sbeimel/dispatcharr:0.20.1
EOF
```

---

## SCHRITT 3: CONTAINER STARTEN

```bash
cd docker

# Alte Container stoppen und entfernen
docker-compose down

# Neue Container starten
docker-compose up -d

# Logs anschauen
docker-compose logs -f
```

---

## SCHRITT 4: VERIFIKATION

### 4.1 Container Status prüfen

```bash
docker-compose ps
```

Alle Container sollten "Up" sein.

### 4.2 Logs prüfen

```bash
# Web-Container Logs
docker-compose logs web

# Celery-Container Logs
docker-compose logs celery
```

Suche nach:
- ✅ `Dispatcharr version: 0.20.1`
- ✅ `database system is ready to accept connections`
- ✅ `uwsgi started with PID`
- ❌ KEINE `ModuleNotFoundError: No module named 'drf_spectacular'`

### 4.3 Web-Interface testen

Öffne im Browser:
- **Hauptseite:** http://localhost:9191
- **API Docs:** http://localhost:9191/api/schema/swagger-ui/

### 4.4 Features testen

1. **Proxy Settings:** Einstellungen → Proxy Settings
   - Prüfe, ob alle 10 Felder vorhanden sind:
     - URL Switch Timeout (20s)
     - Max Stream Switches (200)
     - Max Retries (2)
     - Connection Timeout
     - Read Timeout
     - Retry Delay
     - Retry Backoff Factor
     - Retry Max Delay
     - Failover Grace Period
     - Ghost Client Cleanup Interval

2. **M3U Account Proxy:** M3U Accounts → Edit
   - Prüfe, ob "HTTP Proxy" Feld vorhanden ist

3. **Basic Auth:** M3U/EPG Endpoints
   - Teste mit: `http://username:password@localhost:9191/m3u/...`

---

## TROUBLESHOOTING

### Problem: "Error response from daemon: No such image: ghcr.io/sbeimel/dispatcharr:base"

**Ursache:** Base-Image wurde gebaut, aber nicht mit dem richtigen Tag versehen.

**Lösung:**
```bash
# Image mit ghcr.io Tag versehen
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base

# Dann Haupt-Image bauen
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .
```

### Problem: "failed to authorize: failed to fetch anonymous token: 403 Forbidden"

**Ursache:** Docker versucht das Base-Image von GitHub Container Registry zu holen, findet es aber nicht lokal.

**Lösung:** Siehe Problem oben - Image mit `docker tag` versehen.

### Problem: "ModuleNotFoundError: No module named 'drf_spectacular'"

**Ursache:** Base-Image wurde nicht neu gebaut oder alte Version verwendet.

**Lösung:**
```bash
# Base-Image neu bauen mit --no-cache
docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .

# Haupt-Image neu bauen
docker build --no-cache -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .

# Container neu starten
cd docker
docker-compose down
docker-compose up -d
```

### Problem: "Error response from daemon: No such image: sbeimel/dispatcharr:base"

**Ursache:** Base-Image wurde nicht gebaut.

**Lösung:** Siehe Schritt 1.1

### Problem: Frontend zeigt alte Version

**Ursache:** Browser-Cache oder Frontend nicht neu gebaut.

**Lösung:**
```bash
# Hard Refresh im Browser: Ctrl+Shift+R (Windows/Linux) oder Cmd+Shift+R (Mac)

# Oder Container neu bauen mit --no-cache
docker build --no-cache -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .
```

### Problem: Migration Fehler

**Ursache:** Datenbank enthält alte Struktur.

**Lösung:**
```bash
# In Container einloggen
docker exec -it dispatcharr_web bash

# Migrationen manuell ausführen
cd /app
python manage.py migrate

# Container neu starten
exit
docker-compose restart web
```

---

## SCHNELL-REFERENZ

### Kompletter Build-Prozess (Copy & Paste)

```bash
# In Dispatcharr-0.20.1 Verzeichnis wechseln
cd Dispatcharr-0.20.1

# Base-Image bauen
docker build -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .

# Image mit ghcr.io Tag versehen
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base

# Haupt-Image bauen
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .

# docker-compose.override.yml erstellen
cd docker
cat > docker-compose.override.yml << 'EOF'
services:
  web:
    image: sbeimel/dispatcharr:0.20.1
  
  celery:
    image: sbeimel/dispatcharr:0.20.1
EOF

# Container starten
docker-compose down
docker-compose up -d

# Logs anschauen
docker-compose logs -f web
```

### Rebuild ohne Cache (bei Problemen)

```bash
cd Dispatcharr-0.20.1

# Alles neu bauen
docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
docker build --no-cache -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .

# Container neu starten
cd docker
docker-compose down
docker-compose up -d
```

---

## NÄCHSTE SCHRITTE

Nach erfolgreicher Installation:

1. **Backup erstellen:** Sichere deine Datenbank und Konfiguration
2. **M3U Accounts konfigurieren:** Füge deine IPTV-Quellen hinzu
3. **Proxy Settings anpassen:** Konfiguriere Timeouts und Failover
4. **EPG Sources hinzufügen:** Füge EPG-Quellen hinzu
5. **Channels organisieren:** Erstelle Channel Groups und Profile

---

## SUPPORT

Bei Problemen:
1. Prüfe die Logs: `docker-compose logs -f`
2. Prüfe Container Status: `docker-compose ps`
3. Prüfe Disk Space: `docker system df`
4. Lies die Troubleshooting-Sektion oben

---

## CHANGELOG v0.20.1

**Neue Features (von v0.19.0):**
- Profile Failover System mit 343 Kombinationen
- Universal HTTP Proxy Support für FFmpeg und HTTP Proxy Profiles
- Basic Authentication für M3U/EPG Endpoints
- 10 erweiterte Timeout/Retry Settings
- Ghost-Client Auto-Cleanup
- Proxy Feld in M3U Accounts

**Bugfixes:**
- `get_alternate_streams()` gibt jetzt ALLE Profile zurück (nicht nur eines)
- `get_stream_info_for_profile()` Funktion hinzugefügt
- `current_profile_id` Parameter zu `get_alternate_streams()` hinzugefügt
- Proxy Support in `_establish_transcode_connection()` hinzugefügt
- drf-spectacular Dependency Fix im Docker Build

**Technische Details:**
- 14 Dateien geändert
- 4 kritische Bugfixes
- Vollständig kompatibel mit v0.20.1
- Alle Features aus v0.19.0 integriert
