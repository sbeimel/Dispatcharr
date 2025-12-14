"""
MAC Portal Integration Module
Integrates all MAC Portal components into a unified interface.
Requirements: 41.1, 41.2, 41.3, 41.4
"""

from typing import Dict, Optional, List, Any
from .token_manager import TokenManager
from .mac_rotation_manager import MACRotationManager
from .failover_manager import FailoverManager
from .portal_type_detector import PortalTypeDetector, PortalType, XtreamCredentialExtractor
from .multi_portal_support import HandshakeStrategySelector, HandshakeResult
from .ob2_2025_engine import OB2_2025Engine, ErrorPatternRecognizer, HandshakeType
from .extended_features import (
    FavoritesManager, RecentlyWatchedManager, SortingManager,
    SearchFilter, ParentalControl, HiddenCategoriesManager,
    GenreFilter, SuperscriptNormalizer, TrailerSupport
)
from .xtream_api_compat import XtreamAPICompat


class MACPortalIntegration:
    """
    Unified interface for all MAC Portal functionality.
    """
    
    def __init__(self, account_id: int, use_ob2_2025: bool = False):
        self.account_id = account_id
        self.use_ob2_2025 = use_ob2_2025
        
        # Core managers
        self.token_manager = TokenManager(account_id)
        self.mac_manager = MACRotationManager(account_id)
        self.failover_manager = FailoverManager(account_id)
        
        # Extended features
        self.favorites = FavoritesManager(account_id)
        self.recently_watched = RecentlyWatchedManager(account_id)
        self.hidden_categories = HiddenCategoriesManager(account_id)
        self.parental_control = ParentalControl(account_id)
        
        # OB2_2025 engine (optional)
        self.ob2_engine = OB2_2025Engine(enabled=use_ob2_2025) if use_ob2_2025 else None
        
        # Portal client (set after initialization)
        self._portal_client = None
        self._detected_portal_type = None
    
    def set_portal_client(self, client):
        """Set the portal client instance."""
        self._portal_client = client
    
    def detect_portal_type(self, portal_url: str, mac: str, response_data: Dict = None) -> PortalType:
        """Detect portal type from URL or response."""
        detector = PortalTypeDetector(portal_url, mac)
        
        if response_data:
            result = detector.detect_from_response(response_data)
        else:
            result = detector.detect_from_url()
        
        self._detected_portal_type = result.portal_type
        return result.portal_type
    
    def perform_handshake(self, portal_url: str, mac: str, session) -> HandshakeResult:
        """Perform handshake with automatic strategy selection."""
        if self.use_ob2_2025 and self.ob2_engine:
            # Use OB2_2025 handshake order
            handshake_order = self.ob2_engine.get_handshake_order(portal_url)
            
            for handshake_type in handshake_order:
                try:
                    strategy = HandshakeStrategySelector.get_strategy(
                        handshake_type.value, portal_url, mac
                    )
                    result = strategy.perform_handshake(session)
                    
                    if result.success:
                        self.ob2_engine.cache_successful_handshake(portal_url, handshake_type)
                        return result
                except Exception:
                    continue
            
            return HandshakeResult(success=False, error='All OB2_2025 handshake strategies failed')
        else:
            # Use standard auto-detection
            return HandshakeStrategySelector.auto_detect_and_handshake(portal_url, mac, session)[0]
    
    def get_channels_with_features(self, genre_id: str = None, **kwargs) -> List[Dict]:
        """Get channels with all extended features applied."""
        if not self._portal_client:
            return []
        
        channels = self._portal_client.get_channels(genre_id=genre_id)
        
        # Apply superscript normalization
        channels = SuperscriptNormalizer.normalize_items(channels)
        
        # Apply sorting
        sort_by = kwargs.get('sort_by', 'original')
        channels = SortingManager.sort_items(channels, sort_by)
        
        # Apply search filter
        search_term = kwargs.get('search')
        if search_term:
            channels = SearchFilter.search_items(channels, search_term)
        
        # Mark favorites
        favorites = self.favorites.get_favorites('channel')
        for channel in channels:
            channel['is_favorite'] = str(channel.get('id', '')) in favorites
        
        return channels
    
    def get_categories_with_features(self, content_type: str = 'live', **kwargs) -> List[Dict]:
        """Get categories with all extended features applied."""
        if not self._portal_client:
            return []
        
        if content_type == 'live':
            categories = self._portal_client.get_genres()
        elif content_type == 'vod':
            categories = self._portal_client.get_vod_categories()
        elif content_type == 'series':
            categories = self._portal_client.get_series_categories()
        else:
            categories = []
        
        # Filter hidden categories
        categories = self.hidden_categories.filter_hidden(categories)
        
        # Apply parental control
        include_adult = kwargs.get('include_adult', False)
        categories = self.parental_control.filter_adult_content(categories, include_adult)
        
        # Apply country filter
        country_code = kwargs.get('country_code', '')
        if country_code:
            genre_filter = GenreFilter(country_code)
            categories = genre_filter.filter_genres(categories, include_adult)
        
        return categories
    
    def get_vod_with_features(self, category_id: str = None, **kwargs) -> Dict:
        """Get VOD items with all extended features applied."""
        if not self._portal_client:
            return {'data': [], 'total': 0}
        
        vod_data = self._portal_client.get_vod_items(category_id=category_id)
        items = vod_data.get('data', [])
        
        # Apply superscript normalization
        items = SuperscriptNormalizer.normalize_items(items)
        
        # Apply sorting
        sort_by = kwargs.get('sort_by', 'original')
        items = SortingManager.sort_items(items, sort_by)
        
        # Apply search filter
        search_term = kwargs.get('search')
        if search_term:
            items = SearchFilter.search_items(items, search_term)
        
        # Mark favorites
        favorites = self.favorites.get_favorites('vod')
        for item in items:
            item['is_favorite'] = str(item.get('id', '')) in favorites
            item['has_trailer'] = TrailerSupport.has_trailer(item)
        
        return {'data': items, 'total': len(items)}
    
    def handle_error(self, error_text: str, http_status: int = None) -> Dict:
        """Handle error with pattern recognition and recommended action."""
        error_type = ErrorPatternRecognizer.recognize(error_text, http_status)
        action = ErrorPatternRecognizer.get_failover_action(error_type)
        
        return {
            'error_type': error_type.value,
            'action': action['action'],
            'cooldown_minutes': action['cooldown_minutes'],
            'should_retry': action['retry'],
        }
    
    def get_xtream_api(self) -> Optional[XtreamAPICompat]:
        """Get Xtream API compatibility layer."""
        if self._portal_client:
            return XtreamAPICompat(self._portal_client)
        return None
    
    def extract_xtream_credentials(self, stream_url: str) -> Optional[Dict]:
        """Extract Xtream credentials from stream URL."""
        return XtreamCredentialExtractor.extract_credentials(stream_url)
    
    def get_status(self) -> Dict:
        """Get current integration status."""
        return {
            'account_id': self.account_id,
            'use_ob2_2025': self.use_ob2_2025,
            'detected_portal_type': self._detected_portal_type.value if self._detected_portal_type else None,
            'token_valid': self.token_manager.is_token_valid() if hasattr(self.token_manager, 'is_token_valid') else None,
            'available_macs': self.mac_manager.get_available_mac_count() if hasattr(self.mac_manager, 'get_available_mac_count') else None,
        }


def create_integration(account_id: int) -> MACPortalIntegration:
    """Factory function to create MAC Portal integration."""
    from .mac_portal_models import MACPortalGlobalSettings
    
    try:
        settings = MACPortalGlobalSettings.get_settings()
        use_ob2_2025 = settings.ob2_2025_engine_enabled
    except Exception:
        use_ob2_2025 = False
    
    return MACPortalIntegration(account_id, use_ob2_2025=use_ob2_2025)
