"""
Models for the Proxy app.

This module imports models from submodules to make them discoverable by Django.
"""

# Import Predictive Failover models
from apps.proxy.ts_proxy.predictive.models import (
    FailurePattern,
    PredictiveFailoverEvent,
    StreamPredictiveSettings,
)

__all__ = [
    'FailurePattern',
    'PredictiveFailoverEvent',
    'StreamPredictiveSettings',
]
