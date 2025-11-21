import json
import os
from typing import Optional, Any
from datetime import timedelta
import redis
import structlog

logger = structlog.get_logger(__name__)


class RedisCache:
    """Redis cache client for product service"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        
    def init_redis(self) -> redis.Redis:
        """Initialize Redis connection"""
        # Check if Redis URL is provided
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            # Use Redis URL (e.g., redis://redis:6379)
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            logger.info("Redis connection configured from URL", redis_url=redis_url)
        else:
            # Use individual host/port/password settings
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            password = os.getenv("REDIS_PASSWORD", "")
            
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            logger.info("Redis connection configured", host=host, port=port)
        
        try:
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            return self.redis_client
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def close(self):
        """Close Redis connection"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")
    
    # we are creating this product key eg. product1 for id=1
    def _get_product_key(self, product_id: str) -> str:
        """Generate Redis key for product"""
        return f"product:{product_id}"
    
    def get_product(self, product_id: str) -> Optional[dict]:
        """Get product from cache"""
        if not self.redis_client:
            return None
            
        try:
            key = self._get_product_key(product_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                logger.info("Cache hit", product_id=product_id)
                return json.loads(cached_data)
            else:
                logger.debug("Cache miss", product_id=product_id)
                return None
                
        except Exception as e:
            logger.warning("Failed to get product from cache", 
                          product_id=product_id, error=str(e))
            return None
    
    def set_product(self, product_id: str, product_data: dict, 
                    ttl: timedelta = timedelta(minutes=5)) -> bool:
        """Set product in cache"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_product_key(product_id)
            serialized_data = json.dumps(product_data, default=str)
            
            self.redis_client.setex(
                key, 
                int(ttl.total_seconds()), 
                serialized_data
            )
            
            logger.debug("Product cached", product_id=product_id, ttl_seconds=int(ttl.total_seconds()))
            return True
            
        except Exception as e:
            logger.warning("Failed to cache product", 
                          product_id=product_id, error=str(e))
            return False
    
    def delete_product(self, product_id: str) -> bool:
        """Delete product from cache"""
        if not self.redis_client:
            return False
            
        try:
            key = self._get_product_key(product_id)
            result = self.redis_client.delete(key)
            
            if result:
                logger.debug("Product cache invalidated", product_id=product_id)
            
            return bool(result)
            
        except Exception as e:
            logger.warning("Failed to delete product from cache", 
                          product_id=product_id, error=str(e))
            return False
    
    def clear_all_products(self) -> bool:
        """Clear all product cache entries"""
        if not self.redis_client:
            return False
            
        try:
            pattern = "product:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info("Product cache cleared", deleted_count=deleted_count)
                return True
            else:
                logger.debug("No product cache entries to clear")
                return True
                
        except Exception as e:
            logger.warning("Failed to clear product cache", error=str(e))
            return False


# Global cache instance
redis_cache = RedisCache()


# Convenience functions following the Go pattern
def get_product(product_id: str) -> Optional[dict]:
    """Get product from cache"""
    return redis_cache.get_product(product_id)


def set_product(product_id: str, product_data: dict, 
                ttl: timedelta = timedelta(minutes=5)) -> bool:
    """Set product in cache"""
    return redis_cache.set_product(product_id, product_data, ttl)


def delete_product(product_id: str) -> bool:
    """Delete product from cache"""
    return redis_cache.delete_product(product_id)
