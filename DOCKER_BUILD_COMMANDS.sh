#!/bin/bash
# Dispatcharr v0.20.1 - Docker Build Script
# Datum: 2026-03-12

set -e  # Stop on error

echo "=========================================="
echo "Dispatcharr v0.20.1 - Docker Build"
echo "=========================================="
echo ""

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -f "docker/DispatcharrBase" ]; then
    echo "❌ FEHLER: docker/DispatcharrBase nicht gefunden!"
    echo "Bitte führe dieses Script im Dispatcharr-0.20.1 Verzeichnis aus:"
    echo "  cd /mnt/user/Downloads/eigne/Dispatcharr-0.20.1"
    echo "  bash ../DOCKER_BUILD_COMMANDS.sh"
    exit 1
fi

echo "✅ Verzeichnis OK"
echo ""

# Schritt 1: Base-Image bauen
echo "=========================================="
echo "Schritt 1/4: Base-Image bauen"
echo "=========================================="
echo "Dies dauert ca. 10-15 Minuten..."
echo ""

docker build --no-cache -t sbeimel/dispatcharr:base -f docker/DispatcharrBase .

if [ $? -ne 0 ]; then
    echo "❌ FEHLER: Base-Image Build fehlgeschlagen!"
    exit 1
fi

echo ""
echo "✅ Base-Image erfolgreich gebaut"
echo ""

# Schritt 2: Tag für ghcr.io erstellen
echo "=========================================="
echo "Schritt 2/4: ghcr.io Tag erstellen"
echo "=========================================="
echo ""

docker tag sbeimel/dispatcharr:base ghcr.io/sbeimel/dispatcharr:base

if [ $? -ne 0 ]; then
    echo "❌ FEHLER: Tag konnte nicht erstellt werden!"
    exit 1
fi

echo "✅ Tag erfolgreich erstellt"
echo ""

# Schritt 3: Haupt-Image bauen
echo "=========================================="
echo "Schritt 3/4: Haupt-Image bauen"
echo "=========================================="
echo "Dies dauert ca. 5-10 Minuten..."
echo ""

docker build -t sbeimel/dispatcharr:0.20.1 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr .

if [ $? -ne 0 ]; then
    echo "❌ FEHLER: Haupt-Image Build fehlgeschlagen!"
    exit 1
fi

echo ""
echo "✅ Haupt-Image erfolgreich gebaut"
echo ""

# Schritt 4: Images anzeigen
echo "=========================================="
echo "Schritt 4/4: Gebaute Images"
echo "=========================================="
echo ""

docker images | grep -E "REPOSITORY|sbeimel/dispatcharr|ghcr.io/sbeimel/dispatcharr"

echo ""
echo "=========================================="
echo "✅ BUILD ERFOLGREICH!"
echo "=========================================="
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. docker-compose.override.yml erstellen:"
echo "   cd docker"
echo "   cat > docker-compose.override.yml << 'EOF'"
echo "   services:"
echo "     web:"
echo "       image: sbeimel/dispatcharr:0.20.1"
echo "     celery:"
echo "       image: sbeimel/dispatcharr:0.20.1"
echo "   EOF"
echo ""
echo "2. Container starten:"
echo "   docker-compose down"
echo "   docker-compose up -d"
echo ""
echo "3. Logs prüfen:"
echo "   docker-compose logs -f web"
echo ""
