from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import HDHRDeviceViewSet, DiscoverAPIView, LineupAPIView, LineupStatusAPIView, HDHRDeviceXMLAPIView, hdhr_dashboard_view

app_name = 'hdhr'

router = DefaultRouter()
router.register(r'devices', HDHRDeviceViewSet, basename='hdhr-device')

urlpatterns = [
    path('dashboard/', hdhr_dashboard_view, name='hdhr_dashboard'),
    path('', hdhr_dashboard_view, name='hdhr_dashboard'),
    path('<str:profile>/discover.json', DiscoverAPIView.as_view(), name='discover_with_profile'),
    path('discover.json', DiscoverAPIView.as_view(), name='discover_no_profile'),
    path('<str:profile>/lineup.json', LineupAPIView.as_view(), name='lineup_with_profile'),
    path('lineup.json', LineupAPIView.as_view(), name='lineup_no_profile'),
    path('<str:profile>/lineup_status.json', LineupStatusAPIView.as_view(), name='lineup_status_with_profile'),
    path('lineup_status.json', LineupStatusAPIView.as_view(), name='lineup_status_no_profile'),
    path('device.xml', HDHRDeviceXMLAPIView.as_view(), name='device_xml'),
]

urlpatterns += router.urls
