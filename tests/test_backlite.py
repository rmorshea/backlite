import shutil
import time
from collections.abc import Iterator
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from backlite import Cache
from backlite.types import CacheItem

CACHES_DIR = Path(__file__).parent / "caches"


@pytest.fixture(autouse=True)
def clean_caches_dir() -> Iterator[None]:
    CACHES_DIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(CACHES_DIR, ignore_errors=True)


class CleanCache(Cache):
    __init__ = (
        Cache.__init__
        if TYPE_CHECKING
        else lambda self, p, *a, **kw: super(CleanCache, self).__init__(CACHES_DIR / p, *a, **kw)
    )


def test_cache_set_one_get_one():
    cache = CleanCache("test.db")
    item = CacheItem(value=b"Hello, Alice!")
    cache.set_one("key", item)
    assert cache.get_one("key") == item


def test_cache_set_many_get_many(cache: Cache):
    cache = CleanCache("test.db")
    items = {
        "key1": CacheItem(value=b"Hello, Alice!"),
        "key2": CacheItem(value=b"Hello, Bob!"),
    }
    cache.set_many(items)
    assert cache.get_many(items.keys()) == items


def test_least_recently_used_eviction_policy():
    cache = CleanCache("test.db", size_limit=7, eviction_policy="least-recently-used")

    item_1 = CacheItem(value=b"123")
    cache.set_one("key1", item_1)

    item_2 = CacheItem(value=b"456")
    cache.set_one("key2", item_2)

    # ensure there's a small gap between the accesses
    time.sleep(0.1)

    # access key1 to make it the most recently used
    assert cache.get_one("key1") == item_1

    # add a new item that should evict key2
    item_3 = CacheItem(value=b"789")
    cache.set_one("key3", item_3)

    assert cache.get_one("key1") == item_1
    assert cache.get_one("key2") is None
    assert cache.get_one("key3") == item_3


def test_least_frequently_use_eviction_policy():
    cache = CleanCache("test.db", size_limit=7, eviction_policy="least-frequently-used")

    item_1 = CacheItem(value=b"123")
    cache.set_one("key1", item_1)

    item_2 = CacheItem(value=b"456")
    cache.set_one("key2", item_2)

    # access key1 to make it the most frequently used
    assert cache.get_one("key1") == item_1

    # add a new item that should evict key2
    item_3 = CacheItem(value=b"789")
    cache.set_one("key3", item_3)

    assert cache.get_one("key1") == item_1
    assert cache.get_one("key2") is None
    assert cache.get_one("key3") == item_3


def test_item_larger_than_size_limit_not_stored():
    cache = CleanCache("test.db", size_limit=3)

    item = CacheItem(value=b"12345")
    cache.set_one("key", item)
    assert cache.get_one("key") is None


def test_items_totalling_larger_than_size_limit_are_evicted():
    cache = CleanCache("test.db", size_limit=5)

    items = {
        "key1": CacheItem(value=b"123"),
        "key2": CacheItem(value=b"456"),
        "key3": CacheItem(value=b"789"),
    }
    cache.set_many(items)
    assert len(cache.get_many(items.keys())) == 1


def test_exires_at():
    cache = CleanCache("test.db")

    now = datetime.now(UTC)
    item1 = CacheItem(value=b"123", expires_at=now)
    cache.set_one("key1", item1)

    time.sleep(0.1)

    # no evictions until next set call
    item2 = CacheItem(value=b"456")
    cache.set_one("key2", item2)

    # cache should have cleaned up key1 after the set call
    assert cache.get_one("key1") is None

    assert cache.get_one("key2") == item2


def test_performance_adding_items_scaling():
    """The goal of this test is to ensure that adding items doesn't have scalability issues."""
    cache = CleanCache("test.db")
    item = CacheItem(value=b"")

    # measure time of single set_one call
    old_start = time.time()
    cache.set_one("key0", item)
    old_duration = time.time() - old_start

    # add many items to the cache
    for i in range(1, 2000):
        cache.set_one(f"key{i}", item)

    # measure time of single set_one call again
    new_start = time.time()
    cache.set_one("x", item)
    new_duration = time.time() - new_start

    # check that the time taken for the single set_one call is not significantly larger
    old_duration_with_buffer = old_duration * 2  # allow for some variance
    assert new_duration < old_duration_with_buffer
