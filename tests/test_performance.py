import time

from backlite.types import CacheItem
from tests.conftest import CleanCache


def test_adding_items_scaling():
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
