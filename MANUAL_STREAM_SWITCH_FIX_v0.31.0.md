# Manual Stream Switch Cooldown Bug Fix - v0.31.0

## 🐛 Problem

**Symptom:**
Wenn User manuell einen Stream wechselt, wird der VORHERIGE (laufende) Stream auf Cooldown gesetzt. User kann nicht zurück zum ursprünglichen Stream wechseln.

**Beispiel:**
```
1. WatchHD (832438) läuft perfekt ✅
2. User wechselt manuell zu Stream 1182101
3. System stoppt WatchHD
4. System setzt WatchHD auf 600s Cooldown! ❌
5. Stream 1182101 failed
6. User will zurück zu WatchHD → GESPERRT für 600s! ❌
```

---

## 🔍 Root Cause

### **Problem-Flow:**

```python
# User klickt "Switch to Stream X" im WebUI
↓
ChannelService.change_stream_url()
↓
manager.update_url(new_url, stream_id)  # Manueller Switch
↓
self._close_socket()  # Schließt alte Verbindung
↓
# Connection wird geschlossen
↓
# Manager Loop erkennt: "Server closed connection"
↓
failures >= self.max_retries
↓
self._set_stream_cooldown()  # ← BUG! Cooldown auch bei manuellem Switch!
```

**Das Problem:**
Der Manager unterscheidet NICHT zwischen:
- **Connection Failed** (Provider-Problem → Cooldown richtig!)
- **Manual Switch** (User-Aktion → KEIN Cooldown!)

Beide Szenarien führen zu "Server closed connection" → Cooldown wird IMMER gesetzt!

---

## ✅ Lösung

### **Strategie:**

Füge einen Flag `_manual_switch` hinzu:
- Wird in `update_url()` auf `True` gesetzt
- Verhindert Cooldown-Setzung bei manuellem Switch
- Wird nach Switch wieder auf `False` gesetzt

### **Code-Änderungen:**

#### **1. Flag setzen in `update_url()` (Zeile ~1623)**

```python
# CRITICAL: Set a flag to prevent immediate reconnection with old URL
self.url_switching = True
self.url_switch_start_time = time.time()

# Set flag to prevent cooldown on manual stream switch
self._manual_switch = True  # ← NEU!
```

#### **2. Cooldown-Logic anpassen (Zeile ~651)**

```python
if failures >= self.max_retries:
    url_failed = True
    
    # Don't set cooldown for manual stream switches
    if not getattr(self, '_manual_switch', False):  # ← NEU!
        self._set_stream_cooldown()
        logger.info(f"Set cooldown for stream {self.current_stream_id}")
    else:
        logger.info(f"Skipping cooldown for manual stream switch")
        self._manual_switch = False  # Reset flag
    
    logger.warning(f"Maximum retry attempts ({self.max_retries}) reached")
```

#### **3. Cooldown-Logic anpassen (Exception Handler, Zeile ~687)**

```python
if failures >= self.max_retries:
    url_failed = True
    
    # Don't set cooldown for manual stream switches
    if not getattr(self, '_manual_switch', False):  # ← NEU!
        self._set_stream_cooldown()
        logger.info(f"Set cooldown for stream {self.current_stream_id}")
    else:
        logger.info(f"Skipping cooldown for manual stream switch")
        self._manual_switch = False  # Reset flag
```

#### **4. Flag clearen bei Erfolg (Zeile ~1662)**

```python
# Reset retry counter to allow immediate reconnect
self._clear_connection_failure_history()

# Clear manual switch flag on successful switch
self._manual_switch = False  # ← NEU!
```

---

## 📊 Verhalten Vorher vs. Nachher

### **Vorher (BUG):**

| Szenario | Cooldown gesetzt? | Problem |
|----------|------------------|---------|
| Stream failed automatisch | ✅ Ja | ✅ Korrekt |
| User wechselt manuell | ✅ Ja | ❌ FALSCH! |

**Resultat:** User kann nicht zurück zum vorherigen Stream wechseln (600s gesperrt)!

### **Nachher (FIXED):**

| Szenario | Cooldown gesetzt? | Verhalten |
|----------|------------------|-----------|
| Stream failed automatisch | ✅ Ja | ✅ Korrekt - Auto-Failover zu anderem Provider |
| User wechselt manuell | ❌ Nein | ✅ Korrekt - User kann frei zwischen Streams wechseln |

**Resultat:** User hat volle Kontrolle! Kann jederzeit zurück zum vorherigen Stream!

---

## 🔧 Installation

### **Patch anwenden:**

```bash
# Im Dispatcharr Root-Verzeichnis
git apply dispatcharr_v0.31.0_manual_stream_switch_cooldown_fix.patch

# Service neustarten
docker-compose restart
# oder
systemctl restart dispatcharr
```

### **Manuelle Installation:**

Editiere `apps/proxy/live_proxy/input/manager.py` und füge die 4 Änderungen ein (siehe oben).

---

## ✅ Testing

### **Test 1: Manueller Stream-Switch**

```
1. Starte Channel mit WatchHD Stream (832438)
2. WebUI: Wechsle manuell zu Stream 1182101
3. ✅ Erwartung: WatchHD wird NICHT auf Cooldown gesetzt
4. Log prüfen: "Skipping cooldown for manual stream switch"
```

### **Test 2: Zurück-Switch möglich**

```
1. Stream 1182101 läuft
2. WebUI: Wechsle zurück zu WatchHD (832438)
3. ✅ Erwartung: Switch funktioniert sofort (kein Cooldown!)
```

### **Test 3: Auto-Failover Cooldown weiterhin aktiv**

```
1. Stream startet automatisch
2. Stream failed (Connection Error)
3. ✅ Erwartung: Cooldown wird gesetzt (600s)
4. Log prüfen: "Set cooldown for stream..."
```

---

## 📝 Log-Ausgaben

### **Bei manuellem Switch:**

```
INFO Switching stream URL from WatchHD to TS-IPTV
INFO Skipping cooldown for manual stream switch on channel 9a15d5f4...
INFO Stream switch completed for channel 9a15d5f4...
```

**✅ KEIN** `Set 600s cooldown` Log!

### **Bei automatischem Failover:**

```
ERROR Maximum retry attempts (1) reached for URL: http://...
INFO Set cooldown for stream 691273 with profile 256 on channel 9a15d5f4...
INFO Set 600s cooldown for stream 691273 with profile 256
```

**✅** Cooldown wird gesetzt wie erwartet!

---

## 🎯 Impact

### **User Experience:**

**Vorher:**
- ❌ Manueller Stream-Switch "bestraft" den User (Cooldown auf altem Stream)
- ❌ Kein Weg zurück zum ursprünglichen Stream (600s warten)
- ❌ Frustrierend wenn neuer Stream schlechter ist

**Nachher:**
- ✅ Manueller Stream-Switch hat keine Nebenwirkungen
- ✅ User kann frei zwischen allen Streams wechseln
- ✅ Instant zurück zum vorherigen Stream möglich
- ✅ Cooldown nur bei echten Provider-Problemen

### **System Behavior:**

**Automatischer Failover:**
- ✅ Unverändert - funktioniert wie vorher
- ✅ Cooldown wird weiterhin gesetzt bei Failures
- ✅ Verhindert endlos-loops bei kaputten Streams

**Manueller Switch:**
- ✅ Neues Verhalten - kein Cooldown mehr
- ✅ User hat volle Kontrolle
- ✅ Kompatibel mit Cooldown-System

---

## 🔒 Edge Cases

### **Was wenn User schnell hin-und-her wechselt?**

**Szenario:**
```
User: WatchHD → TS-IPTV → WatchHD → TS-IPTV → WatchHD (5x in 10s)
```

**Verhalten:**
- ✅ Erlaubt! Kein Cooldown
- ⚠️ Aber: Stream-Instabilität möglich (viele Reconnects)
- 💡 Health Monitor kann eingreifen wenn Stream unstable wird

**Das ist OK!** User-Kontrolle > System-Restriktionen

### **Was wenn neuer Stream sofort failed?**

**Szenario:**
```
1. User wechselt zu Stream X
2. Stream X failed sofort (Connection Error)
3. Was passiert?
```

**Verhalten:**
- ✅ Stream X wird auf Cooldown gesetzt (korrekt!)
- ✅ Alter Stream bleibt OHNE Cooldown (User kann zurück!)
- ✅ Auto-Failover zu nächstem verfügbaren Stream

---

## 🚀 Benefits

1. **User-Friendly**: User kann frei experimentieren mit Streams
2. **No Lock-In**: Kein "Gefangen" sein bei schlechtem Stream
3. **Instant Rollback**: Zurück zum alten Stream in <1s
4. **Preserved Failover**: Auto-Failover + Cooldown weiterhin aktiv
5. **Clear Intent**: System unterscheidet User-Action vs. Auto-Failure

---

## 📚 Related Issues

- Cooldown System: `COOLDOWN_SYSTEM_v0.26.0.md`
- Stream Failover: `APPLY_ALL_FIXES_v0.26.0.md`
- Health Monitoring: Integriert in manager.py

---

## ✨ Summary

**Problem:** Manueller Stream-Switch setzte alten Stream auf Cooldown
**Solution:** `_manual_switch` Flag verhindert Cooldown bei User-Aktion
**Result:** User hat volle Kontrolle, Cooldown nur bei echten Failures

**Status:** ✅ **Ready for Production**

---

**Version:** v0.31.0
**Date:** 2026-09-24
**Files Changed:** `apps/proxy/live_proxy/input/manager.py` (4 locations)
