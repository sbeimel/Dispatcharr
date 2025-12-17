from django.urls import path, include
from . import views as proxy_views

app_name = 'proxy'

urlpatterns = [
    path('ts/', include('apps.proxy.ts_proxy.urls')),
    path('hls/', include('apps.proxy.hls_proxy.urls')),
    path('vod/', include('apps.proxy.vod_proxy.urls')),
    # Failover test endpoints
    path('active-streams/', proxy_views.get_active_streams, name='active-streams'),
    path('kill-stream/<int:channel_id>/', proxy_views.kill_stream, name='kill-stream'),
    path('simulate-error/<int:channel_id>/', proxy_views.simulate_error, name='simulate-error'),
]