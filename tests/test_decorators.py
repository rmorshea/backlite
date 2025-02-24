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
