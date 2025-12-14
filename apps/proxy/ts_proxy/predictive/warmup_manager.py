"""
Warmup Manager for the Predictive Failover System.

This module manages backup stream warmup to enable faster failovers.
It maintains connections to backup streams without consuming data,
keeping them ready for instant switching.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

import json
import logging
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class WarmupStatus:
    """
    Status of a warmed-up backup stream.
    
    Attributes:
        channel_id: Channel this warmup is for
        backup_stream_id: ID of the backup stream
        backup_url: URL of the backup stream
        status: Current status (warming, ready, failed)
        started_at: When warmup started
        last_keepalive: Last keepalive timestamp
        error_message: Error message if failed
    """
    channel_id: str
    backup_stream_id: Optional[str] = None
    backup_url: Optional[str] = None
    status: str = "warming"  # warming, ready, failed
    started_at: float = field(default_factory=time.time)
    last_keepalive: float = field(default_factory=time.time)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WarmupStatus':
        """Create from dictionary."""
        return cls(**data)
    
    def is_ready(self) -> bool:
        """Check if warmup is ready for use."""
        return self.status == "ready"
    
    def is_expired(self, timeout: int = 300) -> bool:
        """Check if warmup has expired (default 5 minutes)."""
        return time.time() - self.last_keepalive > timeout


class WarmupManager:
    """
    Manages backup stream warmup for predictive failover.
    
    The manager:
    - Establishes connections to backup streams without consuming data
    - Keeps connections alive with periodic minimal requests
    - Releases warmups after timeout or when no longer needed
    - Provides ready backup streams for instant failover
    
    Requirements:
    - 5.1: Establish connection without consuming data
    - 5.2: Keep-alive every 30 seconds
    - 5.3: Release after 5 minutes of inactivity
    - 5.4: Release when risk score drops below threshold
    - 5.5: Try next backup if current shows problems
    """
    
    # Warmup configuration
    KEEPALIVE_INTERVAL = 30  # seconds
    WARMUP_TIMEOUT = 300  # 5 minutes
    MAX_WARMUP_ATTEMPTS = 3
    
    def __init__(self, config=None, redis_client=None):
        """
        Initialize the warmup manager.
        
        Args:
            config: PredictiveConfig instance
            redis_client: Redis client for status storage
        """
        self._config = config
        self._redis_client = redis_client
        self._active_warmups: Dict[str, WarmupStatus] = {}
        self._keepalive_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        
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
    def redis_client(self):
        """Lazy load Redis client if not provided."""
        if self._redis_client is None:
            try:
                from django_redis import get_redis_connection
                self._redis_client = get_redis_connection("default")
            except Exception as e:
                logger.error(f"Failed to get Redis connection: {e}")
        return self._redis_client
    
    # =========================================================================
    # Task 7.2: warmup_backup() Method
    # =========================================================================
    
    def warmup_backup(self, channel_id: str, backup_stream_id: str = None,
                      backup_url: str = None) -> bool:
        """
        Start warming up a backup stream.
        
        Requirement 5.1: Establish connection without consuming data
        
        Args:
            channel_id: Channel to warmup backup for
            backup_stream_id: Optional specific backup stream ID
            backup_url: Optional specific backup URL
            
        Returns:
            True if warmup started successfully
        """
        if not self.config.enabled:
            return False
        
        try:
            # Check if already warming up
            if channel_id in self._active_warmups:
                existing = self._active_warmups[channel_id]
                if existing.is_ready() or existing.status == "warming":
                    logger.debug(f"Warmup already active for channel {channel_id}")
                    return True
            
            # Get backup stream info if not provided
            if not backup_url:
                backup_info = self._get_backup_stream_info(channel_id, backup_stream_id)
                if not backup_info:
                    logger.warning(f"No backup stream available for channel {channel_id}")
                    return False
                backup_stream_id = backup_info.get('stream_id')
                backup_url = backup_info.get('url')
            
            # Create warmup status
            warmup = WarmupStatus(
                channel_id=channel_id,
                backup_stream_id=backup_stream_id,
                backup_url=backup_url,
                status="warming"
            )
            
            # Attempt to establish connection
            if self._establish_warmup_connection(warmup):
                warmup.status = "ready"
                self._active_warmups[channel_id] = warmup
                self._store_warmup_status(warmup)
                
                # Start keepalive thread
                self._start_keepalive(channel_id)
                
                # Log event
                self._log_warmup_event(channel_id, "warmup_started", backup_stream_id)
                
                logger.info(f"Warmup ready for channel {channel_id}, backup: {backup_stream_id}")
                return True
            else:
                warmup.status = "failed"
                warmup.error_message = "Failed to establish connection"
                self._log_warmup_event(channel_id, "warmup_failed", backup_stream_id)
                return False
                
        except Exception as e:
            logger.error(f"Error starting warmup for channel {channel_id}: {e}")
            return False
    
    def _get_backup_stream_info(self, channel_id: str, 
                                 preferred_stream_id: str = None) -> Optional[Dict[str, Any]]:
        """Get backup stream information for a channel."""
        try:
            from apps.channels.models import Channel
            
            channel = Channel.objects.get(uuid=channel_id)
            
            # Get current stream to exclude
            current_stream_id = None
            if self.redis_client:
                try:
                    metadata_key = f"channel:{channel_id}:metadata"
                    current_stream_id = self.redis_client.hget(metadata_key, "stream_id")
                    if current_stream_id:
                        current_stream_id = int(current_stream_id.decode('utf-8'))
                except Exception:
                    pass
            
            # Get available streams
            streams = channel.streams.filter(is_active=True).exclude(id=current_stream_id)
            
            if preferred_stream_id:
                streams = streams.filter(id=preferred_stream_id)
            
            # Order by priority or health score if available
            streams = streams.order_by('order')
            
            stream = streams.first()
            if stream:
                return {
                    'stream_id': str(stream.id),
                    'url': stream.url,
                    'name': stream.name,
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting backup stream info: {e}")
            return None
    
    def _establish_warmup_connection(self, warmup: WarmupStatus) -> bool:
        """
        Establish a warmup connection to the backup stream.
        
        This makes a HEAD request or minimal GET to verify the stream
        is accessible without consuming significant data.
        """
        import requests
        
        try:
            # Try HEAD request first (minimal data)
            response = requests.head(
                warmup.backup_url,
                timeout=10,
                allow_redirects=True,
                headers={'User-Agent': 'Dispatcharr/1.0 Warmup'}
            )
            
            if response.status_code in (200, 206):
                return True
            
            # If HEAD fails, try minimal GET
            response = requests.get(
                warmup.backup_url,
                timeout=10,
                stream=True,
                headers={'User-Agent': 'Dispatcharr/1.0 Warmup'}
            )
            
            if response.status_code in (200, 206):
                # Read minimal data to verify stream
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        response.close()
                        return True
                    break
            
            return False
            
        except Exception as e:
            logger.debug(f"Warmup connection failed: {e}")
            return False
    
    # =========================================================================
    # Task 7.3: get_warmed_backup() Method
    # =========================================================================
    
    def get_warmed_backup(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a warmed-up backup stream ready for failover.
        
        Args:
            channel_id: Channel to get backup for
            
        Returns:
            Dict with backup stream info or None
        """
        warmup = self._active_warmups.get(channel_id)
        
        if warmup and warmup.is_ready() and not warmup.is_expired(self.WARMUP_TIMEOUT):
            return {
                'stream_id': warmup.backup_stream_id,
                'url': warmup.backup_url,
                'warmed_at': warmup.started_at,
            }
        
        # Try to load from Redis
        warmup = self._load_warmup_status(channel_id)
        if warmup and warmup.is_ready() and not warmup.is_expired(self.WARMUP_TIMEOUT):
            self._active_warmups[channel_id] = warmup
            return {
                'stream_id': warmup.backup_stream_id,
                'url': warmup.backup_url,
                'warmed_at': warmup.started_at,
            }
        
        return None
    
    # =========================================================================
    # Task 7.4: release_warmup() Method
    # =========================================================================
    
    def release_warmup(self, channel_id: str, reason: str = "manual") -> bool:
        """
        Release a warmed-up backup stream.
        
        Requirement 5.4: Release when risk score drops below threshold
        
        Args:
            channel_id: Channel to release warmup for
            reason: Reason for release
            
        Returns:
            True if released successfully
        """
        try:
            # Stop keepalive thread
            self._stop_keepalive(channel_id)
            
            # Remove from active warmups
            if channel_id in self._active_warmups:
                warmup = self._active_warmups.pop(channel_id)
                self._log_warmup_event(channel_id, "warmup_released", 
                                       warmup.backup_stream_id, reason)
            
            # Remove from Redis
            self._remove_warmup_status(channel_id)
            
            logger.info(f"Released warmup for channel {channel_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing warmup for channel {channel_id}: {e}")
            return False
    
    # =========================================================================
    # Task 7.5: keep_alive() Mechanism
    # =========================================================================
    
    def _start_keepalive(self, channel_id: str) -> None:
        """Start keepalive thread for a warmup."""
        if channel_id in self._keepalive_threads:
            return
        
        stop_event = threading.Event()
        self._stop_events[channel_id] = stop_event
        
        thread = threading.Thread(
            target=self._keepalive_loop,
            args=(channel_id, stop_event),
            daemon=True
        )
        thread.start()
        self._keepalive_threads[channel_id] = thread
    
    def _stop_keepalive(self, channel_id: str) -> None:
        """Stop keepalive thread for a warmup."""
        if channel_id in self._stop_events:
            self._stop_events[channel_id].set()
            del self._stop_events[channel_id]
        
        if channel_id in self._keepalive_threads:
            del self._keepalive_threads[channel_id]
    
    def _keepalive_loop(self, channel_id: str, stop_event: threading.Event) -> None:
        """
        Keepalive loop for maintaining warmup connection.
        
        Requirement 5.2: Keep-alive every 30 seconds
        """
        import requests
        
        while not stop_event.is_set():
            try:
                warmup = self._active_warmups.get(channel_id)
                if not warmup or not warmup.backup_url:
                    break
                
                # Send minimal keepalive request
                response = requests.head(
                    warmup.backup_url,
                    timeout=5,
                    headers={'User-Agent': 'Dispatcharr/1.0 Keepalive'}
                )
                
                if response.status_code in (200, 206):
                    warmup.last_keepalive = time.time()
                    self._store_warmup_status(warmup)
                else:
                    # Requirement 5.5: Try next backup if current shows problems
                    logger.warning(f"Keepalive failed for channel {channel_id}, status: {response.status_code}")
                    self._try_next_backup(channel_id)
                    break
                    
            except Exception as e:
                logger.debug(f"Keepalive error for channel {channel_id}: {e}")
                self._try_next_backup(channel_id)
                break
            
            # Wait for next keepalive interval
            stop_event.wait(self.KEEPALIVE_INTERVAL)
    
    def _try_next_backup(self, channel_id: str) -> None:
        """
        Try to warmup the next available backup stream.
        
        Requirement 5.5: Try next backup if current shows problems
        """
        current_warmup = self._active_warmups.get(channel_id)
        current_stream_id = current_warmup.backup_stream_id if current_warmup else None
        
        # Release current warmup
        self.release_warmup(channel_id, "backup_failed")
        
        # Try to get next backup
        backup_info = self._get_backup_stream_info(channel_id)
        if backup_info and backup_info.get('stream_id') != current_stream_id:
            self.warmup_backup(
                channel_id,
                backup_info.get('stream_id'),
                backup_info.get('url')
            )
    
    # =========================================================================
    # Task 7.6: Automatic Release After Timeout
    # =========================================================================
    
    def cleanup_expired_warmups(self) -> int:
        """
        Clean up warmups that have expired.
        
        Requirement 5.3: Release after 5 minutes of inactivity
        
        Returns:
            Number of warmups cleaned up
        """
        cleaned = 0
        
        for channel_id in list(self._active_warmups.keys()):
            warmup = self._active_warmups[channel_id]
            if warmup.is_expired(self.WARMUP_TIMEOUT):
                self.release_warmup(channel_id, "timeout")
                cleaned += 1
        
        return cleaned
    
    # =========================================================================
    # Redis Storage Methods
    # =========================================================================
    
    def _store_warmup_status(self, warmup: WarmupStatus) -> None:
        """Store warmup status in Redis."""
        if not self.redis_client:
            return
        
        try:
            key = self._redis_keys.warmup(warmup.channel_id)
            self.redis_client.hset(key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in warmup.to_dict().items()
            })
            self.redis_client.expire(key, self._redis_keys.WARMUP_TTL)
        except Exception as e:
            logger.error(f"Failed to store warmup status: {e}")
    
    def _load_warmup_status(self, channel_id: str) -> Optional[WarmupStatus]:
        """Load warmup status from Redis."""
        if not self.redis_client:
            return None
        
        try:
            key = self._redis_keys.warmup(channel_id)
            data = self.redis_client.hgetall(key)
            
            if not data:
                return None
            
            # Decode bytes and convert types
            decoded = {}
            for k, v in data.items():
                if isinstance(k, bytes):
                    k = k.decode('utf-8')
                if isinstance(v, bytes):
                    v = v.decode('utf-8')
                
                # Convert numeric fields
                if k in ('started_at', 'last_keepalive'):
                    v = float(v)
                
                decoded[k] = v
            
            return WarmupStatus.from_dict(decoded)
            
        except Exception as e:
            logger.error(f"Failed to load warmup status: {e}")
            return None
    
    def _remove_warmup_status(self, channel_id: str) -> None:
        """Remove warmup status from Redis."""
        if not self.redis_client:
            return
        
        try:
            key = self._redis_keys.warmup(channel_id)
            self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Failed to remove warmup status: {e}")
    
    # =========================================================================
    # Event Logging
    # =========================================================================
    
    def _log_warmup_event(self, channel_id: str, event_type: str,
                          stream_id: str = None, reason: str = None) -> None:
        """Log warmup event to database."""
        try:
            from .models import PredictiveFailoverEvent
            
            PredictiveFailoverEvent.log_event(
                event_type=event_type,
                channel_id=channel_id,
                stream_id=stream_id or "",
                reason=reason or "",
            )
        except Exception as e:
            logger.debug(f"Could not log warmup event: {e}")
    
    # =========================================================================
    # Status Methods
    # =========================================================================
    
    def get_all_warmup_statuses(self) -> List[Dict[str, Any]]:
        """Get status of all active warmups."""
        statuses = []
        
        for channel_id, warmup in self._active_warmups.items():
            statuses.append({
                'channel_id': channel_id,
                'backup_stream_id': warmup.backup_stream_id,
                'status': warmup.status,
                'started_at': warmup.started_at,
                'last_keepalive': warmup.last_keepalive,
                'is_ready': warmup.is_ready(),
                'is_expired': warmup.is_expired(self.WARMUP_TIMEOUT),
            })
        
        return statuses
    
    def get_all_warmup_status(self) -> Dict[str, Any]:
        """
        Get warmup status as a dictionary keyed by channel_id.
        
        Returns:
            Dict mapping channel_id to warmup status
        """
        result = {}
        
        for channel_id, warmup in self._active_warmups.items():
            result[channel_id] = {
                'backup_stream_id': warmup.backup_stream_id,
                'status': warmup.status,
                'started_at': warmup.started_at,
                'last_keepalive': warmup.last_keepalive,
                'is_ready': warmup.is_ready(),
            }
        
        return result
    
    def has_warmup(self, channel_id: str) -> bool:
        """Check if a channel has an active warmup."""
        warmup = self._active_warmups.get(channel_id)
        return warmup is not None and warmup.is_ready() and not warmup.is_expired(self.WARMUP_TIMEOUT)


# =============================================================================
# Singleton instance for global access
# =============================================================================

_manager_instance: Optional[WarmupManager] = None


def get_warmup_manager() -> WarmupManager:
    """
    Get the global WarmupManager instance.
    
    Returns:
        WarmupManager singleton instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = WarmupManager()
    return _manager_instance


def reset_warmup_manager() -> None:
    """Reset the global manager instance (mainly for testing)."""
    global _manager_instance
    if _manager_instance:
        # Stop all keepalive threads
        for channel_id in list(_manager_instance._stop_events.keys()):
            _manager_instance._stop_keepalive(channel_id)
    _manager_instance = None
