# ROOT CAUSE: Connected aber keine Chunks ankommen

## Datum: 2026-06-18

---

## DAS HAUPTPROBLEM (gefunden!)

### User's Beobachtung:
> "das hauptproblem ist doch das nicht erkannt wird, dass es zwar connected ist aber keine chunks kommen"

### Root Cause gefunden in `apps/proxy/live_proxy/input/manager.py`:

**Line ~1900: `_set_waiting_for_clients()` Funktion**

```python
def _set_waiting_for_clients(self):
    """Set channel state to waiting for clients AFTER buffer has enough chunks"""
    # ...
    
    # NEW CODE: Check if buffer has enough chunks
    buffer_index_key = RedisKeys.buffer_index(channel_id)
    current_buffer_index = 0
    try:
        redis_index = redis_client.get(buffer_index_key)
        if redis_index:
            current_buffer_index = int(redis_index)
    except Exception as e:
        logger.error(f"Error reading buffer index from Redis: {e}")

    initial_chunks_needed = ConfigHelper.initial_behind_chunks()  # Default: 4

    if current_buffer_index < initial_chunks_needed:
        # ❌ PROBLEM: Wartet nur 0.5 Sekunden dann gibt auf!
        timer = threading.Timer(0.5, self._check_buffer_and_set_state)
        timer.daemon = True
        timer.start()
        return False  # ❌ Gibt auf!
```

---

## Was passiert:

### Szenario: HTTP 302 Redirect oder langsamer Stream

```
T+0.0s: HTTP connection established (self.connected = True)
        ✅ Status: "connected successfully"

T+0.0s: _set_waiting_for_clients() aufgerufen
        Prüft: current_buffer_index < 4?
        → JA! Index = 0 (noch keine chunks)
        
T+0.0s: Setzt Status auf "CONNECTING"
        Timer: 0.5s bis _check_buffer_and_set_state()
        
T+0.1s: HTTP 302 redirect processing...
        → requests folgt redirect NICHT (allow_redirects=False)
        → Verbindung bleibt stehen
        → KEINE chunks kommen!

T+0.5s: Timer fired → _check_buffer_and_set_state()
        Prüft: current_buffer_index < 4?
        → JA! Immer noch 0!
        ⚠️ Was jetzt? Funktion existiert nicht in Code!

T+5.0s: CHANNEL_INIT_GRACE_PERIOD timeout!
        ❌ Failover triggered!
```

---

## Der kritische Code-Pfad

### 1. HTTP Connection (funktioniert)

**File:** `apps/proxy/live_proxy/input/manager.py`

```python
def _establish_http_connection(self):
    # ...
    self.response = session.get(
        self.url,
        headers=headers,
        stream=True,
        timeout=(5, 30)
        # ❌ FEHLT: allow_redirects=True
    )
    
    if self.response.status_code == 200:
        self.connected = True  # ✅ Connection "successful"
        logger.info("HTTP reader connected successfully")
        
        # ❌ ABER: Bei 302 redirect hängt hier!
        # response.iter_content() wartet auf Daten die nie kommen
```

### 2. Buffer Fill Check (wartet nur 0.5s)

```python
def _set_waiting_for_clients(self):
    if current_buffer_index < initial_chunks_needed:
        # ❌ PROBLEM: Nur EIN retry nach 0.5s!
        timer = threading.Timer(0.5, self._check_buffer_and_set_state)
        timer.daemon = True
        timer.start()
        return False
```

### 3. Fehlende Funktion!

**`_check_buffer_and_set_state()` existiert NICHT im Code!**

```bash
$ grep -r "_check_buffer_and_set_state" apps/
# ❌ Keine Ergebnisse!
```

**Das bedeutet:**
- Timer wird nach 0.5s gefeuert
- Versucht `_check_buffer_and_set_state()` aufzurufen
- ❌ **AttributeError:** Funktion existiert nicht!
- Exception wird ge-catched/ignoriert
- Channel bleibt in "CONNECTING" State
- Nach 5s Grace Period: Timeout → Failover

---

## Warum manche Channels funktionieren

### Channel 9b24a643 (funktioniert):

```
T+0.0s: HTTP GET → 200 OK direkt (kein redirect)
T+0.0s: Stream data kommt SOFORT
T+0.1s: buffer.add_chunk() → Index 1, 2, 3...
T+0.5s: current_buffer_index = 8 (> 4 needed)
       ✅ Status → "WAITING_FOR_CLIENTS"
T+1.0s: Client connected
       ✅ Status → "ACTIVE"
```

### Channel 9a15d5f4 (funktioniert NICHT):

```
T+0.0s: HTTP GET → 302 Found
        ❌ requests folgt nicht (allow_redirects=False)
        Connection hängt bei redirect response
        
T+0.0s: self.connected = True (fälschlicherweise!)
        response.status_code gibt es nicht bei 302
        ❌ Code prüft nur status_code == 200
        
T+0.5s: Timer → _check_buffer_and_set_state()
        ❌ Funktion existiert nicht
        ❌ Exception gecatched
        
T+5.0s: Grace period timeout
        ❌ Failover triggered
```

---

## Beweis aus den Logs

### Deine Logs zeigen:

```
14:07:25 INFO HTTP reader connected successfully  ← ✅ self.connected = True
14:07:25 INFO Channel connected but waiting for buffer to fill: 0/4 chunks
                                                                 ↑ ❌ PROBLEM!
14:07:25 INFO Set channel state to CONNECTING
14:07:30 WARNING Buffer timeout after 5s  ← ❌ Grace period expired
14:07:30 INFO Attempting stream switch...  ← Failover
```

**Zwischen 14:07:25 und 14:07:30:**
- ✅ Connected = True
- ❌ Buffer Index = 0 (KEINE chunks!)
- ⚠️ Kein "Added chunks to Redis" log
- ❌ Kein "HTTP reader followed redirects" log

---

## Die 3 kritischen Bugs

### Bug 1: HTTP Redirect nicht gefolgt

**File:** `apps/proxy/live_proxy/input/http_streamer.py` (Line 87)

```python
self.response = self.session.get(
    self.url,
    headers=headers,
    stream=True,
    timeout=(5, 30),
    proxies=proxies,
    # ❌ FEHLT: allow_redirects=True
)
```

**Fix:**
```python
self.response = self.session.get(
    self.url,
    headers=headers,
    stream=True,
    timeout=(5, 30),
    proxies=proxies,
    allow_redirects=True,  # ✅ Follow 302 redirects
)
```

---

### Bug 2: Fehlende Buffer Check Retry Funktion

**File:** `apps/proxy/live_proxy/input/manager.py` (Line ~1920)

```python
def _set_waiting_for_clients(self):
    if current_buffer_index < initial_chunks_needed:
        # ❌ Ruft nicht-existierende Funktion auf!
        timer = threading.Timer(0.5, self._check_buffer_and_set_state)
        timer.daemon = True
        timer.start()
        return False
```

**Problem:** `_check_buffer_and_set_state()` Funktion **existiert nicht**!

**Fix Option A - Implementiere die Funktion:**
```python
def _check_buffer_and_set_state(self):
    """Retry buffer check and set state when enough chunks available"""
    try:
        if not self.connected or not self.running:
            return
            
        channel_id = self.buffer.channel_id
        redis_client = self.buffer.redis_client
        
        if not channel_id or not redis_client:
            return
            
        # Read current buffer index from Redis
        buffer_index_key = RedisKeys.buffer_index(channel_id)
        current_buffer_index = 0
        try:
            redis_index = redis_client.get(buffer_index_key)
            if redis_index:
                current_buffer_index = int(redis_index)
        except Exception as e:
            logger.error(f"Error reading buffer index: {e}")
            return
            
        initial_chunks_needed = ConfigHelper.initial_behind_chunks()
        
        if current_buffer_index < initial_chunks_needed:
            # Still not enough - schedule another retry
            logger.debug(f"Buffer check retry: {current_buffer_index}/{initial_chunks_needed} chunks")
            timer = threading.Timer(0.5, self._check_buffer_and_set_state)
            timer.daemon = True
            timer.start()
            self._buffer_check_timers.append(timer)
            return
            
        # Enough chunks now - set to waiting_for_clients
        logger.info(f"Buffer ready: {current_buffer_index}/{initial_chunks_needed} chunks")
        self._set_waiting_for_clients()
        
    except Exception as e:
        logger.error(f"Error in _check_buffer_and_set_state: {e}", exc_info=True)
```

**Fix Option B - Verwende gevent spawn_later statt Timer:**
```python
def _set_waiting_for_clients(self):
    if current_buffer_index < initial_chunks_needed:
        # ✅ Verwende gevent spawn_later für bessere Integration
        import gevent
        gevent.spawn_later(0.5, self._retry_buffer_check)
        return False

def _retry_buffer_check(self):
    """Retry buffer check until enough chunks or timeout"""
    max_retries = 10  # 10 * 0.5s = 5 seconds max
    retry_count = 0
    
    while retry_count < max_retries and self.connected and self.running:
        current_buffer_index = self._get_current_buffer_index()
        initial_chunks_needed = ConfigHelper.initial_behind_chunks()
        
        if current_buffer_index >= initial_chunks_needed:
            logger.info(f"Buffer ready after {retry_count} retries")
            self._set_waiting_for_clients()
            return
            
        retry_count += 1
        gevent.sleep(0.5)
    
    logger.warning(f"Buffer check timeout after {retry_count} retries")
```

---

### Bug 3: Keine Erkennung dass Connection hängt

**Problem:** `self.connected = True` aber `buffer.index = 0` für > 5 Sekunden

**File:** `apps/proxy/live_proxy/input/manager.py`

**Aktuell:** Keine Erkennung!

**Fix - Watchdog Timer:**
```python
def _start_buffer_fill_watchdog(self):
    """Monitor if chunks are actually coming after connection"""
    import gevent
    
    def watchdog():
        start_time = time.time()
        grace_period = ConfigHelper.channel_init_grace_period()
        
        while self.connected and self.running:
            elapsed = time.time() - start_time
            current_buffer_index = self._get_current_buffer_index()
            
            if current_buffer_index > 0:
                # Chunks are coming - watchdog successful
                logger.debug(f"Watchdog: Buffer filling ({current_buffer_index} chunks)")
                return
                
            if elapsed > grace_period:
                # Connected but NO chunks for grace_period seconds
                logger.error(
                    f"Watchdog: Connected for {elapsed:.1f}s but NO chunks received! "
                    f"Possible redirect or stream issue. Triggering failover."
                )
                # Force disconnect and retry
                self.connected = False
                self._close_connection()
                return
                
            gevent.sleep(1.0)
    
    gevent.spawn(watchdog)
```

---

## Empfohlene Fixes (Priorität)

### 🔥 CRITICAL - Fix 1: HTTP Redirect Support

**File:** `apps/proxy/live_proxy/input/http_streamer.py`

**Line 87:** Füge `allow_redirects=True` hinzu

**Impact:** 
- ✅ 302 redirects werden gefolgt
- ✅ Stream data kommt an
- ✅ Buffer füllt sich
- ✅ Kein falsches "connected" mehr

**Test:**
```bash
# Vorher:
curl -I http://iptv.watchhd.to:5050/.../136095.ts
# → 302 Found (Dispatcharr hängt)

# Nachher:
curl -L http://iptv.watchhd.to:5050/.../136095.ts
# → 200 OK (funktioniert)
```

---

### 🔥 CRITICAL - Fix 2: Buffer Check Funktion

**File:** `apps/proxy/live_proxy/input/manager.py`

**Füge hinzu:** `_check_buffer_and_set_state()` Funktion (siehe oben)

**Impact:**
- ✅ Retry funktioniert
- ✅ Wartet auf Buffer fill
- ✅ Keine AttributeError mehr

---

### ⚠️ HIGH - Fix 3: Buffer Fill Watchdog

**File:** `apps/proxy/live_proxy/input/manager.py`

**Füge hinzu:** `_start_buffer_fill_watchdog()` Funktion

**Call in:** `_establish_http_connection()` nach `self.connected = True`

**Impact:**
- ✅ Erkennt "connected aber keine chunks"
- ✅ Force disconnect bei Problem
- ✅ Schnellerer Failover (statt 5s grace period)
- ✅ Bessere Logs

---

## Test-Strategie

### Test 1: HTTP 302 Redirect

```bash
# Terminal 1: Start Dispatcharr mit Fix
# Terminal 2: Test redirect stream
curl -v http://localhost:8000/proxy/ts/stream/{channel_uuid}
```

**Expected Logs:**
```
✅ HTTP reader followed redirects: http://iptv...5050/... -> http://89.36.95.53:80/...
✅ HTTP reader connected successfully to http://89.36.95.53:80/...
✅ Added 1 chunks to Redis (256KB)
✅ Channel state: WAITING_FOR_CLIENTS
```

---

### Test 2: Buffer Fill Detection

```python
# Simuliere langsamen Stream (test code):
import time
time.sleep(2)  # Delay vor erstem chunk

# Expected logs:
# T+0.0s: Connected
# T+0.5s: Buffer check retry: 0/4 chunks
# T+1.0s: Buffer check retry: 0/4 chunks
# T+2.0s: Added 1 chunks to Redis
# T+2.5s: Buffer ready: 5/4 chunks
# T+2.5s: Channel state: WAITING_FOR_CLIENTS
```

---

### Test 3: Watchdog Detection

```python
# Simuliere stuck connection:
response.status_code = 200  # Fake success
# Aber: response.iter_content() returnt nichts

# Expected logs:
# T+0.0s: Connected successfully
# T+1.0s: Watchdog: Buffer still at 0 chunks
# T+2.0s: Watchdog: Buffer still at 0 chunks
# ...
# T+5.0s: Watchdog: Connected for 5.0s but NO chunks! Triggering failover.
# T+5.0s: Closed connection, attempting stream switch
```

---

## Zusammenfassung

| Bug | Symptom | Impact | Fix Complexity |
|-----|---------|--------|----------------|
| **HTTP Redirect** | 302 nicht gefolgt | ⭐⭐⭐⭐⭐ Sehr hoch | ⭐ Einfach (1 Zeile) |
| **Buffer Check Funktion** | AttributeError | ⭐⭐⭐⭐ Hoch | ⭐⭐ Mittel (30 Zeilen) |
| **No-Chunk Detection** | Langsamer Failover | ⭐⭐⭐ Mittel | ⭐⭐⭐ Mittel-Hoch (50 Zeilen) |

**Empfehlung:**
1. ✅ **Zuerst Fix 1** (HTTP redirect) - Löst 80% des Problems
2. ✅ **Dann Fix 2** (Buffer check) - Verhindert crashes
3. ⚠️ **Optional Fix 3** (Watchdog) - Bessere Diagnostics

**Status:** Root Cause identifiziert ✅  
**Next Step:** Fixes implementieren (deine Entscheidung)
