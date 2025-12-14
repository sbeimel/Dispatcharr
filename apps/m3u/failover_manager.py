"""
Failover Manager for MAC Portal.

Orchestrates all failover strategies:
- MAC-level failover
- Portal/Endpoint failover
- Stream-level failover
- User-Agent failover

Requirements: 55.1, 56.1, 56.2, 56.3, 57.1, 57.2, 57.3, 57.4, 58.1, 58.2, 58.3, 58.4, 59.1, 59.2, 59.3, 59.4, 60.1, 60.2, 60.3, 60.4, 61.1
"""

import logging
import time
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)


class FailoverExhausted(Exception):
    """Raised when all failover attempts have been exhausted."""
    pass


class AllFailoverStrategiesExhausted(Exception):
    """Raised when all failover strategies have been exhausted."""
    pass


class FailoverManager:
    """
    Orchestrates failover strategies based on configuration.
    
    Requirements: 55.1, 60.2
    """
    
    # Default User-Agent presets
    USER_AGENT_PRESETS = {
        "MAG250": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "MAG254": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG254 stbapp ver: 2 rev: 254 Safari/533.3",
        "MAG322": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG322 stbapp ver: 4 rev: 322 Safari/533.3",
        "MAG424": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG424 stbapp ver: 5 rev: 424 Safari/533.3",
    }
    
    # Default endpoint priority
    DEFAULT_ENDPOINTS = [
        "/server/load.php",
        "/stalker_portal/server/load.php",
        "/portal.php",
        "/c/portal.php",
    ]
    
    def __init__(self, account_id: int):
        """
        Initialize FailoverManager for a specific account.
        
        Args:
            account_id: The M3UAccount ID
        """
        self.account_id = account_id
        self._load_settings()
        
        # Initialize sub-managers
        from apps.m3u.mac_rotation_manager import MACRotationManagerRegistry
        
        self.mac_manager = MACRotationManagerRegistry.get_or_create(account_id)
    
    def _load_settings(self):
        """Load failover settings from database."""
        from apps.m3u.mac_portal_models import FailoverSettings
        
        try:
            settings = FailoverSettings.get_settings()
            
            self._mac_failover_enabled = settings.mac_failover_enabled
            self._portal_failover_enabled = settings.portal_failover_enabled
            self._stream_failover_enabled = settings.stream_failover_enabled
            self._endpoint_failover_enabled = settings.endpoint_failover_enabled
            self._useragent_failover_enabled = settings.useragent_failover_enabled
            
            self._mac_max_attempts = settings.mac_max_attempts
            self._stream_max_retries = settings.stream_max_retries
            
            self._endpoint_priority = settings.endpoint_priority or self.DEFAULT_ENDPOINTS
            self._useragent_rotation_order = settings.useragent_rotation_order or list(self.USER_AGENT_PRESETS.keys())
            self._failover_priority = settings.failover_priority or ['mac', 'useragent', 'endpoint', 'stream']
            
        except Exception as e:
            logger.warning(f"Failed to load failover settings, using defaults: {e}")
            self._mac_failover_enabled = True
            self._portal_failover_enabled = True
            self._stream_failover_enabled = True
            self._endpoint_failover_enabled = True
            self._useragent_failover_enabled = False
            self._mac_max_attempts = 3
            self._stream_max_retries = 3
            self._endpoint_priority = self.DEFAULT_ENDPOINTS
            self._useragent_rotation_order = list(self.USER_AGENT_PRESETS.keys())
            self._failover_priority = ['mac', 'useragent', 'endpoint', 'stream']
    
    def _is_strategy_enabled(self, strategy: str) -> bool:
        """Check if a failover strategy is enabled."""
        if strategy == 'mac':
            return self._mac_failover_enabled
        elif strategy == 'useragent':
            return self._useragent_failover_enabled
        elif strategy == 'endpoint':
            return self._endpoint_failover_enabled
        elif strategy == 'stream':
            return self._stream_failover_enabled
        elif strategy == 'portal':
            return self._portal_failover_enabled
        return False

    def execute_with_failover(self, operation: Callable, **kwargs) -> Any:
        """
        Execute operation with configured failover strategies.
        
        Requirements: 60.2
        """
        start_time = time.time()
        last_error = None
        
        for strategy in self._failover_priority:
            if not self._is_strategy_enabled(strategy):
                logger.debug(f"Failover strategy '{strategy}' is disabled, skipping")
                continue
            
            try:
                result = self._execute_strategy(strategy, operation, **kwargs)
                return result
            except FailoverExhausted as e:
                logger.debug(f"Failover strategy '{strategy}' exhausted: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Unexpected error in failover strategy '{strategy}': {e}")
                last_error = e
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        raise AllFailoverStrategiesExhausted(f"All failover strategies exhausted after {duration_ms}ms: {last_error}")
    
    def _execute_strategy(self, strategy: str, operation: Callable, **kwargs) -> Any:
        """Execute specific failover strategy."""
        if strategy == 'mac':
            return self._mac_failover(operation, **kwargs)
        elif strategy == 'useragent':
            return self._useragent_failover(operation, **kwargs)
        elif strategy == 'endpoint':
            return self._endpoint_failover(operation, **kwargs)
        elif strategy == 'stream':
            return self._stream_failover(operation, **kwargs)
        else:
            raise ValueError(f"Unknown failover strategy: {strategy}")
    
    def _mac_failover(self, operation: Callable, **kwargs) -> Any:
        """
        Try operation with different MACs.
        
        Requirements: 56.1, 56.2, 56.3
        """
        from apps.m3u.mac_portal_models import FailoverEvent
        from apps.m3u.models import M3UAccount
        
        account = M3UAccount.objects.get(pk=self.account_id)
        last_mac = None
        
        for attempt in range(self._mac_max_attempts):
            mac = self.mac_manager.get_next_mac()
            if not mac:
                raise FailoverExhausted("No MACs available")
            
            start_time = time.time()
            
            try:
                result = operation(mac=mac, **kwargs)
                self.mac_manager.report_success(mac)
                
                # Log successful failover if we switched MACs
                if last_mac and last_mac.id != mac.id:
                    duration_ms = int((time.time() - start_time) * 1000)
                    FailoverEvent.log_failover(
                        account=account,
                        failover_type=FailoverEvent.FailoverType.MAC,
                        original=last_mac.address,
                        new=mac.address,
                        reason="Previous MAC failed",
                        success=True,
                        duration_ms=duration_ms
                    )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                error_type = self._classify_error(e)
                self.mac_manager.report_failure(mac, error_type=error_type, error_message=str(e))
                
                # Log failover attempt
                FailoverEvent.log_failover(
                    account=account,
                    failover_type=FailoverEvent.FailoverType.MAC,
                    original=mac.address,
                    new="next_mac",
                    reason=str(e),
                    success=False,
                    duration_ms=duration_ms
                )
                
                last_mac = mac
                logger.debug(f"MAC {mac.address} failed (attempt {attempt + 1}/{self._mac_max_attempts}): {e}")
        
        raise FailoverExhausted(f"All {self._mac_max_attempts} MAC attempts failed")
    
    def _useragent_failover(self, operation: Callable, **kwargs) -> Any:
        """
        Try operation with different User-Agents.
        
        Requirements: 59.1, 59.2, 59.3, 59.4
        """
        from apps.m3u.mac_portal_models import FailoverEvent
        from apps.m3u.models import M3UAccount
        
        account = M3UAccount.objects.get(pk=self.account_id)
        last_ua = kwargs.get('user_agent', 'MAG250')
        
        for ua_name in self._useragent_rotation_order:
            ua_string = self.USER_AGENT_PRESETS.get(ua_name, ua_name)
            start_time = time.time()
            
            try:
                result = operation(user_agent=ua_string, **kwargs)
                
                # Log successful failover if we switched User-Agents
                if ua_name != last_ua:
                    duration_ms = int((time.time() - start_time) * 1000)
                    FailoverEvent.log_failover(
                        account=account,
                        failover_type=FailoverEvent.FailoverType.USERAGENT,
                        original=last_ua,
                        new=ua_name,
                        reason="Previous User-Agent failed",
                        success=True,
                        duration_ms=duration_ms
                    )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                FailoverEvent.log_failover(
                    account=account,
                    failover_type=FailoverEvent.FailoverType.USERAGENT,
                    original=ua_name,
                    new="next_ua",
                    reason=str(e),
                    success=False,
                    duration_ms=duration_ms
                )
                
                last_ua = ua_name
                logger.debug(f"User-Agent {ua_name} failed: {e}")
        
        raise FailoverExhausted("All User-Agent attempts failed")
    
    def _endpoint_failover(self, operation: Callable, **kwargs) -> Any:
        """
        Try operation with different endpoints.
        
        Requirements: 57.1, 57.2, 57.3, 57.4
        """
        from apps.m3u.mac_portal_models import FailoverEvent
        from apps.m3u.models import M3UAccount
        
        account = M3UAccount.objects.get(pk=self.account_id)
        last_endpoint = kwargs.get('endpoint', self._endpoint_priority[0])
        
        for endpoint in self._endpoint_priority:
            start_time = time.time()
            
            try:
                result = operation(endpoint=endpoint, **kwargs)
                
                # Log successful failover if we switched endpoints
                if endpoint != last_endpoint:
                    duration_ms = int((time.time() - start_time) * 1000)
                    FailoverEvent.log_failover(
                        account=account,
                        failover_type=FailoverEvent.FailoverType.ENDPOINT,
                        original=last_endpoint,
                        new=endpoint,
                        reason="Previous endpoint failed",
                        success=True,
                        duration_ms=duration_ms
                    )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                FailoverEvent.log_failover(
                    account=account,
                    failover_type=FailoverEvent.FailoverType.ENDPOINT,
                    original=endpoint,
                    new="next_endpoint",
                    reason=str(e),
                    success=False,
                    duration_ms=duration_ms
                )
                
                last_endpoint = endpoint
                logger.debug(f"Endpoint {endpoint} failed: {e}")
        
        raise FailoverExhausted("All endpoint attempts failed")
    
    def _stream_failover(self, operation: Callable, **kwargs) -> Any:
        """
        Try operation with stream-level failover.
        
        Requirements: 58.1, 58.2, 58.3, 58.4
        """
        from apps.m3u.mac_portal_models import FailoverEvent
        from apps.m3u.models import M3UAccount
        
        account = M3UAccount.objects.get(pk=self.account_id)
        
        for attempt in range(self._stream_max_retries):
            start_time = time.time()
            
            try:
                result = operation(**kwargs)
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                FailoverEvent.log_failover(
                    account=account,
                    failover_type=FailoverEvent.FailoverType.STREAM,
                    original=f"attempt_{attempt}",
                    new=f"attempt_{attempt + 1}",
                    reason=str(e),
                    success=False,
                    duration_ms=duration_ms
                )
                
                logger.debug(f"Stream attempt {attempt + 1}/{self._stream_max_retries} failed: {e}")
        
        raise FailoverExhausted(f"All {self._stream_max_retries} stream attempts failed")
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate handling."""
        error_str = str(error).lower()
        
        if 'block' in error_str or 'banned' in error_str:
            return 'block'
        elif 'device conflict' in error_str:
            return 'device_conflict'
        elif 'rate limit' in error_str or '429' in error_str:
            return 'rate_limit'
        elif 'expired' in error_str or 'subscription' in error_str:
            return 'expired'
        elif 'auth' in error_str or '401' in error_str or '403' in error_str:
            return 'auth_failure'
        else:
            return 'failure'


class FailoverManagerRegistry:
    """Registry for managing multiple FailoverManager instances."""
    
    _instances: Dict[int, FailoverManager] = {}
    
    @classmethod
    def get_or_create(cls, account_id: int) -> FailoverManager:
        """Get or create a FailoverManager for the given account."""
        if account_id not in cls._instances:
            cls._instances[account_id] = FailoverManager(account_id)
        return cls._instances[account_id]
    
    @classmethod
    def remove(cls, account_id: int):
        """Remove a FailoverManager from the registry."""
        if account_id in cls._instances:
            del cls._instances[account_id]
    
    @classmethod
    def clear_all(cls):
        """Clear all FailoverManager instances."""
        cls._instances.clear()
