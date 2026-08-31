# 🐛 Bug Fix: Cooldown-Key Pattern Mismatch

## Problem gefunden! 🎯

### **Symptom:**
Cooldown wird gesetzt, aber **NICHT gescannt** beim Stream-Start!

Logs zeigen:
```
14:21:50,413 INFO Set 600s cooldown for stream 1187282 with profile 579 ✅
14:21:50,139 INFO Previewing stream directly: 1187282 ❌ Kein [COOLDOWN] Log!
```

---

## Root Cause Analysis

### **Was passiert:**

**1. Cooldown wird gesetzt** (in `manager.py`):
```python
# redis_keys.py definiert:
def stream_cooldown(channel_id, stream_id, profile_id):
    return f"live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown"
    #                                                                    ^^^^^^^^^ SUFFIX!
```

**Redis Key:**
```
live:channel:83e7244...57a92:stream:1187282:profile:579:cooldown
                                                          ^^^^^^^^
```

**2. Unser Patch scannt FALSCH** (in `url_utils.py`):
```python
cooldown_pattern = f"live:channel:{channel_id}:stream:{stream.id}:profile:*"
#                                                                           ^ FEHLT :cooldown!
```

**Problem:**
- Pattern endet mit `:profile:*`
- Keys enden mit `:profile:579:cooldown`
- **KEIN MATCH!** ❌

---

## Vergleich mit v0.27.0

### **v0.27.0 (funktioniert):**

**Key Format:**
```python
# redis_keys.py:
return f"live:cooldown:stream:{stream_id}:profile:{profile_id}"
# KEIN :cooldown Suffix!
```

**Scan Pattern:**
```python
# url_utils.py:
cooldown_pattern = f"live:cooldown:stream:{stream_id}:profile:*"
# Matcht! ✅
```

**Redis Key:**
```
live:cooldown:stream:1187282:profile:579
                                    ^^^^ Profile-ID ist das LETZTE Element
```

### **v0.30.0 (Problem):**

**Key Format:**
```python
# redis_keys.py:
return f"live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown"
# HAT :cooldown Suffix!
```

**Unser Scan Pattern (FALSCH):**
```python
# url_utils.py:
cooldown_pattern = f"live:channel:{channel_id}:stream:{stream.id}:profile:*"
# Matcht NICHT! ❌
```

**Redis Key:**
```
live:channel:83e7244...57a92:stream:1187282:profile:579:cooldown
                                                    ^^^^ Profile-ID ist NICHT das letzte Element!
```

---

## Die Lösung ✅

### **Pattern muss `:cooldown` Suffix enthalten!**

**Korrekter Code:**
```python
# url_utils.py (3 Stellen!):

# 1. Stream Preview Path:
cooldown_pattern = f"live:channel:{channel_id}:stream:{stream.id}:profile:*:cooldown"
#                                                                           ^^^^^^^^^^ ADD!

# 2. Channel Path:
cooldown_pattern = f"live:channel:{channel_id}:stream:{ch_stream.id}:profile:*:cooldown"
#                                                                              ^^^^^^^^^^ ADD!

# 3. Parts Length Check:
if len(parts) >= 8:  # War 7, jetzt 8 wegen extra :cooldown
    profile_id_from_key = int(parts[6])  # Index bleibt gleich!
```

**LAST RESORT in manager.py:**
```python
cooldown_pattern = f"live:channel:{self.channel_id}:stream:{stream_id}:profile:*:cooldown"
#                                                                                ^^^^^^^^^^ ADD!
```

---

## Warum `parts[6]` Index bleibt gleich?

**Key Struktur:**
```
live:channel:83e7244...57a92:stream:1187282:profile:579:cooldown
 0      1           2        3       4        5      6     7
```

**Index Mapping:**
- `parts[0]` = `live`
- `parts[1]` = `channel`
- `parts[2]` = `{channel_id}`
- `parts[3]` = `stream`
- `parts[4]` = `{stream_id}`
- `parts[5]` = `profile`
- **`parts[6]` = `{profile_id}`** ← Hier!
- `parts[7]` = `cooldown`

**Length Check:**
```python
if len(parts) >= 8:  # 8 Teile: 0-7
    profile_id_from_key = int(parts[6])  # Korrekt!
```

---

## Files geändert

### 1. `apps/proxy/live_proxy/url_utils.py`
**2 Stellen:**
- Stream Preview Cooldown-Check (Zeile ~93)
- Channel Cooldown-Check (Zeile ~215)

**Änderungen:**
```diff
-cooldown_pattern = f"live:channel:{channel_id}:stream:{stream.id}:profile:*"
+cooldown_pattern = f"live:channel:{channel_id}:stream:{stream.id}:profile:*:cooldown"

-if len(parts) >= 7:
+if len(parts) >= 8:
```

### 2. `apps/proxy/live_proxy/input/manager.py`
**1 Stelle:**
- LAST RESORT Cooldown Clear (Zeile ~2262)

**Änderungen:**
```diff
-cooldown_pattern = f"live:channel:{self.channel_id}:stream:{stream_id}:profile:*"
+cooldown_pattern = f"live:channel:{self.channel_id}:stream:{stream_id}:profile:*:cooldown"
```

---

## Testing

### **Nach dem Fix solltest du sehen:**

**Bei Stream Start mit aktiven Cooldowns:**
```
14:21:50,139 INFO Previewing stream directly: 1187282
[COOLDOWN] Skipping profile 579 for stream 1187282 on reconnect - blocked for 9m 47s more ✅
[COOLDOWN] Skipping profile 582 for stream 1187282 on reconnect - blocked for 9m 37s more ✅
[COOLDOWN] Selected non-cooled profile 580 for stream 1187282 ✅
14:21:50,157 INFO Channel using stream ID 1187282, profile ID 580
```

**Bei LAST RESORT:**
```
[COOLDOWN] LAST RESORT: All 5 stream/profile combinations tried - clearing cooldowns ✅
[COOLDOWN] LAST RESORT: Cleared 5 cooldown keys for channel 83e7244...57a92 ✅
```

---

## Installation

```bash
# Apply Fix
cd /path/to/dispatcharr
patch -p1 < dispatcharr_v0.30.0_COOLDOWN_KEY_FIX.patch

# Rebuild (Python Code-Änderung)
docker compose build --no-cache
docker compose up -d

# Watch Logs
docker compose logs -f --tail=100 | grep -i cooldown
```

---

## Warum ist das passiert?

**v0.27.0 → v0.30.0 Änderung:**
1. Key-Format geändert: Global → Channel-specific
2. Suffix `:cooldown` hinzugefügt für bessere Klarheit
3. **ABER:** Unser Patch verwendete das alte Pattern-Denken!

**Lesson Learned:**
- Immer das **exakte Key-Format** aus `redis_keys.py` prüfen
- Pattern muss **EXAKT** dem Key-Format entsprechen
- Wildcards (`*`) matchen nur **innerhalb** eines Segments, nicht über Trennzeichen hinweg!

---

## Status

- ✅ Bug identifiziert
- ✅ Root Cause gefunden (Pattern Missing `:cooldown`)
- ✅ Fix implementiert (3 Stellen)
- ✅ Patch erstellt
- ⏳ Testing pending

**Patch File:** `dispatcharr_v0.30.0_COOLDOWN_KEY_FIX.patch`

---

**Created:** 2026-06-18  
**Bug:** Cooldown-Key Pattern Mismatch  
**Impact:** HIGH - Cooldown-Check funktionierte nicht!  
**Fix:** Add `:cooldown` suffix to all scan patterns
