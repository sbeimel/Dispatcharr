"""
Central MAC State Manager for BUSY and COOLDOWN flags.

This module provides a unified interface for managing MAC address states
during streaming and failover operations.

IMPORTANT: Uses DATABASE ID as the key for tracking state.
Since duplicate MACs within a portal are prevented, each ID is unique per portal.

BUSY Flag:
- No TTL (manual cleanup only)
- Indicates MAC is actively streaming
- Cleared when stream stops or fails

COOLDOWN Flag:
- TTL from settings (auto-expires)
- Indicates MAC failed and shouldn't be retried
- Duration configurable via WebUI Advanced Settings
"""

import logging
from typing import Optional
from core.utils import RedisClient
from .redis_keys import RedisKeys

logger = logging.getLogger(__name__)


def _get_mac_cooldown_duration() -> int:
    """Get MAC cooldown duration from settings (in seconds)."""
    try:
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings
        settings = MACPortalGlobalSettings.get_settings()
        # mac_cooldown_failure is in minutes, convert to seconds
        return settings.mac_cooldown_failure * 60
    except Exception as e:
        logger.warning(f"Could not load MAC cooldown duration from settings: {e}")
        return 300  # 5 minutes default


def _get_mac_block_cooldown_duration() -> int:
    """Get MAC block cooldown duration from settings (in seconds)."""
    try:
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings
        settings = MACPortalGlobalSettings.get_settings()
        # mac_cooldown_block is in minutes, convert to seconds
        return settings.mac_cooldown_block * 60
    except Exception as e:
        logger.warning(f"Could not load MAC block cooldown duration from settings: {e}")
        return 1800  # 30 minutes default


class MACStateManager:
    """
    Central manager for MAC BUSY and COOLDOWN states.
    
    IMPORTANT: This class uses DATABASE ID as the key.
    Since duplicate MACs within a portal are prevented, each ID is unique.
    
    This class provides a unified interface for all MAC state operations,
    ensuring consistency across the codebase.
    
    Usage:
        manager = MACStateManager()
        manager.mark_busy(mac_id)
        if manager.is_busy(mac_id):
            # MAC is currently streaming
        manager.clear_busy_and_set_cooldown(mac_id)
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize MAC State Manager.
        
        Args:
            redis_client: Optional Redis client. If None, will use default client.
        """
        self.redis_client = redis_client or RedisClient.get_client()
    
    # ==================== BUSY Flag Operations ====================
    
    def mark_busy(self, mac_id: int) -> None:
        """
        Mark MAC as BUSY (actively streaming).
        
        BUSY flag has NO TTL and must be cleared manually when:
        - Stream ends normally
        - Stream fails and triggers failover
        
        Args:
            mac_id: Database ID of M3UAccountMac
        """
        busy_key = f"mac:busy:{mac_id}"
        self.redis_client.set(busy_key, "1")  # No TTL - manual cleanup only
        logger.debug(f"MAC ID {mac_id} marked as BUSY (actively streaming)")
    
    def clear_busy(self, mac_id: int) -> None:
        """
        Clear MAC BUSY flag.
        
        Args:
            mac_id: Database ID of M3UAccountMac
        """
        busy_key = f"mac:busy:{mac_id}"
        self.redis_client.delete(busy_key)
        logger.debug(f"MAC ID {mac_id} BUSY flag cleared")
    
    def is_busy(self, mac_id: int) -> bool:
        """
        Check if MAC is currently BUSY (actively streaming).
        
        Args:
            mac_id: Database ID of M3UAccountMac
            
        Returns:
            True if MAC is busy, False otherwise
        """
        busy_key = f"mac:busy:{mac_id}"
        return bool(self.redis_client.exists(busy_key))
    
    # ==================== COOLDOWN Flag Operations ====================
    
    def mark_cooldown(self, mac_id: int, is_block: bool = False) -> None:
        """
        Mark MAC in COOLDOWN (failed and shouldn't be retried).
        
        COOLDOWN flag has TTL from WebUI Advanced Settings:
        - Normal failure: mac_cooldown_failure (default 5 min)
        - Block/Device conflict: mac_cooldown_block (default 30 min)
        
        Args:
            mac_id: Database ID of M3UAccountMac
            is_block: If True, use longer block cooldown duration
        """
        cooldown_key = f"mac:cooldown:{mac_id}"
        
        if is_block:
            duration = _get_mac_block_cooldown_duration()
            reason = "block/device_conflict"
        else:
            duration = _get_mac_cooldown_duration()
            reason = "failure"
        
        self.redis_client.setex(cooldown_key, duration, "1")
        logger.info(f"MAC ID {mac_id} in COOLDOWN for {duration}s (reason: {reason})")
    
    def is_in_cooldown(self, mac_id: int) -> bool:
        """
        Check if MAC is in COOLDOWN period.
        
        Args:
            mac_id: Database ID of M3UAccountMac
            
        Returns:
            True if MAC is in cooldown, False otherwise
        """
        cooldown_key = f"mac:cooldown:{mac_id}"
        return bool(self.redis_client.exists(cooldown_key))
    
    def get_cooldown_ttl(self, mac_id: int) -> Optional[int]:
        """
        Get remaining COOLDOWN time in seconds.
        
        Args:
            mac_id: Database ID of M3UAccountMac
            
        Returns:
            Remaining seconds, or None if not in cooldown
        """
        cooldown_key = f"mac:cooldown:{mac_id}"
        ttl = self.redis_client.ttl(cooldown_key)
        return ttl if ttl > 0 else None
    
    # ==================== Combined Operations ====================
    
    def clear_busy_and_set_cooldown(self, mac_id: int, is_block: bool = False) -> None:
        """
        Atomic operation: Clear BUSY flag and set COOLDOWN flag.
        
        This is the most common operation when a stream fails:
        1. Clear BUSY (MAC no longer streaming)
        2. Set COOLDOWN (prevent immediate retry)
        
        Args:
            mac_id: Database ID of M3UAccountMac
            is_block: If True, use longer block cooldown duration
        """
        self.clear_busy(mac_id)
        self.mark_cooldown(mac_id, is_block)
        logger.info(f"MAC ID {mac_id}: BUSY cleared, COOLDOWN set")
    
    def get_mac_state(self, mac_id: int) -> dict:
        """
        Get complete state information for a MAC.
        
        Args:
            mac_id: Database ID of M3UAccountMac
            
        Returns:
            Dictionary with state information:
            {
                'mac_id': int,
                'is_busy': bool,
                'is_in_cooldown': bool,
                'cooldown_ttl': int or None
            }
        """
        return {
            'mac_id': mac_id,
            'is_busy': self.is_busy(mac_id),
            'is_in_cooldown': self.is_in_cooldown(mac_id),
            'cooldown_ttl': self.get_cooldown_ttl(mac_id)
        }


# ==================== Convenience Functions ====================

def mark_mac_busy(mac_id: int, redis_client=None) -> None:
    """Convenience function to mark MAC as BUSY."""
    manager = MACStateManager(redis_client)
    manager.mark_busy(mac_id)


def clear_mac_busy(mac_id: int, redis_client=None) -> None:
    """Convenience function to clear MAC BUSY flag."""
    manager = MACStateManager(redis_client)
    manager.clear_busy(mac_id)


def is_mac_busy(mac_id: int, redis_client=None) -> bool:
    """Convenience function to check if MAC is BUSY."""
    manager = MACStateManager(redis_client)
    return manager.is_busy(mac_id)


def mark_mac_cooldown(mac_id: int, is_block: bool = False, redis_client=None) -> None:
    """Convenience function to mark MAC in COOLDOWN."""
    manager = MACStateManager(redis_client)
    manager.mark_cooldown(mac_id, is_block)


def is_mac_in_cooldown(mac_id: int, redis_client=None) -> bool:
    """Convenience function to check if MAC is in COOLDOWN."""
    manager = MACStateManager(redis_client)
    return manager.is_in_cooldown(mac_id)


def clear_busy_and_set_cooldown(mac_id: int, is_block: bool = False, redis_client=None) -> None:
    """Convenience function for atomic BUSY clear + COOLDOWN set."""
    manager = MACStateManager(redis_client)
    manager.clear_busy_and_set_cooldown(mac_id, is_block)
