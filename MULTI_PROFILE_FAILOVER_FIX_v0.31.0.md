# Multi-Profile Failover Fix - v0.31.0

## 🐛 Problem

**Symptom:**
Wenn ein Stream+Profile failed, werden andere Profiles vom selben Provider NICHT versucht. Es wirkt als wäre der gesamte Provider auf Cooldown, obwohl nur 1 Profile betroffen ist.

**User-Beschreibung:**
> "Ich habe das Gefühl der Cooldown wird für den ganzen Provider gesetzt. Pro Provider habe ich mehrere Profile. Scheinbar werden die anderen Profile gar nicht probiert. Wirkt so als ist der Cooldown je Provider und nicht Provider + Profil."

---

## 🔍 Root Cause

### **Cooldown ist korrekt implementiert:**

```python
# Cooldown Key enthält stream_id + profile_id
cooldown_key = f"live:channel:{channel_id}:stream:{stream_id}:profile:{profile_id}:cooldown"
```

✅ **Cooldown ist per Stream+Profile Kombination!** (Korrekt!)

### **ABER: get_alternate_streams() gibt nur 1 Profile pro Stream zurück!**

**Problem-Code (Zeile ~618-657):**

```python
for stream in streams:
    profiles = [default_profile] + [other_profiles]
    
    selected_profile = None  # ← Problem!
    for profile in profiles:
        if profile_available():
            selected_profile = profile  # ← Nimmt nur EINES!
            break  # ← Stoppt danach!
    
    if selected_profile:
        alternate_streams.append({
            'stream_id': stream.id,
            'profile_id': selected_profile.id  # ← Nur 1 Profile pro Stream!
        })
```

**Resultat:**
```
WatchHD Provider:
- Hat 3 Profiles: 469, 470, 471

get_alternate_streams() returns:
[
  {stream_id: 832438, profile_id: 469}  ← Nur Profile 469!
]

Profiles 470 und 471 fehlen! ❌
```

**Was passiert wenn Profile 469 failed:**

```
1. Profile 469 failed → Cooldown 600s ✅
2. Auto-Failover sucht Alternative
3. get_alternate_streams() gibt Stream 832438 mit Profile 469 zurück
4. Cooldown-Check: Profile 469 auf Cooldown → Skip!
5. Kein anderes WatchHD Profile verfügbar! ❌
6. Wechselt zu komplett anderem Provider

Resultat: WatchHD Profiles 470 und 471 werden NIE versucht!
```

---

## ✅ Lösung

### **Ändere get_alternate_streams() um ALLE verfügbaren Profiles zurückzugeben:**

**Vorher (nur 1 Profile):**
```python
selected_profile = None
for profile in profiles:
    if profile_available():
        selected_profile = profile
        break  # ← Stoppt nach erstem!

if selected_profile:
    alternate_streams.append({
        'stream_id': stream.id,
        'profile_id': selected_profile.id
    })
```

**Nachher (ALLE Profiles):**
```python
available_profiles = []  # ← Sammle ALLE!
for profile in profiles:
    if profile_available():
        available_profiles.append(profile)  # ← Kein break!
        # Continue checking other profiles

# Add ALL available profiles as separate entries
for profile in available_profiles:
    alternate_streams.append({
        'stream_id': stream.id,
        'profile_id': profile.id
    })
```

**Resultat:**
```
WatchHD Provider mit 3 Profiles:

get_alternate_streams() returns:
[
  {stream_id: 832438, profile_id: 469},  ← Profile 1
  {stream_id: 832438, profile_id: 470},  ← Profile 2 ✅ NEU!
  {stream_id: 832438, profile_id: 471},  ← Profile 3 ✅ NEU!
  ...
]
```

---

## 📊 Verhalten Vorher vs. Nachher

### **Scenario: WatchHD hat 3 Profiles (469, 470, 471)**

#### **Vorher (BUG):**

```
Stream 832438 + Profile 469 started
↓
Failed → Cooldown for 469 ✅
↓
Auto-Failover
↓
get_alternate_streams() → [{stream: 832438, profile: 469}]
↓
Cooldown Check: 469 on cooldown → Skip
↓
No WatchHD available! ❌ (Profiles 470, 471 ignored!)
↓
Switch to different provider (e.g., TS-IPTV)
```

**Resultat:** WatchHD Profiles 470 und 471 werden NIEMALS versucht!

#### **Nachher (FIXED):**

```
Stream 832438 + Profile 469 started
↓
Failed → Cooldown for 469 ✅
↓
Auto-Failover
↓
get_alternate_streams() → [
  {stream: 832438, profile: 469},
  {stream: 832438, profile: 470},  ← NEU!
  {stream: 832438, profile: 471}   ← NEU!
]
↓
Cooldown Check:
  - Profile 469 → Cooldown → Skip
  - Profile 470 → Available → TRY! ✅
↓
Stream 832438 + Profile 470 started ✅
```

**Resultat:** Alle verfügbaren Profiles werden versucht!

---

## 🎯 Benefits

### **1. Echtes Multi-Profile Failover**

**Vorher:**
- ❌ Nur 1 Profile pro Stream pro Failover-Iteration
- ❌ Andere Profiles werden ignoriert
- ❌ Wirkt als wäre ganzer Provider gesperrt

**Nachher:**
- ✅ ALLE Profiles werden berücksichtigt
- ✅ Cooldown funktioniert per Stream+Profile
- ✅ Maximale Provider-Nutzung

### **2. Bessere Provider-Auslastung**

**Beispiel: WatchHD mit 3 Profiles (max 2 Connections each):**

**Vorher:**
```
Total capacity: 3 profiles × 2 connections = 6
Actual usage: 1 profile × 2 connections = 2 (33%)
```

**Nachher:**
```
Total capacity: 3 profiles × 2 connections = 6
Actual usage: 3 profiles × 2 connections = 6 (100%)
```

### **3. Reduzierte Provider-Wechsel**

**Vorher:**
```
Profile 469 failed → Switch zu TS-IPTV
(WatchHD Profiles 470, 471 ungenutzt)
```

**Nachher:**
```
Profile 469 failed → Try Profile 470 ✅
Profile 470 works → Stay on WatchHD!
```

---

## 📋 Test Cases

### **Test 1: Multi-Profile Provider**

**Setup:**
```
WatchHD Provider:
- Profile 469 (Default)
- Profile 470
- Profile 471
```

**Test:**
1. Start Channel mit WatchHD Profile 469
2. Simuliere Failure (kill stream)
3. Check Logs für "Found X alternate streams"

**Erwartung:**
```
Before Fix:
Found 49 alternate streams [832438, 1182101, ...]  ← Nur 1x WatchHD!

After Fix:
Found 51 alternate streams [832438, 832438, 832438, 1182101, ...]
                             ↑       ↑       ↑
                          P469    P470    P471  ← 3x WatchHD!
```

### **Test 2: Cooldown Skip mit Alternatives**

**Setup:**
```
WatchHD:
- Profile 469 → On Cooldown
- Profile 470 → Available
```

**Test:**
1. Set Cooldown für Profile 469
2. Trigger Failover
3. Check: Versucht es Profile 470?

**Erwartung:**
```
Before Fix:
Stream 832438 with profile 469 is on cooldown
No WatchHD available → Switch to different provider ❌

After Fix:
Stream 832438 with profile 469 is on cooldown (skip)
Trying next stream ID 832438 with profile ID 470 ✅
```

### **Test 3: Single-Profile Provider (Regression)**

**Setup:**
```
Provider mit nur 1 Profile (wie früher)
```

**Test:**
1. Start Channel
2. Trigger Failover

**Erwartung:**
```
Before Fix: 1 entry in alternate_streams
After Fix:  1 entry in alternate_streams
→ Kein Unterschied! ✅ (Backward compatible)
```

---

## 🔧 Installation

### **Patch anwenden:**

```bash
# Im Dispatcharr Root-Verzeichnis
git apply dispatcharr_v0.31.0_multi_profile_failover_fix.patch

# Service neustarten
docker-compose restart
# oder
systemctl restart dispatcharr
```

---

## 📝 Log-Ausgaben

### **Vorher (nur 1 Profile pro Stream):**

```
DEBUG Found available profile 469 for stream 832438
INFO Found 49 alternate streams with available connections
```

### **Nachher (ALLE Profiles pro Stream):**

```
DEBUG Found available profile 469 for stream 832438
DEBUG Found available profile 470 for stream 832438
DEBUG Found available profile 471 for stream 832438
DEBUG Added 3 profile(s) for stream ID 832438
INFO Found 51 alternate streams with available connections
```

**Mehr Streams in Liste = Mehr Optionen für Failover!** ✅

---

## ⚠️ Edge Cases

### **1. Profile Connection Limits**

**Szenario:**
```
Profile 469: 2/2 connections (full)
Profile 470: 1/2 connections (available)
```

**Verhalten:**
```
get_alternate_streams() returns:
[
  {stream: 832438, profile: 470}  ← Nur verfügbares!
]
```

✅ **Korrekt!** Volle Profiles werden nicht hinzugefügt.

### **2. Alle Profiles voll**

**Szenario:**
```
Profile 469: 2/2 (full)
Profile 470: 2/2 (full)
Profile 471: 2/2 (full)
```

**Verhalten:**
```
get_alternate_streams() returns:
[]  ← Kein WatchHD!
```

✅ **Korrekt!** Provider wird übersprungen.

### **3. Keine Redis Connection**

**Szenario:**
```
Redis unavailable
```

**Verhalten:**
```
# Fail-open: Add ALL profiles (no connection check)
get_alternate_streams() returns:
[
  {stream: 832438, profile: 469},
  {stream: 832438, profile: 470},
  {stream: 832438, profile: 471}
]
```

✅ **Korrekt!** Resilient fallback.

---

## 🎯 Impact

### **Performance:**

**CPU/Memory:** 
- ✅ Minimal increase (loop continues statt break)
- ✅ No significant performance impact

**Network:**
- ✅ Same (nur mehr Einträge in Liste, keine zusätzlichen Requests)

**Database:**
- ✅ Same (keine zusätzlichen Queries)

### **Behavior:**

**Failover Quality:**
- ✅ Drastisch verbessert
- ✅ Mehr Optionen = stabilere Streams
- ✅ Provider werden optimal ausgenutzt

**User Experience:**
- ✅ Weniger Provider-Wechsel
- ✅ Schnellere Stabilisierung
- ✅ Bessere Stream-Qualität (mehr High-Quality Profiles verfügbar)

---

## 🚀 Real-World Example

### **Scenario: High-Load Situation**

**Setup:**
```
5 Channels using WatchHD
WatchHD has 3 Profiles (2 connections each = 6 total)

Current usage: 5/6 connections
```

**Before Fix:**
```
Channel 6 starts → Tries Profile 469 (Default) → FULL!
→ No WatchHD available (Profiles 470, 471 ignored!)
→ Switch to TS-IPTV
```

**After Fix:**
```
Channel 6 starts → Tries Profile 469 → FULL!
→ Tries Profile 470 → FULL!
→ Tries Profile 471 → Available! (1/2) ✅
→ Uses WatchHD Profile 471!
```

**Result:** 6/6 WatchHD connections used (100% efficiency!) 🎉

---

## ✨ Summary

**Problem:** `get_alternate_streams()` returned only 1 profile per stream
**Solution:** Return ALL available profiles per stream
**Result:** True multi-profile failover, better provider utilization, fewer provider switches

**Status:** ✅ **Ready for Production**

---

**Version:** v0.31.0
**Date:** 2026-09-24
**Files Changed:** `apps/proxy/live_proxy/url_utils.py` (1 function)
**Backward Compatible:** ✅ Yes
**Breaking Changes:** ❌ None
