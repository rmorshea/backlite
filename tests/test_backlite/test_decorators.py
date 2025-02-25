import asyncio
import time
from threading import Lock
from threading import Thread

from backlite import async_cached
from backlite import cached
from tests.conftest import CleanCache


def test_cached_function():
    cache = CleanCache("test.db")

    call_count = 0

    @cached(storage=cache)
    def expensive_function(_: int) -> None:
        nonlocal call_count
        call_count += 1

    expensive_function(1)
    assert call_count == 1
    expensive_function(1)
    assert call_count == 1
    expensive_function(2)
    assert call_count == 2


def test_cached_function_with_barrier():
    cache = CleanCache("test.db")
    lock = Lock()
    lock.acquire()

    call_count = 0

    @cached(storage=cache, barrier=lock)
    def expensive_function(_: int) -> None:
        nonlocal call_count
        call_count += 1

    thread = Thread(target=expensive_function, args=(1,))
    thread.start()

    time.sleep(0.1)
    assert call_count == 0

    lock.release()
    thread.join()


async def test_async_cached_function():
    cache = CleanCache("test.db")

    call_count = 0

    @async_cached(storage=cache)
    async def expensive_function(_: int) -> None:
        nonlocal call_count
        call_count += 1

    await expensive_function(1)
    assert call_count == 1
    await expensive_function(1)
    assert call_count == 1
    await expensive_function(2)
    assert call_count == 2


async def test_async_cached_function_with_barrier():
    cache = CleanCache("test.db")
    lock = Lock()
    lock.acquire()

    call_count = 0

    @async_cached(storage=cache, barrier=lock)
    async def expensive_function(_: int) -> None:
        nonlocal call_count
        call_count += 1

    thread = Thread(target=asyncio.run, args=(expensive_function(1),))
    thread.start()

    await asyncio.sleep(0.1)
    assert call_count == 0

    lock.release()
    thread.join()
