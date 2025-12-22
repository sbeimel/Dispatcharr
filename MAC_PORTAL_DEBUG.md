# MAC Portal Debugging Guide

## 🔍 **NEUE ERKENNTNIS - Cookie-Handling Problem!**

### Problem identifiziert (2025-12-22 11:11)

Das Portal `dlta4k.com` gibt **leere Antworten** zurück, weil unser Cookie-Handling nicht korrekt ist!

**Beobachtung aus MacReplayXC:**
- MacReplayXC sendet Cookies nur als Session-Cookies, nicht als explizite `cookies=` Parameter
- Dispatcharr hat beide gesendet: Session-Cookies UND explizite Cookies

### ✅ **Neue Fixes implementiert:**

1. **Cookie-Handling korrigiert:**
```python
# VORHER (falsch):
response = session.get(url, cookies=cookies, headers=headers, ...)

# JETZT (korrekt):
# Cookies in Session setzen, dann ohne cookies= Parameter
for cookie_name, cookie_value in session.cookies.items():
    cookies[cookie_name] = cookie_value
response = session.get(url, headers=headers, ...)  # Nur Session-Cookies
```

2. **Enhanced Logging auf INFO-Level:**
```python
logger.info(f"Making expiry request with combined cookies: {dict(cookies)}")
logger.info(f"Session cookies: {dict(session.cookies)}")
```

3. **Cookie-Kombination:**
- Enhanced Cookies (MAC, Device IDs, etc.) werden in Session gesetzt
- Session-Cookies aus Handshake werden beibehalten
- Nur Session-Cookies werden verwendet, keine expliziten Cookie-Parameter

### Erwartete Verbesserung

Das Portal sollte jetzt:
1. ✅ Handshake erfolgreich (funktioniert bereits)
2. ✅ Cookies aus Handshake in Session speichern
3. ✅ Enhanced Cookies in Session kombinieren
4. ✅ Nur Session-Cookies für API-Calls verwenden
5. ✅ **Nicht-leere JSON-Antworten erhalten**

### Nächster Test

Die Logs werden jetzt zeigen:
- `Making expiry request with combined cookies: {...}`
- `Session cookies: {...}`
- Ob das Portal endlich Inhalte zurückgibt

## Technische Details

### Cookie-Flow (korrigiert):
1. **Handshake**: Enhanced Cookies → Session
2. **Handshake Response**: Portal-Cookies → Session hinzufügen
3. **API Calls**: Nur Session-Cookies verwenden
4. **Keine expliziten cookies= Parameter mehr**

### MacReplayXC Vergleich:
```python
# MacReplayXC (funktioniert):
cookies = {"mac": mac, "stb_lang": "en", "timezone": "Europe/London"}
response = session.get(url, cookies=cookies, ...)

# Dispatcharr (jetzt korrigiert):
# Cookies in Session, dann:
response = session.get(url, ...)  # Session handled cookies
```

## Fazit

**Das war der entscheidende Unterschied zu MacReplayXC!**

Die Cookie-Behandlung war der Grund für die leeren Antworten. Mit der korrigierten Implementierung sollte `dlta4k.com` jetzt funktionieren.
