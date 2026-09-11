# Dispatcharr v0.31.0 - Cooldown on Disconnect & Buffering

## 📋 Übersicht

**Version:** v0.31.0  
**Patch File:** `dispatcharr_v0.31.0_cooldown_on_disconnect.patch`  
**Base Version:** v0.30.0+  
**Type:** Feature Enhancement (Non-Breaking)

---

## 🎯 Was macht dieser Patch?

Erweitert das bestehende Cooldown-System um:

1. **Granulare Kontrolle** über Cooldown-Trigger
2. **Cooldown bei Buffering Timeout** (optional, default: AN)
3. **Cooldown bei Provider-Disconnect** (optional, default: AN)
4. **Konfigurierbarer Disconnect-Schwellwert** (0 = ANY disconnect, >0 = nur frühe disconnects)

---

## ✅ Neue Features

### 1. WebUI Settings (3 neue Felder)

| Setting | Type | Default | Range |
|---------|------|---------|-------|
| `stream_cooldown_on_buffering` | Checkbox | ✅ True | - |
| `stream_cooldown_on_disconnect` | Checkbox | ✅ True | - |
| `stream_disconnect_stability_threshold` | Number | 30 | 0-600 |

### 2. Backend Logik

**Buffering Timeout:**
- Stream verbindet, aber buffert > 60s ohne Daten
- Optional: Cooldown setzen (verhindert sofortigen Retry)

**Provider Disconnect:**
- Provider schließt Verbindung
- Optional: Cooldown setzen basierend auf Stream-Dauer
- Threshold = 0: **JEDER** Disconnect → Cooldown
- Threshold > 0: Nur Disconnects **vor** X Sekunden → Cooldown

### 3. Use Cases

**Standard (Default):**
```
✅ Cooldown on Buffering: True
✅ Cooldown on Disconnect: True
🔢 Threshold: 30 seconds
```
→ Nur instabile Streams bekommen Cooldown

**Aggressive (Jeder Disconnect = Problem):**
```
✅ Cooldown on Buffering: True
✅ Cooldown on Disconnect: True
🔢 Threshold: 0 seconds ← KEY!
```
→ **JEDER** Provider-Disconnect bekommt Cooldown

**Nur Connection Failures (Original):**
```
✅ Cooldown on Buffering: False
✅ Cooldown on Disconnect: False
```
→ Wie v0.30.0 (nur Connection Failures bekommen Cooldown)

---

## 📦 Geänderte Dateien

### Backend (3 Dateien)
1. **core/models.py** - 3 neue Settings
2. **apps/proxy/live_proxy/config_helper.py** - 3 neue Methoden
3. **apps/proxy/live_proxy/input/manager.py** - Conditional cooldown logic

### Frontend (3 Dateien)
1. **frontend/src/constants.js** - 3 neue UI-Labels
2. **frontend/src/utils/forms/settings/ProxySettingsFormUtils.js** - 3 neue Defaults
3. **frontend/src/components/forms/settings/ProxySettingsForm.jsx** - Form-Mappings

**Total: 6 Dateien, ~60 Zeilen Code**

---

## 🔧 Installation

### Option 1: Git Apply (empfohlen)

```bash
# Downloade den Patch
wget https://raw.githubusercontent.com/.../dispatcharr_v0.31.0_cooldown_on_disconnect.patch

# Wechsle ins Dispatcharr-Verzeichnis
cd /path/to/dispatcharr

# Backup erstellen (optional aber empfohlen)
git stash

# Patch anwenden
git apply dispatcharr_v0.31.0_cooldown_on_disconnect.patch

# Prüfe ob alles geklappt hat
git status
```

### Option 2: Patch Command

```bash
patch -p1 < dispatcharr_v0.31.0_cooldown_on_disconnect.patch
```

### Option 3: Manuelle Anwendung

Siehe Patch-Datei und übertrage die Änderungen manuell.

---

## 🧪 Nach der Installation

### 1. Backend Verifizieren

```bash
# Syntax-Check
python -m py_compile core/models.py
python -m py_compile apps/proxy/live_proxy/config_helper.py
python -m py_compile apps/proxy/live_proxy/input/manager.py

# Oder mit Django
python manage.py check
```

### 2. Frontend Bauen

```bash
cd frontend
npm install  # Falls neue Dependencies (sollte nicht nötig sein)
npm run build
cd ..
```

### 3. Migrationen (keine nötig!)

```bash
# Keine DB-Migrationen erforderlich
# Settings werden zur Laufzeit aus Config gelesen
```

### 4. Service Neustarten

```bash
# Docker
docker-compose restart

# Systemd
sudo systemctl restart dispatcharr

# Oder manuell
./stop.sh && ./start.sh
```

---

## 🎛️ Konfiguration nach Installation

### Standard-Setup (empfohlen)

```
Settings → Proxy Settings

✅ Stream Cooldown Enabled
🔢 Stream Cooldown Duration: 10 minutes

✅ Cooldown on Buffering Timeout
✅ Cooldown on Disconnect
🔢 Disconnect Stability Threshold: 30 seconds
```

**Verhalten:**
- Buffering > 60s → Cooldown 10min
- Disconnect < 30s → Cooldown 10min
- Disconnect >= 30s → Kein Cooldown
- Connection failure → Cooldown 10min

---

### Aggressive Setup (Jeder Disconnect = Problem)

```
✅ Stream Cooldown Enabled
🔢 Stream Cooldown Duration: 10 minutes

✅ Cooldown on Buffering Timeout
✅ Cooldown on Disconnect
🔢 Disconnect Stability Threshold: 0 ← WICHTIG!
```

**Verhalten:**
- Buffering > 60s → Cooldown 10min
- **JEDER Disconnect → Cooldown 10min** (egal wie lange Stream lief)
- Connection failure → Cooldown 10min

---

### Nur Buffering (Disconnects OK)

```
✅ Stream Cooldown Enabled
✅ Cooldown on Buffering Timeout
☐ Cooldown on Disconnect
```

**Verhalten:**
- Buffering > 60s → Cooldown 10min
- Disconnects → Kein Cooldown (Reconnect wird probiert)
- Connection failure → Cooldown 10min

---

## 📊 Vorher/Nachher Vergleich

### v0.30.0 (Vorher)

**Cooldown-Trigger:**
- ✅ Connection failure (nach max_retries)
- ❌ Buffering timeout → **KEIN** Cooldown
- ❌ Disconnect → **KEIN** Cooldown

**Problem:**
- Streams die verbinden aber buffern → Endlosschleife möglich
- Disconnects nach 10s → Sofort retry → Wieder disconnect
- Multi-User: Gleiche tote Streams immer wieder probiert

### v0.31.0 (Nachher)

**Cooldown-Trigger:**
- ✅ Connection failure (nach max_retries)
- ✅ Buffering timeout → **Optional Cooldown** (default: AN)
- ✅ Disconnect → **Optional Cooldown** mit Threshold (default: AN, 30s)

**Lösung:**
- Streams die buffern → Cooldown → Andere Streams probiert
- Disconnects konfigurierbar (0 = alle, >0 = nur frühe)
- Multi-User: Cooldown über Sessions hinweg (Redis-basiert)

---

## 🔍 Logs & Debugging

### Neue Log-Nachrichten

**Buffering Timeout (Cooldown disabled):**
```
[ERROR] Buffering timeout reached for channel ... after 60.0 seconds
[INFO] Switched to next stream for channel ... after buffering timeout
```

**Buffering Timeout (Cooldown enabled):**
```
[ERROR] Buffering timeout reached for channel ... after 60.0 seconds
[INFO] Set 600s cooldown for stream 123 with profile 456 on channel ...
[INFO] Switched to next stream for channel ... after buffering timeout
```

**Disconnect (Threshold = 30s, Early disconnect):**
```
[WARNING] Server closed connection for channel ...
[INFO] Stream disconnected after 15.2s (< 30s threshold) for channel ... - setting cooldown
[INFO] Set 600s cooldown for stream 123 with profile 456 on channel ...
```

**Disconnect (Threshold = 30s, Stable disconnect):**
```
[WARNING] Server closed connection for channel ...
# NO cooldown - stream ran 45s >= 30s threshold
```

**Disconnect (Threshold = 0, ANY disconnect):**
```
[WARNING] Server closed connection for channel ...
[INFO] Stream disconnected after 125.3s (any disconnect) for channel ... - setting cooldown
[INFO] Set 600s cooldown for stream 123 with profile 456 on channel ...
```

### Log-Grep Commands

```bash
# Buffering timeouts
grep "Buffering timeout reached" logs/dispatcharr.log

# Disconnects mit Cooldown
grep "Stream disconnected.*setting cooldown" logs/dispatcharr.log

# Alle Cooldowns
grep "Set.*cooldown for stream" logs/dispatcharr.log

# Cooldown checks (skipped streams)
grep "is on cooldown" logs/dispatcharr.log
```

---

## ⚠️ Wichtige Hinweise

### 1. Cooldown Master Switch

**Alle neuen Features erfordern:**
```
✅ Stream Cooldown Enabled
```

Wenn disabled: Keine Cooldowns (auch nicht buffering/disconnect)

### 2. Threshold = 0 Bedeutung

**Threshold = 0 ist NICHT "disabled"!**

- Threshold = 0 → **Jeder** Disconnect bekommt Cooldown
- Zum Deaktivieren: Checkbox "Cooldown on Disconnect" ausschalten

### 3. Backwards Compatibility

**Bestehende Installationen:**
- Defaults sind sinnvoll (buffering: true, disconnect: true, threshold: 30s)
- Verhalten ähnlich zu vorheriger Implementation
- Aber: Jetzt konfigurierbar im WebUI!

**Wenn du v0.30.0 Verhalten willst:**
```
✅ Stream Cooldown Enabled
☐ Cooldown on Buffering
☐ Cooldown on Disconnect
```

### 4. Redis erforderlich

Cooldown-System benötigt Redis:
- Speichert Cooldowns persistent
- Überlebt Channel-Neustarts
- TTL (Time To Live) automatisch

Ohne Redis: Cooldown funktioniert nicht!

---

## 🧪 Testing

### Test 1: Buffering Cooldown

```bash
1. Settings:
   ✅ Cooldown Enabled
   ✅ Cooldown on Buffering
   🔢 Duration: 5 minutes (zum Testen)

2. Wähle Stream der buffert (langsam/keine Daten)

3. Warte 60 Sekunden (buffering_timeout)

4. Check Logs:
   grep "Buffering timeout.*setting cooldown" logs/

5. Erwartung:
   - Stream switched
   - Cooldown gesetzt
   - Stream für 5min geblockt
```

### Test 2: Disconnect Cooldown (Threshold = 30s)

```bash
1. Settings:
   ✅ Cooldown on Disconnect
   🔢 Threshold: 30s

2. Wähle instabilen Stream (disconnected nach ~15s)

3. Check Logs:
   grep "Stream disconnected.*< 30s.*cooldown" logs/

4. Erwartung:
   - Disconnect erkannt
   - Cooldown gesetzt (< 30s)
```

### Test 3: Disconnect Cooldown (Threshold = 0)

```bash
1. Settings:
   ✅ Cooldown on Disconnect
   🔢 Threshold: 0

2. Wähle Stream der läuft und dann disconnected

3. Check Logs:
   grep "any disconnect.*cooldown" logs/

4. Erwartung:
   - JEDER Disconnect → Cooldown
   - Egal wie lange Stream lief
```

---

## 🐛 Troubleshooting

### Problem: Settings werden nicht gespeichert

```bash
# Check Django DB Zugriff
python manage.py shell
>>> from core.models import Config
>>> Config.get_proxy_settings()

# Check Frontend Build
cd frontend && npm run build
```

### Problem: Cooldown wird nicht gesetzt

```bash
# Check Master Switch
Settings → Stream Cooldown Enabled = True ?

# Check Sub-Toggle
Settings → Cooldown on Buffering/Disconnect = True ?

# Check Logs
grep "Set.*cooldown" logs/
```

### Problem: Threshold = 0 funktioniert nicht

```bash
# Check Logic in Logs
grep "any disconnect" logs/

# Should see:
# "Stream disconnected after Xs (any disconnect) - setting cooldown"

# If not: Check Settings wurden gespeichert
python manage.py shell
>>> Config.get_proxy_settings()['stream_disconnect_stability_threshold']
0  # Sollte 0 sein!
```

---

## 📈 Performance Impact

**Minimal bis Keiner:**
- Cooldown-Check: O(1) Redis EXISTS
- Nur bei Disconnect/Buffering (selten)
- Keine normale Streaming-Performance betroffen

**Memory:**
- Redis: ~100 bytes pro Cooldown-Entry
- Bei 100 Streams: ~10 KB
- TTL cleanup automatisch

---

## 🔄 Rollback

### Falls Probleme auftreten:

```bash
# Git Apply Rollback
git apply -R dispatcharr_v0.31.0_cooldown_on_disconnect.patch

# Oder: Git Stash Pop (wenn Backup erstellt)
git stash pop

# Service Restart
docker-compose restart
```

### Settings auf "Alt" zurücksetzen:

```
Settings → Proxy Settings

☐ Cooldown on Buffering
☐ Cooldown on Disconnect
```

→ Verhält sich wie v0.30.0

---

## 📚 Related Documentation

1. **COOLDOWN_ON_DISCONNECT_IMPLEMENTATION.md** - Vollständige technische Doku
2. **WEBUI_COOLDOWN_SETTINGS_IMPLEMENTATION.md** - WebUI Details
3. **WEBUI_COOLDOWN_QUICK_GUIDE.md** - Schnell-Anleitung
4. **COOLDOWN_SYSTEM_v0.26.0.md** - Original Cooldown-System Doku

---

## ✅ Checklist nach Installation

- [ ] Patch erfolgreich angewendet
- [ ] Backend Syntax-Check durchgeführt
- [ ] Frontend gebaut (`npm run build`)
- [ ] Service neugestartet
- [ ] WebUI erreichbar
- [ ] Settings → Proxy Settings öffnen
- [ ] Neue Cooldown-Felder sichtbar
- [ ] Settings speichern funktioniert
- [ ] Logs prüfen: `grep cooldown logs/`
- [ ] Test-Stream mit Buffering probiert
- [ ] Cooldown im Log gefunden

---

## 🎯 Empfohlene Konfiguration

**Für die meisten User:**
```
✅ Stream Cooldown Enabled
🔢 Duration: 10 minutes

✅ Cooldown on Buffering Timeout
✅ Cooldown on Disconnect
🔢 Disconnect Threshold: 30 seconds
```

**Für instabile IPTV-Provider:**
```
✅ Stream Cooldown Enabled
🔢 Duration: 5-10 minutes

✅ Cooldown on Buffering Timeout
✅ Cooldown on Disconnect
🔢 Disconnect Threshold: 0 seconds ← Aggressive!
```

**Für eigene stabile Server:**
```
✅ Stream Cooldown Enabled (für Connection Failures)
🔢 Duration: 10 minutes

☐ Cooldown on Buffering Timeout
☐ Cooldown on Disconnect
```

---

## 📞 Support

**Bei Fragen/Problemen:**
1. Check Logs: `grep cooldown logs/dispatcharr.log`
2. Check Settings gespeichert: `Config.get_proxy_settings()`
3. Check Redis läuft: `redis-cli ping`
4. Erstelle GitHub Issue mit:
   - Dispatcharr Version
   - Patch Version
   - Log-Auszug
   - Settings Screenshot

---

**Version:** v0.31.0  
**Datum:** 2026-09-02  
**Status:** ✅ Production Ready  
**Breaking Changes:** None  
**Migration Required:** No
