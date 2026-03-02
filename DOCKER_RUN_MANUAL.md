# Dispatcharr v0.20.1 - Manueller Docker Run

Wenn du `docker run` statt `docker-compose` verwendest, musst du diese Environment-Variablen setzen.

---

## ALL-IN-ONE MODE (Empfohlen für Standalone)

Alles in einem Container: PostgreSQL, Redis, Celery, Web

```bash
docker run -d \
  --name Dispatcharr-old \
  --restart unless-stopped \
  -p 9191:9191 \
  -v /mnt/user/appdata/dispatcharr:/data \
  -e DISPATCHARR_ENV=aio \
  -e REDIS_HOST=localhost \
  -e CELERY_BROKER_URL=redis://localhost:6379/0 \
  -e DISPATCHARR_LOG_LEVEL=info \
  sbeimel/dispatcharr:0.20.1
```

### Minimale Environment-Variablen (AIO Mode):

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `DISPATCHARR_ENV` | `aio` | All-in-One Mode (PostgreSQL + Redis im Container) |
| `REDIS_HOST` | `localhost` | Redis läuft im gleichen Container |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery Broker URL |
| `DISPATCHARR_LOG_LEVEL` | `info` | Log Level (debug, info, warning, error) |

---

## MODULAR MODE (Separate Container)

Wenn du separate Container für PostgreSQL und Redis hast:

```bash
docker run -d \
  --name Dispatcharr-old \
  --restart unless-stopped \
  -p 9191:9191 \
  -v /mnt/user/appdata/dispatcharr:/data \
  -e DISPATCHARR_ENV=modular \
  -e POSTGRES_HOST=192.168.1.100 \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_DB=dispatcharr \
  -e POSTGRES_USER=dispatch \
  -e POSTGRES_PASSWORD=secret \
  -e REDIS_HOST=192.168.1.101 \
  -e REDIS_PORT=6379 \
  -e DISPATCHARR_LOG_LEVEL=info \
  sbeimel/dispatcharr:0.20.1
```

### Erforderliche Environment-Variablen (Modular Mode):

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `DISPATCHARR_ENV` | `modular` | Modular Mode (externe DB + Redis) |
| `POSTGRES_HOST` | IP/Hostname | PostgreSQL Server Adresse |
| `POSTGRES_PORT` | `5432` | PostgreSQL Port |
| `POSTGRES_DB` | `dispatcharr` | Datenbank Name |
| `POSTGRES_USER` | `dispatch` | Datenbank User |
| `POSTGRES_PASSWORD` | `secret` | Datenbank Passwort |
| `REDIS_HOST` | IP/Hostname | Redis Server Adresse |
| `REDIS_PORT` | `6379` | Redis Port |
| `DISPATCHARR_LOG_LEVEL` | `info` | Log Level |

---

## OPTIONALE ENVIRONMENT-VARIABLEN

### Hardware Acceleration

```bash
# Intel/AMD GPU (VA-API)
docker run -d \
  --name Dispatcharr-old \
  --device /dev/dri:/dev/dri \
  --group-add video \
  --group-add render \
  -e LIBVA_DRIVER_NAME=iHD \
  ... # rest der Parameter
```

### Process Priority

```bash
# Höhere Priorität für Streaming
docker run -d \
  --name Dispatcharr-old \
  --cap-add SYS_NICE \
  -e UWSGI_NICE_LEVEL=-5 \
  -e CELERY_NICE_LEVEL=5 \
  ... # rest der Parameter
```

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `UWSGI_NICE_LEVEL` | `0` | uWSGI/Streaming Priorität (-20 bis 19) |
| `CELERY_NICE_LEVEL` | `5` | Celery/Background Priorität (-20 bis 19) |

### Legacy CPU Support

```bash
# Für alte CPUs (ca. 2009)
docker run -d \
  --name Dispatcharr-old \
  -e USE_LEGACY_NUMPY=true \
  ... # rest der Parameter
```

### Redis Authentication

```bash
# Wenn Redis Passwort benötigt
docker run -d \
  --name Dispatcharr-old \
  -e REDIS_PASSWORD=your_password \
  -e REDIS_USER=your_username \
  ... # rest der Parameter
```

---

## KOMPLETTES BEISPIEL (AIO mit allen Optionen)

```bash
docker run -d \
  --name Dispatcharr-old \
  --restart unless-stopped \
  -p 9191:9191 \
  -v /mnt/user/appdata/dispatcharr:/data \
  --device /dev/dri:/dev/dri \
  --group-add video \
  --group-add render \
  --cap-add SYS_NICE \
  -e DISPATCHARR_ENV=aio \
  -e REDIS_HOST=localhost \
  -e CELERY_BROKER_URL=redis://localhost:6379/0 \
  -e DISPATCHARR_LOG_LEVEL=info \
  -e UWSGI_NICE_LEVEL=-5 \
  -e CELERY_NICE_LEVEL=5 \
  -e LIBVA_DRIVER_NAME=iHD \
  sbeimel/dispatcharr:0.20.1
```

---

## WICHTIGE HINWEISE

### 1. Volume Mount

```bash
-v /mnt/user/appdata/dispatcharr:/data
```

Das `/data` Verzeichnis enthält:
- `/data/db` - PostgreSQL Datenbank (nur AIO Mode)
- `/data/jwt` - Django Secret Key
- `/data/scripts` - Custom Scripts
- Logs und temporäre Dateien

### 2. Port Mapping

```bash
-p 9191:9191
```

Dispatcharr läuft auf Port 9191. Du kannst den Host-Port ändern:
```bash
-p 8080:9191  # Zugriff über http://localhost:8080
```

### 3. Container Name

```bash
--name Dispatcharr-old
```

Ändere den Namen nach Bedarf. Wichtig für `docker exec`, `docker logs`, etc.

### 4. Restart Policy

```bash
--restart unless-stopped
```

Container startet automatisch nach Reboot, außer du stoppst ihn manuell.

---

## CONTAINER MANAGEMENT

### Container starten/stoppen

```bash
# Starten
docker start Dispatcharr-old

# Stoppen
docker stop Dispatcharr-old

# Neu starten
docker restart Dispatcharr-old

# Logs anschauen
docker logs -f Dispatcharr-old

# In Container einloggen
docker exec -it Dispatcharr-old bash
```

### Container neu erstellen (nach Image-Update)

```bash
# Alten Container stoppen und löschen
docker stop Dispatcharr-old
docker rm Dispatcharr-old

# Neuen Container mit gleichem Befehl erstellen
docker run -d \
  --name Dispatcharr-old \
  ... # gleiche Parameter wie oben
```

---

## TROUBLESHOOTING

### Container startet nicht

```bash
# Logs prüfen
docker logs Dispatcharr-old

# Häufige Probleme:
# - POSTGRES_HOST nicht erreichbar (Modular Mode)
# - REDIS_HOST nicht erreichbar (Modular Mode)
# - Volume Mount Permissions
# - Port 9191 bereits belegt
```

### Datenbank-Verbindung testen

```bash
# In Container einloggen
docker exec -it Dispatcharr-old bash

# PostgreSQL testen (Modular Mode)
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB

# Redis testen
redis-cli -h $REDIS_HOST ping
```

### Permissions Probleme

```bash
# Volume Permissions prüfen
ls -la /mnt/user/appdata/dispatcharr

# Sollte dem Container User gehören (UID 99 oder 1000)
# Falls nicht:
chown -R 99:100 /mnt/user/appdata/dispatcharr
```

---

## MIGRATION VON ALTER VERSION

Wenn du von einer älteren Version updatest:

```bash
# 1. Backup erstellen
docker exec Dispatcharr-old pg_dump -U dispatch dispatcharr > backup.sql

# 2. Alten Container stoppen
docker stop Dispatcharr-old

# 3. Volume sichern
cp -r /mnt/user/appdata/dispatcharr /mnt/user/appdata/dispatcharr.backup

# 4. Neuen Container mit v0.20.1 starten
docker run -d \
  --name Dispatcharr-old \
  ... # gleiche Parameter wie vorher

# 5. Logs prüfen
docker logs -f Dispatcharr-old

# Migration läuft automatisch beim Start
```

---

## UNRAID SPEZIFISCH

Wenn du Unraid verwendest:

```bash
# Pfade anpassen für Unraid
-v /mnt/user/appdata/dispatcharr:/data

# GPU Support (Intel)
--device /dev/dri:/dev/dri

# Netzwerk
--net=bridge  # oder --net=host für Host-Netzwerk
```

### Unraid Template Variablen

Für Unraid Community Applications Template:

```xml
<Config Name="Data" Target="/data" Default="/mnt/user/appdata/dispatcharr" Mode="rw" Description="Data directory" Type="Path" Display="always" Required="true" Mask="false">/mnt/user/appdata/dispatcharr</Config>

<Config Name="Port" Target="9191" Default="9191" Mode="tcp" Description="Web UI Port" Type="Port" Display="always" Required="true" Mask="false">9191</Config>

<Config Name="DISPATCHARR_ENV" Target="DISPATCHARR_ENV" Default="aio" Mode="" Description="Deployment mode (aio or modular)" Type="Variable" Display="always" Required="true" Mask="false">aio</Config>

<Config Name="DISPATCHARR_LOG_LEVEL" Target="DISPATCHARR_LOG_LEVEL" Default="info" Mode="" Description="Log level (debug, info, warning, error)" Type="Variable" Display="always" Required="false" Mask="false">info</Config>
```

---

## ZUSAMMENFASSUNG

**Minimale Konfiguration (AIO Mode):**
```bash
docker run -d --name Dispatcharr-old -p 9191:9191 \
  -v /mnt/user/appdata/dispatcharr:/data \
  -e DISPATCHARR_ENV=aio \
  -e REDIS_HOST=localhost \
  -e CELERY_BROKER_URL=redis://localhost:6379/0 \
  sbeimel/dispatcharr:0.20.1
```

Das war's! Alle v0.19.0 Features sind integriert und funktionieren.
