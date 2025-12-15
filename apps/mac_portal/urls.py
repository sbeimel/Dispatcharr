from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from apps.m3u.api.mac_portal_overview_api import MACPortalOverviewViewSet

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

app_name = 'mac_portal'

urlpatterns = [
    path('', include(router.urls)),
    
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
