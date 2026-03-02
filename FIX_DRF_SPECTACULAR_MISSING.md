# Fix: ModuleNotFoundError: No module named 'drf_spectacular'

## Problem
Dispatcharr-0.20.1 fails to start with error:
```
ModuleNotFoundError: No module named 'drf_spectacular'
```

## Root Cause
The Docker base image was built before `drf-spectacular>=0.29.0` was added to `pyproject.toml`. The dependency is listed in the file but not installed in the container's virtual environment.

## Solution Options

### Option 1: Rebuild Docker Images (Recommended)
This ensures all dependencies are properly installed:

```bash
cd Dispatcharr-0.20.1

# Rebuild the base image first
docker build -f docker/DispatcharrBase -t dispatcharr:base .

# Then rebuild the main image
docker build -f docker/Dockerfile --build-arg BASE_TAG=base -t dispatcharr:0.20.1 .

# Restart the container
docker-compose down
docker-compose up -d
```

### Option 2: Install Manually in Running Container (Quick Fix)
If you need a quick fix without rebuilding:

```bash
# Enter the running container
docker exec -it dispatcharr bash

# Install drf-spectacular using uv
uv pip install --python /dispatcharrpy/bin/python drf-spectacular>=0.29.0

# Exit and restart the container
exit
docker restart dispatcharr
```

### Option 3: Install via Docker Compose Override
Add this to your `docker-compose.yml` or create `docker-compose.override.yml`:

```yaml
services:
  dispatcharr:
    command: >
      bash -c "
      uv pip install --python /dispatcharrpy/bin/python drf-spectacular>=0.29.0 &&
      /app/docker/entrypoint.sh
      "
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Verification
After applying any solution, verify the installation:

```bash
docker exec -it dispatcharr bash
source /dispatcharrpy/bin/activate
python -c "import drf_spectacular; print(drf_spectacular.__version__)"
```

You should see the version number (e.g., `0.29.0` or higher).

## Why This Happened
- Dispatcharr-0.20.1 uses `drf-spectacular` (OpenAPI v3) instead of `drf-yasg` (OpenAPI v2)
- The dependency is correctly listed in `pyproject.toml`
- But Docker base images cache dependencies at build time
- If the base image was built before the dependency was added, it won't be present

## Related to v0.19.0 Integration?
**NO** - This is a standard Dispatcharr-0.20.1 dependency issue, not related to our v0.19.0 feature integration. All our integrated features (Profile Failover, HTTP Proxy, etc.) are backend/frontend code changes and don't require additional Python packages.

## Next Steps After Fix
Once `drf-spectacular` is installed and the container starts successfully:

1. Verify the application loads: `http://localhost:9191`
2. Check API documentation: `http://localhost:9191/api/schema/swagger-ui/`
3. Test our integrated v0.19.0 features:
   - Profile Failover System (343 combinations)
   - HTTP Proxy Support (FFmpeg + HTTP Proxy profiles)
   - Basic Authentication (M3U/EPG endpoints)
   - Extended Timeout Configuration
   - Ghost-Client Auto-Cleanup

All features are already integrated and ready to use once the dependency issue is resolved.
