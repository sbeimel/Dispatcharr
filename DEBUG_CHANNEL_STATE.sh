#!/bin/bash

CHANNEL_UUID="511b13e3-13d3-496c-933c-a108b79b276b"

echo "=== Debug Channel State ==="
echo "Channel UUID: $CHANNEL_UUID"
echo ""

echo "1. Prüfe Redis Keys für diesen Channel:"
docker exec -it redis redis-cli KEYS "*${CHANNEL_UUID}*"
echo ""

echo "2. Prüfe channel_stream Key:"
docker exec -it redis redis-cli GET "channel_stream:${CHANNEL_UUID}"
echo ""

echo "3. Prüfe stream_profile Key (wenn channel_stream existiert):"
STREAM_ID=$(docker exec -it redis redis-cli GET "channel_stream:${CHANNEL_UUID}" | tr -d '\r')
if [ -n "$STREAM_ID" ]; then
    echo "Stream ID: $STREAM_ID"
    docker exec -it redis redis-cli GET "stream_profile:${STREAM_ID}"
else
    echo "Kein channel_stream Key gefunden"
fi
echo ""

echo "4. Prüfe alle profile_connections:"
docker exec -it redis redis-cli KEYS "profile_connections:*"
echo ""

echo "5. Prüfe Werte:"
for key in $(docker exec -it redis redis-cli KEYS "profile_connections:*" | tr -d '\r'); do
    value=$(docker exec -it redis redis-cli GET "$key" | tr -d '\r')
    echo "$key = $value"
done
echo ""

echo "6. Prüfe Channel Metadata:"
docker exec -it redis redis-cli HGETALL "ts_proxy:channel:${CHANNEL_UUID}:metadata"
echo ""

echo "=== Analyse ==="
echo "Wenn stream_profile Key NICHT existiert:"
echo "→ release_stream() gibt auf ohne Counter zu dekrementieren!"
echo "→ Das ist das Problem!"
