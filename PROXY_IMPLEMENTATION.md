# Proxy-Feld Implementierung für alle Account-Typen

## Übersicht
Diese Implementierung erweitert das bestehende Proxy-Feld von MAC-Accounts auf alle Account-Typen (Standard, Xtream Codes, MAC/STB-Portal) und integriert automatische Proxy-Unterstützung in FFmpeg-Befehle.

## Änderungen

### 1. Frontend (M3U.jsx)
- **Proxy-Feld für alle Account-Typen**: Das Proxy-Feld ist jetzt für alle Account-Typen verfügbar, nicht nur für MAC-Accounts
- **Vereinfachte Proxy-Eingabe**: Für Nicht-MAC-Accounts wird nur ein einzelner Proxy unterstützt (Multi-Proxy bleibt MAC-spezifisch)
- **Automatische Speicherung**: Das Proxy-Feld wird in `custom_properties.proxy` für alle Account-Typen gespeichert

### 2. Backend - StreamProfile (core/models.py)
- **Erweiterte build_command Methode**: Neue Parameter `proxy` hinzugefügt
- **Automatische FFmpeg-Proxy-Integration**: Wenn ein Proxy angegeben ist und FFmpeg verwendet wird, wird automatisch der `-http_proxy` Parameter hinzugefügt
- **Intelligente Parameter-Platzierung**: Der Proxy-Parameter wird vor dem `-i` Parameter eingefügt für optimale Kompatibilität

### 3. Backend - StreamManager (stream_manager.py)
- **Automatische Proxy-Erkennung**: Der StreamManager holt automatisch das Proxy-Feld aus dem M3U-Account
- **Proxy-Weiterleitung**: Das Proxy-Feld wird an die `build_command` Methode weitergegeben
- **Fehlerbehandlung**: Robuste Fehlerbehandlung falls das Proxy-Feld nicht verfügbar ist

## Funktionsweise

### Proxy-Konfiguration
1. Benutzer gibt Proxy im Format `http://proxy:port` in das Proxy-Feld ein
2. Das Feld wird in `custom_properties.proxy` gespeichert
3. Beim Stream-Start wird das Proxy-Feld automatisch abgerufen

### FFmpeg-Integration
1. Wenn ein Stream startet und FFmpeg verwendet wird:
   - StreamManager holt das Proxy-Feld aus dem M3U-Account
   - `build_command` wird mit dem Proxy-Parameter aufgerufen
   - FFmpeg-Befehl wird automatisch um `-http_proxy <proxy_url>` erweitert

### Beispiel FFmpeg-Befehl
**Ohne Proxy:**
```bash
ffmpeg -user_agent "Mozilla/5.0..." -i "http://stream.url" -c copy -f mpegts pipe:1
```

**Mit Proxy:**
```bash
ffmpeg -user_agent "Mozilla/5.0..." -http_proxy "http://proxy:port" -i "http://stream.url" -c copy -f mpegts pipe:1
```

## Kompatibilität
- **Rückwärtskompatibel**: Bestehende MAC-Accounts mit Multi-Proxy-Konfiguration funktionieren weiterhin
- **Keine Datenbank-Änderungen**: Verwendet bestehende `custom_properties` Struktur
- **Automatische Aktivierung**: Streams ohne Proxy-Konfiguration funktionieren unverändert

## Verwendung
1. M3U-Account bearbeiten
2. Proxy-URL im Format `http://proxy:port` eingeben
3. Account speichern
4. Streams verwenden automatisch den konfigurierten Proxy

## Hinweise
- Das Proxy-Feld ist optional - wenn leer, startet der Stream ohne Proxy
- Multi-Proxy-Funktionalität bleibt MAC-Accounts vorbehalten
- Proxy wird nur bei FFmpeg-basierten Streams verwendet
- Unterstützt HTTP-Proxies (HTTPS-Proxies können je nach FFmpeg-Version funktionieren)