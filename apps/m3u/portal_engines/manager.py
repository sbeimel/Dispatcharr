"""
UnifiedPortalEngine Manager - Orchestriert alle Portal-Engines.

Diese Datei importiert den Manager aus unified_portal_engine.py
für Rückwärtskompatibilität.
"""

# Import from unified_portal_engine for backward compatibility
from apps.m3u.unified_portal_engine import (
    UnifiedPortalEngine as _UnifiedPortalEngine,
    create_portal_client as _create_portal_client,
)

# Re-export with same names
UnifiedPortalEngine = _UnifiedPortalEngine
create_portal_client = _create_portal_client

__all__ = ['UnifiedPortalEngine', 'create_portal_client']
