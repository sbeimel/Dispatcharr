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
from .api.failover_test_api import get_failover_test_urls
from .api.simple_benchmark_api import run_benchmark, get_benchmark_result, clear_benchmark

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

# Add Failover Test API endpoints
urlpatterns += get_failover_test_urls()

# Simple Benchmark API endpoints (standalone, guaranteed to work)
urlpatterns += [
    path('benchmark/<int:account_id>/run/', run_benchmark, name='benchmark-run'),
    path('benchmark/<int:account_id>/result/', get_benchmark_result, name='benchmark-result'),
    path('benchmark/<int:account_id>/clear/', clear_benchmark, name='benchmark-clear'),
]

urlpatterns += router.urls
