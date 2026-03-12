# Preview vs. Normal Streaming - Vollständige Erklärung

**Datum:** 2026-03-12  
**Version:** 1.0

---

## Übersicht

Es gibt 2 verschiedene Streaming-Modi mit unterschiedlichem Verhalten:

1. **Stream Preview** - Schneller Test ob Stream funktioniert
2. **Normal Streaming** - Vollständiges Streaming mit Failover

---

## 1. Stream Preview

### Was ist Stream Preview?

Stream Preview ist eine **Test-Funktion** um schnell zu prüfen ob ein Stream funktioniert.

### Wo wird es verwendet?

- In der Web-UI wenn du auf "Preview" klickst
- API Endpoint: `/api/channels/{channel_id}/preview_stream/`

### Wie funktioniert es?

```
User klickt "Preview" für RTL HD
═══════════════════════════════════════════════════════════════

1. Hole AKTUELLEN Stream (z.B. Stream #1 von Provider A)
2. Hole ALLE Profile für diesen Stream (Profile 1, 2, 3)
3. Probiere Profile nacheinander:
   ├─ Profil 1 → FEHLER
   ├─ Profil 2 → FEHLER
   └─ Profil 3 → ERFOLG! ✅

Ergebnis: "Stream funktioniert mit Profil 3"
```

### Wichtig: KEINE Backup-Streams!

```
❌ Preview probiert NICHT:
   - Backup-Streams (Stream #2, #3, etc.)
   - Andere Provider
   - Alternative URLs

✅ Preview probiert NUR:
   - Alle Profile vom AKTUELLEN Stream
```

### Warum keine Backup-Streams?

Preview ist für **schnelle Tests** gedacht:
- Soll in 3-5 Sekunden fertig sein
- Zeigt ob der AKTUELLE Stream funktioniert
- Nicht für vollständiges Failover

### Code-Beispiel

```python
# apps/channels/api_views.py - preview_stream()

# Hole aktuellen Stream
stream_id, profile_id, error = channel.get_stream()

# Probiere alle Profile für DIESEN Stream
for profile in profiles:
    url = generate_url(stream, profile)
    if validate_url(url):
        return {"success": True, "profile": profile.id}

# ❌ KEINE Backup-Streams!
return {"error": "Stream nicht erreichbar"}
```

---

## 2. Normal Streaming

### Was ist Normal Streaming?

Normal Streaming ist das **vollständige Streaming** mit automatischem Failover.

### Wo wird es verwendet?

- Wenn du einen Kanal im Player öffnest
- M3U Playlist URLs
- XC API Streaming

### Wie funktioniert es?

```
User startet RTL HD im Player
═══════════════════════════════════════════════════════════════

PHASE 1: Aktueller Stream (Stream #1)
├─ Profil 1 → FEHLER
├─ Profil 2 → FEHLER
└─ Profil 3 → FEHLER

❌ Alle Profile von Stream #1 fehlgeschlagen!

PHASE 2: Backup-Stream (Stream #2)
├─ Profil 1 → FEHLER
├─ Profil 2 → ERFOLG! ✅

✅ Stream läuft mit Stream #2, Profil 2
```

### Profile Failover (343 Kombinationen)

Das System probiert **ALLE möglichen Kombinationen**:

```
Beispiel: RTL HD hat 3 Streams, jeder mit 2 Profilen
═══════════════════════════════════════════════════════════════

Stream #1 (Provider A):
├─ Profil 1 (FFmpeg)
└─ Profil 2 (HTTP Proxy)

Stream #2 (Provider B):
├─ Profil 1 (FFmpeg)
└─ Profil 2 (HTTP Proxy)

Stream #3 (Provider C):
├─ Profil 1 (FFmpeg)
└─ Profil 2 (HTTP Proxy)

Gesamt: 3 Streams × 2 Profile = 6 Kombinationen
```

### Automatischer Failover während Streaming

```
Stream läuft mit Stream #1, Profil 1
═══════════════════════════════════════════════════════════════

Nach 5 Minuten: Stream bricht ab! ❌

Automatischer Failover:
├─ Stream #1, Profil 2 → FEHLER
├─ Stream #2, Profil 1 → FEHLER
├─ Stream #2, Profil 2 → ERFOLG! ✅

✅ Stream wechselt automatisch zu Stream #2, Profil 2
✅ User merkt nichts (nahtloser Übergang)
```

### Code-Beispiel

```python
# apps/proxy/ts_proxy/stream_manager.py

def _handle_stream_failure(self):
    # Hole alle alternativen Streams
    alternates = get_alternate_streams(channel_id, current_stream_id)
    
    for alt_stream in alternates:
        # Probiere alle Profile für diesen Stream
        for profile in alt_stream.profiles:
            url = generate_url(alt_stream, profile)
            if validate_url(url):
                # ✅ Wechsle zu diesem Stream
                self.switch_stream(url, profile)
                return True
    
    # ❌ Alle Streams fehlgeschlagen
    return False
```

---

## Vergleich: Preview vs. Normal Streaming

| Feature | Stream Preview | Normal Streaming |
|---------|---------------|------------------|
| **Zweck** | Schneller Test | Vollständiges Streaming |
| **Dauer** | 3-5 Sekunden | Unbegrenzt |
| **Profile** | ✅ Alle Profile vom aktuellen Stream | ✅ Alle Profile von allen Streams |
| **Backup-Streams** | ❌ NEIN | ✅ JA |
| **Failover** | ❌ NEIN | ✅ JA (automatisch) |
| **Retry-Loop** | ✅ JA (3 Sekunden) | ✅ JA (3 Sekunden) |
| **Connection Leak Fix** | ✅ JA (Bugfix #7) | ✅ JA (Bugfix #7) |

---

## Beispiel-Szenarien

### Szenario 1: Preview - Stream funktioniert

```
User: Klickt "Preview" für RTL HD
═══════════════════════════════════════════════════════════════

System:
├─ Aktueller Stream: Stream #1 (Provider A)
├─ Probiere Profil 1 → ERFOLG! ✅
└─ Ergebnis: "Stream erreichbar mit Profil 1"

User sieht: ✅ Grüner Haken "Stream OK"
```

### Szenario 2: Preview - Stream funktioniert nicht

```
User: Klickt "Preview" für RTL HD
═══════════════════════════════════════════════════════════════

System:
├─ Aktueller Stream: Stream #1 (Provider A)
├─ Probiere Profil 1 → FEHLER ❌
├─ Probiere Profil 2 → FEHLER ❌
└─ Ergebnis: "Stream nicht erreichbar"

User sieht: ❌ Roter Fehler "Stream nicht erreichbar"

WICHTIG: Backup-Streams werden NICHT probiert!
```

### Szenario 3: Normal Streaming - Failover zu Backup

```
User: Startet RTL HD im Player
═══════════════════════════════════════════════════════════════

System:
├─ Aktueller Stream: Stream #1 (Provider A)
├─ Probiere Profil 1 → FEHLER ❌
├─ Probiere Profil 2 → FEHLER ❌
│
├─ Backup Stream: Stream #2 (Provider B)
├─ Probiere Profil 1 → ERFOLG! ✅
└─ Stream läuft mit Stream #2, Profil 1

User sieht: ✅ Stream läuft (merkt nicht dass Backup verwendet wird)
```

### Szenario 4: Normal Streaming - Alle Streams fehlgeschlagen

```
User: Startet RTL HD im Player
═══════════════════════════════════════════════════════════════

System:
├─ Stream #1, Profil 1 → FEHLER ❌
├─ Stream #1, Profil 2 → FEHLER ❌
├─ Stream #2, Profil 1 → FEHLER ❌
├─ Stream #2, Profil 2 → FEHLER ❌
├─ Stream #3, Profil 1 → FEHLER ❌
└─ Stream #3, Profil 2 → FEHLER ❌

User sieht: ❌ Fehler "No available streams for this channel"
```

---

## Connection Leak Fix (Bugfix #7)

### Gilt für BEIDE Modi!

Bugfix #7 verhindert Connection Leaks in:
- ✅ Stream Preview
- ✅ Normal Streaming

### Wie funktioniert es?

```python
# BEIDE Modi verwenden den gleichen Retry-Loop:

while retry:
    stream_url = generate_stream_url(channel_id)
    # ↑ Reserviert Slot: Counter +1
    
    if stream_url:
        break  # ✅ Erfolg! Counter bleibt
    
    # ❌ Fehler! Gebe Slot frei
    channel.release_stream()  # Counter -1
    gevent.sleep(retry_interval)

# Wenn alle Versuche fehlschlagen:
channel.release_stream()  # ✅ Finaler Cleanup
```

### Ergebnis

```
Vorher (BUGGY):
├─ 14 Versuche → Counter = 14 ❌
└─ Nächster User: "No profiles available" ❌

Nachher (GEFIXT):
├─ 14 Versuche → Counter = 0 ✅
└─ Nächster User: Stream funktioniert ✅
```

---

## Häufige Fragen

### Q1: Warum probiert Preview keine Backup-Streams?

**A:** Preview ist für schnelle Tests gedacht (3-5 Sekunden). Backup-Streams würden zu lange dauern.

### Q2: Wie kann ich alle Streams testen?

**A:** Verwende Normal Streaming im Player. Das System probiert automatisch alle Streams.

### Q3: Was passiert wenn Preview fehlschlägt aber Normal Streaming funktioniert?

**A:** Das ist normal! Preview testet nur den aktuellen Stream. Normal Streaming probiert auch Backup-Streams.

### Q4: Werden Profile-Slots bei Preview auch freigegeben?

**A:** Ja! Bugfix #7 gilt für beide Modi. Slots werden immer korrekt freigegeben.

### Q5: Kann ich Backup-Streams in Preview aktivieren?

**A:** Nein, das ist nicht vorgesehen. Preview ist bewusst auf den aktuellen Stream beschränkt.

---

## Zusammenfassung

### Stream Preview
- ✅ Schneller Test (3-5 Sekunden)
- ✅ Probiert alle Profile vom aktuellen Stream
- ❌ Probiert KEINE Backup-Streams
- ✅ Connection Leak Fix aktiv

### Normal Streaming
- ✅ Vollständiges Streaming
- ✅ Probiert alle Profile von allen Streams
- ✅ Automatischer Failover zu Backup-Streams
- ✅ Connection Leak Fix aktiv
- ✅ 343 Kombinationen möglich

### Beide Modi
- ✅ Retry-Loop (3 Sekunden)
- ✅ Profile Failover
- ✅ Connection Leak Fix (Bugfix #7)
- ✅ TTL (1 Stunde) als Sicherheitsnetz

---

**Erstellt:** 2026-03-12  
**Version:** 1.0  
**Status:** PRODUKTIONSREIF

</content>
