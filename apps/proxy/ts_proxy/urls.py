from django.urls import path
from . import views
from . import health_api

app_name = 'ts_proxy'

urlpatterns = [
    path('stream/<str:channel_id>', views.stream_ts, name='stream'),
    path('change_stream/<str:channel_id>', views.change_stream, name='change_stream'),
    path('status', views.channel_status, name='channel_status'),
    path('status/<str:channel_id>', views.channel_status, name='channel_status_detail'),
    path('stop/<str:channel_id>', views.stop_channel, name='stop_channel'),
    path('stop_client/<str:channel_id>', views.stop_client, name='stop_client'),
    path('next_stream/<str:channel_id>', views.next_stream, name='next_stream'),
    
    # Health and monitoring endpoints
    path('health/failover/', health_api.failover_health, name='failover_health'),
    path('health/channel/<str:channel_id>/', health_api.channel_insights, name='channel_insights'),
    path('health/redis/', health_api.redis_stats, name='redis_stats'),
    path('health/clear-caches/', health_api.clear_caches, name='clear_caches'),
]
