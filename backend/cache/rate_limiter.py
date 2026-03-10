"""
Phase 11C: API Rate Limiter

Rate limiting for external APIs:
- OpenRouter
- v0 Platform API
- GitHub
- Tavily
"""

import time
from typing import Dict, Optional
from datetime import datetime
import redis
from backend.config.settings import get_settings


# Default rate limits (requests per minute)
DEFAULT_RATE_LIMITS = {
    "openrouter": 60,       # 60 requests per minute
    "v0_api": 20,           # 20 requests per minute
    "github": 30,           # 30 requests per minute (with auth)
    "tavily": 100,          # 100 requests per minute
    "stability": 10,        # 10 requests per minute
    "openai": 60,           # 60 requests per minute
    "default": 60,          # Default fallback
}

# Rate limit window in seconds
RATE_LIMIT_WINDOW = 60


class RateLimiter:
    """
    Redis-based sliding window rate limiter.
    
    Uses a sliding log algorithm for accurate rate limiting.
    """
    
    _instance: Optional["RateLimiter"] = None
    
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
        self._local_counts: Dict[str, list] = {}  # Fallback for no Redis
        
        try:
            self._redis = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=getattr(settings, 'redis_db', 0),
                password=getattr(settings, 'redis_password', None),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._redis.ping()
            self._connected = True
        except (redis.ConnectionError, redis.TimeoutError):
            self._redis = None
            self._connected = False
        
        self._initialized = True
    
    def _get_key(self, api_name: str) -> str:
        """Generate Redis key for rate limit tracking"""
        return f"rl:{api_name}:requests"
    
    def _get_limit(self, api_name: str) -> int:
        """Get rate limit for an API"""
        return DEFAULT_RATE_LIMITS.get(api_name, DEFAULT_RATE_LIMITS["default"])
    
    def check(self, api_name: str) -> bool:
        """
        Check if request is allowed without consuming a slot.
        
        Args:
            api_name: Name of the API to check
            
        Returns:
            True if request would be allowed
        """
        current_count = self._get_current_count(api_name)
        limit = self._get_limit(api_name)
        return current_count < limit
    
    def acquire(self, api_name: str, wait: bool = True, timeout: float = 30) -> bool:
        """
        Acquire a rate limit slot.
        
        Args:
            api_name: Name of the API
            wait: If True, wait until slot is available
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if slot was acquired
        """
        limit = self._get_limit(api_name)
        start_time = time.time()
        
        while True:
            current_count = self._get_current_count(api_name)
            
            if current_count < limit:
                self._record_request(api_name)
                return True
            
            if not wait:
                return False
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return False
            
            # Wait a bit before retrying
            wait_time = min(1, timeout - elapsed)
            time.sleep(wait_time)
    
    async def acquire_async(self, api_name: str, wait: bool = True, timeout: float = 30) -> bool:
        """
        Async version of acquire.
        
        Args:
            api_name: Name of the API
            wait: If True, wait until slot is available
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if slot was acquired
        """
        import asyncio
        
        limit = self._get_limit(api_name)
        start_time = time.time()
        
        while True:
            current_count = self._get_current_count(api_name)
            
            if current_count < limit:
                self._record_request(api_name)
                return True
            
            if not wait:
                return False
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return False
            
            # Wait a bit before retrying
            wait_time = min(1, timeout - elapsed)
            await asyncio.sleep(wait_time)
    
    def _get_current_count(self, api_name: str) -> int:
        """Get current request count within the window"""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        if self._connected and self._redis:
            try:
                key = self._get_key(api_name)
                # Remove old entries
                self._redis.zremrangebyscore(key, 0, window_start)
                # Count entries in window
                return self._redis.zcard(key)
            except redis.RedisError:
                pass
        
        # Fallback to local counting
        if api_name not in self._local_counts:
            self._local_counts[api_name] = []
        
        # Clean old entries
        self._local_counts[api_name] = [
            ts for ts in self._local_counts[api_name]
            if ts > window_start
        ]
        
        return len(self._local_counts[api_name])
    
    def _record_request(self, api_name: str):
        """Record a request timestamp"""
        now = time.time()
        
        if self._connected and self._redis:
            try:
                key = self._get_key(api_name)
                # Add timestamp to sorted set
                self._redis.zadd(key, {str(now): now})
                # Set expiry on the key
                self._redis.expire(key, RATE_LIMIT_WINDOW * 2)
                return
            except redis.RedisError:
                pass
        
        # Fallback to local
        if api_name not in self._local_counts:
            self._local_counts[api_name] = []
        self._local_counts[api_name].append(now)
    
    def get_status(self, api_name: str) -> Dict:
        """
        Get rate limit status for an API.
        
        Args:
            api_name: Name of the API
            
        Returns:
            Status dict with current, limit, remaining, reset_in
        """
        limit = self._get_limit(api_name)
        current = self._get_current_count(api_name)
        
        return {
            "api": api_name,
            "current": current,
            "limit": limit,
            "remaining": max(0, limit - current),
            "reset_in_seconds": RATE_LIMIT_WINDOW,
            "is_limited": current >= limit,
        }
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get rate limit status for all configured APIs"""
        return {
            api_name: self.get_status(api_name)
            for api_name in DEFAULT_RATE_LIMITS.keys()
            if api_name != "default"
        }
    
    def reset(self, api_name: str):
        """Reset rate limit for an API"""
        if self._connected and self._redis:
            try:
                key = self._get_key(api_name)
                self._redis.delete(key)
            except redis.RedisError:
                pass
        
        if api_name in self._local_counts:
            self._local_counts[api_name] = []
    
    def reset_all(self):
        """Reset all rate limits"""
        for api_name in DEFAULT_RATE_LIMITS.keys():
            self.reset(api_name)


def get_rate_limiter() -> RateLimiter:
    """Get the singleton RateLimiter instance"""
    return RateLimiter()


# Decorator for rate-limited functions
def rate_limited(api_name: str, wait: bool = True, timeout: float = 30):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        api_name: Name of the API being called
        wait: If True, wait for rate limit slot
        timeout: Maximum wait time
        
    Example:
        @rate_limited("openrouter")
        async def call_llm(prompt: str):
            ...
    """
    import functools
    import inspect
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            if not await limiter.acquire_async(api_name, wait, timeout):
                raise Exception(f"Rate limit exceeded for {api_name}")
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            limiter = get_rate_limiter()
            if not limiter.acquire(api_name, wait, timeout):
                raise Exception(f"Rate limit exceeded for {api_name}")
            return func(*args, **kwargs)
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
