"""
EStalker Strategy - Enigma2 Stalker Client Style.

Diese Datei importiert die Strategie aus unified_portal_engine.py
für Rückwärtskompatibilität.
"""

# Import from unified_portal_engine for backward compatibility
# TODO: Move the actual implementation here in a future refactoring
from apps.m3u.unified_portal_engine import EStalkerStrategy as _EStalkerStrategy

# Re-export with same name
EStalkerStrategy = _EStalkerStrategy

__all__ = ['EStalkerStrategy']
