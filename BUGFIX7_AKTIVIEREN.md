# Bugfix #7 aktivieren - Schritt für Schritt

**Problem:** Bugfix #7 ist im Code vorhanden, aber nicht aktiv!  
**Ursache:** Container wurden nicht neu gestartet nach Code-Änderungen  
**Lösung:** Container neu starten

---

## Schnell-Lösung (3 Befehle)

```bash
# 1. Redis Counter zurücksetzen
docker exec -it $(docker ps --filter "name=redis" --format "{{.Names}}" | head -n 1) redis-cli KEYS "profile_connections:*" | xargs docker exec -it $(docker ps --filter "name=redis" --format "{{.Names}}" | head -n 1) redis-cli DEL

# 2. Container neu starten
cd /mnt/user/Downloads/eigne/Dispatcharr/docker
docker-compose restart web celery

# 3. Logs prüfen
docker-compose logs -f web | grep "Released stream"
```

Wenn du jetzt "Released stream after failed attempt" siehst: ✅ Bugfix #7 ist aktiv!

---

## Detaillierte Anleitung

### Schritt 1: Prüfe ob Code vorhanden ist

```bash
cd /mnt/user/Downloads/eigne/Dispatcharr

# Prüfe views.py
grep -n "Released stream after failed attempt" apps/proxy/ts_proxy/views.py
```

**Erwartetes Ergebnis:**
```
197:                    logger.debug(f"[{client_id}] Released stream after failed attempt {attempt}")
```

Wenn du das siehst: ✅ Code ist vorhanden

### Schritt 2: Prüfe Redis Counter

```bash
# Finde Redis Container Name
docker ps | grep redis

# Zeige alle Counter (ersetze <redis-container> mit dem Namen)
docker exec -it <redis-container> redis-cli KEYS "profile_connections:*"

# Zeige Counter-Werte
docker exec -it <redis-container> redis-cli GET profile_connections:224
```

**Problem:** Counter ist bei 14 oder höher (sollte 0 sein)

### Schritt 3: Reset Counter

```bash
# Option 1: Alle Counter löschen
docker exec -it <redis-container> redis-cli KEYS "profile_connections:*" | xargs docker exec -it <redis-container> redis-cli DEL

# Option 2: Spezifischen Counter löschen
docker exec -it <redis-container> redis-cli DEL profile_connections:224

# Option 3: Python Script verwenden
python reset_profile_connections.py
```

### Schritt 4: Container neu starten

```bash
cd /mnt/user/Downloads/eigne/Dispatcharr/docker

# Container neu starten
docker-compose restart web celery

# Warte 10 Sekunden
sleep 10

# Prüfe Logs
docker-compose logs --tail=50 web
```

### Schritt 5: Verifikation

```bash
# Logs in Echtzeit anschauen
docker-compose logs -f web

# In einem anderen Terminal: Teste einen Stream
# Öffne im Browser: http://localhost:9191
# Klicke auf einen Kanal
```

**Was du sehen solltest:**

```
✅ RICHTIG (Bugfix #7 aktiv):
2026-03-12 15:51:00,173 INFO ts_proxy.views [client_xxx] Waiting 100ms for a connection...
2026-03-12 15:51:00,173 DEBUG ts_proxy.views [client_xxx] Released stream after failed attempt 1
2026-03-12 15:51:00,274 INFO ts_proxy.views [client_xxx] Waiting 125ms for a connection...
2026-03-12 15:51:00,274 DEBUG ts_proxy.views [client_xxx] Released stream after failed attempt 2
...

❌ FALSCH (Bugfix #7 nicht aktiv):
2026-03-12 15:51:00,173 INFO ts_proxy.views [client_xxx] Waiting 100ms for a connection...
2026-03-12 15:51:00,274 INFO ts_proxy.views [client_xxx] Waiting 125ms for a connection...
(KEINE "Released stream" Meldungen!)
```

---

## Automatisches Script

Ich habe ein Script erstellt, das alles automatisch prüft und behebt:

```bash
cd /mnt/user/Downloads/eigne/Dispatcharr
chmod +x CHECK_AND_FIX_BUGFIX7.sh
./CHECK_AND_FIX_BUGFIX7.sh
```

Das Script:
1. ✅ Prüft ob Code vorhanden ist
2. ✅ Zeigt Redis Counter
3. ✅ Bietet an, Counter zurückzusetzen
4. ✅ Bietet an, Container neu zu starten
5. ✅ Zeigt Logs zur Verifikation

---

## Warum ist der Bugfix nicht aktiv?

### Mögliche Ursachen:

1. **Container nicht neu gestartet** (HÄUFIGSTE URSACHE!)
   - Code wurde geändert, aber Container läuft noch mit altem Code
   - Lösung: `docker-compose restart web celery`

2. **Falsches Image verwendet**
   - Container verwendet altes Image ohne Bugfix
   - Lösung: Image neu bauen und Container neu starten

3. **Code nicht gespeichert**
   - Änderungen wurden nicht gespeichert
   - Lösung: Prüfe mit `grep` ob Code vorhanden ist

4. **Falsches Verzeichnis**
   - Container mountet falsches Verzeichnis
   - Lösung: Prüfe `docker-compose.yml` volumes

---

## Deine Logs zeigen:

```
❌ 14 Versuche ohne "Released stream" Meldungen
❌ Counter bleibt bei 14 hängen
❌ Nächster Request bekommt "No profiles available"
```

**Das bedeutet:** Bugfix #7 ist NICHT aktiv!

**Lösung:**

```bash
# 1. Reset Counter
docker exec -it $(docker ps --filter "name=redis" --format "{{.Names}}" | head -n 1) redis-cli DEL profile_connections:224

# 2. Container neu starten
cd /mnt/user/Downloads/eigne/Dispatcharr/docker
docker-compose restart web celery

# 3. Teste erneut
# Öffne Browser: http://localhost:9191
# Klicke auf DAS ERSTE HD

# 4. Prüfe Logs
docker-compose logs -f web | grep "Released stream"
```

Wenn du jetzt "Released stream after failed attempt" siehst: ✅ Problem gelöst!

---

## Nach dem Fix

### Was du sehen solltest:

```
✅ Counter bleibt bei 0 oder 1 (nicht 14!)
✅ "Released stream after failed attempt" in Logs
✅ Keine "No profiles available" Fehler mehr
✅ Streams funktionieren wieder
```

### Redis Counter prüfen:

```bash
# Vor dem Stream-Start
docker exec -it <redis-container> redis-cli GET profile_connections:224
# Ergebnis: (nil) oder 0

# Während Stream läuft
docker exec -it <redis-container> redis-cli GET profile_connections:224
# Ergebnis: 1

# Nach Stream-Ende
docker exec -it <redis-container> redis-cli GET profile_connections:224
# Ergebnis: 0
```

---

## Zusammenfassung

**Problem:** Container läuft mit altem Code (ohne Bugfix #7)  
**Lösung:** Container neu starten  
**Verifikation:** "Released stream after failed attempt" in Logs  
**Ergebnis:** Counter bleibt bei 0, keine Fehler mehr  

---

**Erstellt:** 2026-03-12  
**Version:** 1.0

