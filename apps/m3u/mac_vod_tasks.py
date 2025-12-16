"""
MAC Portal VOD Tasks - Neu implementiert basierend auf MacReplayXC.

Einfache, direkte Logik wie in MacReplayXC-main/stb.py und app-docker.py:
1. Kategorien vom Portal laden (type=vod/series, action=get_categories)
2. In ChannelGroups speichern (wie MacReplayXC in vod_categories Tabelle)
3. Kategorien im Groups-Tab anzeigen mit group_type='vod_movie' oder 'vod_series'
"""

import logging
import re
import requests
from typing import Dict, List

from celery import shared_task
from django.utils import timezone

from .models import M3UAccount
from apps.channels.models import ChannelGroup, ChannelGroupM3UAccount

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions - Basierend auf MacReplayXC utils.py
# =============================================================================

def sanitize_name(name: str) -> str:
    """
    Sanitize category/channel name - basierend auf MacReplayXC sanitize_channel_name().
    
    Entfernt/ersetzt problematische Zeichen und normalisiert Whitespace.
    """
    if not name:
        return ""
    
    # Remove or replace problematic characters (like MacReplayXC)
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', str(name))
    
    # Normalize whitespace (multiple spaces -> single space)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Optional: Remove common decorative characters/emojis
    # Keep letters, numbers, spaces, and basic punctuation
    # sanitized = re.sub(r'[^\w\s\-.,()&]', '', sanitized, flags=re.UNICODE)
    
    return sanitized


# =============================================================================
# VOD Service - Direkte API-Aufrufe wie in MacReplayXC stb.py
# =============================================================================

class MACVodClient:
    """
    Einfacher VOD Client basierend auf MacReplayXC stb.py.
    
    Direkte API-Aufrufe ohne komplexe Abstraktion.
    """
    
    def __init__(self, portal_url: str, mac: str, token: str):
        self.portal_url = portal_url.rstrip('/')
        self.mac = mac
        self.token = token
        
        # Standard Headers wie in MacReplayXC
        self.headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C)",
            "Authorization": f"Bearer {token}",
        }
        
        # Standard Cookies wie in MacReplayXC
        self.cookies = {
            "mac": mac,
            "stb_lang": "en",
            "timezone": "Europe/London"
        }
    
    def _get_url(self) -> str:
        """Get portal endpoint URL."""
        if self.portal_url.endswith('.php'):
            return self.portal_url
        return f"{self.portal_url}/portal.php"
    
    def get_vod_items(self, category_id: str, page: int = 1) -> List[Dict]:
        """
        Get VOD items for a category - wie MacReplayXC getVodItems().
        
        API: type=vod&action=get_ordered_list&category={cat}&p={page}&JsHttpRequest=1-xml
        """
        params = {
            "type": "vod",
            "action": "get_ordered_list",
            "movie_id": "0",
            "season_id": "0",
            "episode_id": "0",
            "row": "0",
            "JsHttpRequest": "1-xml",
            "category": str(category_id),
            "sortby": "added",
            "fav": "0",
            "hd": "0",
            "not_ended": "0",
            "abc": "*",
            "genre": "*",
            "years": "*",
            "search": "",
            "p": str(page)
        }
        
        try:
            response = requests.get(
                self._get_url(),
                params=params,
                cookies=self.cookies,
                headers=self.headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if "js" in data:
                    js_data = data["js"]
                    if isinstance(js_data, dict):
                        # Try multiple possible data keys
                        for data_key in ["data", "items", "list", "movies", "vods"]:
                            if data_key in js_data:
                                items = js_data[data_key]
                                if isinstance(items, list):
                                    logger.info(f"Got {len(items)} VOD items for category {category_id}, page {page}")
                                    return items
            
            logger.warning(f"VOD items failed for category {category_id}: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error getting VOD items for category {category_id}: {e}")
        
        return []
    
    def get_series_items(self, category_id: str, page: int = 1) -> List[Dict]:
        """
        Get Series items for a category - wie MacReplayXC getSeriesItems().
        
        API: type=series&action=get_ordered_list&category={cat}&p={page}&JsHttpRequest=1-xml
        """
        params = {
            "type": "series",
            "action": "get_ordered_list",
            "movie_id": "0",
            "season_id": "0",
            "episode_id": "0",
            "row": "0",
            "JsHttpRequest": "1-xml",
            "category": str(category_id),
            "sortby": "added",
            "fav": "0",
            "hd": "0",
            "not_ended": "0",
            "abc": "*",
            "genre": "*",
            "years": "*",
            "search": "",
            "p": str(page)
        }
        
        try:
            response = requests.get(
                self._get_url(),
                params=params,
                cookies=self.cookies,
                headers=self.headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if "js" in data:
                    js_data = data["js"]
                    if isinstance(js_data, dict):
                        # Try multiple possible data keys
                        for data_key in ["data", "items", "list", "series"]:
                            if data_key in js_data:
                                items = js_data[data_key]
                                if isinstance(items, list):
                                    logger.info(f"Got {len(items)} Series items for category {category_id}, page {page}")
                                    return items
            
            logger.warning(f"Series items failed for category {category_id}: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error getting Series items for category {category_id}: {e}")
        
        return []
    
    def get_vod_categories(self) -> List[Dict]:
        """
        Get VOD categories - wie MacReplayXC getVodCategories().
        
        API: type=vod&action=get_categories&JsHttpRequest=1-xml
        """
        params = {
            "type": "vod",
            "action": "get_categories",
            "JsHttpRequest": "1-xml"
        }
        
        try:
            response = requests.get(
                self._get_url(),
                params=params,
                cookies=self.cookies,
                headers=self.headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if "js" in data:
                    categories = data["js"]
                    if isinstance(categories, list):
                        logger.info(f"Got {len(categories)} VOD categories")
                        return categories
            
            logger.warning(f"VOD categories failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error getting VOD categories: {e}")
        
        return []
    
    def get_series_categories(self) -> List[Dict]:
        """
        Get Series categories - wie MacReplayXC getSeriesCategories().
        
        API: type=series&action=get_categories&JsHttpRequest=1-xml
        """
        params = {
            "type": "series",
            "action": "get_categories",
            "JsHttpRequest": "1-xml"
        }
        
        try:
            response = requests.get(
                self._get_url(),
                params=params,
                cookies=self.cookies,
                headers=self.headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if "js" in data:
                    categories = data["js"]
                    if isinstance(categories, list):
                        logger.info(f"Got {len(categories)} Series categories")
                        return categories
            
            logger.warning(f"Series categories failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error getting Series categories: {e}")
        
        return []


# =============================================================================
# Helper Functions
# =============================================================================

def _get_mac_and_token(account) -> tuple:
    """
    Get MAC address and token for account.
    
    Returns:
        (mac_address, token) or (None, None) if failed
    """
    from apps.m3u.mac_portal_client import MacPortalClient
    
    # Get MAC address
    mac_address = None
    if hasattr(account, 'macs') and account.macs.exists():
        mac_obj = account.macs.filter(status__in=['valid', 'active', 'unknown']).first()
        if mac_obj:
            mac_address = mac_obj.address
    
    if not mac_address:
        mac_address = getattr(account, 'mac_address', None)
        if mac_address and ',' in mac_address:
            mac_address = mac_address.split(',')[0].strip()
    
    if not mac_address:
        logger.error(f"No MAC address for account {account.name}")
        return None, None
    
    # Do handshake to get token
    try:
        client = MacPortalClient(
            base_url=account.server_url,
            mac=mac_address,
            proxy=None
        )
        
        if not client.token:
            client.handshake()
        
        if not client.token:
            logger.error(f"Handshake failed for account {account.name}")
            return None, None
        
        return mac_address, client.token
        
    except Exception as e:
        logger.error(f"Error getting token for {account.name}: {e}")
        return None, None


def _save_vod_item(account, group: ChannelGroup, item: Dict, vod_type: str) -> str:
    """
    Save VOD item as Movie/Series - wie XC Accounts.
    
    Args:
        account: M3UAccount
        group: ChannelGroup (the category)
        item: VOD item data from portal
        vod_type: 'vod_movie' or 'vod_series'
    
    Returns: 'created', 'updated', 'skipped', or 'error'
    """
    from apps.vod.models import Movie, Series, VODCategory, M3UMovieRelation, M3USeriesRelation, VODLogo
    from apps.channels.models import Stream
    
    try:
        # Extract item data (field names vary by portal)
        item_id = item.get('id') or item.get('cmd', '').split('/')[-1]
        name = item.get('name') or item.get('title') or f"Item {item_id}"
        cmd = item.get('cmd', '')
        
        if not item_id or not cmd:
            logger.warning(f"VOD item missing id or cmd: {item}")
            return 'skipped'
        
        # Sanitize name
        name = sanitize_name(name)
        
        # Build stream URL
        if cmd.startswith('http'):
            stream_url = cmd
        else:
            base_url = account.server_url.rstrip('/')
            if not cmd.startswith('/'):
                cmd = '/' + cmd
            stream_url = f"{base_url}{cmd}"
        
        # Extract metadata
        logo_url = item.get('screenshot') or item.get('screenshot_uri') or item.get('poster') or item.get('logo') or ''
        description = item.get('description') or item.get('desc') or ''
        year_str = item.get('year') or item.get('releasedate') or ''
        genre = item.get('genre') or item.get('genre_str') or ''
        rating = item.get('rating') or item.get('rating_imdb') or ''
        duration_str = item.get('time') or item.get('duration') or item.get('length') or ''
        
        # Parse year
        year = None
        if year_str:
            try:
                year = int(str(year_str)[:4])  # Extract first 4 digits
            except (ValueError, TypeError):
                pass
        
        # Parse duration (convert to seconds)
        duration_secs = None
        if duration_str:
            try:
                # Duration can be in format "HH:MM:SS" or just seconds
                if ':' in str(duration_str):
                    parts = str(duration_str).split(':')
                    if len(parts) == 3:
                        duration_secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    elif len(parts) == 2:
                        duration_secs = int(parts[0]) * 60 + int(parts[1])
                else:
                    duration_secs = int(duration_str)
            except (ValueError, TypeError):
                pass
        
        # Get or create logo
        logo = None
        if logo_url:
            logo, _ = VODLogo.objects.get_or_create(
                url=logo_url,
                defaults={'name': name}
            )
        
        # Get or create VOD category (from ChannelGroup)
        portal_category_id = group.custom_properties.get('portal_category_id')
        category, _ = VODCategory.objects.get_or_create(
            name=group.name,
            defaults={
                'category_type': 'movie' if vod_type == 'vod_movie' else 'series',
                'custom_properties': {
                    'portal_category_id': portal_category_id,
                    'is_mac_category': True,
                }
            }
        )
        
        # Custom properties
        custom_props = {
            'portal_item_id': item_id,
            'portal_category_id': portal_category_id,
            'stream_url': stream_url,
            'cmd': cmd,
            'is_mac_vod': True,
        }
        
        # Create Movie or Series
        if vod_type == 'vod_series' or group.group_type == 'vod_series':
            # Create Series
            series, created = Series.objects.update_or_create(
                name=name,
                year=year,
                defaults={
                    'description': description,
                    'rating': rating,
                    'genre': genre,
                    'logo': logo,
                    'custom_properties': custom_props,
                }
            )
            
            # Create relation to M3U account and category
            M3USeriesRelation.objects.get_or_create(
                series=series,
                m3u_account=account,
                category=category,
                defaults={'custom_properties': {}}
            )
            
            # Also create a Stream for playback
            Stream.objects.update_or_create(
                m3u_account=account,
                url=stream_url,
                defaults={
                    'name': name,
                    'logo_url': logo_url,
                    'channel_group': group,
                    'custom_properties': {'vod_series_id': series.id, **custom_props},
                    'last_seen': timezone.now(),
                }
            )
        else:
            # Create Movie
            movie, created = Movie.objects.update_or_create(
                name=name,
                year=year,
                defaults={
                    'description': description,
                    'rating': rating,
                    'genre': genre,
                    'duration_secs': duration_secs,
                    'logo': logo,
                    'custom_properties': custom_props,
                }
            )
            
            # Create relation to M3U account and category
            M3UMovieRelation.objects.get_or_create(
                movie=movie,
                m3u_account=account,
                category=category,
                defaults={'custom_properties': {}}
            )
            
            # Also create a Stream for playback
            Stream.objects.update_or_create(
                m3u_account=account,
                url=stream_url,
                defaults={
                    'name': name,
                    'logo_url': logo_url,
                    'channel_group': group,
                    'custom_properties': {'vod_movie_id': movie.id, **custom_props},
                    'last_seen': timezone.now(),
                }
            )
        
        return 'created' if created else 'updated'
        
    except Exception as e:
        logger.error(f"Error saving VOD item {item.get('id')}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 'error'


def _save_category(account, cat_id: str, title: str, 
                   group_type: str) -> str:
    """
    Save category as ChannelGroup - wie MacReplayXC INSERT OR REPLACE.
    
    Args:
        account: M3UAccount
        cat_id: Category ID from portal
        title: Category title from portal
        group_type: 'vod_movie' or 'vod_series'
    
    Returns: 'created', 'updated', 'skipped', or 'error'
    """
    # Skip "All" category (id = "*") - same as MacReplayXC
    if cat_id == "*" or not cat_id:
        return 'skipped'
    
    # Skip if no title - don't use ID as fallback
    if not title:
        logger.warning(f"Category {cat_id} has no title, skipping")
        return 'skipped'
    
    # Sanitize title (remove problematic characters) - like MacReplayXC
    group_name = sanitize_name(title)
    
    try:
        # Get or create ChannelGroup
        group, created = ChannelGroup.objects.get_or_create(
            name=group_name,
            defaults={
                'group_type': group_type,
                'custom_properties': {
                    'portal_category_id': cat_id,
                    'portal_category_name': title,
                    'is_vod_category': True,
                }
            }
        )
        
        if not created:
            # Update if needed
            needs_save = False
            if group.group_type != group_type:
                group.group_type = group_type
                needs_save = True
            
            props = group.custom_properties or {}
            if props.get('portal_category_id') != cat_id:
                group.custom_properties = {
                    'portal_category_id': cat_id,
                    'portal_category_name': title,
                    'is_vod_category': True,
                }
                needs_save = True
            
            if needs_save:
                group.save()
        
        # Auto-enable setting
        account_props = account.custom_properties or {}
        auto_enable = account_props.get('auto_enable_new_groups_vod', True)
        
        # Create/update M3U account relation
        ChannelGroupM3UAccount.objects.update_or_create(
            channel_group=group,
            m3u_account=account,
            defaults={
                'enabled': auto_enable,
                'custom_properties': {
                    'portal_category_id': cat_id,
                    'portal_category_name': title,
                    'is_vod_category': True,
                    'vod_type': group_type,
                }
            }
        )
        
        return 'created' if created else 'updated'
        
    except Exception as e:
        logger.error(f"Error saving category {cat_id}: {e}")
        return 'error'


# =============================================================================
# Celery Tasks
# =============================================================================

@shared_task
def refresh_mac_portal_categories(account_id):
    """
    Load VOD/Series categories for MAC account.
    
    Basiert auf MacReplayXC /api/portal/<id>/load_vod_categories
    """
    from apps.m3u.tasks import send_m3u_update
    
    try:
        account = M3UAccount.objects.get(id=account_id, is_active=True)
        
        if account.account_type != M3UAccount.Types.MAC:
            return "Not a MAC account"
        
        # Check if VOD enabled
        props = account.custom_properties or {}
        if not props.get('enable_vod', False):
            logger.info(f"VOD disabled for {account.name}")
            return "VOD disabled"
        
        logger.info(f"=== Starting VOD refresh for {account.name} ===")
        start_time = timezone.now()
        
        send_m3u_update(account_id, "category_refresh", 0, status="processing")
        
        # Get MAC and token
        mac_address, token = _get_mac_and_token(account)
        if not mac_address or not token:
            send_m3u_update(account_id, "category_refresh", 100, status="error",
                          message="Could not authenticate")
            return "Authentication failed"
        
        # Create VOD client
        vod_client = MACVodClient(
            portal_url=account.server_url,
            mac=mac_address,
            token=token
        )
        
        stats = {"vod": 0, "series": 0, "created": 0, "updated": 0, "errors": 0}
        
        # === VOD Categories ===
        logger.info("Loading VOD categories...")
        vod_cats = vod_client.get_vod_categories()
        
        if vod_cats:
            stats["vod"] = len(vod_cats)
            # Log first category like MacReplayXC
            logger.info(f"VOD category fields: {list(vod_cats[0].keys())}")
            logger.info(f"First VOD category: {vod_cats[0]}")
            
            for cat in vod_cats:
                # Try multiple fields for title (title, alias, name)
                title = cat.get('title') or cat.get('alias') or cat.get('name') or ''
                result = _save_category(
                    account=account,
                    cat_id=str(cat.get('id', '')),
                    title=title,
                    group_type='vod_movie'
                )
                if result == 'created':
                    stats["created"] += 1
                elif result == 'updated':
                    stats["updated"] += 1
                elif result == 'error':
                    stats["errors"] += 1
        
        # === Series Categories ===
        logger.info("Loading Series categories...")
        series_cats = vod_client.get_series_categories()
        
        if series_cats:
            stats["series"] = len(series_cats)
            # Log first category
            logger.info(f"Series category fields: {list(series_cats[0].keys())}")
            logger.info(f"First Series category: {series_cats[0]}")
            
            for cat in series_cats:
                # Try multiple fields for title (title, alias, name)
                title = cat.get('title') or cat.get('alias') or cat.get('name') or ''
                result = _save_category(
                    account=account,
                    cat_id=str(cat.get('id', '')),
                    title=title,
                    group_type='vod_series'
                )
                if result == 'created':
                    stats["created"] += 1
                elif result == 'updated':
                    stats["updated"] += 1
                elif result == 'error':
                    stats["errors"] += 1
        
        # Done
        duration = (timezone.now() - start_time).total_seconds()
        total = stats["vod"] + stats["series"]
        
        logger.info(f"=== VOD refresh completed for {account.name} ===")
        logger.info(f"VOD: {stats['vod']}, Series: {stats['series']}, Total: {total}")
        logger.info(f"Created: {stats['created']}, Updated: {stats['updated']}, Errors: {stats['errors']}")
        logger.info(f"Duration: {duration:.2f}s")
        
        send_m3u_update(account_id, "category_refresh", 100, status="success",
                       message=f"Loaded {total} categories ({stats['created']} new)")
        
        return f"Success: {total} categories"
        
    except M3UAccount.DoesNotExist:
        return "Account not found"
    except Exception as e:
        logger.error(f"VOD refresh failed: {e}", exc_info=True)
        send_m3u_update(account_id, "category_refresh", 100, status="error",
                       message=str(e))
        return f"Error: {e}"


@shared_task
def refresh_mac_portal_selected_vod(account_id):
    """
    Import VOD content for selected categories.
    
    Phase 2: Nach Kategorie-Auswahl im Groups-Tab.
    Wird automatisch bei "Save and Refresh" aufgerufen wenn VOD Kategorien aktiviert sind.
    """
    from apps.m3u.tasks import send_m3u_update
    
    try:
        account = M3UAccount.objects.get(id=account_id, is_active=True)
        
        if account.account_type != M3UAccount.Types.MAC:
            return "Not a MAC account"
        
        # Check if VOD enabled
        props = account.custom_properties or {}
        if not props.get('enable_vod', False):
            logger.info(f"VOD disabled for {account.name}")
            return "VOD disabled"
        
        logger.info(f"=== Starting VOD content import for {account.name} ===")
        start_time = timezone.now()
        
        send_m3u_update(account_id, "vod_import", 0, status="processing")
        
        # Step 1: Delete streams from DISABLED VOD categories
        logger.info("Step 1: Cleaning up disabled VOD categories...")
        disabled_vod_groups = ChannelGroupM3UAccount.objects.filter(
            m3u_account=account,
            enabled=False,
            channel_group__group_type__in=['vod_movie', 'vod_series']
        ).select_related('channel_group')
        
        deleted_count = 0
        for group_relation in disabled_vod_groups:
            group = group_relation.channel_group
            # Delete all streams from this account that belong to this group
            streams_to_delete = account.streams.filter(channel_group=group)
            count = streams_to_delete.count()
            if count > 0:
                logger.info(f"Deleting {count} streams from disabled category '{group.name}'")
                streams_to_delete.delete()
                deleted_count += count
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} streams from disabled categories")
        
        # Step 2: Get enabled VOD categories
        logger.info("Step 2: Getting enabled VOD categories...")
        enabled_vod_groups = ChannelGroupM3UAccount.objects.filter(
            m3u_account=account,
            enabled=True,
            channel_group__group_type__in=['vod_movie', 'vod_series']
        ).select_related('channel_group')
        
        if not enabled_vod_groups.exists():
            logger.info(f"No enabled VOD categories for {account.name}")
            send_m3u_update(account_id, "vod_import", 100, status="success",
                          message=f"Cleaned up {deleted_count} streams from disabled categories")
            return f"Cleanup complete: {deleted_count} streams deleted"
        
        # Get MAC and token
        mac_address, token = _get_mac_and_token(account)
        if not mac_address or not token:
            send_m3u_update(account_id, "vod_import", 100, status="error",
                          message="Could not authenticate")
            return "Authentication failed"
        
        # Create VOD client
        vod_client = MACVodClient(
            portal_url=account.server_url,
            mac=mac_address,
            token=token
        )
        
        stats = {"categories": 0, "items": 0, "created": 0, "updated": 0, "errors": 0}
        
        # Import content for each enabled category
        for group_relation in enabled_vod_groups:
            group = group_relation.channel_group
            props = group.custom_properties or {}
            category_id = props.get('portal_category_id')
            vod_type = props.get('vod_type', group.group_type)  # 'vod_movie' or 'vod_series'
            
            if not category_id:
                logger.warning(f"Group {group.name} has no portal_category_id")
                continue
            
            stats["categories"] += 1
            logger.info(f"Importing VOD items for category {category_id} ({group.name})")
            
            # Get VOD items from portal (with pagination) - wie MacReplayXC
            page = 1
            category_items = 0
            
            while True:
                # Get items based on type
                if vod_type == 'vod_series' or group.group_type == 'vod_series':
                    items = vod_client.get_series_items(category_id, page)
                else:
                    items = vod_client.get_vod_items(category_id, page)
                
                if not items:
                    break  # No more items
                
                # Save items as Streams
                for item in items:
                    try:
                        result = _save_vod_item(account, group, item, vod_type)
                        if result == 'created':
                            stats["created"] += 1
                        elif result == 'updated':
                            stats["updated"] += 1
                        elif result == 'error':
                            stats["errors"] += 1
                        category_items += 1
                    except Exception as e:
                        logger.error(f"Error saving VOD item: {e}")
                        stats["errors"] += 1
                
                stats["items"] += len(items)
                
                # Check if there are more pages (wie MacReplayXC)
                # Stop if: less than 14 items (last page) or no items at all
                if len(items) < 14:
                    logger.debug(f"Last page reached for category {group.name}: {len(items)} items")
                    break
                
                page += 1
                
                # Safety limit to prevent infinite loops (very high limit)
                if page > 1000:
                    logger.warning(f"Safety limit reached for category {group.name} at page {page}")
                    break
            
            logger.info(f"Imported {category_items} items for category {group.name}")
        
        # Done
        duration = (timezone.now() - start_time).total_seconds()
        
        logger.info(f"=== VOD content import completed for {account.name} ===")
        logger.info(f"Categories: {stats['categories']}, Items: {stats['items']}")
        logger.info(f"Created: {stats['created']}, Errors: {stats['errors']}")
        logger.info(f"Duration: {duration:.2f}s")
        
        send_m3u_update(account_id, "vod_import", 100, status="success",
                       message=f"Imported {stats['items']} items from {stats['categories']} categories")
        
        return f"Success: {stats['items']} items from {stats['categories']} categories"
        
    except M3UAccount.DoesNotExist:
        return "Account not found"
    except Exception as e:
        logger.error(f"VOD content import failed: {e}", exc_info=True)
        send_m3u_update(account_id, "vod_import", 100, status="error",
                       message=str(e))
        return f"Error: {e}"
