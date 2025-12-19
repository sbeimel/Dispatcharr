"""
Clear AUTO Engine Cache API

Provides endpoint to clear the cached AUTO engine selection for a specific portal.
This allows users to force re-detection of the best engine.

Endpoint:
- POST /api/m3u/clear-auto-cache/<account_id>/ - Clear AUTO cache for portal
"""

import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_auto_cache(request, account_id):
    """
    POST /api/m3u/clear-auto-cache/<account_id>/
    POST /api/m3u/test-auto-mode/<account_id>/
    
    Clears the AUTO engine cache and optionally tests AUTO mode.
    
    When called via /test-auto-mode/, it:
    1. Clears the engine cache
    2. Triggers a channel fetch to test AUTO mode
    3. Returns the working engine and channel count
    
    The AUTO engine mode caches the first successful engine per portal+MAC combination.
    This endpoint allows users to clear that cache and force re-detection.
    
    Use cases:
    - Portal changed its configuration
    - Want to test different engines
    - Cached engine is no longer working optimally
    
    Returns:
        {
            "success": true,
            "message": "AUTO cache cleared for 3 MACs",
            "cleared_count": 3,
            "working_engine": "macattack",
            "channels_found": 13933
        }
    """
    from apps.m3u.models import M3UAccount
    
    try:
        account = M3UAccount.objects.get(pk=account_id)
    except M3UAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=404)
    
    if account.account_type != 'MAC':
        return Response({'error': 'Not a MAC portal account'}, status=400)
    
    # Get all MACs for this account
    macs = account.macs.all()
    
    if not macs.exists():
        return Response({
            'error': 'No MAC addresses found for this account'
        }, status=400)
    
    # Clear cache for this portal from persistent storage
    from apps.m3u.mac_portal_models import MACPortalGlobalSettings
    
    portal_url = account.server_url.rstrip('/')
    settings = MACPortalGlobalSettings.get_settings()
    
    cached_engine = None
    if settings.engine_cache and portal_url in settings.engine_cache:
        cached_engine = settings.engine_cache[portal_url]
        del settings.engine_cache[portal_url]
        settings.save(update_fields=['engine_cache'])
        logger.info(f"Cleared engine cache for {portal_url} (was: {cached_engine})")
    
    # Also clear from account custom_properties if exists
    custom_props = account.custom_properties or {}
    if 'engine_cache_date' in custom_props:
        del custom_props['engine_cache_date']
        account.custom_properties = custom_props
        account.save(update_fields=['custom_properties'])
    
    # Check if this is a test-auto-mode request (test AUTO mode after clearing)
    test_mode = request.path.endswith('/test-auto-mode/' + str(account_id) + '/')
    
    if test_mode:
        # Test AUTO mode - der AUTO-Modus testet jetzt automatisch ALLE Engines und wählt die schnellste
        try:
            from apps.m3u.mac_portal_client import UnifiedMacPortalClient
            from django.utils import timezone
            
            # Get first available MAC
            first_mac = macs.filter(status='valid').first() or macs.first()
            if not first_mac:
                return Response({
                    'success': False,
                    'error': 'Keine verfügbare MAC-Adresse gefunden'
                }, status=400)
            
            logger.info(f"Calibrate AUTO: Teste alle Engines nacheinander für Portal {portal_url[:50]}...")
            
            # Create client with AUTO mode - testet automatisch alle Engines nacheinander
            client = UnifiedMacPortalClient(
                base_url=portal_url,
                mac=first_mac.address,
                proxy=account.proxy,
                portal_engine='auto'
            )
            
            # get_channels() testet jetzt automatisch ALLE Engines und wählt die schnellste
            channels = client.get_channels()
            
            if channels and len(channels) > 0:
                # Get the working engine from persistent cache (AUTO mode saves it)
                settings = MACPortalGlobalSettings.get_settings()
                working_engine = settings.engine_cache.get(portal_url) if settings.engine_cache else None
                
                # Save cache date and portal info to account custom_properties
                custom_props = account.custom_properties or {}
                custom_props['engine_cache_date'] = timezone.now().isoformat()
                
                # Portal-Info (falls vom AUTO-Modus erkannt)
                if hasattr(client, '_portal_info') and client._portal_info:
                    portal_info = client._portal_info
                    if portal_info.get('portal_type'):
                        custom_props['portal_type'] = portal_info['portal_type']
                    if portal_info.get('portal_version'):
                        custom_props['portal_version'] = portal_info['portal_version']
                    if portal_info.get('max_connections'):
                        custom_props['max_connections'] = portal_info['max_connections']
                    if portal_info.get('detected_by'):
                        custom_props['portal_detected_by'] = portal_info['detected_by']
                    
                    logger.info(f"Calibrate AUTO: Portal-Info gespeichert - "
                               f"Typ: {portal_info.get('portal_type')}, "
                               f"Version: {portal_info.get('portal_version')}, "
                               f"Max Connections: {portal_info.get('max_connections')}")
                
                account.custom_properties = custom_props
                account.save(update_fields=['custom_properties'])
                
                logger.info(f"Calibrate AUTO: ERFOLG - Schnellste Engine: {working_engine}, "
                           f"{len(channels)} Kanäle gefunden")
                
                return Response({
                    'success': True,
                    'message': f'Kalibrierung erfolgreich - Schnellste Engine gefunden',
                    'working_engine': working_engine,
                    'channels_found': len(channels),
                    'portal_url': portal_url,
                    'tested_mac': first_mac.address
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Keine funktionierende Engine gefunden - alle Engines fehlgeschlagen',
                    'portal_url': portal_url
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error testing AUTO mode: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': f'AUTO-Modus-Test fehlgeschlagen: {str(e)}'
            }, status=500)
    
    # Regular cache clear response
    if cached_engine:
        return Response({
            'success': True,
            'message': f'Engine cache cleared for portal',
            'cleared_engine': cached_engine,
            'portal_url': portal_url
        })
    else:
        return Response({
            'success': True,
            'message': 'No cached engine found (cache was already empty)',
            'portal_url': portal_url
        })


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_auto_cache_status(request, account_id):
    """
    GET /api/m3u/clear-auto-cache/<account_id>/status/
    
    Gets the current AUTO cache status for a portal.
    Shows which engines are cached for which MACs.
    
    Returns:
        {
            "portal_url": "http://portal.com",
            "total_macs": 5,
            "cached_macs": 3,
            "cache_entries": [
                {
                    "mac": "00:1A:79:...",
                    "cached_engine": "macattack",
                    "cache_key": "http://portal.com:00:1A:79:..."
                }
            ]
        }
    """
    from apps.m3u.models import M3UAccount
    
    try:
        account = M3UAccount.objects.get(pk=account_id)
    except M3UAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=404)
    
    if account.account_type != 'MAC':
        return Response({'error': 'Not a MAC portal account'}, status=400)
    
    # Get all MACs for this account
    macs = account.macs.all()
    
    if not macs.exists():
        return Response({
            'error': 'No MAC addresses found for this account'
        }, status=400)
    
    # Check cache status from persistent storage
    from apps.m3u.mac_portal_models import MACPortalGlobalSettings
    
    portal_url = account.server_url.rstrip('/')
    settings = MACPortalGlobalSettings.get_settings()
    
    cached_engine = None
    if settings.engine_cache and portal_url in settings.engine_cache:
        cached_engine = settings.engine_cache[portal_url]
    
    # Get cache date from custom_properties
    custom_props = account.custom_properties or {}
    cache_date = custom_props.get('engine_cache_date')
    
    return Response({
        'portal_url': portal_url,
        'total_macs': macs.count(),
        'cached_engine': cached_engine,
        'cache_date': cache_date,
        'has_cache': cached_engine is not None
    })
