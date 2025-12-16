# Dispatcharr 0.14.0 - Code Analysis Report

## 1. Projektübersicht

### Architektur
- **Backend**: Django 4.x mit Django REST Framework
- **Frontend**: React mit Vite
- **Datenbank**: PostgreSQL (via Django ORM)
- **Cache/Queue**: Redis (für Pub/Sub, Caching, Celery)
- **Task Queue**: Celery
- **Streaming**: FFmpeg, Streamlink

### Hauptkomponenten
| Komponente | Pfad | Beschreibung |
|------------|------|--------------|
| TS Proxy | `apps/proxy/ts_proxy/` | Kernfunktionalität für Stream-Proxying |
| M3U Management | `apps/m3u/` | M3U Account, MAC Portal Integration |
| Channels | `apps/channels/` | Channel Management |
| EPG | `apps/epg/` | Electronic Program Guide |
| VOD | `apps/vod/` | Video on Demand |

---

## 2. Identifizierte Probleme

### 2.1 Bare Except Clauses (Code Smell - Hoch)

**Problem**: 30+ Stellen mit `except:` ohne spezifische Exception-Typen. Dies kann Bugs verstecken und macht Debugging schwierig.

**Betroffene Dateien**:
- `core/serializers.py:52`
- `core/utils.py:113`
- `core/redis_pubsub.py:145, 162`
- `apps/proxy/ts_proxy/stream_manager.py:1123`
- `apps/proxy/ts_proxy/server.py:1339`
- `apps/m3u/mac_portal_client.py:46, 77`
- `apps/m3u/tasks.py:3001`
- `apps/m3u/api/mac_portal_overview_api.py:106, 124, 157, 226, 252, 277, 361, 390`
- `apps/epg/tasks.py:1123, 1366, 1372, 1694`

**Empfehlung**: Ersetzen durch spezifische Exceptions:
```python
# Schlecht
except:
    pass

# Besser
except (ValueError, TypeError) as e:
    logger.warning(f"Expected error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

### 2.2 TODO/FIXME Kommentare (Unvollständige Implementierungen)

| Datei | Zeile | Beschreibung |
|-------|-------|--------------|
| `apps/channels/models.py` | 342 | `@TODO: honor stream's stream profile` |
| `apps/proxy/ts_proxy/views.py` | 555 | `@TODO: support multiple outputs` |
| `apps/m3u/api/mac_portal_overview_api.py` | 259, 265 | Activity Level & Watchdog Timeout nicht implementiert |

### 2.3 Potenzielle Race Conditions

**Bereich**: `apps/proxy/ts_proxy/stream_manager.py`

Die `StreamManager` Klasse verwendet mehrere Threads:
- Health Monitor Thread
- Stderr Reader Thread
- HTTP Reader Thread

**Potenzielle Probleme**:
1. `self.running` Flag wird ohne Lock gesetzt/gelesen
2. `self.connected` Status kann zwischen Threads inkonsistent sein
3. `self.url_switching` State kann stuck werden (bereits mit Timeout behandelt)

### 2.4 Duplizierter Code

**MAC Portal Client Dateien**:
- `mac_portal_client.py`
- `mac_portal_client_extended.py`
- `portal_client_extensions.py`

Diese Dateien haben überlappende Funktionalität und sollten konsolidiert werden.

### 2.5 Fehlende Tests

**Bereiche ohne ausreichende Tests**:
- `apps/m3u/failover_manager.py`
- `apps/m3u/mac_rotation_manager.py`
- `apps/m3u/token_manager.py`
- `apps/proxy/ts_proxy/failover_utils.py`

---

## 3. Abhängigkeiten

### Kritische Abhängigkeiten
```
stream_manager.py
    ├── failover_utils.py
    │   ├── M3UAccount (models)
    │   ├── M3UAccountProfile (models)
    │   └── M3UAccountMac (models)
    └── mac_portal_client.py
        └── cloudscraper (optional)
```

### Zirkuläre Import-Risiken
- `apps/m3u/models.py` ↔ `apps/channels/models.py`
- `apps/proxy/ts_proxy/` ↔ `apps/m3u/`

---

## 4. Empfohlene Maßnahmen

### Priorität 1 (Kritisch)
1. [x] ~~Bare except Clauses durch spezifische Exceptions ersetzen~~ ✅ **ERLEDIGT**
2. [ ] Thread-Safety in StreamManager verbessern (Locks hinzufügen)
3. [ ] Unit Tests für Failover-Logik schreiben

### Priorität 2 (Wichtig)
4. [ ] MAC Portal Client Dateien konsolidieren
5. [ ] TODO Kommentare abarbeiten oder als Issues tracken
6. [ ] Logging verbessern (strukturiertes Logging)

### Priorität 3 (Nice-to-have)
7. [ ] Type Hints hinzufügen
8. [ ] Docstrings vervollständigen
9. [ ] Integration Tests für kritische Pfade

---

## 5. Durchgeführte Fixes

### Session 1 - Bare Except Fixes (Initial)

| Datei | Änderung |
|-------|----------|
| `core/serializers.py:52` | `except:` → `except (ValueError, TypeError):` |
| `apps/proxy/ts_proxy/url_utils.py:22` | `except:` → `except (ValueError, Channel.DoesNotExist):` |
| `apps/proxy/ts_proxy/server.py:1339` | `except:` → `except (ValueError, Channel.DoesNotExist):` mit zusätzlichem Try-Block |
| `apps/m3u/mac_portal_client.py:46,77` | `except:` → `except Exception as e:` mit Logging |

### Session 2 - Bare Except Fixes (Vollständig - 14.12.2025)

**Alle verbleibenden bare except Stellen wurden gefixt:**

| Datei | Änderung |
|-------|----------|
| `dispatcharr/celery.py:24` | `except:` → `except (IOError, OSError):` |
| `dispatcharr/consumers.py:35` | `except:` → `except Exception:` |
| `core/utils.py:113` | `except:` → `except Exception:` |
| `core/redis_pubsub.py:145,162` | `except:` → `except Exception:` |
| `core/api_views.py:133` | `except:` → `except (ValueError, TypeError):` |
| `apps/m3u/api/mac_portal_overview_api.py` | 8 Stellen gefixt mit spezifischen Exceptions |
| `apps/m3u/tasks.py:3001` | `except:` → `except M3UAccount.DoesNotExist:` |
| `apps/proxy/vod_proxy/views.py` | 3 Stellen gefixt mit spezifischen Exceptions |
| `apps/proxy/vod_proxy/multi_worker_connection_manager.py:648` | `except:` → `except (OSError, AttributeError):` |
| `apps/proxy/ts_proxy/stream_manager.py:1123` | `except:` → `except Exception:` |
| `apps/proxy/ts_proxy/http_streamer.py` | 4 Stellen gefixt mit `OSError` oder `Exception` |
| `apps/proxy/ts_proxy/stream_generator.py:150` | `except:` → `except (ValueError, UnicodeDecodeError):` |
| `apps/epg/tasks.py` | 4 Stellen gefixt mit spezifischen Exceptions |

**Status: ✅ ALLE bare except Stellen wurden behoben (0 verbleibend)**

---

## 6. Nächste Schritte

1. ~~**Bare Except Fix**: Automatisiertes Refactoring der except-Klauseln~~ ✅ **ERLEDIGT**
2. **Test Coverage**: pytest-cov Report generieren
3. **Linting**: flake8/pylint Report erstellen
4. **Thread-Safety**: Locks in StreamManager hinzufügen
5. **Unit Tests**: Für kritische Failover-Logik
