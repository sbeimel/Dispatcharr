"""
MAC Rotation Manager for MAC Portal.

Handles:
- MAC address rotation with health-based selection
- Cooldown management after failures
- Health score calculation
- Auto-recovery after cooldown

Requirements: 23.1, 23.2, 23.3, 46.1, 46.2, 46.3, 49.1, 56.4
"""

import logging
import random
import threading
from typing import Optional, List, Dict
from django.utils import timezone

logger = logging.getLogger(__name__)


class MACRotationManager:
    """
    Manages MAC address rotation with cooldown and health tracking.
    
    Requirements: 23.1, 23.2, 23.3
    """
    
    class SelectionStrategy:
        ROUND_ROBIN = "round_robin"
        HEALTH_BASED = "health_based"
        RANDOM = "random"
    
    def __init__(self, account_id: int):
        """
        Initialize MACRotationManager for a specific account.
        
        Args:
            account_id: The M3UAccount ID
        """
        self.account_id = account_id
        self._current_index = 0
        self._lock = threading.Lock()
        self._strategy = self.SelectionStrategy.HEALTH_BASED
        
        # Load settings
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from database."""
        from apps.m3u.mac_portal_models import MACPortalGlobalSettings, FailoverSettings
        
        try:
            global_settings = MACPortalGlobalSettings.get_settings()
            failover_settings = FailoverSettings.get_settings()
            
            self._cooldown_failure_minutes = global_settings.mac_cooldown_failure
            self._cooldown_block_minutes = global_settings.mac_cooldown_block
            self._strategy = failover_settings.mac_selection_strategy
            self._max_attempts = failover_settings.mac_max_attempts
        except Exception as e:
            logger.warning(f"Failed to load settings, using defaults: {e}")
            self._cooldown_failure_minutes = 5
            self._cooldown_block_minutes = 30
            self._strategy = self.SelectionStrategy.HEALTH_BASED
            self._max_attempts = 3
    
    def _get_all_macs(self) -> List:
        """Get all MAC addresses for this account."""
        from apps.m3u.models import M3UAccount
        
        try:
            account = M3UAccount.objects.get(pk=self.account_id)
            return list(account.macs.all().order_by('priority', 'id'))
        except M3UAccount.DoesNotExist:
            logger.error(f"Account {self.account_id} not found")
            return []
    
    def _is_in_cooldown(self, mac) -> bool:
        """Check if a MAC is currently in cooldown."""
        from apps.m3u.mac_portal_models import MACCooldown
        return MACCooldown.is_mac_in_cooldown(mac)
    
    def _get_health_score(self, mac) -> int:
        """Get health score for a MAC."""
        from apps.m3u.mac_portal_models import MACHealthRecord
        return MACHealthRecord.get_health_score(mac)
    
    def get_next_mac(self) -> Optional[object]:
        """
        Get next available MAC, excluding those in cooldown.
        
        Requirements: 23.1, 23.2
        """
        with self._lock:
            all_macs = self._get_all_macs()
            if not all_macs:
                logger.warning(f"No MACs available for account {self.account_id}")
                return None
            
            # Filter out MACs in cooldown or with bad status
            available = []
            for mac in all_macs:
                if self._is_in_cooldown(mac):
                    logger.debug(f"MAC {mac.address} is in cooldown, skipping")
                    continue
                if mac.status in ['expired', 'error']:
                    logger.debug(f"MAC {mac.address} has status {mac.status}, skipping")
                    continue
                available.append(mac)
            
            if not available:
                logger.warning(f"No available MACs for account {self.account_id} (all in cooldown or bad status)")
                return None
            
            # Select based on strategy
            if self._strategy == self.SelectionStrategy.ROUND_ROBIN:
                return self._select_round_robin(available)
            elif self._strategy == self.SelectionStrategy.RANDOM:
                return self._select_random(available)
            else:  # HEALTH_BASED (default)
                return self._select_health_based(available)
    
    def _select_round_robin(self, available: List) -> object:
        """Select MAC using round-robin strategy."""
        self._current_index = self._current_index % len(available)
        mac = available[self._current_index]
        self._current_index += 1
        return mac
    
    def _select_random(self, available: List) -> object:
        """Select MAC randomly."""
        return random.choice(available)
    
    def _select_health_based(self, available: List) -> object:
        """
        Select MAC with highest health score.
        
        Requirements: 23.1
        """
        # Get health scores for all available MACs
        mac_scores = [(mac, self._get_health_score(mac)) for mac in available]
        
        # Sort by health score (descending)
        mac_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return MAC with highest score
        return mac_scores[0][0]

    def report_failure(self, mac, error_type: str = "failure", error_message: str = ""):
        """
        Report MAC failure and apply cooldown if needed.
        
        Requirements: 23.3, 46.1, 46.2
        """
        from apps.m3u.mac_portal_models import MACHealthRecord, MACCooldown
        
        # Record the failure
        MACHealthRecord.record_failure(mac, error_message=error_message)
        
        # Determine cooldown duration based on error type
        if error_type in ['block', 'device_conflict']:
            cooldown_minutes = self._cooldown_block_minutes
            reason = MACCooldown.CooldownReason.BLOCK
        elif error_type == 'rate_limit':
            cooldown_minutes = self._cooldown_failure_minutes
            reason = MACCooldown.CooldownReason.RATE_LIMIT
        elif error_type == 'expired':
            # Don't apply cooldown for expired, just mark status
            mac.status = 'expired'
            mac.save(update_fields=['status'])
            return
        else:
            cooldown_minutes = self._cooldown_failure_minutes
            reason = MACCooldown.CooldownReason.FAILURE
        
        # Apply cooldown
        MACCooldown.apply_cooldown(mac, reason, cooldown_minutes)
        logger.info(f"Applied {cooldown_minutes}min cooldown to MAC {mac.address} (reason: {reason})")
    
    def report_success(self, mac, response_time_ms: int = None, endpoint_used: str = ""):
        """
        Report successful MAC usage.
        
        Requirements: 49.1
        """
        from apps.m3u.mac_portal_models import MACHealthRecord
        
        # Record the success
        MACHealthRecord.record_success(mac, response_time_ms=response_time_ms, endpoint_used=endpoint_used)
        
        # Update MAC status if needed
        if mac.status != 'valid':
            mac.status = 'valid'
            mac.last_checked = timezone.now()
            mac.save(update_fields=['status', 'last_checked'])
    
    def reset_cooldown(self, mac):
        """
        Manually reset cooldown for a MAC.
        
        Requirements: 46.3
        """
        from apps.m3u.mac_portal_models import MACCooldown
        
        MACCooldown.objects.filter(mac=mac, is_active=True).update(is_active=False)
        logger.info(f"Cooldown reset for MAC {mac.address}")
    
    def get_mac_status(self, mac) -> Dict:
        """Get detailed status for a MAC."""
        from apps.m3u.mac_portal_models import MACCooldown, MACHealthRecord
        
        cooldown = MACCooldown.get_active_cooldown(mac)
        health_score = MACHealthRecord.get_health_score(mac)
        
        return {
            'address': mac.address,
            'status': mac.status,
            'health_score': health_score,
            'in_cooldown': cooldown is not None,
            'cooldown_remaining': cooldown.remaining_seconds if cooldown else 0,
            'cooldown_reason': cooldown.reason if cooldown else None,
            'expires_at': mac.expires_at,
            'last_checked': mac.last_checked,
        }
    
    def get_all_mac_statuses(self) -> List[Dict]:
        """Get status for all MACs in this account."""
        all_macs = self._get_all_macs()
        return [self.get_mac_status(mac) for mac in all_macs]
    
    def check_and_recover_macs(self):
        """
        Check for MACs that can be recovered from cooldown.
        
        Requirements: 56.4
        """
        from apps.m3u.mac_portal_models import MACCooldown
        
        # Find expired cooldowns
        expired_cooldowns = MACCooldown.objects.filter(
            mac__account_id=self.account_id,
            is_active=True,
            expires_at__lte=timezone.now()
        )
        
        count = expired_cooldowns.count()
        if count > 0:
            expired_cooldowns.update(is_active=False)
            logger.info(f"Recovered {count} MACs from cooldown for account {self.account_id}")
        
        return count


class MACRotationManagerRegistry:
    """
    Registry for managing multiple MACRotationManager instances.
    """
    
    _instances: Dict[int, MACRotationManager] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_or_create(cls, account_id: int) -> MACRotationManager:
        """Get or create a MACRotationManager for the given account."""
        with cls._lock:
            if account_id not in cls._instances:
                cls._instances[account_id] = MACRotationManager(account_id)
            return cls._instances[account_id]
    
    @classmethod
    def remove(cls, account_id: int):
        """Remove a MACRotationManager from the registry."""
        with cls._lock:
            if account_id in cls._instances:
                del cls._instances[account_id]
    
    @classmethod
    def clear_all(cls):
        """Clear all MACRotationManager instances."""
        with cls._lock:
            cls._instances.clear()
