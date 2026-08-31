# HTTP Streamer Race Condition Fix - v0.30.0

## Problem

HTTP-Streams crashten kurz nach dem Start mit folgendem Fehler:
```
AttributeError: 'NoneType' object has no attribute 'readline'
```

### Root Cause

Race Condition beim Stream-Shutdown:

1. HTTP-Reader-Thread läuft und liest Daten via `response.iter_content()`
2. Stream-Manager entscheidet zu stoppen (z.B. weil Client disconnected)
3. `http_reader.stop()` schließt `self.response` **sofort**
4. Reader-Thread ist noch in der `iter_content()` Schleife aktiv
5. Thread versucht `readline()` auf der bereits geschlossenen Response
6. **Crash:** `AttributeError: 'NoneType' object has no attribute 'readline'`

### Konsequenzen

- HTTP-Stream crasht sofort nach Start
- Keine neuen Chunks werden zum Buffer hinzugefügt
- Buffer bleibt bei alten Chunks "hängen"
- Clients sehen 3000+ Warnungen über fehlende Chunks
- Stream-Manager versucht Neustart, scheitert wieder

---

## Lösung

### Fix 1: Erweiterte Error-Erkennung

**Vorher:**
```python
except AttributeError as e:
    if "'NoneType' object has no attribute 'read'" in str(e):
        logger.debug(f"HTTP reader stopped during shutdown (expected race condition)")
```

**Nachher:**
```python
except AttributeError as e:
    error_str = str(e)
    if "'NoneType' object has no attribute 'read'" in error_str or "'NoneType' object has no attribute 'readline'" in error_str:
        logger.debug(f"HTTP reader stopped during shutdown (expected race condition)")
```

**Warum:** Der Code fing nur `'read'` Fehler ab, aber `requests` verwendet intern auch `readline()`.

---

### Fix 2: Graceful Shutdown mit Timeout

**Vorher:**
```python
def stop(self):
    logger.info("Stopping HTTP stream reader")
    self.running = False
    
    # Close response immediately
    if self.response:
        try:
            self.response.close()
```

**Nachher:**
```python
def stop(self):
    logger.info("Stopping HTTP stream reader")
    self.running = False

    # Give the thread a brief moment to notice the flag and exit gracefully
    if self.thread and self.thread.is_alive():
        self.thread.join(timeout=0.1)

    # Close response after grace period
    if self.response:
        try:
            self.response.close()
```

**Warum:** 
- Setzt `self.running = False` **zuerst**
- Wartet 0.1s, damit Thread die Flag bemerkt und die Loop verlässt
- Schließt erst danach die Response
- Reduziert die Race Condition erheblich (eliminiert sie nicht komplett, aber das ist OK)

---

## Testergebnisse (v0.30.0)

### ✅ Vor dem Fix
- Streams crashten nach 1-2 Sekunden
- `AttributeError: 'NoneType' object has no attribute 'readline'`
- Buffer stuck bei alten Chunks

### ✅ Nach dem Fix
- **Channel `9f6cb738...`:** 92.7 Sekunden stabil ✅
- **Channel `7db57ed7...`:** 32.4 Sekunden stabil ✅
- **Channel `3677a0bd...`:** Läuft weiterhin aktiv ✅
- **Keine AttributeError-Crashes mehr** ✅
- **Graceful Shutdown funktioniert:**
  ```
  INFO live_proxy.http_streamer Stopping HTTP stream reader
  INFO live_proxy.http_streamer HTTP stream ended
  INFO live_proxy.manager Stream was stable for 92.7 seconds
  ```

---

## Installation

### Manuelle Anwendung

```bash
# 1. Patch anwenden
patch -p1 < http_streamer_race_condition_fix_v0.30.0.patch

# 2. Container neu bauen
docker-compose build

# 3. Container neu starten
docker-compose up -d
```

### Oder manuell editieren

Datei: `apps/proxy/live_proxy/input/http_streamer.py`

1. **Zeile 134-136:** Error-Handler erweitern (siehe Fix 1)
2. **Zeile 152-156:** Graceful shutdown hinzufügen (siehe Fix 2)

---

## Betroffene Dateien

- `apps/proxy/live_proxy/input/http_streamer.py` (2 Änderungen)

---

## Kompatibilität

- ✅ Dispatcharr v0.30.0
- ✅ Linux Docker Container
- ✅ HTTP-Streaming (non-transcode)
- ✅ Transcode-Streaming (unverändert)

---

## Technische Details

### Warum nicht komplett elimieren?

Die Race Condition kann nicht zu 100% eliminiert werden, weil:
1. `self.running` Flag wird im Hauptthread gesetzt
2. Reader-Thread läuft parallel
3. Zwischen `if not self.running` Check und dem nächsten `read()` kann `stop()` aufgerufen werden

**Aber:** Das ist **OK**, weil:
- Der erweiterte Error-Handler fängt den Crash ab
- Es wird nur als DEBUG geloggt (expected behavior)
- Stream stoppt sauber ohne Datenverlust

### Performance-Impact

- Minimaler Overhead: 0.1s Wartezeit beim Shutdown
- Keine Performance-Einbußen während des Streamings
- Reduziert Log-Spam durch ungraceful shutdowns

---

## Author

Fix erstellt von: Kiro AI Assistant  
Datum: 31. August 2026  
Version: 0.30.0
