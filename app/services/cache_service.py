import logging
import json
import redis
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

class RedisCacheService:
    """Redis cache service for storing and retrieving cached data."""

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0,
                 default_ttl: int = 3600):
        """
        Initialize Redis cache service.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            default_ttl: Default time-to-live in seconds
        """
        try:
            self.redis_client = redis.from_url(url=settings.redis.url)
            self.redis_client.ping()
            self.default_ttl = settings.redis.ttl
            logger.info(f"Redis connection established at {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (uses default if not specified)

        Returns:
            True if successful
        """
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"Cached key '{key}' with TTL {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key '{key}': {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = self.redis_client.get(key)
            if value is None:
                logger.debug(f"Cache miss for key '{key}'")
                return None
            logger.debug(f"Cache hit for key '{key}'")
            return json.loads(value)
        except Exception as e:
            logger.error(f"Error retrieving cache for key '{key}': {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        Delete a value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"Deleted key '{key}'")
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache for key '{key}': {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking existence of key '{key}': {e}")
            return False

    def clear(self) -> bool:
        """
        Clear all entries from the current database.

        Returns:
            True if successful
        """
        try:
            self.redis_client.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def close(self):
        """Close Redis connection."""
        try:
            self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

_redis_cache_service = None
def get_redis_cache_service():
    global _redis_cache_service
    if _redis_cache_service is None:
        _redis_cache_service = RedisCacheService()
    return _redis_cache_service

def is_redis_cache_enabled():
    return settings.redis.url is not None