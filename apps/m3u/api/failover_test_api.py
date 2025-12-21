"""
Failover Test API Endpoints.

Provides REST API for the Failover Test Page.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class BackupStreamSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    url = serializers.URLField()
    priority = serializers.IntegerField(default=0)
    name = serializers.CharField(required=False, allow_blank=True, default='')


class MACPortalConfigSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    portal_url = serializers.CharField(required=False, allow_blank=True)
    macs = serializers.ListField(child=serializers.CharField(), required=False)
    endpoints = serializers.ListField(child=serializers.CharField(), required=False)
    user_agents = serializers.ListField(child=serializers.CharField(), required=False)


class TestChannelSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    primary_stream_url = serializers.URLField()
    backup_streams = BackupStreamSerializer(many=True, required=False)
    mac_portal_config = MACPortalConfigSerializer(required=False, allow_null=True)
    is_imported = serializers.BooleanField(read_only=True)
    original_channel_id = serializers.IntegerField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class InterruptRequestSerializer(serializers.Serializer):
    channel_id = serializers.CharField()
    error_type = serializers.ChoiceField(
        choices=['timeout', 'connection_reset', '403', '404', '500', 'stream_error'],
        default='timeout',
    )


class TestChannelViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        from ..failover_test_service import get_failover_test_service
        service = get_failover_test_service()
        channels = service.get_all_test_channels()
        data = [ch.to_dict() for ch in channels]
        return Response(data)
    
    def create(self, request):
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
        from ..failover_test_service import get_failover_test_service
        service = get_failover_test_service()
        channel = service.get_test_channel(pk)
        if not channel:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(channel.to_dict())
    
    def destroy(self, request, pk=None):
        from ..failover_test_service import get_failover_test_service
        from ..stream_simulation_service import get_stream_simulation_service
        service = get_failover_test_service()
        sim_service = get_stream_simulation_service()
        sim_service.stop_all_simulations(pk)
        result = service.delete_test_channel(pk)
        if not result:
            return Response({'error': 'Channel not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        from ..failover_test_service import get_failover_test_service
        service = get_failover_test_service()
        channels = service.get_available_channels()
        return Response(channels)
    
    @action(detail=False, methods=['post'])
    def import_channel(self, request):
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
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def interrupt(self, request):
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
    
    @action(detail=False, methods=['post'])
    def stop(self, request):
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
        from ..stream_simulation_service import get_stream_simulation_service
        service = get_stream_simulation_service()
        simulations = service.get_active_simulations()
        return Response({'active_simulations': simulations})


class StatisticsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        from ..failover_test_service import get_failover_test_service
        service = get_failover_test_service()
        stats = service.get_statistics()
        return Response(stats.to_dict())
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        from ..failover_test_service import get_failover_test_service
        service = get_failover_test_service()
        service.reset_statistics()
        return Response({'status': 'reset'})


class LogsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        from ..failover_test_service import get_failover_test_service
        limit = int(request.query_params.get('limit', 100))
        service = get_failover_test_service()
        entries = service.get_log_entries(limit=limit)
        return Response([e.to_dict() for e in entries])


class ExportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def logs(self, request):
        from ..failover_test_service import get_failover_test_service
        import json
        service = get_failover_test_service()
        data = service.export_logs_json()
        response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="failover_test_logs.json"'
        return response
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        from ..failover_test_service import get_failover_test_service
        service = get_failover_test_service()
        csv_data = service.export_statistics_csv()
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="failover_test_statistics.csv"'
        return response


class SettingsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        from ..mac_portal_models import FailoverSettings
        settings = FailoverSettings.get_settings()
        return Response({
            'mac_failover_enabled': settings.mac_failover_enabled,
            'portal_failover_enabled': settings.portal_failover_enabled,
            'stream_failover_enabled': settings.stream_failover_enabled,
            'endpoint_failover_enabled': settings.endpoint_failover_enabled,
            'useragent_failover_enabled': settings.useragent_failover_enabled,
            'mac_max_attempts': settings.mac_max_attempts,
            'failover_priority': settings.failover_priority,
        })


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
