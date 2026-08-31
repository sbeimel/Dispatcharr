# Buffer Timeout Problem - Analyse & Lösungsansätze

## Datum: 2026-06-18

---

## Problem-Zusammenfassung

User berichtet von endlosem Failover durch alle 94 Stream-Kombinationen, obwohl:
- Buffer erfolgreich gefüllt wird (18/4 chunks)
- Channel Status korrekt zu "waiting_for_clients" wechselt
- Clients sofort mit "Broken pipe" disconnecten (0.12-0.18s)

**Hauptursache:** Buffer Timeout von nur **5 Sekunden** ist zu aggressiv für langsame Verbindungen/Initialisierung.

---

## Aktuelle Architektur

### v0.26.0 Buffer Timeout Konfiguration

**File: `apps/proxy/config.py`**

```python
class TSConfig(BaseConfig):
    # Default values
    CHUNK_TIMEOUT = 5  # Seconds to wait for each chunk read
    BUFFERING_TIMEOUT = 15  # Seconds to wait for buffering before switching streams
    
    # Database-dependent settings (WebUI konfigurierbar)
    @classmethod
    def get_buffering_timeout(cls):
        settings = cls.get_proxy_settings()
        return settings.get("buffering_timeout", 15)
    
    @classmethod
    def get_channel_init_grace_period(cls):
        settings = cls.get_proxy_settings()
        return settings.get("channel_init_grace_period", 5)  # ⚠️ NUR 5 SEKUNDEN!
```

**Problem:** `channel_init_grace_period` ist der kritische Wert - **nur 5 Sekunden** für gesamte Initialisierung!

---

## Vergleich: v0.26.0 vs Aktuelle Version

### v0.26.0 (Dispatcharr - 26.0)

**Buffer Management:**
- ✅ `StreamBuffer` mit Redis-basierten Timeouts
- ✅ Chunk-basiertes TTL System (60 Sekunden default)
- ✅ Lua-Scripte für atomare Buffer-Operationen
- ✅ Zeit-basierte Chunk-Positionierung (`find_chunk_index_by_time`)

**Timeout-Mechanismen:**
```python
CHUNK_TIMEOUT = 5                    # ❌ Zu kurz für langsame Streams
BUFFERING_TIMEOUT = 15               # ✅ OK für Buffer-Fill
CHANNEL_INIT_GRACE_PERIOD = 5        # ❌ KRITISCH: Zu kurz!
CLIENT_WAIT_TIMEOUT = 60             # ✅ OK
FAILOVER_GRACE_PERIOD = 20           # ✅ OK
```

### Aktuelle Version (Dispatcharr)

**Ähnliche Struktur, aber:**
- Gleiche Buffer-Architektur
- Gleiche Timeout-Probleme
- Zusätzliche Features (FMP4, Output Profiles)

---

## Identifizierte Timeout-Probleme

### 1. **Channel Init Grace Period - HAUPTPROBLEM**

**Location:** WebUI → Settings → Proxy Settings → "Channel Initialization Grace Period"

**Aktueller Wert:** 5 Sekunden

**Was passiert in 5 Sekunden:**
```
T+0.0s: Client connected
T+0.5s: Channel initialization started
T+1.0s: Stream URL validation (kann bei 302 redirect 2-3s dauern!)
T+3.0s: FFmpeg process spawned
T+4.0s: Buffer filling started
T+5.0s: ⚠️ TIMEOUT! Failover triggered!
       ❌ Client noch nicht verbunden
       ❌ Buffer noch nicht voll
```

**Empfohlener Wert:** **25-30 Sekunden**

---

### 2. **Chunk Timeout**

**Problem:** `CHUNK_TIMEOUT = 5` Sekunden ist zu aggressiv

**Szenario bei langsamen Streams:**
```
T+0s: Warte auf ersten Chunk
T+1s: Network latency (IPTV provider weit entfernt)
T+2s: HTTP 302 redirect processing
T+3s: Neue Connection aufbauen
T+4s: Daten kommen langsam (niedrige Bitrate)
T+5s: ⚠️ TIMEOUT! Failover!
```

**Empfohlen:** 10-15 Sekunden für ersten Chunk

---

### 3. **Buffering Timeout**

**Aktuell:** 15 Sekunden für Buffer-Fill

**Problem bei langsamen Verbindungen:**
- Target: 18 Chunks @ ~256KB = ~4.5MB
- Bei 500 Kbps: 72 Sekunden Ladezeit
- Bei 1 Mbps: 36 Sekunden
- Bei 2 Mbps: 18 Sekunden
- ⚠️ 15 Sekunden zu kurz für < 2 Mbps Streams!

**Empfohlen:** 30-45 Sekunden oder adaptive Erkennung

---

## Lösungsansätze

### ✅ Lösung 1: WebUI Konfiguration Anpassen (EINFACHSTE)

**Keine Code-Änderungen nötig!**

1. Dispatcharr WebUI öffnen
2. Settings → Proxy Settings
3. Ändern:
   - **"Channel Initialization Grace Period"**: 5 → **30 Sekunden**
   - **"Buffering Timeout"**: 15 → **30 Sekunden**
   - **"Failover Grace Period"**: 20 → **30 Sekunden**

**Vorteile:**
- ✅ Keine Code-Änderungen
- ✅ Sofort wirksam
- ✅ Per Channel/User anpassbar

**Nachteile:**
- ❌ Muss manuell konfiguriert werden
- ❌ Gilt nicht für neue Installationen

---

### Lösung 2: Default-Werte im Code Anpassen

**File:** `apps/proxy/config.py`

```python
@classmethod
def get_proxy_settings(cls):
    return {
        "buffering_timeout": 30,              # 15 → 30
        "channel_init_grace_period": 30,      # 5 → 30 ⚠️ WICHTIG!
        "chunk_timeout": 10,                  # 5 → 10
        "failover_grace_period": 30,          # 20 → 30
        # ... rest gleich
    }
```

**Vorteile:**
- ✅ Gilt für alle neuen Installationen
- ✅ User können immer noch per WebUI anpassen
- ✅ Bessere Default-Werte

**Nachteile:**
- ❌ Bestehendes System muss Update durchführen
- ❌ WebUI-Konfiguration überschreibt diese Werte

---

### Lösung 3: Adaptive Timeout-Erkennung

**Konzept:** Timeout dynamisch anpassen basierend auf:
- Stream Bitrate (erkannt aus FFmpeg metadata)
- Network latency (erste Chunk-Antwortzeit)
- Buffer Fill Rate (Chunks/Sekunde)

**Pseudo-Code:**

```python
def calculate_adaptive_timeout(self):
    # Messe erste Chunk-Antwortzeit
    first_chunk_latency = self.first_chunk_time - self.connection_start_time
    
    # Schätze Bitrate aus Buffer Fill Rate
    chunks_per_second = self.chunks_filled / self.time_elapsed
    estimated_bitrate = chunks_per_second * self.chunk_size * 8
    
    # Berechne benötigte Zeit für Target-Buffer
    target_chunks = 18
    time_needed = target_chunks / chunks_per_second
    
    # Sicherheitsfaktor + Netzwerk-Overhead
    adaptive_timeout = time_needed * 1.5 + first_chunk_latency * 2
    
    # Minimum/Maximum Grenzen
    return max(10, min(adaptive_timeout, 60))
```

**Vorteile:**
- ✅ Funktioniert automatisch für alle Stream-Geschwindigkeiten
- ✅ Optimal für langsame UND schnelle Streams
- ✅ Reduziert unnötige Failovers

**Nachteile:**
- ❌ Komplexe Implementierung
- ❌ Kann bei instabilen Streams falsch berechnen
- ❌ Braucht Testing mit verschiedenen Streams

---

### Lösung 4: "Delayed Failover" mit Warnung

**Konzept:** Erst warnen, dann failover

```python
def check_buffer_timeout(self):
    elapsed = time.time() - self.buffer_start_time
    
    if elapsed > self.warning_threshold:  # z.B. 15s
        logger.warning(f"Slow buffering detected: {elapsed}s elapsed, "
                      f"{self.chunks_filled}/18 chunks filled")
        # Weiter warten...
    
    if elapsed > self.failover_threshold:  # z.B. 45s
        logger.error(f"Buffer timeout: {elapsed}s elapsed, failing over")
        self.trigger_failover()
```

**Vorteile:**
- ✅ Gibt langsamen Streams mehr Zeit
- ✅ Logging hilft bei Debugging
- ✅ Einfach zu implementieren

**Nachteile:**
- ❌ User müssen immer noch lange warten bei echten Problemen

---

## Alternative Ansätze (Außerhalb Timeout)

### A. Parallele Stream-Validierung

**Problem:** Sequential validation verschwendet Zeit

**Lösung:** Mehrere Streams parallel testen:

```python
import concurrent.futures

def validate_streams_parallel(alternate_streams):
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(validate_stream_url, s['url']): s
            for s in alternate_streams[:5]  # Teste top 5
        }
        
        for future in concurrent.futures.as_completed(futures, timeout=10):
            stream = futures[future]
            try:
                is_valid, final_url, status, msg = future.result()
                if is_valid:
                    return stream  # Erste erfolgreiche!
            except Exception as e:
                logger.debug(f"Stream validation failed: {e}")
    
    return None  # Keine funktionieren
```

**Vorteil:** Schnellerer Failover (3x schneller bei 3 parallel)

---

### B. "Fast Start" mit Mini-Buffer

**Problem:** 18 Chunks (4.5MB) dauert zu lange

**Lösung:** Client mit kleineren Buffer starten:

```python
# Für neue Clients:
if is_new_client:
    # Start mit nur 4 Chunks (~1MB) statt 18
    client.start_index = buffer.index - 4
    client.fast_start = True
    
    # Nachfüllen während Streaming
    spawn_later(5.0, client.catchup_to_live_position)
```

**Vorteil:** Client startet in <2 Sekunden statt 15+

**Nachteil:** Anfangs mehr Buffering-Events beim Client

---

### C. Smarter Failover mit "Health Check"

**Problem:** Failover auch bei temporären Problemen

**Lösung:** Health check vor Failover:

```python
def should_trigger_failover(self):
    # Nicht bei temporären Netzwerk-Problemen
    if self.is_network_recovering():
        logger.info("Network recovering, delaying failover")
        return False
    
    # Nicht wenn Buffer sich langsam füllt
    if self.buffer_fill_rate > 0:
        logger.info(f"Buffer still filling ({self.buffer_fill_rate} chunks/s)")
        return False
    
    # Nur bei echtem Problem
    if self.no_data_received_for > 20:
        return True
    
    return False
```

---

## Empfehlung für User

### 🔥 **SOFORT-LÖSUNG (5 Minuten):**

1. **WebUI öffnen** → Settings → Proxy Settings
2. **Ändern:**
   ```
   Channel Initialization Grace Period: 5 → 30
   Buffering Timeout: 15 → 30
   Failover Grace Period: 20 → 30
   Chunk Timeout: 5 → 10
   ```
3. **Speichern & Neustarten**

### 📊 **MONITORING:**

**Logs beobachten für:**
```
✅ "Buffer filled successfully" innerhalb 30s
✅ "Client connected" ohne "Broken pipe"
✅ "Channel state: ACTIVE" bleibt stabil
❌ "Buffer timeout" → Wert erhöhen
❌ Häufige Failovers → Stream-Provider Problem
```

### 🔧 **LANGFRISTIG:**

1. **Code-Defaults anpassen** (wie Lösung 2)
2. **Adaptive Timeouts implementieren** (wie Lösung 3)
3. **Parallele Stream-Validierung** (wie Alternative A)

---

## Debug-Kommandos

### Redis Buffer Status Checken:

```bash
redis-cli
> HGETALL live:channel:<channel_uuid>:metadata
> GET live:channel:<channel_uuid>:input:buffer:index
> ZRANGE live:channel:<channel_uuid>:input:buffer:chunk_timestamps 0 -1
```

### Logs Filtern:

```bash
# Nur Buffer-relevante Logs
grep -E "buffer|timeout|failover|chunks" dispatcharr.log

# Channel-spezifische Logs
grep "channel_uuid:<deine_uuid>" dispatcharr.log
```

---

## Zusammenfassung

| Lösung | Aufwand | Effektivität | Empfehlung |
|--------|---------|--------------|------------|
| **WebUI Konfiguration** | ⭐ Niedrig | ⭐⭐⭐⭐ Hoch | ✅ **JETZT MACHEN** |
| **Code-Defaults** | ⭐⭐ Mittel | ⭐⭐⭐⭐ Hoch | ✅ Für v0.27.1 |
| **Adaptive Timeout** | ⭐⭐⭐⭐ Hoch | ⭐⭐⭐⭐⭐ Sehr Hoch | 💡 Zukünftig |
| **Parallele Validierung** | ⭐⭐⭐ Mittel-Hoch | ⭐⭐⭐ Mittel | 💡 Optional |
| **Fast Start Buffer** | ⭐⭐⭐ Mittel-Hoch | ⭐⭐⭐⭐ Hoch | 💡 Zukünftig |

---

## Status

**Analyse:** ✅ Abgeschlossen  
**Empfohlene Aktion:** WebUI Timeout-Werte erhöhen  
**Langfristig:** Code-Defaults + Adaptive Timeouts

**Letzte Aktualisierung:** 2026-06-18
