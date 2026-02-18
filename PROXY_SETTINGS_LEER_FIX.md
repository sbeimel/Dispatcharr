# 🔧 FIX: Proxy Settings Felder sind leer

## Problem

Die neuen Proxy Settings Felder im Frontend sind leer:
- Max Retries
- URL Switch Timeout
- Max Stream Switches
- Connection Timeout
- Failover Grace Period

## Ursache

Die `CoreSettings.get_proxy_settings()` Methode in `core/models.py` enthält **nicht die neuen Felder** in den Default-Werten.

**Aktueller Code (FALSCH):**
```python
@classmethod
def get_proxy_settings(cls):
    """Get proxy settings."""
    return cls._get_group(PROXY_SETTINGS_KEY, {
        "buffering_timeout": 15,
        "buffering_speed": 1.0,
        "redis_chunk_ttl": 60,
        "channel_shutdown_delay": 0,
        "channel_init_grace_period": 5,
        # FEHLEN: Die 5 neuen Felder!
    })
```

## Lösung

Die Datei `core/models.py` wurde bereits korrigiert:

**Neuer Code (KORREKT):**
```python
@classmethod
def get_proxy_settings(cls):
    """Get proxy settings."""
    return cls._get_group(PROXY_SETTINGS_KEY, {
        "buffering_timeout": 15,
        "buffering_speed": 1.0,
        "redis_chunk_ttl": 60,
        "channel_shutdown_delay": 0,
        "channel_init_grace_period": 5,
        "max_retries": 2,                    # NEU
        "url_switch_timeout": 20,            # NEU
        "max_stream_switches": 200,          # NEU
        "connection_timeout": 10,            # NEU
        "failover_grace_period": 20,         # NEU
    })
```

## Anwendung

### Option 1: Docker Image neu bauen (EMPFOHLEN)

```bash
cd ~/Dispatcharr

# Docker Image neu bauen
docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile .

# Container neu starten
cd docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml up -d
```

### Option 2: Patch anwenden (wenn Container läuft)

```bash
cd ~/Dispatcharr

# Patch anwenden
patch -p1 < core_models_proxy_settings_fix.patch

# Container neu starten (damit Python-Code neu geladen wird)
cd docker
docker compose -f docker-compose.aio.yml restart
```

## Verifikation

Nach dem Neustart:

1. **Frontend öffnen:** http://dispatcharr:8000/settings/proxy
2. **Felder prüfen:** Alle 5 neuen Felder sollten jetzt Werte haben:
   - Max Retries: **2**
   - URL Switch Timeout: **20**
   - Max Stream Switches: **200**
   - Connection Timeout: **10**
   - Failover Grace Period: **20**

3. **Werte ändern und speichern**
4. **Seite neu laden** → Werte sollten gespeichert bleiben

## Warum waren die Felder leer?

Das Frontend ruft die API auf:
```
GET /api/settings/proxy/
```

Die API gibt zurück, was `CoreSettings.get_proxy_settings()` liefert.

Wenn die neuen Felder nicht in den Defaults sind, gibt die API `null` oder `undefined` zurück, und das Frontend zeigt leere Felder.

**Mit dem Fix:**
- API gibt Default-Werte zurück
- Frontend zeigt die Werte an
- User kann Werte ändern und speichern
- Backend nutzt die gespeicherten Werte

---

## Zusätzliche Prüfung: API-Endpoint

Du kannst auch direkt die API prüfen:

```bash
# API-Aufruf (ersetze TOKEN mit deinem Auth-Token)
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/settings/proxy/
```

**Erwartete Antwort:**
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

---

**Status:** ✅ BEHOBEN

Die Datei `core/models.py` wurde korrigiert. Nach dem Neustart sollten alle Felder Werte haben.
