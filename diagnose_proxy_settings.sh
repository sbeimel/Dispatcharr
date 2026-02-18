#!/bin/bash

echo "=========================================="
echo "Dispatcharr Proxy Settings Diagnose"
echo "=========================================="
echo ""

# Prüfe ob Container läuft
if ! docker ps | grep -q dispatcharr; then
    echo "❌ Dispatcharr Container läuft nicht!"
    echo "Starte mit: docker compose -f docker-compose.aio.yml up -d"
    exit 1
fi

echo "✅ Container läuft"
echo ""

# Prüfe core/models.py im Container
echo "Prüfe core/models.py im Container..."
docker exec dispatcharr grep -A 15 "def get_proxy_settings" /app/core/models.py | head -20

echo ""
echo "=========================================="
echo "Erwartete Ausgabe sollte enthalten:"
echo "  \"max_retries\": 2,"
echo "  \"url_switch_timeout\": 20,"
echo "  \"max_stream_switches\": 200,"
echo "  \"connection_timeout\": 10,"
echo "  \"failover_grace_period\": 20,"
echo "=========================================="
echo ""

# Prüfe API-Antwort
echo "Prüfe API-Antwort..."
echo "Rufe http://localhost:8000/api/settings/proxy/ auf..."
echo ""

# Versuche API-Aufruf (ohne Auth)
curl -s http://localhost:8000/api/settings/proxy/ | python3 -m json.tool 2>/dev/null || echo "API-Aufruf fehlgeschlagen (Auth erforderlich?)"

echo ""
echo "=========================================="
echo "DIAGNOSE ABGESCHLOSSEN"
echo "=========================================="
echo ""
echo "Wenn die neuen Felder NICHT in der Container-Datei sind:"
echo "  → Docker Image neu bauen:"
echo "     cd ~/Dispatcharr"
echo "     docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile ."
echo "     cd docker"
echo "     docker compose -f docker-compose.aio.yml down"
echo "     docker compose -f docker-compose.aio.yml up -d"
echo ""
