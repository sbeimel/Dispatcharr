## Bug #7: 'NoneType' object has no attribute 'user_agent'

```python
ERROR live_proxy.manager Error getting stream info for stream 1187282 with profile 582: 'NoneType' object has no attribute 'user_agent'
```

**Problem:** 
```python
new_user_agent = m3u_account.get_user_agent().user_agent  # FAILS wenn get_user_agent() None zurückgibt
```

**Ursache:**
`get_user_agent()` kann `None` zurückgeben wenn kein spezifischer User-Agent für den Account konfiguriert ist.

**Fix:**
```python
new_user_agent = m3u_account.get_user_agent_string()  # Verwendet System-Default wenn None
```

Die Funktion `get_user_agent_string()` behandelt den None-Fall automatisch und gibt den System-Default User-Agent zurück.

---

# Bug Fix: Stream Preview Failover - tried_combinations Tracking + UUID ValidationError

## Problem 1: tried_stream_ids statt tried_combinations
Stream preview failover war defekt weil nur `stream_id` getrackt wurde, aber nicht `profile_id`. 

**Fehlerbeschreibung:**
```
Log: "Found 5 alternate profiles for stream preview 1187282: [582, 580, 581, 583, 584]"
Log: "No untried streams available for channel [...], tried: {1187282}"
```

**Root Cause:**
Alle Profile haben die gleiche `stream_id` (z.B. 1187282) aber unterschiedliche `profile_id` (z.B. 582, 580, 581, 583, 584).

Die alte Logik in v0.30.0:
```python
untried_streams = [s for s in alternate_streams if s['stream_id'] not in self.tried_stream_ids]
```

Nach dem ersten Versuch mit stream_id=1187282 wurden ALLE Profiles ausgefiltert, weil alle dieselbe stream_id haben.

## Problem 2: UUID ValidationError in get_stream_info_for_switch()

```python
ERROR live_proxy.url_utils Error getting stream info for switch: ['"83e7244bac2a954aa66785b94a53aa306218a7734e9f4404510bf9f354057a92" is not a valid UUID.']
File "/app/apps/proxy/live_proxy/url_utils.py", line 219, in get_stream_info_for_switch
    channel = get_object_or_404(Channel, uuid=channel_id)
django.core.exceptions.ValidationError: ['"83e7244bac2a954aa66785b94a53aa306218a7734e9f4404510bf9f354057a92" is not a valid UUID.']
```

**Root Cause:**
Bei **Stream Preview** ist `channel_id` ein **Stream Hash**, kein Channel UUID! Die Funktion `get_stream_info_for_switch()` versucht aber ein Channel-Object zu laden:
```python
channel = get_object_or_404(Channel, uuid=channel_id)  # FAILS for stream preview!
```

## Lösung (aus v0.27.0)

### 1. Tracking von `(stream_id, profile_id)` Tupeln statt nur `stream_id`
### 2. Direktes Holen der Stream-Info statt `get_stream_info_for_switch()` Funktion

v0.27.0 verwendet:
```python
stream_obj = Stream.objects.get(id=stream_id)
profile_obj = M3UAccountProfile.objects.get(id=profile_id)
new_url = _resolve_live_stream_url(stream_obj, m3u_account, profile_obj)
```

Statt:
```python
stream_info = get_stream_info_for_switch(self.channel_id, stream_id)  # FAILS!
```

### Änderungen in `apps/proxy/live_proxy/input/manager.py`

#### 1. Initialisierung (Zeile ~88-93)
```python
# Add tracking for tried streams and current stream
self.current_stream_id = stream_id
self.current_profile_id = None  # Track current M3U profile ID
self.tried_stream_ids = set()
self.tried_combinations = set()  # Track (stream_id, profile_id) tuples for profile failover
self.last_stream_switch_time = time.time()
```

#### 2. Filter Logik in `_try_next_stream()` (Zeile ~2136)
**ALT:**
```python
untried_streams = [s for s in alternate_streams if s['stream_id'] not in self.tried_stream_ids]
```

**NEU:**
```python
# Filter out stream+profile combinations we've already tried
untried_streams = [
    s for s in alternate_streams 
    if (s['stream_id'], s['profile_id']) not in self.tried_combinations
]
```

#### 3. Direktes Holen der Stream-Info (Zeile ~2250-2280)
**ALT (FEHLERHAFT):**
```python
logger.info(f"Trying next stream ID {stream_id} with profile ID {profile_id} for channel {self.channel_id}")
stream_info = get_stream_info_for_switch(self.channel_id, stream_id)  # FAILS for stream preview!

if 'error' in stream_info or not stream_info.get('url'):
    logger.error(f"Error getting info for stream {stream_id}...")
    continue

new_url = stream_info['url']
new_user_agent = stream_info['user_agent']
new_transcode = stream_info['transcode']
```

**NEU (v0.27.0 Lösung):**
```python
logger.info(f"Trying next stream ID {stream_id} with profile ID {profile_id} for channel {self.channel_id}")

try:
    from apps.channels.models import Stream
    from apps.m3u.models import M3UAccountProfile
    from apps.proxy.live_proxy.url_utils import _resolve_live_stream_url, get_stream_object
    
    stream_obj = Stream.objects.get(id=stream_id)
    profile_obj = M3UAccountProfile.objects.get(id=profile_id)
    
    if not stream_obj.m3u_account:
        logger.error(f"Stream {stream_id} has no M3U account")
        continue
    
    m3u_account = stream_obj.m3u_account
    
    # Get user agent
    new_user_agent = m3u_account.get_user_agent().user_agent
    
    # Generate URL using _resolve_live_stream_url (handles XC and STD accounts)
    new_url = _resolve_live_stream_url(stream_obj, m3u_account, profile_obj)
    
    # Get transcode setting - use get_stream_object to handle both Channel UUID and stream_hash
    try:
        channel_or_stream = get_stream_object(self.channel_id)
        if isinstance(channel_or_stream, Stream):
            # Stream preview - get transcode from stream's profile
            stream_profile = channel_or_stream.get_stream_profile()
        else:
            # Regular channel - get transcode from channel's profile
            stream_profile = channel_or_stream.get_stream_profile()
        new_transcode = not (stream_profile.is_proxy() or stream_profile is None)
    except:
        new_transcode = self.transcode  # Keep current setting on error
    
except Exception as e:
    logger.error(f"Error getting stream info for stream {stream_id} with profile {profile_id}: {e}")
    continue  # Try next combination
```
**ALT:**
```python
# Add to tried streams
self.tried_stream_ids.add(stream_id)
```

**NEU:**
```python
# Add to tried combinations
self.tried_combinations.add((stream_id, profile_id))

# Also update tried_stream_ids for backward compatibility with error messages
self.tried_stream_ids.add(stream_id)
```

#### 4. Tracking bei Stream-Wechsel (Zeile ~2232)
**ALT:**
```python
# Update stream ID tracking
self.current_stream_id = stream_id
```

**NEU:**
```python
# Update stream ID and profile ID tracking
self.current_stream_id = stream_id
self.current_profile_id = profile_id
```

#### 5. URL Update direkt statt update_url() (Zeile ~2280-2290)
**ALT:**
```python
switch_result = self.update_url(new_url, stream_id, profile_id)
if not switch_result:
    logger.error(f"Failed to update URL for stream ID {stream_id}...")
    continue
```

**NEU:**
```python
# Update the URL directly - the main run() loop will handle reconnection
self.url = new_url

# Update tracking variables IMMEDIATELY
self.current_stream_id = stream_id
self.current_profile_id = profile_id
self.last_stream_switch_time = time.time()
```

#### 6. Update current tracking (Zeile ~2266)
**ALT:**
```python
if self.current_stream_id:
    self.tried_stream_ids = {self.current_stream_id}
else:
    self.tried_stream_ids.clear()
```

**NEU:**
```python
if self.current_stream_id and self.current_profile_id:
    self.tried_combinations = {(self.current_stream_id, self.current_profile_id)}
    self.tried_stream_ids = {self.current_stream_id}
else:
    self.tried_combinations.clear()
    self.tried_stream_ids.clear()
```

#### 7. Reset bei stabiler Connection `_note_stable_connection()` (Zeile ~246)
**ALT:**
```python
if self.current_stream_id:
    self.tried_stream_ids = {self.current_stream_id}
else:
    self.tried_stream_ids.clear()

untried_streams = [
    s for s in alternate_streams
    if s['stream_id'] not in self.tried_stream_ids
]
```

**NEU:**
```python
if self.current_stream_id and self.current_profile_id:
    self.tried_combinations = {(self.current_stream_id, self.current_profile_id)}
    self.tried_stream_ids = {self.current_stream_id}
else:
    self.tried_combinations.clear()
    self.tried_stream_ids.clear()

untried_streams = [
    s for s in alternate_streams
    if (s['stream_id'], s['profile_id']) not in self.tried_combinations
]
```

#### 8. Reset bei Failover Rotation (Zeile ~2208)
**ALT:**
```python
def reset_failover_rotation_state(self):
    """Clear tried-stream / wrap bookkeeping after a manual stream change."""
    self.tried_stream_ids = set()
    self._failover_rotation_passes = 0
    self._rotation_cooldown_until = None
```

**NEU:**
```python
def reset_failover_rotation_state(self):
    """Clear tried-stream / wrap bookkeeping after a manual stream change."""
    self.tried_combinations.clear()
    self.tried_stream_ids = set()
    self._failover_rotation_passes = 0
    self._rotation_cooldown_until = None
```

#### 9. Redis Metadata Update mit stream_profile_id (Zeile ~2295-2310)
**ALT:**
```python
self.buffer.redis_client.hset(metadata_key, mapping={
    ChannelMetadataField.STREAM_PROFILE: stream_info['stream_profile'],  # FAILS!
    ChannelMetadataField.STREAM_SWITCH_REASON: "max_retries_exceeded"
})
```

**NEU:**
```python
# Get channel's stream profile ID
from apps.channels.models import Channel
try:
    channel = Channel.objects.get(uuid=self.channel_id)
    stream_profile_id = channel.get_stream_profile().id
except:
    stream_profile_id = 1  # Fallback to default

self.buffer.redis_client.hset(metadata_key, mapping={
    ChannelMetadataField.STREAM_PROFILE: str(stream_profile_id),
    ChannelMetadataField.STREAM_SWITCH_REASON: "profile_failover"
})
```

#### 10. Reset Funktion `reset_failover_rotation_state()` (Zeile ~1810)
`tried_stream_ids` wird weiterhin gepflegt für:
- Backward compatibility
- Error Messages / Logging
- Debugging

Die eigentliche Failover-Logik verwendet aber `tried_combinations`.

## Test-Scenario
1. Stream preview mit stream_id=1187282 startet mit profile_id=582
2. Stream failover wird ausgelöst
3. System versucht profile_id=580 (selbe stream_id=1187282)
4. Falls profile_id=580 auch fehlschlägt, versucht profile_id=581
5. Alle 5 Profiles werden durchiteriert

**Vorher:** Nach Versuch 1 wurden alle Profiles ausgefiltert (alle haben stream_id=1187282)
**Nachher:** Alle 5 Kombinationen werden versucht: (1187282, 582), (1187282, 580), (1187282, 581), (1187282, 583), (1187282, 584)

## Referenz
- Quelle: `Dispatcharr - 27.0/apps/proxy/live_proxy/input/manager.py`
- Zeilen: 91-94, 2131-2240, 244-252, 1805-1810
- Feature: Stream preview failover mit Multi-Profile Support

## Files Modified
- `apps/proxy/live_proxy/input/manager.py` - 7 Stellen geändert
- Patch: `dispatcharr_v0.30.0_tried_combinations_fix.patch`

## Status
✅ Implementiert in v0.30.0 Hauptworkspace
✅ Patch erstellt
⏳ Testing ausstehend


## Zusammenfassung der Bugs

### Bug #5: tried_stream_ids statt tried_combinations
- **Symptom:** "No untried streams available" obwohl 5 Profile verfügbar
- **Ursache:** Filter nur nach stream_id, nicht nach (stream_id, profile_id)
- **Fix:** `tried_combinations` Set mit Tupeln verwenden

### Bug #6: UUID ValidationError in get_stream_info_for_switch()
- **Symptom:** `ValidationError: '"83e7244...92" is not a valid UUID.'`
- **Ursache:** Stream Preview verwendet Stream Hash als channel_id, nicht Channel UUID
- **Funktion:** `get_stream_info_for_switch()` erwartet Channel UUID: `Channel.objects.get(uuid=channel_id)`
- **Fix:** Stream-Info direkt holen wie in v0.27.0:
  - `Stream.objects.get(id=stream_id)`
  - `_resolve_live_stream_url(stream_obj, m3u_account, profile_obj)`
  - `get_stream_object(self.channel_id)` für Transcode-Einstellung

### Bug #7: NoneType has no attribute 'user_agent'
- **Symptom:** `'NoneType' object has no attribute 'user_agent'`
- **Ursache:** `m3u_account.get_user_agent()` gibt `None` zurück wenn kein spezifischer User-Agent konfiguriert
- **Code:** `new_user_agent = m3u_account.get_user_agent().user_agent` → CRASH
- **Fix:** `new_user_agent = m3u_account.get_user_agent_string()` → Verwendet System-Default

## Affected Code Sections
1. **Initialisierung** - Zeile 88-94: `tried_combinations` Set hinzugefügt
2. **Filter Logik** - Zeile 2136: Tupel-Filter statt stream_id-Filter
3. **Stream Info Holen** - Zeile 2250-2280: Direktes DB-Query statt Funktion
4. **User Agent Fix** - Zeile 2270: `get_user_agent_string()` statt `.get_user_agent().user_agent`
5. **Tracking** - Zeile 2232: Tupel zu `tried_combinations` hinzufügen
6. **URL Update** - Zeile 2280-2290: Direktes Update statt `update_url()`
7. **Redis Metadata** - Zeile 2295-2310: stream_profile_id aus Channel holen
8. **Stable Connection** - Zeile 246-252: `tried_combinations` reset
9. **Rotation** - Zeile 2208-2220: `tried_combinations` reset
10. **Reset Funktion** - Zeile 1810: `tried_combinations.clear()`

## Files Modified
- `apps/proxy/live_proxy/input/manager.py` - 10 Stellen geändert
- Patch: `dispatcharr_v0.30.0_stream_preview_failover_fix.patch`

## Status
✅ Implementiert in v0.30.0 Hauptworkspace
✅ Patch erstellt
⏳ Testing ausstehend

## Referenz
- Quelle: `Dispatcharr - 27.0/apps/proxy/live_proxy/input/manager.py`
- Zeilen: 91-94, 2131-2240, 244-252, 1805-1810
- Feature: Stream preview failover mit Multi-Profile Support + UUID-Fix
