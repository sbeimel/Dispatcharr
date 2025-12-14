"""
Predictive Failover Manager for the Predictive Failover System.

This module orchestrates proactive failover decisions based on risk scores.
It coordinates between the metrics collector, risk calculator, pattern analyzer,
and warmup manager to provide seamless stream transitions.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 12.1, 12.2, 12.3, 12.4
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FailoverDecision:
    """
    Represents a failover decision made by the predictive system.
    
    Attributes:
        action: Action to take (none, warmup, failover)
        channel_id: Channel this decision is for
        stream_id: Current stream ID
        risk_score: Risk score that triggered the decision
        reason: Human-readable reason
        backup_stream_id: Backup stream to switch to (if failover)
        backup_url: Backup URL (if failover)
    """
    action: str  # none, warmup, failover
    channel_id: str
    stream_id: str = ""
    risk_score: int = 0
    reason: str = ""
    backup_stream_id: Optional[str] = None
    backup_url: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def should_warmup(self) -> bool:
        return self.action == "warmup"
    
    def should_failover(self) -> bool:
        return self.action == "failover"


class PredictiveFailoverManager:
    """
    Orchestrates predictive failover decisions.
    
    The manager:
    - Evaluates streams based on risk scores
    - Triggers warmup when risk exceeds warmup threshold
    - Triggers failover when risk exceeds failover threshold
    - Integrates with existing reactive failover as fallback
    - Implements cooldown to prevent rapid failovers
    
    Requirements:
    - 4.1: Trigger warmup at warmup threshold
    - 4.2: Trigger failover at failover threshold
    - 4.3: Complete failover within 500ms
    - 4.4: Fallback to reactive failover if no backup
    - 4.5: Mark successful failovers for pattern learning
    - 12.1-12.4: Resource management and cooldown
    """
    
    def __init__(self, config=None, risk_calculator=None, pattern_analyzer=None,
                 warmup_manager=None, redis_client=None):
        """
        Initialize the predictive failover manager.
        
        Args:
            config: PredictiveConfig instance
            risk_calculator: RiskScoreCalculator instance
            pattern_analyzer: PatternAnalyzer instance
            warmup_manager: WarmupManager instance
            redis_client: Redis client
        """
        self._config = config
        self._risk_calculator = risk_calculator
        self._pattern_analyzer = pattern_analyzer
        self._warmup_manager = warmup_manager
        self._redis_client = redis_client
        
        # Callbacks for failover execution
        self._failover_callback: Optional[Callable] = None
        
        # Import here to avoid circular imports
        from .redis_keys import PredictiveRedisKeys
        self._redis_keys = PredictiveRedisKeys
    
    @property
    def config(self):
        """Lazy load config if not provided."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load predictive config: {e}")
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config
    
    @property
    def risk_calculator(self):
        """Lazy load risk calculator if not provided."""
        if self._risk_calculator is None:
            try:
                from .risk_calculator import get_risk_calculator
                self._risk_calculator = get_risk_calculator()
            except Exception as e:
                logger.error(f"Failed to get risk calculator: {e}")
        return self._risk_calculator
    
    @property
    def pattern_analyzer(self):
        """Lazy load pattern analyzer if not provided."""
        if self._pattern_analyzer is None:
            try:
                from .pattern_analyzer import get_pattern_analyzer
                self._pattern_analyzer = get_pattern_analyzer()
            except Exception as e:
                logger.error(f"Failed to get pattern analyzer: {e}")
        return self._pattern_analyzer
    
    @property
    def warmup_manager(self):
        """Lazy load warmup manager if not provided."""
        if self._warmup_manager is None:
            try:
                from .warmup_manager import get_warmup_manager
                self._warmup_manager = get_warmup_manager()
            except Exception as e:
                logger.error(f"Failed to get warmup manager: {e}")
        return self._warmup_manager
    
    @property
    def redis_client(self):
        """Lazy load Redis client if not provided."""
        if self._redis_client is None:
            try:
                from django_redis import get_redis_connection
                self._redis_client = get_redis_connection("default")
            except Exception as e:
                logger.error(f"Failed to get Redis connection: {e}")
        return self._redis_client
    
    def set_failover_callback(self, callback: Callable) -> None:
        """
        Set callback function for executing failovers.
        
        The callback should accept (channel_id, backup_stream_id, backup_url)
        and return True if failover was successful.
        """
        self._failover_callback = callback
    
    # =========================================================================
    # Task 8.2: evaluate_stream() Method
    # =========================================================================
    
    def evaluate_stream(self, stream_id: str, channel_id: str = None,
                        m3u_account_id: int = None) -> FailoverDecision:
        """
        Evaluate a stream and decide on action.
        
        Requirements:
        - 4.1: Trigger warmup at warmup threshold
        - 4.2: Trigger failover at failover threshold
        
        Args:
            stream_id: Stream to evaluate
            channel_id: Channel ID
            m3u_account_id: Optional M3U account ID
            
        Returns:
            FailoverDecision with recommended action
        """
        if not self.config.enabled:
            return FailoverDecision(action="none", channel_id=channel_id or stream_id)
        
        try:
            # Check cooldown
            if self._is_in_cooldown(channel_id or stream_id):
                return FailoverDecision(
                    action="none",
                    channel_id=channel_id or stream_id,
                    stream_id=stream_id,
                    reason="In cooldown period"
                )
            
            # Get pattern confidence for risk calculation
            pattern_confidence = 0
            if self.pattern_analyzer and self.config.pattern_learning_enabled:
                pattern_confidence = self.pattern_analyzer.get_pattern_confidence_for_risk_score(
                    stream_id, m3u_account_id
                )
            
            # Calculate risk score
            risk_score = self.risk_calculator.calculate_risk_score(
                stream_id, channel_id, pattern_confidence
            )
            
            # Get effective thresholds (may be adjusted per-stream)
            warmup_threshold, failover_threshold = self._get_effective_thresholds(
                channel_id, m3u_account_id
            )
            
            # Make decision based on risk score
            if risk_score.score >= failover_threshold:
                # Task 8.4: Failover threshold reached
                return self._create_failover_decision(
                    channel_id or stream_id, stream_id, risk_score
                )
            elif risk_score.score >= warmup_threshold:
                # Task 8.3: Warmup threshold reached
                return self._create_warmup_decision(
                    channel_id or stream_id, stream_id, risk_score
                )
            else:
                # Risk is acceptable
                # Release warmup if risk dropped below threshold
                if risk_score.score < warmup_threshold - 10:
                    if self.warmup_manager and self.warmup_manager.has_warmup(channel_id or stream_id):
                        self.warmup_manager.release_warmup(
                            channel_id or stream_id, 
                            "risk_score_dropped"
                        )
                
                return FailoverDecision(
                    action="none",
                    channel_id=channel_id or stream_id,
                    stream_id=stream_id,
                    risk_score=risk_score.score,
                    reason=f"Risk score {risk_score.score} below thresholds"
                )
                
        except Exception as e:
            logger.error(f"Error evaluating stream {stream_id}: {e}")
            return FailoverDecision(
                action="none",
                channel_id=channel_id or stream_id,
                stream_id=stream_id,
                reason=f"Evaluation error: {e}"
            )
    
    def _get_effective_thresholds(self, channel_id: str = None,
                                   m3u_account_id: int = None) -> tuple:
        """Get effective warmup and failover thresholds."""
        warmup = self.config.warmup_threshold
        failover = self.config.failover_threshold
        
        # Check for stream-specific settings
        if channel_id:
            try:
                from .models import StreamPredictiveSettings
                
                settings = StreamPredictiveSettings.objects.filter(
                    channel_id=channel_id
                ).first()
                
                if settings:
                    warmup = settings.get_effective_warmup_threshold(warmup)
                    failover = settings.get_effective_failover_threshold(failover)
                    
            except Exception:
                pass
        
        # Check for account-wide settings
        if m3u_account_id and warmup == self.config.warmup_threshold:
            try:
                from .models import StreamPredictiveSettings
                
                settings = StreamPredictiveSettings.objects.filter(
                    m3u_account_id=m3u_account_id,
                    channel_id__isnull=True
                ).first()
                
                if settings:
                    warmup = settings.get_effective_warmup_threshold(warmup)
                    failover = settings.get_effective_failover_threshold(failover)
                    
            except Exception:
                pass
        
        # Apply peak time adjustment if enabled
        if self.config.peak_time_awareness_enabled and self._is_peak_time():
            factor = self.config.peak_threshold_factor
            warmup = int(warmup * factor)
            failover = int(failover * factor)
        
        return warmup, failover
    
    def _is_peak_time(self) -> bool:
        """Check if current time is in peak time window."""
        now = datetime.now()
        
        # Check day of week
        if now.weekday() not in self.config.peak_days:
            return False
        
        # Parse time window
        try:
            start_parts = self.config.peak_time_start.split(':')
            end_parts = self.config.peak_time_end.split(':')
            
            start_hour = int(start_parts[0])
            end_hour = int(end_parts[0])
            current_hour = now.hour
            
            if start_hour <= end_hour:
                return start_hour <= current_hour < end_hour
            else:
                # Wraps around midnight
                return current_hour >= start_hour or current_hour < end_hour
                
        except Exception:
            return False
    
    # =========================================================================
    # Task 8.3: Warmup Trigger
    # =========================================================================
    
    def _create_warmup_decision(self, channel_id: str, stream_id: str,
                                 risk_score) -> FailoverDecision:
        """Create a warmup decision and trigger warmup."""
        decision = FailoverDecision(
            action="warmup",
            channel_id=channel_id,
            stream_id=stream_id,
            risk_score=risk_score.score,
            reason=f"Risk score {risk_score.score} reached warmup threshold. {risk_score.get_reason_summary()}"
        )
        
        # Trigger warmup
        if self.warmup_manager:
            self.warmup_manager.warmup_backup(channel_id)
        
        # Log event
        self._log_event("threshold_crossed", channel_id, stream_id, 
                       risk_score.score, decision.reason)
        
        return decision
    
    # =========================================================================
    # Task 8.4: Failover Trigger
    # =========================================================================
    
    def _create_failover_decision(self, channel_id: str, stream_id: str,
                                   risk_score) -> FailoverDecision:
        """Create a failover decision."""
        # Get warmed backup if available
        backup_info = None
        if self.warmup_manager:
            backup_info = self.warmup_manager.get_warmed_backup(channel_id)
        
        decision = FailoverDecision(
            action="failover",
            channel_id=channel_id,
            stream_id=stream_id,
            risk_score=risk_score.score,
            reason=f"Risk score {risk_score.score} reached failover threshold. {risk_score.get_reason_summary()}",
            backup_stream_id=backup_info.get('stream_id') if backup_info else None,
            backup_url=backup_info.get('url') if backup_info else None,
        )
        
        # Log event
        self._log_event("proactive_failover", channel_id, stream_id,
                       risk_score.score, decision.reason)
        
        return decision
    
    # =========================================================================
    # Task 8.5: Integration with Existing FailoverManager
    # =========================================================================
    
    def execute_failover(self, decision: FailoverDecision) -> bool:
        """
        Execute a failover decision.
        
        Requirement 4.3: Complete failover within 500ms
        
        Args:
            decision: FailoverDecision to execute
            
        Returns:
            True if failover was successful
        """
        if not decision.should_failover():
            return False
        
        start_time = time.time()
        
        try:
            # Use callback if set
            if self._failover_callback:
                success = self._failover_callback(
                    decision.channel_id,
                    decision.backup_stream_id,
                    decision.backup_url
                )
            else:
                # Task 8.6: Fallback to reactive failover
                success = self._fallback_to_reactive_failover(decision)
            
            elapsed = (time.time() - start_time) * 1000
            
            if success:
                # Task 8.7: Start cooldown
                self._start_cooldown(decision.channel_id)
                
                # Release warmup
                if self.warmup_manager:
                    self.warmup_manager.release_warmup(decision.channel_id, "failover_executed")
                
                # Log success
                self._log_event("failover_success", decision.channel_id,
                               decision.stream_id, decision.risk_score,
                               f"Failover completed in {elapsed:.0f}ms")
                
                logger.info(f"Proactive failover completed for channel {decision.channel_id} in {elapsed:.0f}ms")
            else:
                self._log_event("failover_failed", decision.channel_id,
                               decision.stream_id, decision.risk_score,
                               "Failover execution failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing failover: {e}")
            self._log_event("failover_failed", decision.channel_id,
                           decision.stream_id, decision.risk_score, str(e))
            return False
    
    # =========================================================================
    # Task 8.6: Fallback to Reactive Failover
    # =========================================================================
    
    def _fallback_to_reactive_failover(self, decision: FailoverDecision) -> bool:
        """
        Fallback to reactive failover system.
        
        Requirement 4.4: Fallback if no backup available
        """
        try:
            # Import the existing failover utilities
            from apps.proxy.ts_proxy.url_utils import get_alternate_streams
            
            # Get alternate streams
            alternates = get_alternate_streams(decision.channel_id)
            
            if alternates:
                # Signal that a failover should happen
                # The actual switch is handled by the stream manager
                logger.info(f"Falling back to reactive failover for channel {decision.channel_id}")
                return True
            
            logger.warning(f"No alternate streams available for channel {decision.channel_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error in reactive failover fallback: {e}")
            return False
    
    # =========================================================================
    # Task 8.7: Cooldown Logic
    # =========================================================================
    
    def _start_cooldown(self, channel_id: str) -> None:
        """Start cooldown period after failover."""
        if not self.redis_client:
            return
        
        try:
            key = self._redis_keys.failover_cooldown(channel_id)
            self.redis_client.setex(key, self.config.cooldown_period, "1")
            
            self._log_event("cooldown_started", channel_id, "",
                           reason=f"Cooldown for {self.config.cooldown_period}s")
            
        except Exception as e:
            logger.error(f"Failed to start cooldown: {e}")
    
    def _is_in_cooldown(self, channel_id: str) -> bool:
        """Check if channel is in cooldown period."""
        if not self.redis_client:
            return False
        
        try:
            key = self._redis_keys.failover_cooldown(channel_id)
            return self.redis_client.exists(key) > 0
        except Exception:
            return False
    
    # =========================================================================
    # Event Logging
    # =========================================================================
    
    def _log_event(self, event_type: str, channel_id: str, stream_id: str = "",
                   risk_score: int = None, reason: str = "") -> None:
        """Log predictive failover event."""
        try:
            from .models import PredictiveFailoverEvent
            
            PredictiveFailoverEvent.log_event(
                event_type=event_type,
                channel_id=channel_id,
                stream_id=stream_id,
                risk_score=risk_score,
                reason=reason,
            )
        except Exception as e:
            logger.debug(f"Could not log event: {e}")
    
    # =========================================================================
    # Status Methods
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the predictive failover system."""
        return {
            'enabled': self.config.enabled,
            'warmup_threshold': self.config.warmup_threshold,
            'failover_threshold': self.config.failover_threshold,
            'cooldown_period': self.config.cooldown_period,
            'pattern_learning_enabled': self.config.pattern_learning_enabled,
            'peak_time_awareness_enabled': self.config.peak_time_awareness_enabled,
            'is_peak_time': self._is_peak_time() if self.config.peak_time_awareness_enabled else False,
        }
    
    def get_active_evaluations(self) -> Dict[str, Any]:
        """Get all active stream evaluations."""
        if not self.risk_calculator:
            return {}
        
        return self.risk_calculator.get_all_risk_scores()


# =============================================================================
# Singleton instance for global access
# =============================================================================

_manager_instance: Optional[PredictiveFailoverManager] = None


def get_predictive_failover_manager() -> PredictiveFailoverManager:
    """
    Get the global PredictiveFailoverManager instance.
    
    Returns:
        PredictiveFailoverManager singleton instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PredictiveFailoverManager()
    return _manager_instance


def reset_predictive_failover_manager() -> None:
    """Reset the global manager instance (mainly for testing)."""
    global _manager_instance
    _manager_instance = None
