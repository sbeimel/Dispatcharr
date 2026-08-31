# Spezifisches Problem: Client Connect + Chunk Waiting

## Datum: 2026-06-18

---

## Problem-Beschreibung

**User-Aussage:** "es funktioniert ja eigentlich sehr gut nur bei connected und chunk waiting ist das problem"

**Das bedeutet:**
- ✅ Normale Streams funktionieren gut
- ✅ Buffer füllt sich korrekt (18/4 chunks)
- ✅ Channel Status wird korrekt auf "waiting_for_clients"
- ❌ **NUR bei bestimmten Channels:** Client disconnected sofort mit "Broken pipe" (0.12-0.18s)

---

## Root Cause Analyse

### Aus deinen Logs:

```
14:07:25 WARNING Method Not Allowed: /proxy/ts/stream/...
14:07:25 INFO Worker ID: 2 HEAD 405
uwsgi: Broken pipe
Client disconnected after 0.12s
```

### Was hier passiert:

1. **Client (Jellyfin/Plex) sendet HEAD request** → Check ob Stream verfügbar
2. **Dispatcharr antwortet mit 405 Method Not Allowed** → Nur GET erlaubt
3. **Client interpretiert 405 als Fehler** → Disconnected sofort
4. **Dispatcharr versucht GET request zu verarbeiten** → Aber Client ist schon weg
5. **"Broken pipe" Error** → Connection wurde vom Client bereits geschlossen

### Channel 9b24a643 funktioniert, aber 9a15d5f4 nicht

**Wahrscheinliche Ursache:** 
- Channel 9b24a643: Client sendet direkt GET (kein HEAD vorher)
- Channel 9a15d5f4: Client sendet zuerst HEAD (wird mit 405 rejected)

**Warum?**
- Verschiedene Clients verhalten sich unterschiedlich
- Verschiedene Stream-Typen triggern verschiedenes Client-Verhalten
- Content-Type Detection im Client

---

## Das eigentliche Problem

### Problem 1: HEAD Request nicht unterstützt

**File:** `apps/proxy/live_proxy/views.py`

```python
@api_view(["GET"])  # ❌ Nur GET!
@permission_classes([AllowAny])
def stream_ts(request, channel_id, user=None, force_output_format=None):
    # ...
```

**Lösung (die du nicht willst):**
```python
@api_view(["GET", "HEAD"])  # ✅ GET + HEAD
@permission_classes([AllowAny])
def stream_ts(request, channel_id, user=None, force_output_format=None):
    if request.method == "HEAD":
        response = HttpResponse(status=200)
        response["Content-Type"] = "video/mp2t"
        return response
    # ... rest of GET handling
```

---

### Problem 2: HTTP 302 Redirect (vom curl log)

```
< HTTP/1.1 302 Found
< Location: http://89.36.95.53:80/auth/...
```

**File:** `apps/proxy/live_proxy/input/http_streamer.py`

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

**Ohne `allow_redirects=True`:**
- Python requests folgt redirect NICHT automatisch
- Connection bleibt bei 302 stehen
- Kein Stream data kommt an
- Timeout → Failover

---

## Warum funktionieren manche Channels?

### Channel 9b24a643 (funktioniert):
1. ✅ Client sendet nur GET (kein HEAD)
2. ✅ IPTV Provider gibt direkt 200 OK (kein 302)
3. ✅ Stream startet sofort
4. ✅ Bleibt "active"

### Channel 9a15d5f4 (funktioniert nicht):
1. ❌ Client sendet HEAD → 405 Error → Disconnect
2. ❌ **ODER:** IPTV Provider gibt 302 redirect → requests folgt nicht → Timeout
3. ❌ Endless failover durch alle 94 Kombinationen

---

## Weitere mögliche Ursachen (ohne Code-Änderung)

### Ursache A: Chunk Size Mismatch

**Generator erwartet TS packets (188 bytes aligned):**

```python
# apps/proxy/live_proxy/input/buffer.py
self.TS_PACKET_SIZE = 188

# Nur complete TS packets werden weitergegeben:
complete_packets_size = (len(combined_data) // 188) * 188
if complete_packets_size == 0:
    self._partial_packet = combined_data
    return True  # ❌ Kein Chunk für Generator!
```

**Problem bei manchen Streams:**
- HTTP streamer liest chunks von 8192 bytes
- Bei langsamen Streams: Erste Response < 188 bytes
- Buffer fügt nichts hinzu → Generator wartet endlos
- Client timeout → "Broken pipe"

**Prüfe in Logs:**
```
✅ "Added X chunks to Redis" → OK
❌ Kein "Added chunks" nach "connected successfully" → Problem!
```

---

### Ursache B: Client User-Agent Detection

**Manche Clients erwarten bestimmte Headers:**

```python
# Im Generator:
response["Content-Type"] = "video/mp2t"  # TS stream
response["Cache-Control"] = "no-cache"
# ❌ FEHLEN: Transfer-Encoding, Accept-Ranges
```

**Manche Clients (Plex) erwarten:**
```python
response["Transfer-Encoding"] = "chunked"
response["Accept-Ranges"] = "none"  # Kein seeking in live stream
```

---

### Ursache C: Connection Keepalive

**HTTP/1.1 Connection Keepalive Problem:**

```python
# Wenn Client HTTP/1.1 nutzt mit Connection: keep-alive
# Aber Server schließt Connection nach Response:
response = StreamingHttpResponse(...)
# ❌ FEHLT: response["Connection"] = "close"
```

**Manche Clients:**
- Erwarten dass Connection offen bleibt
- Server schließt zu früh
- "Broken pipe" weil Client noch schreibt

---

### Ursache D: Transcode vs Direct Stream

**Bei Channel 9a15d5f4:**

```python
# Wenn Stream HLS/RTSP/UDP ist:
self.stream_type = detect_stream_type(self.url)
if self.transcode == False and self.stream_type in (StreamType.HLS, ...):
    self.transcode = True  # FFmpeg required
```

**Problem:**
- FFmpeg braucht länger zum starten (2-5s)
- Client timeout innerhalb 5s
- "Broken pipe" bevor FFmpeg Daten liefert

---

## Debug-Strategie (OHNE Code-Änderung)

### 1. Prüfe welche Channels funktionieren

```bash
# Logs filtern für erfolgreiche Channels
grep "Channel state: ACTIVE" dispatcharr.log | grep -v "9a15d5f4"

# Vergleiche URLs
# Funktioniert: rtmp://...
# Funktioniert nicht: http://iptv.watchhd.to:5050/...
```

### 2. Prüfe HTTP Response Codes

```bash
# Für funktionierende Channels:
curl -I "http://stream1.example.com/channel1.ts"
# Expected: HTTP/1.1 200 OK

# Für nicht-funktionierende:
curl -I "http://iptv.watchhd.to:5050/live/.../136095.ts"
# Expected: HTTP/1.1 302 Found  ← PROBLEM!
```

### 3. Prüfe Client User-Agent

```bash
# In Logs:
grep "Client connected with user agent" dispatcharr.log

# Funktioniert: "VLC/3.0.20"
# Funktioniert nicht: "Jellyfin/10.8.0" oder "Plex/..."
```

### 4. Prüfe Stream Type

```bash
grep "Detected.*stream" dispatcharr.log

# Channel 9b24a643: "Detected HTTP stream"
# Channel 9a15d5f4: "Detected HLS stream" oder "RTSP stream"
```

---

## Workarounds (OHNE Code-Änderung)

### Workaround 1: Stream URL Proxy verwenden

**Problem:** IPTV Provider sendet 302 redirect

**Lösung:** Verwende redirected URL direkt:

1. Finde finale URL mit curl:
   ```bash
   curl -L "http://iptv.watchhd.to:5050/live/.../136095.ts" 2>&1 | grep "Location:"
   # → http://89.36.95.53:80/auth/...
   ```

2. In Dispatcharr: Ersetze Stream URL mit finaler URL
   - WebUI → Channels → Edit Channel → Custom Stream URL
   - Paste: `http://89.36.95.53:80/auth/...`

**Vorteil:** Kein 302 redirect mehr  
**Nachteil:** URL könnte ablaufen, muss regelmäßig aktualisiert werden

---

### Workaround 2: Force Transcode für problematische Channels

**Problem:** Direct streaming schlägt fehl

**Lösung:** Force FFmpeg transcoding:

1. WebUI → Channels → Edit Channel
2. Output Profile: Select "FFmpeg Re-encode" statt "Direct"
3. Save

**FFmpeg folgt redirects automatisch:**
```bash
ffmpeg -i "http://iptv.watchhd.to:5050/.../136095.ts" ...
# FFmpeg folgt 302 automatisch!
```

**Vorteil:** Funktioniert mit allen Stream-Typen  
**Nachteil:** Höhere CPU-Last, etwas Latenz

---

### Workaround 3: Proxy vor Dispatcharr

**Problem:** IPTV Provider probleme

**Lösung:** Nginx/HAProxy vor Dispatcharr:

```nginx
# nginx.conf
location /proxy-iptv/ {
    proxy_pass http://iptv.watchhd.to:5050/;
    proxy_redirect off;
    proxy_set_header Host iptv.watchhd.to:5050;
    
    # Folge redirects automatisch
    proxy_intercept_errors on;
    error_page 301 302 307 = @handle_redirect;
}

location @handle_redirect {
    resolver 8.8.8.8;
    set $redirect_uri $upstream_http_location;
    proxy_pass $redirect_uri;
}
```

**In Dispatcharr:**
- Stream URL: `http://localhost/proxy-iptv/live/.../136095.ts`

**Vorteil:** Zentrales redirect handling  
**Nachteil:** Extra service, mehr Komplexität

---

### Workaround 4: Erhöhe Buffer Before Client Connect

**Problem:** Client connected bevor Buffer voll ist

**Lösung:** WebUI Settings anpassen:

```
Initial Behind Chunks: 4 → 10
New Client Behind Seconds: 5 → 15
```

**Effekt:**
- Clients starten weiter hinten im Buffer
- Mehr Zeit für Buffer zum füllen
- Weniger "waiting at buffer head" scenarios

---

## Empfehlung für spezifisches Problem

### 🔥 SOFORT-TEST (5 Minuten):

**1. Prüfe HTTP 302 redirect:**
```bash
curl -I "http://iptv.watchhd.to:5050/live/watchgrisu/uBMGG0XQ1hFw/136095.ts"
```

**Wenn 302:**
- ✅ **Root Cause gefunden:** HTTP redirect nicht supported
- ✅ **Lösung:** Code-Änderung nötig (allow_redirects=True)
- ⚠️ **Workaround:** Force transcode oder finale URL verwenden

**2. Prüfe Client Type:**
```bash
grep "9a15d5f4" dispatcharr.log | grep "user agent"
```

**Wenn Jellyfin/Plex:**
- ✅ **Root Cause gefunden:** HEAD request nicht supported
- ✅ **Lösung:** Code-Änderung nötig (accept HEAD)
- ⚠️ **Workaround:** Unterschiedlicher Client (VLC)

**3. Prüfe Stream Type:**
```bash
grep "9a15d5f4" dispatcharr.log | grep "Detected"
```

**Wenn HLS/RTSP:**
- ✅ **Root Cause gefunden:** FFmpeg startup delay
- ✅ **Lösung:** Erhöhe grace period
- ⚠️ **Workaround:** Force transcode profile

---

## Zusammenfassung

| Problem | Wahrscheinlichkeit | Code-Fix Nötig? | Workaround? |
|---------|-------------------|-----------------|-------------|
| **HTTP 302 redirect** | 🔴 Sehr hoch (curl zeigt 302) | ✅ Ja | ✅ Ja (URL/transcode) |
| **HEAD request 405** | 🟡 Mittel (Jellyfin/Plex) | ✅ Ja | ✅ Ja (VLC client) |
| **Chunk size < 188** | 🟢 Niedrig | ❌ Nein | ✅ Ja (buffer settings) |
| **Client keepalive** | 🟢 Niedrig | ⚠️ Maybe | ✅ Ja (headers) |
| **FFmpeg delay** | 🟡 Mittel (HLS/RTSP) | ⚠️ Maybe | ✅ Ja (grace period) |

---

## Next Steps

1. **Prüfe curl output für 302 redirect** ← Deine Logs zeigen das bereits!
2. **Wenn 302:** Entscheide zwischen:
   - ✅ Code-Fix (`allow_redirects=True`)
   - ⚠️ Workaround (transcode oder finale URL)
3. **Prüfe Client User-Agent** in Logs
4. **Wenn Jellyfin/Plex:** Entscheide zwischen:
   - ✅ Code-Fix (HEAD request support)
   - ⚠️ Workaround (VLC statt Jellyfin)

**Status:** Warte auf deine Entscheidung - Code-Fix oder Workaround?
