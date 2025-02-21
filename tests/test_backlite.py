import shutil
import time
from functools import partial
from pathlib import Path

import pytest

from backlite import Cache
from backlite.types import CacheItem

CACHES_DIR = Path(__file__).parent / "caches"


@pytest.fixture(autouse=True)
def clean_caches():
    yield
    shutil.rmtree(CACHES_DIR, ignore_errors=True)


make_test_cache = partial(Cache, directory=CACHES_DIR)


def test_cache_set_one_get_one(cache: Cache):
    cache = make_test_cache()

    item = CacheItem(value=b"Hello, Alice!")
    cache.set_one("key", item)
    assert cache.get_one("key") == item


def test_cache_set_many_get_many(cache: Cache):
    cache = make_test_cache()

    items = {
        "key1": CacheItem(value=b"Hello, Alice!"),
        "key2": CacheItem(value=b"Hello, Bob!"),
    }
    cache.set_many(items)
    assert cache.get_many(items.keys()) == items


def test_least_recently_used_eviction_policy():
    cache = make_test_cache(approximate_size_limit=7, eviction_policy="least-recently-used")

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
    cache = make_test_cache(approximate_size_limit=7, eviction_policy="least-frequently-used")

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
