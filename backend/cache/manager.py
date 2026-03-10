"""
Phase 11C: Redis Cache Manager

Centralized cache management with configurable TTLs per cache type.
"""

import json
import hashlib
import pickle
from datetime import timedelta
from typing import Any, Dict, Optional, Union
import redis
from backend.config.settings import get_settings


# Cache TTL configurations
CACHE_TTLS = {
    "research": timedelta(days=7),
    "design_inspiration": timedelta(days=30),
    "llm_response": timedelta(hours=24),
    "embeddings": timedelta(days=30),
    "default": timedelta(hours=1),
    "short": timedelta(minutes=15),
    "medium": timedelta(hours=6),
    "long": timedelta(days=14),
}

# Cache key prefixes
CACHE_PREFIXES = {
    "research": "research:",
    "design_inspiration": "design:",
    "llm_response": "llm:",
    "embeddings": "emb:",
    "project": "proj:",
    "agent": "agent:",
    "rate_limit": "rl:",
}


class CacheManager:
    """
    Redis-based cache manager with TTL support and typed cache categories.
    """
    
    _instance: Optional["CacheManager"] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        settings = get_settings()
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        
        try:
            self._redis = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=getattr(settings, 'redis_db', 0),
                password=getattr(settings, 'redis_password', None),
                decode_responses=False,  # We handle encoding ourselves
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            self._redis.ping()
            self._connected = True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis connection failed: {e}. Cache will be disabled.")
            self._redis = None
            self._connected = False
        
        self._initialized = True
    
    @property
    def connected(self) -> bool:
        return self._connected and self._redis is not None
    
    def _make_key(self, key: str, cache_type: str = "default") -> str:
        """Create a namespaced cache key"""
        prefix = CACHE_PREFIXES.get(cache_type, "cache:")
        return f"{prefix}{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first for common types
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize stored value"""
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(data)
    
    def get(
        self,
        key: str,
        cache_type: str = "default",
        default: Any = None
    ) -> Any:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache (research, llm_response, etc.)
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        if not self.connected:
            return default
        
        try:
            full_key = self._make_key(key, cache_type)
            data = self._redis.get(full_key)
            
            if data is None:
                return default
            
            return self._deserialize(data)
        except Exception as e:
            print(f"Cache get error: {e}")
            return default
    
    def set(
        self,
        key: str,
        value: Any,
        cache_type: str = "default",
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            cache_type: Type of cache
            ttl: Time to live (uses default for cache_type if not specified)
            
        Returns:
            True if successful
        """
        if not self.connected:
            return False
        
        try:
            full_key = self._make_key(key, cache_type)
            data = self._serialize(value)
            
            # Determine TTL
            if ttl is None:
                ttl = CACHE_TTLS.get(cache_type, CACHE_TTLS["default"])
            
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            else:
                ttl_seconds = ttl
            
            self._redis.setex(full_key, ttl_seconds, data)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str, cache_type: str = "default") -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            cache_type: Type of cache
            
        Returns:
            True if deleted
        """
        if not self.connected:
            return False
        
        try:
            full_key = self._make_key(key, cache_type)
            return bool(self._redis.delete(full_key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str, cache_type: str = "default") -> bool:
        """Check if key exists in cache"""
        if not self.connected:
            return False
        
        try:
            full_key = self._make_key(key, cache_type)
            return bool(self._redis.exists(full_key))
        except Exception:
            return False
    
    def get_ttl(self, key: str, cache_type: str = "default") -> Optional[int]:
        """Get remaining TTL for a key in seconds"""
        if not self.connected:
            return None
        
        try:
            full_key = self._make_key(key, cache_type)
            ttl = self._redis.ttl(full_key)
            return ttl if ttl >= 0 else None
        except Exception:
            return None
    
    def clear_type(self, cache_type: str) -> int:
        """
        Clear all keys of a specific cache type.
        
        Args:
            cache_type: Type of cache to clear
            
        Returns:
            Number of keys deleted
        """
        if not self.connected:
            return 0
        
        try:
            prefix = CACHE_PREFIXES.get(cache_type, "cache:")
            pattern = f"{prefix}*"
            
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += self._redis.delete(*keys)
                if cursor == 0:
                    break
            
            return deleted
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cached data (use with caution)"""
        if not self.connected:
            return False
        
        try:
            self._redis.flushdb()
            return True
        except Exception as e:
            print(f"Cache flush error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.connected:
            return {"connected": False}
        
        try:
            info = self._redis.info()
            
            # Count keys by type
            type_counts = {}
            for cache_type, prefix in CACHE_PREFIXES.items():
                cursor = 0
                count = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=f"{prefix}*", count=100)
                    count += len(keys)
                    if cursor == 0:
                        break
                type_counts[cache_type] = count
            
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_keys": info.get("db0", {}).get("keys", 0) if isinstance(info.get("db0"), dict) else 0,
                "keys_by_type": type_counts,
                "hit_rate": self._calculate_hit_rate(info),
                "uptime_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> Optional[float]:
        """Calculate cache hit rate from Redis info"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return None
        
        return round(hits / total * 100, 2)


def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate a deterministic cache key from arguments.
    
    Args:
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        MD5 hash of the arguments
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cache_manager() -> CacheManager:
    """Get the singleton CacheManager instance"""
    return CacheManager()
