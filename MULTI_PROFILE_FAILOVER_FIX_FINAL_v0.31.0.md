# Multi-Profile Failover Fix v0.31.0

## 🎯 Problem

Multi-Profile Failover funktionierte in v0.27/v0.29, aber nicht mehr in v0.30/v0.31.

**Symptom:** Nur 1 Profile pro Provider wird beim Failover probiert, danach springt er zum nächsten Provider.

**Erwartetes Verhalten:** ALLE Profiles eines Providers werden probiert, bevor zum nächsten Provider gewechselt wird.

---

## 🔍 Root Cause Analysis

### Was ist in v0.30.0 passiert?

In v0.30.0 wurde `order_alternates_from_current()` **NEU** eingeführt für Stream-Rotation:

**Grund (CHANGELOG v0.30.0):**
> "Live proxy failover now walks backup streams in channel order. After a stable session on a backup stream, tried_stream_ids is cleared so rotation continues from the current position (stream 2 → 3 → 4 → 1) instead of jumping back to stream 1."

**Design-Ziel:** Rotation A→B→C→D→A statt Zurückspringen zu Stream 1 ✅

**Bug:** Die Implementierung ging davon aus, dass **1 Stream = 1 Entry** ist, aber mit Multi-Profile Support hat **1 Stream = mehrere Entries**!

---

## 🐛 Der Bug im Detail

### Problematischer Code (Zeile 449-475 in url_utils.py):

```python
def order_alternates_from_current(...):
    # BUG: Dictionary überschreibt mehrere Profiles desselben Streams!
    alt_by_id = {entry['stream_id']: entry for entry in alternate_streams}
    #           ☝️ Dictionary keeps only LAST entry per stream_id!
```

### Beispiel:

**Input von `get_alternate_streams()`:**
```python
[
  {'stream_id': 832438, 'profile_id': 469, 'name': 'WatchHD'},  # Profile 1
  {'stream_id': 832438, 'profile_id': 470, 'name': 'WatchHD'},  # Profile 2 ← Überschreibt 469!
  {'stream_id': 832438, 'profile_id': 471, 'name': 'WatchHD'},  # Profile 3 ← Überschreibt 470!
]
```

**Dictionary Result:**
```python
alt_by_id = {
  832438: {'stream_id': 832438, 'profile_id': 471, 'name': 'WatchHD'}  # ← Nur das LETZTE!
}
```

**Output nach order_alternates_from_current():**
```python
[
  {'stream_id': 832438, 'profile_id': 471, 'name': 'WatchHD'}  # ← Profiles 469 + 470 verloren!
]
```

### Impact:

1. `get_alternate_streams()` gibt korrekt alle 3 Profiles zurück ✅
2. `order_alternates_from_current()` reduziert auf nur 1 Profile ❌
3. Failover probiert nur Profile 471, nicht 469 und 470 ❌

---

## ✅ Die Lösung

**Ändere Dictionary zu List-basierter Gruppierung:**

```python
def order_alternates_from_current(
    alternate_streams: List[dict],
    ordered_stream_ids: List[int],
    current_stream_id: Optional[int],
) -> List[dict]:
    """
    Reorder failover candidates to start after the current stream in channel order,
    wrapping around. Preserves ALL profiles for each stream.
    
    BUGFIX v0.31.0: Changed from dict (1 profile per stream) to list (ALL profiles per stream)
    to support multi-profile failover within the same provider.
    """
    if not alternate_streams or not ordered_stream_ids or current_stream_id is None:
        return alternate_streams

    # BUGFIX: Group by stream_id (keep ALL profiles per stream!)
    # OLD: alt_by_id = {entry['stream_id']: entry for entry in alternate_streams}
    #      ☝️ Dictionary only kept LAST profile per stream!
    # NEW: Use list to preserve ALL profiles per stream
    alt_by_id = {}
    for entry in alternate_streams:
        sid = entry['stream_id']
        if sid not in alt_by_id:
            alt_by_id[sid] = []
        alt_by_id[sid].append(entry)

    try:
        current_index = ordered_stream_ids.index(current_stream_id)
    except ValueError:
        return alternate_streams

    rotated = []
    for offset in range(1, len(ordered_stream_ids)):
        stream_id = ordered_stream_ids[(current_index + offset) % len(ordered_stream_ids)]
        entries = alt_by_id.get(stream_id, [])  # Get ALL profiles for this stream
        rotated.extend(entries)  # Add ALL profiles (not just first one)
    return rotated
```

---

## 📊 Vorher/Nachher Vergleich

### Vorher (v0.30.0):

```
Provider WatchHD: Profiles 469, 470, 471
Provider Backup: Profiles 580, 581

Failover Sequence:
1. Stream 832438 + Profile 471 (nur dieses!) ❌
2. Stream 999999 + Profile 580
3. Stream 999999 + Profile 581

❌ Profiles 469 und 470 wurden nie probiert!
```

### Nachher (v0.31.0):

```
Provider WatchHD: Profiles 469, 470, 471
Provider Backup: Profiles 580, 581

Failover Sequence:
1. Stream 832438 + Profile 469 ✅
2. Stream 832438 + Profile 470 ✅
3. Stream 832438 + Profile 471 ✅
4. Stream 999999 + Profile 580
5. Stream 999999 + Profile 581

✅ ALLE Profiles von Provider 1 werden probiert vor Provider 2!
```

---

## 🧪 Test-Szenario mit Cooldown

### Setup:

```
Channel "Sport HD":
- Stream 1 (Provider WatchHD): Profiles 469, 470, 471
- Stream 2 (Provider Backup): Profiles 580, 581

Settings:
- stream_cooldown_enabled = True
- stream_cooldown_seconds = 600 (10 Minuten)
```

### Ablauf:

**T+0s:** Stream startet mit 832438 + Profile 469
```
✅ Connection successful
```

**T+120s:** Profile 469 max_connections erreicht
```
❌ Connection failed
✅ Cooldown gesetzt: stream 832438 + profile 469 → 600s
```

**T+121s:** Auto-Failover startet
```
1. get_alternate_streams() returns:
   [
     {stream_id: 832438, profile_id: 470},  ← Profile 2 ✅
     {stream_id: 832438, profile_id: 471},  ← Profile 3 ✅
     {stream_id: 999999, profile_id: 580},
     {stream_id: 999999, profile_id: 581}
   ]

2. order_alternates_from_current() preserves ALL profiles:
   Output = same as input ✅

3. manager.py filters cooldowns:
   - Checkt stream 832438 + profile 470 → NOT on cooldown ✅
   - Tries stream 832438 + profile 470 ✅
```

**T+140s:** Profile 470 failed auch
```
❌ Connection failed
✅ Cooldown gesetzt: stream 832438 + profile 470 → 600s
```

**T+141s:** Auto-Failover startet
```
1. get_alternate_streams() returns:
   [
     {stream_id: 832438, profile_id: 471},  ← Profile 3 (letztes!) ✅
     {stream_id: 999999, profile_id: 580},
     {stream_id: 999999, profile_id: 581}
   ]

2. manager.py filters cooldowns:
   - Checkt stream 832438 + profile 471 → NOT on cooldown ✅
   - Tries stream 832438 + profile 471 ✅
```

**T+160s:** Profile 471 failed auch (alle WatchHD Profiles erschöpft)
```
❌ Connection failed
✅ Cooldown gesetzt: stream 832438 + profile 471 → 600s
```

**T+161s:** Auto-Failover startet
```
1. get_alternate_streams() returns:
   [
     {stream_id: 999999, profile_id: 580},  ← Backup Provider ✅
     {stream_id: 999999, profile_id: 581}
   ]

2. Tries stream 999999 + profile 580 ✅
✅ Connection successful → Backup Provider wird genutzt
```

---

## 🎯 Zusammenfassung

### Was wurde gefixt:

1. ✅ `order_alternates_from_current()` preserviert jetzt **ALLE** Profiles pro Stream
2. ✅ Rotation-Logik (A→B→C→D→A) bleibt erhalten
3. ✅ Multi-Profile Failover funktioniert wieder wie in v0.27/v0.29
4. ✅ Cooldown-Logik in manager.py bleibt unverändert (war bereits korrekt)

### Was wurde NICHT geändert:

- ❌ Keine Änderungen an manager.py nötig
- ❌ Keine Änderungen an Cooldown-Logik nötig
- ❌ Keine Änderungen an get_alternate_streams() nötig (gibt bereits alle Profiles zurück)

### Die einzige Änderung:

**File:** `apps/proxy/live_proxy/url_utils.py`
**Function:** `order_alternates_from_current()` (Zeile 449-483)
**Change:** Dictionary → List-basierte Gruppierung um alle Profiles zu preservieren

---

## 📝 Testing Checklist

- [ ] Provider mit 3+ Profiles → alle werden beim Failover probiert
- [ ] Cooldown wird per Stream+Profile gesetzt (nicht global)
- [ ] Rotation A→B→C→D→A funktioniert weiterhin
- [ ] Nach stabilem Stream wird tried_combinations geleert
- [ ] Manual stream switch setzt KEIN Cooldown (dank _manual_switch Flag)
- [ ] LAST RESORT löscht Cooldowns wenn alle Kombinationen erschöpft

---

## 🚀 Deployment

**Files Changed:**
- `apps/proxy/live_proxy/url_utils.py` (1 function: order_alternates_from_current)

**No Database Changes**
**No Frontend Changes**
**No Config Changes**

**Restart Required:** Yes (Django app reload)

---

## 📚 Related Fixes

Diese Änderung ist Teil des v0.31.0 Bugfix-Sets:

1. ✅ **Standard M3U HTTP Proxy** (Frontend only)
2. ✅ **Manual Stream Switch Cooldown** (manager.py)
3. ✅ **Multi-Profile Failover** (url_utils.py) ← Dieses Fix

Alle drei Fixes sind unabhängig voneinander und können separat deployed werden.
