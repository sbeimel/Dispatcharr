# ❌ KRITISCHES FEATURE FEHLT: VOD Streaming Proxy Support

## Problem

**VOD Streaming verwendet KEIN HTTP Proxy!**

### Status:
- ✅ **VOD XC API Calls:** Verwenden Proxy (via `account.get_proxy_for_api()`)
- ❌ **VOD Streaming:** Verwendet KEIN Proxy

### Code-Analyse:

**File:** `apps/proxy/vod_proxy/multi_worker_connection_manager.py` (Zeile 484)

```python
# PROBLEM: Kein Proxy-Parameter!
response = self.local_session.get(
    target_url,
    headers=headers,
    stream=True,
    timeout=(10, 10),
    allow_redirects=allow_redirects
)
```

**Vergleich mit Live TV Streaming:**
```python
# apps/proxy/live_proxy/input/http_streamer.py
if proxy:
    self.session.proxies = {
        'http': proxy,
        'https': proxy
    }

response = self.session.get(url, ...)
```

---

## Lösung

### 1. StreamState erweitern mit m3u_account_id

**File:** `apps/proxy/vod_proxy/multi_worker_connection_manager.py`

**Änderung 1: StreamState.__init__**
```python
def __init__(self, session_id: str, stream_url: str, headers: dict,
             content_length: str = None, content_type: str = None,
             final_url: str = None, 
             m3u_profile_id: int = None,
             m3u_account_id: int = None,  # ← NEU HINZUFÜGEN
             # ... rest
):
    self.m3u_profile_id = m3u_profile_id
    self.m3u_account_id = m3u_account_id  # ← NEU HINZUFÜGEN
```

**Änderung 2: StreamState.to_dict()**
```python
def to_dict(self):
    return {
        # ...
        'm3u_profile_id': str(self.m3u_profile_id) if self.m3u_profile_id is not None else '',
        'm3u_account_id': str(self.m3u_account_id) if self.m3u_account_id is not None else '',  # ← NEU
        # ...
    }
```

**Änderung 3: StreamState.from_dict()**
```python
@classmethod
def from_dict(cls, data: dict):
    obj = cls(
        # ...
        m3u_profile_id=int(data.get('m3u_profile_id')) if data.get('m3u_profile_id') else None,
        m3u_account_id=int(data.get('m3u_account_id')) if data.get('m3u_account_id') else None,  # ← NEU
        # ...
    )
```

---

### 2. Proxy-Retrieval in _make_request

**File:** `apps/proxy/vod_proxy/multi_worker_connection_manager.py` (vor Zeile 484)

```python
def _make_request(self, range_header=None):
    # ... existing code ...
    
    # Get proxy from M3U account if available
    proxy = None
    if state.m3u_account_id:
        try:
            from apps.m3u.models import M3UAccount
            m3u_account = M3UAccount.objects.get(id=state.m3u_account_id)
            proxy = m3u_account.get_proxy_for_streaming()
            
            if proxy:
                from core.utils import sanitize_proxy_url
                logger.info(
                    f"[{self.session_id}] Using HTTP proxy for VOD streaming: "
                    f"{sanitize_proxy_url(proxy)}"
                )
        except M3UAccount.DoesNotExist:
            logger.warning(f"[{self.session_id}] M3U account {state.m3u_account_id} not found")
        except Exception as e:
            logger.error(f"[{self.session_id}] Error retrieving proxy: {e}")
    
    # Configure session proxy
    if proxy:
        self.local_session.proxies = {
            'http': proxy,
            'https': proxy
        }
    else:
        self.local_session.proxies = {}  # Clear any previous proxy
    
    # Make request (NOW WITH PROXY!)
    response = self.local_session.get(
        target_url,
        headers=headers,
        stream=True,
        timeout=(10, 10),
        allow_redirects=allow_redirects
    )
```

---

### 3. m3u_account_id beim Stream-Start übergeben

**File:** `apps/proxy/vod_proxy/views.py` (Zeile ~800-850)

**Zeile finden wo StreamState erstellt wird:**
```python
# VORHER (ungefähr Zeile 820):
state = StreamState(
    session_id=session_id,
    stream_url=final_stream_url,
    headers=headers,
    m3u_profile_id=m3u_profile.id if m3u_profile else None,
    # ... rest
)

# NACHHER:
state = StreamState(
    session_id=session_id,
    stream_url=final_stream_url,
    headers=headers,
    m3u_profile_id=m3u_profile.id if m3u_profile else None,
    m3u_account_id=m3u_account.id if m3u_account else None,  # ← NEU HINZUFÜGEN
    # ... rest
)
```

**Wichtig:** Suche nach ALLEN `StreamState(` Aufrufen und füge `m3u_account_id` hinzu!

---

## Testing

### 1. VOD mit Proxy testen
```bash
# In M3U Form: Proxy konfigurieren
# http://proxy.example.com:8080

# VOD Stream starten
curl http://localhost:8000/vod/movie/abc-123

# Log prüfen:
# [session-xyz] Using HTTP proxy for VOD streaming: http://***:***@proxy:8080
```

### 2. Proxy-Fehler testen
```bash
# Ungültigen Proxy konfigurieren
# http://invalid-proxy:9999

# Stream starten - sollte gracefully fehlschlagen
```

---

## Impact

### Betroffene User:
- **Jeder der VOD mit Proxy verwenden will**
- Besonders wichtig in Ländern mit Geo-Blocking
- Wichtig für Enterprise-Umgebungen mit Proxy-Pflicht

### Severity:
- 🔴 **HIGH** - Feature funktioniert nicht wie erwartet
- VOD API Calls verwenden Proxy ✅
- VOD Streaming verwendet KEIN Proxy ❌

### Workaround:
- **Keiner!** User können VOD nicht über Proxy streamen
- Nur XC API Calls (Metadaten) gehen durch Proxy
- Streaming selbst geht direkt (kann blockiert werden)

---

## Implementation Priority

**Empfehlung:** ⚠️ **HOCH - Vor Production Deployment**

**Warum:**
1. Feature-Inkonsistenz (Live TV hat Proxy, VOD nicht)
2. Keine Workaround-Möglichkeit
3. Relativ einfach zu implementieren (~50 Zeilen Code)
4. Kein Breaking Change (backward compatible)

**Zeitaufwand:** ~30-60 Minuten

---

## Zusammenfassung

| Komponente | Proxy Support | Status |
|------------|---------------|--------|
| M3U/EPG Download | ✅ | Implementiert |
| XC API Calls | ✅ | Implementiert |
| Live TV Streaming | ✅ | Implementiert |
| Live TV Transcode | ✅ | Implementiert |
| **VOD Streaming** | ❌ | **FEHLT!** |

**Nächster Schritt:** Implementation gemäß obiger Anleitung durchführen.
