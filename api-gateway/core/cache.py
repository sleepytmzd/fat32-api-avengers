"""
Caching Module
Implements distributed caching with Redis backend
"""
import json
import logging
from typing import Any, Optional
import redis.asyncio as redis

from core.config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Distributed cache manager with Redis backend"""
    
    def __init__(self):
        self.enabled = settings.CACHE_ENABLED
        self.redis_client: Optional[redis.Redis] = None
        self._in_memory_cache = {}
    
    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis for caching")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory cache: {e}")
                self.redis_client = None
        
        return self.redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        cache_key = f"cache:{key}"
        
        # Try Redis first
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                value = await redis_client.get(cache_key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis cache get error: {e}")
        
        # Fallback to memory cache
        return self._in_memory_cache.get(cache_key)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        if not self.enabled:
            return False
        
        cache_key = f"cache:{key}"
        ttl = ttl or settings.CACHE_TTL
        
        try:
            serialized = json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Cache serialization error: {e}")
            return False
        
        # Try Redis first
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                await redis_client.setex(cache_key, ttl, serialized)
                return True
            except Exception as e:
                logger.error(f"Redis cache set error: {e}")
        
        # Fallback to memory cache
        self._in_memory_cache[cache_key] = value
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled:
            return False
        
        cache_key = f"cache:{key}"
        
        # Try Redis
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                await redis_client.delete(cache_key)
            except Exception as e:
                logger.error(f"Redis cache delete error: {e}")
        
        # Also delete from memory cache
        if cache_key in self._in_memory_cache:
            del self._in_memory_cache[cache_key]
        
        return True
    
    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern"""
        if not self.enabled:
            return 0
        
        count = 0
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                search_pattern = f"cache:{pattern}*" if pattern else "cache:*"
                cursor = 0
                
                while True:
                    cursor, keys = await redis_client.scan(
                        cursor,
                        match=search_pattern,
                        count=100
                    )
                    
                    if keys:
                        await redis_client.delete(*keys)
                        count += len(keys)
                    
                    if cursor == 0:
                        break
            
            except Exception as e:
                logger.error(f"Redis cache clear error: {e}")
        
        # Clear from memory cache
        if pattern:
            keys_to_delete = [
                k for k in self._in_memory_cache.keys()
                if k.startswith(f"cache:{pattern}")
            ]
        else:
            keys_to_delete = list(self._in_memory_cache.keys())
        
        for key in keys_to_delete:
            del self._in_memory_cache[key]
            count += 1
        
        return count
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled:
            return False
        
        cache_key = f"cache:{key}"
        
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                return await redis_client.exists(cache_key) > 0
            except Exception as e:
                logger.error(f"Redis cache exists error: {e}")
        
        return cache_key in self._in_memory_cache
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in cache"""
        cache_key = f"cache:{key}"
        
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                return await redis_client.incrby(cache_key, amount)
            except Exception as e:
                logger.error(f"Redis increment error: {e}")
        
        # Fallback to memory
        current = self._in_memory_cache.get(cache_key, 0)
        self._in_memory_cache[cache_key] = current + amount
        return self._in_memory_cache[cache_key]
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Closed Redis connection")