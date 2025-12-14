"""
WebSocket routing for Predictive Failover System.

Requirements: 7.2, 7.5
"""

from django.urls import re_path
from .consumers import PredictiveFailoverConsumer

websocket_urlpatterns = [
    re_path(r'ws/predictive-failover/$', PredictiveFailoverConsumer.as_asgi()),
]
