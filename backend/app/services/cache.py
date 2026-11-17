import json
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

# Fallback in-memory cache when Redis is unavailable
_in_memory_cache: Dict[str, Dict[str, Any]] = {}
_redis_disabled = False

# Initialize Redis client (with error handling)
try:
    import redis.asyncio as redis
    redis_client = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        socket_connect_timeout=0.2,
        socket_timeout=0.2
    )
except Exception as e:
    logger.warning(f"Failed to initialize Redis client: {e}")
    redis_client = None
    _redis_disabled = True

async def get_revenue_summary(
    property_id: str, 
    tenant_id: str,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching with strict tenant isolation to improve performance.
    """
    # Strict tenant-isolated cache key
    if month and year:
        cache_key = f"revenue:{tenant_id}:{property_id}:{year}:{month}"
    else:
        cache_key = f"revenue:{tenant_id}:{property_id}"
    
    # Try to get from Redis cache
    global _redis_disabled
    if redis_client and not _redis_disabled:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            _redis_disabled = True
            logger.debug(f"Redis unavailable, falling back to local memory cache: {e}")

    # Check local in-memory cache
    if cache_key in _in_memory_cache:
        return _in_memory_cache[cache_key]
    
    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_total_revenue
    
    # Calculate revenue
    result = await calculate_total_revenue(property_id, tenant_id, month=month, year=year)
    
    # Cache the result for 5 minutes
    if redis_client:
        try:
            await redis_client.setex(cache_key, 300, json.dumps(result))
        except Exception as e:
            logger.debug(f"Redis set failed for {cache_key}: {e}")

    _in_memory_cache[cache_key] = result
    
    return result
