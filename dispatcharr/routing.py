from django.urls import path, re_path
from dispatcharr.consumers import MyWebSocketConsumer

websocket_urlpatterns = [
    path("ws/", MyWebSocketConsumer.as_asgi()),
    # Failover Test WebSocket removed - service was missing
    # Manual failover test (kill_stream) still works
]
