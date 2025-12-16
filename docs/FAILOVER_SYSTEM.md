# Dispatcharr Failover System

## Übersicht

Das Failover-System in Dispatcharr sorgt dafür, dass Streams bei Problemen automatisch auf alternative Quellen umgeschaltet werden. Es gibt mehrere Failover-Ebenen, die in einer bestimmten Reihenfolge durchlaufen werden.

## Failover-Hierarchie

```
Stream läuft → Problem erkannt → Failover startet
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │  1. MAC Failover    │  (nur bei MAC/STB Accounts)
                              │  Nächste MAC im     │
                              │  selben Account     │
                              └─────────┬───────────┘
                                        │ Fehlgeschlagen
                                        ▼
                              ┌─────────────────────┐
                              │  2. Profile Failover│  (nur bei XC Accounts)
                              │  Nächstes Profil im │
                              │  selben Account     │
                              └─────────┬───────────┘
                                        │ Fehlgeschlagen
                                        ▼
                              ┌─────────────────────┐
                              │  3. Stream Failover │
                              │  Nächster Stream    │
                              │  (Backup-Quelle)    │
                              └─────────┬───────────┘
                                        │ Fehlgeschlagen
                                        ▼
                              ┌─────────────────────┐
                              │  Alle Optionen      │
                              │  erschöpft - Stop   │
                              └─────────────────────┘
```

## Detaillierte Erklärung

### 1. MAC Failover (nur MAC/STB Portale)

**Was passiert:**
- Wenn ein MAC-Portal-Stream fehlschlägt, wird zuerst versucht, eine andere MAC-Adresse im selben Account zu verwenden
- Die fehlgeschlagene MAC wird in "Cooldown" gesetzt (standardmäßig 5 Minuten)
- Die nächste verfügbare MAC wird ausgewählt

**Beispiel:**
```
Account: "IPTV Portal 1" (MAC Account)
MACs: 
  - 00:1A:79:AA:BB:CC (aktiv, wird gerade verwendet)
  - 00:1A:79:DD:EE:FF (verfügbar)
  - 00:1A:79:11:22:33 (verfügbar)

Stream "RTL HD" läuft mit MAC 00:1A:79:AA:BB:CC
→ Verbindung bricht ab
→ MAC 00:1A:79:AA:BB:CC wird in Cooldown gesetzt
→ MAC 00:1A:79:DD:EE:FF wird verwendet
→ Stream läuft weiter
```

**Einstellungen (MAC Portal → Settings → Cooldowns):**
- `mac_cooldown_failure`: Cooldown nach Fehler (Standard: 5 Min)
- `mac_cooldown_block`: Cooldown nach Block (Standard: 30 Min)

### 2. Profile Failover (nur XtreamCodes Accounts)

**Was passiert:**
- Bei XtreamCodes-Accounts mit mehreren Profilen wird das nächste Profil versucht
- Profile können unterschiedliche Zugangsdaten oder Server haben
- Das fehlgeschlagene Profil wird in Cooldown gesetzt

**Beispiel:**
```
Account: "XC Provider" (XtreamCodes Account)
Profile:
  - "Hauptprofil" (Standard, max 2 Streams)
  - "Backup-Profil" (max 1 Stream)

Stream "ProSieben" läuft mit "Hauptprofil"
→ Server antwortet nicht
→ "Hauptprofil" wird in Cooldown gesetzt
→ "Backup-Profil" wird verwendet
→ Stream läuft weiter
```

**Einstellungen:**
- `portal_cooldown_error`: Cooldown nach Fehler (Standard: 3 Min)

### 3. Stream Failover (Backup-Streams)

**Was passiert:**
- Wenn MAC und Profile Failover erschöpft sind, wird der nächste Stream für den Channel verwendet
- Streams sind nach Priorität sortiert (niedrigere Nummer = höhere Priorität)
- Kann auch Streams von anderen Accounts sein

**Beispiel:**
```
Channel: "Das Erste HD"
Zugewiesene Streams (nach Priorität):
  1. Stream von "IPTV Portal 1" (MAC Account)
  2. Stream von "XC Provider" (XtreamCodes Account)
  3. Stream von "Backup M3U" (Standard M3U)

Stream 1 fehlgeschlagen (alle MACs erschöpft)
→ Stream 2 wird versucht
→ Stream 2 funktioniert
→ Channel läuft weiter
```

## Ablauf-Beispiele

### Beispiel 1: MAC Account mit mehreren MACs

```
Ausgangssituation:
- Channel: "RTL HD"
- Account: MAC Portal mit 3 MACs
- Aktive MAC: 00:1A:79:AA:BB:CC

Ablauf:
1. Stream startet mit MAC 00:1A:79:AA:BB:CC ✓
2. Nach 10 Minuten: Verbindung bricht ab
3. MAC Failover startet:
   - MAC 00:1A:79:AA:BB:CC → Cooldown (5 Min)
   - Versuche MAC 00:1A:79:DD:EE:FF → Erfolg ✓
4. Stream läuft weiter mit neuer MAC
```

### Beispiel 2: XtreamCodes Account mit Profilen

```
Ausgangssituation:
- Channel: "ProSieben"
- Account: XtreamCodes mit 2 Profilen
- Aktives Profil: "Hauptprofil"

Ablauf:
1. Stream startet mit "Hauptprofil" ✓
2. Server gibt 403 Forbidden zurück
3. Profile Failover startet:
   - "Hauptprofil" → Cooldown (3 Min)
   - Versuche "Backup-Profil" → Erfolg ✓
4. Stream läuft weiter mit neuem Profil
```

### Beispiel 3: Vollständiger Failover über alle Ebenen

```
Ausgangssituation:
- Channel: "Das Erste HD"
- Stream 1: MAC Portal (2 MACs)
- Stream 2: XtreamCodes (1 Profil)
- Stream 3: Standard M3U

Ablauf:
1. Stream 1 startet mit MAC 1 ✓
2. Verbindung bricht ab
3. MAC Failover:
   - MAC 1 → Cooldown
   - Versuche MAC 2 → Fehlgeschlagen (Portal down)
   - MAC 2 → Cooldown
   - Keine MACs mehr verfügbar
4. Stream Failover zu Stream 2:
   - XtreamCodes Profil → Fehlgeschlagen (Server überlastet)
   - Profil → Cooldown
   - Keine Profile mehr verfügbar
5. Stream Failover zu Stream 3:
   - Standard M3U → Erfolg ✓
6. Channel läuft mit Stream 3
```

## Konfiguration

### MAC Portal Settings (UI: MAC Portal → Settings)

#### Cooldowns Tab
| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| `mac_cooldown_failure` | Cooldown nach MAC-Fehler | 5 Min |
| `mac_cooldown_block` | Cooldown nach MAC-Block | 30 Min |
| `portal_cooldown_error` | Cooldown nach Portal-Fehler | 3 Min |

#### Failover Tab
| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| `mac_failover_enabled` | MAC Failover aktivieren | Ja |
| `stream_failover_enabled` | Stream Failover aktivieren | Ja |
| `mac_max_attempts` | Max. MAC-Versuche | 3 |
| `stream_max_retries` | Max. Stream-Versuche | 3 |

### Code-Dateien

| Datei | Beschreibung |
|-------|--------------|
| `apps/proxy/ts_proxy/stream_manager.py` | Hauptlogik für Stream-Management und Failover-Auslösung |
| `apps/proxy/ts_proxy/failover_utils.py` | Failover-Hilfsfunktionen und FailoverManager-Klasse |
| `apps/m3u/failover_manager.py` | Orchestrierung der Failover-Strategien |
| `apps/m3u/mac_rotation_manager.py` | MAC-Rotation und -Auswahl |
| `apps/m3u/mac_portal_models.py` | Datenbank-Modelle für Failover-Settings |

## Redis Keys

Das Failover-System verwendet Redis für Status-Tracking:

| Key | Beschreibung | TTL |
|-----|--------------|-----|
| `mac:{id}:cooldown` | MAC ist in Cooldown | 5-30 Min |
| `mac:{id}:busy` | MAC wird aktiv verwendet | 1 Stunde |
| `profile:{id}:cooldown` | Profil ist in Cooldown | 3 Min |
| `profile:{id}:connections` | Aktive Verbindungen des Profils | 1 Stunde |
| `channel:{id}:current_mac` | Aktuell verwendete MAC für Channel | 1 Stunde |
| `channel:{id}:failover_attempts` | Anzahl Failover-Versuche | 5 Min |

## Wichtige Konzepte

### Cooldown vs. Busy

- **Cooldown**: MAC/Profil ist fehlgeschlagen und darf für X Minuten nicht verwendet werden
- **Busy**: MAC wird aktiv für einen Stream verwendet (verhindert Doppelnutzung)

### Failover-Attempt-Limit

- Maximum 15 Failover-Versuche pro Channel
- Verhindert Endlosschleifen
- Reset nach 5 Minuten oder bei Erfolg

### MAC-Status

| Status | Beschreibung | Health Score |
|--------|--------------|--------------|
| `VALID` | MAC funktioniert | 50-100 (je nach Historie) |
| `UNKNOWN` | Noch nicht getestet | 10 |
| `ERROR` | Temporärer Fehler | 0 |
| `EXPIRED` | Abonnement abgelaufen | 0 |
| `BLOCKED` | MAC wurde gesperrt | 5 |

---

## FailoverManager (apps/m3u/failover_manager.py)

Der `FailoverManager` ist die zentrale Orchestrierungsklasse für alle Failover-Strategien. Er wird pro Account instanziiert und verwaltet die Reihenfolge der Failover-Versuche.

### Failover-Strategien

Der FailoverManager unterstützt 5 verschiedene Strategien, die in konfigurierbarer Reihenfolge ausgeführt werden:

```python
# Standard-Reihenfolge (konfigurierbar in Settings)
failover_priority = ['mac', 'useragent', 'endpoint', 'stream']
```

| Strategie | Beschreibung | Standard |
|-----------|--------------|----------|
| `mac` | Wechselt zur nächsten MAC-Adresse | Aktiviert |
| `useragent` | Wechselt User-Agent (MAG250, MAG254, etc.) | Deaktiviert |
| `endpoint` | Wechselt Portal-Endpoint (/server/load.php, etc.) | Aktiviert |
| `stream` | Wechselt zum Backup-Stream | Aktiviert |
| `portal` | Wechselt zu anderem Portal | Aktiviert |

### execute_with_failover()

Die Hauptmethode des FailoverManagers:

```python
def execute_with_failover(self, operation: Callable, **kwargs) -> Any:
    """
    Führt eine Operation mit allen konfigurierten Failover-Strategien aus.
    
    Ablauf:
    1. Iteriert durch failover_priority Liste
    2. Für jede aktivierte Strategie: Versuche Operation
    3. Bei Erfolg: Return
    4. Bei FailoverExhausted: Nächste Strategie
    5. Alle erschöpft: AllFailoverStrategiesExhausted Exception
    """
```

### Beispiel-Aufruf:

```python
from apps.m3u.failover_manager import FailoverManagerRegistry

# Manager für Account holen
manager = FailoverManagerRegistry.get_or_create(account_id=123)

# Operation mit Failover ausführen
result = manager.execute_with_failover(
    operation=my_stream_function,
    channel_id=456,
    cmd="ffmpeg http://..."
)
```

---

## MACRotationManager (apps/m3u/mac_rotation_manager.py)

Der `MACRotationManager` verwaltet die MAC-Auswahl und -Rotation für einen Account.

### MAC-Auswahl-Strategien

```python
class SelectionStrategy:
    ROUND_ROBIN = "round_robin"   # Reihum
    HEALTH_BASED = "health_based" # Nach Health Score (Standard)
    RANDOM = "random"             # Zufällig
```

### get_next_mac() - MAC-Auswahl

```python
def get_next_mac(self) -> Optional[object]:
    """
    Wählt die nächste verfügbare MAC aus.
    
    Ablauf:
    1. Hole alle MACs für diesen Account
    2. Filtere aus:
       - MACs in Cooldown
       - MACs mit Status 'expired', 'error', 'blocked'
    3. Wähle nach Strategie:
       - HEALTH_BASED: MAC mit höchstem Health Score
       - ROUND_ROBIN: Nächste MAC in der Liste
       - RANDOM: Zufällige MAC
    """
```

### report_failure() - Fehler melden

```python
def report_failure(self, mac, error_type: str = "failure", error_message: str = ""):
    """
    Meldet einen MAC-Fehler und setzt Cooldown.
    
    Error Types und Cooldowns:
    - 'block', 'device_conflict' → mac_cooldown_block (30 Min)
    - 'rate_limit' → mac_cooldown_failure (5 Min)
    - 'expired' → Kein Cooldown, Status auf 'expired'
    - Andere → mac_cooldown_failure (5 Min)
    """
```

### report_success() - Erfolg melden

```python
def report_success(self, mac, response_time_ms: int = None, endpoint_used: str = ""):
    """
    Meldet erfolgreiche MAC-Nutzung.
    
    Aktionen:
    1. MACHealthRecord.record_success() aufrufen
    2. MAC-Status auf 'valid' setzen
    3. last_checked aktualisieren
    """
```

---

## MAC Health System

### MACHealthRecord (apps/m3u/mac_portal_models.py)

Speichert die Historie aller MAC-Operationen für Health-Score-Berechnung.

```python
class EventType(models.TextChoices):
    SUCCESS = "success"    # Erfolgreiche Operation
    FAILURE = "failure"    # Fehlgeschlagene Operation
    COOLDOWN = "cooldown"  # In Cooldown gesetzt
    BLOCK = "block"        # MAC wurde blockiert
    RECOVERY = "recovery"  # Aus Cooldown erholt
    EXPIRED = "expired"    # Abonnement abgelaufen
```

### Health Score Berechnung

```python
@classmethod
def get_health_score(cls, mac, hours=24):
    """
    Berechnet Health Score basierend auf:
    1. MAC-Status (Priorität)
    2. Erfolgs-/Fehler-Verhältnis der letzten 24h
    
    Status-basierte Scores:
    - 'error', 'expired' → 0
    - 'blocked' → 5
    - 'unknown' → 10
    - 'valid' ohne Historie → 50
    
    Historie-basierte Berechnung:
    score = (success_count / total_events) * 100
    """
```

### Beispiel Health Score Berechnung:

```
MAC: 00:1A:79:AA:BB:CC
Status: valid
Letzte 24h: 45 Erfolge, 5 Fehler

Health Score = (45 / 50) * 100 = 90%
```

---

## MACCooldown (apps/m3u/mac_portal_models.py)

Verwaltet temporäre Sperren für MACs nach Fehlern.

### Cooldown-Gründe

```python
class CooldownReason(models.TextChoices):
    FAILURE = "failure"        # Allgemeiner Fehler
    BLOCK = "block"            # MAC blockiert
    RATE_LIMIT = "rate_limit"  # Rate Limit erreicht
    DEVICE_CONFLICT = "device_conflict"  # Gerätekonflikt
    MANUAL = "manual"          # Manuell gesetzt
```

### Cooldown-Dauern (konfigurierbar)

| Grund | Standard-Dauer | Einstellung |
|-------|----------------|-------------|
| Failure | 5 Minuten | `mac_cooldown_failure` |
| Block | 30 Minuten | `mac_cooldown_block` |
| Rate Limit | 5 Minuten | `mac_cooldown_failure` |
| Device Conflict | 30 Minuten | `mac_cooldown_block` |

### Cooldown-Prüfung

```python
@classmethod
def is_mac_in_cooldown(cls, mac) -> bool:
    """Prüft ob MAC aktuell in Cooldown ist."""
    return cls.objects.filter(
        mac=mac,
        is_active=True,
        expires_at__gt=timezone.now()
    ).exists()
```

---

## FailoverEvent (apps/m3u/mac_portal_models.py)

Protokolliert alle Failover-Ereignisse für Statistiken und Debugging.

### Event-Typen

```python
class FailoverType(models.TextChoices):
    MAC = "mac"            # MAC-Wechsel
    PORTAL = "portal"      # Portal-Wechsel
    STREAM = "stream"      # Stream-Wechsel
    USERAGENT = "useragent"  # User-Agent-Wechsel
    ENDPOINT = "endpoint"  # Endpoint-Wechsel
```

### Gespeicherte Daten

| Feld | Beschreibung |
|------|--------------|
| `m3u_account` | Betroffener Account |
| `timestamp` | Zeitpunkt des Failovers |
| `failover_type` | Art des Failovers |
| `original_value` | Ursprünglicher Wert (z.B. alte MAC) |
| `new_value` | Neuer Wert (z.B. neue MAC) |
| `reason` | Grund für Failover |
| `success` | Ob Failover erfolgreich war |
| `duration_ms` | Dauer in Millisekunden |

### Statistik-Abfrage

```python
# Failover-Statistiken der letzten 7 Tage
stats = FailoverEvent.get_statistics(account, days=7)
# Returns: total, success_count, by_type (mit count und avg_duration)
```

## Technische Details: Die Failover-Funktionen im StreamManager

### `_try_next_mac()` - MAC Failover im StreamManager

**Datei:** `apps/proxy/ts_proxy/stream_manager.py` (Zeile ~1921)

Diese Funktion wird aufgerufen, wenn ein laufender Stream fehlschlägt und versucht, eine andere MAC-Adresse zu verwenden.

**Ablauf:**
```
_try_next_mac() aufgerufen
        │
        ▼
┌───────────────────────────────┐
│ 1. Prüfe: MAC Failover        │
│    aktiviert in Settings?     │
│    (FailoverSettings.         │
│     mac_failover_enabled)     │
└───────────┬───────────────────┘
            │ Ja
            ▼
┌───────────────────────────────┐
│ 2. Hole aktuelle Stream-ID    │
│    und M3U-Profil aus Redis   │
│    (channel:{id}:metadata)    │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 3. _mark_current_mac_failed() │
│    - Busy-Flag löschen        │
│    - Cooldown setzen          │
│    - MAC-ID speichern         │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 4. get_stream_info_for_profile│
│    → FailoverManager          │
│    → MACRotationManager       │
│    → Nächste verfügbare MAC   │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 5. Neue URL erhalten?         │
│    Ja → URL aktualisieren     │
│    Nein → return False        │
└───────────────────────────────┘
```

**Code-Auszug:**
```python
def _try_next_mac(self) -> bool:
    # 1. Check if MAC failover is enabled
    from apps.m3u.mac_portal_models import FailoverSettings
    settings = FailoverSettings.get_settings()
    if not settings.mac_failover_enabled:
        return False
    
    # 2. Get current M3U profile from Redis metadata
    metadata_key = RedisKeys.channel_metadata(self.channel_id)
    md = redis_client.hgetall(metadata_key)
    m3u_profile_id = int(md[ChannelMetadataField.M3U_PROFILE])
    
    # 3. Mark current MAC as failed (sets cooldown)
    self._mark_current_mac_failed()
    
    # 4. Get new URL with different MAC
    from .url_utils import get_stream_info_for_profile
    info = get_stream_info_for_profile(
        self.channel_id, 
        self.current_stream_id, 
        m3u_profile_id
    )
    
    # 5. Update URL if successful
    if info and info.get("url"):
        self.update_url(info["url"], info["stream_id"], info["m3u_profile_id"])
        return True
    return False
```

### `_mark_current_mac_failed()` - MAC als fehlgeschlagen markieren

**Datei:** `apps/proxy/ts_proxy/stream_manager.py` (Zeile ~2040)

Diese Hilfsfunktion wird von `_try_next_mac()` aufgerufen, bevor eine neue MAC angefordert wird.

**Was sie macht:**
1. Extrahiert MAC-Adresse aus aktueller URL
2. Findet das zugehörige `M3UAccountMac` Objekt
3. Löscht das "Busy"-Flag in Redis (MAC streamt nicht mehr)
4. Setzt Cooldown in Redis (MAC wird für X Minuten nicht verwendet)
5. Speichert MAC-ID für Channel (damit FailoverManager sie überspringt)

**Code-Auszug:**
```python
def _mark_current_mac_failed(self):
    # Extract MAC from URL
    mac_address = self._extract_mac_from_url(self.url)
    mac_entry = self._get_mac_entry_from_address(mac_address)
    
    # Clear busy flag (MAC is no longer streaming)
    busy_key = RedisKeys.mac_busy(mac_entry.id)
    redis_client.delete(busy_key)
    
    # Get cooldown duration from settings
    from apps.m3u.mac_portal_models import MACPortalGlobalSettings
    settings = MACPortalGlobalSettings.get_settings()
    cooldown_duration = settings.mac_cooldown_failure * 60  # In Sekunden
    
    # Set cooldown in Redis
    cooldown_key = RedisKeys.mac_cooldown(mac_entry.id)
    redis_client.setex(cooldown_key, cooldown_duration, "1")
    
    # Store current MAC for channel (so FailoverManager skips it)
    mac_key = f"channel:{self.channel_id}:current_mac"
    redis_client.setex(mac_key, 3600, str(mac_entry.id))
    
    logger.info(f"MAC {mac_address} set to COOLDOWN for {cooldown_duration}s")
```

### `_try_profile_failover()` - Profil Failover

**Datei:** `apps/proxy/ts_proxy/stream_manager.py`

Versucht ein anderes Profil im selben Account zu verwenden (nur für XtreamCodes).

### `_try_next_stream()` - Stream Failover

**Datei:** `apps/proxy/ts_proxy/stream_manager.py` (Zeile ~2085)

Wechselt zum nächsten Backup-Stream wenn MAC und Profil Failover erschöpft sind.

**Ablauf:**
```
_try_next_stream() aufgerufen
        │
        ▼
┌───────────────────────────────┐
│ 1. Broadcast: Failover        │
│    gestartet (WebSocket)      │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 2. get_next_failover_stream() │
│    aus failover_utils.py      │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 3. Für jeden alternativen     │
│    Stream:                    │
│    - MAC Account?             │
│      → _try_mac_account_failover│
│    - XC Account?              │
│      → _try_standard_account_failover│
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 4. Erfolg?                    │
│    Ja → URL aktualisieren     │
│         Broadcast: Erfolg     │
│    Nein → Broadcast: Fehler   │
└───────────────────────────────┘
```

## Aufruf-Hierarchie im Code

```
StreamManager.run()
    │
    │ Stream fehlgeschlagen
    ▼
┌─────────────────────────────────────────────────────────┐
│ if url_failed and self.running:                         │
│     # 1. Versuche MAC Failover                          │
│     mac_switched = self._try_next_mac()                 │
│     if mac_switched:                                    │
│         continue  # Stream läuft mit neuer MAC          │
│                                                         │
│     # 2. Versuche Profile Failover                      │
│     profile_switched = self._try_profile_failover()     │
│     if profile_switched:                                │
│         continue  # Stream läuft mit neuem Profil       │
│                                                         │
│     # 3. Versuche Stream Failover                       │
│     switch_result = self._try_next_stream()             │
│     if switch_result:                                   │
│         continue  # Stream läuft mit Backup-Stream      │
│     else:                                               │
│         break  # Alle Optionen erschöpft                │
└─────────────────────────────────────────────────────────┘
```

## Komponenten-Zusammenhänge

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           StreamManager                                  │
│                    (apps/proxy/ts_proxy/stream_manager.py)              │
│                                                                          │
│  _try_next_mac() ──────────────────────────────────────────────────┐    │
│       │                                                             │    │
│       ├── _mark_current_mac_failed()                                │    │
│       │       │                                                     │    │
│       │       ├── Redis: mac:{id}:busy → DELETE                     │    │
│       │       ├── Redis: mac:{id}:cooldown → SETEX                  │    │
│       │       └── Redis: channel:{id}:current_mac → SETEX           │    │
│       │                                                             │    │
│       └── get_stream_info_for_profile() ────────────────────────────┼───┘
│               │                                                     │
└───────────────┼─────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FailoverManager                                │
│                    (apps/m3u/failover_manager.py)                       │
│                                                                          │
│  execute_with_failover()                                                 │
│       │                                                                  │
│       ├── _mac_failover() ──────────────────────────────────────────┐   │
│       │       │                                                      │   │
│       │       └── MACRotationManager.get_next_mac() ─────────────────┼───┘
│       │                                                              │
│       ├── _useragent_failover()                                      │
│       ├── _endpoint_failover()                                       │
│       └── _stream_failover()                                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MACRotationManager                                │
│                    (apps/m3u/mac_rotation_manager.py)                   │
│                                                                          │
│  get_next_mac()                                                          │
│       │                                                                  │
│       ├── _get_all_macs() → M3UAccountMac.objects.filter(account=...)   │
│       │                                                                  │
│       ├── Filter: _is_in_cooldown() → MACCooldown.is_mac_in_cooldown()  │
│       │                                                                  │
│       ├── Filter: status not in ['expired', 'error', 'blocked']         │
│       │                                                                  │
│       └── Select by Strategy:                                            │
│           ├── HEALTH_BASED → _select_health_based()                     │
│           │       └── MACHealthRecord.get_health_score()                │
│           ├── ROUND_ROBIN → _select_round_robin()                       │
│           └── RANDOM → _select_random()                                 │
│                                                                          │
│  report_failure(mac, error_type)                                         │
│       │                                                                  │
│       ├── MACHealthRecord.record_failure()                              │
│       └── MACCooldown.apply_cooldown()                                  │
│                                                                          │
│  report_success(mac)                                                     │
│       │                                                                  │
│       ├── MACHealthRecord.record_success()                              │
│       └── mac.status = 'valid'                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Datenbank-Modelle                                │
│                    (apps/m3u/mac_portal_models.py)                      │
│                                                                          │
│  MACHealthRecord                                                         │
│       ├── event_type: SUCCESS, FAILURE, COOLDOWN, BLOCK, RECOVERY       │
│       ├── response_time_ms, http_status, error_message                  │
│       └── get_health_score() → 0-100 basierend auf Historie             │
│                                                                          │
│  MACCooldown                                                             │
│       ├── reason: FAILURE, BLOCK, RATE_LIMIT, DEVICE_CONFLICT           │
│       ├── expires_at: Wann Cooldown endet                               │
│       └── is_mac_in_cooldown() → True/False                             │
│                                                                          │
│  FailoverEvent                                                           │
│       ├── failover_type: MAC, PORTAL, STREAM, USERAGENT, ENDPOINT       │
│       ├── original_value, new_value, reason, success                    │
│       └── get_statistics() → Statistiken für UI                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Stream wechselt ständig
- Prüfe ob genug MACs/Profile verfügbar sind
- Erhöhe Cooldown-Zeiten
- Prüfe Portal-Stabilität

### Kein Failover trotz Fehler
- Prüfe ob Failover aktiviert ist (Settings)
- Prüfe ob alternative MACs/Streams vorhanden sind
- Prüfe Redis-Verbindung

### Alle MACs in Cooldown
- Warte bis Cooldown abläuft
- Oder: Cooldown manuell zurücksetzen (MAC Portal → MACs → Reset Cooldown)

### Logs zur Diagnose

Suche in den Logs nach:
```
# MAC Failover gestartet
"Trying MAC failover within current stream"

# MAC erfolgreich gewechselt
"MAC failover successful for channel"

# MAC in Cooldown gesetzt
"MAC ... set to COOLDOWN for"

# Alle MACs erschöpft
"MAC failover exhausted for channel"

# Stream Failover
"Trying backup MAC stream"
"Successfully switched to new URL"
```
