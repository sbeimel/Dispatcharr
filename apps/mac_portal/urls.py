from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from . import views
from apps.m3u.api.mac_portal_overview_api import MACPortalOverviewViewSet
from apps.m3u.mac_portal_models import MACPortalGlobalSettings, FailoverSettings

router = DefaultRouter()
router.register(r'portals', views.MACPortalViewSet, basename='macportal')
router.register(r'mac-addresses', views.MACAddressViewSet, basename='macaddress')

# Overview ViewSet
overview_viewset = MACPortalOverviewViewSet.as_view({
    'get': 'overview',
})
overview_statistics = MACPortalOverviewViewSet.as_view({
    'get': 'statistics',
})
overview_refresh = MACPortalOverviewViewSet.as_view({
    'post': 'refresh_status',
})


# ============== Simple Settings API Views (CSRF Exempt) ==============

class MACPortalSettingsView(APIView):
    """Simple API view for MAC Portal settings - CSRF exempt."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/mac-portal/settings/ - Get global settings."""
        settings = MACPortalGlobalSettings.get_settings()
        return Response({
            'connection_timeout': settings.connection_timeout,
            'read_timeout': settings.read_timeout,
            'max_retries': settings.max_retries,
            'retry_delay': settings.retry_delay,
            'exponential_backoff': settings.exponential_backoff,
            'mac_cooldown_failure': settings.mac_cooldown_failure,
            'mac_cooldown_block': settings.mac_cooldown_block,
            'portal_cooldown_error': settings.portal_cooldown_error,
            'token_refresh_threshold': settings.token_refresh_threshold,
            'cloudscraper_enabled': settings.cloudscraper_enabled,
            'vod_support_enabled': settings.vod_support_enabled,
            'series_support_enabled': settings.series_support_enabled,
            'epg_download_enabled': settings.epg_download_enabled,
            'short_epg_enabled': settings.short_epg_enabled,
            'picon_download_enabled': settings.picon_download_enabled,
            'tmdb_integration_enabled': settings.tmdb_integration_enabled,
            'stream_validation_enabled': settings.stream_validation_enabled,
            'multi_mac_rotation_enabled': settings.multi_mac_rotation_enabled,
            'token_auto_refresh_enabled': settings.token_auto_refresh_enabled,
            'debug_logging_enabled': settings.debug_logging_enabled,
            'ob2_2025_engine_enabled': settings.ob2_2025_engine_enabled,
            'portal_engine': settings.portal_engine,
            'parental_pin': settings.parental_pin,
        })
    
    def put(self, request):
        """PUT /api/mac-portal/settings/ - Update global settings."""
        return self._update_settings(request)
    
    def patch(self, request):
        """PATCH /api/mac-portal/settings/ - Partial update global settings."""
        return self._update_settings(request)
    
    def _update_settings(self, request):
        settings = MACPortalGlobalSettings.get_settings()
        data = request.data
        
        # Update all fields that are present in the request
        for field in ['connection_timeout', 'read_timeout', 'max_retries', 'retry_delay',
                      'mac_cooldown_failure', 'mac_cooldown_block', 'portal_cooldown_error',
                      'token_refresh_threshold', 'parental_pin', 'portal_engine']:
            if field in data:
                setattr(settings, field, data[field])
        
        # Boolean fields
        for field in ['exponential_backoff', 'cloudscraper_enabled', 'vod_support_enabled',
                      'series_support_enabled', 'epg_download_enabled', 'short_epg_enabled',
                      'picon_download_enabled', 'tmdb_integration_enabled', 'stream_validation_enabled',
                      'multi_mac_rotation_enabled', 'token_auto_refresh_enabled', 'debug_logging_enabled',
                      'ob2_2025_engine_enabled']:
            if field in data:
                setattr(settings, field, bool(data[field]))
        
        settings.save()
        return self.get(request)


class MACPortalSettingsSaveView(MACPortalSettingsView):
    """Alias for settings save endpoint."""
    pass


class MACPortalSettingsResetView(APIView):
    """Reset settings to defaults."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        MACPortalGlobalSettings.objects.filter(pk=1).delete()
        MACPortalGlobalSettings.get_settings()  # Recreate with defaults
        return MACPortalSettingsView().get(request)


class FailoverSettingsView(APIView):
    """Simple API view for Failover settings - CSRF exempt."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """GET /api/mac-portal/failover-settings/ - Get failover settings."""
        settings = FailoverSettings.get_settings()
        return Response({
            'mac_failover_enabled': settings.mac_failover_enabled,
            'portal_failover_enabled': settings.portal_failover_enabled,
            'stream_failover_enabled': settings.stream_failover_enabled,
            'endpoint_failover_enabled': settings.endpoint_failover_enabled,
            'useragent_failover_enabled': settings.useragent_failover_enabled,
            'mac_max_attempts': settings.mac_max_attempts,
            'mac_selection_strategy': settings.mac_selection_strategy,
            'mac_cooldown_failure': settings.mac_cooldown_failure,
            'mac_cooldown_block': settings.mac_cooldown_block,
            'mac_auto_recovery_interval': settings.mac_auto_recovery_interval,
            'endpoint_priority': settings.endpoint_priority,
            'endpoint_timeout': settings.endpoint_timeout,
            'endpoint_cache_enabled': settings.endpoint_cache_enabled,
            'stream_validation_enabled': settings.stream_validation_enabled,
            'stream_validation_timeout': settings.stream_validation_timeout,
            'stream_max_retries': settings.stream_max_retries,
            'stream_retry_different_mac': settings.stream_retry_different_mac,
            'stream_retry_different_cmd': settings.stream_retry_different_cmd,
            'useragent_rotation_order': settings.useragent_rotation_order,
            'useragent_rotate_on_auth_failure': settings.useragent_rotate_on_auth_failure,
            'useragent_rotate_on_403': settings.useragent_rotate_on_403,
            'useragent_rotate_on_cloudflare': settings.useragent_rotate_on_cloudflare,
            'useragent_remember_successful': settings.useragent_remember_successful,
            'failover_priority': settings.failover_priority,
        })
    
    def put(self, request):
        """PUT /api/mac-portal/failover-settings/ - Update failover settings."""
        return self._update_settings(request)
    
    def patch(self, request):
        """PATCH /api/mac-portal/failover-settings/ - Partial update."""
        return self._update_settings(request)
    
    def _update_settings(self, request):
        settings = FailoverSettings.get_settings()
        data = request.data
        
        # Integer fields
        for field in ['mac_max_attempts', 'mac_cooldown_failure', 'mac_cooldown_block',
                      'mac_auto_recovery_interval', 'endpoint_timeout', 'stream_validation_timeout',
                      'stream_max_retries']:
            if field in data:
                setattr(settings, field, int(data[field]))
        
        # String fields
        for field in ['mac_selection_strategy']:
            if field in data:
                setattr(settings, field, data[field])
        
        # Boolean fields
        for field in ['mac_failover_enabled', 'portal_failover_enabled', 'stream_failover_enabled',
                      'endpoint_failover_enabled', 'useragent_failover_enabled', 'endpoint_cache_enabled',
                      'stream_validation_enabled', 'stream_retry_different_mac', 'stream_retry_different_cmd',
                      'useragent_rotate_on_auth_failure', 'useragent_rotate_on_403',
                      'useragent_rotate_on_cloudflare', 'useragent_remember_successful']:
            if field in data:
                setattr(settings, field, bool(data[field]))
        
        # JSON fields
        for field in ['endpoint_priority', 'useragent_rotation_order', 'failover_priority']:
            if field in data:
                setattr(settings, field, data[field])
        
        settings.save()
        return self.get(request)


app_name = 'mac_portal'

urlpatterns = [
    path('', include(router.urls)),
    
    # Settings Endpoints (CSRF exempt via APIView)
    path('settings/', csrf_exempt(MACPortalSettingsView.as_view()), name='settings'),
    path('settings/save/', csrf_exempt(MACPortalSettingsSaveView.as_view()), name='settings-save'),
    path('settings/reset/', csrf_exempt(MACPortalSettingsResetView.as_view()), name='settings-reset'),
    path('failover-settings/', csrf_exempt(FailoverSettingsView.as_view()), name='failover-settings'),
    
    # Overview Endpunkte
    path('overview/', overview_viewset, name='overview'),
    path('overview/statistics/', overview_statistics, name='overview-statistics'),
    path('overview/refresh-status/', overview_refresh, name='overview-refresh'),
    
    # Zusätzliche benutzerdefinierte Endpunkte
    path('portals/<int:pk>/refresh/', views.MACPortalViewSet.as_view({'post': 'refresh'}), name='portal-refresh'),
    path('mac-addresses/bulk-refresh/', views.MACAddressViewSet.as_view({'post': 'bulk_refresh'}), name='mac-bulk-refresh'),
    
    # Statistik-Endpunkt
    path('portals/stats/', views.MACPortalViewSet.as_view({'get': 'stats'}), name='portal-stats'),
]
