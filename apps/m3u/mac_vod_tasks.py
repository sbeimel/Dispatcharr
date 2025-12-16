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
    """
    # Placeholder - wird später implementiert
    logger.info(f"VOD content import for account {account_id} - not yet implemented")
    return "Not implemented"
