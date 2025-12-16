"""
Simple Engine Benchmark API - Standalone, guaranteed to work.

This is a completely standalone implementation that doesn't rely on
ViewSets, routers, or complex URL patterns.

Endpoints:
- POST /api/m3u/benchmark/<account_id>/run/  - Run benchmark
- GET /api/m3u/benchmark/<account_id>/result/ - Get cached result
"""

import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_benchmark(request, account_id):
    """
    POST /api/m3u/benchmark/<account_id>/run/
    
    Runs a comprehensive benchmark of all portal engines.
    Tests: Handshake → Genres → Channels → Stream Link → Portal Type
    
    Returns the fastest working engine and portal type information.
    """
    from apps.m3u.models import M3UAccount
    
    try:
        account = M3UAccount.objects.get(pk=account_id)
    except M3UAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=404)
    
    if account.account_type != 'MAC':
        return Response({'error': 'Not a MAC portal account'}, status=400)
    
    # Get first available MAC
    mac = account.macs.filter(status='valid').first()
    if not mac:
        mac = account.macs.first()
    
    if not mac:
        return Response({
            'error': 'No MAC addresses available for this account'
        }, status=400)
    
    # Get proxy from custom_properties
    props = account.custom_properties or {}
    proxy = props.get('proxy')
    if isinstance(proxy, str):
        proxy = proxy.strip() or None
    
    logger.info(f"Starting benchmark for account {account_id} ({account.name})")
    logger.info(f"Portal URL: {account.server_url}")
    logger.info(f"MAC: {mac.address}")
    
    try:
        # Use the existing benchmark implementation
        from apps.m3u.mac_portal_client import UnifiedMacPortalClient
        
        results = UnifiedMacPortalClient.benchmark_all_engines(
            portal_url=account.server_url,
            mac=mac.address,
            proxy=proxy
        )
        
        # Save results to account's custom_properties
        custom_props = account.custom_properties or {}
        
        if results.get('fastest'):
            custom_props['fastest_engine'] = results['fastest']
            custom_props['fastest_engine_time_ms'] = results['summary'].get('fastest_time_ms')
            custom_props['fastest_has_stream_link'] = results['summary'].get('fastest_has_stream_link', False)
        
        if results.get('portal_info'):
            portal_info = results['portal_info']
            if portal_info.get('portal_type') and portal_info['portal_type'] != 'unknown':
                custom_props['portal_type'] = portal_info['portal_type']
            if portal_info.get('portal_version'):
                custom_props['portal_version'] = portal_info['portal_version']
            if portal_info.get('detected_by'):
                custom_props['portal_detected_by'] = portal_info['detected_by']
        
        custom_props['benchmark_date'] = timezone.now().isoformat()
        account.custom_properties = custom_props
        account.save(update_fields=['custom_properties'])
        
        logger.info(f"Benchmark complete for account {account_id}: fastest={results.get('fastest')}")
        
        return Response({
            'account_id': account.id,
            'account_name': account.name,
            'portal_url': account.server_url,
            'mac_used': mac.address,
            **results
        })
        
    except Exception as e:
        logger.error(f"Benchmark failed for account {account_id}: {e}", exc_info=True)
        return Response({
            'error': str(e),
            'account_id': account_id
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_benchmark_result(request, account_id):
    """
    GET /api/m3u/benchmark/<account_id>/result/
    
    Returns the cached benchmark result for an account.
    """
    from apps.m3u.models import M3UAccount
    from apps.m3u.mac_portal_client import UnifiedMacPortalClient
    
    try:
        account = M3UAccount.objects.get(pk=account_id)
    except M3UAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=404)
    
    props = account.custom_properties or {}
    
    # Also get cached data from UnifiedMacPortalClient
    fastest_data = UnifiedMacPortalClient.get_fastest_engine(account.server_url)
    cached_engine = UnifiedMacPortalClient.get_cached_engine(account.server_url)
    
    return Response({
        'account_id': account.id,
        'account_name': account.name,
        'portal_url': account.server_url,
        # From custom_properties
        'fastest_engine': props.get('fastest_engine'),
        'fastest_engine_time_ms': props.get('fastest_engine_time_ms'),
        'fastest_has_stream_link': props.get('fastest_has_stream_link', False),
        'portal_type': props.get('portal_type', 'unknown'),
        'portal_version': props.get('portal_version'),
        'portal_detected_by': props.get('portal_detected_by'),
        'benchmark_date': props.get('benchmark_date'),
        # From cache
        'cached_fastest': fastest_data,
        'cached_auto_engine': cached_engine,
        'has_benchmark': props.get('fastest_engine') is not None or fastest_data is not None,
    })


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_benchmark(request, account_id):
    """
    DELETE /api/m3u/benchmark/<account_id>/clear/
    
    Clears the benchmark cache for an account.
    """
    from apps.m3u.models import M3UAccount
    from apps.m3u.mac_portal_client import UnifiedMacPortalClient
    from django.core.cache import cache
    
    try:
        account = M3UAccount.objects.get(pk=account_id)
    except M3UAccount.DoesNotExist:
        return Response({'error': 'Account not found'}, status=404)
    
    # Clear from custom_properties
    props = account.custom_properties or {}
    for key in ['fastest_engine', 'fastest_engine_time_ms', 'fastest_has_stream_link',
                'portal_type', 'portal_version', 'portal_detected_by', 'benchmark_date']:
        props.pop(key, None)
    account.custom_properties = props
    account.save(update_fields=['custom_properties'])
    
    # Clear from cache
    UnifiedMacPortalClient.clear_cached_engine(account.server_url)
    
    # Clear fastest engine cache
    fastest_key = UnifiedMacPortalClient._get_fastest_engine_cache_key(account.server_url)
    cache.delete(fastest_key)
    
    return Response({
        'status': 'cleared',
        'account_id': account.id,
        'message': 'Benchmark cache cleared successfully'
    })
