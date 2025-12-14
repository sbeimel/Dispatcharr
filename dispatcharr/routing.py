from django.urls import path, re_path
from dispatcharr.consumers import MyWebSocketConsumer
from apps.m3u.consumers.failover_test_consumer import FailoverTestConsumer

websocket_urlpatterns = [
    path("ws/", MyWebSocketConsumer.as_asgi()),
    re_path(r"ws/failover-test/$", FailoverTestConsumer.as_asgi()),
]
