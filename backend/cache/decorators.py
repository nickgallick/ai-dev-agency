"""
Phase 11C: Cache Decorators

Provides @cached decorator for easy function caching.
"""

import functools
import hashlib
import json
import inspect
from typing import Any, Callable, Optional, Union
from datetime import timedelta

from backend.cache.manager import get_cache_manager, CACHE_TTLS


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        MD5 hash string
    """
    # Convert args and kwargs to a serializable format
    def make_serializable(obj):
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif isinstance(obj, (list, tuple)):
            return [make_serializable(i) for i in obj]
        elif isinstance(obj, dict):
            return {str(k): make_serializable(v) for k, v in obj.items()}
        else:
            return str(obj)
    
    key_data = {
        "args": make_serializable(args),
        "kwargs": make_serializable(kwargs)
    }
    
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(
    cache_type: str = "default",
    ttl: Optional[Union[int, timedelta]] = None,
    key_prefix: str = "",
    skip_args: tuple = ("self", "cls", "db"),
    skip_if: Optional[Callable[..., bool]] = None
):
    """
    Decorator to cache function results.
    
    Args:
        cache_type: Type of cache (research, llm_response, etc.)
        ttl: Custom TTL (uses cache_type default if None)
        key_prefix: Optional prefix for cache key
        skip_args: Argument names to exclude from cache key
        skip_if: Optional function that returns True to skip caching
        
    Example:
        @cached(cache_type="research", ttl=timedelta(days=7))
        async def fetch_research(query: str) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Get function signature for argument processing
        sig = inspect.signature(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Check if caching should be skipped
            if skip_if and skip_if(*args, **kwargs):
                return await func(*args, **kwargs)
            
            # Build cache key from arguments
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Filter out skipped arguments
            key_args = {
                k: v for k, v in bound.arguments.items()
                if k not in skip_args
            }
            
            # Generate cache key
            func_key = f"{key_prefix}{func.__module__}.{func.__name__}"
            arg_key = cache_key(**key_args)
            full_key = f"{func_key}:{arg_key}"
            
            # Try to get from cache
            cached_value = cache.get(full_key, cache_type)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(full_key, result, cache_type, ttl)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Check if caching should be skipped
            if skip_if and skip_if(*args, **kwargs):
                return func(*args, **kwargs)
            
            # Build cache key from arguments
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Filter out skipped arguments
            key_args = {
                k: v for k, v in bound.arguments.items()
                if k not in skip_args
            }
            
            # Generate cache key
            func_key = f"{key_prefix}{func.__module__}.{func.__name__}"
            arg_key = cache_key(**key_args)
            full_key = f"{func_key}:{arg_key}"
            
            # Try to get from cache
            cached_value = cache.get(full_key, cache_type)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(full_key, result, cache_type, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def invalidate_cache(
    func: Callable,
    cache_type: str = "default",
    key_prefix: str = "",
    skip_args: tuple = ("self", "cls", "db"),
    *args,
    **kwargs
) -> bool:
    """
    Manually invalidate cache for a specific function call.
    
    Args:
        func: The cached function
        cache_type: Type of cache used
        key_prefix: Prefix used in @cached decorator
        skip_args: Same skip_args used in @cached decorator
        *args, **kwargs: The exact arguments to invalidate
        
    Returns:
        True if cache was deleted
    """
    cache = get_cache_manager()
    sig = inspect.signature(func)
    
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    
    key_args = {
        k: v for k, v in bound.arguments.items()
        if k not in skip_args
    }
    
    func_key = f"{key_prefix}{func.__module__}.{func.__name__}"
    arg_key = cache_key(**key_args)
    full_key = f"{func_key}:{arg_key}"
    
    return cache.delete(full_key, cache_type)
