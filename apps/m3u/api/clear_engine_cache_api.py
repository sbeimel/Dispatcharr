"""
API endpoint to clear engine cache for a specific portal or all portals.
"""

import logging
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from apps.m3u.mac_portal_models import MACPortalGlobalSettings

logger = logging.getLogger(__name__)


@api_view(['POST'])
def clear_engine_cache(request):
    """
    Clear engine cache for a specific portal or all portals.
    Optionally trigger a refresh to rebuild the cache.
    
    POST /api/m3u/engine-cache/clear/
    Body: {
        "portal_url": "http://portal.example.com",  # Optional, if omitted clears all
        "account_id": 123,  # Optional, if provided triggers refresh after clear
        "trigger_refresh": true  # Optional, default false
    }
    
    Returns:
        200: Cache cleared successfully
        400: Invalid request
    """
    try:
        portal_url = request.data.get('portal_url')
        account_id = request.data.get('account_id')
        trigger_refresh = request.data.get('trigger_refresh', False)
        
        settings = MACPortalGlobalSettings.get_settings()
        
        if not settings.engine_cache:
            return Response({
                'success': True,
                'message': 'Cache is already empty',
                'cleared_count': 0
            })
        
        if portal_url:
            # Clear cache for specific portal
            if portal_url in settings.engine_cache:
                del settings.engine_cache[portal_url]
                settings.save(update_fields=['engine_cache'])
                logger.info(f"Cleared engine cache for portal: {portal_url}")
                
                # Trigger refresh if requested
                if trigger_refresh and account_id:
                    from apps.m3u.models import M3UAccount
                    from apps.m3u.tasks import refresh_m3u_account
                    
                    try:
                        account = M3UAccount.objects.get(id=account_id)
                        refresh_m3u_account.delay(account.id)
                        logger.info(f"Triggered refresh for account {account_id} after cache clear")
                        
                        return Response({
                            'success': True,
                            'message': f'Cache cleared and refresh triggered for {portal_url}',
                            'cleared_count': 1,
                            'refresh_triggered': True
                        })
                    except M3UAccount.DoesNotExist:
                        logger.warning(f"Account {account_id} not found for refresh")
                
                return Response({
                    'success': True,
                    'message': f'Cache cleared for {portal_url}',
                    'cleared_count': 1,
                    'refresh_triggered': False
                })
            else:
                return Response({
                    'success': True,
                    'message': f'No cache found for {portal_url}',
                    'cleared_count': 0
                })
        else:
            # Clear all cache
            cleared_count = len(settings.engine_cache)
            settings.engine_cache = {}
            settings.save(update_fields=['engine_cache'])
            logger.info(f"Cleared all engine cache ({cleared_count} entries)")
            return Response({
                'success': True,
                'message': f'Cleared all engine cache',
                'cleared_count': cleared_count
            })
            
    except Exception as e:
        logger.error(f"Error clearing engine cache: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_engine_cache(request):
    """
    Get current engine cache status.
    
    GET /api/m3u/engine-cache/
    GET /api/m3u/engine-cache/?portal_url=http://portal.example.com
    
    Returns:
        200: Cache data
    """
    try:
        settings = MACPortalGlobalSettings.get_settings()
        portal_url_filter = request.query_params.get('portal_url')
        
        cache_data = []
        if settings.engine_cache:
            for portal_url, engine in settings.engine_cache.items():
                # Filter by portal_url if provided
                if portal_url_filter and portal_url != portal_url_filter:
                    continue
                
                cache_data.append({
                    'portal_url': portal_url,
                    'engine': engine
                })
        
        # If filtering by portal_url, return single object or null
        if portal_url_filter:
            if cache_data:
                return Response({
                    'success': True,
                    'cached': True,
                    'engine': cache_data[0]['engine']
                })
            else:
                return Response({
                    'success': True,
                    'cached': False,
                    'engine': None
                })
        
        # Return all cache data
        return Response({
            'success': True,
            'cache_count': len(cache_data),
            'cache_data': cache_data
        })
        
    except Exception as e:
        logger.error(f"Error getting engine cache: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
