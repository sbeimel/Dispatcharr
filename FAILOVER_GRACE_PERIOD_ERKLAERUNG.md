# ⚠️ WICHTIG: failover_grace_period vs url_switch_timeout

## UNTERSCHIED DER BEIDEN SETTINGS

### 1. `url_switch_timeout` (20s)
**Zweck:** Maximale Zeit für den Stream-Wechsel-PROZESS selbst

**Verwendung:**
```python
# stream_manager.py
if self.url_switching and time.time() - self.url_switch_start_time > self.url_switch_timeout:
    logger.warning(f"URL switching state appears stuck for channel {self.channel_id}")
    self._reset_url_switching_state()
```

**Was es macht:**
- Überwacht wie lange der Stream-Manager im "switching" Zustand ist
- Verhindert dass der Manager in einem "stuck" Zustand bleibt
- Ist ein **TIMEOUT für den Wechsel-Prozess**

---

### 2. `failover_grace_period` (20s)
**Zweck:** Zusätzliche Wartezeit für CLIENTS während Stream-Wechsel

**Verwendung:**
```python
# stream_generator.py
stream_timeout = ConfigHelper.stream_timeout()  # z.B. 20s
failover_grace_period = ConfigHelper.failover_grace_period()  # z.B. 20s
total_timeout = stream_timeout + failover_grace_period  # = 40s

# Disconnect after long inactivity
if time.time() - self.last_yield_time > total_timeout:
    if self.stream_manager and not self.stream_manager.healthy:
        if self.stream_manager.url_switching:
            logger.info(f"Stream switching in progress, giving more time")
            return False  # NICHT disconnecten!
```

**Was es macht:**
- Gibt Clients EXTRA Zeit während Stream-Wechsel
- Verhindert dass Clients disconnecten während der Manager noch am Wechseln ist
- Ist eine **GRACE PERIOD für Clients**

---

## BEISPIEL-SZENARIO

### Ohne failover_grace_period:
```
00:00 - Stream A läuft
00:20 - Stream A failed, keine Daten mehr
00:20 - stream_timeout (20s) erreicht
00:20 - Client disconnected ❌ (zu früh!)
00:25 - Stream Manager wechselt zu Stream B
00:30 - Stream B läuft, aber Client ist weg
```

### Mit failover_grace_period:
```
00:00 - Stream A läuft
00:20 - Stream A failed, keine Daten mehr
00:20 - stream_timeout (20s) erreicht
00:20 - ABER: failover_grace_period gibt 20s extra
00:25 - Stream Manager wechselt zu Stream B
00:30 - Stream B sendet Daten
00:35 - Client empfängt Daten ✓ (noch connected!)
00:40 - total_timeout (40s) wäre erreicht gewesen
```

---

## SIND SIE GLEICH?

**NEIN!** Sie haben unterschiedliche Zwecke:

| Setting | Zweck | Wer nutzt es | Wann |
|---------|-------|--------------|------|
| `url_switch_timeout` | Timeout für Wechsel-Prozess | Stream Manager | Während Switching |
| `failover_grace_period` | Extra Zeit für Clients | Stream Generator | Während Inaktivität |

---

## PROBLEM IN v0.19.0

In v0.19.0 fehlt `failover_grace_period`! Das bedeutet:

**Aktuell:**
```python
# stream_generator.py (v0.19.0)
stream_timeout = ConfigHelper.stream_timeout()  # 20s
# failover_grace_period fehlt!
total_timeout = stream_timeout  # Nur 20s!

if time.time() - self.last_yield_time > total_timeout:
    # Client disconnected nach 20s ohne Daten
```

**Problem:**
- Clients disconnecten zu früh während Stream-Wechsel
- Stream Manager braucht Zeit zum Wechseln (bis zu 20s)
- Clients haben keine Grace Period mehr

---

## LÖSUNG: failover_grace_period MUSS PORTIERT WERDEN!

### Was fehlt in v0.19.0:

1. **config.py:**
   ```python
   @classmethod
   def get_failover_grace_period(cls):
       settings = cls.get_proxy_settings()
       return settings.get("failover_grace_period", 20)
   ```

2. **config_helper.py:**
   ```python
   @staticmethod
   def failover_grace_period():
       from apps.proxy.config import BaseConfig
       return BaseConfig.get_failover_grace_period()
   ```

3. **Frontend (constants.js):**
   ```javascript
   failover_grace_period: {
     label: 'Failover Grace Period (seconds)',
     description: 'Extra time for clients during stream switching',
   }
   ```

4. **Frontend (ProxySettingsFormUtils.js):**
   ```javascript
   failover_grace_period: 20,
   ```

---

## EMPFEHLUNG

**KRITISCH:** `failover_grace_period` MUSS in v0.19.0 implementiert werden!

**Ohne dieses Setting:**
- ❌ Clients disconnecten zu früh
- ❌ Stream-Wechsel funktioniert nicht zuverlässig
- ❌ Profile Failover wird unterbrochen

**Mit diesem Setting:**
- ✅ Clients warten während Stream-Wechsel
- ✅ Stream-Wechsel hat Zeit zum Abschluss
- ✅ Profile Failover funktioniert zuverlässig

---

## FAZIT

**NEIN, sie sind NICHT gleich!**

- `url_switch_timeout` = Timeout für Manager-Prozess
- `failover_grace_period` = Extra Zeit für Clients

**Beide werden benötigt für zuverlässiges Profile Failover!**

---

**Status:** ⚠️ MUSS IMPLEMENTIERT WERDEN
**Priorität:** HOCH
**Auswirkung:** Ohne dieses Setting funktioniert Profile Failover nicht zuverlässig
