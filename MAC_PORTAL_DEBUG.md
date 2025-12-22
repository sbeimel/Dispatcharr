# MAC Portal Debugging Guide

## 🎯 **DURCHBRUCH: "login-failed" Problem identifiziert!**

### Neue Erkenntnisse (2025-12-22 11:15)

**Das Portal antwortet mit "login-failed" - Status 488!**

**Logs zeigen:**
- ✅ Handshake erfolgreich
- ❌ `Session cookies: {}` - Keine Cookies in Session
- ❌ `Response status: 488` (nicht 200)
- ❌ `Response content: " login-failed "`

### Root Cause gefunden:
Das Portal erwartet, dass die **Enhanced Cookies aus dem Handshake in der Session gespeichert** werden, nicht als explizite Cookie-Parameter gesendet.

### ✅ **Kritische Fixes implementiert:**

1. **Enhanced Cookies VOR Handshake in Session setzen:**
```python
# Enhanced Cookies in Session setzen BEVOR Handshake
for cookie_name, cookie_value in cookies.items():
    session.cookies.set(cookie_name, cookie_value)

# Handshake OHNE explizite cookies= Parameter
response = session.get(full_url, headers=headers, proxies=proxies, timeout=20)
```

2. **Alle API-Calls verwenden nur Session-Cookies:**
```python
# Keine expliziten cookies= Parameter mehr
response = session.get(url, headers=headers, proxies=proxies, timeout=15)
```

3. **Enhanced Logging für Session-Cookies:**
```python
logger.info(f"Session cookies for expiry request: {dict(session.cookies)}")
logger.info(f"Session now has {len(session.cookies)} total cookies")
```

### Erwartetes Ergebnis:

Das Portal sollte jetzt:
1. ✅ Enhanced Cookies in Session haben
2. ✅ Handshake mit Session-Cookies durchführen
3. ✅ **Status 200 statt 488 zurückgeben**
4. ✅ **Gültige JSON-Antworten statt "login-failed"**
5. ✅ Channels und Expiry-Daten liefern

### Nächster Test wird zeigen:
- `Set X enhanced cookies in session before handshake`
- `Session now has X total cookies`
- `Session cookies for expiry request: {...}`
- **Hoffentlich Status 200 und gültige JSON-Antworten!**

## Technische Details

### Cookie-Flow (korrigiert):
1. **Enhanced Cookies → Session** (VOR Handshake)
2. **Handshake** mit Session-Cookies (keine expliziten)
3. **Portal-Response-Cookies → Session** (falls vorhanden)
4. **API-Calls** nur mit Session-Cookies

### Das war der Fehler:
```python
# FALSCH (Portal sagt "login-failed"):
response = session.get(url, cookies=explicit_cookies, ...)

# RICHTIG (Portal sollte funktionieren):
session.cookies.set(name, value)  # Cookies in Session
response = session.get(url, ...)  # Nur Session-Cookies
```

## Fazit

**Das "login-failed" Problem sollte jetzt gelöst sein!**

Der entscheidende Unterschied war, dass das Portal erwartet, dass die Enhanced Cookies als **Session-Cookies** gesendet werden, nicht als explizite Request-Parameter.
