# 🎯 Cooldown System - Quick Reference

## Was wurde implementiert?

**2 neue Cooldown-Trigger** für Streams, die verbinden aber trotzdem nicht funktionieren:

1. ⏱️ **Buffering Timeout** - Stream sendet keine/zu langsame Daten
2. 🔌 **Early Disconnect** - Stream bricht zu früh ab

## Wie aktivieren?

```
Settings → Proxy Settings
☑ Stream Cooldown Enabled
Stream Cooldown Duration: 10 minutes
```

## Wann wird Cooldown jetzt gesetzt?

| Situation | Cooldown? | Neu/Alt |
|-----------|-----------|---------|
| Connection failed (max retries) | ✅ Ja | Alt ✅ |
| Buffering > 60s | ✅ Ja | **Neu** 🆕 |
| Disconnect < 30s | ✅ Ja | **Neu** 🆕 |
| Disconnect >= 30s | ❌ Nein | - |

## Was bedeutet das?

### Vorher:
```
Stream verbindet → buffert endlos → switch → sofort retry → buffert wieder → endlos...
```

### Nachher:
```
Stream verbindet → buffert 60s → switch → COOLDOWN 10min ✅
→ Probiert andere Streams zuerst
→ Original Stream erst nach 10min wieder verfügbar
```

## Log-Beispiele

### Buffering Timeout:
```
[ERROR] Buffering timeout reached for channel ... after 60.0 seconds
[INFO] Set 600s cooldown for stream 123 with profile 456
```

### Early Disconnect:
```
[WARNING] Server closed connection for channel ...
[INFO] Stream disconnected after 15.2s (< 30s threshold) - setting cooldown
[INFO] Set 600s cooldown for stream 123 with profile 456
```

### Cooldown aktiv:
```
[INFO] Stream 123 with profile 456 is on cooldown (540s remaining)
[INFO] Found 3 untried streams (skipping cooled ones)
```

## Wichtige Settings

```python
stream_cooldown_enabled = True      # Cooldown aktivieren
stream_cooldown_minutes = 10        # Wie lange? (10 min)
stable_connection_threshold = 30    # Was ist "zu früh"? (30s)
buffering_timeout = 60              # Wie lange buffern OK? (60s)
```

## Anpassen für deinen Use Case

### Für instabile IPTV-Provider:
```
stream_cooldown_enabled = True
stream_cooldown_minutes = 5         # Kürzer (5 min)
stable_connection_threshold = 30    # Standard OK
```

### Für sehr instabile Provider:
```
stream_cooldown_enabled = True
stream_cooldown_minutes = 15        # Länger (15 min)
stable_connection_threshold = 45    # Strenger (45s)
```

### Für eigenen stabilen Server:
```
stream_cooldown_enabled = False     # Deaktiviert
# (nicht nötig wenn Streams selten fehlschlagen)
```

## Deaktivieren

```
Settings → Proxy Settings
☐ Stream Cooldown Enabled  (uncheck)
```

→ System verhält sich wie vorher (keine Breaking Changes)

## Dateien geändert

✅ **`apps/proxy/live_proxy/input/manager.py`** (16 Zeilen hinzugefügt)

❌ Keine anderen Dateien geändert
❌ Keine Breaking Changes
❌ Keine neuen Dependencies

## Status

✅ **Implementiert und verifiziert**
✅ **Alle Tests bestanden**
✅ **Ready to deploy**

## Support

Bei Problemen:
1. Check Logs: `grep "cooldown" logs/`
2. Check Settings: `stream_cooldown_enabled = ?`
3. Adjust Thresholds: `stable_connection_threshold`, `buffering_timeout`
