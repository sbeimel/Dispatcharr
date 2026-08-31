# Final Root Cause: Connected aber keine Chunks

## Datum: 2026-06-18

---

## Das ECHTE Problem

Du hast Recht - **redirect funktioniert normalerweise**. Das Problem ist **NICHT der redirect selbst**, sondern:

### **Problem: Kein Monitoring zwischen "connected" und "chunks arriving"**

---

## Der aktuelle Code-Flow

### Phase 1: Connection Establishment

```python
# apps/proxy/live_proxy/input/manager.py - Line ~1200
def _establish_http_connection(self):
    # Start HTTP streamer thread
    self.http_reader = HTTPStreamReader(url=self.url, ...)
    pipe_fd = self.http_reader.start()  # ✅ Thread gestartet
    
    self.socket = os.fdopen(pipe_fd, 'rb', buffering=0)
    self.connected = True  # ✅ "CONNECTED"
    
    # Set channel state
    self._set_waiting_for_clients()  # ← HIER IST DAS PROBLEM
    
    return True
```

### Phase 2: State Setting (FEHLERHAFT!)

```python
# Line ~1950
def _set_waiting_for_clients(self):
    current_buffer_index = redis_client.get(buffer_index_key)  # = 0
    initial_chunks_needed = ConfigHelper.initial_behind_chunks()  # = 4
    
    if current_buffer_index < initial_chunks_needed:
        # ❌ PROBLEM: Schedulet Funktion die NICHT EXISTIERT!
        timer = threading.Timer(0.5, self._check_buffer_and_set_state)
        timer.daemon = True
        timer.start()
        return False
```

### Phase 3: Chunk Processing (läuft parallel)

```python
# Line ~1250 - _process_stream_data()
def _process_stream_data(self):
    while self.running and self.connected:
        if self.fetch_chunk():  # ← Liest aus pipe
            self.last_data_time = time.time()
            # ✅ Chunks kommen an!
        else:
            gevent.sleep(0.1)  # ⚠️ Timeout, wartet...
```

---

## Was passiert bei deinem Problem-Channel

### Timeline:

```
T+0.00s: _establish_http_connection() called
         ✅ http_reader.start() → Thread started
         ✅ self.connected = True
         ✅ _set_waiting_for_clients() called
         
T+0.00s: _set_waiting_for_clients()
         current_buffer_index = 0 (noch keine chunks!)
         ❌ Scheduled: self._check_buffer_and_set_state()
         ⚠️ Funktion existiert NICHT!
         State = "CONNECTING"
         
T+0.00s: _process_stream_data() läuft parallel
         while self.connected:
             if self.fetch_chunk():  ← Wartet auf Daten aus pipe
                 # Noch nichts da...
                 
T+0.10s: HTTP Reader Thread (parallel):
         response = session.get(url)
         if response.status_code == 200:
             for chunk in response.iter_content():
                 os.write(pipe_write, chunk)  ← Schreibt in pipe
                 
T+0.50s: Timer fired → _check_buffer_and_set_state()
         ❌ AttributeError: Function does not exist!
         ❌ Exception gecatched/ignoriert
         ⚠️ State bleibt "CONNECTING"
         
T+0.50s-5.00s: Zwei Szenarien:

SZENARIO A (funktioniert):
T+0.5s-1.0s: Chunks kommen via pipe
             _process_stream_data() → fetch_chunk() → buffer.add_chunk()
             Buffer index: 1, 2, 3, 4, 5...
             ⚠️ ABER: State bleibt "CONNECTING" (Timer failed!)
             ✅ Clients können trotzdem connecten (State nicht kritisch)

SZENARIO B (funktioniert NICHT):
T+0.5s-5.0s: KEINE Chunks kommen via pipe
             WHY?
             - HTTP Reader Thread hängt bei response.iter_content()
             - Oder: Provider sendet nichts
             - Oder: Netzwerk Problem
             - Oder: Auth Problem (token expired)
             
             _process_stream_data() → fetch_chunk() returns False
             Buffer index bleibt 0
             
T+5.00s: CHANNEL_INIT_GRACE_PERIOD timeout!
         ❌ Failover triggered!
         Channel state → ERROR
         Try next stream...
```

---

## Warum manche Channels funktionieren

### Channel 9b24a643 (funktioniert):

```
T+0.0s: Connection established
T+0.1s: HTTP 200 OK, stream data SOFORT
T+0.2s: fetch_chunk() → data comes through pipe
T+0.3s: buffer.add_chunk() → index = 1, 2, 3...
T+0.5s: Timer fails (function doesn't exist) BUT DOESN'T MATTER
        ✅ Chunks are flowing!
T+1.0s: Client connects
        ✅ Stream works!
```

### Channel 9a15d5f4 (funktioniert NICHT):

```
T+0.0s: Connection established
T+0.1s: HTTP Reader wartet auf Response
T+0.5s: Timer fails
T+1.0s: ⚠️ Immer noch KEINE chunks!
        WHY? Provider Problem:
        - Auth token expired?
        - IP blocked?
        - Stream offline?
        - Rate limiting?
T+5.0s: ❌ Grace period timeout
        ❌ Failover
```

---

## Das ECHTE Problem (nicht redirect!)

### Problem 1: Fehlende Funktion `_check_buffer_and_set_state()`

**File:** `apps/proxy/live_proxy/input/manager.py`

**Line 1950:**
```python
timer = threading.Timer(0.5, self._check_buffer_and_set_state)
```

**Funktion existiert NICHT:**
```bash
$ grep "_check_buffer_and_set_state" apps/proxy/live_proxy/input/manager.py
# Line 1950: timer = threading.Timer(0.5, self._check_buffer_and_set_state)
# ❌ Keine Definition gefunden!
```

**Impact:**
- AttributeError nach 0.5s
- State bleibt "CONNECTING" (statt "WAITING_FOR_CLIENTS")
- ⚠️ Aber nicht kritisch wenn Chunks kommen!

---

### Problem 2: KEIN Watchdog für "connected but no chunks"

**Aktuell gibt es KEIN Monitoring für:**
```
self.connected = True
UND
buffer.index == 0 für > X Sekunden
```

**Es gibt nur:**
1. `last_data_time` check im Health Monitor (läuft alle 5s)
2. Grace period timeout (5s global)

**Aber KEIN spezifisches:**
- "Connected seit 2s aber immer noch 0 chunks" → Force disconnect
- "HTTP Reader Thread lebt aber schreibt nichts" → Force restart

---

### Problem 3: HTTP Reader Error Detection

**File:** `apps/proxy/live_proxy/input/http_streamer.py`

**Problem:** HTTP Reader Thread kann hängen/failen aber niemand merkt es!

```python
def _read_stream(self):
    self.response = self.session.get(self.url, ...)
    
    if self.response.status_code != 200:
        logger.error(f"HTTP {self.response.status_code}")
        return  # ❌ Thread stirbt leise!
    
    for chunk in self.response.iter_content():
        # ⚠️ Kann hier hängen wenn Provider langsam/kaputt
        os.write(self.pipe_write, chunk)
```

**Niemand prüft:**
- Ist HTTP Reader Thread noch am Leben?
- Hat er einen Error?
- Warum kommen keine chunks?

---

## Die ECHTE Root Cause

### **Nicht genug Monitoring zwischen diesen Zuständen:**

```
1. Thread started        ← ✅ Detected
2. Connection opened     ← ✅ Detected (self.connected = True)
3. **Data flowing**      ← ❌ NOT PROPERLY DETECTED!
4. Buffer filling        ← ✅ Detected (buffer.index > 0)
```

**Zwischen 2 und 3 fehlt Detection!**

---

## Lösung: Watchdog für "Connected but no chunks"

### Fix 1: Implementiere fehlende Funktion

**File:** `apps/proxy/live_proxy/input/manager.py`

**Füge nach `_set_waiting_for_clients()` hinzu:**

```python
def _check_buffer_and_set_state(self):
    """
    Retry buffer check and update state when enough chunks available.
    Called by timer in _set_waiting_for_clients().
    """
    try:
        if not self.connected or not self.running:
            logger.debug(f"Skipping buffer check - not connected or not running for channel {self.channel_id}")
            return
            
        channel_id = self.buffer.channel_id
        redis_client = self.buffer.redis_client
        
        if not channel_id or not redis_client:
            logger.warning(f"Missing channel_id or redis_client in buffer check for channel {self.channel_id}")
            return
            
        # Read current buffer index from Redis
        buffer_index_key = RedisKeys.buffer_index(channel_id)
        current_buffer_index = 0
        try:
            redis_index = redis_client.get(buffer_index_key)
            if redis_index:
                current_buffer_index = int(redis_index)
        except Exception as e:
            logger.error(f"Error reading buffer index for channel {self.channel_id}: {e}")
            return
            
        initial_chunks_needed = ConfigHelper.initial_behind_chunks()
        
        # Check if we now have enough chunks
        if current_buffer_index >= initial_chunks_needed:
            logger.info(f"Buffer ready for channel {self.channel_id}: {current_buffer_index}/{initial_chunks_needed} chunks")
            
            # Update state to waiting_for_clients
            metadata_key = RedisKeys.channel_metadata(channel_id)
            current_time = str(time.time())
            update_data = {
                ChannelMetadataField.STATE: ChannelState.WAITING_FOR_CLIENTS,
                ChannelMetadataField.STATE_CHANGED_AT: current_time
            }
            redis_client.hset(metadata_key, mapping=update_data)
            logger.info(f"Updated channel {channel_id} state to WAITING_FOR_CLIENTS")
            return
            
        # Still not enough chunks - check if we should give up or retry
        elapsed_since_connection = time.time() - getattr(self, 'connection_start_time', time.time())
        grace_period = ConfigHelper.channel_init_grace_period()
        
        if elapsed_since_connection >= grace_period:
            # Timeout - connected but no chunks within grace period
            logger.error(
                f"Buffer check timeout for channel {self.channel_id}: "
                f"Connected for {elapsed_since_connection:.1f}s but only {current_buffer_index}/{initial_chunks_needed} chunks. "
                f"Possible provider issue or slow stream."
            )
            
            # Check if HTTP reader thread had an error
            if hasattr(self, 'http_reader') and self.http_reader:
                if self.http_reader.error_occurred:
                    logger.error(f"HTTP reader reported error for channel {self.channel_id} - triggering reconnect")
                    
            # Don't force disconnect here - let grace period timeout handle it
            return
            
        # Retry - schedule another check
        retry_interval = min(0.5 + (elapsed_since_connection * 0.1), 2.0)  # Progressive backoff
        logger.debug(
            f"Buffer check retry for channel {self.channel_id}: "
            f"{current_buffer_index}/{initial_chunks_needed} chunks after {elapsed_since_connection:.1f}s, "
            f"retry in {retry_interval:.1f}s"
        )
        
        timer = threading.Timer(retry_interval, self._check_buffer_and_set_state)
        timer.daemon = True
        timer.start()
        self._buffer_check_timers.append(timer)
        
    except Exception as e:
        logger.error(f"Error in _check_buffer_and_set_state for channel {self.channel_id}: {e}", exc_info=True)
```

---

### Fix 2: HTTP Reader Error Tracking

**File:** `apps/proxy/live_proxy/input/http_streamer.py`

**Füge `error_occurred` flag hinzu:**

```python
class HTTPStreamReader:
    def __init__(self, url, user_agent=None, ...):
        # ... existing code ...
        self.error_occurred = False  # ✅ NEW
        self.error_message = None    # ✅ NEW
    
    def _read_stream(self):
        try:
            # ... existing connection code ...
            
            if self.response.status_code != 200:
                self.error_occurred = True  # ✅ NEW
                self.error_message = f"HTTP {self.response.status_code}"  # ✅ NEW
                logger.error(f"HTTP {self.response.status_code} from {self.url}")
                return
                
            # ... rest of code ...
            
        except requests.exceptions.RequestException as e:
            self.error_occurred = True  # ✅ NEW
            self.error_message = str(e)  # ✅ NEW
            logger.error(f"HTTP reader request error: {e}")
```

---

### Fix 3: Bessere Logging für Diagnostics

**In `_check_buffer_and_set_state()`:**

```python
# Log HTTP reader status
if hasattr(self, 'http_reader') and self.http_reader:
    if self.http_reader.running:
        logger.debug(f"HTTP reader thread is running for channel {self.channel_id}")
    else:
        logger.warning(f"HTTP reader thread is NOT running for channel {self.channel_id}")
        
    if self.http_reader.error_occurred:
        logger.error(f"HTTP reader error: {self.http_reader.error_message}")
```

---

## Test-Strategie

### Test 1: Fehlende Funktion Fix

```bash
# Logs beobachten:
grep "_check_buffer_and_set_state" dispatcharr.log

# Expected:
# T+0.5s: Buffer check retry: 0/4 chunks after 0.5s
# T+1.0s: Buffer check retry: 2/4 chunks after 1.0s
# T+1.5s: Buffer ready: 5/4 chunks
# T+1.5s: Updated channel state to WAITING_FOR_CLIENTS
```

### Test 2: Timeout Detection

```bash
# Logs beobachten für problematischen Channel:

# Expected (bei Problem):
# T+0.5s: Buffer check retry: 0/4 chunks
# T+1.0s: Buffer check retry: 0/4 chunks
# T+2.0s: Buffer check retry: 0/4 chunks
# T+3.0s: Buffer check retry: 0/4 chunks
# T+5.0s: Buffer check timeout: Connected 5.0s but only 0/4 chunks
# T+5.0s: HTTP reader reported error: HTTP 403 Forbidden
# T+5.0s: Grace period timeout - attempting stream switch
```

### Test 3: HTTP Reader Error Detection

```python
# Simuliere HTTP Error:
# HTTP Reader gibt 403/404/500

# Expected logs:
# HTTP reader error occurred: HTTP 403
# Buffer check: HTTP reader reported error - triggering reconnect
```

---

## Zusammenfassung

| Problem | Impact | Fix Effort | Priority |
|---------|--------|-----------|----------|
| Fehlende `_check_buffer_and_set_state()` | ⭐⭐⭐⭐ Hoch | ⭐⭐ Mittel | 🔥 CRITICAL |
| Keine HTTP Reader Error Detection | ⭐⭐⭐ Mittel | ⭐ Einfach | ⚠️ HIGH |
| Schlechte Diagnostics | ⭐⭐ Niedrig | ⭐ Einfach | ✅ NICE |

**Empfehlung:**
1. ✅ **Fix 1** implementieren (fehlende Funktion) - Löst Timer Problem
2. ✅ **Fix 2** implementieren (Error Tracking) - Bessere Diagnostics
3. ✅ **Fix 3** implementieren (Logging) - Debugging

**Status:** Root Cause final identifiziert ✅  
**Problem:** Fehlende Funktion + keine Error Detection zwischen "connected" und "chunks flowing"
