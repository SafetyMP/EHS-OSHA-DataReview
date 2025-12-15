"""
Caching layer for query results.
Provides in-memory and optional Redis caching.
"""

from functools import wraps
import hashlib
import json
import time
from typing import Any, Callable, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# In-memory cache
_memory_cache: Dict[str, tuple] = {}  # {key: (value, expiry_timestamp)}


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    # Create a stable representation of arguments
    key_data = {
        'args': str(args),
        'kwargs': sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def get_from_cache(key: str, ttl: int = 3600) -> Optional[Any]:
    """
    Get value from cache if not expired.
    
    Args:
        key: Cache key
        ttl: Time-to-live in seconds (default: 1 hour)
    
    Returns:
        Cached value or None if not found/expired
    """
    if key in _memory_cache:
        value, expiry = _memory_cache[key]
        if time.time() < expiry:
            logger.debug(f"Cache HIT: {key}")
            return value
        else:
            # Expired, remove it
            del _memory_cache[key]
            logger.debug(f"Cache EXPIRED: {key}")
    
    logger.debug(f"Cache MISS: {key}")
    return None


def set_in_cache(key: str, value: Any, ttl: int = 3600):
    """
    Store value in cache with TTL.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time-to-live in seconds (default: 1 hour)
    """
    expiry = time.time() + ttl
    _memory_cache[key] = (value, expiry)
    logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")


def cached(ttl: int = 3600, max_size: int = 1000):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (default: 1 hour)
        max_size: Maximum cache size (default: 1000 entries)
    
    Usage:
        @cached(ttl=1800)  # Cache for 30 minutes
        def expensive_function(param1, param2):
            # ... expensive computation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Check cache
            cached_result = get_from_cache(key, ttl)
            if cached_result is not None:
                return cached_result
            
            # Cache miss, compute result
            result = func(*args, **kwargs)
            
            # Enforce max cache size
            if len(_memory_cache) >= max_size:
                # Remove oldest entries (simple FIFO)
                oldest_key = min(_memory_cache.keys(), 
                               key=lambda k: _memory_cache[k][1])
                del _memory_cache[oldest_key]
            
            # Store in cache
            set_in_cache(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def clear_cache(pattern: Optional[str] = None):
    """
    Clear cache entries.
    
    Args:
        pattern: If provided, only clear keys matching pattern (None = clear all)
    """
    if pattern is None:
        _memory_cache.clear()
        logger.info("Cache cleared")
    else:
        keys_to_remove = [k for k in _memory_cache.keys() if pattern in k]
        for key in keys_to_remove:
            del _memory_cache[key]
        logger.info(f"Cleared {len(keys_to_remove)} cache entries matching '{pattern}'")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    now = time.time()
    valid_entries = sum(1 for _, (_, expiry) in _memory_cache.items() if now < expiry)
    expired_entries = len(_memory_cache) - valid_entries
    
    return {
        'total_entries': len(_memory_cache),
        'valid_entries': valid_entries,
        'expired_entries': expired_entries,
        'hit_rate': 'N/A'  # Would need tracking for actual hit rate
    }

