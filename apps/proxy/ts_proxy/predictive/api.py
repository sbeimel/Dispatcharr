"""
REST API Endpoints for the Predictive Failover System.

This module provides API endpoints for:
- Configuration management (GET/PUT/POST reset)
- Dashboard data (active streams, risk scores, events)
- Pattern management (CRUD operations)
- Stream-specific settings

Requirements: 6.1-6.6, 7.1-7.7, 8.1-8.7, 9.1-9.6
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .config import (
    PredictiveConfig,
    get_predictive_config,
    save_predictive_config,
    reset_predictive_config,
)
from .serializers import PredictiveConfigSerializer
from .models import (
    FailurePattern,
    PredictiveFailoverEvent,
    StreamPredictiveSettings,
)

logger = logging.getLogger(__name__)


# ============== Additional Serializers ==============

from rest_framework import serializers


class FailurePatternSerializer(serializers.ModelSerializer):
    """Serializer for FailurePattern model."""
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = FailurePattern
        fields = [
            'id', 'name', 'pattern_type', 'pattern_data',
            'confidence', 'hit_count', 'success_count', 'false_positive_count',
            'status', 'last_hit', 'created_at', 'updated_at',
            'm3u_account', 'success_rate'
        ]
        read_only_fields = [
            'id', 'hit_count', 'success_count', 'false_positive_count',
            'last_hit', 'created_at', 'updated_at', 'success_rate'
        ]


class StreamPredictiveSettingsSerializer(serializers.ModelSerializer):
    """Serializer for StreamPredictiveSettings model."""
    false_positive_rate = serializers.FloatField(read_only=True)
    should_suggest_lower_sensitivity = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = StreamPredictiveSettings
        fields = [
            'id', 'channel_id', 'm3u_account', 'sensitivity',
            'custom_warmup_threshold', 'custom_failover_threshold',
            'false_positive_count', 'total_predictions',
            'false_positive_rate', 'should_suggest_lower_sensitivity',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'false_positive_count', 'total_predictions',
            'false_positive_rate', 'should_suggest_lower_sensitivity',
            'created_at', 'updated_at'
        ]


class PredictiveFailoverEventSerializer(serializers.ModelSerializer):
    """Serializer for PredictiveFailoverEvent model."""
    event_type_display = serializers.CharField(
        source='get_event_type_display', read_only=True
    )
    
    class Meta:
        model = PredictiveFailoverEvent
        fields = [
            'id', 'event_type', 'event_type_display', 'timestamp',
            'channel_id', 'channel_name', 'stream_id',
            'risk_score', 'reason', 'metrics_snapshot',
            'success', 'pattern', 'm3u_account'
        ]


class RiskScoreSerializer(serializers.Serializer):
    """Serializer for risk score data."""
    stream_id = serializers.CharField()
    channel_id = serializers.UUIDField(allow_null=True)
    channel_name = serializers.CharField()
    risk_score = serializers.IntegerField()
    reasons = serializers.ListField(child=serializers.CharField())
    warmup_active = serializers.BooleanField()
    last_updated = serializers.DateTimeField()


class DashboardSerializer(serializers.Serializer):
    """Serializer for dashboard data."""
    enabled = serializers.BooleanField()
    active_streams = RiskScoreSerializer(many=True)
    warmup_status = serializers.DictField()
    recent_events = PredictiveFailoverEventSerializer(many=True)
    statistics = serializers.DictField()


# ============== ViewSets ==============

class PredictiveConfigViewSet(viewsets.ViewSet):
    """
    API endpoint for Predictive Failover configuration.
    
    Requirements: 6.1, 6.3, 6.4, 6.6
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        GET /api/settings/predictive-failover/
        
        Returns current predictive failover configuration.
        """
        config = get_predictive_config()
        serializer = PredictiveConfigSerializer(config.to_dict())
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """
        PUT /api/settings/predictive-failover/
        
        Update predictive failover configuration.
        """
        serializer = PredictiveConfigSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Merge with existing config
        current_config = get_predictive_config()
        config_dict = current_config.to_dict()
        config_dict.update(serializer.validated_data)
        
        # Create new config and save
        new_config = PredictiveConfig.from_dict(config_dict)
        
        if save_predictive_config(new_config):
            return Response(PredictiveConfigSerializer(new_config.to_dict()).data)
        else:
            return Response(
                {'error': 'Failed to save configuration'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """
        POST /api/settings/predictive-failover/reset/
        
        Reset configuration to defaults.
        """
        config = reset_predictive_config()
        serializer = PredictiveConfigSerializer(config.to_dict())
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """
        GET /api/settings/predictive-failover/defaults/
        
        Get default configuration values.
        """
        defaults = PredictiveConfig.get_defaults()
        serializer = PredictiveConfigSerializer(defaults.to_dict())
        return Response(serializer.data)


class PredictiveDashboardViewSet(viewsets.ViewSet):
    """
    API endpoint for Predictive Failover dashboard.
    
    Requirements: 7.1, 7.6, 7.7
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        GET /api/predictive-failover/dashboard/
        
        Returns dashboard data including active streams, risk scores,
        warmup status, recent events, and statistics.
        """
        config = get_predictive_config()
        
        # Get active streams with risk scores
        active_streams = self._get_active_streams_with_risk()
        
        # Get warmup status
        warmup_status = self._get_warmup_status()
        
        # Get recent events
        recent_events = PredictiveFailoverEvent.get_recent_events(limit=20)
        
        # Get statistics
        statistics = PredictiveFailoverEvent.get_statistics(days=7)
        
        data = {
            'enabled': config.enabled,
            'active_streams': active_streams,
            'warmup_status': warmup_status,
            'recent_events': PredictiveFailoverEventSerializer(recent_events, many=True).data,
            'statistics': statistics,
        }
        
        return Response(data)
    
    def _get_active_streams_with_risk(self):
        """Get list of active streams with their risk scores."""
        from .risk_calculator import RiskScoreCalculator
        from .metrics_collector import StreamMetricsCollector
        from django.utils import timezone
        
        active_streams = []
        
        try:
            # Get all streams being monitored from Redis
            collector = StreamMetricsCollector()
            monitored_streams = collector.get_monitored_streams()
            
            calculator = RiskScoreCalculator()
            
            for stream_info in monitored_streams:
                stream_id = stream_info.get('stream_id')
                if not stream_id:
                    continue
                
                # Calculate risk score
                risk_result = calculator.calculate_risk_score(stream_id)
                
                active_streams.append({
                    'stream_id': stream_id,
                    'channel_id': stream_info.get('channel_id'),
                    'channel_name': stream_info.get('channel_name', 'Unknown'),
                    'risk_score': risk_result.score,
                    'reasons': risk_result.reasons,
                    'warmup_active': stream_info.get('warmup_active', False),
                    'last_updated': timezone.now(),
                })
        except Exception as e:
            logger.error(f"Error getting active streams: {e}")
        
        return active_streams
    
    def _get_warmup_status(self):
        """Get current warmup status for all channels."""
        from .warmup_manager import WarmupManager
        
        try:
            manager = WarmupManager()
            return manager.get_all_warmup_status()
        except Exception as e:
            logger.error(f"Error getting warmup status: {e}")
            return {}
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        GET /api/predictive-failover/dashboard/statistics/
        
        Get detailed statistics.
        """
        days = int(request.query_params.get('days', 7))
        m3u_account_id = request.query_params.get('m3u_account')
        
        m3u_account = None
        if m3u_account_id:
            from apps.m3u.models import M3UAccount
            m3u_account = get_object_or_404(M3UAccount, pk=m3u_account_id)
        
        stats = PredictiveFailoverEvent.get_statistics(
            days=days,
            m3u_account=m3u_account
        )
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def events(self, request):
        """
        GET /api/predictive-failover/dashboard/events/
        
        Get recent events with filtering.
        """
        limit = int(request.query_params.get('limit', 50))
        event_type = request.query_params.get('event_type')
        channel_id = request.query_params.get('channel_id')
        m3u_account_id = request.query_params.get('m3u_account')
        
        queryset = PredictiveFailoverEvent.objects.all()
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if channel_id:
            queryset = queryset.filter(channel_id=channel_id)
        if m3u_account_id:
            queryset = queryset.filter(m3u_account_id=m3u_account_id)
        
        events = queryset[:limit]
        serializer = PredictiveFailoverEventSerializer(events, many=True)
        return Response(serializer.data)


class FailurePatternViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Failure Pattern management.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.6
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FailurePatternSerializer
    queryset = FailurePattern.objects.all()
    
    def get_queryset(self):
        """Filter patterns by status and m3u_account if provided."""
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        m3u_account_id = self.request.query_params.get('m3u_account')
        if m3u_account_id:
            queryset = queryset.filter(m3u_account_id=m3u_account_id)
        
        pattern_type = self.request.query_params.get('pattern_type')
        if pattern_type:
            queryset = queryset.filter(pattern_type=pattern_type)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """
        POST /api/predictive-failover/patterns/{id}/mark_false_positive/
        
        Mark pattern as false positive.
        """
        pattern = self.get_object()
        pattern.mark_as_false_positive()
        
        # Log the event
        PredictiveFailoverEvent.log_event(
            event_type=PredictiveFailoverEvent.EventType.FALSE_POSITIVE,
            reason=f"Pattern '{pattern.name}' marked as false positive by user",
            pattern=pattern
        )
        
        return Response({'status': 'marked_as_false_positive'})
    
    @action(detail=True, methods=['post'])
    def mark_confirmed(self, request, pk=None):
        """
        POST /api/predictive-failover/patterns/{id}/mark_confirmed/
        
        Mark pattern as confirmed (protected from cleanup).
        """
        pattern = self.get_object()
        pattern.mark_as_confirmed()
        return Response({'status': 'marked_as_confirmed'})
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """
        POST /api/predictive-failover/patterns/{id}/toggle_status/
        
        Toggle pattern between active and disabled.
        """
        pattern = self.get_object()
        
        if pattern.status == FailurePattern.Status.ACTIVE:
            pattern.disable()
            new_status = 'disabled'
        elif pattern.status == FailurePattern.Status.DISABLED:
            pattern.enable()
            new_status = 'active'
        else:
            return Response(
                {'error': f'Cannot toggle pattern with status {pattern.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'status': new_status})
    
    @action(detail=False, methods=['post'])
    def cleanup(self, request):
        """
        POST /api/predictive-failover/patterns/cleanup/
        
        Remove low-confidence patterns.
        """
        threshold = int(request.data.get('threshold', 30))
        deleted = FailurePattern.cleanup_low_confidence(threshold)
        return Response({'deleted': deleted})


class StreamPredictiveSettingsViewSet(viewsets.ViewSet):
    """
    API endpoint for stream-specific predictive settings.
    
    Requirements: 9.1, 9.2, 9.3, 9.5
    """
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, pk=None):
        """
        GET /api/streams/{id}/predictive-settings/
        
        Get predictive settings for a stream.
        """
        import uuid
        try:
            channel_id = uuid.UUID(pk)
        except ValueError:
            return Response(
                {'error': 'Invalid channel ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        settings = StreamPredictiveSettings.get_for_channel(channel_id)
        serializer = StreamPredictiveSettingsSerializer(settings)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """
        PUT /api/streams/{id}/predictive-settings/
        
        Update predictive settings for a stream.
        """
        import uuid
        try:
            channel_id = uuid.UUID(pk)
        except ValueError:
            return Response(
                {'error': 'Invalid channel ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        settings = StreamPredictiveSettings.get_for_channel(channel_id)
        serializer = StreamPredictiveSettingsSerializer(
            settings, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_account(self, request):
        """
        GET /api/streams/predictive-settings/by_account/?m3u_account={id}
        
        Get predictive settings for an M3U account.
        """
        m3u_account_id = request.query_params.get('m3u_account')
        if not m3u_account_id:
            return Response(
                {'error': 'm3u_account parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.m3u.models import M3UAccount
        m3u_account = get_object_or_404(M3UAccount, pk=m3u_account_id)
        
        settings = StreamPredictiveSettings.get_for_account(m3u_account)
        serializer = StreamPredictiveSettingsSerializer(settings)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def update_account(self, request):
        """
        PUT /api/streams/predictive-settings/update_account/
        
        Update predictive settings for an M3U account.
        """
        m3u_account_id = request.data.get('m3u_account')
        if not m3u_account_id:
            return Response(
                {'error': 'm3u_account parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.m3u.models import M3UAccount
        m3u_account = get_object_or_404(M3UAccount, pk=m3u_account_id)
        
        settings = StreamPredictiveSettings.get_for_account(m3u_account)
        serializer = StreamPredictiveSettingsSerializer(
            settings, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProviderHealthViewSet(viewsets.ViewSet):
    """
    API endpoint for Provider Health data.
    
    Requirements: 16.4, 16.5, 16.6, 16.7
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """
        GET /api/predictive-failover/provider-health/
        
        Returns provider health data including scores, problem MACs, and top performers.
        """
        try:
            from .provider_health import get_provider_health_scorer
            
            scorer = get_provider_health_scorer()
            
            # Get all health data
            providers = scorer.get_all_health_data() or {}
            
            # Get problem MACs
            problem_macs = scorer.get_problem_macs(threshold=50) or []
            
            # Get top performers
            top_performers = scorer.get_top_performers(limit=10) or []
            
            return Response({
                'providers': providers,
                'problem_macs': problem_macs,
                'top_performers': top_performers,
            })
        except Exception as e:
            logger.error(f"Error getting provider health data: {e}")
            # Return empty data instead of error to prevent frontend crash
            return Response({
                'providers': {},
                'problem_macs': [],
                'top_performers': [],
            })
    
    @action(detail=False, methods=['get'])
    def provider(self, request):
        """
        GET /api/predictive-failover/provider-health/provider/?account_id={id}
        
        Get health data for a specific provider.
        """
        account_id = request.query_params.get('account_id')
        if not account_id:
            return Response(
                {'error': 'account_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        provider = scorer.get_provider_health(int(account_id))
        
        if provider:
            return Response(provider.to_dict())
        return Response({'error': 'Provider not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def problem_macs(self, request):
        """
        GET /api/predictive-failover/provider-health/problem_macs/
        
        Get list of problematic MACs.
        """
        threshold = int(request.query_params.get('threshold', 50))
        account_id = request.query_params.get('account_id')
        
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        problems = scorer.get_problem_macs(
            account_id=int(account_id) if account_id else None,
            threshold=threshold
        )
        
        return Response(problems)
    
    @action(detail=False, methods=['get'])
    def top_performers(self, request):
        """
        GET /api/predictive-failover/provider-health/top_performers/
        
        Get list of top performing MACs.
        """
        limit = int(request.query_params.get('limit', 10))
        account_id = request.query_params.get('account_id')
        
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        performers = scorer.get_top_performers(
            account_id=int(account_id) if account_id else None,
            limit=limit
        )
        
        return Response(performers)
    
    @action(detail=False, methods=['get'])
    def ranked_providers(self, request):
        """
        GET /api/predictive-failover/provider-health/ranked_providers/
        
        Get providers ranked by health score.
        """
        from .provider_health import get_provider_health_scorer
        
        scorer = get_provider_health_scorer()
        ranked = scorer.get_ranked_providers()
        
        return Response([p.to_dict() for p in ranked])


class AnalyticsViewSet(viewsets.ViewSet):
    """
    API endpoint for Predictive Failover Analytics.
    
    Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        GET /api/predictive-failover/analytics/summary/
        
        Get analytics dashboard summary.
        """
        from .analytics import get_predictive_analytics
        
        analytics = get_predictive_analytics()
        return Response(analytics.get_dashboard_summary())
    
    @action(detail=False, methods=['get'])
    def comparison(self, request):
        """
        GET /api/predictive-failover/analytics/comparison/
        
        Get portal comparison data.
        """
        from .analytics import get_predictive_analytics
        
        analytics = get_predictive_analytics()
        return Response(analytics.get_portal_comparison())
    
    @action(detail=False, methods=['get'])
    def heatmap(self, request):
        """
        GET /api/predictive-failover/analytics/heatmap/
        
        Get failure heatmap data.
        """
        account_id = request.query_params.get('account_id')
        days = int(request.query_params.get('days', 7))
        
        from .analytics import get_predictive_analytics
        
        analytics = get_predictive_analytics()
        return Response(analytics.get_failure_heatmap(
            account_id=int(account_id) if account_id else None,
            days=days
        ))
    
    @action(detail=False, methods=['get'])
    def trend(self, request):
        """
        GET /api/predictive-failover/analytics/trend/
        
        Get health score trend for a provider.
        """
        account_id = request.query_params.get('account_id')
        days = int(request.query_params.get('days', 30))
        
        if not account_id:
            return Response(
                {'error': 'account_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .analytics import get_predictive_analytics
        
        analytics = get_predictive_analytics()
        return Response(analytics.get_health_trend(int(account_id), days))
    
    @action(detail=False, methods=['get'])
    def mac_stats(self, request):
        """
        GET /api/predictive-failover/analytics/mac_stats/
        
        Get MAC statistics for a provider.
        """
        account_id = request.query_params.get('account_id')
        
        if not account_id:
            return Response(
                {'error': 'account_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .analytics import get_predictive_analytics
        
        analytics = get_predictive_analytics()
        return Response(analytics.get_mac_statistics(int(account_id)))
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        GET /api/predictive-failover/analytics/export/
        
        Export analytics data.
        """
        format_type = request.query_params.get('format', 'json')
        
        from .analytics import get_predictive_analytics
        
        analytics = get_predictive_analytics()
        
        data = {
            'summary': analytics.get_dashboard_summary(),
            'comparison': analytics.get_portal_comparison(),
            'problem_macs': analytics.get_problem_macs_report(),
        }
        
        if format_type == 'csv':
            # Export comparison as CSV
            csv_data = analytics.export_to_csv(data['comparison'])
            return Response(csv_data, content_type='text/csv')
        else:
            return Response(data)


# ============== URL Configuration ==============

def get_predictive_failover_urls():
    """Get URL patterns for Predictive Failover API."""
    from rest_framework.routers import DefaultRouter
    
    router = DefaultRouter()
    router.register(
        r'settings/predictive-failover',
        PredictiveConfigViewSet,
        basename='predictive-config'
    )
    router.register(
        r'predictive-failover/dashboard',
        PredictiveDashboardViewSet,
        basename='predictive-dashboard'
    )
    router.register(
        r'predictive-failover/patterns',
        FailurePatternViewSet,
        basename='predictive-patterns'
    )
    router.register(
        r'streams/predictive-settings',
        StreamPredictiveSettingsViewSet,
        basename='stream-predictive-settings'
    )
    router.register(
        r'predictive-failover/provider-health',
        ProviderHealthViewSet,
        basename='provider-health'
    )
    router.register(
        r'predictive-failover/analytics',
        AnalyticsViewSet,
        basename='predictive-analytics'
    )
    
    return router.urls
