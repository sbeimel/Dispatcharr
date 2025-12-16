"""
Engine Benchmark API - Simple APIView implementation.

This provides a clean, working endpoint for engine benchmarking.
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

from ..models import M3UAccount

logger = logging.getLogger(__name__)


class EngineBenchmarkAPIView(APIView):
    """
    API endpoint for engine benchmarking.
    
    GET  /api/m3u-accounts/{id}/engine-benchmark/ - Get cached results
    POST /api/m3u-accounts/{id}/engine-benchmark/ - Run benchmark
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, account_pk):
        """Get cached benchmark results."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        from ..mac_portal_client import UnifiedMacPortalClient
        
        fastest_data = UnifiedMacPortalClient.get_fastest_engine(account.server_url)
        cached_engine = UnifiedMacPortalClient.get_cached_engine(account.server_url)
        
        return Response({
            'account_id': account.id,
            'portal_url': account.server_url,
            'fastest_engine': fastest_data,
            'cached_auto_engine': cached_engine,
            'has_benchmark': fastest_data is not None,
        })
    
    def post(self, request, account_pk):
        """Run benchmark for all engines."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        # Get first available MAC
        mac = account.macs.filter(status='valid').first()
        if not mac:
            mac = account.macs.first()
        
        if not mac:
            return Response(
                {'error': 'No MAC addresses available for this account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from ..mac_portal_client import UnifiedMacPortalClient
        
        try:
            results = UnifiedMacPortalClient.benchmark_all_engines(
                portal_url=account.server_url,
                mac=mac.address,
                proxy=account.proxy_url
            )
            
            # Save portal_info to account's custom_properties
            if results.get('portal_info'):
                portal_info = results['portal_info']
                custom_props = account.custom_properties or {}
                if portal_info.get('portal_type') and portal_info['portal_type'] != 'unknown':
                    custom_props['portal_type'] = portal_info['portal_type']
                if portal_info.get('portal_version'):
                    custom_props['portal_version'] = portal_info['portal_version']
                if portal_info.get('detected_by'):
                    custom_props['portal_detected_by'] = portal_info['detected_by']
                account.custom_properties = custom_props
                account.save(update_fields=['custom_properties'])
                logger.info(f"Saved portal_info for account {account_pk}: {portal_info}")
            
            return Response({
                'account_id': account.id,
                'portal_url': account.server_url,
                'mac_used': mac.address,
                **results
            })
        except Exception as e:
            logger.error(f"Benchmark failed for account {account_pk}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, account_pk):
        """Clear benchmark caches."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        from ..mac_portal_client import UnifiedMacPortalClient
        from django.core.cache import cache
        
        action = request.query_params.get('action', 'all')
        
        if action == 'auto':
            UnifiedMacPortalClient.clear_cached_engine(account.server_url)
            return Response({
                'status': 'auto_cleared',
                'account_id': account.id,
                'message': 'Auto engine cache cleared.',
            })
        else:
            fastest_key = UnifiedMacPortalClient._get_fastest_engine_cache_key(account.server_url)
            cache.delete(fastest_key)
            
            auto_key = UnifiedMacPortalClient._get_engine_cache_key(account.server_url)
            cache.delete(auto_key)
            
            return Response({
                'status': 'all_cleared',
                'account_id': account.id,
                'cleared': ['fastest_engine', 'auto_engine'],
            })


def get_engine_benchmark_urls():
    """Get URL patterns for Engine Benchmark API."""
    from django.urls import path
    
    return [
        path('m3u-accounts/<int:account_pk>/engine-benchmark/', 
             EngineBenchmarkAPIView.as_view(), 
             name='engine-benchmark'),
    ]
