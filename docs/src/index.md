# BackLite

A file-based caching library backed by SQLite

## Installation

```bash
pip install backlite
```

## Decorators

Create a [`Storage`][backlite.storage.Storage] object and use the
[`@cached`][backlite.decorators.cached] decorator to cache the results of a function.

```python
import time

from backlite import Storage
from backlite import cached

storage = Storage("cache.db")


@cached(storage=storage)
def expensive_function(x, y):
    time.sleep(2)  # Simulate an expensive computation
    return x + y


expensive_function(1, 2)  # slow
expensive_function(1, 2)  # fast (cached)
expensive_function(3, 4)  # slow
```

### Barriers

You can use barriers to prevent a function from being called while the result is being cached.

```python
import time
from threading import Lock

from backlite import Storage
from backlite import cached

storage = Storage("cache.db")
lock = Lock()


@cached(storage=storage, barrier=lock)
def expensive_function(x, y):
    time.sleep(2)  # Simulate an expensive computation
    return x + y
```

### Async

You can use the `@async_cached` decorator to cache the results of an async functions.

```python
import asyncio

from backlite import Storage
from backlite import async_cached

storage = Storage("cache.db")


@async_cached(storage=storage)
async def expensive_function(x, y):
    await asyncio.sleep(2)  # Simulate an expensive computation
    return x + y
```

!!! note

    This async decorator supports both sync and async barriers. This can be useful if
    you need to use a file lock (which typically has a sync interface) to prevent
    multiple processes from accessing the same file.

## Options

### Max Size

BackLite will automatically evict the least recently used items when the values in the storage
exceed the max size (1GB by default). You can set the `max_size` when creating the storage object.

```python
from backlite import Storage

cache = Storage("cache.db", max_size=1024**3)
```

!!! note

    The max size is approximate since it's based on the values in the storage, not the
    actual size of the database file itself.

### Eviction Policy

BackLite uses a least recently used (LRU) eviction policy by default. You can change the
[`EvictionPolicy`][backlite.types.EvictionPolicy]
by setting the `eviction_policy` when creating the storage object. Available policies are:

- [`least-recently-used`](<https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_Recently_Used_(LRU)>) (default)
- [`least-frequently-used`](<https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_frequently_used_(LFU)>)
- [`most-recently-used`](<https://en.wikipedia.org/wiki/Cache_replacement_policies#Most-recently-used_(MRU)>)
- [`first-in-first-out`](<https://en.wikipedia.org/wiki/Cache_replacement_policies#First_in_first_out_(FIFO)>)
- [`last-in-first-out`](<https://en.wikipedia.org/wiki/Cache_replacement_policies#Last_in_first_out_(LIFO)>)

```python
from backlite import Storage

cache = Storage("cache.db", eviction_policy="least-frequently-used")
```

## Direct Usage

You can use BackLite storages directly without decorators. This is useful for
more complex use cases. Note that the storage expects you to have serialized
the values you want to store as bytes.

```python
from backlite import Storage

storage = Storage("cache.db")

# Store a value
storage.set("key", {"value": b"value"})

# Retrieve a value
assert storage.get("key") == {"value": b"value"}
```

With direct usage, you can also set an expiration time each item separately:

```python
from datetime import timedelta

from backlite import Storage

storage = Storage("cache.db")

# Store a value with an expiration time
storage.set("key", {"value": b"value", "expiration": timedelta(seconds=60)})
```
