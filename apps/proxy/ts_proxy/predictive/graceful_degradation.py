"""
Graceful Degradation for the Predictive Failover System.

This module provides quality degradation before failover:
- Quality hierarchy per stream
- Automatic switch to lower quality
- Automatic return to higher quality

Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Stream quality levels."""
    ORIGINAL = "original"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AUDIO_ONLY = "audio_only"


@dataclass
class QualityConfig:
    """
    Quality configuration for a stream.
    
    Attributes:
        stream_id: Stream identifier
        current_level: Current quality level
        available_levels: Available quality levels
        original_url: Original stream URL
        quality_urls: URLs for each quality level
        degradation_history: History of quality changes
    """
    stream_id: str
    current_level: QualityLevel = QualityLevel.ORIGINAL
    available_levels: List[QualityLevel] = field(default_factory=lambda: [QualityLevel.ORIGINAL])
    original_url: str = ""
    quality_urls: Dict[QualityLevel, str] = field(default_factory=dict)
    degradation_history: List[Dict[str, Any]] = field(default_factory=list)
    last_degradation: float = 0
    last_upgrade: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'stream_id': self.stream_id,
            'current_level': self.current_level.value,
            'available_levels': [l.value for l in self.available_levels],
            'original_url': self.original_url,
            'quality_urls': {k.value: v for k, v in self.quality_urls.items()},
            'degradation_history': self.degradation_history[-20:],
            'last_degradation': self.last_degradation,
            'last_upgrade': self.last_upgrade,
        }


class GracefulDegradationManager:
    """
    Manages graceful quality degradation for streams.
    
    Requirements:
    - 18.1: Define quality hierarchy per stream
    - 18.2: Automatic switch to lower quality
    - 18.3: Automatic return to higher quality
    - 18.4: Configurable degradation thresholds
    """
    
    # Quality hierarchy (best to worst)
    QUALITY_HIERARCHY = [
        QualityLevel.ORIGINAL,
        QualityLevel.HIGH,
        QualityLevel.MEDIUM,
        QualityLevel.LOW,
        QualityLevel.AUDIO_ONLY,
    ]
    
    # Minimum time between quality changes (seconds)
    MIN_DEGRADATION_INTERVAL = 30
    MIN_UPGRADE_INTERVAL = 60
    
    # Risk score thresholds for degradation
    DEGRADATION_THRESHOLD = 70
    UPGRADE_THRESHOLD = 40
    
    def __init__(self, config=None, redis_client=None):
        """
        Initialize the graceful degradation manager.
        
        Args:
            config: PredictiveConfig instance
            redis_client: Redis client for storage
        """
        self._config = config
        self._redis_client = redis_client
        self._stream_configs: Dict[str, QualityConfig] = {}
    
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
    
    def is_enabled(self) -> bool:
        """Check if graceful degradation is enabled."""
        return self.config.graceful_degradation_enabled
    
    def register_stream(self, stream_id: str, original_url: str,
                        quality_urls: Dict[str, str] = None) -> bool:
        """
        Register a stream for graceful degradation.
        
        Requirement 18.1: Define quality hierarchy per stream
        
        Args:
            stream_id: Stream identifier
            original_url: Original stream URL
            quality_urls: Dict mapping quality level names to URLs
            
        Returns:
            True if registered successfully
        """
        if not self.is_enabled():
            return False
        
        # Parse quality URLs
        parsed_urls = {QualityLevel.ORIGINAL: original_url}
        available = [QualityLevel.ORIGINAL]
        
        if quality_urls:
            for level_name, url in quality_urls.items():
                try:
                    level = QualityLevel(level_name.lower())
                    parsed_urls[level] = url
                    if level not in available:
                        available.append(level)
                except ValueError:
                    logger.warning(f"Unknown quality level: {level_name}")
        
        # Sort available levels by hierarchy
        available.sort(key=lambda l: self.QUALITY_HIERARCHY.index(l))
        
        self._stream_configs[stream_id] = QualityConfig(
            stream_id=stream_id,
            current_level=QualityLevel.ORIGINAL,
            available_levels=available,
            original_url=original_url,
            quality_urls=parsed_urls,
        )
        
        logger.debug(f"Registered stream {stream_id} with {len(available)} quality levels")
        return True
    
    def unregister_stream(self, stream_id: str) -> bool:
        """
        Unregister a stream from graceful degradation.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if unregistered successfully
        """
        if stream_id in self._stream_configs:
            del self._stream_configs[stream_id]
            return True
        return False
    
    def evaluate_degradation(self, stream_id: str, risk_score: int) -> Optional[Dict[str, Any]]:
        """
        Evaluate if quality should be degraded or upgraded.
        
        Requirements:
        - 18.2: Automatic switch to lower quality
        - 18.3: Automatic return to higher quality
        
        Args:
            stream_id: Stream identifier
            risk_score: Current risk score (0-100)
            
        Returns:
            Dict with action and new URL if quality change needed, None otherwise
        """
        if not self.is_enabled():
            return None
        
        config = self._stream_configs.get(stream_id)
        if not config:
            return None
        
        now = time.time()
        
        # Check for degradation
        if risk_score >= self.DEGRADATION_THRESHOLD:
            if now - config.last_degradation >= self.MIN_DEGRADATION_INTERVAL:
                return self._degrade_quality(config)
        
        # Check for upgrade
        elif risk_score <= self.UPGRADE_THRESHOLD:
            if now - config.last_upgrade >= self.MIN_UPGRADE_INTERVAL:
                return self._upgrade_quality(config)
        
        return None
    
    def _degrade_quality(self, config: QualityConfig) -> Optional[Dict[str, Any]]:
        """
        Degrade stream quality to next lower level.
        
        Requirement 18.2: Automatic switch to lower quality
        """
        current_idx = self.QUALITY_HIERARCHY.index(config.current_level)
        
        # Find next available lower quality
        for level in self.QUALITY_HIERARCHY[current_idx + 1:]:
            if level in config.available_levels:
                old_level = config.current_level
                config.current_level = level
                config.last_degradation = time.time()
                
                # Record history
                config.degradation_history.append({
                    'action': 'degrade',
                    'from': old_level.value,
                    'to': level.value,
                    'timestamp': time.time(),
                })
                
                new_url = config.quality_urls.get(level, config.original_url)
                
                logger.info(f"Degraded stream {config.stream_id} from {old_level.value} to {level.value}")
                
                return {
                    'action': 'degrade',
                    'stream_id': config.stream_id,
                    'old_level': old_level.value,
                    'new_level': level.value,
                    'new_url': new_url,
                }
        
        # Already at lowest quality
        return None
    
    def _upgrade_quality(self, config: QualityConfig) -> Optional[Dict[str, Any]]:
        """
        Upgrade stream quality to next higher level.
        
        Requirement 18.3: Automatic return to higher quality
        """
        if config.current_level == QualityLevel.ORIGINAL:
            return None  # Already at highest
        
        current_idx = self.QUALITY_HIERARCHY.index(config.current_level)
        
        # Find next available higher quality
        for level in reversed(self.QUALITY_HIERARCHY[:current_idx]):
            if level in config.available_levels:
                old_level = config.current_level
                config.current_level = level
                config.last_upgrade = time.time()
                
                # Record history
                config.degradation_history.append({
                    'action': 'upgrade',
                    'from': old_level.value,
                    'to': level.value,
                    'timestamp': time.time(),
                })
                
                new_url = config.quality_urls.get(level, config.original_url)
                
                logger.info(f"Upgraded stream {config.stream_id} from {old_level.value} to {level.value}")
                
                return {
                    'action': 'upgrade',
                    'stream_id': config.stream_id,
                    'old_level': old_level.value,
                    'new_level': level.value,
                    'new_url': new_url,
                }
        
        return None
    
    def get_current_quality(self, stream_id: str) -> Optional[str]:
        """
        Get current quality level for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Quality level name or None
        """
        config = self._stream_configs.get(stream_id)
        if config:
            return config.current_level.value
        return None
    
    def get_stream_config(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        Get quality configuration for a stream.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Config dict or None
        """
        config = self._stream_configs.get(stream_id)
        if config:
            return config.to_dict()
        return None
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all stream quality configurations."""
        return {
            stream_id: config.to_dict()
            for stream_id, config in self._stream_configs.items()
        }
    
    def force_quality(self, stream_id: str, level: str) -> Optional[Dict[str, Any]]:
        """
        Force a specific quality level for a stream.
        
        Args:
            stream_id: Stream identifier
            level: Quality level name
            
        Returns:
            Dict with new URL or None
        """
        config = self._stream_configs.get(stream_id)
        if not config:
            return None
        
        try:
            new_level = QualityLevel(level.lower())
        except ValueError:
            logger.error(f"Unknown quality level: {level}")
            return None
        
        if new_level not in config.available_levels:
            logger.error(f"Quality level {level} not available for stream {stream_id}")
            return None
        
        old_level = config.current_level
        config.current_level = new_level
        
        config.degradation_history.append({
            'action': 'force',
            'from': old_level.value,
            'to': new_level.value,
            'timestamp': time.time(),
        })
        
        new_url = config.quality_urls.get(new_level, config.original_url)
        
        return {
            'action': 'force',
            'stream_id': stream_id,
            'old_level': old_level.value,
            'new_level': new_level.value,
            'new_url': new_url,
        }


# =============================================================================
# Singleton instance
# =============================================================================

_degradation_manager: Optional[GracefulDegradationManager] = None


def get_degradation_manager() -> GracefulDegradationManager:
    """Get the global GracefulDegradationManager instance."""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager()
    return _degradation_manager


def reset_degradation_manager() -> None:
    """Reset the global instance (for testing)."""
    global _degradation_manager
    _degradation_manager = None
