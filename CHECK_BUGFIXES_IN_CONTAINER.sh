#!/bin/bash

echo "=== Prüfe ob Bugfixes im Container sind ==="
echo ""

echo "1. Bugfix #7 in views.py (Zeile ~196):"
docker exec -it Dispatcharr grep -A 5 "Released stream after failed attempt" /app/apps/proxy/ts_proxy/views.py | head -10
echo ""

echo "2. Bugfix #7 TTL in models.py (Zeile ~478):"
docker exec -it Dispatcharr grep -A 2 "expire(profile_connections_key, 3600)" /app/apps/channels/models.py
echo ""

echo "3. Bugfix #9 in stream_generator.py (Zeile ~444):"
docker exec -it Dispatcharr grep -A 5 "BUGFIX #9" /app/apps/proxy/ts_proxy/stream_generator.py | head -10
echo ""

echo "4. Bugfix #10 in server.py (Zeile ~1338):"
docker exec -it Dispatcharr grep -A 5 "BUGFIX #10" /app/apps/proxy/ts_proxy/server.py | head -10
echo ""

echo "=== Redis Counter prüfen ==="
echo ""
docker exec -it redis redis-cli KEYS "profile_connections:*"
echo ""
docker exec -it redis redis-cli GET profile_connections:224
echo ""

echo "=== Wenn Bugfixes NICHT gefunden werden ==="
echo "→ Container wurde NICHT neu gebaut!"
echo "→ Führe aus: docker-compose down && docker-compose up -d --build"
