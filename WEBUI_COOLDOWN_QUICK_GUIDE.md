# 🎛️ WebUI Cooldown Settings - Quick Guide

## Neue Einstellungen (Settings → Proxy Settings)

### 1. ☑️ Cooldown on Buffering Timeout
**Was macht das?**  
Setzt Cooldown wenn Stream verbindet aber keine Daten sendet (buffering timeout).

**Wann deaktivieren?**  
Wenn Buffering normal ist und sich meist selbst löst.

---

### 2. ☑️ Cooldown on Disconnect
**Was macht das?**  
Setzt Cooldown wenn Provider die Verbindung schließt.

**Wann deaktivieren?**  
Wenn Disconnects normal sind und Reconnect funktioniert.

---

### 3. 🔢 Disconnect Stability Threshold
**Was ist das?**  
Wie lange muss Stream laufen um als "stabil" zu gelten.

**Wichtige Werte:**

| Wert | Bedeutung |
|------|-----------|
| **0** | **Jeder Disconnect → Cooldown** |
| 30 | Disconnect < 30s → Cooldown |
| 60 | Disconnect < 60s → Cooldown |
| 120 | Disconnect < 120s → Cooldown |

---

## 🎯 Dein Use-Case: "Jeder Disconnect ist Problem"

**Lösung:**
```
Settings → Proxy Settings

✅ Stream Cooldown Enabled
✅ Cooldown on Disconnect
🔢 Disconnect Stability Threshold: 0  ← WICHTIG!
🔢 Stream Cooldown Duration: 10 minutes
```

**Ergebnis:**
- Provider schließt Verbindung nach 10s → Cooldown ✅
- Provider schließt Verbindung nach 5 Min → Cooldown ✅
- **JEDER** Provider-Disconnect → Cooldown ✅

---

## 🔧 Empfohlene Setups

### Setup 1: Aggressive (Dein Use-Case)
```
✅ Cooldown Enabled
✅ On Buffering
✅ On Disconnect
🔢 Threshold: 0 seconds ← Key!
🔢 Duration: 10 minutes
```
→ Maximale Cooldown-Abdeckung

---

### Setup 2: Standard (Default)
```
✅ Cooldown Enabled
✅ On Buffering
✅ On Disconnect
🔢 Threshold: 30 seconds
🔢 Duration: 10 minutes
```
→ Nur frühe Disconnects

---

### Setup 3: Nur Connection Failures
```
✅ Cooldown Enabled
☐ On Buffering
☐ On Disconnect
🔢 Duration: 10 minutes
```
→ Nur wenn Connect fehlschlägt (original)

---

## 📝 Was bedeutet Threshold = 0?

**Normal (Threshold = 30s):**
```
Stream läuft 10s  → Disconnect → Cooldown ✅
Stream läuft 45s  → Disconnect → Kein Cooldown ❌
Stream läuft 2min → Disconnect → Kein Cooldown ❌
```

**Aggressive (Threshold = 0s):**
```
Stream läuft 10s  → Disconnect → Cooldown ✅
Stream läuft 45s  → Disconnect → Cooldown ✅
Stream läuft 2min → Disconnect → Cooldown ✅
```

---

## ⚡ Quick Actions

### Ich will maximale Cooldowns:
```
Threshold: 0
On Buffering: ✅
On Disconnect: ✅
```

### Ich will nur Connection Failures cooldown:
```
On Buffering: ☐
On Disconnect: ☐
```

### Ich will nur instabile Streams cooldown:
```
Threshold: 60 (oder höher)
On Buffering: ✅
On Disconnect: ✅
```

---

## 🔍 Wie teste ich?

1. **Aktiviere Settings:**
   ```
   ✅ Stream Cooldown Enabled
   ✅ On Disconnect
   🔢 Threshold: 0
   ```

2. **Starte instabilen Stream**

3. **Check Logs:**
   ```
   grep "setting cooldown" logs/
   ```

4. **Erwartetes Log:**
   ```
   Stream disconnected after 15.3s (any disconnect) - setting cooldown
   Set 600s cooldown for stream 123 with profile 456
   ```

---

## ❓ FAQs

**Q: Threshold auf 0 setzen = Problem?**  
A: Nein! Das ist genau für deinen Use-Case gedacht.

**Q: Kann ich Buffering und Disconnect getrennt steuern?**  
A: Ja! Beide haben separate Checkboxes.

**Q: Was wenn ich Cooldown komplett deaktiviere?**  
A: Verhält sich wie vor dem Update (keine Cooldowns).

**Q: Threshold = 0 vs. Threshold = 1?**  
A: 
- 0 = Jeder Disconnect
- 1 = Nur Disconnects < 1s

**Q: Empfohlener Threshold-Wert?**  
A:
- Instabile Provider: 0
- Normale Provider: 30-60
- Stabile Provider: 60-120 oder disabled

---

## 🚀 Sofort-Lösung für dich

```
1. Öffne Settings → Proxy Settings
2. Finde "Stream Cooldown" Sektion
3. Setze:
   ✅ Stream Cooldown Enabled
   ✅ Cooldown on Disconnect
   🔢 Disconnect Stability Threshold: 0
4. Save Settings
5. Fertig!
```

**Ab jetzt:** Jeder Provider-Disconnect → 10min Cooldown → Probiert andere Streams zuerst

---

**Status:** ✅ Implementiert und einsatzbereit!
