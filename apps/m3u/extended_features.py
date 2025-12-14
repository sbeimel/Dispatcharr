"""
Extended Features for MAC Portal
Requirements: 15-21, 29, 34-36
"""

import re
import unicodedata
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models


class FavoritesManager:
    """
    Manages channel and VOD favorites.
    Requirements: 15.1, 15.2, 15.3, 15.4
    """
    
    def __init__(self, account_id: int):
        self.account_id = account_id
        self._favorites_cache = None
    
    def add_favorite(self, item_id: str, item_type: str = 'channel') -> bool:
        """Add item to favorites."""
        from .mac_portal_models import MACFavorite
        
        favorite, created = MACFavorite.objects.get_or_create(
            m3u_account_id=self.account_id,
            item_id=item_id,
            item_type=item_type,
        )
        self._favorites_cache = None
        return created
    
    def remove_favorite(self, item_id: str, item_type: str = 'channel') -> bool:
        """Remove item from favorites."""
        from .mac_portal_models import MACFavorite
        
        deleted, _ = MACFavorite.objects.filter(
            m3u_account_id=self.account_id,
            item_id=item_id,
            item_type=item_type,
        ).delete()
        self._favorites_cache = None
        return deleted > 0
    
    def is_favorite(self, item_id: str, item_type: str = 'channel') -> bool:
        """Check if item is a favorite."""
        favorites = self.get_favorites(item_type)
        return item_id in favorites
    
    def get_favorites(self, item_type: str = 'channel') -> Set[str]:
        """Get all favorite item IDs of a type."""
        from .mac_portal_models import MACFavorite
        
        return set(MACFavorite.objects.filter(
            m3u_account_id=self.account_id,
            item_type=item_type,
        ).values_list('item_id', flat=True))


class RecentlyWatchedManager:
    """
    Manages recently watched items.
    Requirements: 16.1, 16.2, 16.3, 16.4
    """
    
    MAX_ENTRIES = 28
    MIN_WATCH_TIME = 120  # 2 minutes in seconds
    
    def __init__(self, account_id: int):
        self.account_id = account_id
    
    def add_watched(self, item_id: str, item_type: str, watch_duration: int = 0) -> bool:
        """Add item to recently watched if watched long enough."""
        if watch_duration < self.MIN_WATCH_TIME:
            return False
        
        from .mac_portal_models import MACRecentlyWatched
        
        # Update or create entry
        entry, created = MACRecentlyWatched.objects.update_or_create(
            m3u_account_id=self.account_id,
            item_id=item_id,
            item_type=item_type,
            defaults={'watched_at': timezone.now()}
        )
        
        # Trim old entries
        self._trim_entries()
        return True
    
    def remove_watched(self, item_id: str, item_type: str) -> bool:
        """Remove item from recently watched."""
        from .mac_portal_models import MACRecentlyWatched
        
        deleted, _ = MACRecentlyWatched.objects.filter(
            m3u_account_id=self.account_id,
            item_id=item_id,
            item_type=item_type,
        ).delete()
        return deleted > 0
    
    def get_recently_watched(self, item_type: Optional[str] = None) -> List[Dict]:
        """Get recently watched items, newest first."""
        from .mac_portal_models import MACRecentlyWatched
        
        queryset = MACRecentlyWatched.objects.filter(
            m3u_account_id=self.account_id
        ).order_by('-watched_at')
        
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        return list(queryset.values('item_id', 'item_type', 'watched_at'))
    
    def _trim_entries(self):
        """Remove oldest entries if over limit."""
        from .mac_portal_models import MACRecentlyWatched
        
        entries = MACRecentlyWatched.objects.filter(
            m3u_account_id=self.account_id
        ).order_by('-watched_at')
        
        if entries.count() > self.MAX_ENTRIES:
            ids_to_keep = entries[:self.MAX_ENTRIES].values_list('id', flat=True)
            MACRecentlyWatched.objects.filter(
                m3u_account_id=self.account_id
            ).exclude(id__in=list(ids_to_keep)).delete()


class SortingManager:
    """
    Manages sorting options for channels and categories.
    Requirements: 17.1, 17.2, 17.3, 17.4
    """
    
    SORT_OPTIONS = ['a-z', 'z-a', 'original', 'added']
    
    @staticmethod
    def sort_items(items: List[Dict], sort_by: str, name_field: str = 'name') -> List[Dict]:
        """Sort items by specified criteria."""
        if sort_by == 'a-z':
            return sorted(items, key=lambda x: x.get(name_field, '').lower())
        elif sort_by == 'z-a':
            return sorted(items, key=lambda x: x.get(name_field, '').lower(), reverse=True)
        elif sort_by == 'original':
            return sorted(items, key=lambda x: x.get('number', x.get('position', 0)))
        elif sort_by == 'added':
            return sorted(items, key=lambda x: x.get('added', x.get('created_at', '')), reverse=True)
        return items


class SearchFilter:
    """
    Manages search and filter functionality.
    Requirements: 18.1, 18.2, 18.3, 18.4
    """
    
    @staticmethod
    def search_items(items: List[Dict], search_term: str, fields: List[str] = None) -> List[Dict]:
        """Filter items by search term (case-insensitive)."""
        if not search_term:
            return items
        
        search_lower = search_term.lower()
        fields = fields or ['name', 'title']
        
        return [
            item for item in items
            if any(
                search_lower in str(item.get(field, '')).lower()
                for field in fields
            )
        ]
    
    @staticmethod
    def filter_by_category(items: List[Dict], category_id: str) -> List[Dict]:
        """Filter items by category."""
        if not category_id:
            return items
        return [
            item for item in items
            if str(item.get('category_id', item.get('genre_id', ''))) == str(category_id)
        ]


class ParentalControl:
    """
    Manages parental control and PIN protection.
    Requirements: 19.1, 19.2, 19.3, 19.4
    """
    
    ADULT_KEYWORDS = ['adult', '18+', 'xxx', 'erotic', 'porn', 'sex', 'mature']
    PIN_VALIDITY_MINUTES = 15
    
    def __init__(self, account_id: int):
        self.account_id = account_id
        self._pin_verified_until = None
    
    def is_adult_category(self, category_name: str) -> bool:
        """Check if category name contains adult keywords."""
        name_lower = category_name.lower()
        return any(keyword in name_lower for keyword in self.ADULT_KEYWORDS)
    
    def verify_pin(self, entered_pin: str) -> bool:
        """Verify PIN and grant temporary access."""
        from .mac_portal_models import MACPortalGlobalSettings
        
        try:
            settings = MACPortalGlobalSettings.objects.first()
            if settings and settings.parental_pin == entered_pin:
                self._pin_verified_until = timezone.now() + timedelta(minutes=self.PIN_VALIDITY_MINUTES)
                return True
        except Exception:
            pass
        return False
    
    def is_access_granted(self) -> bool:
        """Check if PIN was recently verified."""
        if self._pin_verified_until is None:
            return False
        return timezone.now() < self._pin_verified_until
    
    def filter_adult_content(self, items: List[Dict], include_adult: bool = False) -> List[Dict]:
        """Filter out adult content unless access is granted."""
        if include_adult or self.is_access_granted():
            return items
        
        return [
            item for item in items
            if not self.is_adult_category(item.get('name', item.get('category_name', '')))
        ]


class HiddenCategoriesManager:
    """
    Manages hidden categories.
    Requirements: 20.1, 20.2, 20.3, 20.4
    """
    
    def __init__(self, account_id: int):
        self.account_id = account_id
    
    def hide_category(self, category_id: str) -> bool:
        """Mark category as hidden."""
        from .mac_portal_models import MACHiddenCategory
        
        _, created = MACHiddenCategory.objects.get_or_create(
            m3u_account_id=self.account_id,
            category_id=category_id,
        )
        return created
    
    def unhide_category(self, category_id: str) -> bool:
        """Remove category from hidden list."""
        from .mac_portal_models import MACHiddenCategory
        
        deleted, _ = MACHiddenCategory.objects.filter(
            m3u_account_id=self.account_id,
            category_id=category_id,
        ).delete()
        return deleted > 0
    
    def get_hidden_categories(self) -> Set[str]:
        """Get all hidden category IDs."""
        from .mac_portal_models import MACHiddenCategory
        
        return set(MACHiddenCategory.objects.filter(
            m3u_account_id=self.account_id
        ).values_list('category_id', flat=True))
    
    def filter_hidden(self, categories: List[Dict]) -> List[Dict]:
        """Filter out hidden categories."""
        hidden = self.get_hidden_categories()
        return [
            cat for cat in categories
            if str(cat.get('id', cat.get('category_id', ''))) not in hidden
        ]


class GenreFilter:
    """
    Filters genres/categories by country code.
    Requirements: 29.1, 29.2, 29.3, 29.4
    """
    
    def __init__(self, country_code: str = '', excluded_keywords: List[str] = None):
        self.country_code = country_code.upper() if country_code else ''
        self.excluded_keywords = [kw.lower() for kw in (excluded_keywords or [])]
    
    def filter_genres(self, genres: List[Dict], include_adult: bool = False) -> List[Dict]:
        """Filter genres by country code and excluded keywords."""
        if not self.country_code and not self.excluded_keywords:
            return genres
        
        adult_keywords = ParentalControl.ADULT_KEYWORDS
        filtered = []
        
        for genre in genres:
            name = genre.get('name', genre.get('title', '')).lower()
            
            # Check excluded keywords
            if any(kw in name for kw in self.excluded_keywords):
                continue
            
            # Include adult content if enabled
            if include_adult and any(kw in name for kw in adult_keywords):
                filtered.append(genre)
                continue
            
            # Filter by country code prefix
            if self.country_code:
                genre_name_upper = genre.get('name', '').upper()
                if genre_name_upper.startswith(self.country_code) or f'|{self.country_code}' in genre_name_upper:
                    filtered.append(genre)
            else:
                filtered.append(genre)
        
        return filtered


class SuperscriptNormalizer:
    """
    Normalizes superscript characters in channel names.
    Requirements: 36.1, 36.2, 36.3, 36.4
    """
    
    SUPERSCRIPT_MAP = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
        'ᵃ': 'a', 'ᵇ': 'b', 'ᶜ': 'c', 'ᵈ': 'd', 'ᵉ': 'e',
        'ᶠ': 'f', 'ᵍ': 'g', 'ʰ': 'h', 'ⁱ': 'i', 'ʲ': 'j',
        'ᵏ': 'k', 'ˡ': 'l', 'ᵐ': 'm', 'ⁿ': 'n', 'ᵒ': 'o',
        'ᵖ': 'p', 'ʳ': 'r', 'ˢ': 's', 'ᵗ': 't', 'ᵘ': 'u',
        'ᵛ': 'v', 'ʷ': 'w', 'ˣ': 'x', 'ʸ': 'y', 'ᶻ': 'z',
        'ᴬ': 'A', 'ᴮ': 'B', 'ᴰ': 'D', 'ᴱ': 'E', 'ᴳ': 'G',
        'ᴴ': 'H', 'ᴵ': 'I', 'ᴶ': 'J', 'ᴷ': 'K', 'ᴸ': 'L',
        'ᴹ': 'M', 'ᴺ': 'N', 'ᴼ': 'O', 'ᴾ': 'P', 'ᴿ': 'R',
        'ᵀ': 'T', 'ᵁ': 'U', 'ⱽ': 'V', 'ᵂ': 'W',
    }
    
    @classmethod
    def normalize(cls, text: str) -> str:
        """Normalize superscript characters to regular characters."""
        if not text:
            return text
        
        result = text
        for sup, normal in cls.SUPERSCRIPT_MAP.items():
            result = result.replace(sup, normal)
        
        # Also normalize using Unicode NFKC
        result = unicodedata.normalize('NFKC', result)
        return result
    
    @classmethod
    def normalize_items(cls, items: List[Dict], fields: List[str] = None) -> List[Dict]:
        """Normalize superscript characters in specified fields."""
        fields = fields or ['name', 'title']
        
        for item in items:
            for field in fields:
                if field in item and isinstance(item[field], str):
                    item[field] = cls.normalize(item[field])
        
        return items


class StreamTypeManager:
    """
    Manages stream type switching.
    Requirements: 21.1, 21.2, 21.3, 21.4
    """
    
    STREAM_TYPES = ['iptv', 'dvb', 'gstreamer', 'exteplayer']
    
    def __init__(self, account_id: int):
        self.account_id = account_id
        self._current_type_index = 0
    
    def get_current_type(self) -> str:
        """Get current stream type."""
        return self.STREAM_TYPES[self._current_type_index]
    
    def cycle_type(self) -> str:
        """Cycle to next stream type."""
        self._current_type_index = (self._current_type_index + 1) % len(self.STREAM_TYPES)
        return self.get_current_type()
    
    def set_type(self, stream_type: str) -> bool:
        """Set specific stream type."""
        if stream_type in self.STREAM_TYPES:
            self._current_type_index = self.STREAM_TYPES.index(stream_type)
            return True
        return False


class TrailerSupport:
    """
    Manages VOD trailer playback.
    Requirements: 34.1, 34.2, 34.3, 34.4
    """
    
    YOUTUBE_PATTERN = re.compile(
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    )
    
    @classmethod
    def extract_youtube_id(cls, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        if not url:
            return None
        match = cls.YOUTUBE_PATTERN.search(url)
        return match.group(1) if match else None
    
    @classmethod
    def get_youtube_embed_url(cls, video_id: str) -> str:
        """Get YouTube embed URL."""
        return f'https://www.youtube.com/embed/{video_id}'
    
    @classmethod
    def has_trailer(cls, item: Dict) -> bool:
        """Check if VOD item has a trailer."""
        trailer_url = item.get('trailer_url', item.get('trailer', ''))
        return bool(trailer_url)
    
    @classmethod
    def get_trailer_url(cls, item: Dict) -> Optional[str]:
        """Get playable trailer URL."""
        trailer_url = item.get('trailer_url', item.get('trailer', ''))
        if not trailer_url:
            return None
        
        # Check if it's a YouTube URL
        youtube_id = cls.extract_youtube_id(trailer_url)
        if youtube_id:
            return cls.get_youtube_embed_url(youtube_id)
        
        return trailer_url
