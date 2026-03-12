#!/bin/bash

STREAM_HASH="7366ad15aa36885ccea633ad512551201948d48bb82b765c49fd311f561d6459"
STREAM_ID="849527"
PROFILE_ID="488"

echo "=== Debug Stream Hash Issue ==="
echo "Stream Hash: $STREAM_HASH"
echo "Stream ID: $STREAM_ID"
echo "Profile ID: $PROFILE_ID"
echo ""

echo "1. Prüfe Metadata unter Stream-Hash:"
docker exec -it redis redis-cli HGETALL "ts_proxy:channel:${STREAM_HASH}:metadata"
echo ""

echo "2. Prüfe channel_stream Key:"
docker exec -it redis redis-cli GET "channel_stream:${STREAM_HASH}"
echo ""

echo "3. Prüfe stream_profile Key mit Stream ID:"
docker exec -it redis redis-cli GET "stream_profile:${STREAM_ID}"
echo ""

echo "4. Prüfe profile_connections:"
docker exec -it redis redis-cli GET "profile_connections:${PROFILE_ID}"
echo ""

echo "5. Prüfe ALLE profile_connections:"
docker exec -it redis redis-cli KEYS "profile_connections:*"
for key in $(docker exec -it redis redis-cli KEYS "profile_connections:*" | tr -d '\r'); do
    value=$(docker exec -it redis redis-cli GET "$key" | tr -d '\r')
    echo "$key = $value"
done
echo ""

echo "=== Analyse ==="
echo "Problem: Stream-Hash wird als channel_id verwendet"
echo "Metadata wird unter: ts_proxy:channel:{stream_hash}:metadata gespeichert"
echo "stream_profile wird unter: stream_profile:{stream_id} gespeichert"
echo ""
echo "Wenn _clean_redis_keys() aufgerufen wird:"
echo "1. Sucht nach Metadata unter stream_hash ✅"
echo "2. Findet stream_id und profile_id ✅"
echo "3. SOLLTE Counter dekrementieren ✅"
echo "4. SOLLTE Keys löschen ✅"
echo ""
echo "Wenn das NICHT passiert:"
echo "→ Metadata wurde nicht gefunden"
echo "→ Oder stream_id/profile_id fehlen in Metadata"
echo "→ Oder Reihenfolge ist immer noch falsch"
