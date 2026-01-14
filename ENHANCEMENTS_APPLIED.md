# Dispatcharr 0.17.0 - Angewendete Enhancements

## ✅ Erfolgreich Angewendet

Alle Features aus den Enhancement-Patches wurden erfolgreich in diese Version von Dispatcharr 0.17.0 integriert.

### 1. **Profile Failover Enhancement**
- ✅ `apps/proxy/ts_proxy/stream_manager.py`
  - Import von `get_stream_info_for_profile` hinzugefügt
  - `current_profile_id` und `tried_combinations` Tracking implementiert
  - Profile-ID aus Redis laden
  - Proxy-Support für FFmpeg mit M3U Account Integration
  
- ✅ `apps/proxy/ts_proxy/url_utils.py`
  - `get_alternate_streams()` erweitert um `current_profile_id` Parameter
  - Profile Failover Logik: Versucht alle Profile eines Streams vor Wechsel zum nächsten Stream
  - Neue Funktion `get_stream_info_for_profile()` für spezifische Stream+Profile Kombinationen

### 2. **HTTP Proxy Support**
- ✅ `apps/m3u/serializers.py`
  - `proxy` Feld zum M3UAccountSerializer hinzugefügt
  
- ✅ `apps/proxy/ts_proxy/stream_manager.py`
  - Automatische Proxy-Erkennung aus M3U Account
  - Proxy wird an FFmpeg via `-http_proxy` Parameter übergeben
  - Funktioniert für alle Transcoding-Profile

### 3. **Configuration Enhancements**
- ✅ `apps/proxy/config.py`
  - `MAX_RETRIES` von 3 auf 2 reduziert
  - Neue Stream Health & Recovery Settings hinzugefügt:
    - `MAX_HEALTH_RECOVERY_ATTEMPTS = 2`
    - `MAX_RECONNECT_ATTEMPTS = 3`
    - `MIN_STABLE_TIME_BEFORE_RECONNECT = 30`
    - `FAILOVER_GRACE_PERIOD = 20`
    - `URL_SWITCH_TIMEOUT = 8`
  - Neue Methoden in `BaseConfig`:
    - `get_max_retries()`
    - `get_url_switch_timeout()`
  - Neue Methoden in `TSConfig`:
    - `get_channel_shutdown_delay()`
    - `get_buffering_timeout()`
    - `get_buffering_speed()`
    - `get_channel_init_grace_period()`
    - `get_failover_grace_period()`
  - Dynamic Properties für alle Settings

### 4. **Basic Authentication Support**
- ✅ `apps/output/views.py`
  - `get_basic_auth_user()` Funktion für HTTP Basic Auth
  - `require_basic_auth()` Funktion für 401 Response
  - Vollständige Base64 Credential Validierung

## 📋 Technische Details

### Geänderte Dateien
1. `apps/proxy/config.py` - Konfigurationserweiterungen
2. `apps/m3u/serializers.py` - Proxy-Feld
3. `apps/proxy/ts_proxy/stream_manager.py` - Profile Failover + Proxy Support
4. `apps/proxy/ts_proxy/url_utils.py` - Profile Failover Logik
5. `apps/output/views.py` - Basic Auth

### Wichtige Funktionen

#### Profile Failover
```python
# Versucht alle Profile eines Streams vor Wechsel zum nächsten
alternate_streams = get_alternate_streams(channel_id, current_stream_id, current_profile_id)
# Gibt Liste von {stream_id, profile_id, name} zurück
```

#### HTTP Proxy für FFmpeg
```python
# Automatisch aus M3U Account geladen
proxy = stream.m3u_account.proxy
# An FFmpeg übergeben
self.transcode_cmd = stream_profile.build_command(self.url, self.user_agent, proxy)
```

#### Basic Authentication
```python
# Extrahiert und validiert User aus HTTP Basic Auth Header
user = get_basic_auth_user(request)
if not user:
    return require_basic_auth(request)
```

## 🔧 Tricky Stellen für Nächste Version

### 1. **Stream Manager Initialisierung** ⚠️
**Problem:** Der StreamManager hat viele Parameter im `__init__`
**Lösung:** Profile-ID Tracking wurde sauber in bestehende Struktur integriert
**Für nächste Version:** Prüfen ob `__init__` Parameter als kwargs übergeben werden sollten

### 2. **get_alternate_streams Signatur** ⚠️
**Problem:** Funktion wird an vielen Stellen aufgerufen
**Lösung:** `current_profile_id` als optionaler Parameter (backward compatible)
**Für nächste Version:** Alle Aufrufe prüfen und ggf. profile_id übergeben

### 3. **Redis Metadata Keys** ⚠️
**Problem:** Neue Keys für `m3u_profile` müssen konsistent verwendet werden
**Lösung:** Verwendet `ChannelMetadataField.M3U_PROFILE` Konstante
**Für nächste Version:** Sicherstellen dass alle Stellen die Konstante verwenden

### 4. **Proxy Parameter in build_command** ⚠️
**Problem:** `core/models.py` StreamProfile.build_command() muss proxy Parameter haben
**Lösung:** Parameter wurde bereits in vorheriger Version hinzugefügt
**Für nächste Version:** Prüfen ob alle StreamProfile Implementierungen proxy unterstützen

### 5. **URL Utils Import** ⚠️
**Problem:** Neue Funktion `get_stream_info_for_profile` muss importiert werden
**Lösung:** Import in stream_manager.py hinzugefügt
**Für nächste Version:** Prüfen ob andere Module diese Funktion auch brauchen

## 🚀 Nächste Schritte

1. **Datenbank Migration ausführen:**
   ```bash
   python manage.py makemigrations m3u
   python manage.py migrate m3u
   ```

2. **Dispatcharr neu starten:**
   ```bash
   systemctl restart dispatcharr
   # oder
   docker-compose restart
   ```

3. **Testen:**
   - Profile Failover: Stream mit mehreren Profilen testen
   - HTTP Proxy: M3U Account mit Proxy konfigurieren
   - Basic Auth: `curl -u user:pass http://localhost:9191/output/m3u/`

## 📝 Hinweise

- Alle Änderungen sind **backward compatible**
- Keine Breaking Changes
- Bestehende Funktionalität bleibt unverändert
- Neue Features sind optional und müssen konfiguriert werden

## 🐛 Bekannte Einschränkungen

1. **Proxy Support:** Funktioniert nur mit FFmpeg Transcoding, nicht mit direktem Proxy
2. **Profile Failover:** Benötigt Redis für Connection Tracking
3. **Basic Auth:** Nur für M3U Endpoints, nicht für alle API Endpoints

## 📚 Weitere Dokumentation

- Siehe `dispatcharr_enhancements.patch` für detaillierte Änderungen
- Siehe `apply_dispatcharr_enhancements.sh` für automatische Installation
- Siehe Original-Dokumentation für weitere Features
