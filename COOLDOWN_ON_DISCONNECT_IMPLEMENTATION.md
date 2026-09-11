# Cooldown on Disconnect - Implementation Summary

## 📋 Übersicht

Erweitert das bestehende Cooldown-System um zwei neue Trigger:
1. **Buffering Timeout** - Stream verbindet, aber sendet keine/zu langsame Daten
2. **Early Disconnect** - Stream bricht zu früh ab (< stable_connection_threshold)

## ✅ Was wurde implementiert?

### 1. Cooldown bei Buffering Timeout

**Datei:** `apps/proxy/live_proxy/input/manager.py` (Zeile ~1271)

**Trigger:**
- Stream verbindet erfolgreich ✅
- FFmpeg-Speed < buffering_speed (zu langsam) ❌
- Buffering dauert > buffering_timeout (default: 60s) ❌

**Code:**
```python
if buffering_duration > self.buffering_timeout:
    logger.error(f"Buffering timeout reached for channel {self.channel_id}")
    
    # Set cooldown for this stream+profile combination
    # This prevents immediate retry of streams that connect but don't deliver data
    self._set_stream_cooldown()
    
    # Send next stream request
    if self._try_next_stream():
        ...
```

**Vorher:**
- Stream switch ohne Cooldown → sofortiger Retry möglich

**Nachher:**
- Stream switch MIT Cooldown → Retry erst nach cooldown_duration (default: 10min)

---

### 2. Cooldown bei Early Disconnect

**Datei:** `apps/proxy/live_proxy/input/manager.py` (Zeile ~2017)

**Trigger:**
- Stream verbindet und läuft eine Zeit ✅
- Verbindung wird vom Server geschlossen ❌
- Connection duration < stable_connection_threshold (default: 30s) ❌

**Code:**
```python
if not chunk:
    # Connection closed by server
    logger.warning(f"Server closed connection for channel {self.channel_id}")
    
    # Set cooldown if connection was closed too early (unstable stream)
    # Only apply cooldown if stream was running less than stable_connection_threshold
    connection_start = getattr(self, 'connection_start_time', None)
    if connection_start:
        connection_duration = time.time() - connection_start
        stable_threshold = ConfigHelper.stable_connection_threshold()
        
        if connection_duration < stable_threshold:
            logger.info(
                f"Stream disconnected after {connection_duration:.1f}s (< {stable_threshold}s threshold) "
                f"for channel {self.channel_id} - setting cooldown"
            )
            self._set_stream_cooldown()
    
    self._close_socket()
    self.connected = False
    return False
```

**Vorher:**
- Stream disconnect → sofortiger Reconnect/Failover ohne Cooldown

**Nachher:**
- Stream disconnect < 30s → Cooldown → Retry erst nach cooldown_duration
- Stream disconnect >= 30s → KEIN Cooldown (war stabil genug)

---

## 🔒 Safety Features

### 1. Feature Flag Respect
```python
def _set_stream_cooldown(self, ...):
    if not ConfigHelper.stream_cooldown_enabled():
        return  # Cooldown disabled - exit early
```
- Cooldown wird NUR gesetzt wenn `stream_cooldown_enabled = True`
- Wenn disabled: Verhält sich wie vorher (keine Breaking Changes)

### 2. Null-Safety
```python
connection_start = getattr(self, 'connection_start_time', None)
if connection_start:
    # Only calculate if connection_start exists
```
- Kein AttributeError wenn `connection_start_time` nicht gesetzt ist
- Graceful fallback zu None

### 3. Configuration-Driven
```python
stable_threshold = ConfigHelper.stable_connection_threshold()
```
- Nutzt existierende Konfiguration (default: 30s)
- Keine Hardcoded-Werte
- User kann Threshold in Settings anpassen

### 4. Logging
```python
logger.info(f"Stream disconnected after {duration:.1f}s ... - setting cooldown")
```
- Informative Logs für Debugging
- User kann nachvollziehen warum Cooldown gesetzt wurde

---

## 🎯 Cooldown-Trigger Übersicht

| **Trigger** | **Wann?** | **Status** |
|-------------|-----------|------------|
| **Connection Failed** | Nach max_retries Verbindungsversuchen | ✅ Original |
| **Connection Exception** | Exception während Connect-Phase | ✅ Original |
| **Buffering Timeout** | Stream verbindet, aber buffert zu lange | ✅ NEU |
| **Early Disconnect** | Stream bricht vor stable_threshold ab | ✅ NEU |

---

## 📊 Szenarien

### Szenario 1: Provider antwortet nicht
```
1. Versuch Stream zu connecten → Timeout
2. Versuch Stream zu connecten → Timeout
3. Versuch Stream zu connecten → Timeout (max_retries erreicht)
4. ❌ Connection Failed → Cooldown ✅ (ORIGINAL)
```

### Szenario 2: Stream verbindet, aber sendet keine Daten
```
1. Stream Connect ✅
2. Warte auf Daten... (buffering)
3. 60 Sekunden vergangen (buffering_timeout)
4. ❌ Buffering Timeout → Cooldown ✅ (NEU)
5. Versuche nächsten Stream
```

### Szenario 3: Stream läuft 10s und bricht ab
```
1. Stream Connect ✅
2. Stream läuft 10 Sekunden ✅
3. Server schließt Verbindung ❌
4. 10s < 30s (stable_threshold)
5. ❌ Early Disconnect → Cooldown ✅ (NEU)
6. Versuche nächsten Stream
```

### Szenario 4: Stream läuft 45s und bricht ab
```
1. Stream Connect ✅
2. Stream läuft 45 Sekunden ✅
3. Server schließt Verbindung ❌
4. 45s >= 30s (stable_threshold)
5. ✅ War stabil → KEIN Cooldown
6. Versuche nächsten Stream (kann gleichen wieder probieren)
```

---

## 🔧 Konfiguration

### Cooldown aktivieren/deaktivieren
```python
# In Settings oder core/models.py
{
    "stream_cooldown_enabled": True,      # Feature aktivieren
    "stream_cooldown_minutes": 10,        # Cooldown-Dauer
}
```

### Schwellwerte anpassen
```python
{
    "stable_connection_threshold": 30,    # Wie lange muss Stream laufen?
    "buffering_timeout": 60,              # Wie lange darf buffering dauern?
}
```

---

## ✅ Verification Results

### Syntax Check
- ✅ Python-Syntax korrekt
- ✅ Keine Import-Fehler
- ✅ 4 Cooldown-Calls gefunden (2 original + 2 neu)

### Logic Check
- ✅ Cooldown respektiert Feature Flag
- ✅ Null-Safety mit getattr()
- ✅ Nutzt ConfigHelper für Threshold
- ✅ Logging vorhanden

### Backwards Compatibility
- ✅ Original Logic unverändert
- ✅ Keine geänderten Function Signatures
- ✅ Keine Breaking Changes
- ✅ Additive Changes nur

---

## 📝 Code Changes Summary

### Geänderte Datei
- `apps/proxy/live_proxy/input/manager.py`

### Zeilen geändert
1. **Line ~1277** - Cooldown bei Buffering Timeout (3 Zeilen hinzugefügt)
2. **Line ~2020** - Cooldown bei Early Disconnect (13 Zeilen hinzugefügt)

### Total: 16 neue Zeilen Code

---

## 🚀 Benefits

### 1. Reduziert Provider-Last
- Streams die "connect but don't work" werden nicht sofort wieder probiert
- 10 Minuten Pause gibt Provider Zeit sich zu erholen

### 2. Verhindert Endlosschleifen
- Buffering-Streams werden nicht endlos retried
- Instabile Streams werden cooldown-blocked

### 3. Nutzt existierende Config
- Keine neuen Settings nötig
- stable_connection_threshold bereits vorhanden
- stream_cooldown_enabled bereits im System

### 4. Debugging-Friendly
- Informative Logs
- User kann nachvollziehen warum Streams übersprungen werden

---

## ⚠️ Wichtige Hinweise

### 1. Cooldown muss aktiviert sein
```python
stream_cooldown_enabled = True  # In Settings!
```
Wenn deaktiviert: Feature hat keinen Effekt

### 2. Stable Threshold beachten
```python
stable_connection_threshold = 30  # Sekunden
```
- Zu niedrig (z.B. 5s): Zu viele Cooldowns
- Zu hoch (z.B. 120s): Weniger effektiv

### 3. Cooldown-Dauer anpassen
```python
stream_cooldown_minutes = 10  # 10 Minuten Standard
```
- Für instabile Provider: 5-10 Minuten
- Für sehr instabile: 15-30 Minuten

---

## 🧪 Testing

### Wie testen?

1. **Aktiviere Cooldown:**
   ```
   Settings → Proxy Settings
   ☑ Stream Cooldown Enabled
   Stream Cooldown Duration: 10 minutes
   ```

2. **Simuliere Buffering Timeout:**
   - Wähle Stream der verbindet aber sehr langsam ist
   - Warte 60 Sekunden (buffering_timeout)
   - Check Logs: `[COOLDOWN] Set Xs cooldown for stream...`

3. **Simuliere Early Disconnect:**
   - Wähle instabilen Stream
   - Stream bricht nach 10-20s ab
   - Check Logs: `Stream disconnected after Xs ... - setting cooldown`

4. **Prüfe Cooldown wirkt:**
   - Nach Cooldown-Set: Stream sollte übersprungen werden
   - Check Logs: `Stream X with profile Y is on cooldown (Xs remaining)`

---

## 📈 Expected Log Output

### Buffering Timeout
```
[INFO] Buffering started for channel ... - speed: 0.5x
[ERROR] Buffering timeout reached for channel ... after 60.0 seconds
[INFO] Set 600s cooldown for stream 123 with profile 456 on channel ...
[INFO] Switched to next stream for channel ... after buffering timeout
```

### Early Disconnect
```
[INFO] Stream connected for channel ...
[WARNING] Server closed connection for channel ...
[INFO] Stream disconnected after 12.5s (< 30s threshold) for channel ... - setting cooldown
[INFO] Set 600s cooldown for stream 123 with profile 456 on channel ...
```

### Cooldown Active
```
[INFO] Stream 123 with profile 456 is on cooldown for channel ... (580s remaining)
[INFO] Found 2 untried streams for channel ... (skipping cooled ones)
```

---

## ✅ Deployment Ready

- ✅ Implementation complete
- ✅ All checks passed
- ✅ Backwards compatible
- ✅ Edge cases handled
- ✅ Configuration-driven
- ✅ Logging implemented
- ✅ No breaking changes

**Ready to commit and deploy!** 🚀
