"""
MAC Portal Specific Metrics for the Predictive Failover System.

This module provides MAC-specific metrics collection and risk scoring:
- Token expiry tracking
- Portal response time tracking
- MAC-specific risk score factors
- MAC warmup before failover

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class MACMetrics:
    """
    MAC Portal specific metrics.
    
    Attributes:
        mac_address: The MAC address
        account_id: The M3U account ID
        token_ttl_seconds: Remaining token validity in seconds
        portal_response_time_ms: Last portal response time in milliseconds
        last_handshake_time: Timestamp of last successful handshake
        handshake_failures: Count of recent handshake failures
        portal_errors: Count of recent portal errors
    """
    mac_address: str
    account_id: int
    token_ttl_seconds: int = 0
    portal_response_time_ms: float = 0
    last_handshake_time: float = 0
    handshake_failures: int = 0
    portal_errors: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mac_address': self.mac_address,
            'account_id': self.account_id,
            'token_ttl_seconds': self.token_ttl_seconds,
            'portal_response_time_ms': self.portal_response_time_ms,
            'last_handshake_time': self.last_handshake_time,
            'handshake_failures': self.handshake_failures,
            'portal_errors': self.portal_errors,
        }


class MACMetricsCollector:
    """
    Collects MAC Portal specific metrics for predictive failover.
    
    Requirements:
    - 14.1: Track token expiry time
    - 14.2: Track portal response times
    - 14.3: Integrate with risk score calculation
    """
    
    def __init__(self, redis_client=None, config=None):
        """
        Initialize the MAC metrics collector.
        
        Args:
            redis_client: Redis client for storage
            config: PredictiveConfig instance
        """
        self._redis_client = redis_client
        self._config = config
        self._mac_metrics: Dict[str, MACMetrics] = {}
        
        from .redis_keys import PredictiveRedisKeys
        self._redis_keys = PredictiveRedisKeys
    
    @property
    def redis_client(self):
        """Lazy load Redis client."""
        if self._redis_client is None:
            try:
                from django_redis import get_redis_connection
                self._redis_client = get_redis_connection("default")
            except Exception as e:
                logger.error(f"Failed to get Redis connection: {e}")
        return self._redis_client
    
    @property
    def config(self):
        """Lazy load config."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config

    def record_token_ttl(self, mac_address: str, account_id: int, 
                         ttl_seconds: int) -> bool:
        """
        Record token TTL for a MAC address.
        
        Requirement 14.1: Track token expiry time
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            ttl_seconds: Remaining token validity in seconds
            
        Returns:
            True if recorded successfully
        """
        try:
            key = f"{account_id}:{mac_address}"
            
            if key not in self._mac_metrics:
                self._mac_metrics[key] = MACMetrics(
                    mac_address=mac_address,
                    account_id=account_id
                )
            
            self._mac_metrics[key].token_ttl_seconds = ttl_seconds
            
            # Also record as a metric for the stream
            from .metrics_collector import get_metrics_collector, MetricType
            collector = get_metrics_collector()
            
            # Find stream_id for this MAC
            stream_id = self._get_stream_id_for_mac(mac_address, account_id)
            if stream_id:
                collector.record_metric(
                    stream_id,
                    MetricType.MAC_TOKEN_TTL,
                    ttl_seconds,
                    {'mac_address': mac_address, 'account_id': account_id}
                )
            
            # Store in Redis
            self._store_mac_metrics(key)
            
            # Log warning if token is expiring soon
            if ttl_seconds < 120:  # Less than 2 minutes
                logger.warning(
                    f"MAC {mac_address[:8]}... token expiring in {ttl_seconds}s"
                )
            elif ttl_seconds < 300:  # Less than 5 minutes
                logger.info(
                    f"MAC {mac_address[:8]}... token expiring in {ttl_seconds}s"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record token TTL: {e}")
            return False
    
    def record_portal_response_time(self, mac_address: str, account_id: int,
                                     response_time_ms: float) -> bool:
        """
        Record portal response time for a MAC address.
        
        Requirement 14.2: Track portal response times
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            response_time_ms: Portal response time in milliseconds
            
        Returns:
            True if recorded successfully
        """
        try:
            key = f"{account_id}:{mac_address}"
            
            if key not in self._mac_metrics:
                self._mac_metrics[key] = MACMetrics(
                    mac_address=mac_address,
                    account_id=account_id
                )
            
            self._mac_metrics[key].portal_response_time_ms = response_time_ms
            
            # Also record as a metric for the stream
            from .metrics_collector import get_metrics_collector, MetricType
            collector = get_metrics_collector()
            
            stream_id = self._get_stream_id_for_mac(mac_address, account_id)
            if stream_id:
                collector.record_metric(
                    stream_id,
                    MetricType.PORTAL_RESPONSE_TIME,
                    response_time_ms,
                    {'mac_address': mac_address, 'account_id': account_id}
                )
            
            # Store in Redis
            self._store_mac_metrics(key)
            
            # Log warning for slow portal
            if response_time_ms > 5000:  # More than 5 seconds
                logger.warning(
                    f"MAC {mac_address[:8]}... portal very slow: {response_time_ms:.0f}ms"
                )
            elif response_time_ms > 2000:  # More than 2 seconds
                logger.info(
                    f"MAC {mac_address[:8]}... portal slow: {response_time_ms:.0f}ms"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record portal response time: {e}")
            return False
    
    def record_handshake_success(self, mac_address: str, account_id: int) -> bool:
        """
        Record successful handshake.
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            
        Returns:
            True if recorded successfully
        """
        try:
            key = f"{account_id}:{mac_address}"
            
            if key not in self._mac_metrics:
                self._mac_metrics[key] = MACMetrics(
                    mac_address=mac_address,
                    account_id=account_id
                )
            
            self._mac_metrics[key].last_handshake_time = time.time()
            self._mac_metrics[key].handshake_failures = 0
            
            self._store_mac_metrics(key)
            return True
            
        except Exception as e:
            logger.error(f"Failed to record handshake success: {e}")
            return False
    
    def record_handshake_failure(self, mac_address: str, account_id: int) -> bool:
        """
        Record handshake failure.
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            
        Returns:
            True if recorded successfully
        """
        try:
            key = f"{account_id}:{mac_address}"
            
            if key not in self._mac_metrics:
                self._mac_metrics[key] = MACMetrics(
                    mac_address=mac_address,
                    account_id=account_id
                )
            
            self._mac_metrics[key].handshake_failures += 1
            
            self._store_mac_metrics(key)
            
            logger.warning(
                f"MAC {mac_address[:8]}... handshake failure "
                f"(count: {self._mac_metrics[key].handshake_failures})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record handshake failure: {e}")
            return False
    
    def record_portal_error(self, mac_address: str, account_id: int,
                            error_type: str = None) -> bool:
        """
        Record portal error.
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            error_type: Optional error type description
            
        Returns:
            True if recorded successfully
        """
        try:
            key = f"{account_id}:{mac_address}"
            
            if key not in self._mac_metrics:
                self._mac_metrics[key] = MACMetrics(
                    mac_address=mac_address,
                    account_id=account_id
                )
            
            self._mac_metrics[key].portal_errors += 1
            
            self._store_mac_metrics(key)
            
            logger.warning(
                f"MAC {mac_address[:8]}... portal error: {error_type or 'unknown'}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record portal error: {e}")
            return False

    def get_mac_metrics(self, mac_address: str, account_id: int) -> Optional[MACMetrics]:
        """
        Get current metrics for a MAC address.
        
        Args:
            mac_address: The MAC address
            account_id: The M3U account ID
            
        Returns:
            MACMetrics object or None
        """
        key = f"{account_id}:{mac_address}"
        
        # Try memory first
        if key in self._mac_metrics:
            return self._mac_metrics[key]
        
        # Try Redis
        return self._load_mac_metrics(key)
    
    def _get_stream_id_for_mac(self, mac_address: str, account_id: int) -> Optional[str]:
        """Get the stream ID associated with a MAC address."""
        if not self.redis_client:
            return None
        
        try:
            # Look up in Redis mapping
            key = f"mac_stream_mapping:{account_id}:{mac_address}"
            stream_id = self.redis_client.get(key)
            if stream_id:
                if isinstance(stream_id, bytes):
                    stream_id = stream_id.decode('utf-8')
                return stream_id
            return None
        except Exception as e:
            logger.debug(f"Failed to get stream ID for MAC: {e}")
            return None
    
    def set_stream_mac_mapping(self, stream_id: str, mac_address: str, 
                                account_id: int) -> bool:
        """
        Set mapping between stream ID and MAC address.
        
        Args:
            stream_id: The stream identifier
            mac_address: The MAC address
            account_id: The M3U account ID
            
        Returns:
            True if set successfully
        """
        if not self.redis_client:
            return False
        
        try:
            key = f"mac_stream_mapping:{account_id}:{mac_address}"
            self.redis_client.setex(key, 3600, stream_id)  # 1 hour TTL
            return True
        except Exception as e:
            logger.error(f"Failed to set stream MAC mapping: {e}")
            return False
    
    def _store_mac_metrics(self, key: str) -> bool:
        """Store MAC metrics in Redis."""
        if not self.redis_client:
            return False
        
        try:
            metrics = self._mac_metrics.get(key)
            if not metrics:
                return False
            
            import json
            redis_key = f"predictive:mac_metrics:{key}"
            self.redis_client.setex(
                redis_key,
                3600,  # 1 hour TTL
                json.dumps(metrics.to_dict())
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store MAC metrics: {e}")
            return False
    
    def _load_mac_metrics(self, key: str) -> Optional[MACMetrics]:
        """Load MAC metrics from Redis."""
        if not self.redis_client:
            return None
        
        try:
            import json
            redis_key = f"predictive:mac_metrics:{key}"
            data = self.redis_client.get(redis_key)
            
            if not data:
                return None
            
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            
            metrics_dict = json.loads(data)
            metrics = MACMetrics(**metrics_dict)
            
            # Cache in memory
            self._mac_metrics[key] = metrics
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to load MAC metrics: {e}")
            return None


class MACRiskScoreCalculator:
    """
    Calculates MAC-specific risk score contributions.
    
    Requirements:
    - 14.3: MAC-specific risk score factors
    - 14.4: Token expiry warning/critical thresholds
    - 14.5: Portal response time thresholds
    """
    
    def __init__(self, config=None):
        """
        Initialize the MAC risk score calculator.
        
        Args:
            config: PredictiveConfig instance
        """
        self._config = config
    
    @property
    def config(self):
        """Lazy load config."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config
    
    def calculate_mac_risk_contributions(self, mac_metrics: MACMetrics) -> List[Dict[str, Any]]:
        """
        Calculate risk score contributions from MAC metrics.
        
        Requirement 14.3: MAC-specific risk score factors
        
        Args:
            mac_metrics: MACMetrics object
            
        Returns:
            List of risk contribution dictionaries
        """
        from .risk_calculator import RiskContribution, RiskReason
        
        contributions = []
        
        # Token expiry risk
        contributions.extend(
            self._calculate_token_expiry_risk(mac_metrics.token_ttl_seconds)
        )
        
        # Portal response time risk
        contributions.extend(
            self._calculate_portal_response_risk(mac_metrics.portal_response_time_ms)
        )
        
        # Handshake failure risk
        if mac_metrics.handshake_failures > 0:
            points = min(mac_metrics.handshake_failures * 15, 45)
            contributions.append(RiskContribution(
                reason=RiskReason.MAC_TOKEN_EXPIRY,
                points=points,
                description=f"{mac_metrics.handshake_failures} handshake failure(s)",
                metric_value=mac_metrics.handshake_failures,
                threshold=0
            ))
        
        return contributions
    
    def _calculate_token_expiry_risk(self, ttl_seconds: int) -> List:
        """
        Calculate risk from token expiry.
        
        Requirement 14.4: Token expiry thresholds
        """
        from .risk_calculator import RiskContribution, RiskReason
        
        contributions = []
        
        if ttl_seconds <= 0:
            # Token expired
            contributions.append(RiskContribution(
                reason=RiskReason.MAC_TOKEN_EXPIRY,
                points=self.config.mac_token_expiry_critical_weight,
                description="MAC token expired",
                metric_value=ttl_seconds,
                threshold=0
            ))
        elif ttl_seconds < 120:  # Less than 2 minutes
            contributions.append(RiskContribution(
                reason=RiskReason.MAC_TOKEN_EXPIRY,
                points=self.config.mac_token_expiry_critical_weight,
                description=f"MAC token expiring in {ttl_seconds}s (critical)",
                metric_value=ttl_seconds,
                threshold=120
            ))
        elif ttl_seconds < 300:  # Less than 5 minutes
            contributions.append(RiskContribution(
                reason=RiskReason.MAC_TOKEN_EXPIRY,
                points=self.config.mac_token_expiry_warning_weight,
                description=f"MAC token expiring in {ttl_seconds}s (warning)",
                metric_value=ttl_seconds,
                threshold=300
            ))
        
        return contributions
    
    def _calculate_portal_response_risk(self, response_time_ms: float) -> List:
        """
        Calculate risk from portal response time.
        
        Requirement 14.5: Portal response time thresholds
        """
        from .risk_calculator import RiskContribution, RiskReason
        
        contributions = []
        
        if response_time_ms > 5000:  # More than 5 seconds
            contributions.append(RiskContribution(
                reason=RiskReason.MAC_PORTAL_SLOW,
                points=self.config.mac_portal_very_slow_weight,
                description=f"Portal very slow ({response_time_ms:.0f}ms)",
                metric_value=response_time_ms,
                threshold=5000
            ))
        elif response_time_ms > 2000:  # More than 2 seconds
            contributions.append(RiskContribution(
                reason=RiskReason.MAC_PORTAL_SLOW,
                points=self.config.mac_portal_slow_weight,
                description=f"Portal slow ({response_time_ms:.0f}ms)",
                metric_value=response_time_ms,
                threshold=2000
            ))
        
        return contributions


class MACWarmupManager:
    """
    Manages MAC-specific warmup before failover.
    
    Requirements:
    - 14.6: Pre-authenticate backup MAC before failover
    - 14.7: Keep backup MAC token fresh
    """
    
    def __init__(self, config=None):
        """
        Initialize the MAC warmup manager.
        
        Args:
            config: PredictiveConfig instance
        """
        self._config = config
        self._warmed_macs: Dict[str, Dict[str, Any]] = {}
    
    @property
    def config(self):
        """Lazy load config."""
        if self._config is None:
            try:
                from .config import get_predictive_config
                self._config = get_predictive_config()
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                from .config import PredictiveConfig
                self._config = PredictiveConfig()
        return self._config
    
    def warmup_backup_mac(self, account_id: int, current_mac: str,
                          backup_mac: str = None) -> bool:
        """
        Warmup a backup MAC address by pre-authenticating.
        
        Requirement 14.6: Pre-authenticate backup MAC
        
        Args:
            account_id: The M3U account ID
            current_mac: Current MAC address in use
            backup_mac: Optional specific backup MAC to warmup
            
        Returns:
            True if warmup successful
        """
        try:
            # Get backup MAC if not specified
            if not backup_mac:
                backup_mac = self._get_backup_mac(account_id, current_mac)
                if not backup_mac:
                    logger.debug(f"No backup MAC available for account {account_id}")
                    return False
            
            # Check if already warmed
            key = f"{account_id}:{backup_mac}"
            if key in self._warmed_macs:
                warmup_info = self._warmed_macs[key]
                if time.time() - warmup_info.get('warmed_at', 0) < 300:
                    logger.debug(f"Backup MAC {backup_mac[:8]}... already warmed")
                    return True
            
            # Perform handshake for backup MAC
            success = self._perform_backup_handshake(account_id, backup_mac)
            
            if success:
                self._warmed_macs[key] = {
                    'mac_address': backup_mac,
                    'account_id': account_id,
                    'warmed_at': time.time(),
                    'status': 'ready'
                }
                logger.info(f"Backup MAC {backup_mac[:8]}... warmed successfully")
                return True
            else:
                logger.warning(f"Failed to warmup backup MAC {backup_mac[:8]}...")
                return False
                
        except Exception as e:
            logger.error(f"Error warming up backup MAC: {e}")
            return False
    
    def get_warmed_backup_mac(self, account_id: int, 
                               current_mac: str) -> Optional[str]:
        """
        Get a warmed backup MAC ready for failover.
        
        Args:
            account_id: The M3U account ID
            current_mac: Current MAC address to exclude
            
        Returns:
            Backup MAC address or None
        """
        for key, info in self._warmed_macs.items():
            if info.get('account_id') != account_id:
                continue
            if info.get('mac_address') == current_mac:
                continue
            if info.get('status') != 'ready':
                continue
            
            # Check if still fresh (less than 5 minutes old)
            if time.time() - info.get('warmed_at', 0) < 300:
                return info.get('mac_address')
        
        return None
    
    def release_warmup(self, account_id: int, mac_address: str) -> bool:
        """
        Release a warmed MAC address.
        
        Args:
            account_id: The M3U account ID
            mac_address: The MAC address to release
            
        Returns:
            True if released
        """
        key = f"{account_id}:{mac_address}"
        if key in self._warmed_macs:
            del self._warmed_macs[key]
            logger.debug(f"Released warmup for MAC {mac_address[:8]}...")
            return True
        return False
    
    def _get_backup_mac(self, account_id: int, current_mac: str) -> Optional[str]:
        """Get a backup MAC address for the account."""
        try:
            from apps.m3u.mac_portal_models import MACAddress
            
            # Get active MACs for this account, excluding current
            macs = MACAddress.objects.filter(
                account_id=account_id,
                is_active=True
            ).exclude(
                mac_address=current_mac
            ).order_by('priority', '-health_score')
            
            mac = macs.first()
            if mac:
                return mac.mac_address
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting backup MAC: {e}")
            return None
    
    def _perform_backup_handshake(self, account_id: int, mac_address: str) -> bool:
        """Perform handshake for backup MAC."""
        try:
            from apps.m3u.models import M3UAccount
            from apps.m3u.mac_portal_client_extended import MACPortalClientExtended
            
            account = M3UAccount.objects.get(id=account_id)
            
            # Create client for backup MAC
            client = MACPortalClientExtended(
                portal_url=account.server_url,
                mac_address=mac_address
            )
            
            # Perform handshake
            result = client.handshake()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error performing backup handshake: {e}")
            return False


# =============================================================================
# Singleton instances
# =============================================================================

_mac_metrics_collector: Optional[MACMetricsCollector] = None
_mac_risk_calculator: Optional[MACRiskScoreCalculator] = None
_mac_warmup_manager: Optional[MACWarmupManager] = None


def get_mac_metrics_collector() -> MACMetricsCollector:
    """Get the global MACMetricsCollector instance."""
    global _mac_metrics_collector
    if _mac_metrics_collector is None:
        _mac_metrics_collector = MACMetricsCollector()
    return _mac_metrics_collector


def get_mac_risk_calculator() -> MACRiskScoreCalculator:
    """Get the global MACRiskScoreCalculator instance."""
    global _mac_risk_calculator
    if _mac_risk_calculator is None:
        _mac_risk_calculator = MACRiskScoreCalculator()
    return _mac_risk_calculator


def get_mac_warmup_manager() -> MACWarmupManager:
    """Get the global MACWarmupManager instance."""
    global _mac_warmup_manager
    if _mac_warmup_manager is None:
        _mac_warmup_manager = MACWarmupManager()
    return _mac_warmup_manager


def reset_mac_metrics():
    """Reset all MAC metrics instances (for testing)."""
    global _mac_metrics_collector, _mac_risk_calculator, _mac_warmup_manager
    _mac_metrics_collector = None
    _mac_risk_calculator = None
    _mac_warmup_manager = None
