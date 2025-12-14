"""
Failover Test API Endpoints.

Provides REST API for the Failover Test Page.

Requirements: 1.1, 1.2, 2.1, 2.3, 2.5, 3.1, 3.4, 3.5, 6.1, 6.4, 8.1, 9.1, 9.2, 9.3
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.http import HttpResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Serializers
# =============================================================================

class BackupStreamSerializer(serializers.Serializer):
    """Serializer for backup streams."""
    id = serializers.CharField(read_only=True)
    url = serializers.URLField()
    priority = serializers.IntegerField(default=0)
    name = serializers.CharField(required=False, allow_blank=True, default='')


class MACPortalConfigSerializer(serializers.Serializer):
    """Serializer for MAC portal configuration."""
    account_id = serializers.IntegerField()
    portal_url = serializers.CharField(required=False, allow_blank=True)
    macs = serializers.ListField(child=serializers.CharField(), required=False)
    endpoints = serializers.ListField(child=serializers.CharField(), required=False)
    user_agents = serializers.ListField(child=serializers.CharField(), required=False)


class TestChannelSerializer(serializers.Serializer):
    """Serializer for test channels."""
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    primary_stream_url = serializers.URLField()
    backup_streams = BackupStreamSerializer(many=True, required=False)
    mac_portal_config = MACPortalConfigSerializer(required=False, allow_null=True)
    is_imported = serializers.BooleanField(read_only=True)
    original_channel_id = serializers.IntegerField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class SimulationConfigSerializer(serializers.Serializer):
    """Serializer for simulation configuration."""
    interval_ms = serializers.IntegerField(default=5000, min_value=1000, max_value=60000)
    error_types = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'timeout', 'connection_reset', '403', '404', '500', 'stream_error'
        ]),
        required=False,
    )
    max_interruptions = serializers.IntegerField(default=10, min_value=1, max_value=100)


class InterruptRequestSerializer(serializers.Serializer):
    """Serializer for interrupt request."""
    channel_id = serializers.CharField()
    error_type = serializers.ChoiceField(
        choices=['timeout', 'connection_reset', '403', '404', '500', 'stream_error'],
        default='timeout',
    )


class AutoSimulationRequestSerializer(serializers.Serializer):
    """Serializer for auto-simulation request."""
    channel_id = serializers.CharField()
    config = SimulationConfigSerializer()


class LogEntrySerializer(serializers.Serializer):
    """Serializer for log entries."""
    id = serializers.CharField()
    timestamp = serializers.DateTimeField()
    event_type = serializers.CharField()
    strategy = serializers.CharField()
    original_value = serializers.CharField()
    new_value = serializers.CharField()
    reason = serializers.CharField()
    success = serializers.BooleanField()
    duration_ms = serializers.IntegerField()
    details = serializers.DictField(required=False)


class StrategyStatsSerializer(serializers.Serializer):
    """Serializer for strategy statistics."""
    attempts = serializers.IntegerField()
    successes = serializers.IntegerField()
    failures = serializers.IntegerField()
    avg_time_ms = serializers.FloatField()


class TestStatisticsSerializer(serializers.Serializer):
    """Serializer for test statistics."""
    total_tests = serializers.IntegerField()
    successful_failovers = serializers.IntegerField()
    failed_failovers = serializers.IntegerField()
    average_failover_time_ms = serializers.FloatField()
    strategy_stats = serializers.DictField(child=StrategyStatsSerializer())


class AvailableChannelSerializer(serializers.Serializer):
    """Serializer for available channels."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    channel_number = serializers.IntegerField(allow_null=True)


# =============================================================================
# ViewSets
# =============================================================================

class TestChannelViewSet(viewsets.ViewSet):
    """
    API endpoint for test channels.
    
    Requirements: 2.1, 2.3, 2.5, 8.1, 8.2
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/failover-test/channels/ - List all test channels."""
        from ..failover_test_service import get_failover_test_service
        
        service = get_failover_test_service()
        channels = service.get_all_test_channels()
        
        data = [ch.to_dict() for ch in channels]
        return Response(data)
    
    def create(self, request):
        """POST /api/failover-test/channels/ - Create a test channel."""
        from ..failover_test_service import get_failover_test_service
        
        serializer = TestChannelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_failover_test_service()
        
        try:
            channel = service.create_test_channel(serializer.validated_data)
            return Response(channel.to_dict(), status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """GET /api/failover-test/channels/{id}/ - Get a test channel."""
        from ..failover_test_service import get_failover_test_service
        
        service = get_failover_test_service()
        channel = service.get_test_channel(pk)
        
        if not channel:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(channel.to_dict())
    
    def destroy(self, request, pk=None):
        """DELETE /api/failover-test/channels/{id}/ - Delete a test channel."""
        from ..failover_test_service import get_failover_test_service
        from ..stream_simulation_service import get_stream_simulation_service
        
        service = get_failover_test_service()
        sim_service = get_stream_simulation_service()
        
        # Stop any simulations for this channel
        sim_service.stop_all_simulations(pk)
        
        result = service.delete_test_channel(pk)
        
        if not result:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """GET /api/failover-test/channels/available/ - Get available channels for import."""
        from ..failover_test_service import get_failover_test_service
        
        service = get_failover_test_service()
        channels = service.get_available_channels()
        
        return Response(channels)
    
    @action(detail=False, methods=['post'])
    def import_channel(self, request):
        """POST /api/failover-test/channels/import/ - Import an existing channel."""
        from ..failover_test_service import get_failover_test_service
        
        channel_id = request.data.get('channel_id')
        if not channel_id:
            return Response({'error': 'channel_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_failover_test_service()
        
        try:
            channel = service.import_channel(int(channel_id))
            return Response(channel.to_dict(), status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error importing channel: {e}")
            return Response({'error': 'Import failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SimulationViewSet(viewsets.ViewSet):
    """
    API endpoint for stream simulation.
    
    Requirements: 3.1, 3.4, 3.5
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def interrupt(self, request):
        """POST /api/failover-test/simulate/interrupt/ - Trigger immediate interruption."""
        from ..stream_simulation_service import get_stream_simulation_service
        
        serializer = InterruptRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_stream_simulation_service()
        
        result = service.simulate_error(
            serializer.validated_data['channel_id'],
            serializer.validated_data['error_type'],
        )
        
        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
    
    @action(detail=False, methods=['post'], url_path='auto-start')
    def auto_start(self, request):
        """POST /api/failover-test/simulate/auto-start/ - Start auto-simulation."""
        from ..stream_simulation_service import get_stream_simulation_service
        
        serializer = AutoSimulationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_stream_simulation_service()
        
        simulation_id = service.start_auto_simulation(
            serializer.validated_data['channel_id'],
            serializer.validated_data['config'],
        )
        
        return Response({
            'simulation_id': simulation_id,
            'status': 'started',
        })
    
    @action(detail=False, methods=['post'])
    def stop(self, request):
        """POST /api/failover-test/simulate/stop/ - Stop simulation."""
        from ..stream_simulation_service import get_stream_simulation_service
        
        simulation_id = request.data.get('simulation_id')
        channel_id = request.data.get('channel_id')
        
        service = get_stream_simulation_service()
        
        if simulation_id:
            result = service.stop_simulation(simulation_id)
        elif channel_id:
            service.stop_all_simulations(channel_id)
            result = True
        else:
            service.stop_all_simulations()
            result = True
        
        return Response({'stopped': result})
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """GET /api/failover-test/simulate/status/ - Get simulation status."""
        from ..stream_simulation_service import get_stream_simulation_service
        
        service = get_stream_simulation_service()
        simulations = service.get_active_simulations()
        
        return Response({'active_simulations': simulations})


class StatisticsViewSet(viewsets.ViewSet):
    """
    API endpoint for test statistics.
    
    Requirements: 6.1, 6.4
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/failover-test/statistics/ - Get test statistics."""
        from ..failover_test_service import get_failover_test_service
        
        service = get_failover_test_service()
        stats = service.get_statistics()
        
        return Response(stats.to_dict())
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """POST /api/failover-test/statistics/reset/ - Reset statistics."""
        from ..failover_test_service import get_failover_test_service
        
        service = get_failover_test_service()
        service.reset_statistics()
        
        return Response({'status': 'reset'})


class LogsViewSet(viewsets.ViewSet):
    """
    API endpoint for test logs.
    
    Requirements: 4.1
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/failover-test/logs/ - Get log entries."""
        from ..failover_test_service import get_failover_test_service
        
        limit = int(request.query_params.get('limit', 100))
        
        service = get_failover_test_service()
        entries = service.get_log_entries(limit=limit)
        
        return Response([e.to_dict() for e in entries])


class ExportViewSet(viewsets.ViewSet):
    """
    API endpoint for exporting test data.
    
    Requirements: 9.1, 9.2, 9.3
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def logs(self, request):
        """GET /api/failover-test/export/logs/ - Export logs as JSON."""
        from ..failover_test_service import get_failover_test_service
        import json
        
        service = get_failover_test_service()
        data = service.export_logs_json()
        
        response = HttpResponse(
            json.dumps(data, indent=2),
            content_type='application/json',
        )
        response['Content-Disposition'] = 'attachment; filename="failover_test_logs.json"'
        
        return response
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """GET /api/failover-test/export/statistics/ - Export statistics as CSV."""
        from ..failover_test_service import get_failover_test_service
        
        service = get_failover_test_service()
        csv_data = service.export_statistics_csv()
        
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="failover_test_statistics.csv"'
        
        return response


class SettingsViewSet(viewsets.ViewSet):
    """
    API endpoint for failover settings.
    
    Requirements: 1.2
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/failover-test/settings/ - Get current failover settings."""
        from ..mac_portal_models import FailoverSettings
        
        settings = FailoverSettings.get_settings()
        
        return Response({
            'mac_failover_enabled': settings.mac_failover_enabled,
            'portal_failover_enabled': settings.portal_failover_enabled,
            'stream_failover_enabled': settings.stream_failover_enabled,
            'endpoint_failover_enabled': settings.endpoint_failover_enabled,
            'useragent_failover_enabled': settings.useragent_failover_enabled,
            'mac_max_attempts': settings.mac_max_attempts,
            'stream_max_retries': settings.stream_max_retries,
            'failover_priority': settings.failover_priority,
        })


# =============================================================================
# URL Configuration
# =============================================================================

def get_failover_test_urls():
    """Get URL patterns for Failover Test API."""
    from rest_framework.routers import DefaultRouter
    
    router = DefaultRouter()
    router.register(r'failover-test/channels', TestChannelViewSet, basename='failover-test-channels')
    router.register(r'failover-test/simulate', SimulationViewSet, basename='failover-test-simulate')
    router.register(r'failover-test/statistics', StatisticsViewSet, basename='failover-test-statistics')
    router.register(r'failover-test/logs', LogsViewSet, basename='failover-test-logs')
    router.register(r'failover-test/export', ExportViewSet, basename='failover-test-export')
    router.register(r'failover-test/settings', SettingsViewSet, basename='failover-test-settings')
    
    return router.urls
