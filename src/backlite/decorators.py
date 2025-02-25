import pickle
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Coroutine
from contextlib import AbstractAsyncContextManager
from contextlib import AbstractContextManager
from datetime import timedelta
from functools import wraps
from inspect import Signature
from inspect import signature
from typing import Any
from typing import ParamSpec
from typing import TypeAlias
from typing import TypeVar

from anyio.to_thread import run_sync
from paramorator import paramorator

from backlite.cache import Cache

P = ParamSpec("P")
R = TypeVar("R")
AsyncCallable: TypeAlias = Callable[P, Awaitable[R]]
CoroCallable: TypeAlias = Callable[P, Coroutine[None, None, R]]


@paramorator
def cached(
    func: Callable[P, R],
    *,
    storage: Cache,
    expiration: timedelta | None = None,
    barrier: AbstractContextManager | None = None,
) -> Callable[P, R]:
    """Decorate a function to cache its result."""
    sig = signature(func)

    def _run(key: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> R:
        if (item := storage.get_one(key)) is not None:
            value = pickle.loads(item["value"])
        else:
            value = func(*args, **kwargs)
            storage.set_one(key, {"value": pickle.dumps(value), "expiration": expiration})
        return value

    if barrier:

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = _param_hash_func(sig, args, kwargs)
            if (item := storage.get_one(key)) is not None:
                return pickle.loads(item["value"])
            else:
                with barrier:
                    return _run(key, args, kwargs)

    else:

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = _param_hash_func(sig, args, kwargs)
            return _run(key, args, kwargs)

    return wraps(func)(wrapper)


@paramorator
def async_cached(
    func: AsyncCallable[P, R],
    storage: Cache,
    *,
    expiration: timedelta | None = None,
    barrier: AbstractContextManager | AbstractAsyncContextManager | None = None,
) -> CoroCallable[P, R]:
    """Decorate an async function to cache its result."""
    sig = signature(func)

    async def _run(key: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> R:
        if (item := storage.get_one(key)) is not None:
            value = pickle.loads(item["value"])
        else:
            value = await func(*args, **kwargs)
            storage.set_one(key, {"value": pickle.dumps(value), "expiration": expiration})
        return value

    if barrier:
        async_barrier = (
            barrier
            if isinstance(barrier, AbstractAsyncContextManager)
            else _AsyncContextWrapper(barrier)
        )

        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = _param_hash_func(sig, args, kwargs)
            if (item := storage.get_one(key)) is not None:
                return pickle.loads(item["value"])
            else:
                async with async_barrier:
                    return await _run(key, args, kwargs)
    else:

        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = _param_hash_func(sig, args, kwargs)
            return await _run(key, args, kwargs)

    return wrapper


class _AsyncContextWrapper:
    def __init__(self, ctx: AbstractContextManager) -> None:
        self.ctx = ctx

    async def __aenter__(self) -> None:
        return await run_sync(self.ctx.__enter__)

    async def __aexit__(self, *args: Any) -> bool | None:
        return await run_sync(self.ctx.__exit__, *args)


def _param_hash_func(_: Signature, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    return str(hash((args, frozenset(kwargs.items()))))
