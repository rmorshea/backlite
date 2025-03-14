import time
from datetime import timedelta

from backlite.storage import Storage
from backlite.types import CacheItem
from tests.conftest import CleanCache


def short_sleep():
    time.sleep(0.01)


def test_cache_set_one_get_one():
    cache = CleanCache("test.db")
    item = CacheItem(value=b"Hello, Alice!")
    cache.set_one("key", item)
    assert cache.get_one("key") == item


def test_cache_set_many_get_many(cache: Storage):
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
    short_sleep()

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


def test_most_recently_used_eviction_policy():
    cache = CleanCache("test.db", size_limit=7, eviction_policy="most-recently-used")

    item_1 = CacheItem(value=b"123")
    cache.set_one("key1", item_1)

    item_2 = CacheItem(value=b"456")
    cache.set_one("key2", item_2)

    # access key1 to make it the most recently used
    assert cache.get_one("key1") == item_1

    # add a new item that should evict key1
    item_3 = CacheItem(value=b"789")
    cache.set_one("key3", item_3)

    assert cache.get_one("key1") is None
    assert cache.get_one("key2") == item_2
    assert cache.get_one("key3") == item_3


def test_first_in_first_out_eviction_policy():
    cache = CleanCache("test.db", size_limit=7, eviction_policy="first-in-first-out")

    item_1 = CacheItem(value=b"123")
    cache.set_one("key1", item_1)

    short_sleep()

    item_2 = CacheItem(value=b"456")
    cache.set_one("key2", item_2)

    # add a new item that should evict key1
    item_3 = CacheItem(value=b"789")
    cache.set_one("key3", item_3)

    assert cache.get_one("key1") is None
    assert cache.get_one("key2") == item_2
    assert cache.get_one("key3") == item_3


def test_last_in_first_out_eviction_policy():
    cache = CleanCache("test.db", size_limit=7, eviction_policy="last-in-first-out")

    item_1 = CacheItem(value=b"123")
    cache.set_one("key1", item_1)

    short_sleep()

    item_2 = CacheItem(value=b"456")
    cache.set_one("key2", item_2)

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

    item1 = CacheItem(value=b"123", expiration=timedelta(seconds=0))
    cache.set_one("key1", item1)

    short_sleep()

    # no evictions until next set call
    item2 = CacheItem(value=b"456")
    cache.set_one("key2", item2)

    # cache should have cleaned up key1 after the set call
    assert cache.get_one("key1") is None

    assert cache.get_one("key2") == item2


def test_get_all_items():
    cache = CleanCache("test.db")

    items = {
        "key1": CacheItem(value=b"Hello, Alice!"),
        "key2": CacheItem(value=b"Hello, Bob!"),
    }
    cache.set_many(items)

    assert cache.get_many() == items


def test_get_keys():
    cache = CleanCache("test.db")
    items = {
        "key1": CacheItem(value=b"Hello, Alice!"),
        "key2": CacheItem(value=b"Hello, Bob!"),
    }
    cache.set_many(items)

    assert cache.get_keys() == set(items.keys())
    assert cache.get_keys(["key1"]) == {"key1"}
    assert cache.get_keys(["not_in_cache"]) == set()
    assert cache.get_keys([]) == set()
