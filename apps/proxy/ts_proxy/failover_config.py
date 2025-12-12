"""
Centralized configuration management for failover system.
"""

import time
from typing import Dict, Any
from django.db import connection


class FailoverConfig:
    """Centralized configuration for failover system with database integration."""
    
    # Default values
    DEFAULT_MAC_COOLDOWN_SECONDS = 300  # 5 minutes
    DEFAULT_PROFILE_COOLDOWN_SECONDS = 300  # 5 minutes
    DEFAULT_MAX_FAILOVER_ATTEMPTS = 3
    DEFAULT_BUSY_CHECK_ENABLED = True
    DEFAULT_PREDICTIVE_FAILOVER_ENABLED = False
    DEFAULT_FAILURE_RATE_THRESHOLD = 0.8  # 80%
    DEFAULT_CIRCUIT_BREAKER_ENABLED = True
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5
    DEFAULT_CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes
    
    # Cache for settings
    _settings_cache = None
    _settings_cache_time = 0
    _settings_cache_ttl = 30  # Cache for 30 seconds
    
    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Get failover settings from database with caching."""
        now = time.time()
        if cls._settings_cache and (now - cls._settings_cache_time) < cls._settings_cache_ttl:
            return cls._settings_cache
        
        try:
            from core.models import CoreSettings
            settings = CoreSettings.get_proxy_settings()
            
            # Merge with failover-specific settings
            failover_settings = {
                "mac_cooldown_seconds": settings.get("mac_cooldown_seconds", cls.DEFAULT_MAC_COOLDOWN_SECONDS),
                "profile_cooldown_seconds": settings.get("profile_cooldown_seconds", cls.DEFAULT_PROFILE_COOLDOWN_SECONDS),
                "max_failover_attempts": settings.get("max_failover_attempts", cls.DEFAULT_MAX_FAILOVER_ATTEMPTS),
                "busy_check_enabled": settings.get("busy_check_enabled", cls.DEFAULT_BUSY_CHECK_ENABLED),
                "predictive_failover_enabled": settings.get("predictive_failover_enabled", cls.DEFAULT_PREDICTIVE_FAILOVER_ENABLED),
                "failure_rate_threshold": settings.get("failure_rate_threshold", cls.DEFAULT_FAILURE_RATE_THRESHOLD),
                "circuit_breaker_enabled": settings.get("circuit_breaker_enabled", cls.DEFAULT_CIRCUIT_BREAKER_ENABLED),
                "circuit_breaker_threshold": settings.get("circuit_breaker_threshold", cls.DEFAULT_CIRCUIT_BREAKER_THRESHOLD),
                "circuit_breaker_timeout": settings.get("circuit_breaker_timeout", cls.DEFAULT_CIRCUIT_BREAKER_TIMEOUT),
            }
            
            cls._settings_cache = failover_settings
            cls._settings_cache_time = now
            return failover_settings
            
        except Exception:
            # Return defaults if database query fails
            return {
                "mac_cooldown_seconds": cls.DEFAULT_MAC_COOLDOWN_SECONDS,
                "profile_cooldown_seconds": cls.DEFAULT_PROFILE_COOLDOWN_SECONDS,
                "max_failover_attempts": cls.DEFAULT_MAX_FAILOVER_ATTEMPTS,
                "busy_check_enabled": cls.DEFAULT_BUSY_CHECK_ENABLED,
                "predictive_failover_enabled": cls.DEFAULT_PREDICTIVE_FAILOVER_ENABLED,
                "failure_rate_threshold": cls.DEFAULT_FAILURE_RATE_THRESHOLD,
                "circuit_breaker_enabled": cls.DEFAULT_CIRCUIT_BREAKER_ENABLED,
                "circuit_breaker_threshold": cls.DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
                "circuit_breaker_timeout": cls.DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
            }
        finally:
            try:
                connection.close()
            except Exception:
                pass
    
    @classmethod
    def get_mac_cooldown_seconds(cls) -> int:
        return cls.get_settings()["mac_cooldown_seconds"]
    
    @classmethod
    def get_profile_cooldown_seconds(cls) -> int:
        return cls.get_settings()["profile_cooldown_seconds"]
    
    @classmethod
    def get_max_failover_attempts(cls) -> int:
        return cls.get_settings()["max_failover_attempts"]
    
    @classmethod
    def is_busy_check_enabled(cls) -> bool:
        return cls.get_settings()["busy_check_enabled"]
    
    @classmethod
    def is_predictive_failover_enabled(cls) -> bool:
        return cls.get_settings()["predictive_failover_enabled"]
    
    @classmethod
    def get_failure_rate_threshold(cls) -> float:
        return cls.get_settings()["failure_rate_threshold"]
    
    @classmethod
    def is_circuit_breaker_enabled(cls) -> bool:
        return cls.get_settings()["circuit_breaker_enabled"]
    
    @classmethod
    def get_circuit_breaker_threshold(cls) -> int:
        return cls.get_settings()["circuit_breaker_threshold"]
    
    @classmethod
    def get_circuit_breaker_timeout(cls) -> int:
        return cls.get_settings()["circuit_breaker_timeout"]