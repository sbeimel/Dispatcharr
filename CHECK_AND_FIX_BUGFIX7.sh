#!/bin/bash
# Bugfix #7 Verification and Fix Script
# Datum: 2026-03-12

set -e

echo "=========================================="
echo "Bugfix #7 - Verification & Fix"
echo "=========================================="
echo ""

# Schritt 1: Prüfe ob Bugfix #7 im Code vorhanden ist
echo "Schritt 1: Prüfe Code-Änderungen..."
echo ""

if grep -q "Released stream after failed attempt" apps/proxy/ts_proxy/views.py; then
    echo "✅ Bugfix #7 Code ist in views.py vorhanden"
else
    echo "❌ Bugfix #7 Code ist NICHT in views.py vorhanden!"
    echo ""
    echo "LÖSUNG: Führe install_v0.20.1_enhancements.sh aus:"
    echo "  chmod +x install_v0.20.1_enhancements.sh"
    echo "  ./install_v0.20.1_enhancements.sh"
    exit 1
fi

if grep -q "redis_client.expire(profile_connections_key, 3600)" apps/channels/models.py; then
    echo "✅ TTL Code ist in models.py vorhanden"
else
    echo "❌ TTL Code ist NICHT in models.py vorhanden!"
    echo ""
    echo "LÖSUNG: Führe install_v0.20.1_enhancements.sh aus:"
    echo "  chmod +x install_v0.20.1_enhancements.sh"
    echo "  ./install_v0.20.1_enhancements.sh"
    exit 1
fi

echo ""
echo "✅ Code-Änderungen sind vorhanden"
echo ""

# Schritt 2: Prüfe Redis Counter
echo "=========================================="
echo "Schritt 2: Prüfe Redis Counter"
echo "=========================================="
echo ""

# Finde Redis Container
REDIS_CONTAINER=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -n 1)

if [ -z "$REDIS_CONTAINER" ]; then
    echo "❌ Redis Container nicht gefunden!"
    echo "Bitte prüfe: docker ps | grep redis"
    exit 1
fi

echo "Redis Container: $REDIS_CONTAINER"
echo ""

# Zeige alle profile_connections Keys
echo "Aktuelle Profile Connection Counter:"
echo "-------------------------------------------"
docker exec -it $REDIS_CONTAINER redis-cli KEYS "profile_connections:*" | while read key; do
    if [ ! -z "$key" ]; then
        value=$(docker exec -it $REDIS_CONTAINER redis-cli GET "$key" | tr -d '\r')
        echo "  $key = $value"
    fi
done
echo ""

# Schritt 3: Reset Counter
echo "=========================================="
echo "Schritt 3: Reset Profile Connection Counter"
echo "=========================================="
echo ""

read -p "Möchtest du alle Counter zurücksetzen? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setze Counter zurück..."
    docker exec -it $REDIS_CONTAINER redis-cli KEYS "profile_connections:*" | while read key; do
        if [ ! -z "$key" ]; then
            docker exec -it $REDIS_CONTAINER redis-cli DEL "$key" > /dev/null
            echo "  ✅ Gelöscht: $key"
        fi
    done
    echo ""
    echo "✅ Alle Counter zurückgesetzt"
else
    echo "Counter wurden NICHT zurückgesetzt"
fi

echo ""

# Schritt 4: Prüfe ob Container neu gestartet werden muss
echo "=========================================="
echo "Schritt 4: Container Status"
echo "=========================================="
echo ""

# Finde Dispatcharr Container
DISPATCHARR_CONTAINER=$(docker ps --filter "name=dispatcharr" --filter "name=web" --format "{{.Names}}" | head -n 1)

if [ -z "$DISPATCHARR_CONTAINER" ]; then
    echo "❌ Dispatcharr Container nicht gefunden!"
    echo "Bitte prüfe: docker ps | grep dispatcharr"
    exit 1
fi

echo "Dispatcharr Container: $DISPATCHARR_CONTAINER"
echo ""

# Prüfe wann Container gestartet wurde
CONTAINER_STARTED=$(docker inspect -f '{{.State.StartedAt}}' $DISPATCHARR_CONTAINER)
echo "Container gestartet: $CONTAINER_STARTED"
echo ""

# Prüfe wann views.py zuletzt geändert wurde
VIEWS_MODIFIED=$(stat -c %y apps/proxy/ts_proxy/views.py 2>/dev/null || stat -f "%Sm" apps/proxy/ts_proxy/views.py)
echo "views.py geändert: $VIEWS_MODIFIED"
echo ""

echo "⚠️  WICHTIG: Container muss neu gestartet werden, damit Änderungen aktiv werden!"
echo ""

read -p "Möchtest du die Container jetzt neu starten? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starte Container neu..."
    cd docker
    docker-compose restart web celery
    echo ""
    echo "✅ Container neu gestartet"
    echo ""
    echo "Warte 10 Sekunden auf Container-Start..."
    sleep 10
    echo ""
    echo "Container Logs (letzte 20 Zeilen):"
    echo "-------------------------------------------"
    docker-compose logs --tail=20 web
else
    echo "Container wurden NICHT neu gestartet"
    echo ""
    echo "⚠️  Bitte starte die Container manuell:"
    echo "  cd docker"
    echo "  docker-compose restart web celery"
fi

echo ""
echo "=========================================="
echo "Nächste Schritte"
echo "=========================================="
echo ""
echo "1. Teste einen Stream im Browser"
echo "2. Prüfe die Logs auf 'Released stream after failed attempt':"
echo "   docker-compose logs -f web | grep 'Released stream'"
echo ""
echo "3. Wenn du die Meldung siehst: ✅ Bugfix #7 ist aktiv!"
echo "   Wenn nicht: ❌ Container wurden nicht neu gestartet"
echo ""
