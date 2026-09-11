# ✅ Dispatcharr v0.31.0 - Cooldown on Disconnect Summary

## 📦 Patch Paket Komplett

### Enthaltene Dateien:

1. **dispatcharr_v0.31.0_cooldown_on_disconnect.patch** 
   - Git-kompatibles Patch-File
   - 6 Dateien geändert
   - ~60 Zeilen hinzugefügt

2. **PATCH_v0.31.0_COOLDOWN_ON_DISCONNECT_GUIDE.md**
   - Vollständiges Installations-Guide
   - Konfigurations-Beispiele
   - Troubleshooting

3. **verify_v0.31.0_patch.py**
   - Automatisches Verifikations-Script
   - Prüft alle Änderungen

4. **COOLDOWN_v0.31.0_SUMMARY.md** (dieses Dokument)
   - Schnell-Übersicht

---

## 🎯 Was macht der Patch?

### Neue WebUI-Einstellungen (Settings → Proxy Settings)

```
Stream Cooldown (erweitert)
├─ ☑ Stream Cooldown Enabled (wie vorher)
├─ 🔢 Stream Cooldown Duration: 10 min (wie vorher)
│
├─ ☑ Cooldown on Buffering Timeout (NEU)
├─ ☑ Cooldown on Disconnect (NEU)
└─ 🔢 Disconnect Stability Threshold: 30s (NEU, Range: 0-600)
```

### Was bedeuten die neuen Settings?

| Setting | Funktion |
|---------|----------|
| **Cooldown on Buffering** | Stream verbindet aber buffert → Cooldown |
| **Cooldown on Disconnect** | Provider schließt Verbindung → Cooldown |
| **Threshold = 0** | **JEDER** Disconnect → Cooldown |
| **Threshold = 30** | Nur Disconnects < 30s → Cooldown |
| **Threshold = 60** | Nur Disconnects < 60s → Cooldown |

---

## 🚀 Quick Start

### 1. Patch anwenden

```bash
cd /path/to/dispatcharr
git apply dispatcharr_v0.31.0_cooldown_on_disconnect.patch
```

### 2. Verifizieren

```bash
python verify_v0.31.0_patch.py
```

### 3. Frontend bauen

```bash
cd frontend && npm run build && cd ..
```

### 4. Service neustarten

```bash
docker-compose restart
```

### 5. WebUI konfigurieren

```
Settings → Proxy Settings

Für "Jeder Disconnect = Problem":
✅ Stream Cooldown Enabled
✅ Cooldown on Disconnect
🔢 Disconnect Threshold: 0 ← KEY!
```

---

## 📊 Vorher/Nachher

### v0.30.0 (Vorher)

```
Cooldown nur bei:
✅ Connection failure (max_retries)
❌ Buffering timeout (KEIN Cooldown)
❌ Disconnect (KEIN Cooldown)
```

**Problem:**
- Buffering-Streams → Endlosschleife
- Disconnects → Sofort retry
- Multi-User → Gleiche tote Streams

### v0.31.0 (Nachher)

```
Cooldown bei:
✅ Connection failure (wie vorher)
✅ Buffering timeout (optional, AN)
✅ Disconnect (optional, AN, konfigurierbar)
```

**Lösung:**
- Buffering-Streams → Cooldown → Skip
- Disconnects → Cooldown (wenn enabled)
- Multi-User → Cooldown persistent (Redis)

---

## 🎛️ Konfigurations-Beispiele

### Standard (Empfohlen)

```
✅ Cooldown Enabled
✅ On Buffering: True
✅ On Disconnect: True
🔢 Threshold: 30 seconds
🔢 Duration: 10 minutes
```

**Verhalten:**
- Connection failure → Cooldown ✅
- Buffering > 60s → Cooldown ✅
- Disconnect < 30s → Cooldown ✅
- Disconnect >= 30s → Kein Cooldown

---

### Aggressive (Jeder Disconnect)

```
✅ Cooldown Enabled
✅ On Buffering: True
✅ On Disconnect: True
🔢 Threshold: 0 ← WICHTIG!
🔢 Duration: 10 minutes
```

**Verhalten:**
- Connection failure → Cooldown ✅
- Buffering > 60s → Cooldown ✅
- **JEDER Disconnect → Cooldown** ✅

---

### Konservativ (Nur Connection Failures)

```
✅ Cooldown Enabled
☐ On Buffering: False
☐ On Disconnect: False
🔢 Duration: 10 minutes
```

**Verhalten:**
- Connection failure → Cooldown ✅
- Buffering → Kein Cooldown
- Disconnect → Kein Cooldown
- (Wie v0.30.0)

---

## 🔍 Logs prüfen

### Nach Patch-Anwendung

```bash
# Buffering mit Cooldown
grep "Buffering timeout.*cooldown" logs/dispatcharr.log

# Disconnect mit Cooldown
grep "Stream disconnected.*setting cooldown" logs/dispatcharr.log

# Threshold = 0 (Any disconnect)
grep "any disconnect.*cooldown" logs/dispatcharr.log

# Alle Cooldowns
grep "Set.*cooldown for stream" logs/dispatcharr.log
```

### Erwartete Log-Ausgaben

**Buffering Timeout:**
```
[ERROR] Buffering timeout reached for channel ... after 60.0 seconds
[INFO] Set 600s cooldown for stream 123 with profile 456 on channel ...
```

**Disconnect (Threshold = 30s, Early):**
```
[WARNING] Server closed connection for channel ...
[INFO] Stream disconnected after 12.5s (< 30s threshold) - setting cooldown
[INFO] Set 600s cooldown for stream 123 with profile 456
```

**Disconnect (Threshold = 0, Any):**
```
[WARNING] Server closed connection for channel ...
[INFO] Stream disconnected after 125.3s (any disconnect) - setting cooldown
[INFO] Set 600s cooldown for stream 123 with profile 456
```

---

## ✅ Checklist

- [ ] Patch-Datei heruntergeladen
- [ ] Git apply erfolgreich
- [ ] Verifikations-Script ausgeführt
- [ ] Alle Checks ✅ passed
- [ ] Frontend gebaut
- [ ] Service neugestartet
- [ ] WebUI erreichbar
- [ ] Neue Settings sichtbar
- [ ] Konfiguration gespeichert
- [ ] Logs geprüft

---

## 📚 Dokumentation

| Datei | Zweck |
|-------|-------|
| `dispatcharr_v0.31.0_cooldown_on_disconnect.patch` | Patch-File zum Anwenden |
| `PATCH_v0.31.0_COOLDOWN_ON_DISCONNECT_GUIDE.md` | Installation & Konfiguration |
| `verify_v0.31.0_patch.py` | Automatische Verifikation |
| `COOLDOWN_ON_DISCONNECT_IMPLEMENTATION.md` | Technische Details |
| `WEBUI_COOLDOWN_QUICK_GUIDE.md` | Schnell-Anleitung |

---

## 🎯 Deine Anforderung

> "Jeder disconnect der nicht durch uns ausgelöst ist ist ein problem eigentlich"

**✅ GELÖST mit:**

```
Settings → Proxy Settings

✅ Stream Cooldown Enabled
✅ Cooldown on Disconnect
🔢 Disconnect Stability Threshold: 0

→ JEDER Provider-Disconnect bekommt Cooldown
→ Egal ob nach 5s oder 5 Minuten
→ Stream wird für 10min geblockt
```

---

## 📈 Benefits

### 1. Verhindert Endlosschleifen
- Buffering-Streams bekommen Cooldown
- Keine sofortigen Retries mehr

### 2. Multi-User Safe
- Cooldown persistent in Redis
- User B öffnet Channel → Sieht Cooldown von User A

### 3. Provider-Schonung
- Reduziert unnötige Requests
- Gibt Providern Zeit zur Erholung

### 4. Flexibel Konfigurierbar
- Threshold = 0: Aggressive (jeder Disconnect)
- Threshold > 0: Nur instabile Streams
- Komplett deaktivierbar: Checkboxes

### 5. Backwards Compatible
- Defaults sind sinnvoll
- Keine Breaking Changes
- Optional aktivierbar

---

## ⚠️ Wichtig

### Cooldown Master Switch

**Alle Features benötigen:**
```
✅ Stream Cooldown Enabled = True
```

Wenn disabled: Keine Cooldowns (auch nicht neu)

### Threshold = 0 vs. Disabled

**Threshold = 0:**
- Cooldown bei **JEDEM** Disconnect
- Feature ist AN

**Checkbox disabled:**
- Cooldown **NIE** bei Disconnect
- Feature ist AUS

### Redis erforderlich

Cooldown-System benötigt Redis:
- Persistent über Sessions
- TTL (automatisches Löschen)
- Ohne Redis: Feature funktioniert nicht

---

## 🔄 Rollback

Falls Probleme:

```bash
# Patch rückgängig
git apply -R dispatcharr_v0.31.0_cooldown_on_disconnect.patch

# Oder: Settings anpassen
☐ Cooldown on Buffering
☐ Cooldown on Disconnect

# Service restart
docker-compose restart
```

---

## 📞 Support

**Probleme?**

1. Check Logs: `grep cooldown logs/`
2. Run Verification: `python verify_v0.31.0_patch.py`
3. Check Settings gespeichert
4. Check Redis läuft: `redis-cli ping`

**GitHub Issue erstellen mit:**
- Dispatcharr Version
- Patch Version
- verify_v0.31.0_patch.py Output
- Log-Auszug
- Settings Screenshot

---

## 🎉 Status

**Patch:** ✅ Complete  
**Testing:** ✅ Verified  
**Documentation:** ✅ Complete  
**Ready:** ✅ Production  

**Installation Time:** ~5 Minuten  
**Breaking Changes:** None  
**Migration:** Not required  

---

**Version:** v0.31.0  
**Datum:** 2026-09-02  
**Type:** Feature Enhancement  
**Complexity:** Low  
**Risk:** Low (Additive, Optional)
