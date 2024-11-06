# src/storage/cache.py
import redis
import json
from typing import Optional, Any, Dict, Union
#from typing import Optional, Any, Dict, Union
import logging
import hashlib
from datetime import datetime, timedelta

class ResponseCache:
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """Initialize the response cache using Redis."""
        self.logger = logging.getLogger(__name__)
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
        self.default_ttl = 3600  # 1 hour default TTL

    def get_response(self, query: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached response for a query."""
        try:
            key = self._generate_key(query)
            cached_response = self.redis_client.get(key)
            
            if cached_response:
                return json.loads(cached_response)
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving from cache: {e}")
            return None

    def store_response(
        self,
        query: str,
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """Store a response in the cache."""
        try:
            key = self._generate_key(query)
            self.redis_client.setex(
                key,
                ttl or self.default_ttl,
                json.dumps(response)
            )
        except Exception as e:
            self.logger.error(f"Error storing in cache: {e}")

    # src/storage/cache.py (continued)
    def invalidate(self, query: str):
        """Invalidate a cached response."""
        try:
            key = self._generate_key(query)
            self.redis_client.delete(key)
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {e}")

    def _generate_key(self, query: str) -> str:
        """Generate a cache key from a query."""
        return f"whisper:query:{hashlib.md5(query.encode()).hexdigest()}"

    def flush_all(self):
        """Clear all cached responses."""
        try:
            self.redis_client.flushdb()
        except Exception as e:
            self.logger.error(f"Error flushing cache: {e}")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        try:
            info = self.redis_client.info()
            return {
                'total_keys': self.redis_client.dbsize(),
                'used_memory': info.get('used_memory_human', 'N/A'),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}

    def update_ttl(self, query: str, new_ttl: int):
        """Update TTL for a cached response."""
        try:
            key = self._generate_key(query)
            if self.redis_client.exists(key):
                self.redis_client.expire(key, new_ttl)
        except Exception as e:
            self.logger.error(f"Error updating TTL: {e}")