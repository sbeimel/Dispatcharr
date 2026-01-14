# 🔍 FINALE CHECKLISTE - Dispatcharr Enhancements

## Patch-Dateien (12 Dateien)

### Backend (9 Dateien)
1. ✅ `apps/proxy/config.py` - MAX_RETRIES, neue Settings
2. ✅ `apps/m3u/models.py` - proxy CharField
3. ✅ `core/models.py` - build_command mit proxy Parameter
4. ✅ `apps/m3u/serializers.py` - proxy in fields
5. ✅ `apps/proxy/ts_proxy/stream_manager.py` - Profile Failover + Proxy
6. ✅ `apps/proxy/ts_proxy/url_utils.py` - get_stream_info_for_profile
7. ✅ `apps/output/views.py` - Basic Auth
8. ✅ `apps/proxy/ts_proxy/config_helper.py` - failover_grace_period
9. ⚠️ `apps/m3u/migrations/0019_m3uaccount_proxy.py` - Migration (muss erstellt werden)

### Frontend (4 Dateien)
10. ✅ `frontend/src/components/forms/M3U.jsx` - proxy Input
11. ✅ `frontend/src/constants.js` - neue PROXY_SETTINGS_OPTIONS
12. ✅ `frontend/src/components/forms/settings/ProxySettingsForm.jsx` - neue Felder (2x im Patch)
13. ⚠️ `frontend/src/utils/forms/settings/ProxySettingsFormUtils.js` - FEHLT IM PATCH!

---

## Prüfung wird durchgeführt...
