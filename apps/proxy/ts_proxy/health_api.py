"""
Health check API endpoints for failover system monitoring.
"""

import time
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def failover_health(request):
    """Get overall failover system health."""
    try:
        from .failover_metrics import failover_metrics
        from .predictive_failover import predictive_failover
        from core.utils import RedisClient
        
        # Get basic health summary
        health_summary = failover_metrics.get_health_summary()
        
        # Get predictive insights
        global_insights = predictive_failover.get_global_insights()
        
        # Get Redis connection status
        redis_status = "unknown"
        try:
            redis_client = RedisClient.get_client()
            redis_client.ping()
            redis_status = "healthy"
        except Exception:
            redis_status = "unhealthy"
        
        # Combine all health data
        health_data = {
            "status": "healthy" if redis_status == "healthy" else "degraded",
            "redis_status": redis_status,
            "failover_metrics": health_summary,
            "predictive_insights": global_insights,
            "timestamp": int(time.time())
        }
        
        return JsonResponse(health_data)
        
    except Exception as e:
        logger.error(f"Failed to get failover health: {e}")
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "timestamp": int(time.time())
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def channel_insights(request, channel_id):
    """Get detailed insights for a specific channel."""
    try:
        from .predictive_failover import predictive_failover
        from core.utils import RedisClient
        
        # Get channel-specific insights
        insights = predictive_failover.get_channel_insights(channel_id)
        
        # Get current Redis state for the channel
        redis_state = {}
        try:
            redis_client = RedisClient.get_client()
            from .redis_keys import RedisKeys
            
            # Check various Redis keys for this channel
            metadata_key = RedisKeys.channel_metadata(channel_id)
            metadata = redis_client.hgetall(metadata_key)
            
            redis_state = {
                "has_metadata": bool(metadata),
                "metadata_keys": list(metadata.keys()) if metadata else [],
                "buffer_exists": redis_client.exists(RedisKeys.buffer_index(channel_id)),
                "stopping": redis_client.exists(RedisKeys.channel_stopping(channel_id)),
                "clients_count": redis_client.scard(RedisKeys.clients(channel_id))
            }
            
        except Exception as e:
            redis_state = {"error": str(e)}
        
        response_data = {
            "channel_id": channel_id,
            "insights": insights,
            "redis_state": redis_state,
            "timestamp": int(time.time())
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Failed to get channel insights for {channel_id}: {e}")
        return JsonResponse({
            "channel_id": channel_id,
            "error": str(e),
            "timestamp": int(time.time())
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def redis_stats(request):
    """Get Redis performance statistics."""
    try:
        from core.utils import RedisClient
        
        redis_client = RedisClient.get_client()
        
        # Get Redis info
        redis_info = redis_client.info()
        
        # Extract relevant stats
        stats = {
            "connected_clients": redis_info.get("connected_clients", 0),
            "used_memory": redis_info.get("used_memory", 0),
            "used_memory_human": redis_info.get("used_memory_human", "0B"),
            "keyspace_hits": redis_info.get("keyspace_hits", 0),
            "keyspace_misses": redis_info.get("keyspace_misses", 0),
            "total_commands_processed": redis_info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": redis_info.get("instantaneous_ops_per_sec", 0),
        }
        
        # Calculate hit rate
        hits = stats["keyspace_hits"]
        misses = stats["keyspace_misses"]
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        stats["hit_rate_percent"] = round(hit_rate, 2)
        
        # Get failover-specific key counts
        try:
            failover_keys = {
                "mac_busy_keys": len(redis_client.keys("ts_proxy:mac:*:busy")),
                "mac_cooldown_keys": len(redis_client.keys("ts_proxy:mac:*:cooldown")),
                "profile_cooldown_keys": len(redis_client.keys("ts_proxy:profile:*:cooldown")),
                "stream_profile_mappings": len(redis_client.keys("ts_proxy:stream_profile:*")),
                "channel_metadata_keys": len(redis_client.keys("ts_proxy:channel:*:metadata"))
            }
            stats["failover_keys"] = failover_keys
        except Exception as e:
            stats["failover_keys"] = {"error": str(e)}
        
        return JsonResponse({
            "status": "healthy",
            "redis_stats": stats,
            "timestamp": int(time.time())
        })
        
    except Exception as e:
        logger.error(f"Failed to get Redis stats: {e}")
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "timestamp": int(time.time())
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_caches(request):
    """Clear all caches (for debugging/maintenance)."""
    try:
        from .redis_optimizer import RedisOptimizer
        from core.utils import RedisClient
        
        # Clear Redis optimizer caches if available
        redis_client = RedisClient.get_client()
        optimizer = RedisOptimizer(redis_client)
        optimizer.clear_cache()
        
        return JsonResponse({
            "status": "success",
            "message": "Caches cleared successfully",
            "timestamp": int(time.time())
        })
        
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "timestamp": int(time.time())
        }, status=500)