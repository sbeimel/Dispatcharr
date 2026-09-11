# HTTP Proxy for Standard M3U Accounts - Implementation

## 📋 Übersicht

Erweitert HTTP Proxy Support von nur Xtream Codes auf **ALLE** M3U Account-Typen.

**Vorher:**
- ✅ Xtream Codes: HTTP Proxy Felder verfügbar
- ❌ Standard M3U: Keine Proxy-Felder im WebUI

**Nachher:**
- ✅ Xtream Codes: HTTP Proxy Felder verfügbar
- ✅ Standard M3U: HTTP Proxy Felder verfügbar ← **NEU!**

---

## 🎯 Was wurde geändert?

### Frontend (1 Datei)

**`frontend/src/components/forms/M3U.jsx`**

**Vorher:**
```jsx
{form.getValues().account_type == 'XC' && (
  <Box>
    <TextInput label="HTTP Proxy" ... />
    <Switch label="Use Proxy for API Calls" ... />
    {/* Andere XC-spezifische Felder */}
  </Box>
)}
```

**Nachher:**
```jsx
{/* HTTP Proxy fields - available for ALL account types */}
<TextInput
  label="HTTP Proxy"
  description="HTTP proxy URL for streaming (Live TV and VOD)"
  {...form.getInputProps('proxy')}
/>

<Switch
  label="Use Proxy for API Calls"
  description="When enabled, the HTTP proxy will also be used for API calls..."
  {...form.getInputProps('proxy_for_api', { type: 'checkbox' })}
/>

{form.getValues().account_type == 'XC' && (
  <Box>
    {/* XC-spezifische Felder: VOD Priority, Enable VOD, Create EPG */}
  </Box>
)}
```

**Änderung:**
- Proxy-Felder **raus** aus der XC-Bedingung
- Proxy-Felder **vor** der XC-Bedingung
- Description angepasst: "Live TV and VOD" statt "always used"

---

## ✅ Backend Support (bereits vorhanden!)

### Models (`apps/m3u/models.py`)

```python
class M3UAccount(models.Model):
    # ...
    proxy = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="HTTP proxy URL for streaming"
    )
    proxy_for_api = models.BooleanField(
        default=False,
        help_text="Use HTTP proxy for API calls"
    )
    
    def get_proxy_for_streaming(self):
        """Get proxy URL for streaming - works for ALL account types!"""
        if self.proxy and self.proxy.strip():
            return self.proxy
        return None
```

✅ **Funktioniert bereits für Standard M3U!**

---

## 🔄 Wie wird Proxy genutzt?

### 1. Live-TV Streaming

**Code:** `apps/proxy/live_proxy/input/manager.py`

```python
if hasattr(stream, 'm3u_account') and stream.m3u_account:
    proxy = stream.m3u_account.get_proxy_for_streaming()
    if proxy:
        logger.info(f"Using proxy {proxy} for HTTP streaming")
```

✅ **Account-Type unabhängig** (Standard + XC)

---

### 2. VOD Streaming

**Code:** `apps/proxy/vod_proxy/multi_worker_connection_manager.py`

```python
m3u_account = M3UAccount.objects.get(id=state.m3u_account_id)
proxy = m3u_account.get_proxy_for_streaming()
if proxy:
    self.local_session.proxies = {
        'http': proxy,
        'https': proxy
    }
    logger.info(f"Using HTTP proxy for VOD streaming: {proxy}")
```

✅ **Account-Type unabhängig** (Standard + XC)

---

### 3. API Calls (Optional)

**Code:** `apps/m3u/models.py`

```python
def get_proxy_for_api(self):
    """Get proxy URL for API calls only if proxy_for_api is enabled."""
    if self.proxy and self.proxy.strip() and self.proxy_for_api:
        return self.proxy
    return None
```

✅ **Account-Type unabhängig** (Standard + XC)

**Genutzt für:**
- M3U Download (bei Standard M3U: direkte URL)
- Xtream API Calls (bei XC: get.php, player_api.php)
- EPG Downloads

---

## 📊 Use Cases

### Use Case 1: Standard M3U + Geo-Block

**Problem:**
- M3U-Provider geo-blockt Streaming
- Aber M3U-URL selbst ist erreichbar

**Lösung:**
```
Account Type: Standard
HTTP Proxy: http://myproxy:8080
☐ Use Proxy for API Calls

→ M3U Download: Direkt (kein Proxy)
→ Live-TV Streaming: Via Proxy ✅
→ VOD Streaming: Via Proxy ✅
```

---

### Use Case 2: Standard M3U + M3U auch geo-blockt

**Problem:**
- M3U-Provider geo-blockt alles
- M3U-URL + Streaming beide blockiert

**Lösung:**
```
Account Type: Standard
HTTP Proxy: http://myproxy:8080
☑ Use Proxy for API Calls

→ M3U Download: Via Proxy ✅
→ Live-TV Streaming: Via Proxy ✅
→ VOD Streaming: Via Proxy ✅
```

---

### Use Case 3: Xtream Codes (wie vorher)

**Unverändert:**
```
Account Type: Xtream Codes
HTTP Proxy: http://myproxy:8080
☑ Use Proxy for API Calls

→ XC API Calls: Via Proxy
→ Live-TV Streaming: Via Proxy
→ VOD Streaming: Via Proxy
```

---

## 🎨 WebUI Changes

### Standard M3U Account Form

**Vorher:**
```
┌─────────────────────────────────────┐
│ Account Type: Standard              │
├─────────────────────────────────────┤
│ Server URL: http://...              │
│ Max Streams: 1                      │
│ User Agent: (Default)               │
│                                     │
│ (KEINE Proxy-Felder)                │ ← Fehlt!
└─────────────────────────────────────┘
```

**Nachher:**
```
┌─────────────────────────────────────┐
│ Account Type: Standard              │
├─────────────────────────────────────┤
│ Server URL: http://...              │
│ Max Streams: 1                      │
│ User Agent: (Default)               │
│                                     │
│ HTTP Proxy                          │ ← NEU!
│ [http://proxy:8080]                 │
│                                     │
│ ☑ Use Proxy for API Calls          │ ← NEU!
└─────────────────────────────────────┘
```

---

### Xtream Codes Account Form

**Unverändert:**
```
┌─────────────────────────────────────┐
│ Account Type: Xtream Codes          │
├─────────────────────────────────────┤
│ Server URL: http://...              │
│ Username: user123                   │
│ Password: ****                      │
│                                     │
│ HTTP Proxy                          │ ← Wie vorher
│ [http://proxy:8080]                 │
│                                     │
│ ☑ Use Proxy for API Calls          │ ← Wie vorher
│                                     │
│ VOD Priority: 0                     │ ← XC-spezifisch
│ ☑ Enable VOD Scanning               │ ← XC-spezifisch
└─────────────────────────────────────┘
```

---

## 🔧 Installation

### 1. Datei editieren

```bash
cd /path/to/dispatcharr
nano frontend/src/components/forms/M3U.jsx
```

Ersetze die Proxy-Felder-Sektion wie oben beschrieben.

---

### 2. Frontend neu bauen

```bash
cd frontend
npm run build
cd ..
```

---

### 3. Service neustarten (optional)

```bash
# Docker
docker-compose restart

# Systemd
sudo systemctl restart dispatcharr
```

---

### 4. WebUI testen

1. Öffne WebUI
2. Gehe zu M3U Accounts
3. Erstelle/Editiere Standard M3U Account
4. ✅ Proxy-Felder sollten sichtbar sein!

---

## ✅ Verification

### Manuell prüfen:

1. **WebUI öffnen:**
   - Settings → M3U Accounts → Create/Edit Standard Account

2. **Proxy-Felder sichtbar:**
   - ✅ "HTTP Proxy" TextInput vorhanden
   - ✅ "Use Proxy for API Calls" Switch vorhanden
   - ✅ Felder funktionieren (eingeben + speichern)

3. **Backend-Test:**
   ```python
   # Django Shell
   python manage.py shell
   
   >>> from apps.m3u.models import M3UAccount
   >>> account = M3UAccount.objects.filter(account_type='STD').first()
   >>> account.proxy = "http://test:8080"
   >>> account.save()
   >>> account.get_proxy_for_streaming()
   'http://test:8080'  # ← Sollte Proxy zurückgeben!
   ```

4. **Log-Test (Live-TV):**
   ```bash
   # Stream starten und Logs prüfen
   grep "Using proxy.*for HTTP streaming" logs/dispatcharr.log
   
   # Sollte zeigen:
   # INFO Using proxy http://test:8080 for HTTP streaming channel ...
   ```

5. **Log-Test (VOD):**
   ```bash
   # VOD streamen und Logs prüfen
   grep "Using HTTP proxy for VOD streaming" logs/dispatcharr.log
   
   # Sollte zeigen:
   # INFO Using HTTP proxy for VOD streaming: http://test:8080
   ```

---

## 📝 Was ändert sich NICHT?

### Backend Logic
- ✅ Bleibt unverändert
- ✅ `get_proxy_for_streaming()` funktioniert bereits für alle Account-Types
- ✅ `get_proxy_for_api()` funktioniert bereits für alle Account-Types

### Database Schema
- ✅ Keine Migrations nötig
- ✅ `proxy` und `proxy_for_api` Felder existieren bereits
- ✅ Funktionieren bereits für Standard M3U (nur UI fehlte!)

### API Endpoints
- ✅ Unverändert
- ✅ Serializer enthält bereits `proxy` und `proxy_for_api`
- ✅ Funktioniert bereits für alle Account-Types

---

## 🎯 Benefits

### 1. Feature Parity
- ✅ Standard M3U hat jetzt gleiche Proxy-Optionen wie XC
- ✅ Konsistente User Experience

### 2. Mehr Use Cases
- ✅ Geo-blocked Standard M3U Providers
- ✅ Privacy/Anonymität für Standard M3U
- ✅ Corporate Proxies für Standard M3U

### 3. Einfache Implementierung
- ✅ Nur Frontend-Änderung (1 Datei, ~50 Zeilen)
- ✅ Backend funktioniert bereits
- ✅ Keine Breaking Changes

### 4. Backwards Compatible
- ✅ Bestehende Accounts unbeeinflusst
- ✅ Neue Felder optional (blank=True)
- ✅ Defaults: proxy="" (leer), proxy_for_api=False

---

## ⚠️ Wichtige Hinweise

### 1. API Calls bei Standard M3U

**Standard M3U hat weniger API Calls:**
- Nur M3U-Download (server_url)
- Kein Panel-API wie bei XC

**Toggle "Use Proxy for API" macht bei Standard:**
- M3U-Download via Proxy (wenn URL geo-blockt)
- Sonst meist nicht nötig (M3U-URL meist erreichbar)

---

### 2. Proxy-Validierung

**Backend validiert Proxy-Format:**
```python
def clean(self):
    if self.proxy and self.proxy.strip():
        from core.utils import validate_proxy_url
        validate_proxy_url(self.proxy.strip())
```

**Gültige Formate:**
- `http://proxy.example.com:8080`
- `http://user:pass@proxy:8080`
- `socks5://proxy:1080`

---

### 3. Proxy Performance

**Proxy kann Streaming verlangsamen:**
- Zusätzlicher Hop
- Proxy Bandwidth limit
- Proxy Latenz

**Empfehlung:**
- Nur nutzen wenn nötig (Geo-Block)
- Schnellen Proxy wählen
- Monitoring der Stream-Qualität

---

## 🧪 Testing Checklist

- [ ] Frontend gebaut (`npm run build`)
- [ ] Service neugestartet
- [ ] WebUI geöffnet
- [ ] Standard M3U Account erstellt/editiert
- [ ] Proxy-Felder sichtbar ✅
- [ ] HTTP Proxy eingegeben und gespeichert
- [ ] Live-TV Stream gestartet
- [ ] Log zeigt "Using proxy" ✅
- [ ] VOD Stream gestartet (falls verfügbar)
- [ ] Log zeigt "Using HTTP proxy for VOD" ✅
- [ ] Toggle "Use Proxy for API" getestet
- [ ] M3U Download erfolgt via Proxy (wenn Toggle AN)

---

## 📚 Related Files

**Frontend:**
- `frontend/src/components/forms/M3U.jsx` - M3U Account Form (GEÄNDERT)

**Backend:**
- `apps/m3u/models.py` - M3UAccount Model (Proxy Felder + Methoden)
- `apps/m3u/serializers.py` - Serializer (enthält bereits proxy fields)
- `apps/proxy/live_proxy/input/manager.py` - Live-TV Proxy Usage
- `apps/proxy/vod_proxy/multi_worker_connection_manager.py` - VOD Proxy Usage

---

## 🚀 Deployment Ready

- ✅ Implementation complete
- ✅ No backend changes needed
- ✅ No database migrations needed
- ✅ No breaking changes
- ✅ Backwards compatible
- ✅ Simple frontend-only change

**Ready to deploy!** 🎉

---

**Date:** 2026-09-11  
**Change Type:** Feature Enhancement (Frontend)  
**Risk Level:** LOW (UI-only, existing backend)  
**Breaking Changes:** None
