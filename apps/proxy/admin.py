"""
Django Admin configuration for the Proxy app.

This module registers the Predictive Failover models with the Django admin interface.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.proxy.ts_proxy.predictive.models import (
    FailurePattern,
    PredictiveFailoverEvent,
    StreamPredictiveSettings,
)


@admin.register(FailurePattern)
class FailurePatternAdmin(admin.ModelAdmin):
    """Admin interface for FailurePattern model."""
    
    list_display = [
        'name',
        'pattern_type',
        'confidence_display',
        'status',
        'hit_count',
        'success_rate_display',
        'm3u_account',
        'last_hit',
    ]
    list_filter = [
        'status',
        'pattern_type',
        'm3u_account',
    ]
    search_fields = [
        'name',
        'm3u_account__name',
    ]
    readonly_fields = [
        'hit_count',
        'success_count',
        'false_positive_count',
        'last_hit',
        'created_at',
        'updated_at',
    ]
    ordering = ['-confidence', '-hit_count']
    
    fieldsets = (
        ('Pattern Information', {
            'fields': ('name', 'pattern_type', 'pattern_data', 'm3u_account')
        }),
        ('Confidence & Statistics', {
            'fields': ('confidence', 'hit_count', 'success_count', 'false_positive_count')
        }),
        ('Status', {
            'fields': ('status', 'last_hit', 'created_at', 'updated_at')
        }),
    )
    
    def confidence_display(self, obj):
        """Display confidence with color coding."""
        color = 'green' if obj.confidence >= 70 else 'orange' if obj.confidence >= 40 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>%',
            color,
            obj.confidence
        )
    confidence_display.short_description = 'Confidence'
    confidence_display.admin_order_field = 'confidence'
    
    def success_rate_display(self, obj):
        """Display success rate with color coding."""
        rate = obj.success_rate
        color = 'green' if rate >= 70 else 'orange' if rate >= 40 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}</span>%',
            color,
            rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    actions = ['mark_as_false_positive', 'mark_as_confirmed', 'disable_patterns', 'enable_patterns']
    
    @admin.action(description='Mark selected patterns as false positive')
    def mark_as_false_positive(self, request, queryset):
        count = queryset.update(status=FailurePattern.Status.FALSE_POSITIVE)
        self.message_user(request, f'{count} pattern(s) marked as false positive.')
    
    @admin.action(description='Mark selected patterns as confirmed')
    def mark_as_confirmed(self, request, queryset):
        count = queryset.update(status=FailurePattern.Status.CONFIRMED)
        self.message_user(request, f'{count} pattern(s) marked as confirmed.')
    
    @admin.action(description='Disable selected patterns')
    def disable_patterns(self, request, queryset):
        count = queryset.update(status=FailurePattern.Status.DISABLED)
        self.message_user(request, f'{count} pattern(s) disabled.')
    
    @admin.action(description='Enable selected patterns')
    def enable_patterns(self, request, queryset):
        count = queryset.filter(status=FailurePattern.Status.DISABLED).update(
            status=FailurePattern.Status.ACTIVE
        )
        self.message_user(request, f'{count} pattern(s) enabled.')


@admin.register(PredictiveFailoverEvent)
class PredictiveFailoverEventAdmin(admin.ModelAdmin):
    """Admin interface for PredictiveFailoverEvent model."""
    
    list_display = [
        'timestamp',
        'event_type',
        'channel_name',
        'risk_score_display',
        'success_display',
        'm3u_account',
    ]
    list_filter = [
        'event_type',
        'success',
        'm3u_account',
        ('timestamp', admin.DateFieldListFilter),
    ]
    search_fields = [
        'channel_name',
        'reason',
        'm3u_account__name',
    ]
    readonly_fields = [
        'timestamp',
        'event_type',
        'channel_id',
        'channel_name',
        'stream_id',
        'risk_score',
        'reason',
        'metrics_snapshot',
        'success',
        'pattern',
        'm3u_account',
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'timestamp', 'success')
        }),
        ('Stream/Channel', {
            'fields': ('channel_id', 'channel_name', 'stream_id', 'm3u_account')
        }),
        ('Risk Assessment', {
            'fields': ('risk_score', 'reason', 'pattern')
        }),
        ('Metrics Snapshot', {
            'fields': ('metrics_snapshot',),
            'classes': ('collapse',)
        }),
    )
    
    def risk_score_display(self, obj):
        """Display risk score with color coding."""
        if obj.risk_score is None:
            return '-'
        color = 'red' if obj.risk_score >= 85 else 'orange' if obj.risk_score >= 60 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.risk_score
        )
    risk_score_display.short_description = 'Risk Score'
    risk_score_display.admin_order_field = 'risk_score'
    
    def success_display(self, obj):
        """Display success status with icons."""
        if obj.success is None:
            return '-'
        icon = '✓' if obj.success else '✗'
        color = 'green' if obj.success else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            icon
        )
    success_display.short_description = 'Success'
    success_display.admin_order_field = 'success'
    
    def has_add_permission(self, request):
        """Disable adding events manually - they should be created by the system."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing events - they are immutable logs."""
        return False


@admin.register(StreamPredictiveSettings)
class StreamPredictiveSettingsAdmin(admin.ModelAdmin):
    """Admin interface for StreamPredictiveSettings model."""
    
    list_display = [
        'get_target_display',
        'sensitivity',
        'custom_warmup_threshold',
        'custom_failover_threshold',
        'false_positive_rate_display',
        'total_predictions',
        'updated_at',
    ]
    list_filter = [
        'sensitivity',
        'm3u_account',
    ]
    search_fields = [
        'channel_id',
        'm3u_account__name',
    ]
    readonly_fields = [
        'false_positive_count',
        'total_predictions',
        'created_at',
        'updated_at',
    ]
    ordering = ['-updated_at']
    
    fieldsets = (
        ('Target', {
            'fields': ('channel_id', 'm3u_account')
        }),
        ('Sensitivity Settings', {
            'fields': ('sensitivity', 'custom_warmup_threshold', 'custom_failover_threshold')
        }),
        ('Statistics', {
            'fields': ('false_positive_count', 'total_predictions', 'created_at', 'updated_at')
        }),
    )
    
    def get_target_display(self, obj):
        """Display the target (channel or account)."""
        if obj.channel_id:
            return f'Channel: {obj.channel_id}'
        elif obj.m3u_account:
            return f'Portal: {obj.m3u_account.name}'
        return 'Unknown'
    get_target_display.short_description = 'Target'
    
    def false_positive_rate_display(self, obj):
        """Display false positive rate with color coding."""
        rate = obj.false_positive_rate
        color = 'red' if rate > 30 else 'orange' if rate > 15 else 'green'
        return format_html(
            '<span style="color: {};">{:.1f}</span>%',
            color,
            rate
        )
    false_positive_rate_display.short_description = 'FP Rate'
