# Patch Notes für v0.19.0 Enhancements

## Wichtige Hinweise zur Patch-Anwendung

### Große Dateien mit komplexen Änderungen

Die folgenden Dateien haben umfangreiche Änderungen, die schwer als klassisches Patch darzustellen sind:

1. **apps/proxy/ts_proxy/stream_manager.py**
   - Zeilen geändert: ~150 Zeilen
   - Hauptänderungen:
     - `tried_combinations` statt nur `tried_stream_ids`
     - `current_profile_id` Tracking hinzugefügt
     - Proxy-Support in `_establish_transcode_connection()`
     - Proxy-Support in `_establish_http_connection()`
     - Komplette Neuimplementierung von `_try_next_stream()`
     - Profile ID Tracking in `update_url()`

2. **apps/proxy/ts_proxy/url_utils.py**
   - Zeilen geändert: ~100 Zeilen
   - Hauptänderungen:
     - `get_alternate_streams()` erweitert für Profile Failover
     - Neue Funktion `get_stream_info_for_profile()` hinzugefügt
     - Alle Profile werden zurückgegeben, nicht nur eines

### Empfohlene Anwendung

**Option A: Automatische Anwendung (empfohlen)**
```bash
cd Dispatcharr-0.19.0/
bash ../apply_dispatcharr_enhancements_v0.19.0.sh
```

**Option B: Manuelle Anwendung**
```bash
# 1. Patch anwenden (kleinere Dateien)
cd Dispatcharr-0.19.0/
patch -p1 < ../dispatcharr_enhancements_v0.19.0.patch

# 2. Große Dateien manuell anpassen
# Siehe INSTALLATION_COMPLETE_v0.19.0.md für Details
```

**Option C: Git-basierte Anwendung**
```bash
# Wenn du Git verwendest:
cd Dispatcharr-0.19.0/
git init
git add .
git commit -m "Original v0.19.0"

# Dann Änderungen aus unserem Enhanced Repo mergen
```

## Detaillierte Änderungen

### stream_manager.py - Hauptänderungen

#### 1. Initialisierung (Zeile ~65-95)
```python
# ALT:
self.current_stream_id = stream_id
self.tried_stream_ids = set()

# NEU:
self.current_stream_id = stream_id
self.current_profile_id = None
self.tried_combinations = set()  # Track (stream_id, profile_id)
self.tried_stream_ids = set()  # Keep for backward compatibility

# + Profile ID aus Redis laden
profile_id_bytes = buffer.redis_client.hget(metadata_key, "m3u_profile")
if profile_id_bytes:
    self.current_profile_id = int(profile_id_bytes.decode('utf-8'))
```

#### 2. Transcode Connection (Zeile ~490-520)
```python
# NEU: Proxy-Support hinzugefügt
proxy = None
try:
    channel_obj = Channel.objects.get(uuid=self.channel_id)
    if hasattr(self, 'current_stream_id') and self.current_stream_id:
        stream = Stream.objects.get(id=self.current_stream_id)
        if hasattr(stream, 'm3u_account') and stream.m3u_account:
            proxy = stream.m3u_account.proxy
            if proxy:
                logger.info(f"Using proxy {proxy} for channel {self.channel_id}")
except Exception as e:
    logger.debug(f"Could not get proxy for channel {self.channel_id}: {e}")

# ALT:
self.transcode_cmd = stream_profile.build_command(self.url, self.user_agent)

# NEU:
self.transcode_cmd = stream_profile.build_command(self.url, self.user_agent, proxy)
```

#### 3. HTTP Connection (Zeile ~915-945)
```python
# NEU: Proxy-Support hinzugefügt (gleiche Logik wie Transcode)
proxy = None
# ... (siehe oben)

# ALT:
self.http_reader = HTTPStreamReader(
    url=self.url,
    user_agent=self.user_agent,
    chunk_size=self.chunk_size
)

# NEU:
self.http_reader = HTTPStreamReader(
    url=self.url,
    user_agent=self.user_agent,
    chunk_size=self.chunk_size,
    proxy=proxy  # Pass proxy to HTTPStreamReader
)
```

#### 4. Update URL (Zeile ~1100-1130)
```python
# NEU: Profile ID Tracking
if m3u_profile_id:
    old_profile_id = self.current_profile_id
    self.current_profile_id = m3u_profile_id
    logger.info(f"Updated profile ID from {old_profile_id} to {m3u_profile_id}")
    
    # Add combination to tried_combinations
    if stream_id and m3u_profile_id:
        self.tried_combinations.add((stream_id, m3u_profile_id))
```

#### 5. Try Next Stream (Zeile ~1585-1700)
```python
# KOMPLETT NEU IMPLEMENTIERT für Profile Failover

# ALT: Nur Streams durchprobieren
alternate_streams = get_alternate_streams(self.channel_id, self.current_stream_id)
untried_streams = [s for s in alternate_streams if s['stream_id'] not in self.tried_stream_ids]

# NEU: Stream/Profile-Kombinationen durchprobieren
alternate_streams = get_alternate_streams(self.channel_id, self.current_stream_id, self.current_profile_id)
untried = [s for s in alternate_streams if (s['stream_id'], s['profile_id']) not in self.tried_combinations]

# NEU: Neue Funktion verwenden
from .url_utils import get_stream_info_for_profile
stream_info = get_stream_info_for_profile(self.channel_id, stream_id, profile_id)

# NEU: Profile ID tracken
self.current_profile_id = profile_id
self.tried_combinations.add((stream_id, profile_id))
```

### url_utils.py - Hauptänderungen

#### 1. get_alternate_streams() (Zeile ~316-450)
```python
# ALT: Nur ein Profile pro Stream
def get_alternate_streams(channel_id: str, current_stream_id: Optional[int] = None)

# NEU: Alle Profile pro Stream
def get_alternate_streams(channel_id: str, current_stream_id: Optional[int] = None, current_profile_id: Optional[int] = None)

# ALT: Skip current stream
if current_stream_id and stream.id == current_stream_id:
    continue

# NEU: Skip current stream+profile combination
for profile in profiles:
    if current_stream_id and stream.id == current_stream_id and current_profile_id and profile.id == current_profile_id:
        continue

# ALT: Nur ein Profile zurückgeben
selected_profile = None
for profile in profiles:
    # ... check availability
    selected_profile = profile
    break

if selected_profile:
    alternate_streams.append({
        'stream_id': stream.id,
        'profile_id': selected_profile.id,
        'name': stream.name
    })

# NEU: Alle verfügbaren Profile zurückgeben
for profile in profiles:
    # ... check availability
    alternate_streams.append({
        'stream_id': stream.id,
        'profile_id': profile.id,
        'name': stream.name
    })
```

#### 2. get_stream_info_for_profile() (NEU, Zeile ~550-600)
```python
# KOMPLETT NEUE FUNKTION
def get_stream_info_for_profile(channel_id: str, stream_id: int, m3u_profile_id: int) -> dict:
    """
    Build URL/User-Agent/Transcode for a fixed combination of Stream + M3U profile.
    Return schema compatible with get_stream_info_for_switch(...).
    """
    try:
        channel = get_stream_object(channel_id)
        stream = get_object_or_404(Stream, pk=stream_id)
        m3u_profile = get_object_or_404(M3UAccountProfile, pk=m3u_profile_id)
        
        m3u_account = m3u_profile.m3u_account
        user_agent = m3u_account.get_user_agent().user_agent
        
        # Generate URL using the specific profile's transformation
        input_url = stream.url
        stream_url = transform_url(input_url, m3u_profile.search_pattern, m3u_profile.replace_pattern)
        
        # Get transcode info from the channel's stream profile
        stream_profile = channel.get_stream_profile()
        transcode = not (stream_profile.is_proxy() or stream_profile is None)
        profile_value = stream_profile.id
        
        return {
            'url': stream_url,
            'user_agent': user_agent,
            'transcode': transcode,
            'stream_profile': profile_value,
            'stream_id': stream_id,
            'm3u_profile_id': m3u_profile_id
        }
    except Exception as e:
        logger.error(f"Error in get_stream_info_for_profile: {e}", exc_info=True)
        return {'error': f'Error: {str(e)}'}
```

## Frontend-Änderungen

### M3U.jsx
```javascript
// Zeile ~56: initialValues
proxy: '',

// Zeile ~100: setValues
proxy: m3uAccount.proxy || '',

// Zeile ~270: Nach server_url TextInput
<TextInput
  style={{ width: '100%' }}
  id="proxy"
  name="proxy"
  label="HTTP Proxy"
  placeholder="http://proxy:8080"
  description="HTTP proxy URL for streams (optional)"
  {...form.getInputProps('proxy')}
  key={form.key('proxy')}
/>
```

### constants.js
```javascript
// Zeile ~33: PROXY_SETTINGS_OPTIONS erweitern
max_retries: {
  label: 'Max Retries',
  description: 'Maximum number of retry attempts before switching streams',
},
url_switch_timeout: {
  label: 'URL Switch Timeout (seconds)',
  description: 'Maximum time allowed for stream switching operations',
},
max_stream_switches: {
  label: 'Max Stream Switches',
  description: 'Maximum number of stream/profile combinations to try before giving up',
},
connection_timeout: {
  label: 'Connection Timeout (seconds)',
  description: 'Maximum time to wait for initial connection to a stream',
},
```

### ProxySettingsForm.jsx
```javascript
// Zeile ~23: isNumericField erweitern
'max_retries',
'url_switch_timeout',
'max_stream_switches',
'connection_timeout',

// Zeile ~35: getNumericFieldMax erweitern
: key === 'max_retries'
  ? 10
  : key === 'url_switch_timeout'
    ? 60
    : key === 'max_stream_switches'
      ? 500
      : key === 'connection_timeout'
        ? 60
        : 60;
```

### ProxySettingsFormUtils.js
```javascript
// Zeile ~11: getProxySettingDefaults erweitern
max_retries: 2,
url_switch_timeout: 20,
max_stream_switches: 200,
connection_timeout: 10,
```

## Migration

```python
# apps/m3u/migrations/0020_add_proxy_field.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('m3u', '0019_m3uaccount_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='m3uaccount',
            name='proxy',
            field=models.CharField(
                blank=True,
                help_text='HTTP proxy URL for streams (e.g., http://proxy:8080)',
                max_length=500,
                null=True
            ),
        ),
    ]
```

## Zusammenfassung

- **14 Dateien geändert**
- **~500 Zeilen hinzugefügt**
- **~50 Zeilen entfernt**
- **1 neue Migration**
- **1 neue Funktion** (get_stream_info_for_profile)

Alle Änderungen sind rückwärtskompatibel und haben sinnvolle Defaults!
