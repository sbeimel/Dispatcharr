# Docker Build - Quick Reference

**Datum:** 2026-03-12  
**Version:** v0.20.1

---

## Option 1: Automatisches Script (EMPFOHLEN)

```bash
cd /mnt/user/Downloads/eigne/Dispatcharr-0.20.1
chmod +x ../DOCKER_BUILD_COMMANDS.sh
../DOCKER_BUILD_COMMANDS.sh
```

Das Script führt alle Schritte automatisch aus und prüft auf Fehler.

---

## Option 2: Manuelle Befehle

### Schritt 1: Base-Image bauen

```bash
cd /mnt/user/Downloads/eigne/Dispatcharr-0.20.1

docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .
```

**Dauer:** 10-15 Minuten

### Schritt 2: Tag für ghcr.io erstellen

```bash
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
```

**WICHTIG:** Dieser Schritt ist notwendig, damit das Dockerfile das Base-Image findet!

### Schritt 3: Haupt-Image bauen

```bash
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .
```

**Dauer:** 5-10 Minuten

### Schritt 4: docker-compose.override.yml erstellen

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

### Schritt 5: Container starten

```bash
docker-compose down
docker-compose up -d
```

### Schritt 6: Logs prüfen

```bash
docker-compose logs -f web
```

Suche nach:
- ✅ `Dispatcharr version: 0.20.1`
- ✅ `uwsgi started with PID`
- ❌ KEINE `ModuleNotFoundError`

---

## Häufige Fehler

### Fehler: "No such image: ghcr.io/sbeimel/dispatcharr:base"

**Ursache:** Schritt 2 (docker tag) wurde vergessen!

**Lösung:**
```bash
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
```

Dann Schritt 3 wiederholen.

### Fehler: "ModuleNotFoundError: No module named 'drf_spectacular'"

**Ursache:** Base-Image wurde nicht neu gebaut oder alte Version verwendet.

**Lösung:**
```bash
# Alles neu bauen
docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
docker build --no-cache -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .

cd docker
docker-compose down
docker-compose up -d
```

---

## Verifikation

### Images prüfen

```bash
docker images | grep dispatcharr
```

Sollte zeigen:
```
sbeimel/dispatcharr          0.20.1    <ID>    <TIME>    <SIZE>
sbeimel/dispatcharr          base      <ID>    <TIME>    <SIZE>
ghcr.io/sbeimel/dispatcharr  base      <ID>    <TIME>    <SIZE>
```

### Container Status prüfen

```bash
cd docker
docker-compose ps
```

Alle Container sollten "Up" sein.

### Web-Interface testen

Öffne im Browser:
- http://localhost:9191

---

## Deine Befehle (KORRIGIERT)

**Was du geschrieben hast:**
```bash
docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .
```

**Was fehlt:**
```bash
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base
```

**Korrekte Reihenfolge:**
```bash
# 1. Base-Image bauen
docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .

# 2. Tag erstellen (WICHTIG!)
docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base

# 3. Haupt-Image bauen
docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .
```

---

## Zusammenfassung

✅ **Schritt 1:** Base-Image bauen  
✅ **Schritt 2:** Tag für ghcr.io erstellen (NICHT VERGESSEN!)  
✅ **Schritt 3:** Haupt-Image bauen  
✅ **Schritt 4:** docker-compose.override.yml erstellen  
✅ **Schritt 5:** Container starten  
✅ **Schritt 6:** Logs prüfen  

**Gesamtdauer:** 15-25 Minuten

---

**Erstellt:** 2026-03-12  
**Version:** 1.0

