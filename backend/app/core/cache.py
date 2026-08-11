import time
import hashlib
import inspect
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


def _default_key_func(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    Builds a deterministic key suffix from ALL bound arguments instead of
    a hand-picked subset (previously only user_id/date were used, which
    caused different calls — e.g. different post_id — to collide on the
    same cache key). Uses inspect.signature to bind args/kwargs to
    parameter names so equivalent calls (positional vs keyword) produce
    the SAME key, while calls with different values always differ.
    """
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        arg_items = sorted(bound.arguments.items())
    except TypeError:
        # Fallback for signatures that don't bind cleanly (e.g. *args-only)
        arg_items = [("args", args), ("kwargs", sorted(kwargs.items()))]

    return repr(arg_items)


def cached(ttl_seconds: int = 300, key_prefix: str = "", key_func: Optional[Callable] = None):
    """
    Decorator to cache function results with TTL.
    
    Args:
        ttl_seconds: Time to live in seconds (default 5 minutes)
        key_prefix: Prefix for cache key
        key_func: Optional callable (func, args, kwargs) -> str. Use this
            to explicitly control which arguments participate in the cache
            key — e.g. to exclude a non-hashable object like a db session.
            If omitted, ALL bound arguments are used by default (safe).
    """
    def decorator(func: Callable) -> Callable:

        def _build_key_hash(args, kwargs) -> str:
            if key_func is not None:
                key_suffix = key_func(func, args, kwargs)
            else:
                key_suffix = _default_key_func(func, args, kwargs)

            key = ":".join([key_prefix, func.__name__, key_suffix])
            return hashlib.md5(key.encode()).hexdigest()

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key_hash = _build_key_hash(args, kwargs)

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
            key_hash = _build_key_hash(args, kwargs)

            cached_value = _cache.get(key_hash)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            _cache.set(key_hash, result, ttl_seconds)

            return result

        # Return appropriate wrapper based on whether function is async
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
