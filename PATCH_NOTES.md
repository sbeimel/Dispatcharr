# Dispatcharr 0.15.0 Patch Notes

## Änderungen gegenüber Original 0.15.0

---

### 1. Profil-Failover Logik (NEU)

**Problem:** Bei Stream-Failover wurde nur zum nächsten Stream gewechselt, nicht zu anderen Profilen desselben Streams.

**Lösung:** Erweitertes Failover das alle Profile eines Streams durchprobiert bevor zum nächsten Stream gewechselt wird.

**Geänderte Dateien:**
- `apps/proxy/ts_proxy/url_utils.py` - `get_alternate_streams()` gibt jetzt alle Stream/Profil-Kombinationen zurück
- `apps/proxy/ts_proxy/stream_manager.py` - Tracking von `tried_combinations` statt `tried_stream_ids`

**Failover-Reihenfolge jetzt:**
1. Stream 1, Profil A (Default)
2. Stream 1, Profil B
3. Stream 2, Profil A
4. Stream 2, Profil B
5. ...

---

### 2. Basic Auth für /output/m3u und /output/epg (NEU)

**Problem:** M3U und EPG Endpunkte waren ohne Authentifizierung erreichbar.

**Lösung:** HTTP Basic Authentication gegen Django User-Datenbank.

**Geänderte Dateien:**
- `apps/output/views.py` - Neue Funktionen `get_basic_auth_user()` und `require_basic_auth()`

**Nutzung:**
```bash
curl -u username:password http://localhost:9191/output/m3u
```

Oder in URL (für IPTV-Clients):
```
http://username:password@localhost:9191/output/m3u
```

---

### 3. HTTP Proxy Support für FFmpeg (NEU)

**Problem:** Kein Proxy-Support für FFmpeg-Streams.

**Lösung:** Neues `proxy` Feld im M3U Account Model, wird als `-http_proxy` Parameter an FFmpeg übergeben.

**Geänderte Dateien:**
- `apps/m3u/models.py` - Neues Feld `proxy`
- `apps/m3u/serializers.py` - Feld zur API hinzugefügt
- `core/models.py` - `build_command()` akzeptiert `proxy` Parameter
- `apps/proxy/ts_proxy/stream_manager.py` - Holt Proxy vom M3U Account
- `apps/m3u/migrations/0019_m3uaccount_proxy.py` - Migration

**Nutzung im Web-UI:**
- Bei M3U Account → Proxy Feld ausfüllen (z.B. `http://proxy:8080`)

---

### 4. Retry/Timeout Werte angepasst (FIX)

**Problem:** Werte wichen von 0.12.0-06 ab.

**Geänderte Datei:** `apps/proxy/config.py`

| Einstellung | Vorher | Nachher |
|-------------|--------|---------|
| `MAX_RETRIES` | 3 | **2** |
| `URL_SWITCH_TIMEOUT` | 20s | **4s** |

---

### 5. Docker Entrypoint Permission Fix (FIX)

**Problem:** `permission denied` beim Container-Start unter Windows.

**Lösung:** `chmod +x` im Dockerfile hinzugefügt.

**Geänderte Datei:** `docker/Dockerfile`
```dockerfile
# Copy application code
COPY . /app
# Ensure entrypoint script is executable
RUN chmod +x /app/docker/entrypoint.sh /app/docker/init/*.sh
```

---

## Zusammenfassung der geänderten Dateien

```
apps/m3u/models.py                              # Proxy Feld
apps/m3u/serializers.py                         # Proxy in API
apps/m3u/migrations/0019_m3uaccount_proxy.py    # Migration (NEU)
apps/output/views.py                            # Basic Auth
apps/proxy/config.py                            # Retry/Timeout Werte
apps/proxy/ts_proxy/url_utils.py                # Profil-Failover
apps/proxy/ts_proxy/stream_manager.py           # Profil-Failover + Proxy
apps/proxy/ts_proxy/views.py                    # tried_combinations Reset
core/models.py                                  # build_command mit Proxy
docker/Dockerfile                               # chmod +x Fix
```

---

## Installation

1. Bestehende Installation stoppen
2. Dateien ersetzen
3. Migration ausführen: `python manage.py migrate`
4. Neu starten
