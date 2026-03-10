"""
Phase 11C: Redis Caching Layer

Provides caching for:
- Research results (TTL: 7 days)
- Design inspiration (TTL: 30 days)
- LLM responses (TTL: 24 hours)
- Embeddings (TTL: 30 days)

Also includes rate limiting for external APIs.
"""

from backend.cache.manager import CacheManager, get_cache_manager
from backend.cache.decorators import cached, cache_key
from backend.cache.rate_limiter import RateLimiter, get_rate_limiter

__all__ = [
    "CacheManager",
    "get_cache_manager",
    "cached",
    "cache_key",
    "RateLimiter",
    "get_rate_limiter"
]
