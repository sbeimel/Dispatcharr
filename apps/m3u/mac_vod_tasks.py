"""
MAC Portal VOD Tasks - Zweistufiger Import für MAC/STB Portale.

Phase 1: Kategorien laden und im Groups-Tab anzeigen
Phase 2: Nur ausgewählte Kategorien importieren
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import M3UAccount
from apps.channels.models import ChannelGroup, ChannelGroupM3UAccount

logger = logging.getLogger(__name__)


@shared_task
def refresh_mac_portal_categories(account_id):
    """
    Phase 1: Lade nur VOD/Series Kategorien für MAC Portal Account.
    Erstellt ChannelGroups für VOD-Movies und VOD-Series Kategorien.
    """
    from apps.m3u.tasks import send_m3u_update
    
    try:
        account = M3UAccount.objects.get(id=account_id, is_active=True)
        
        if account.account_type != M3UAccount.Types.MAC:
            logger.warning(f"MAC category refresh called for non-MAC account {account_id}")
            return "MAC category refresh only available for MAC/STB accounts"
        
        logger.info(f"Starting MAC category refresh for account {account.name}")
        start_time = timezone.now()
        
        # Send start notification
        send_m3u_update(account_id, "category_refresh", 0, status="processing")
        
        # Get MAC address
        mac_address = _get_mac_address(account)
        if not mac_address:
            logger.error(f"No MAC address available for account {account_id}")
            send_m3u_update(account_id, "category_refresh", 100, status="error",
                           message="No MAC address available")
            return "No MAC address available"
        
        # Initialize UnifiedPortalEngine
        engine = _create_portal_engine(account, mac_address)
        
        # Perform handshake
        result = engine.perform_handshake()
        if not result.success:
            logger.error(f"Handshake failed for MAC category refresh: {result.error}")
            send_m3u_update(account_id, "category_refresh", 100, status="error",
                           message=f"Portal handshake failed: {result.error}")
            return f"Handshake failed: {result.error}"
        
        total_categories = 0
        
        # Fetch VOD categories (Movies)
        logger.info(f"Fetching VOD categories for account {account.name}")
        vod_categories = engine.get_vod_categories()
        
        if vod_categories:
            vod_count = _create_channel_groups_for_categories(
                account, vod_categories, "VOD - Movies", "vod_movie"
            )
            total_categories += vod_count
            logger.info(f"Created {vod_count} VOD movie category groups")
        
        # Fetch Series categories
        logger.info(f"Fetching series categories for account {account.name}")
        series_categories = engine.get_series_categories()
        
        if series_categories:
            series_count = _create_channel_groups_for_categories(
                account, series_categories, "VOD - Series", "vod_series"
            )
            total_categories += series_count
            logger.info(f"Created {series_count} VOD series category groups")
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"MAC category refresh completed for account {account.name}: "
                   f"{total_categories} categories in {duration:.2f}s")
        
        send_m3u_update(account_id, "category_refresh", 100, status="success",
                       message=f"Categories loaded: {total_categories} VOD categories. "
                               f"Select categories in Groups tab and refresh to import content.")
        
        return f"MAC categories loaded: {total_categories} categories"
        
    except Exception as e:
        logger.error(f"Error refreshing MAC categories for account {account_id}: {e}", exc_info=True)
        send_m3u_update(account_id, "category_refresh", 100, status="error",
                       message=f"Category refresh failed: {str(e)}")
        return f"MAC category refresh failed: {str(e)}"


def _get_vod_category_id(group_rel):
    """Get portal_category_id from either ChannelGroup or relationship custom_properties."""
    # First try relationship's custom_properties (always available)
    rel_props = group_rel.custom_properties or {}
    cat_id = rel_props.get('portal_category_id')
    if cat_id:
        return cat_id
    
    # Then try ChannelGroup's custom_properties (if model has the field)
    if hasattr(group_rel.channel_group, 'custom_properties'):
        group_props = group_rel.channel_group.custom_properties or {}
        cat_id = group_props.get('portal_category_id')
        if cat_id:
            return cat_id
    
    return None


def _get_vod_type(group_rel):
    """Get VOD type (vod_movie or vod_series) from either ChannelGroup or relationship."""
    # First try ChannelGroup's group_type (if model has the field)
    if hasattr(group_rel.channel_group, 'group_type'):
        return group_rel.channel_group.group_type
    
    # Then try relationship's custom_properties
    rel_props = group_rel.custom_properties or {}
    return rel_props.get('vod_type')


@shared_task
def refresh_mac_portal_selected_vod(account_id):
    """
    Phase 2: Importiere VOD Content nur für ausgewählte Kategorien.
    Läuft nach Kategorie-Auswahl im Groups-Tab.
    """
    from apps.m3u.tasks import send_m3u_update
    from apps.vod.tasks import batch_create_categories, process_mac_vod_items, process_mac_series_items, cleanup_orphaned_vod_content
    
    try:
        account = M3UAccount.objects.get(id=account_id, is_active=True)
        
        if account.account_type != M3UAccount.Types.MAC:
            logger.warning(f"MAC VOD import called for non-MAC account {account_id}")
            return "MAC VOD import only available for MAC/STB accounts"
        
        logger.info(f"Starting MAC VOD import for selected categories: {account.name}")
        start_time = timezone.now()
        
        # Send start notification
        send_m3u_update(account_id, "vod_import", 0, status="processing")
        
        # Get enabled VOD category groups - check both new and old model structures
        has_group_type = hasattr(ChannelGroup, 'group_type')
        
        if has_group_type:
            # New model with group_type field
            enabled_groups = ChannelGroupM3UAccount.objects.filter(
                m3u_account=account,
                enabled=True,
                channel_group__group_type__in=['vod_movie', 'vod_series']
            ).select_related('channel_group')
        else:
            # Old model - filter by relationship's custom_properties
            enabled_groups = ChannelGroupM3UAccount.objects.filter(
                m3u_account=account,
                enabled=True,
                custom_properties__is_vod_category=True
            ).select_related('channel_group')
        
        if not enabled_groups.exists():
            logger.info(f"No VOD categories selected for account {account.name}")
            send_m3u_update(account_id, "vod_import", 100, status="success",
                           message="No VOD categories selected for import")
            return "No VOD categories selected"
        
        # Get MAC address and engine
        mac_address = _get_mac_address(account)
        if not mac_address:
            logger.error(f"No MAC address available for account {account_id}")
            send_m3u_update(account_id, "vod_import", 100, status="error",
                           message="No MAC address available")
            return "No MAC address available"
        
        engine = _create_portal_engine(account, mac_address)
        
        # Perform handshake
        result = engine.perform_handshake()
        if not result.success:
            logger.error(f"Handshake failed for MAC VOD import: {result.error}")
            send_m3u_update(account_id, "vod_import", 100, status="error",
                           message=f"Portal handshake failed: {result.error}")
            return f"Handshake failed: {result.error}"
        
        total_movies = 0
        total_series = 0
        
        # Separate movie and series groups using helper function
        movie_groups = [g for g in enabled_groups if _get_vod_type(g) == 'vod_movie']
        series_groups = [g for g in enabled_groups if _get_vod_type(g) == 'vod_series']
        
        # Process movie categories
        if movie_groups:
            logger.info(f"Processing {len(movie_groups)} selected movie categories")
            
            # Get all VOD categories to create category map
            vod_categories = engine.get_vod_categories()
            if vod_categories:
                movie_category_map = batch_create_categories(vod_categories, 'movie', account)
                
                for group_rel in movie_groups:
                    cat_id = _get_vod_category_id(group_rel)
                    if not cat_id:
                        continue
                    
                    try:
                        logger.info(f"Importing VOD items for category {cat_id}")
                        vod_items = engine.get_vod_items(category_id=str(cat_id))
                        
                        if vod_items and 'data' in vod_items:
                            items = vod_items['data']
                            if items:
                                process_mac_vod_items(account, items, movie_category_map, start_time)
                                total_movies += len(items)
                                logger.info(f"Imported {len(items)} movies from category {cat_id}")
                    except Exception as e:
                        logger.warning(f"Error importing VOD category {cat_id}: {e}")
                        continue
        
        # Process series categories
        if series_groups:
            logger.info(f"Processing {len(series_groups)} selected series categories")
            
            # Get all series categories to create category map
            series_categories = engine.get_series_categories()
            if series_categories:
                series_category_map = batch_create_categories(series_categories, 'series', account)
                
                for group_rel in series_groups:
                    cat_id = _get_vod_category_id(group_rel)
                    if not cat_id:
                        continue
                    
                    try:
                        logger.info(f"Importing series for category {cat_id}")
                        series_items = engine.get_series_items(category_id=str(cat_id))
                        
                        if series_items and 'data' in series_items:
                            items = series_items['data']
                            if items:
                                process_mac_series_items(account, items, series_category_map, start_time)
                                total_series += len(items)
                                logger.info(f"Imported {len(items)} series from category {cat_id}")
                    except Exception as e:
                        logger.warning(f"Error importing series category {cat_id}: {e}")
                        continue
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"MAC VOD import completed for account {account.name}: "
                   f"{total_movies} movies, {total_series} series in {duration:.2f}s")
        
        # Cleanup orphaned content
        cleanup_orphaned_vod_content(account_id=account_id, scan_start_time=start_time)
        
        send_m3u_update(account_id, "vod_import", 100, status="success",
                       message=f"VOD import completed: {total_movies} movies, {total_series} series")
        
        return f"MAC VOD import completed: {total_movies} movies, {total_series} series"
        
    except Exception as e:
        logger.error(f"Error importing MAC VOD for account {account_id}: {e}", exc_info=True)
        send_m3u_update(account_id, "vod_import", 100, status="error",
                       message=f"VOD import failed: {str(e)}")
        return f"MAC VOD import failed: {str(e)}"


def _get_mac_address(account):
    """Get MAC address for account."""
    mac_address = None
    if hasattr(account, 'macs') and account.macs.exists():
        mac_obj = account.macs.filter(status__in=['valid', 'active', 'unknown']).first()
        if mac_obj:
            mac_address = mac_obj.address
    
    if not mac_address:
        # Fallback to mac_address field
        mac_address = getattr(account, 'mac_address', None)
        if mac_address and ',' in mac_address:
            mac_address = mac_address.split(',')[0].strip()
    
    return mac_address


def _create_portal_engine(account, mac_address):
    """Create UnifiedPortalEngine for account with fastest engine support."""
    from apps.m3u.unified_portal_engine import UnifiedPortalEngine, PortalEngine
    
    props = account.custom_properties or {}
    engine_pref = props.get("portal_engine", "auto")
    
    # Handle "fastest" mode - use benchmarked fastest_engine if available
    if engine_pref == "fastest":
        fastest_engine = props.get("fastest_engine")
        if fastest_engine:
            engine_pref = fastest_engine
            logger.info(f"VOD using FASTEST benchmarked engine: {engine_pref}")
        else:
            engine_pref = "auto"
            logger.info(f"VOD: 'fastest' mode but no benchmark data, using auto")
    
    try:
        selected_engine = PortalEngine(engine_pref) if engine_pref != "auto" else PortalEngine.AUTO
    except ValueError:
        selected_engine = PortalEngine.AUTO
    
    return UnifiedPortalEngine(
        portal_url=account.server_url,
        mac=mac_address,
        engine=selected_engine,
    )


def _create_channel_groups_for_categories(account, categories, prefix, group_type):
    """Create ChannelGroups for VOD/Series categories.
    
    Note: This function now handles both old models (without group_type/custom_properties)
    and new models (with these fields) gracefully.
    """
    count = 0
    
    for cat_data in categories:
        cat_id = cat_data.get('category_id') or cat_data.get('id')
        cat_name = cat_data.get('category_name') or cat_data.get('name') or f"Category {cat_id}"
        
        if not cat_id:
            continue
        
        # Create group name with prefix
        group_name = f"{prefix} - {cat_name}"
        
        try:
            with transaction.atomic():
                # Check if ChannelGroup model has the new fields
                has_new_fields = hasattr(ChannelGroup, 'group_type') and hasattr(ChannelGroup, 'custom_properties')
                
                if has_new_fields:
                    # New model with group_type and custom_properties
                    group, created = ChannelGroup.objects.update_or_create(
                        name=group_name,
                        defaults={
                            'group_type': group_type,
                            'custom_properties': {
                                'portal_category_id': str(cat_id),
                                'portal_category_name': cat_name,
                                'is_vod_category': True,
                            }
                        }
                    )
                else:
                    # Old model without new fields - just create by name
                    group, created = ChannelGroup.objects.get_or_create(
                        name=group_name
                    )
                
                # Get auto-enable setting
                account_props = account.custom_properties or {}
                auto_enable = account_props.get("auto_enable_new_groups_vod", True)
                
                # Store VOD category info in the relationship's custom_properties
                rel_custom_props = {
                    'portal_category_id': str(cat_id),
                    'portal_category_name': cat_name,
                    'is_vod_category': True,
                    'vod_type': group_type,  # 'vod_movie' or 'vod_series'
                }
                
                # Create or update M3U account relation
                relation, rel_created = ChannelGroupM3UAccount.objects.update_or_create(
                    channel_group=group,
                    m3u_account=account,
                    defaults={
                        'enabled': auto_enable,
                        'custom_properties': rel_custom_props
                    }
                )
                
                if created or rel_created:
                    count += 1
                    logger.debug(f"Created VOD category group: {group_name}")
                
        except Exception as e:
            logger.warning(f"Error creating category group {group_name}: {e}")
            continue
    
    return count