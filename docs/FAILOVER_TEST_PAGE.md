# Failover Test Page - Benutzeranleitung

## Übersicht

Die Failover Test Page ermöglicht das Testen der Failover-Mechanismen von Dispatcharr in einer isolierten Umgebung. Du kannst Test-Channels erstellen, Stream-Unterbrechungen simulieren und die Failover-Events in Echtzeit beobachten.

## Zugriff

Die Seite ist unter `/failover-test` erreichbar und erscheint im Sidebar-Menü als "Failover Test" (nur für Admin-Benutzer).

## Funktionen

### 1. Test-Channels erstellen

Klicke auf "New Test Channel" um einen neuen Test-Channel anzulegen:

- **Channel Name**: Eindeutiger Name für den Test-Channel
- **Primary Stream URL**: Haupt-Stream-URL
- **Backup Streams**: Zusätzliche Backup-URLs mit Priorität
- **MAC Portal Config** (optional): MAC-Adresse, Portal-URL, Endpoints, User-Agents

### 2. Stream-Unterbrechungen simulieren

Wähle einen Test-Channel aus und nutze den "Stream Simulator":

**Manueller Modus:**
- Klicke auf "Stream unterbrechen" (roter Button)
- Wähle den Fehlertyp aus dem Dropdown:
  - `timeout` - Verbindungs-Timeout
  - `connection_reset` - Verbindung zurückgesetzt
  - `403` - Forbidden
  - `404` - Not Found
  - `500` - Server Error
  - `stream_error` - Allgemeiner Stream-Fehler

**Auto-Modus:**
- Aktiviere "Auto-Simulation"
- Konfiguriere das Intervall (1-60 Sekunden)
- Setze maximale Unterbrechungen (1-100)
- Der Simulator unterbricht automatisch in den konfigurierten Intervallen

### 3. Live-Log beobachten

Der Live-Log zeigt alle Failover-Events in Echtzeit:

- **Grün**: Erfolgreiche Failovers
- **Rot**: Fehlgeschlagene Failovers
- **Blau**: Informations-Events

Jeder Eintrag zeigt:
- Timestamp
- Event-Typ (MAC_ROTATION, PORTAL_FAILOVER, STREAM_SWITCH, etc.)
- Strategie
- Original-Wert → Neuer Wert
- Dauer in Millisekunden

### 4. Statistiken

Die Statistik-Sektion zeigt:
- Gesamtanzahl Tests
- Erfolgreiche Failovers
- Fehlgeschlagene Failovers
- Durchschnittliche Failover-Zeit (ms)
- Aufschlüsselung nach Strategie

### 5. Export

- **Logs exportieren**: JSON-Datei mit allen Log-Einträgen
- **Statistiken exportieren**: CSV-Datei mit Statistiken

## API Endpoints

Die Failover Test API ist unter `/api/m3u/failover-test/` verfügbar:

```
GET    /api/m3u/failover-test/channels/           - Liste aller Test-Channels
POST   /api/m3u/failover-test/channels/           - Neuen Test-Channel erstellen
GET    /api/m3u/failover-test/channels/{id}/      - Test-Channel abrufen
DELETE /api/m3u/failover-test/channels/{id}/      - Test-Channel löschen
GET    /api/m3u/failover-test/channels/available/ - Verfügbare Channels zum Import
POST   /api/m3u/failover-test/channels/import/    - Channel importieren

POST   /api/m3u/failover-test/simulate/interrupt/   - Sofortige Unterbrechung
POST   /api/m3u/failover-test/simulate/auto-start/  - Auto-Simulation starten
POST   /api/m3u/failover-test/simulate/stop/        - Simulation stoppen
GET    /api/m3u/failover-test/simulate/status/      - Simulations-Status

GET    /api/m3u/failover-test/statistics/       - Statistiken abrufen
POST   /api/m3u/failover-test/statistics/reset/ - Statistiken zurücksetzen

GET    /api/m3u/failover-test/logs/             - Log-Einträge abrufen

GET    /api/m3u/failover-test/export/logs/       - Logs als JSON exportieren
GET    /api/m3u/failover-test/export/statistics/ - Statistiken als CSV exportieren

GET    /api/m3u/failover-test/settings/         - Failover-Einstellungen abrufen
```

## WebSocket

Echtzeit-Updates werden über WebSocket geliefert:

```
ws://host/ws/failover-test/
```

Event-Typen:
- `initial_state` - Initialer Zustand beim Verbinden
- `log_entry` - Neuer Log-Eintrag
- `failover_event` - Failover-Event
- `statistics_update` - Statistik-Update
- `simulation_started` - Simulation gestartet
- `simulation_stopped` - Simulation gestoppt
- `simulation_completed` - Simulation abgeschlossen

## Tipps

1. **Isolierte Tests**: Test-Channels beeinflussen nicht die produktiven Channels
2. **MAC-Rotation testen**: Erstelle einen Channel mit mehreren MACs um die Rotation zu testen
3. **Portal-Failover testen**: Konfiguriere mehrere Endpoints um Portal-Failover zu testen
4. **Backup-Streams testen**: Füge mehrere Backup-URLs hinzu um Stream-Failover zu testen
