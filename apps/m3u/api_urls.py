from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    M3UAccountViewSet,
    M3UFilterViewSet,
    ServerGroupViewSet,
    RefreshM3UAPIView,
    RefreshSingleM3UAPIView,
    RefreshAccountInfoAPIView,
    UserAgentViewSet,
    M3UAccountProfileViewSet,
)
from .api.mac_portal_api import get_mac_portal_urls, get_mac_management_urls
from .api.clear_auto_cache_api import clear_auto_cache, get_auto_cache_status
from .api.clear_engine_cache_api import clear_engine_cache, get_engine_cache
from .api.failover_test_api import get_failover_test_urls

app_name = "m3u"

router = DefaultRouter()
router.register(r"accounts", M3UAccountViewSet, basename="m3u-account")
router.register(
    r"accounts\/(?P<account_id>\d+)\/profiles",
    M3UAccountProfileViewSet,
    basename="m3u-account-profiles",
)
router.register(
    r"accounts\/(?P<account_id>\d+)\/filters",
    M3UFilterViewSet,
    basename="m3u-filters",
)
router.register(r"server-groups", ServerGroupViewSet, basename="server-group")

urlpatterns = [
    path("refresh/", RefreshM3UAPIView.as_view(), name="m3u_refresh"),
    path(
        "refresh/<int:account_id>/",
        RefreshSingleM3UAPIView.as_view(),
        name="m3u_refresh_single",
    ),
    path(
        "refresh-account-info/<int:profile_id>/",
        RefreshAccountInfoAPIView.as_view(),
        name="m3u_refresh_account_info",
    ),
]

# Add MAC Portal Import API endpoints (Task 8)
urlpatterns += get_mac_portal_urls()
urlpatterns += get_mac_management_urls()

# Clear AUTO Cache API endpoints
urlpatterns += [
    path('clear-auto-cache/<int:account_id>/', clear_auto_cache, name='clear-auto-cache'),
    path('clear-auto-cache/<int:account_id>/status/', get_auto_cache_status, name='auto-cache-status'),
]

# Engine Cache API endpoints
urlpatterns += [
    path('engine-cache/', get_engine_cache, name='engine-cache-get'),
    path('engine-cache/clear/', clear_engine_cache, name='engine-cache-clear'),
    path('clear-engine-cache/<int:account_id>/', clear_engine_cache, name='clear-engine-cache'),
    path('test-auto-mode/<int:account_id>/', clear_auto_cache, name='test-auto-mode'),
]

# Failover Test API endpoints
urlpatterns += get_failover_test_urls()

urlpatterns += router.urls
