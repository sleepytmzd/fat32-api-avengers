"""
Rate Limiting Module
Implements sliding window rate limiting with Redis backend
"""
import time
import logging
from typing import Optional
import redis.asyncio as redis

from core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Sliding window rate limiter"""
    
    def __init__(self):
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.requests_limit = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW
        self.redis_client: Optional[redis.Redis] = None
        self._in_memory_store = {}
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis for rate limiting")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory store: {e}")
                self.redis_client = None
        
        return self.redis_client
    
    async def check_limit(
        self,
        client_id: str,
        service_name: Optional[str] = None
    ) -> bool:
        """
        Check if request is within rate limit
        Returns True if allowed, False if rate limit exceeded
        """
        if not self.enabled:
            return True
        
        key = f"rate_limit:{client_id}"
        if service_name:
            key += f":{service_name}"
        
        current_time = time.time()
        
        # Try Redis first
        redis_client = await self._get_redis_client()
        
        if redis_client:
            return await self._check_redis(redis_client, key, current_time)
        else:
            return self._check_memory(key, current_time)
    
    async def _check_redis(
        self,
        redis_client: redis.Redis,
        key: str,
        current_time: float
    ) -> bool:
        """Check rate limit using Redis"""
        try:
            window_start = current_time - self.window
            
            # Use Redis sorted set for sliding window
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window)
            
            results = await pipe.execute()
            request_count = results[1]
            
            return request_count < self.requests_limit
        
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return self._check_memory(key, current_time)
    
    def _check_memory(self, key: str, current_time: float) -> bool:
        """Fallback in-memory rate limiting"""
        window_start = current_time - self.window
        
        # Initialize if key doesn't exist
        if key not in self._in_memory_store:
            self._in_memory_store[key] = []
        
        # Remove old entries
        self._in_memory_store[key] = [
            ts for ts in self._in_memory_store[key]
            if ts > window_start
        ]
        
        # Check limit
        if len(self._in_memory_store[key]) >= self.requests_limit:
            return False
        
        # Add current request
        self._in_memory_store[key].append(current_time)
        
        return True
    
    async def get_remaining(
        self,
        client_id: str,
        service_name: Optional[str] = None
    ) -> int:
        """Get remaining requests in current window"""
        if not self.enabled:
            return self.requests_limit
        
        key = f"rate_limit:{client_id}"
        if service_name:
            key += f":{service_name}"
        
        current_time = time.time()
        window_start = current_time - self.window
        
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                count = await redis_client.zcount(key, window_start, current_time)
                return max(0, self.requests_limit - count)
            except Exception as e:
                logger.error(f"Error getting remaining requests: {e}")
        
        # Fallback to memory
        if key in self._in_memory_store:
            valid_requests = [
                ts for ts in self._in_memory_store[key]
                if ts > window_start
            ]
            return max(0, self.requests_limit - len(valid_requests))
        
        return self.requests_limit
    
    async def reset(self, client_id: str, service_name: Optional[str] = None):
        """Reset rate limit for a client"""
        key = f"rate_limit:{client_id}"
        if service_name:
            key += f":{service_name}"
        
        redis_client = await self._get_redis_client()
        
        if redis_client:
            try:
                await redis_client.delete(key)
            except Exception as e:
                logger.error(f"Error resetting rate limit: {e}")
        
        # Also clear from memory
        if key in self._in_memory_store:
            del self._in_memory_store[key]