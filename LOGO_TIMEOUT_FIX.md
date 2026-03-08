# Logo Timeout Fix

## Problem

Logo-Downloads von `logos.jesmann.com` schlagen mit Timeout fehl:

```
WARNING apps.channels.api_views Timeout fetching logo from https://logos.jesmann.com/KABEL1H.png
WARNING django.request Not Found: /api/channels/logos/5185/cache/
```

Logs zeigen:
- Requests dauern ~3000-3100ms (3+ Sekunden)
- Aktueller Timeout: `(3, 5)` = 3s connect, 5s read
- Server antwortet zu langsam

## Root Cause

**Datei:** `apps/channels/api_views.py` (Zeile ~1960)

```python
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(3, 5),  # ❌ Zu kurz für langsame Server!
    headers={'User-Agent': user_agent}
)
```

**Hardcoded Timeouts:**
- Connect Timeout: 3 Sekunden
- Read Timeout: 5 Sekunden

**Problem:**
- `logos.jesmann.com` braucht oft 3+ Sekunden zum Antworten
- Connect Timeout wird überschritten
- Request schlägt fehl → 404 Error

## Lösung 1: Timeouts erhöhen (Empfohlen)

**Datei:** `apps/channels/api_views.py`

```python
# VORHER (ZU KURZ)
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(3, 5),  # ❌ Zu kurz
    headers={'User-Agent': user_agent}
)

# NACHHER (LÄNGER)
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(10, 15),  # ✅ 10s connect, 15s read
    headers={'User-Agent': user_agent}
)
```

**Vorteile:**
- Einfache Änderung
- Funktioniert für langsame Server
- Keine Breaking Changes

**Nachteile:**
- Requests können länger hängen
- Blockiert Worker länger

## Lösung 2: Konfigurierbare Timeouts (Besser)

**Schritt 1:** Setting in `core/models.py` hinzufügen

```python
class CoreSettings(models.Model):
    # ... existing fields
    
    @classmethod
    def get_logo_timeout(cls):
        """Get logo fetch timeout (connect, read) in seconds"""
        try:
            settings = cls.objects.first()
            if settings and settings.data:
                return (
                    settings.data.get('logo_connect_timeout', 10),
                    settings.data.get('logo_read_timeout', 15)
                )
        except Exception:
            pass
        return (10, 15)  # Default: 10s connect, 15s read
```

**Schritt 2:** In `api_views.py` verwenden

```python
from core.models import CoreSettings

# ...

connect_timeout, read_timeout = CoreSettings.get_logo_timeout()
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(connect_timeout, read_timeout),
    headers={'User-Agent': user_agent}
)
```

**Schritt 3:** Frontend Setting hinzufügen

In `frontend/src/components/forms/settings/ProxySettingsForm.jsx`:

```jsx
<TextField
  label="Logo Connect Timeout (seconds)"
  name="logo_connect_timeout"
  type="number"
  defaultValue={10}
  helperText="Timeout for connecting to logo servers"
/>
<TextField
  label="Logo Read Timeout (seconds)"
  name="logo_read_timeout"
  type="number"
  defaultValue={15}
  helperText="Timeout for reading logo data"
/>
```

## Lösung 3: Retry-Mechanismus (Am Besten)

**Datei:** `apps/channels/api_views.py`

```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def get_logo_with_retry(logo_url, user_agent, max_retries=3):
    """Fetch logo with retry mechanism"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1,  # Wait 1s, 2s, 4s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session.get(
        logo_url,
        stream=True,
        timeout=(10, 15),  # Longer timeouts
        headers={'User-Agent': user_agent}
    )

# In der View verwenden:
remote_response = get_logo_with_retry(logo_url, user_agent)
```

**Vorteile:**
- Automatische Retries bei Timeouts
- Exponential Backoff
- Robuster gegen temporäre Probleme

## Schnellfix (Sofort anwendbar)

Wenn du das Problem JETZT beheben willst:

```bash
# Datei editieren
nano apps/channels/api_views.py

# Zeile ~1960 ändern von:
timeout=(3, 5),

# Zu:
timeout=(10, 15),

# Speichern und Server neu starten
docker compose restart
```

## Empfehlung

**Kurzfristig:** Lösung 1 (Timeouts erhöhen auf 10, 15)  
**Langfristig:** Lösung 3 (Retry-Mechanismus)

**Warum nicht Lösung 2?**
- Mehr Code-Änderungen
- Frontend-Änderungen erforderlich
- Für die meisten User nicht nötig

**Warum Lösung 3?**
- Robuster gegen temporäre Netzwerkprobleme
- Automatische Retries
- Bessere User Experience
- Standard-Pattern für HTTP-Requests

## Alternative: Logo-Caching verbessern

Wenn Logos häufig abgerufen werden, könnte man auch das Caching verbessern:

```python
# Cache logos lokal für 24h
from django.core.cache import cache

cache_key = f"logo_{channel_id}"
cached_logo = cache.get(cache_key)

if cached_logo:
    return cached_logo

# Fetch logo...
cache.set(cache_key, logo_data, 86400)  # 24h
```

## Zusammenfassung

**Problem:** Hardcoded Timeouts (3s, 5s) zu kurz für langsame Logo-Server  
**Lösung:** Timeouts erhöhen auf (10s, 15s) oder Retry-Mechanismus implementieren  
**Impact:** Niedrig - nur Logo-Downloads betroffen  
**Priorität:** Mittel - Logos werden nicht angezeigt, aber Funktionalität nicht beeinträchtigt

---

**Erstellt:** 2026-03-08  
**Status:** Analyse abgeschlossen, Lösungen vorgeschlagen
