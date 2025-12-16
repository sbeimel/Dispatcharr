"""
AllinOne Strategy - Best-of-All kombiniert alle Techniken.

Diese Datei importiert die Strategie aus unified_portal_engine.py
für Rückwärtskompatibilität.
"""

# Import from unified_portal_engine for backward compatibility
# TODO: Move the actual implementation here in a future refactoring
from apps.m3u.unified_portal_engine import AllinOneStrategy as _AllinOneStrategy

# Re-export with same name
AllinOneStrategy = _AllinOneStrategy

__all__ = ['AllinOneStrategy']
