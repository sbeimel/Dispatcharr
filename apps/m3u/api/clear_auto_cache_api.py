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
    
    Clears the AUTO engine cache for a specific MAC portal account.
    
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
            "cache_keys": ["http://portal.com:00:1A:79:...", ...]
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
    
    # Clear cache for all MACs of this portal
    from apps.m3u.unified_portal_engine import UnifiedPortalEngine
    
    cleared_keys = []
    portal_url = account.server_url.rstrip('/')
    
    for mac in macs:
        # Generate cache key (same format as in UnifiedPortalEngine)
        cache_key = f"{portal_url}:{mac.address}"
        
        # Remove from cache if exists
        if cache_key in UnifiedPortalEngine._strategy_cache:
            cached_engine = UnifiedPortalEngine._strategy_cache[cache_key]
            del UnifiedPortalEngine._strategy_cache[cache_key]
            cleared_keys.append({
                'key': cache_key,
                'mac': mac.address,
                'cached_engine': cached_engine.value
            })
            logger.info(f"Cleared AUTO cache for {cache_key} (was: {cached_engine.value})")
    
    if cleared_keys:
        return Response({
            'success': True,
            'message': f'AUTO cache cleared for {len(cleared_keys)} MAC(s)',
            'cleared_count': len(cleared_keys),
            'cleared_entries': cleared_keys,
            'portal_url': portal_url
        })
    else:
        return Response({
            'success': True,
            'message': 'No cached entries found (cache was already empty)',
            'cleared_count': 0,
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
    
    # Check cache status for all MACs
    from apps.m3u.unified_portal_engine import UnifiedPortalEngine
    
    portal_url = account.server_url.rstrip('/')
    cache_entries = []
    
    for mac in macs:
        cache_key = f"{portal_url}:{mac.address}"
        
        if cache_key in UnifiedPortalEngine._strategy_cache:
            cached_engine = UnifiedPortalEngine._strategy_cache[cache_key]
            cache_entries.append({
                'mac': mac.address,
                'mac_status': mac.status,
                'cached_engine': cached_engine.value,
                'cache_key': cache_key
            })
    
    return Response({
        'portal_url': portal_url,
        'total_macs': macs.count(),
        'cached_macs': len(cache_entries),
        'cache_entries': cache_entries,
        'has_cache': len(cache_entries) > 0
    })
