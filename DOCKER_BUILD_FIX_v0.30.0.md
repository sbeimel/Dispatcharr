# Docker Build Fix for v0.30.0

## Problem

Bei Docker-Builds mit dem v0.30.0 Patch trat folgender Fehler auf:
```
ModuleNotFoundError: No module named 'drf_spectacular'
```

## Root Cause

Das Problem hat **zwei Ursachen**:

### 1. UV Sync Package-Installation
`uv sync` in der DispatcharrBase installiert nicht zuverlässig alle Pakete aus `pyproject.toml`. Besonders kritische Pakete wie `drf-spectacular`, `django-db-geventpool`, und `psycopg[binary]` werden manchmal übersprungen.

### 2. Multi-Stage Build ohne Fallback
Der `docker/Dockerfile` verwendet ein Multi-Stage Build:
- **Stage 1 (builder)**: Erstellt Base-Image mit Python-Paketen
- **Stage 2 (final)**: Kopiert Packages vom Base-Image

Wenn Pakete im Base-Image fehlen, schlägt das Final-Image zur Laufzeit fehl.

## Solution (wie v0.27.0)

Die Lösung kommt aus **Dispatcharr v0.27.0** und besteht aus **zwei Teilen**:

### Teil 1: DispatcharrBase - Explizite Package-Installation

Nach `uv sync` werden kritische Pakete **explizit nachinstalliert**:

```dockerfile
# EXPLICIT installation of critical packages that might be version-mismatched
RUN echo "=== Ensuring critical packages with correct versions ===" && \
    uv pip install --python $UV_PROJECT_ENVIRONMENT/bin/python \
    'psycopg[binary]' \
    django-db-geventpool \
    'drf-spectacular>=0.30.0' \
    django-redis \
    'channels-redis>=4.3.0'

# Verify critical packages are installed
RUN echo "=== Verifying critical packages ===" && \
    $UV_PROJECT_ENVIRONMENT/bin/python -c "import django_db_geventpool; print('✓ django-db-geventpool')" && \
    $UV_PROJECT_ENVIRONMENT/bin/python -c "import drf_spectacular; print('✓ drf-spectacular')" && \
    $UV_PROJECT_ENVIRONMENT/bin/python -c "import gevent; print('✓ gevent')" && \
    $UV_PROJECT_ENVIRONMENT/bin/python -c "import psycopg; print('✓ psycopg')" && \
    $UV_PROJECT_ENVIRONMENT/bin/python -c "import django_redis; print('✓ django-redis')" && \
    $UV_PROJECT_ENVIRONMENT/bin/python -c "import channels_redis; print('✓ channels-redis')" && \
    echo "=== All critical packages verified ==="
```

### Teil 2: Dockerfile - Fallback-Installation im Final Stage

Im **Final-Image** werden Pakete **geprüft und nachinstalliert**, falls sie fehlen:

```dockerfile
# IMPORTANT: Verify Python packages are still available after base image
RUN echo "=== Verifying packages in final stage ===" && \
    /dispatcharrpy/bin/python -c "import django_db_geventpool; print('✓ django-db-geventpool in final')" || \
    echo "⚠️ WARNING: django-db-geventpool NOT found in final stage!"

# Fallback: Install critical packages if they're missing
RUN /dispatcharrpy/bin/python -c "import psycopg; import psycopg.pq" 2>/dev/null || \
    (echo "⚠️  psycopg missing! Installing..." && \
    uv pip install --python /dispatcharrpy/bin/python 'psycopg[binary]>=3.1.18')

RUN /dispatcharrpy/bin/python -c "import django_db_geventpool" 2>/dev/null || \
    (echo "Installing missing django-db-geventpool..." && \
    uv pip install --python /dispatcharrpy/bin/python django-db-geventpool>=4.0.8)

RUN /dispatcharrpy/bin/python -c "import drf_spectacular" 2>/dev/null || \
    (echo "Installing missing drf-spectacular..." && \
    uv pip install --python /dispatcharrpy/bin/python drf-spectacular>=0.29.0)

RUN /dispatcharrpy/bin/python -c "import django_redis" 2>/dev/null || \
    (echo "Installing missing django-redis..." && \
    uv pip install --python /dispatcharrpy/bin/python django-redis)

RUN /dispatcharrpy/bin/python -c "import channels_redis" 2>/dev/null || \
    (echo "Installing missing channels-redis..." && \
    uv pip install --python /dispatcharrpy/bin/python channels-redis==4.3.0)

# Final verification - fail build if packages are still missing
RUN echo "=== Final verification ===" && \
    /dispatcharrpy/bin/python -c "import psycopg; print('✓ psycopg version:', psycopg.__version__)" && \
    /dispatcharrpy/bin/python -c "import psycopg.pq; print('✓ psycopg binary driver')" && \
    /dispatcharrpy/bin/python -c "import django_db_geventpool; print('✓ django-db-geventpool available')" && \
    /dispatcharrpy/bin/python -c "import drf_spectacular; print('✓ drf-spectacular available')" && \
    /dispatcharrpy/bin/python -c "import django_redis; print('✓ django-redis available')" && \
    /dispatcharrpy/bin/python -c "import channels_redis; print('✓ channels-redis available')"
```

## Implementation Status

✅ **DispatcharrBase**: Bereits implementiert (Zeilen 37-52)  
✅ **Dockerfile**: Implementiert in diesem Patch (nach Zeile 22)

## Build Commands

```bash
# 1. Alte Images entfernen
docker rmi sbeimel/dispatcharr:base sbeimel/dispatcharr:0.30.0 -f

# 2. Base Image bauen (mit expliziter Package-Installation)
docker build -t sbeimel/dispatcharr:base -f docker/DispatcharrBase . --no-cache

# 3. Base Image verifizieren
docker run --rm sbeimel/dispatcharr:base /dispatcharrpy/bin/python -c "import drf_spectacular; print('✓ SUCCESS')"

# 4. Final Image bauen (mit Fallback-Installation)
docker build -t sbeimel/dispatcharr:0.30.0 -f docker/Dockerfile \
  --build-arg BASE_TAG=base \
  --build-arg REPO_OWNER=sbeimel \
  --build-arg REPO_NAME=dispatcharr \
  --no-cache .

# 5. Container starten
cd docker
docker-compose down
docker-compose up -d

# 6. Migrations ausführen
docker-compose exec dispatcharr python manage.py migrate
```

## What This Fix Does

1. **Base Image**: Installiert Pakete explizit nach `uv sync`
2. **Final Image**: Prüft Pakete und installiert sie bei Bedarf nach
3. **Verification**: Zeigt genau, welche Pakete fehlen/vorhanden sind
4. **Fail-Safe**: Build schlägt nur fehl, wenn Installation auch im Final nicht funktioniert

## Why This Works

- **Redundanz**: Pakete werden zweimal installiert (Base + Final)
- **Visibility**: Logs zeigen genau, wo Pakete fehlen
- **Flexibility**: Funktioniert sowohl mit lokalem als auch mit ghcr.io Base-Image
- **Proven**: Diese Lösung ist in v0.27.0 produktiv im Einsatz

## Alternative: docker-compose.yml anpassen

Statt `image: ghcr.io/dispatcharr/dispatcharr:latest` verwende:

```yaml
web:
  image: sbeimel/dispatcharr:0.30.0
  # ...rest of config
```

Dies ist bereits im Patch enthalten (docker-compose.yml wurde angepasst).

## Files Modified

- `docker/DispatcharrBase` - Explizite Package-Installation ✅ (bereits vorhanden)
- `docker/Dockerfile` - Fallback-Installation im Final Stage ✅ (in diesem Patch)
- `docker/docker-compose.yml` - Image-Referenz angepasst ✅ (in diesem Patch)

## Verification

Nach dem Build solltest du sehen:

```
=== Verifying packages in final stage ===
✓ django-db-geventpool in final
=== Final verification ===
✓ psycopg version: 3.1.x
✓ psycopg binary driver
✓ django-db-geventpool available
✓ drf-spectacular available
✓ django-redis available
✓ channels-redis available
```

Falls Pakete fehlen, siehst du:
```
⚠️ WARNING: django-db-geventpool NOT found in final stage!
Installing missing django-db-geventpool...
```

## Related Issues

- Issue #XXX: ModuleNotFoundError: No module named 'drf_spectacular'
- Issue #YYY: UV sync doesn't install all packages from pyproject.toml

## Credits

Solution adapted from **Dispatcharr v0.27.0** where this issue was already resolved.
