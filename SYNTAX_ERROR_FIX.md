# 🔧 SYNTAX ERROR FIX - stream_manager.py

## Problem

```
IndentationError: unexpected indent
File "/app/apps/proxy/ts_proxy/stream_manager.py", line 1741
```

## Ursache

Beim Lesen der Datei aus dem Patch wurde **doppelter Code** eingefügt. Die alte Version der `_try_next_stream()` Methode wurde nicht vollständig entfernt.

## Lösung

### Option 1: Manuelle Korrektur (EMPFOHLEN)

```bash
cd ~/Dispatcharr

# Backup erstellen
cp apps/proxy/ts_proxy/stream_manager.py apps/proxy/ts_proxy/stream_manager.py.backup

# Datei bearbeiten
nano apps/proxy/ts_proxy/stream_manager.py
```

**Suche nach Zeile ~1741** und entferne ALLE Zeilen zwischen:
```python
        except Exception as e:
            logger.error(f"Error trying next stream for channel {self.channel_id}: {e}", exc_info=True)
            return False

# HIER BEGINNT DER DOPPELTE CODE - ALLES BIS ZUR NÄCHSTEN METHODE LÖSCHEN!
                # IMPORTANT: Just update the URL, don't stop the channel or release resources
                switch_result = self.update_url(new_url, stream_id, profile_id)
                ...
                # (viel mehr doppelter Code)
                ...
            return False

    # Add a new helper method to safely reset the URL switching state  ← HIER ENDET DER DOPPELTE CODE
    def _reset_url_switching_state(self):
```

**Die Datei sollte so aussehen:**
```python
        except Exception as e:
            logger.error(f"Error trying next stream for channel {self.channel_id}: {e}", exc_info=True)
            return False

    # Add a new helper method to safely reset the URL switching state
    def _reset_url_switching_state(self):
        """Safely reset the URL switching state if it gets stuck"""
        self.url_switching = False
        self.url_switch_start_time = 0
        logger.info(f"Reset URL switching state for channel {self.channel_id}")
```

### Option 2: Automatische Korrektur

```bash
cd ~/Dispatcharr

# Backup erstellen
cp apps/proxy/ts_proxy/stream_manager.py apps/proxy/ts_proxy/stream_manager.py.backup

# Doppelten Code entfernen (Zeilen 1741-1767)
sed -i '1741,1767d' apps/proxy/ts_proxy/stream_manager.py

# Syntax prüfen
python3 -m py_compile apps/proxy/ts_proxy/stream_manager.py

# Wenn kein Fehler → OK!
echo "✅ Syntax OK"
```

### Option 3: Komplette Datei neu erstellen

Wenn die Korrektur zu kompliziert ist, kann ich dir die komplette korrekte Datei bereitstellen.

## Nach der Korrektur

```bash
# Docker Image neu bauen
cd ~/Dispatcharr
docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile .

# Container neu starten
cd docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml up -d
```

## Verifikation

```bash
# Logs prüfen
docker compose -f docker-compose.aio.yml logs -f

# Sollte KEINE IndentationError mehr zeigen
```

---

## Warum ist das passiert?

Beim Erstellen des Patches wurde die `_try_next_stream()` Methode komplett neu geschrieben. Beim Anwenden des Patches wurde aber die alte Version nicht vollständig entfernt, sodass doppelter Code entstand.

Die Zeilen 1741-1767 enthalten den alten Code, der nach dem `except Exception` Block nicht mehr sein sollte.

---

## Schnelle Lösung (Copy-Paste)

Wenn du die Datei manuell bearbeitest, lösche einfach ALLE Zeilen zwischen:

**LÖSCHEN VON:**
```python
            return False

                # IMPORTANT: Just update the URL...
```

**BIS (aber nicht einschließlich):**
```python
    # Add a new helper method to safely reset the URL switching state
    def _reset_url_switching_state(self):
```

Sodass es direkt so aussieht:
```python
            return False

    # Add a new helper method to safely reset the URL switching state
    def _reset_url_switching_state(self):
```

---

**Entschuldigung für den Fehler!** Der Patch hatte einen Merge-Konflikt, der nicht sauber aufgelöst wurde.
