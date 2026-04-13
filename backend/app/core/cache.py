import time
import hashlib
from functools import wraps
from typing import Callable, Any, Optional
from fastapi import Response


class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        if key not in self._cache:
            return None
        
        # Check TTL
        if key in self._timestamps:
            if time.time() > self._timestamps[key]:
                # Expired
                del self._cache[key]
                del self._timestamps[key]
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl_seconds: int = None):
        """Set value in cache with optional TTL."""
        self._cache[key] = value
        if ttl_seconds:
            self._timestamps[key] = time.time() + ttl_seconds
    
    def delete(self, key: str):
        """Delete a specific key from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
    
    def invalidate_pattern(self, pattern: str):
        """Delete all keys matching a pattern."""
        keys_to_delete = [k for k in self._cache.keys() if pattern in k]
        for key in keys_to_delete:
            self.delete(key)


# Global cache instance
_cache = SimpleCache()


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results with TTL.
    
    Args:
        ttl_seconds: Time to live in seconds (default 5 minutes)
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            
            # Add user_id if present in kwargs or args
            if 'user_id' in kwargs:
                key_parts.append(str(kwargs['user_id']))
            elif args and hasattr(args[0], 'user_id'):
                key_parts.append(str(args[0].user_id))
            
            # Add date if present for daily caches
            if 'date' in kwargs:
                key_parts.append(str(kwargs['date']))
            
            key = ":".join(key_parts)
            key_hash = hashlib.md5(key.encode()).hexdigest()
            
            # Check cache
            cached_value = _cache.get(key_hash)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            _cache.set(key_hash, result, ttl_seconds)
            
            return result
        
        # Also support sync functions
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key_parts = [key_prefix, func.__name__]
            
            if 'user_id' in kwargs:
                key_parts.append(str(kwargs['user_id']))
            elif args and hasattr(args[0], 'user_id'):
                key_parts.append(str(args[0].user_id))
            
            if 'date' in kwargs:
                key_parts.append(str(kwargs['date']))
            
            key = ":".join(key_parts)
            key_hash = hashlib.md5(key.encode()).hexdigest()
            
            cached_value = _cache.get(key_hash)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            _cache.set(key_hash, result, ttl_seconds)
            
            return result
        
        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "size": len(_cache._cache),
        "keys": list(_cache._cache.keys())
    }


def invalidate_cache(pattern: str = ""):
    """Invalidate cache entries matching pattern."""
    if pattern:
        _cache.invalidate_pattern(pattern)
    else:
        _cache.clear()


def add_cache_header(response: Response, hit: bool):
    """Add X-Cache header to response."""
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return response
