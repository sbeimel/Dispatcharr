# 🚀 Quick Reference - v0.30.0 COMPLETE FIX

## TL;DR - Was macht der Patch?

1. ✅ **LAST RESORT** statt 60s warten → Löscht Cooldowns + sofortiger Retry
2. ✅ **Cooldown-Check bei Start** → Überspringt gecoolte Profiles SOFORT
3. ✅ **3x Reset** → Hourly (1h) + Success (5min) + Stop
4. ✅ **max_switches = 200** (statt 10)
5. ✅ **Load profile_id** aus Redis
6. ✅ **HTTP Race Fix** bei Shutdown

---

## 📝 Antworten auf deine Fragen

### 1. LAST RESORT vs 60s Wait - was ist das?

**v0.30.0 Original (SCHLECHT):**
```
Alle Streams probiert → Warte 60s → Retry (aber Cooldowns NOCH AKTIV!) → Warte 60s → ...
```
❌ Endlosschleife + schwarzer Bildschirm

**v0.30.0 mit Patch (GUT):**
```
Alle Streams probiert → Lösche ALLE Cooldowns → SOFORT Retry
```
✅ Keine Wartezeit, instabiler Stream besser als kein Stream

### 2. Woher kommt das Rotation System?

**War BEREITS in v0.30.0!** NICHT durch unseren Patch.

v0.27.0 hatte LAST RESORT, v0.30.0 hat es entfernt und durch 60s-Wait ersetzt.

**Unser Patch:** Bringt LAST RESORT zurück! 🎉

### 3. Health Monitoring - Booleans vs Events?

**War BEREITS in v0.30.0!** Vereinfachung gegenüber v0.27.0.

- v0.27.0: `gevent.event.Event()` objects
- v0.30.0: Simple `True/False` booleans

Funktioniert gleich gut, einfacher Code.

### 4. Cooldown-Check bei Start - fehlt das?

**JA! War in v0.30.0 entfernt!** 🔴 KRITISCH!

**Ohne Check:** Gecoolte Profiles werden sofort wieder probiert → Cooldown macht keinen Sinn!

**Unser Patch:** Fügt Check hinzu → Logs zeigen `[COOLDOWN] Skipping profile X - blocked for Ym Zs`

### 5. max_switches wieder auf 200?

**JA! Geändert von 10 → 200** ✅

**WICHTIG:** Über Frontend konfigurierbar! User kann in Settings ändern.

### 6. Cooldown-Check nur wenn aktiviert?

**JA! Korrekt!** ✅

```python
if ConfigHelper.stream_cooldown_enabled():  # ← Prüft Frontend-Setting
    # ... Cooldown scanning nur wenn aktiviert ...
```

Wenn Cooldown OFF → kein Redis-Scan → keine Performance-Impact.

---

## 🎯 Was ist jetzt besser?

| Was | Vorher | Nachher |
|-----|--------|---------|
| Alle Streams probiert | Warte 60s | LAST RESORT (sofort) |
| Cooldown bei Start | ❌ Fehlte | ✅ Funktioniert |
| tried_combinations | Nie Reset | 3x Reset (hourly/success/stop) |
| max_switches | 10 | 200 |
| profile_id laden | ❌ Fehlte | ✅ Aus Redis |
| HTTP race | ❌ Error-Logs | ✅ Sauber gehandlet |

---

## 📋 Installation

```bash
# 1. Backup
docker-compose down
cp -r . ../dispatcharr_backup

# 2. Apply
patch -p1 < dispatcharr_v0.30.0_COMPLETE_FIX.patch

# 3. Rebuild
docker-compose build --no-cache
docker-compose up -d

# 4. Logs prüfen
docker-compose logs -f --tail=100
```

---

## ✅ Erwartete Logs

### Cooldown-Check bei Start:
```
[COOLDOWN] Skipping profile 123 - blocked for 14m 32s more
[COOLDOWN] Selected non-cooled profile 789
```

### LAST RESORT:
```
[COOLDOWN] LAST RESORT: All 8 combinations tried - clearing cooldowns and retrying (pass 1/200)
[COOLDOWN] LAST RESORT: Cleared 8 cooldown keys
```

### Resets:
```
Hourly tried_combinations reset - clearing 5 entries
Stream stable for 300s - clearing 3 tried combinations
Clearing 2 tried combinations on channel stop
```

---

## 🔧 Was ist noch konfigurierbar?

Frontend Settings → Proxy:
- `max_stream_switches`: 200 (default, änderbar)
- `stream_cooldown_enabled`: ON/OFF
- `stream_cooldown_duration`: Z.B. 900s (15min)

---

## 🎉 Fazit

**v0.30.0 mit diesem Patch ist BESSER als v0.27.0!**

- ✅ Alle v0.27.0 Features portiert
- ✅ Channel-specific Cooldown Keys (bessere Isolation)
- ✅ Time-window Retry Logic (robuster)
- ✅ LAST RESORT statt nutzlosem 60s Wait
- ✅ Über Frontend konfigurierbar

**Bereit zum Testen!** 🚀
