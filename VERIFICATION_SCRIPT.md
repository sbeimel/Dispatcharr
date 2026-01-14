# 🔍 VOLLSTÄNDIGE VERIFIKATION

## Prüfung läuft...

### Backend-Dateien:
1. apps/proxy/config.py
2. apps/m3u/models.py
3. core/models.py
4. apps/m3u/serializers.py
5. apps/proxy/ts_proxy/stream_manager.py
6. apps/proxy/ts_proxy/url_utils.py
7. apps/output/views.py
8. apps/proxy/ts_proxy/config_helper.py

### Frontend-Dateien:
9. frontend/src/components/forms/M3U.jsx
10. frontend/src/constants.js
11. frontend/src/components/forms/settings/ProxySettingsForm.jsx
12. frontend/src/utils/forms/settings/ProxySettingsFormUtils.js

## Kritische Checks:
- [ ] tried_combinations in __init__
- [ ] current_profile_id in __init__
- [ ] get_stream_info_for_profile import
- [ ] _try_next_stream verwendet tried_combinations
- [ ] get_alternate_streams hat current_profile_id Parameter
- [ ] build_command hat proxy Parameter
- [ ] Proxy wird an build_command übergeben
