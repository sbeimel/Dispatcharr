# Bug Fix: Stream Preview Failover - tried_combinations Tracking

## Problem
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

## Lösung (aus v0.27.0)
Tracking von `(stream_id, profile_id)` Tupeln statt nur `stream_id`.

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

#### 3. Tracking bei Stream-Wechsel (Zeile ~2232)
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

#### 4. Update current tracking (Zeile ~2266)
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

#### 5. Reset bei stabiler Connection `_note_stable_connection()` (Zeile ~246)
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

#### 6. Reset bei Failover Rotation (Zeile ~2208)
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

#### 7. Reset Funktion `reset_failover_rotation_state()` (Zeile ~1810)
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

## Warum `tried_stream_ids` beibehalten?
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
