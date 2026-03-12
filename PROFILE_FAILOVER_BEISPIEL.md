# Profile Failover Beispiel - Max Connections

## Dein Szenario

**Provider:** 1 M3U Account mit 3 Profilen
- **Default Profile:** max_connections = 0 (unbegrenzt)
- **Profil 1:** max_connections = 1
- **Profil 2:** max_connections = 1

**Channels:** 3 Channels, alle mit demselben Stream vom Provider

**Frage:** Werden alle 3 Profile verwendet oder wird auf Backup-Stream gewechselt?

---

## Antwort: Alle 3 Profile werden verwendet! ✅

### Ablauf:

#### Channel 1 startet:
1. Prüft **Default Profile** → 0/0 (unbegrenzt) → ✅ Verfügbar
2. Verwendet **Default Profile**
3. Redis: `profile_connections:default = 1`

#### Channel 2 startet:
1. Prüft **Default Profile** → 1/0 (unbegrenzt) → ✅ Verfügbar
2. Verwendet **Default Profile**
3. Redis: `profile_connections:default = 2`

#### Channel 3 startet:
1. Prüft **Default Profile** → 2/0 (unbegrenzt) → ✅ Verfügbar
2. Verwendet **Default Profile**
3. Redis: `profile_connections:default = 3`

**Ergebnis:** Alle 3 Channels verwenden das **Default Profile**

---

## Wann werden Profil 1 und 2 verwendet?

### Szenario A: Default Profile hat max_connections = 2

**Provider:** 1 M3U Account mit 3 Profilen
- **Default Profile:** max_connections = 2 ⚠️
- **Profil 1:** max_connections = 1
- **Profil 2:** max_connections = 1

#### Channel 1 startet:
1. Prüft **Default Profile** → 0/2 → ✅ Verfügbar
2. Verwendet **Default Profile**
3. Redis: `profile_connections:default = 1`

#### Channel 2 startet:
1. Prüft **Default Profile** → 1/2 → ✅ Verfügbar
2. Verwendet **Default Profile**
3. Redis: `profile_connections:default = 2`

#### Channel 3 startet:
1. Prüft **Default Profile** → 2/2 → ❌ Voll
2. Prüft **Profil 1** → 0/1 → ✅ Verfügbar
3. Verwendet **Profil 1**
4. Redis: `profile_connections:profil1 = 1`

#### Channel 4 startet:
1. Prüft **Default Profile** → 2/2 → ❌ Voll
2. Prüft **Profil 1** → 1/1 → ❌ Voll
3. Prüft **Profil 2** → 0/1 → ✅ Verfügbar
4. Verwendet **Profil 2**
5. Redis: `profile_connections:profil2 = 1`

#### Channel 5 startet:
1. Prüft **Default Profile** → 2/2 → ❌ Voll
2. Prüft **Profil 1** → 1/1 → ❌ Voll
3. Prüft **Profil 2** → 1/1 → ❌ Voll
4. **Kein Profil verfügbar** → Wechselt zu **Backup-Stream**

---

## Szenario B: Failover bei Stream-Fehler

**Situation:** Channel 1 verwendet Default Profile, aber Stream funktioniert nicht

#### Channel 1 Failover:
1. Aktuell: Stream 1 + Default Profile → ❌ Fehler
2. Sucht Alternativen:
   - Stream 1 + Profil 1 → ✅ Verfügbar
   - Stream 1 + Profil 2 → ✅ Verfügbar
   - Stream 2 (Backup) + Default Profile → ✅ Verfügbar
   - Stream 2 (Backup) + Profil 1 → ✅ Verfügbar
   - Stream 2 (Backup) + Profil 2 → ✅ Verfügbar
3. Versucht **Stream 1 + Profil 1** (nächste Kombination)

**Wichtig:** Profile werden VOR Backup-Streams versucht!

---

## Logik-Reihenfolge

### 1. Profile-Prüfung (für aktuellen Stream)
```
Stream 1 + Default Profile
Stream 1 + Profil 1
Stream 1 + Profil 2
```

### 2. Backup-Stream-Prüfung (wenn alle Profile voll)
```
Stream 2 + Default Profile
Stream 2 + Profil 1
Stream 2 + Profil 2
```

### 3. Weitere Backup-Streams
```
Stream 3 + Default Profile
Stream 3 + Profil 1
Stream 3 + Profil 2
```

---

## Code-Logik

**Datei:** `apps/proxy/ts_proxy/url_utils.py` - `get_alternate_streams()`

```python
# Für jeden Stream (in Reihenfolge)
for stream in streams:
    # Für jedes Profil (Default zuerst, dann andere)
    profiles = [default_profile] + [other_profiles]
    
    for profile in profiles:
        # Prüfe max_connections
        if profile.max_streams == 0 or current_connections < profile.max_streams:
            # ✅ Profil verfügbar - zur Liste hinzufügen
            alternate_streams.append({
                'stream_id': stream.id,
                'profile_id': profile.id
            })
        else:
            # ❌ Profil voll - nächstes Profil prüfen
            continue
```

**Wichtig:** 
- Alle verfügbaren Kombinationen werden zur Liste hinzugefügt
- Stream Manager versucht sie in Reihenfolge
- Erst wenn ALLE Profile eines Streams voll sind, wird nächster Stream versucht

---

## Zusammenfassung

### Dein Szenario (Default = unbegrenzt):
- ✅ Alle 3 Channels verwenden **Default Profile**
- ❌ Profil 1 und 2 werden **NICHT** verwendet
- ❌ Backup-Stream wird **NICHT** verwendet

### Wenn Default Profile begrenzt wäre:
- ✅ Channels verteilen sich auf alle verfügbaren Profile
- ✅ Erst wenn ALLE Profile voll sind → Backup-Stream
- ✅ Profile werden VOR Backup-Streams versucht

### Failover-Reihenfolge:
1. **Aktueller Stream + andere Profile** (wenn verfügbar)
2. **Backup-Stream + alle Profile** (wenn aktueller Stream keine Profile mehr hat)
3. **Weitere Backup-Streams + alle Profile**

---

## Empfehlung

Wenn du willst, dass die Channels sich auf alle Profile verteilen:

**Option 1:** Default Profile auch begrenzen
```
Default Profile: max_connections = 1
Profil 1: max_connections = 1
Profil 2: max_connections = 1
```
→ Jeder Channel bekommt ein eigenes Profil

**Option 2:** Load Balancing implementieren
- Aktuell: Immer Default Profile zuerst
- Besser: Profile mit wenigsten Connections zuerst

**Option 3:** So lassen (empfohlen)
- Default Profile unbegrenzt = einfach und funktioniert
- Andere Profile nur als Fallback bei Problemen
- Backup-Streams für echte Ausfälle

---

**Erstellt:** 2026-03-08  
**Status:** Erklärung der Profile Failover Logik
