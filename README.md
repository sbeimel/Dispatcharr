# 🚀 Dispatcharr Enhancements - AIO Integration

Einfache Integration der Enhancements in das All-in-One Docker-Setup.

## 📁 Was ist enthalten

- ✅ `apply_enhancements_simple.sh` - **Sichere Version** ohne komplexe Failover-Änderungen
- ✅ `docker/Dockerfile` - **Bereits erweitert** mit Enhancement-Integration
- ✅ `docker/entrypoint.sh` - **Bereits erweitert** mit automatischer Migration
- ✅ `docker/docker-compose.aio.yml` - **Bereits erweitert** für AIO-Setup

## 🎯 Features

- ✅ **Profile Failover**: Automatischer Wechsel zu nächstem Profil bei Stream-Fehlern
- ✅ **Basic Authentication**: HTTP Basic Auth für M3U/EPG Output
- ✅ **FFmpeg Proxy**: Proxy-Unterstützung pro M3U-Account
- ✅ **Reduzierte Retries**: Von 3 auf 2 Versuche (konfigurierbar)
- ✅ **Verbesserte Fehlerbehandlung**: Detaillierte Protokollierung
- ✅ **Automatische Migration**: Wird beim Container-Start angewendet

## 🐳 AIO Integration (Bereits erledigt!)

### **Das Dockerfile ist intelligent umstrukturiert!** ✅

**Neue Build-Reihenfolge für Frontend-Kompatibilität:**

```dockerfile
# 1. Enhancement-Stage: Enhancements anwenden
FROM node:24 AS enhancement-stage
COPY . /app
COPY apply_enhancements.sh /app/
RUN ./apply_enhancements.sh

# 2. Frontend-Builder: Mit Enhancements bauen
FROM node:24 AS frontend-builder
COPY --from=enhancement-stage /app/frontend /app/frontend
RUN npm install && npm run build

# 3. Final: Alles zusammenfügen
FROM ghcr.io/dispatcharr/dispatcharr:base AS final
COPY --from=enhancement-stage /app /app
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
```

**Das löst das Frontend-Problem:**
- ✅ Enhancements werden **vor** dem Frontend-Build angewendet
- ✅ Frontend wird **mit** Proxy-Feld kompiliert
- ✅ Alle Enhancements sind im finalen Image enthalten

### **Die AIO docker-compose.yml ist bereits erweitert!** ✅

```yaml
# === DISPATCHARR WITH ENHANCEMENTS ===
# Uncomment to build with enhancements locally:
# build:
#   context: ..
#   dockerfile: docker/Dockerfile

environment:
  # === ENHANCEMENT SETTINGS ===
  - ENHANCEMENT_MAX_RETRIES=2
  - ENHANCEMENT_URL_SWITCH_TIMEOUT=8
  - ENHANCEMENT_FAILOVER_GRACE_PERIOD=20
```

## 🚀 Verwendung

### **Option 1: Lokaler Build mit Enhancements**
```bash
# 1. Script ins Projekt-Root kopieren
cp apply_enhancements_simple.sh /path/to/dispatcharr/

# 2. AIO docker-compose.yml bearbeiten - Build-Sektion aktivieren:
# Uncomment diese Zeilen:
# build:
#   context: ..
#   dockerfile: docker/Dockerfile

# 3. Mit Enhancements bauen und starten
cd docker
docker-compose -f docker-compose.aio.yml up --build -d
```

### **Option 2: Pre-built Image + Manuelle Anwendung**
```bash
# 1. Standard AIO starten
cd docker
docker-compose -f docker-compose.aio.yml up -d

# 2. Enhancements manuell anwenden
docker cp apply_enhancements_simple.sh dispatcharr:/app/
docker exec -it dispatcharr /app/apply_enhancements_simple.sh
docker exec -it dispatcharr python manage.py migrate m3u
docker-compose restart
```

### **Option 3: Eigenes Enhanced Image bauen**
```bash
# 1. Image mit Enhancements bauen
docker build -f docker/Dockerfile -t dispatcharr-enhanced .

# 2. AIO docker-compose.yml anpassen:
# image: dispatcharr-enhanced  # statt ghcr.io/dispatcharr/dispatcharr:latest

# 3. Starten
cd docker
docker-compose -f docker-compose.aio.yml up -d
```

## 🧪 Testen

### **1. Proxy-Funktionalität**
- Öffne `http://localhost:9191`
- Gehe zu M3U-Accounts
- Proxy-Feld sollte verfügbar sein
- Trage ein: `http://proxy:8080`

### **2. Basic Authentication**
```bash
# Mit Authentifizierung
curl -u username:password http://localhost:9191/output/m3u/

# Ohne Authentifizierung (sollte 401 zurückgeben)
curl http://localhost:9191/output/m3u/
```

### **3. Stream Failover**
```bash
# Logs überwachen
docker logs -f dispatcharr | grep -i "failover\|retry\|switch"
```

## 📋 Build-Ausgabe

Beim Build siehst du:
```
=== Applying Dispatcharr Enhancements ===
1. Updating MAX_RETRIES...
2. Adding proxy field to M3UAccount...
3. Creating migration file...
4. Adding Basic Auth to output views...
5. Updating frontend M3U form...
6. Enhancing failover logic...
✓ All enhancements applied successfully!
```

Beim Start siehst du:
```
🔧 Applying Dispatcharr enhancement migrations...
✅ Enhancement migrations completed
```

## 🔧 Konfiguration

Die AIO-Konfiguration unterstützt diese Umgebungsvariablen:

```yaml
environment:
  # Enhancement-Einstellungen
  - ENHANCEMENT_MAX_RETRIES=2              # Retry-Versuche (1-10)
  - ENHANCEMENT_URL_SWITCH_TIMEOUT=8       # Stream-Switch Timeout (1-60s)
  - ENHANCEMENT_FAILOVER_GRACE_PERIOD=20   # Failover Grace Period (1-120s)
```

## 🚨 Wichtige Hinweise

- ✅ **AIO-Ready**: Perfekt in das All-in-One Setup integriert
- ✅ **Automatisch**: Alles wird beim Build/Start automatisch angewendet
- ✅ **Konfigurierbar**: Alle Einstellungen über Umgebungsvariablen
- ✅ **Flexibel**: Mehrere Installationsoptionen verfügbar

## 🎉 Das war's!

**Die AIO-Integration ist bereits fertig - einfach verwenden!** 🚀

```bash
# Für lokalen Build mit Enhancements:
cd docker
# docker-compose.aio.yml bearbeiten (build aktivieren)
docker-compose -f docker-compose.aio.yml up --build -d

# Oder für schnelle manuelle Anwendung:
docker-compose -f docker-compose.aio.yml up -d
docker exec -it dispatcharr /app/apply_enhancements.sh
docker-compose restart
```