"""
Portal Engines Registry - Zentrale Verwaltung aller Portal-Engines.

Jede Engine ist in einer eigenen Datei und erbt von BasePortalStrategy.
Die Registry ermöglicht einfaches Hinzufügen neuer Engines.

ARCHITEKTUR:
- BasePortalStrategy (base.py): Abstrakte Basisklasse mit gemeinsamer Logik
- Jede Engine (macattack.py, istb.py, etc.): Eigene Implementierung
- Registry (__init__.py): Factory-Funktionen und Engine-Verwaltung

VERWENDUNG:
    from apps.m3u.portal_engines import create_engine, PortalEngine
    
    engine = create_engine('macattack', portal_url, mac)
    result = engine.perform_handshake()
    channels = engine.get_all_channels()
"""

import logging
from typing import Dict, Type, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# Base imports
from .base import BasePortalStrategy, PortalIdentity, HandshakeResult

# Lazy imports für Engines (werden bei Bedarf geladen)
_ENGINE_CLASSES: Dict[str, Type[BasePortalStrategy]] = {}


class PortalEngine(Enum):
    """Verfügbare Portal-Engines."""
    MACATTACK = "macattack"      # MacAttack v4.7.6 Style - BEST
    ISTB = "istb"                # iSTB iOS Emulator Style
    OB2_2025 = "ob2_2025"        # OB2_2025 Prüflogik
    BOXPIRATE = "boxpirate"      # BoxPirate Dreambox
    ESTALKER = "estalker"        # EStalker Enigma2
    MACREPLAY = "macreplay"      # Standard MacReplayXC
    ALLINONE = "allinone"        # Best-of-All kombiniert
    AUTO = "auto"                # Automatische Erkennung


# Engine priority order for AUTO mode (best performers first)
AUTO_ENGINE_ORDER = [
    'macattack',   # Best: Fast, reliable, 14k+ channels
    'istb',        # Good: iOS emulator style
    'ob2_2025',    # Good: Alternative handshake
    'boxpirate',   # Good: Dreambox style
    'estalker',    # Good: Enigma2 style
    'macreplay',   # Standard: Original MacReplay
    'allinone',    # Fallback: Tries everything
]


def _load_engine_class(engine_name: str) -> Optional[Type[BasePortalStrategy]]:
    """Lazy-load engine class by name."""
    if engine_name in _ENGINE_CLASSES:
        return _ENGINE_CLASSES[engine_name]
    
    try:
        if engine_name == 'macattack':
            from .macattack import MacAttackStrategy
            _ENGINE_CLASSES[engine_name] = MacAttackStrategy
        elif engine_name == 'istb':
            from .istb import iSTBStrategy
            _ENGINE_CLASSES[engine_name] = iSTBStrategy
        elif engine_name == 'ob2_2025':
            from .ob2_2025 import OB2_2025Strategy
            _ENGINE_CLASSES[engine_name] = OB2_2025Strategy
        elif engine_name == 'boxpirate':
            from .boxpirate import BoxPirateStrategy
            _ENGINE_CLASSES[engine_name] = BoxPirateStrategy
        elif engine_name == 'estalker':
            from .estalker import EStalkerStrategy
            _ENGINE_CLASSES[engine_name] = EStalkerStrategy
        elif engine_name == 'macreplay':
            from .macreplay import MacReplayStrategy
            _ENGINE_CLASSES[engine_name] = MacReplayStrategy
        elif engine_name == 'allinone':
            from .allinone import AllinOneStrategy
            _ENGINE_CLASSES[engine_name] = AllinOneStrategy
        else:
            logger.warning(f"Unknown engine: {engine_name}")
            return None
        
        return _ENGINE_CLASSES.get(engine_name)
    except ImportError as e:
        logger.error(f"Failed to import engine {engine_name}: {e}")
        return None


def get_engine_class(engine_name: str) -> Optional[Type[BasePortalStrategy]]:
    """Get engine class by name."""
    return _load_engine_class(engine_name.lower())


def create_engine(
    engine_name: str,
    portal_url: str,
    mac: str,
    user_agent: str = 'MAG250',
    timeout: int = 10,
    proxy: Optional[str] = None,
    use_cloudscraper: Optional[bool] = None
) -> Optional[BasePortalStrategy]:
    """
    Factory function to create an engine instance.
    
    Args:
        engine_name: Name of the engine (macattack, istb, etc.)
        portal_url: Portal URL
        mac: MAC address
        user_agent: User-Agent preset or custom string
        timeout: Request timeout in seconds
        proxy: Optional proxy URL
        use_cloudscraper: Use cloudscraper for Cloudflare bypass
    
    Returns:
        Engine instance or None if engine not found
    """
    engine_class = get_engine_class(engine_name)
    if not engine_class:
        return None
    
    identity = PortalIdentity(mac=mac)
    
    return engine_class(
        portal_url=portal_url,
        identity=identity,
        user_agent=user_agent,
        timeout=timeout,
        proxy=proxy,
        use_cloudscraper=use_cloudscraper
    )


def get_available_engines() -> List[str]:
    """Get list of available engine names."""
    return [e.value for e in PortalEngine if e != PortalEngine.AUTO]


def get_engine_info() -> Dict[str, Dict]:
    """Get info about all available engines."""
    info = {}
    for engine_name in get_available_engines():
        engine_class = get_engine_class(engine_name)
        if engine_class:
            info[engine_name] = {
                'name': getattr(engine_class, 'NAME', engine_name),
                'description': getattr(engine_class, 'DESCRIPTION', ''),
            }
    return info
