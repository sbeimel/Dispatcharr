"""
Portal Engines Package - Modulare Engine-Architektur für MAC/STB Portale.

Jede Engine ist in einer eigenen Datei für bessere Wartbarkeit.

Verfügbare Engines:
- MacReplayStrategy: Standard MacReplayXC (nutzt mac_portal_client.py)
- OB2_2025Strategy: OB2_2025 Prüflogik
- EStalkerStrategy: EStalker Enigma2 Style
- BoxPirateStrategy: BoxPirate Dreambox Style
- AllinOneStrategy: Kombiniert alle Strategien

Der UnifiedPortalEngine Manager orchestriert alle Engines.

HINWEIS: Die Implementierungen sind aktuell noch in unified_portal_engine.py.
Diese Package-Struktur ermöglicht schrittweises Refactoring.
"""

# Re-export everything from unified_portal_engine for backward compatibility
# This allows imports like: from apps.m3u.portal_engines import UnifiedPortalEngine
from apps.m3u.unified_portal_engine import (
    # Enums
    PortalEngine,
    
    # Base classes
    BasePortalStrategy,
    PortalIdentity,
    HandshakeResult,
    CLOUDSCRAPER_AVAILABLE,
    
    # Strategies
    MacReplayStrategy,
    OB2_2025Strategy,
    EStalkerStrategy,
    BoxPirateStrategy,
    AllinOneStrategy,
    
    # Manager
    UnifiedPortalEngine,
    create_portal_client,
)

# Export all public symbols
__all__ = [
    # Enums
    'PortalEngine',
    
    # Base classes
    'BasePortalStrategy',
    'PortalIdentity', 
    'HandshakeResult',
    'CLOUDSCRAPER_AVAILABLE',
    
    # Strategies
    'MacReplayStrategy',
    'OB2_2025Strategy',
    'EStalkerStrategy',
    'BoxPirateStrategy',
    'AllinOneStrategy',
    
    # Manager
    'UnifiedPortalEngine',
    'create_portal_client',
]
