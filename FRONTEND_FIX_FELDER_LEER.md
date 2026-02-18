# ✅ FRONTEND FIX: Felder sind leer

## Problem

Die 5 neuen Proxy Settings Felder waren im Frontend leer, auch nach Docker-Rebuild.

## Ursache

**Zwei Frontend-Probleme:**

### Problem 1: Initial Values waren leer
```javascript
// VORHER (FALSCH):
export const getProxySettingsFormInitialValues = () => {
  return Object.keys(PROXY_SETTINGS_OPTIONS).reduce((acc, key) => {
    acc[key] = '';  // ← LEER!
    return acc;
  }, {});
};
```

### Problem 2: API-Werte wurden nicht mit Defaults gemerged
```javascript
// VORHER (FALSCH):
useEffect(() => {
  if (settings) {
    if (settings['proxy_settings']?.value) {
      proxySettingsForm.setValues(settings['proxy_settings'].value);
      // ← Wenn API null/undefined zurückgibt, bleiben Felder leer!
    }
  }
}, [settings]);
```

## Lösung

### Fix 1: Initial Values nutzen Defaults
```javascript
// NACHHER (KORREKT):
export const getProxySettingsFormInitialValues = () => {
  // Use defaults instead of empty strings
  return getProxySettingDefaults();
};
```

### Fix 2: API-Werte mit Defaults mergen
```javascript
// NACHHER (KORREKT):
useEffect(() => {
  if (settings) {
    if (settings['proxy_settings']?.value) {
      // Merge API values with defaults to ensure all fields have values
      const defaults = getProxySettingDefaults();
      const mergedValues = { ...defaults, ...settings['proxy_settings'].value };
      proxySettingsForm.setValues(mergedValues);
    } else {
      // If no settings from API, use defaults
      proxySettingsForm.setValues(getProxySettingDefaults());
    }
  }
}, [settings]);
```

## Geänderte Dateien

1. ✅ `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js`
   - `getProxySettingsFormInitialValues()` nutzt jetzt `getProxySettingDefaults()`

2. ✅ `frontend/src/components/forms/settings/ProxySettingsForm.jsx`
   - `useEffect` merged API-Werte mit Defaults
   - Fallback auf Defaults wenn keine API-Werte

3. ✅ `dispatcharr_enhancements_v0.19.0.patch`
   - Beide Änderungen im Patch enthalten

## Anwendung

```bash
cd ~/Dispatcharr

# Docker Image neu bauen (Frontend wird neu kompiliert)
docker build -t sbeimel/dispatcharr:0.19.0 -f docker/Dockerfile .

# Container neu starten
cd docker
docker compose -f docker-compose.aio.yml down
docker compose -f docker-compose.aio.yml up -d

# Warten bis bereit
sleep 30

# Browser öffnen
# http://dispatcharr:8000/settings/proxy
```

## Verifikation

### 1. Felder sollten jetzt Werte haben

Beim Öffnen der Seite sollten alle Felder **sofort** Werte haben:
- Max Retries: **2**
- URL Switch Timeout: **20**
- Max Stream Switches: **200**
- Connection Timeout: **10**
- Failover Grace Period: **20**

### 2. Browser-Cache leeren

Falls die Felder immer noch leer sind:
- **Hard Reload:** Strg+Shift+R (Chrome/Edge) oder Strg+F5 (Firefox)
- **Oder:** Browser-Cache komplett leeren
- **Oder:** Inkognito-Modus testen

### 3. Browser DevTools prüfen

Öffne Browser DevTools (F12) → Console:
- Sollte **keine Fehler** zeigen
- Sollte **keine Warnungen** über fehlende Werte zeigen

### 4. Werte ändern und speichern

1. Ändere einen Wert (z.B. Max Retries auf 3)
2. Klicke "Save"
3. Lade Seite neu (F5)
4. Wert sollte **3** sein (gespeichert)

## Warum hat das nicht funktioniert?

### Problem-Kette:

1. **Backend** gibt Defaults zurück → ✅ OK
2. **API** gibt Defaults zurück → ✅ OK
3. **Frontend** empfängt Defaults → ✅ OK
4. **Frontend** initialisiert Form mit **leeren Strings** → ❌ PROBLEM
5. **Frontend** überschreibt nur wenn API **nicht-null** Werte hat → ❌ PROBLEM
6. **Ergebnis:** Felder bleiben leer → ❌ PROBLEM

### Lösung:

1. **Frontend** initialisiert Form mit **Defaults** → ✅ FIX
2. **Frontend** merged API-Werte mit **Defaults** → ✅ FIX
3. **Ergebnis:** Felder haben immer Werte → ✅ OK

## Technische Details

### Warum Merge statt Replace?

```javascript
// FALSCH (Replace):
proxySettingsForm.setValues(settings['proxy_settings'].value);
// Problem: Wenn API nur 3 von 10 Feldern zurückgibt, bleiben 7 leer

// RICHTIG (Merge):
const mergedValues = { ...defaults, ...settings['proxy_settings'].value };
proxySettingsForm.setValues(mergedValues);
// Lösung: Alle 10 Felder haben Werte (Defaults + API-Overrides)
```

### Warum Initial Values = Defaults?

```javascript
// FALSCH:
initialValues: { max_retries: '' }
// Problem: Feld ist leer bis API antwortet

// RICHTIG:
initialValues: { max_retries: 2 }
// Lösung: Feld hat sofort einen Wert
```

## Nach dem Fix

**Alle 10 Proxy Settings sollten jetzt funktionieren:**

1. ✅ Buffering Timeout (15)
2. ✅ Buffering Speed (1.0)
3. ✅ Buffer Chunk TTL (60)
4. ✅ Channel Shutdown Delay (0)
5. ✅ Channel Initialization Grace Period (5)
6. ✅ **Max Retries (2)** ← NEU
7. ✅ **URL Switch Timeout (20)** ← NEU
8. ✅ **Max Stream Switches (200)** ← NEU
9. ✅ **Connection Timeout (10)** ← NEU
10. ✅ **Failover Grace Period (20)** ← NEU

---

**Status:** ✅ BEHOBEN

Frontend initialisiert jetzt alle Felder mit Defaults und merged API-Werte korrekt.
