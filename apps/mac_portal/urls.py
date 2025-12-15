from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'portals', views.MACPortalViewSet, basename='macportal')
router.register(r'mac-addresses', views.MACAddressViewSet, basename='macaddress')

app_name = 'mac_portal'

urlpatterns = [
    path('', include(router.urls)),
    
    # Zusätzliche benutzerdefinierte Endpunkte
    path('portals/<int:pk>/refresh/', views.MACPortalViewSet.as_view({'post': 'refresh'}), name='portal-refresh'),
    path('mac-addresses/bulk-refresh/', views.MACAddressViewSet.as_view({'post': 'bulk_refresh'}), name='mac-bulk-refresh'),
    
    # Statistik-Endpunkt
    path('portals/stats/', views.MACPortalViewSet.as_view({'get': 'stats'}), name='portal-stats'),
]
