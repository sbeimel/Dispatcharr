# 🚀 DISPATCHARR ENHANCEMENTS v0.18.1 EXTENDED

**Vollständige Enhancement-Suite für Dispatcharr 0.18.1**

---

## 📦 **WAS IST ENTHALTEN**

### **✅ CORE FEATURES**
- **Profile Failover System** - Intelligentes Stream+Profile Switching
- **HTTP Proxy Support** - Proxy-Unterstützung für M3U Accounts
- **Basic Authentication** - Sichere M3U/EPG Endpoints
- **Configuration Enhancements** - Optimierte Retry-Logik

### **✅ EXTENDED FEATURES**
- **Frontend Timeout Configuration** - Alle Timeouts über UI konfigurierbar
- **Ghost-Client Fix** - Automatische Bereinigung ohne Stats-Klick
- **Universal HTTP Proxy Support** - Proxy für ALLE Stream-Profile (FFmpeg + Proxy)
- **Enhanced Logging** - Verbesserte Fehlerbehandlung

---

## 🎛️ **NEUE KONFIGURIERBARE SETTINGS**

| Setting | Default | Beschreibung |
|---------|---------|--------------|
| `max_retries` | 2 | Retry-Versuche pro Stream/Profile |
| `url_switch_timeout` | 8s | Timeout für Stream-Wechsel |
| `max_stream_switches` | 10 | Max Stream+Profile Kombinationen |
| `connection_timeout` | 10s | Verbindungs-Timeout |
| `buffering_timeout` | 15s | Puffer-Timeout |
| `failover_grace_period` | 20s | Grace Period für Failover |

**Alle Settings sind über das Frontend konfigurierbar!**

---

## 🛠️ **INSTALLATION**

### **Einfache Installation:**
```bash
cd Dispatcharr-0.18.1/
../apply_dispatcharr_enhancements_v0.18.1.sh
```

### **Manuelle Installation:**
```bash
cd Dispatcharr-0.18.1/
patch -p1 < ../dispatcharr_enhancements_v0.18.1_extended.patch
python manage.py makemigrations m3u
python manage.py migrate
# Dispatcharr neu starten
```

---

## 🔍 **VERIFIKATION**

Nach der Installation prüfen:

### **✅ Profile Failover**
- Logs zeigen `tried_combinations` tracking
- Stream-Switching zwischen verschiedenen Profilen

### **✅ HTTP Proxy**
- M3U Form hat "HTTP Proxy" Feld
- FFmpeg verwendet Proxy-Parameter
- **NEU:** Proxy Profile verwenden HTTP-Proxy über requests.Session

### **✅ Basic Auth**
- M3U/EPG Endpoints funktionieren ohne User-Parameter
- HTTP Basic Authentication wird akzeptiert

### **✅ Extended Config**
- Frontend zeigt alle neuen Timeout-Settings
- Settings werden in Datenbank gespeichert

### **✅ Ghost-Client Fix**
- Logs zeigen automatische Client-Bereinigung
- Stats sind immer korrekt ohne manuellen Klick

---

## 📋 **DATEIEN**

### **✅ AKTUELLE DATEIEN:**
- `dispatcharr_enhancements_v0.18.1_extended.patch` - **Master Patch**
- `apply_dispatcharr_enhancements_v0.18.1.sh` - **Auto-Installer**
- `ERWEITERTE_KONFIGURATION_COMPLETE.md` - **Feature-Dokumentation**
- `DISPATCHARR_ENHANCEMENTS_README.md` - **Diese Datei**

### **🗑️ AUFGERÄUMT:**
Alle veralteten .md und .patch Dateien wurden entfernt für bessere Übersicht.

---

## 🐛 **GHOST-CLIENT FIX DETAILS**

### **Problem:**
- Clients disconnecten aber bleiben in Stats sichtbar
- Redis SET vs Individual Keys Race Condition

### **Lösung:**
- **Heartbeat-Thread** prüft alle 5-10s automatisch
- **Atomic Operations** entfernen Ghosts aus Redis SET
- **Smart Client Count** bereinigt bei jeder Abfrage
- **Keine manuellen Stats-Klicks** mehr nötig

### **Logging:**
```
INFO: Removed 3 ghost clients from Redis set for channel abc123
INFO: Client cleanup for channel abc123: 5 total (3 set ghosts, 2 inactive)
DEBUG: Auto-cleaned 2 ghost clients from set during count
```

---

## 🎯 **SEAMLESS-SWITCHING INFO**

**Frage:** Funktioniert Seamless-Switching bei Codec/Resolution-Änderungen?

**Antwort:** **NEIN** - Bei Format-Änderungen wird automatisch neu verbunden:
- FFmpeg-Prozess muss neu gestartet werden
- Buffer wird geleert für sauberen Wechsel
- Typische Unterbrechung: 4-8 Sekunden
- **Technisch unvermeidlich** für Format-Wechsel

---

## 🚀 **NEXT STEPS**

1. **Installation** mit dem Auto-Installer
2. **Dispatcharr neu starten**
3. **Frontend-Settings** konfigurieren
4. **Logs überwachen** für Ghost-Client Cleanup
5. **Profile Failover** testen

---

## 📞 **SUPPORT**

Bei Problemen:
1. **Backup** wurde automatisch erstellt
2. **Logs** prüfen für Fehlermeldungen
3. **Rollback** mit Backup möglich
4. **Verifikation** im Installer zeigt Status

---

**Happy Streaming! 🎬**

*Dispatcharr Enhancements v0.18.1 Extended - Alles in einem Paket!*