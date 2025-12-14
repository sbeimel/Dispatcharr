# MAC Portal Import Plugin

Importiert Stalker/STB Portal-Daten in Dispatcharr mit automatischer Profil-Erstellung für MAC-Failover.

## Features

- **MAC-Normalisierung**: Verschiedene Eingabeformate werden automatisch normalisiert
- **MAC-Validierung**: Prüft alle MACs gegen das Portal (Token + Expiry)
- **Kanal-Abruf**: Holt alle Kanäle mit Gruppen/Genres
- **M3U-Generierung**: Erstellt M3U-Playlist mit allen Metadaten
- **Automatische Profile**: Erstellt Profile für MAC-Failover

## Installation

### Option 1: Plugin-Verzeichnis

1. Kopiere den `mac_portal_import` Ordner nach `/data/plugins/`
2. Starte Dispatcharr neu oder lade Plugins neu

### Option 2: ZIP-Datei

1. Entpacke `mac_portal_import.zip` nach `/data/plugins/`
2. Starte Dispatcharr neu

## Konfiguration

| Feld | Beschreibung |
|------|--------------|
| Portal Name | Name für den M3U-Account |
| Portal URL | URL des Stalker/STB Portals |
| MAC-Adressen | Eine oder mehrere MACs (Leerzeichen/Komma/Zeilenumbruch getrennt) |
| Proxy | Optional: HTTP-Proxy |

## Aktionen

### MACs normalisieren
Normalisiert MAC-Adressen zu einer pro Zeile (uppercase, mit Doppelpunkten).

**Eingabe-Formate:**
- `00:1a:79:19:1F:A9 00:1a:79:19:1F:B9` (Leerzeichen)
- `00:1a:79:19:1F:A9,00:1a:79:19:1F:B9` (Komma)
- `00:1a:79:19:1F:A9, 00:1a:79:19:1F:B9` (Komma + Leerzeichen)
- Gemischte Formate

### MACs validieren
Prüft alle MAC-Adressen gegen das Portal:
- Token-Abruf
- Ablaufdatum-Check
- Markiert abgelaufene/ungültige MACs

### Kanäle abrufen
Ruft alle verfügbaren Kanäle vom Portal ab:
- Kanal-Name, Nummer, Logo
- Gruppen/Genres
- Stream-URLs

### Portal importieren
Vollständiger Import:
1. MACs validieren
2. Kanäle abrufen
3. M3U-Datei generieren
4. M3U-Account erstellen
5. Profile für jede gültige MAC erstellen

## Profil-Failover

Für jede gültige MAC wird ein Profil erstellt:

| Profil | search_pattern | replace_pattern | max_connections |
|--------|----------------|-----------------|-----------------|
| Portal MAC 1 | erste MAC | erste MAC | 1 |
| Portal MAC 2 | erste MAC | zweite MAC | 1 |
| Portal MAC 3 | erste MAC | dritte MAC | 1 |

Das ermöglicht automatisches Failover zwischen MACs über das Dispatcharr Profil-System.

## Beispiel

**Eingabe:**
```
Portal Name: MeinPortal
Portal URL: http://example.com/stalker_portal/
MAC-Adressen: 00:1A:79:11:11:11 00:1A:79:22:22:22, 00:1A:79:33:33:33
```

**Ergebnis:**
- M3U-Account: "MeinPortal (MAC Import)"
- 3 Profile mit Failover-Konfiguration
- Alle Kanäle als unzugeordnete Streams

## Streams zuordnen

Nach dem Import erscheinen die Streams NICHT automatisch bei den Channels.
Du musst sie manuell zuordnen:

1. Gehe zu M3U Sources
2. Wähle den importierten Account
3. Ordne Streams den gewünschten Channels zu

## Anforderungen

- Dispatcharr 0.14.0+
- Python 3.8+
- requests

## Lizenz

MIT
