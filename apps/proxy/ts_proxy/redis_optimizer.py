"""
Redis operations optimizer with batching and caching.
"""

import time
import logging
from typing import Dict, Any, List, Tuple
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


def redis_retry(max_attempts: int = 3, delay: float = 0.1):
    """Decorator for Redis operations with retry logic."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        logger.debug(f"Redis operation failed, retrying ({attempt + 1}/{max_attempts}): {e}")
                    else:
                        logger.error(f"Redis operation failed after {max_attempts} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


class RedisOptimizer:
    """Optimizes Redis operations with batching, caching, and retry logic."""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self._cache_lock = Lock()
        self._mac_entry_cache = {}
        self._cache_ttl = 60  # 1 minute cache TTL
    
    @redis_retry(max_attempts=3)
    def batch_operations(self, operations: List[Tuple[str, str, Any]]) -> List[Any]:
        """Execute multiple Redis operations in a pipeline.
        
        Args:
            operations: List of (operation, key, value) tuples
            
        Returns:
            List of operation results
        """
        if not operations:
            return []
        
        try:
            pipeline = self.redis_client.pipeline()
            
            for operation, key, value in operations:
                if operation == "set":
                    pipeline.set(key, value)
                elif operation == "setex":
                    ttl, val = value
                    pipeline.setex(key, ttl, val)
                elif operation == "get":
                    pipeline.get(key)
                elif operation == "delete":
                    pipeline.delete(key)
                elif operation == "exists":
                    pipeline.exists(key)
                elif operation == "sadd":
                    pipeline.sadd(key, value)
                elif operation == "srem":
                    pipeline.srem(key, value)
                elif operation == "scard":
                    pipeline.scard(key)
                elif operation == "hset":
                    pipeline.hset(key, mapping=value)
                elif operation == "hget":
                    pipeline.hget(key, value)
                elif operation == "hgetall":
                    pipeline.hgetall(key)
                else:
                    logger.warning(f"Unknown Redis operation: {operation}")
            
            results = pipeline.execute()
            logger.debug(f"Executed {len(operations)} Redis operations in batch")
            return results
            
        except Exception as e:
            logger.error(f"Redis batch operation failed: {e}")
            raise
    
    @redis_retry(max_attempts=3)
    def set_with_ttl(self, key: str, value: Any, ttl: int):
        """Set key with TTL."""
        return self.redis_client.setex(key, ttl, value)
    
    @redis_retry(max_attempts=3)
    def get_multiple(self, keys: List[str]) -> List[Any]:
        """Get multiple keys efficiently."""
        if not keys:
            return []
        return self.redis_client.mget(keys)
    
    @redis_retry(max_attempts=3)
    def delete_multiple(self, keys: List[str]) -> int:
        """Delete multiple keys efficiently."""
        if not keys:
            return 0
        return self.redis_client.delete(*keys)
    
    def get_mac_entry_cached(self, mac_address: str):
        """Get MAC entry with caching."""
        with self._cache_lock:
            cache_key = f"mac_entry:{mac_address}"
            current_time = time.time()
            
            # Check cache
            if cache_key in self._mac_entry_cache:
                entry, timestamp = self._mac_entry_cache[cache_key]
                if current_time - timestamp < self._cache_ttl:
                    return entry
                else:
                    # Cache expired
                    del self._mac_entry_cache[cache_key]
            
            # Cache miss - fetch from database
            try:
                from apps.m3u.models import M3UAccountMac
                entry = M3UAccountMac.objects.filter(address__iexact=mac_address).first()
                
                # Cache the result
                self._mac_entry_cache[cache_key] = (entry, current_time)
                
                # Clean old cache entries periodically
                if len(self._mac_entry_cache) > 100:
                    self._cleanup_cache()
                
                return entry
                
            except Exception as e:
                logger.error(f"Failed to fetch MAC entry for {mac_address}: {e}")
                return None
    
    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._mac_entry_cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._mac_entry_cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear_cache(self):
        """Clear all cached entries."""
        with self._cache_lock:
            self._mac_entry_cache.clear()
            logger.debug("Cleared MAC entry cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            current_time = time.time()
            valid_entries = sum(
                1 for _, timestamp in self._mac_entry_cache.values()
                if current_time - timestamp < self._cache_ttl
            )
            
            return {
                "total_entries": len(self._mac_entry_cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self._mac_entry_cache) - valid_entries,
                "cache_ttl": self._cache_ttl
            }