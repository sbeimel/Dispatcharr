"""
STB Profil V1 - Dispatcharr Plugin

Live TV Integration für STB/Stalker-basierte IPTV-Portale.
Unterstützt MAC-Rotation via Profile für Failover.
"""

__version__ = "1.0.0"
__author__ = "StiniStinson"
__description__ = "STB Profil V1 - Live TV Integration mit Profile-Management für Dispatcharr"

from .plugin import Plugin, STBClient

# Celery Tasks (optional)
try:
    from .tasks import auto_update_live_tv, CELERY_BEAT_SCHEDULE
except ImportError:
    # Falls Celery nicht verfügbar ist
    auto_update_live_tv = None
    CELERY_BEAT_SCHEDULE = {}

__all__ = [
    'Plugin',
    'STBClient',
    'auto_update_live_tv',
    'CELERY_BEAT_SCHEDULE'
]
