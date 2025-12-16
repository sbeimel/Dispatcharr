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

| Status | Beschreibung |
|--------|--------------|
| `VALID` | MAC funktioniert |
| `ERROR` | Temporärer Fehler |
| `EXPIRED` | Abonnement abgelaufen |
| `BLOCKED` | MAC wurde gesperrt |

## Technische Details: Die Failover-Funktionen

### `_try_next_mac()` - MAC Failover im StreamManager

**Datei:** `apps/proxy/ts_proxy/stream_manager.py`

Diese Funktion wird aufgerufen, wenn ein laufender Stream fehlschlägt und versucht, eine andere MAC-Adresse zu verwenden.

**Ablauf:**
```
_try_next_mac() aufgerufen
        │
        ▼
┌───────────────────────────────┐
│ 1. Prüfe: MAC Failover        │
│    aktiviert in Settings?     │
└───────────┬───────────────────┘
            │ Ja
            ▼
┌───────────────────────────────┐
│ 2. Hole aktuelle Stream-ID    │
│    und M3U-Profil aus Redis   │
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

**Was `_mark_current_mac_failed()` macht:**
1. Extrahiert MAC-Adresse aus aktueller URL
2. Löscht das "Busy"-Flag (MAC streamt nicht mehr)
3. Setzt Cooldown (MAC wird für X Minuten nicht verwendet)
4. Speichert MAC-ID damit FailoverManager sie überspringt

### `_try_profile_failover()` - Profil Failover

**Datei:** `apps/proxy/ts_proxy/stream_manager.py`

Versucht ein anderes Profil im selben Account zu verwenden (nur für XtreamCodes).

### `_try_next_stream()` - Stream Failover

**Datei:** `apps/proxy/ts_proxy/stream_manager.py`

Wechselt zum nächsten Backup-Stream wenn MAC und Profil Failover erschöpft sind.

**Ablauf:**
```
_try_next_stream() aufgerufen
        │
        ▼
┌───────────────────────────────┐
│ 1. Hole alle Streams für      │
│    diesen Channel             │
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 2. Für jeden Stream:          │
│    - Ist MAC Account?         │
│      → _try_mac_account_failover│
│    - Ist XC Account?          │
│      → _try_standard_account_failover│
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────┐
│ 3. Erfolg? → URL aktualisieren│
│    Fehlschlag? → Nächster Stream│
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
