"""
Token Management System for MAC Portal.

Handles:
- Token storage with expiry timestamp
- Proactive token refresh at 80% TTL
- Automatic re-authentication on 401
- Token persistence across sessions
- Keep-alive for active sessions

Requirements: 41.1, 41.2, 41.3, 41.4, 42.1, 42.2, 42.3, 42.4, 43.1, 43.2, 43.3, 43.4
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages portal tokens with automatic refresh and persistence.
    
    Requirements: 41.1, 41.2, 41.3, 41.4
    """
    
    # Default TTL for tokens (1 hour)
    DEFAULT_TTL = 3600
    
    # Refresh threshold (refresh at 80% of TTL)
    DEFAULT_REFRESH_THRESHOLD = 0.8
    
    def __init__(self, account_id: int, mac_address: str):
        """
        Initialize TokenManager for a specific account and MAC.
        
        Args:
            account_id: The M3UAccount ID
            mac_address: The MAC address
        """
        self.account_id = account_id
        self.mac_address = mac_address
        self.token: Optional[str] = None
        self.token_random: Optional[str] = None
        self.play_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.token_ttl: int = self.DEFAULT_TTL
        self.refresh_threshold: float = self.DEFAULT_REFRESH_THRESHOLD
        self._lock = threading.Lock()
        self._handshake_func: Optional[Callable] = None
        
        # Try to restore from cache
        self._restore_from_cache()
    
    @property
    def cache_key(self) -> str:
        """Generate cache key for this token."""
        return f"mac_token:{self.account_id}:{self.mac_address}"
    
    def set_handshake_function(self, func: Callable):
        """Set the handshake function to use for re-authentication."""
        self._handshake_func = func
    
    def get_token(self) -> Optional[str]:
        """
        Get valid token, refreshing if needed.
        
        Requirements: 41.1, 41.2
        """
        with self._lock:
            if self._should_refresh():
                logger.debug(f"Token needs refresh for MAC {self.mac_address[:8]}...")
                self._refresh_token()
            return self.token
    
    def set_token(self, token: str, token_random: str = None, play_token: str = None, ttl: int = None):
        """
        Set a new token with optional TTL.
        
        Requirements: 41.1
        """
        with self._lock:
            self.token = token
            self.token_random = token_random
            self.play_token = play_token
            self.token_ttl = ttl or self.DEFAULT_TTL
            self.token_expiry = timezone.now() + timedelta(seconds=self.token_ttl)
            self._persist_to_cache()
            logger.debug(f"Token set for MAC {self.mac_address[:8]}..., expires at {self.token_expiry}")
    
    def invalidate(self):
        """Invalidate the current token."""
        with self._lock:
            self.token = None
            self.token_random = None
            self.play_token = None
            self.token_expiry = None
            cache.delete(self.cache_key)
            logger.debug(f"Token invalidated for MAC {self.mac_address[:8]}...")

    def _should_refresh(self) -> bool:
        """
        Check if token needs refresh based on TTL.
        
        Requirements: 41.2
        """
        if not self.token or not self.token_expiry:
            return True
        
        now = timezone.now()
        if now >= self.token_expiry:
            return True
        
        # Calculate remaining time
        remaining = (self.token_expiry - now).total_seconds()
        threshold_seconds = self.token_ttl * (1 - self.refresh_threshold)
        
        return remaining < threshold_seconds
    
    def _refresh_token(self):
        """
        Refresh the token using the handshake function.
        
        Requirements: 41.2, 41.3
        """
        if not self._handshake_func:
            logger.warning(f"No handshake function set for MAC {self.mac_address[:8]}...")
            return
        
        try:
            logger.info(f"Refreshing token for MAC {self.mac_address[:8]}...")
            result = self._handshake_func()
            if result:
                # Handshake function should call set_token
                logger.info(f"Token refreshed successfully for MAC {self.mac_address[:8]}...")
        except Exception as e:
            logger.error(f"Failed to refresh token for MAC {self.mac_address[:8]}...: {e}")
            self.invalidate()
    
    def _persist_to_cache(self):
        """
        Save token state to cache.
        
        Requirements: 42.1
        """
        if not self.token:
            return
        
        data = {
            'token': self.token,
            'token_random': self.token_random,
            'play_token': self.play_token,
            'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None,
            'token_ttl': self.token_ttl,
        }
        
        # Cache for the remaining TTL
        remaining = 0
        if self.token_expiry:
            remaining = max(0, int((self.token_expiry - timezone.now()).total_seconds()))
        
        cache.set(self.cache_key, data, timeout=remaining or self.token_ttl)
        logger.debug(f"Token persisted to cache for MAC {self.mac_address[:8]}...")
    
    def _restore_from_cache(self):
        """
        Load token state from cache.
        
        Requirements: 42.2, 42.3
        """
        data = cache.get(self.cache_key)
        if not data:
            return
        
        self.token = data.get('token')
        self.token_random = data.get('token_random')
        self.play_token = data.get('play_token')
        self.token_ttl = data.get('token_ttl', self.DEFAULT_TTL)
        
        expiry_str = data.get('token_expiry')
        if expiry_str:
            try:
                self.token_expiry = datetime.fromisoformat(expiry_str)
                if timezone.is_naive(self.token_expiry):
                    self.token_expiry = timezone.make_aware(self.token_expiry)
            except (ValueError, TypeError):
                self.token_expiry = None
        
        # Validate restored token
        if self.token and self.token_expiry:
            if timezone.now() >= self.token_expiry:
                logger.debug(f"Restored token expired for MAC {self.mac_address[:8]}..., invalidating")
                self.invalidate()
            else:
                logger.debug(f"Token restored from cache for MAC {self.mac_address[:8]}...")
    
    def is_valid(self) -> bool:
        """Check if current token is valid."""
        if not self.token:
            return False
        if not self.token_expiry:
            return False
        return timezone.now() < self.token_expiry
    
    def get_remaining_seconds(self) -> int:
        """Get remaining token validity in seconds."""
        if not self.token_expiry:
            return 0
        remaining = (self.token_expiry - timezone.now()).total_seconds()
        return max(0, int(remaining))


class KeepAliveManager:
    """
    Manages keep-alive requests for active streaming sessions.
    
    Requirements: 43.1, 43.2, 43.3, 43.4
    """
    
    # Default keep-alive interval (5 minutes)
    DEFAULT_INTERVAL = 300
    
    def __init__(self, token_manager: TokenManager, interval: int = None):
        """
        Initialize KeepAliveManager.
        
        Args:
            token_manager: The TokenManager instance
            interval: Keep-alive interval in seconds (default: 5 minutes)
        """
        self.token_manager = token_manager
        self.interval = interval or self.DEFAULT_INTERVAL
        self._active = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._keep_alive_func: Optional[Callable] = None
    
    def set_keep_alive_function(self, func: Callable):
        """Set the keep-alive function to call periodically."""
        self._keep_alive_func = func
    
    def start(self):
        """
        Start sending keep-alive requests.
        
        Requirements: 43.1
        """
        if self._active:
            return
        
        self._active = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
        self._thread.start()
        logger.debug(f"Keep-alive started for MAC {self.token_manager.mac_address[:8]}...")
    
    def stop(self):
        """
        Stop sending keep-alive requests.
        
        Requirements: 43.4
        """
        if not self._active:
            return
        
        self._active = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.debug(f"Keep-alive stopped for MAC {self.token_manager.mac_address[:8]}...")
    
    def _keep_alive_loop(self):
        """Background loop for sending keep-alive requests."""
        while not self._stop_event.wait(timeout=self.interval):
            if not self._active:
                break
            
            try:
                self._send_keep_alive()
            except Exception as e:
                logger.error(f"Keep-alive failed: {e}")
                # Try to refresh token on failure
                self.token_manager._refresh_token()
    
    def _send_keep_alive(self):
        """
        Send a keep-alive request.
        
        Requirements: 43.2, 43.3
        """
        if not self._keep_alive_func:
            logger.debug("No keep-alive function set, skipping")
            return
        
        try:
            self._keep_alive_func()
            logger.debug(f"Keep-alive sent for MAC {self.token_manager.mac_address[:8]}...")
        except Exception as e:
            logger.warning(f"Keep-alive request failed: {e}")
            raise


class TokenManagerRegistry:
    """
    Registry for managing multiple TokenManager instances.
    """
    
    _instances: Dict[str, TokenManager] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_or_create(cls, account_id: int, mac_address: str) -> TokenManager:
        """Get or create a TokenManager for the given account and MAC."""
        key = f"{account_id}:{mac_address}"
        
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = TokenManager(account_id, mac_address)
            return cls._instances[key]
    
    @classmethod
    def remove(cls, account_id: int, mac_address: str):
        """Remove a TokenManager from the registry."""
        key = f"{account_id}:{mac_address}"
        
        with cls._lock:
            if key in cls._instances:
                cls._instances[key].invalidate()
                del cls._instances[key]
    
    @classmethod
    def clear_all(cls):
        """Clear all TokenManager instances."""
        with cls._lock:
            for manager in cls._instances.values():
                manager.invalidate()
            cls._instances.clear()
