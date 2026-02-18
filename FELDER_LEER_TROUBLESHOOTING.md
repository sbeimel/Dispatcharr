# 🔧 TROUBLESHOOTING: Proxy Settings Felder sind leer

## Problem

Die 5 neuen Proxy Settings Felder sind im Frontend leer:
- Max Retries
- URL Switch Timeout  
- Max Stream Switches
- Connection Timeout
- Failover Grace Period

## Ursache

Das **Docker-Image** enthält noch die **alte Version** von `core/models.py` ohne die neuen Default-Werte.

## Diagnose

### Schritt 1: Prüfe ob Container die neue Version hat

```bash
cd ~/Dispatcharr/docker

# Prüfe core/models.py im Container
docker exec dispatcharr grep -A 15 "def get_proxy_settings" /app/core/models.py
```

**Erwartete Ausgabe (KORREKT):**
```python
def get_proxy_settings(cls):
    """Get proxy settings."""
    return cls._get_group(PROXY_SETTINGS_KEY, {
        "buffering_timeout": 15,
        "buffering_speed": 1.0,
        "redis_chunk_ttl": 60,
        "channel_shutdown_delay": 0,
        "channel_init_grace_period": 5,
        "max_retries": 2,                    # ← MUSS DA SEIN
        "url_switch_timeout": 20,            # ← MUSS DA SEIN
        "max_stream_switches": 200,          # ← MUSS DA SEIN
        "connection_timeout": 10,            # ← MUSS DA SEIN
        "failover_grace_period": 20,         # ← MUSS DA SEIN
    })
```

**Wenn die 5 neuen Zeilen FEHLEN** → Container hat alte Version!

### Schritt 2: Prüfe API-Antwort

```bash
# API direkt aufrufen (im Container)
docker exec dispatcharr python3 -c "
from core.models import CoreSettings
import json
print(json.dumps(CoreSettings.get_proxy_settings(), indent=2))
"
```

**Erwartete Ausgabe:**
```json
{
  "buffering_timeout": 15,
  "buffering_speed": 1.0,
  "redis_chunk_ttl": 60,
  "channel_shutdown_delay": 0,
  "channel_init_grace_period": 5,
  "max_retries": 2,
  "url_switch_timeout": 20,
  "max_stream_switches": 200,
  "connection_timeout": 10,
  "failover_grace_period": 20
}
```

## Lösung

### Option 1: Docker Image neu bauen (EMPFOHLEN)

```bash
cd ~/Dispatcharr

# Image neu bauen
docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile .

# Container neu starten
cd docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml up -d

# Logs prüfen
docker compose -f docker-compose.aio.yml logs -f
```

### Option 2: Datei direkt im Container ersetzen (TEMPORÄR)

**⚠️ WARNUNG:** Diese Änderung geht beim nächsten Container-Neustart verloren!

```bash
cd ~/Dispatcharr

# Datei in Container kopieren
docker cp core/models.py dispatcharr:/app/core/models.py

# Container neu starten (damit Python-Code neu geladen wird)
cd docker
docker compose -f docker-compose.aio.yml restart

# Warten bis Container bereit ist
sleep 10

# Logs prüfen
docker compose -f docker-compose.aio.yml logs -f
```

### Option 3: Automatisches Diagnose-Script

```bash
cd ~/Dispatcharr
bash diagnose_proxy_settings.sh
```

## Verifikation nach dem Fix

### 1. Frontend prüfen
- Öffne: http://dispatcharr:8000/settings/proxy
- **Alle 5 neuen Felder sollten jetzt Werte haben**
- Ändere einen Wert und speichere
- Lade Seite neu → Wert sollte gespeichert bleiben

### 2. API direkt prüfen
```bash
docker exec dispatcharr python3 -c "
from core.models import CoreSettings
settings = CoreSettings.get_proxy_settings()
print('max_retries:', settings.get('max_retries'))
print('url_switch_timeout:', settings.get('url_switch_timeout'))
print('max_stream_switches:', settings.get('max_stream_switches'))
print('connection_timeout:', settings.get('connection_timeout'))
print('failover_grace_period:', settings.get('failover_grace_period'))
"
```

**Erwartete Ausgabe:**
```
max_retries: 2
url_switch_timeout: 20
max_stream_switches: 200
connection_timeout: 10
failover_grace_period: 20
```

### 3. Browser-Cache leeren
Manchmal cached der Browser die API-Antwort:
- **Chrome/Edge:** Strg+Shift+R (Hard Reload)
- **Firefox:** Strg+F5
- Oder: Browser-Cache komplett leeren

## Häufige Probleme

### Problem 1: "Image wurde neu gebaut, aber Felder sind immer noch leer"

**Lösung:**
```bash
# Prüfe ob das richtige Image verwendet wird
docker images | grep dispatcharr

# Sollte zeigen:
# sbeimel/dispatcharr   0.19.0   <IMAGE_ID>   X minutes ago

# Prüfe welches Image der Container nutzt
docker inspect dispatcharr | grep Image

# Container mit neuem Image starten
cd ~/Dispatcharr/docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml pull  # Falls Image von Registry
docker compose -f docker-compose.aio.yml up -d
```

### Problem 2: "API gibt 401 Unauthorized"

Das ist normal - die Settings-API benötigt Authentifizierung. Prüfe stattdessen direkt im Container (siehe oben).

### Problem 3: "Felder sind leer, aber API gibt Werte zurück"

**Lösung:** Frontend-Problem
```bash
# Browser-Cache leeren
# Oder: Inkognito-Modus testen

# Frontend-Logs prüfen (Browser DevTools → Console)
# Sollte keine Fehler zeigen
```

## Warum passiert das?

Docker baut das Image aus dem Code-Stand zum Build-Zeitpunkt. Wenn du `core/models.py` NACH dem letzten Build geändert hast, enthält das Image noch die alte Version.

**Lösung:** Image neu bauen, damit die Änderungen übernommen werden.

---

## Quick Fix (Copy-Paste)

```bash
cd ~/Dispatcharr
docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile .
cd docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml up -d
```

Dann warte 30 Sekunden und öffne: http://dispatcharr:8000/settings/proxy

**Die Felder sollten jetzt Werte haben!** ✅

---

**Status:** Warte auf Image-Rebuild
