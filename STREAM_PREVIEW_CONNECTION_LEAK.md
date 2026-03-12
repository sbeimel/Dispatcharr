# Stream Preview Connection Leak

## Problem

Stream/Quality Checks belegen Profile-Connections permanent, auch wenn kein aktiver Stream läuft.

**Logs zeigen:**
```
INFO ts_proxy.url_utils Previewing stream directly: 872017 (( AT ) ORF 1 HD)
INFO ts_proxy.url_utils Kilci5 Default (Kilci5)
ERROR ts_proxy.url_utils No profiles available with connection capacity for M3U account 229
```

**Symptome:**
- Alle Profile zeigen "No profiles available with connection capacity"
- Stats zeigen keine aktiven Streams
- Neue Stream-Requests bekommen 503 Service Unavailable
- Problem tritt nach Stream/Quality Checks auf

## Root Cause

**Datei:** `apps/proxy/ts_proxy/url_utils.py` (Zeilen 40-100)

### Problem 1: Preview prüft Connections, belegt sie aber nicht

```python
# In get_stream_info_for_switch() für Stream Preview
if isinstance(channel_or_stream, Stream):
    stream = channel_or_stream
    logger.info(f"Previewing stream directly: {stream.id} ({stream.name})")
    
    # Prüft Connection-Verfügbarkeit
    current_connections = int(redis_client.get(profile_connections_key) or 0)
    if profile.max_streams == 0 or current_connections < profile.max_streams:
        selected_profile = profile
        # ❌ Aber: acquire_stream() wird NICHT aufgerufen!
        break
```

**Was passiert:**
1. Preview prüft ob Profile verfügbar sind
2. Wählt ein Profile aus
3. **Belegt die Connection NICHT** (kein `acquire_stream()`)
4. Stream wird gestartet (belegt Connection implizit)
5. Stream wird gestoppt nach Check
6. **Connection wird NICHT freigegeben** (kein `release_stream()`)
7. Redis-Counter bleibt erhöht → Profile erscheint "voll"

### Problem 2: Normale Streams vs. Preview Streams

**Normale Streams** (über Channel):
```python
# In views.py
stream_info = get_stream_info_for_switch(channel_id)
# ... später ...
channel.acquire_stream(stream_id, profile_id)  # ✅ Belegt Connection
# ... Stream läuft ...
channel.release_stream()  # ✅ Gibt Connection frei
```

**Preview Streams** (direkt über Stream):
```python
# In url_utils.py
stream_info = get_stream_info_for_switch(stream)  # Stream-Objekt statt Channel
# ❌ acquire_stream() wird NIE aufgerufen
# ❌ release_stream() wird NIE aufgerufen
```

## Warum passiert das?

**Stream Previews** werden verwendet für:
1. **Quality Checks** - Kurze Tests ob Stream funktioniert
2. **Stream Selection** - Auswahl des besten Streams
3. **Failover Testing** - Test ob Backup-Stream verfügbar ist

Diese Checks laufen nur wenige Sekunden und sollten **KEINE** Connections belegen.

## Lösung 1: Preview-Modus ohne Connection-Reservierung (Empfohlen)

Stream Previews sollten Connections **NICHT** belegen, da sie nur kurz laufen.

**Datei:** `apps/proxy/ts_proxy/url_utils.py`

```python
def get_stream_info_for_switch(
    channel_or_stream, 
    current_stream_id=None, 
    current_profile_id=None,
    preview_mode=False  # ✅ NEU: Preview-Modus Flag
):
    """
    Get stream information for switching or previewing.
    
    Args:
        preview_mode: If True, skip connection capacity checks (for quality checks)
    """
    
    # Handle direct stream preview (custom streams)
    if isinstance(channel_or_stream, Stream):
        stream = channel_or_stream
        logger.info(f"Previewing stream directly: {stream.id} ({stream.name})")
        
        # ... M3U account und profile logic ...
        
        for profile in profiles:
            logger.info(profile)
            
            # ✅ NEU: Skip connection check in preview mode
            if preview_mode:
                selected_profile = profile
                logger.debug(f"Preview mode: Using profile {profile.id} without connection check")
                break
            
            # Check connection availability (nur für normale Streams)
            if redis_client:
                profile_connections_key = f"profile_connections:{profile.id}"
                current_connections = int(redis_client.get(profile_connections_key) or 0)
                
                if profile.max_streams == 0 or current_connections < profile.max_streams:
                    selected_profile = profile
                    logger.debug(f"Selected profile {profile.id} with {current_connections}/{profile.max_streams} connections")
                    break
```

**Dann in views.py:**

```python
# Für Quality Checks / Stream Preview
stream_info = get_stream_info_for_switch(stream, preview_mode=True)  # ✅ Keine Connection-Prüfung

# Für normale Streams
stream_info = get_stream_info_for_switch(channel)  # ✅ Mit Connection-Prüfung
```

## Lösung 2: Separate Preview-Funktion (Sauberer)

Erstelle eine separate Funktion für Stream Previews:

```python
def get_stream_info_for_preview(stream):
    """
    Get stream information for preview/quality check WITHOUT connection reservation.
    This is used for short-lived checks and should not count against connection limits.
    """
    logger.info(f"Previewing stream: {stream.id} ({stream.name})")
    
    m3u_account = stream.m3u_account
    if not m3u_account:
        logger.error(f"Stream {stream.id} has no M3U account")
        return None
    
    # Get first active profile (no connection check needed for preview)
    m3u_profiles = m3u_account.profiles.filter(is_active=True)
    default_profile = next((obj for obj in m3u_profiles if obj.is_default), None)
    
    if not default_profile:
        # Try any active profile
        default_profile = m3u_profiles.first()
    
    if not default_profile:
        logger.error(f"No active profile found for M3U account {m3u_account.id}")
        return None
    
    # Get stream URL and user agent
    stream_url = transform_url(stream.url, default_profile.search_pattern, default_profile.replace_pattern)
    user_agent = m3u_account.get_user_agent().user_agent
    
    return {
        'url': stream_url,
        'user_agent': user_agent,
        'transcode': False,  # Previews usually don't transcode
        'stream_profile': None,
        'stream_id': stream.id,
        'm3u_profile_id': default_profile.id,
        'preview': True  # ✅ Flag to indicate this is a preview
    }
```

## Lösung 3: Cleanup-Script für blockierte Connections

Wenn Connections bereits blockiert sind, manuell freigeben:

```python
#!/usr/bin/env python
"""
Cleanup script to reset all profile connection counters.
Use this if connections are stuck after failed stream checks.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatcharr.settings')
django.setup()

from core.utils import RedisClient
from apps.m3u.models import M3UAccountProfile

redis_client = RedisClient.get_client()

print("Resetting all profile connection counters...")

for profile in M3UAccountProfile.objects.all():
    profile_key = f"profile_connections:{profile.id}"
    current = redis_client.get(profile_key)
    
    if current:
        print(f"Profile {profile.id} ({profile.name}): {current} connections → 0")
        redis_client.delete(profile_key)
    else:
        print(f"Profile {profile.id} ({profile.name}): already at 0")

print("\nDone! All profile connections reset.")
```

## Sofort-Fix (Workaround)

Wenn du das Problem JETZT beheben willst ohne Code-Änderungen:

```bash
# Redis CLI öffnen
docker exec -it <redis-container> redis-cli

# Alle profile_connections Keys löschen
KEYS profile_connections:*
# Für jeden Key:
DEL profile_connections:227
DEL profile_connections:229
# Oder alle auf einmal:
EVAL "return redis.call('del', unpack(redis.call('keys', 'profile_connections:*')))" 0
```

## Empfehlung

**Kurzfristig:** Lösung 3 (Cleanup-Script) ausführen um blockierte Connections freizugeben

**Langfristig:** Lösung 2 (Separate Preview-Funktion) implementieren
- Saubere Trennung zwischen Preview und normalen Streams
- Previews belegen keine Connections
- Keine Änderungen an bestehender Logic nötig

## Zusätzliche Verbesserung: Connection Timeout

Profile-Connections sollten automatisch ablaufen:

```python
# In channel.acquire_stream()
redis_client.setex(
    f"profile_connections:{profile_id}",
    3600,  # ✅ TTL: 1 Stunde
    current_connections + 1
)
```

So werden "vergessene" Connections automatisch nach 1 Stunde freigegeben.

---

**Erstellt:** 2026-03-11  
**Status:** Problem identifiziert, Lösungen vorgeschlagen
