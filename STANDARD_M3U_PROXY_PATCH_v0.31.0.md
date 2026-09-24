# Standard M3U HTTP Proxy Support - Patch v0.31.0

## 📋 Zusammenfassung

Macht HTTP Proxy Felder für **ALLE M3U Account-Typen** verfügbar (vorher nur für Xtream Codes).

## 🎯 Ziel

- Standard M3U Accounts können jetzt HTTP Proxy für Streaming nutzen
- Identische Funktionalität wie bei Xtream Codes Accounts
- MacBridge Plugin Kompatibilität bestätigt

## 🔧 Änderungen

### Frontend (`frontend/src/components/forms/M3U.jsx`)

**Vorher:**
```jsx
{form.getValues().account_type == 'XC' && (
  <Box>
    {/* Proxy fields here - only for Xtream */}
    <TextInput label="HTTP Proxy" ... />
    <Switch label="Use Proxy for API Calls" ... />
  </Box>
)}
```

**Nachher:**
```jsx
{/* HTTP Proxy fields - available for ALL account types */}
<TextInput
  label="HTTP Proxy"
  placeholder="http://proxy.example.com:8080"
  description="HTTP proxy URL for streaming (Live TV and VOD)"
  {...form.getInputProps('proxy')}
/>

<Switch
  label="Use Proxy for API Calls"
  description="When enabled, the HTTP proxy will also be used for API calls (M3U download, XC API). When disabled, proxy is only used for streaming."
  {...form.getInputProps('proxy_for_api', { type: 'checkbox' })}
/>

{form.getValues().account_type == 'XC' && (
  <Box>
    {/* XC-specific fields only */}
  </Box>
)}
```

**Resultat:**
- ✅ Proxy-Felder **VOR** der XC-Condition platziert
- ✅ Sichtbar für Standard, XC UND MAC Account-Typen
- ✅ Beschreibungstext präzisiert ("for streaming")

### Backend

**❌ KEINE Änderungen nötig!**

Backend unterstützt bereits alle Account-Typen:
- `apps/m3u/models.py` - `proxy` field (Zeile 102)
- `apps/m3u/models.py` - `proxy_for_api` field (Zeile 109)
- `apps/m3u/models.py` - `get_proxy_for_streaming()` (Zeile 131-135)
- `apps/m3u/models.py` - `get_proxy_for_api()` (Zeile 117-129)
- `apps/proxy/live_proxy/input/manager.py` - Verwendet `get_proxy_for_streaming()` (account-type unabhängig)
- `apps/proxy/vod_proxy/multi_worker_connection_manager.py` - Gleiche Logik

## 📦 Patch anwenden

```bash
# Patch anwenden
git apply dispatcharr_v0.31.0_standard_m3u_proxy.patch

# Frontend bauen
cd frontend
npm run build
cd ..

# Service neustarten
docker-compose restart
# oder
systemctl restart dispatcharr
```

## ✅ Verifizierung

### WebUI Test:

1. **Standard M3U Account erstellen:**
   - Account Type: **Standard** wählen
   - M3U URL: `http://provider.com/playlist.m3u8`
   - HTTP Proxy: `http://myproxy:8080` ← **JETZT SICHTBAR!**
   - ☑ Use Proxy for API Calls ← **JETZT VERFÜGBAR!**

2. **Xtream Codes Account:**
   - Felder weiterhin verfügbar ✅
   
3. **MAC Account:**
   - Felder jetzt auch verfügbar ✅

### Backend Verhalten:

```python
# Standard M3U mit Proxy
account = M3UAccount.objects.get(name="My Standard M3U")
account.account_type  # "Standard"
account.proxy         # "http://myproxy:8080"
account.proxy_for_api # True/False

# Streaming verwendet Proxy
account.get_proxy_for_streaming()  # → "http://myproxy:8080"

# API Calls je nach Setting
account.get_proxy_for_api()  # → "http://myproxy:8080" (wenn proxy_for_api=True)
                             # → None (wenn proxy_for_api=False)
```

## 🔌 MacBridge Plugin Kompatibilität

### Plugin Status: ✅ **KOMPATIBEL**

**Was das Plugin setzt:**
```python
# macbridge_v6/plugin.py Zeile 571-575
if proxy:
    if hasattr(M3UAccount, 'proxy'):
        account_defaults['proxy'] = proxy  # ✅ Korrekt!
```

**Resultat:**
- ✅ Plugin setzt `proxy` Feld
- ✅ Live-TV Streaming via Proxy
- ✅ VOD Streaming via Proxy
- ❌ API Calls OHNE Proxy (Plugin setzt `proxy_for_api` nicht)

**Falls API-Proxy gewünscht:**
Nach Plugin-Import im WebUI manuell `proxy_for_api` aktivieren.

## 📊 Account-Type Matrix

| Account Type | HTTP Proxy Feld | Use Proxy for API | Streaming | API Calls |
|--------------|----------------|-------------------|-----------|-----------|
| **Standard** | ✅ Verfügbar | ✅ Verfügbar | ✅ Proxy | ☑ Optional |
| **Xtream (XC)** | ✅ Verfügbar | ✅ Verfügbar | ✅ Proxy | ☑ Optional |
| **MAC** | ✅ Verfügbar | ✅ Verfügbar | ✅ Proxy | ☑ Optional |

## 🔄 Migration

**Bestehende Accounts:**
- ✅ Keine Migration nötig
- ✅ Felder bereits in DB vorhanden
- ✅ Nur UI-Änderung (waren versteckt)
- ✅ Nach Patch sofort sichtbar

## 📝 Use Cases

### 1. Standard M3U mit Proxy
```
Szenario: Provider blockiert Server-IPs
Lösung: HTTP Proxy für Streaming nutzen

Account Settings:
- Type: Standard
- URL: http://provider.com/playlist.m3u8
- Proxy: http://residential-proxy:8080
- Use Proxy for API: ☑ (wenn M3U Download auch geblockt)
```

### 2. MacBridge Import mit Proxy
```
Plugin Settings:
- Portal: http://portal.example.com
- MAC: 00:1A:79:XX:XX:XX
- Proxy: http://myproxy:8080

→ Erstellt MAC Account mit proxy="http://myproxy:8080"
→ Streaming läuft automatisch via Proxy
```

### 3. Geo-Restricted Content
```
Provider erlaubt nur bestimmte Länder
→ HTTP Proxy mit IP aus erlaubtem Land
→ Streaming funktioniert
```

## 🛠️ Technische Details

### Proxy Usage Flow:

```
User Request
   ↓
Dispatcharr Proxy Manager
   ↓
m3u_account.get_proxy_for_streaming()
   ↓
if m3u_account.proxy:
    return m3u_account.proxy  # ← Unabhängig vom Account Type!
else:
    return None
   ↓
HTTP Request mit/ohne Proxy
   ↓
Provider Stream
```

### Code Locations:

**Frontend:**
- `frontend/src/components/forms/M3U.jsx` (Zeile ~427-445)

**Backend:**
- `apps/m3u/models.py` - Felder & Getter-Methoden
- `apps/m3u/serializers.py` - API Serialization
- `apps/proxy/live_proxy/input/manager.py` - Live-TV Proxy Usage
- `apps/proxy/vod_proxy/multi_worker_connection_manager.py` - VOD Proxy Usage

## 🐛 Bekannte Einschränkungen

**Keine!** Feature ist vollständig funktional.

**Hinweise:**
- MacBridge Plugin setzt `proxy_for_api` nicht automatisch (manuell aktivieren falls benötigt)
- Plugin prüft noch veraltetes `proxy_std_xc` Feld (wird ignoriert via `hasattr()`)

## 📚 Siehe auch

- `PROXY_FOR_STANDARD_M3U_IMPLEMENTATION.md` - Detaillierte Implementierungsanalyse
- `STANDARD_M3U_PROXY_SUMMARY.md` - Feature-Übersicht
- `verify_standard_m3u_proxy.py` - Verifikations-Script

## ✨ Credits

Feature-Request: HTTP Proxy Support für Standard M3U (wie Xtream Codes)
Implementiert: v0.31.0
Status: ✅ Production Ready
