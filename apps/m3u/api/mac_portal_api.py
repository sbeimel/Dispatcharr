"""
MAC Portal API Endpoints.

This module provides REST API endpoints for:
- Global Settings (10.1)
- Feature Toggles (10.2)
- Failover Settings (10.3)
- MAC Health (10.4)
- Batch Operations (10.5)
- Import/Export (10.6)
- Connection Test (10.7)
- Debug Logs (10.8)
- Failover Statistics (10.9)
- VOD/Series (10.10)
- MAC Portal Import (8.1-8.4)
  - Normalize Endpoint (8.1)
  - Validate Endpoint (8.2)
  - Import Endpoint (8.3)
  - MAC Management Endpoints (8.4)

Requirements: 44.1-44.4, 47.1-47.4, 49.1-49.4, 50.1-50.4, 51.1-51.4, 52.1-52.4, 53.1-53.4, 55.1, 55.4, 61.2
MAC Portal Import Requirements: 1.1-1.5, 2.1-2.5, 4.1-4.5, 5.1-5.2, 6.1-6.6, 9.1-9.4
"""

import logging
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

from ..models import M3UAccount, M3UAccountMac
from ..mac_portal_models import (
    MACPortalGlobalSettings,
    FailoverSettings,
    MACHealthRecord,
    FailoverEvent,
    MACCooldown,
)

logger = logging.getLogger(__name__)


# ============== Serializers ==============


class MACPortalGlobalSettingsSerializer(serializers.ModelSerializer):
    """Serializer for MACPortalGlobalSettings."""
    
    class Meta:
        model = MACPortalGlobalSettings
        exclude = ['id', 'created_at', 'updated_at']


class FailoverSettingsSerializer(serializers.ModelSerializer):
    """Serializer for FailoverSettings."""
    
    class Meta:
        model = FailoverSettings
        exclude = ['id', 'created_at', 'updated_at']


class MACHealthRecordSerializer(serializers.ModelSerializer):
    """Serializer for MACHealthRecord."""
    mac_address = serializers.CharField(source='mac.address', read_only=True)
    
    class Meta:
        model = MACHealthRecord
        fields = ['id', 'mac_address', 'timestamp', 'event_type', 'error_message', 
                  'response_time_ms', 'http_status', 'endpoint_used']


class MACCooldownSerializer(serializers.ModelSerializer):
    """Serializer for MACCooldown."""
    mac_address = serializers.CharField(source='mac.address', read_only=True)
    remaining_seconds = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = MACCooldown
        fields = ['id', 'mac_address', 'reason', 'started_at', 'expires_at', 
                  'is_active', 'remaining_seconds']


class FailoverEventSerializer(serializers.ModelSerializer):
    """Serializer for FailoverEvent."""
    
    class Meta:
        model = FailoverEvent
        fields = ['id', 'timestamp', 'failover_type', 'original_value', 
                  'new_value', 'reason', 'success', 'duration_ms']


class MACStatusSerializer(serializers.Serializer):
    """Serializer for MAC status."""
    address = serializers.CharField()
    status = serializers.CharField()
    health_score = serializers.IntegerField()
    in_cooldown = serializers.BooleanField()
    cooldown_remaining = serializers.IntegerField()
    cooldown_reason = serializers.CharField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    last_checked = serializers.DateTimeField(allow_null=True)


# ============== ViewSets ==============

class MACPortalSettingsViewSet(viewsets.ViewSet):
    """
    API endpoint for MAC Portal global settings.
    
    Requirements: 44.1, 44.2, 44.3, 44.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/mac-portal/settings/ - Get global settings."""
        settings = MACPortalGlobalSettings.get_settings()
        serializer = MACPortalGlobalSettingsSerializer(settings)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """PUT /api/mac-portal/settings/{pk}/ - Update global settings."""
        settings = MACPortalGlobalSettings.get_settings()
        serializer = MACPortalGlobalSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put', 'patch'])
    def save(self, request):
        """PUT/PATCH /api/mac-portal/settings/save/ - Update global settings (no pk required)."""
        settings = MACPortalGlobalSettings.get_settings()
        serializer = MACPortalGlobalSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """POST /api/mac-portal/settings/reset/ - Reset to defaults."""
        MACPortalGlobalSettings.objects.filter(pk=1).delete()
        settings = MACPortalGlobalSettings.get_settings()
        serializer = MACPortalGlobalSettingsSerializer(settings)
        return Response(serializer.data)


class FeatureTogglesViewSet(viewsets.ViewSet):
    """
    API endpoint for feature toggles.
    
    Requirements: 47.1, 47.2, 47.3, 47.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/mac-portal/features/ - Get feature toggles."""
        settings = MACPortalGlobalSettings.get_settings()
        features = {
            'cloudscraper_enabled': settings.cloudscraper_enabled,
            'vod_support_enabled': settings.vod_support_enabled,
            'series_support_enabled': settings.series_support_enabled,
            'epg_download_enabled': settings.epg_download_enabled,
            'short_epg_enabled': settings.short_epg_enabled,
            'picon_download_enabled': settings.picon_download_enabled,
            'tmdb_integration_enabled': settings.tmdb_integration_enabled,
            'stream_validation_enabled': settings.stream_validation_enabled,
            'multi_mac_rotation_enabled': settings.multi_mac_rotation_enabled,
            'token_auto_refresh_enabled': settings.token_auto_refresh_enabled,
            'debug_logging_enabled': settings.debug_logging_enabled,
            'ob2_2025_engine_enabled': settings.ob2_2025_engine_enabled,
            'portal_engine': settings.portal_engine,
        }
        return Response(features)
    
    def update(self, request, pk=None):
        """PUT /api/mac-portal/features/{pk}/ - Update feature toggles."""
        settings = MACPortalGlobalSettings.get_settings()
        
        for key, value in request.data.items():
            if hasattr(settings, key):
                if isinstance(value, bool) or key == 'portal_engine':
                    setattr(settings, key, value)
        
        settings.save()
        return self.list(request)
    
    @action(detail=False, methods=['put', 'patch'])
    def save(self, request):
        """PUT/PATCH /api/mac-portal/features/save/ - Update feature toggles (no pk required)."""
        settings = MACPortalGlobalSettings.get_settings()
        
        for key, value in request.data.items():
            if hasattr(settings, key):
                if isinstance(value, bool) or key == 'portal_engine':
                    setattr(settings, key, value)
        
        settings.save()
        return self.list(request)


class FailoverSettingsViewSet(viewsets.ViewSet):
    """
    API endpoint for failover settings.
    
    Requirements: 55.1, 55.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/mac-portal/failover-settings/ - Get failover settings."""
        settings = FailoverSettings.get_settings()
        serializer = FailoverSettingsSerializer(settings)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """PUT /api/mac-portal/failover-settings/{pk}/ - Update failover settings."""
        settings = FailoverSettings.get_settings()
        serializer = FailoverSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put', 'patch'])
    def save(self, request):
        """PUT/PATCH /api/mac-portal/failover-settings/save/ - Update failover settings (no pk required)."""
        settings = FailoverSettings.get_settings()
        serializer = FailoverSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class MACHealthViewSet(viewsets.ViewSet):
    """
    API endpoint for MAC health monitoring.
    
    Requirements: 49.1, 49.2, 49.3, 49.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/macs/health/ - Get all MAC health status."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        from ..mac_rotation_manager import MACRotationManagerRegistry
        manager = MACRotationManagerRegistry.get_or_create(account.id)
        
        statuses = manager.get_all_mac_statuses()
        serializer = MACStatusSerializer(statuses, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, account_pk=None, pk=None):
        """GET /api/m3u-accounts/{id}/macs/{mac_id}/health/ - Get specific MAC health."""
        mac = get_object_or_404(M3UAccountMac, pk=pk, account_id=account_pk)
        
        from ..mac_rotation_manager import MACRotationManagerRegistry
        manager = MACRotationManagerRegistry.get_or_create(account_pk)
        
        status_data = manager.get_mac_status(mac)
        serializer = MACStatusSerializer(status_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def history(self, request, account_pk=None, pk=None):
        """GET /api/m3u-accounts/{id}/macs/{mac_id}/health/history/ - Get MAC health history."""
        mac = get_object_or_404(M3UAccountMac, pk=pk, account_id=account_pk)
        
        records = MACHealthRecord.objects.filter(mac=mac).order_by('-timestamp')[:100]
        serializer = MACHealthRecordSerializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reset_cooldown(self, request, account_pk=None, pk=None):
        """POST /api/m3u-accounts/{id}/macs/{mac_id}/health/reset_cooldown/ - Reset MAC cooldown."""
        mac = get_object_or_404(M3UAccountMac, pk=pk, account_id=account_pk)
        
        from ..mac_rotation_manager import MACRotationManagerRegistry
        manager = MACRotationManagerRegistry.get_or_create(account_pk)
        manager.reset_cooldown(mac)
        
        return Response({'status': 'cooldown_reset', 'mac': mac.address})


class MACBatchOperationsViewSet(viewsets.ViewSet):
    """
    API endpoint for batch MAC operations.
    
    Requirements: 50.1, 50.2, 50.3, 50.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def batch_test(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/macs/batch-test/ - Test multiple MACs."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        mac_ids = request.data.get('mac_ids', [])
        
        if not mac_ids:
            # Test all MACs
            macs = account.macs.all()
        else:
            macs = account.macs.filter(id__in=mac_ids)
        
        results = []
        for mac in macs:
            result = self._test_mac(account, mac)
            results.append(result)
        
        return Response({'results': results})
    
    def _test_mac(self, account, mac):
        """Test a single MAC."""
        from ..mac_portal_client_extended import ExtendedMacPortalClient
        import time
        
        start_time = time.time()
        try:
            client = ExtendedMacPortalClient(
                base_url=account.server_url,
                mac=mac.address,
                proxy=account.proxy_url,
            )
            token = client.handshake()
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                'mac_id': mac.id,
                'address': mac.address,
                'success': True,
                'duration_ms': duration_ms,
                'token_obtained': bool(token),
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                'mac_id': mac.id,
                'address': mac.address,
                'success': False,
                'duration_ms': duration_ms,
                'error': str(e),
            }
    
    @action(detail=False, methods=['post'])
    def batch_enable(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/macs/batch-enable/ - Enable multiple MACs."""
        mac_ids = request.data.get('mac_ids', [])
        M3UAccountMac.objects.filter(id__in=mac_ids, account_id=account_pk).update(status='valid')
        return Response({'status': 'enabled', 'count': len(mac_ids)})
    
    @action(detail=False, methods=['post'])
    def batch_disable(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/macs/batch-disable/ - Disable multiple MACs."""
        mac_ids = request.data.get('mac_ids', [])
        M3UAccountMac.objects.filter(id__in=mac_ids, account_id=account_pk).update(status='disabled')
        return Response({'status': 'disabled', 'count': len(mac_ids)})


class MACImportExportViewSet(viewsets.ViewSet):
    """
    API endpoint for MAC import/export.
    
    Requirements: 51.1, 51.2, 51.3, 51.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def export(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/macs/export/ - Export MACs."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        macs = account.macs.all()
        export_data = [
            {
                'address': mac.address,
                'status': mac.status,
                'priority': mac.priority,
                'expires_at': mac.expires_at.isoformat() if mac.expires_at else None,
            }
            for mac in macs
        ]
        
        return Response({
            'account_id': account.id,
            'account_name': account.name,
            'mac_count': len(export_data),
            'macs': export_data,
        })
    
    @action(detail=False, methods=['post'])
    def import_macs(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/macs/import/ - Import MACs."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        macs_data = request.data.get('macs', [])
        replace = request.data.get('replace', False)
        
        if replace:
            account.macs.all().delete()
        
        imported = 0
        errors = []
        
        for mac_data in macs_data:
            address = mac_data.get('address', '').strip()
            if not address:
                continue
            
            try:
                mac, created = M3UAccountMac.objects.update_or_create(
                    account=account,
                    address=address,
                    defaults={
                        'status': mac_data.get('status', 'unknown'),
                        'priority': mac_data.get('priority', 0),
                    }
                )
                imported += 1
            except Exception as e:
                errors.append({'address': address, 'error': str(e)})
        
        return Response({
            'imported': imported,
            'errors': errors,
        })


class ConnectionTestViewSet(viewsets.ViewSet):
    """
    API endpoint for connection testing.
    
    Requirements: 52.1, 52.2, 52.3, 52.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def test(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/connection-test/ - Run connection test."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        results = {
            'account_id': account.id,
            'steps': [],
        }
        
        # Step 1: Portal URL resolution
        step1 = self._test_portal_resolution(account)
        results['steps'].append(step1)
        
        if not step1['success']:
            results['overall_success'] = False
            return Response(results)
        
        # Step 2: Handshake/Token
        step2 = self._test_handshake(account)
        results['steps'].append(step2)
        
        if not step2['success']:
            results['overall_success'] = False
            return Response(results)
        
        # Step 3: Channel list
        step3 = self._test_channel_list(account)
        results['steps'].append(step3)
        
        results['overall_success'] = all(s['success'] for s in results['steps'])
        return Response(results)
    
    def _test_portal_resolution(self, account):
        """Test portal URL resolution."""
        from ..mac_portal_client_extended import ExtendedMacPortalClient
        import time
        
        mac = account.macs.first()
        if not mac:
            return {'step': 'portal_resolution', 'success': False, 'error': 'No MAC addresses'}
        
        start = time.time()
        try:
            client = ExtendedMacPortalClient(
                base_url=account.server_url,
                mac=mac.address,
                proxy=account.proxy_url,
            )
            portal_url = client.resolve_portal_url()
            duration = int((time.time() - start) * 1000)
            
            return {
                'step': 'portal_resolution',
                'success': True,
                'portal_url': portal_url,
                'duration_ms': duration,
            }
        except Exception as e:
            return {
                'step': 'portal_resolution',
                'success': False,
                'error': str(e),
                'duration_ms': int((time.time() - start) * 1000),
            }
    
    def _test_handshake(self, account):
        """Test handshake/token acquisition."""
        from ..mac_portal_client_extended import ExtendedMacPortalClient
        import time
        
        mac = account.macs.first()
        start = time.time()
        try:
            client = ExtendedMacPortalClient(
                base_url=account.server_url,
                mac=mac.address,
                proxy=account.proxy_url,
            )
            token = client.handshake()
            duration = int((time.time() - start) * 1000)
            
            return {
                'step': 'handshake',
                'success': bool(token),
                'token_obtained': bool(token),
                'duration_ms': duration,
            }
        except Exception as e:
            return {
                'step': 'handshake',
                'success': False,
                'error': str(e),
                'duration_ms': int((time.time() - start) * 1000),
            }
    
    def _test_channel_list(self, account):
        """Test channel list retrieval."""
        from ..mac_portal_client_extended import ExtendedMacPortalClient
        import time
        
        mac = account.macs.first()
        start = time.time()
        try:
            client = ExtendedMacPortalClient(
                base_url=account.server_url,
                mac=mac.address,
                proxy=account.proxy_url,
            )
            client.handshake()
            channels = client.get_all_channels_raw()
            duration = int((time.time() - start) * 1000)
            
            return {
                'step': 'channel_list',
                'success': bool(channels),
                'channel_count': len(channels) if channels else 0,
                'duration_ms': duration,
            }
        except Exception as e:
            return {
                'step': 'channel_list',
                'success': False,
                'error': str(e),
                'duration_ms': int((time.time() - start) * 1000),
            }



class DebugLogsViewSet(viewsets.ViewSet):
    """
    API endpoint for debug logs.
    
    Requirements: 53.1, 53.2, 53.3, 53.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/mac-portal/logs/ - Get debug logs."""
        # Get recent health records as logs
        limit = int(request.query_params.get('limit', 100))
        event_type = request.query_params.get('type', None)
        mac_id = request.query_params.get('mac_id', None)
        
        queryset = MACHealthRecord.objects.all().order_by('-timestamp')
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if mac_id:
            queryset = queryset.filter(mac_id=mac_id)
        
        records = queryset[:limit]
        serializer = MACHealthRecordSerializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """DELETE /api/mac-portal/logs/clear/ - Clear old logs."""
        from django.utils import timezone
        from datetime import timedelta
        
        days = int(request.query_params.get('days', 7))
        cutoff = timezone.now() - timedelta(days=days)
        
        deleted, _ = MACHealthRecord.objects.filter(timestamp__lt=cutoff).delete()
        return Response({'deleted': deleted})


class FailoverStatisticsViewSet(viewsets.ViewSet):
    """
    API endpoint for failover statistics.
    
    Requirements: 61.2
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/failover-stats/ - Get failover statistics."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        days = int(request.query_params.get('days', 7))
        stats = FailoverEvent.get_statistics(account, days=days)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def events(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/failover-stats/events/ - Get failover events."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        limit = int(request.query_params.get('limit', 50))
        events = FailoverEvent.objects.filter(m3u_account=account).order_by('-timestamp')[:limit]
        
        serializer = FailoverEventSerializer(events, many=True)
        return Response(serializer.data)


class EngineBenchmarkViewSet(viewsets.ViewSet):
    """
    API endpoint for engine benchmarking.
    
    Allows testing all portal engines and finding the fastest one.
    
    URLs:
    - GET  /api/m3u-accounts/{id}/engine-benchmark/     - Get cached results
    - POST /api/m3u-accounts/{id}/engine-benchmark/     - Run benchmark (was /run/)
    - DELETE /api/m3u-accounts/{id}/engine-benchmark/   - Clear all caches (was /clear/)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/engine-benchmark/ - Get cached benchmark results."""
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
    
    def create(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/engine-benchmark/ - Run benchmark for all engines."""
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
    
    def destroy(self, request, account_pk=None, pk=None):
        """DELETE /api/m3u-accounts/{id}/engine-benchmark/{action}/ - Clear caches.
        
        pk='all' - Clear all caches
        pk='auto' - Clear only auto engine cache
        """
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        from ..mac_portal_client import UnifiedMacPortalClient
        from django.core.cache import cache
        
        if pk == 'auto':
            # Only clear auto engine cache - forces re-detection on next request
            UnifiedMacPortalClient.clear_cached_engine(account.server_url)
            return Response({
                'status': 'auto_cleared',
                'account_id': account.id,
                'message': 'Auto engine cache cleared. Next request will re-detect the best engine.',
            })
        else:
            # Clear all caches (default)
            fastest_key = UnifiedMacPortalClient._get_fastest_engine_cache_key(account.server_url)
            cache.delete(fastest_key)
            
            auto_key = UnifiedMacPortalClient._get_engine_cache_key(account.server_url)
            cache.delete(auto_key)
            
            return Response({
                'status': 'all_cleared',
                'account_id': account.id,
                'cleared': ['fastest_engine', 'auto_engine'],
            })


class VODSeriesAPIViewSet(viewsets.ViewSet):
    """
    API endpoint for VOD and Series.
    
    Requirements: 4.1-4.5, 13.1-13.4
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def vod_categories(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/vod/categories/ - Get VOD categories."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        if not account.enable_vod_scanning:
            return Response({'error': 'VOD scanning disabled'}, status=status.HTTP_400_BAD_REQUEST)
        
        from ..vod_series_client import VODImportManager
        manager = VODImportManager(account.id)
        categories = manager.import_vod_categories()
        
        return Response({'categories': categories})
    
    @action(detail=False, methods=['get'])
    def vod_items(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/vod/items/ - Get VOD items."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        if not account.enable_vod_scanning:
            return Response({'error': 'VOD scanning disabled'}, status=status.HTTP_400_BAD_REQUEST)
        
        category = request.query_params.get('category', '*')
        page = int(request.query_params.get('page', 1))
        search = request.query_params.get('search', '')
        
        from ..vod_series_client import VODImportManager
        manager = VODImportManager(account.id)
        client = manager._get_client()
        
        if not client:
            return Response({'error': 'No available MAC'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        items, total = client.get_vod_items(category_id=category, page=page, search=search)
        
        return Response({
            'items': items,
            'total': total,
            'page': page,
        })
    
    @action(detail=False, methods=['get'])
    def series_categories(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/series/categories/ - Get series categories."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        if not account.enable_vod_scanning:
            return Response({'error': 'VOD scanning disabled'}, status=status.HTTP_400_BAD_REQUEST)
        
        from ..vod_series_client import VODImportManager
        manager = VODImportManager(account.id)
        categories = manager.import_series_categories()
        
        return Response({'categories': categories})
    
    @action(detail=False, methods=['get'])
    def series_items(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/series/items/ - Get series items."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        if not account.enable_vod_scanning:
            return Response({'error': 'VOD scanning disabled'}, status=status.HTTP_400_BAD_REQUEST)
        
        category = request.query_params.get('category', '*')
        page = int(request.query_params.get('page', 1))
        search = request.query_params.get('search', '')
        
        from ..vod_series_client import VODImportManager
        manager = VODImportManager(account.id)
        client = manager._get_client()
        
        if not client:
            return Response({'error': 'No available MAC'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        items, total = client.get_series_items(category_id=category, page=page, search=search)
        
        return Response({
            'items': items,
            'total': total,
            'page': page,
        })
    
    @action(detail=False, methods=['post'])
    def save_resume_point(self, request, account_pk=None):
        """POST /api/m3u-accounts/{id}/vod/resume/ - Save resume point."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        vod_id = request.data.get('vod_id')
        position = request.data.get('position', 0)
        duration = request.data.get('duration')
        content_type = request.data.get('content_type', 'vod')
        
        if not vod_id:
            return Response({'error': 'vod_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from ..vod_series_client import ResumePointManager
        manager = ResumePointManager(account.id)
        manager.save_position(vod_id, position, duration, content_type)
        
        return Response({'status': 'saved'})
    
    @action(detail=False, methods=['get'])
    def get_resume_point(self, request, account_pk=None):
        """GET /api/m3u-accounts/{id}/vod/resume/ - Get resume point."""
        account = get_object_or_404(M3UAccount, pk=account_pk)
        
        vod_id = request.query_params.get('vod_id')
        content_type = request.query_params.get('content_type', 'vod')
        
        if not vod_id:
            return Response({'error': 'vod_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from ..vod_series_client import ResumePointManager
        manager = ResumePointManager(account.id)
        position = manager.get_position(vod_id, content_type)
        
        return Response({'vod_id': vod_id, 'position': position})


# ============== URL Configuration ==============

def get_mac_portal_urls():
    """Get URL patterns for MAC Portal API."""
    from rest_framework.routers import DefaultRouter
    
    router = DefaultRouter()
    router.register(r'mac-portal/settings', MACPortalSettingsViewSet, basename='mac-portal-settings')
    router.register(r'mac-portal/features', FeatureTogglesViewSet, basename='mac-portal-features')
    router.register(r'mac-portal/failover-settings', FailoverSettingsViewSet, basename='mac-portal-failover-settings')
    router.register(r'mac-portal/logs', DebugLogsViewSet, basename='mac-portal-logs')
    
    return router.urls


def get_mac_management_urls():
    """Get URL patterns for MAC Management API.
    
    Note: Engine Benchmark URLs are now in engine_benchmark_api.py
    """
    from rest_framework.routers import DefaultRouter
    
    router = DefaultRouter()
    
    # Register nested viewsets for account-specific MAC operations
    router.register(
        r'm3u-accounts/(?P<account_pk>\d+)/macs/health',
        MACHealthViewSet,
        basename='mac-health'
    )
    router.register(
        r'm3u-accounts/(?P<account_pk>\d+)/macs/batch',
        MACBatchOperationsViewSet,
        basename='mac-batch'
    )
    router.register(
        r'm3u-accounts/(?P<account_pk>\d+)/macs/import-export',
        MACImportExportViewSet,
        basename='mac-import-export'
    )
    router.register(
        r'm3u-accounts/(?P<account_pk>\d+)/connection-test',
        ConnectionTestViewSet,
        basename='connection-test'
    )
    router.register(
        r'm3u-accounts/(?P<account_pk>\d+)/failover-stats',
        FailoverStatisticsViewSet,
        basename='failover-stats'
    )
    router.register(
        r'm3u-accounts/(?P<account_pk>\d+)/vod-series',
        VODSeriesAPIViewSet,
        basename='vod-series'
    )
    
    return router.urls
