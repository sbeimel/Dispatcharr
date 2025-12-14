"""
Predictive Failover System for Dispatcharr.

This module provides proactive stream failover capabilities by:
- Collecting stream metrics continuously
- Calculating risk scores based on metrics
- Learning from historical failure patterns
- Initiating failovers before users notice interruptions

The system is designed to be non-invasive, keeping the existing reactive
failover system as a fallback.
"""

from .config import PredictiveConfig, get_predictive_config, save_predictive_config, reset_predictive_config
from .redis_keys import PredictiveRedisKeys
from .serializers import PredictiveConfigSerializer
from .metrics_collector import (
    MetricType,
    Metric,
    StreamMetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)
from .risk_calculator import (
    RiskReason,
    RiskContribution,
    RiskScore,
    RiskScoreCalculator,
    get_risk_calculator,
    reset_risk_calculator,
)
from .pattern_analyzer import (
    FailurePatternData,
    PatternAnalyzer,
    get_pattern_analyzer,
    reset_pattern_analyzer,
)
from .warmup_manager import (
    WarmupStatus,
    WarmupManager,
    get_warmup_manager,
    reset_warmup_manager,
)
from .failover_manager import (
    FailoverDecision,
    PredictiveFailoverManager,
    get_predictive_failover_manager,
    reset_predictive_failover_manager,
)
from .mac_metrics import (
    MACMetrics,
    MACMetricsCollector,
    MACRiskScoreCalculator,
    MACWarmupManager,
    get_mac_metrics_collector,
    get_mac_risk_calculator,
    get_mac_warmup_manager,
    reset_mac_metrics,
)
from .provider_health import (
    HealthScore,
    ProviderHealthData,
    ProviderHealthScorer,
    get_provider_health_scorer,
    reset_provider_health_scorer,
)
from .qos_monitor import (
    QoSMetricType,
    QoSMetric,
    QoSScore,
    QoSMonitor,
    get_qos_monitor,
    reset_qos_monitor,
)
from .peak_time import (
    PeakTimeManager,
    get_peak_time_manager,
    reset_peak_time_manager,
)
from .graceful_degradation import (
    QualityLevel,
    QualityConfig,
    GracefulDegradationManager,
    get_degradation_manager,
    reset_degradation_manager,
)
from .analytics import (
    PredictiveAnalytics,
    get_predictive_analytics,
    reset_predictive_analytics,
)

# Models are imported lazily to avoid circular imports during Django setup
# Use: from apps.proxy.ts_proxy.predictive.models import FailurePattern, etc.

__all__ = [
    # Config
    'PredictiveConfig',
    'get_predictive_config',
    'save_predictive_config',
    'reset_predictive_config',
    # Redis Keys
    'PredictiveRedisKeys',
    # Serializers
    'PredictiveConfigSerializer',
    # Metrics Collector
    'MetricType',
    'Metric',
    'StreamMetricsCollector',
    'get_metrics_collector',
    'reset_metrics_collector',
    # Risk Calculator
    'RiskReason',
    'RiskContribution',
    'RiskScore',
    'RiskScoreCalculator',
    'get_risk_calculator',
    'reset_risk_calculator',
    # Pattern Analyzer
    'FailurePatternData',
    'PatternAnalyzer',
    'get_pattern_analyzer',
    'reset_pattern_analyzer',
    # Warmup Manager
    'WarmupStatus',
    'WarmupManager',
    'get_warmup_manager',
    'reset_warmup_manager',
    # Failover Manager
    'FailoverDecision',
    'PredictiveFailoverManager',
    'get_predictive_failover_manager',
    'reset_predictive_failover_manager',
    # MAC Metrics
    'MACMetrics',
    'MACMetricsCollector',
    'MACRiskScoreCalculator',
    'MACWarmupManager',
    'get_mac_metrics_collector',
    'get_mac_risk_calculator',
    'get_mac_warmup_manager',
    'reset_mac_metrics',
    # Provider Health
    'HealthScore',
    'ProviderHealthData',
    'ProviderHealthScorer',
    'get_provider_health_scorer',
    'reset_provider_health_scorer',
    # QoS Monitor
    'QoSMetricType',
    'QoSMetric',
    'QoSScore',
    'QoSMonitor',
    'get_qos_monitor',
    'reset_qos_monitor',
    # Peak Time
    'PeakTimeManager',
    'get_peak_time_manager',
    'reset_peak_time_manager',
    # Graceful Degradation
    'QualityLevel',
    'QualityConfig',
    'GracefulDegradationManager',
    'get_degradation_manager',
    'reset_degradation_manager',
    # Analytics
    'PredictiveAnalytics',
    'get_predictive_analytics',
    'reset_predictive_analytics',
]
