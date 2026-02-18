# 🔧 MIGRATION FIX - 0020_add_proxy_field

## Problem

```
NodeNotFoundError: Migration m3u.0020_add_proxy_field dependencies reference nonexistent parent node ('m3u', '0019_m3uaccount_priority')
```

## Ursache

Die Migration `0020_add_proxy_field.py` verweist auf `0019_m3uaccount_priority`, aber in deiner v0.19.0 Installation existiert nur bis `0018_add_profile_custom_properties`.

## Lösung

Die Migration wurde bereits korrigiert:

**VORHER:**
```python
dependencies = [
    ('m3u', '0019_m3uaccount_priority'),  # FALSCH!
]
```

**NACHHER:**
```python
dependencies = [
    ('m3u', '0018_add_profile_custom_properties'),  # KORREKT!
]
```

## Nächste Schritte

```bash
cd ~/Dispatcharr

# Docker Image neu bauen
docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile .

# Container neu starten
cd docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml up -d

# Logs prüfen
docker compose -f docker-compose.aio.yml logs -f
```

## Verifikation

Nach dem Neustart solltest du sehen:
```
✅ Postgres started
✅ nginx started
✅ Migrations applied successfully
✅ Dispatcharr is ready
```

---

**Status:** ✅ BEHOBEN

Die Datei `apps/m3u/migrations/0020_add_proxy_field.py` wurde korrigiert und verweist jetzt auf die korrekte Parent-Migration.
