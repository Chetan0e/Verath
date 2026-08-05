import time
import asyncio

from app.core.cache import cached, invalidate_cache
from fastapi import Response

from app.core.cache import (
    SimpleCache,
    add_cache_header,
    get_cache_stats,
    invalidate_cache,
)


def test_get_missing_key_returns_none():
    cache = SimpleCache()

    assert cache.get("missing") is None


def test_set_and_get_value():
    cache = SimpleCache()

    cache.set("name", "verath")

    assert cache.get("name") == "verath"


def test_delete_removes_key():
    cache = SimpleCache()

    cache.set("key", "value")
    cache.delete("key")

    assert cache.get("key") is None


def test_clear_removes_all_entries():
    cache = SimpleCache()

    cache.set("a", 1)
    cache.set("b", 2)

    cache.clear()

    assert cache.get("a") is None
    assert cache.get("b") is None


def test_ttl_expiration():
    cache = SimpleCache()

    cache.set("temp", "value", ttl_seconds=1)

    assert cache.get("temp") == "value"

    time.sleep(1.1)

    assert cache.get("temp") is None


def test_invalidate_pattern_removes_matching_keys():
    cache = SimpleCache()

    cache.set("user:1", "alice")
    cache.set("user:2", "bob")
    cache.set("admin:1", "root")

    cache.invalidate_pattern("user")

    assert cache.get("user:1") is None
    assert cache.get("user:2") is None
    assert cache.get("admin:1") == "root"


def test_add_cache_header_hit():
    response = Response()

    add_cache_header(response, True)

    assert response.headers["X-Cache"] == "HIT"


def test_add_cache_header_miss():
    response = Response()

    add_cache_header(response, False)

    assert response.headers["X-Cache"] == "MISS"


def test_get_cache_stats_returns_expected_keys():
    invalidate_cache()

    stats = get_cache_stats()

    assert "size" in stats
    assert "keys" in stats
    assert isinstance(stats["keys"], list)


def test_cached_sync_function():
    invalidate_cache()

    calls = {"count": 0}

    @cached(ttl_seconds=60)
    def add(a, b):
        calls["count"] += 1
        return a + b

    assert add(2, 3) == 5
    assert add(2, 3) == 5
    assert calls["count"] == 1


def test_invalidate_cache_clears_cached_sync_result():
    invalidate_cache()

    calls = {"count": 0}

    @cached(ttl_seconds=60)
    def multiply(a, b):
        calls["count"] += 1
        return a * b

    multiply(2, 4)
    invalidate_cache()
    multiply(2, 4)

    assert calls["count"] == 2


def test_cached_async_function():
    invalidate_cache()

    calls = {"count": 0}

    @cached(ttl_seconds=60)
    async def square(x):
        calls["count"] += 1
        return x * x

    async def runner():
        assert await square(5) == 25
        assert await square(5) == 25

    asyncio.run(runner())

    assert calls["count"] == 1