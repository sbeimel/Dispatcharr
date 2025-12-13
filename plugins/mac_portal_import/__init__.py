"""
MAC Portal Import Plugin für Dispatcharr

Ermöglicht das schnelle Importieren von Stalker/STB Portal-Daten mit automatischer
Profil-Erstellung für MAC-Failover.
"""

__version__ = "1.0.0"
__author__ = "Dispatcharr"
__description__ = "MAC Portal Import mit automatischer Profil-Erstellung"

from .plugin import Plugin
from .utils import MACNormalizer, MACValidator, StreamLinkGenerator, ChannelFetcher

__all__ = [
    'Plugin',
    'MACNormalizer',
    'MACValidator', 
    'StreamLinkGenerator',
    'ChannelFetcher'
]
