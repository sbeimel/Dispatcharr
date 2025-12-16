"""
OB2_2025 Strategy - Erweiterte Prüflogik mit api_signature 263.

Diese Datei importiert die Strategie aus unified_portal_engine.py
für Rückwärtskompatibilität.
"""

# Import from unified_portal_engine for backward compatibility
# TODO: Move the actual implementation here in a future refactoring
from apps.m3u.unified_portal_engine import OB2_2025Strategy as _OB2_2025Strategy

# Re-export with same name
OB2_2025Strategy = _OB2_2025Strategy

__all__ = ['OB2_2025Strategy']
