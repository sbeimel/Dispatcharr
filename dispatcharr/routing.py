from django.urls import path
from dispatcharr.consumers import MyWebSocketConsumer

websocket_urlpatterns = [
    path("ws/", MyWebSocketConsumer.as_asgi()),
]
