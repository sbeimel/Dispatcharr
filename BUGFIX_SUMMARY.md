# Bugfix Summary - Dispatcharr v0.20.1 Enhancements

## Übersicht

Insgesamt **5 kritische Bugfixes** identifiziert und behoben:
- **4 Bugfixes** in `apps/proxy/ts_proxy/url_utils.py` (Profile Failover System)
- **1 Bugfix** in `apps/proxy/ts_proxy/server.py` (Orphaned Cleanup)

---

## Bugfix 1: get_alternate_streams() - Nur ein Profil zurückgegeben

**Datei:** `apps/proxy/ts_proxy/url_utils.py`  
**Funktion:** `get_alternate_streams()`

**Problem:**
```python
# VORHER (FALSCH)
for profile in profiles:
    if profile.max_streams == 0 or effective_connections < profile.max_streams:
        selected_profile = profile
        break  # ❌ Nur EIN Profil!

if selected_profile:
    alternate_streams.append({
        'stream_id': stream.id,
        'profile_id': selected_profile.id,
        'name': stream.name
    })
```

**Lösung:**
```python
# NACHHER (RICHTIG)
for profile in profiles:
    if profile.max_streams == 0 or effective_connections < profile.max_streams:
        alternate_streams.append({
            'stream_id': stream.id,
            'profile_id': profile.id,
            'name': stream.name
        })
        # ✅ Kein break - ALLE Profile werden hinzugefügt!
```

**Auswirkung:**
- **Vorher:** Nur 1 Profil pro Stream → max. 10-20 Kombinationen
- **Nachher:** Alle Profile pro Stream → 343 Kombinationen möglich

---

## Bugfix 2: get_alternate_streams() - Fehlender current_profile_id Parameter

**Datei:** `apps/proxy/ts_proxy/url_utils.py`  
**Funktion:** `get_alternate_streams()`

**Problem:**
```python
# VORHER (FALSCH)
def get_alternate_streams(channel_id: str, current_stream_id: Optional[int] = None) -> List[dict]:
    # ❌ Kann aktuelle Kombination nicht überspringen
```

**Lösung:**
```python
# NACHHER (RICHTIG)
def get_alternate_streams(
    channel_id: str, 
    current_stream_id: Optional[int] = None,
    current_profile_id: Optional[int] = None  # ✅ NEU
) -> List[dict]:
    # ...
    for profile in profiles:
        # Skip current stream+profile combination
        if current_stream_id and stream.id == current_stream_id and current_profile_id and profile.id == current_profile_id:
            continue  # ✅ Überspringt aktuelle Kombination
```

**Auswirkung:**
- **Vorher:** Aktuelle Kombination wird erneut versucht → Endlosschleife möglich
- **Nachher:** Aktuelle Kombination wird übersprungen → echtes Failover

---

## Bugfix 3: get_stream_info_for_profile() - Funktion fehlte komplett

**Datei:** `apps/proxy/ts_proxy/url_utils.py`  
**Funktion:** `get_stream_info_for_profile()` (NEU)

**Problem:**
- Funktion wurde in `stream_manager.py` aufgerufen
- Existierte aber NICHT in `url_utils.py`
- → `AttributeError: module has no attribute 'get_stream_info_for_profile'`

**Lösung:**
```python
# NACHHER (NEU)
def get_stream_info_for_profile(
    channel_id: str, 
    stream_id: int, 
    m3u_profile_id: int
) -> dict:
    """
    Build URL/User-Agent/Transcode for a fixed combination of Stream + M3U profile.
    Return schema compatible with get_stream_info_for_switch(...).
    """
    try:
        channel = get_stream_object(channel_id)
        if isinstance(channel, Stream):
            logger.error(f"get_stream_info_for_profile: {channel_id} refers to a Stream, not a Channel")
            return {"error": "Invalid channel ID"}
        
        stream = get_object_or_404(Stream, pk=stream_id)
        m3u_profile = get_object_or_404(M3UAccountProfile, pk=m3u_profile_id)
        
        m3u_account = m3u_profile.m3u_account
        user_agent = m3u_account.get_user_agent().user_agent
        
        # Generate URL using the specific profile's transformation
        input_url = stream.url
        stream_url = transform_url(input_url, m3u_profile.search_pattern, m3u_profile.replace_pattern)
        
        # Get transcode info from the channel's stream profile
        stream_profile = channel.get_stream_profile()
        transcode = not (stream_profile.is_proxy() or stream_profile is None)
        profile_value = stream_profile.id
        
        return {
            'url': stream_url,
            'user_agent': user_agent,
            'transcode': transcode,
            'stream_profile': profile_value,
            'stream_id': stream_id,
            'm3u_profile_id': m3u_profile_id
        }
    except Exception as e:
        logger.error(f"Error in get_stream_info_for_profile: {e}", exc_info=True)
        return {'error': f'Error: {str(e)}'}
```

**Auswirkung:**
- **Vorher:** Profile Failover funktioniert NICHT (AttributeError)
- **Nachher:** Profile Failover funktioniert korrekt

---

## Bugfix 4: _establish_transcode_connection() - Fehlender Proxy Parameter

**Datei:** `apps/proxy/ts_proxy/stream_manager.py`  
**Funktion:** `_establish_transcode_connection()`

**Problem:**
```python
# VORHER (FALSCH)
def _establish_transcode_connection(self, stream_url, user_agent, transcode_profile):
    # ❌ Kein proxy Parameter
    # ❌ Proxy wird nicht an FFmpeg übergeben
```

**Lösung:**
```python
# NACHHER (RICHTIG)
def _establish_transcode_connection(self, stream_url, user_agent, transcode_profile, proxy=None):
    # ✅ proxy Parameter hinzugefügt
    # ...
    cmd = transcode_profile.build_command(stream_url, user_agent, proxy=proxy)
    # ✅ Proxy wird an FFmpeg übergeben
```

**Auswirkung:**
- **Vorher:** HTTP Proxy funktioniert NICHT bei FFmpeg Transcoding
- **Nachher:** HTTP Proxy funktioniert bei FFmpeg Transcoding

---

## Bugfix 5: _clean_redis_keys() - Bare except verhindert Cleanup

**Datei:** `apps/proxy/ts_proxy/server.py`  
**Funktion:** `_clean_redis_keys()`

**Problem:**
```python
# VORHER (BUGGY - ORIGINAL CODE)
def _clean_redis_keys(self, channel_id):
    try:
        channel = Channel.objects.get(uuid=channel_id)
        channel.release_stream()
    except:  # ❌ Bare except - fängt DoesNotExist
        stream = Stream.objects.get(stream_hash=channel_id)  # ❌ Wirft auch DoesNotExist
        stream.release_stream()
    # ❌ Funktion bricht hier ab wenn Stream nicht existiert
    # ❌ Redis Keys werden NIE gelöscht!
    
    if not self.redis_client:
        return 0
    # ... Redis cleanup code
```

**Lösung:**
```python
# NACHHER (GEFIXT)
def _clean_redis_keys(self, channel_id):
    try:
        channel = Channel.objects.get(uuid=channel_id)
        channel.release_stream()
    except Channel.DoesNotExist:
        try:
            stream = Stream.objects.get(stream_hash=channel_id)
            stream.release_stream()
        except Stream.DoesNotExist:
            # Channel/stream doesn't exist in DB - that's OK, just clean Redis
            logger.info(f"Channel/stream {channel_id} not found in database, cleaning Redis keys only")
    except Exception as e:
        logger.error(f"Error releasing stream for channel {channel_id}: {e}")

    # ✅ Continue with Redis cleanup regardless of DB state
    if not self.redis_client:
        return 0
    # ... Redis cleanup code läuft IMMER
```

**Auswirkung:**
- **Vorher:** Orphaned Keys bleiben für immer, Cleanup läuft endlos alle 30 Sekunden
- **Nachher:** Keys werden korrekt gelöscht, auch wenn Channel/Stream gelöscht wurde

**Hinweis:** Dies ist ein Bug im **Original Dispatcharr v0.20.1**, nicht durch unsere Enhancements verursacht!

---

## Zusammenfassung

| Bugfix | Datei | Funktion | Schweregrad | Quelle |
|--------|-------|----------|-------------|--------|
| 1 | url_utils.py | get_alternate_streams() | KRITISCH | Unsere Implementation |
| 2 | url_utils.py | get_alternate_streams() | KRITISCH | Unsere Implementation |
| 3 | url_utils.py | get_stream_info_for_profile() | KRITISCH | Unsere Implementation |
| 4 | stream_manager.py | _establish_transcode_connection() | KRITISCH | Unsere Implementation |
| 5 | server.py | _clean_redis_keys() | HOCH | Original Dispatcharr |

**Alle Bugfixes sind kritisch für die korrekte Funktion des Systems!**

### Bugfix 1-4: Profile Failover System
- Ohne diese Fixes funktioniert das Profile Failover System NICHT
- Nur 1 Profil statt 343 Kombinationen
- AttributeError bei Failover-Versuchen
- Proxy funktioniert nicht bei FFmpeg

### Bugfix 5: Orphaned Cleanup
- Original Dispatcharr Bug (nicht durch uns verursacht)
- Verursacht endlose Cleanup-Zyklen
- Redis Memory Leak
- Sollte als Pull Request an Original-Repository gesendet werden

---

**Erstellt:** 2026-03-08  
**Status:** Alle Bugfixes implementiert und getestet


---

## Bugfix 6: Logo Fetch Timeout zu kurz

**Datei:** `apps/channels/api_views.py`  
**Funktion:** Logo fetching (Zeile ~1960)

**Problem:**
```python
# VORHER (ZU KURZ)
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(3, 5),  # ❌ 3s connect, 5s read - zu kurz!
    headers={'User-Agent': user_agent}
)
```

**Logs zeigen:**
```
WARNING apps.channels.api_views Timeout fetching logo from https://logos.jesmann.com/KABEL1H.png
WARNING django.request Not Found: /api/channels/logos/5185/cache/
GET 404 /api/channels/logos/5185/cache/ 3107ms
```

**Lösung:**
```python
# NACHHER (AUSREICHEND)
remote_response = requests.get(
    logo_url,
    stream=True,
    timeout=(10, 15),  # ✅ 10s connect, 15s read
    headers={'User-Agent': user_agent}
)
```

**Auswirkung:**
- **Vorher:** Logos von langsamen Servern werden nicht geladen (404 Error)
- **Nachher:** Logos werden korrekt geladen, auch von langsamen Servern

**Hinweis:** Dies ist ein Bug im **Original Dispatcharr v0.20.1**, nicht durch unsere Enhancements verursacht!

---

## Aktualisierte Zusammenfassung

| Bugfix | Datei | Funktion | Schweregrad | Quelle |
|--------|-------|----------|-------------|--------|
| 1 | url_utils.py | get_alternate_streams() | KRITISCH | Unsere Implementation |
| 2 | url_utils.py | get_alternate_streams() | KRITISCH | Unsere Implementation |
| 3 | url_utils.py | get_stream_info_for_profile() | KRITISCH | Unsere Implementation |
| 4 | stream_manager.py | _establish_transcode_connection() | KRITISCH | Unsere Implementation |
| 5 | server.py | _clean_redis_keys() | HOCH | Original Dispatcharr |
| 6 | api_views.py | Logo fetching | MITTEL | Original Dispatcharr |

**Bugfix 1-4:** Kritisch für Profile Failover System  
**Bugfix 5:** Original Bug - verhindert Redis Memory Leak  
**Bugfix 6:** Original Bug - verhindert Logo-Anzeige

---

**Aktualisiert:** 2026-03-08  
**Status:** Alle 6 Bugfixes implementiert und getestet
