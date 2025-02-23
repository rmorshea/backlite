import pickle
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Coroutine
from contextlib import AbstractAsyncContextManager
from contextlib import AbstractContextManager
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from functools import wraps
from inspect import Signature
from inspect import signature
from typing import Any
from typing import ParamSpec
from typing import TypeAlias
from typing import TypeVar

from paramorator import paramorator

from backlite.cache import Cache
from backlite.types import ParamHashFunc

P = ParamSpec("P")
R = TypeVar("R")
AsyncCallable: TypeAlias = Callable[P, Awaitable[R]]
CoroCallable: TypeAlias = Callable[P, Coroutine[None, None, R]]


def _default_param_hash_func(_: Signature, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    return str(hash((args, frozenset(kwargs.items()))))


@paramorator
def cached(
    func: Callable[P, R],
    cache: Cache,
    *,
    expire_after: timedelta | None,
    param_hash_func: ParamHashFunc = _default_param_hash_func,
) -> Callable[P, R]:
    """Decorate a function to cache its result."""
    sig = signature(func)

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        key = param_hash_func(sig, args, kwargs)
        if (item := cache.get_one(key)) is not None:
            value = pickle.loads(item["value"])
        else:
            value = func(*args, **kwargs)
            cache.set_one(
                key,
                {
                    "value": pickle.dumps(value),
                    "expires_at": datetime.now(UTC) + expire_after if expire_after else None,
                },
            )
        return value

    return wrapper


@paramorator
def barrier(func: Callable[P, R], lock: AbstractContextManager) -> Callable[P, R]:
    """Decorate a function to acquire a lock before executing it."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with lock:
            return func(*args, **kwargs)

    return wrapper


@paramorator
def async_cached(
    func: AsyncCallable[P, R],
    cache: Cache,
    *,
    expire_after: timedelta | None,
    param_hash_func: ParamHashFunc = _default_param_hash_func,
) -> CoroCallable[P, R]:
    """Decorate an async function to cache its result."""
    sig = signature(func)

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        key = param_hash_func(sig, args, kwargs)
        if (item := cache.get_one(key)) is not None:
            value = pickle.loads(item["value"])
        else:
            value = await func(*args, **kwargs)
            cache.set_one(
                key,
                {
                    "value": pickle.dumps(value),
                    "expires_at": datetime.now(UTC) + expire_after if expire_after else None,
                },
            )
        return value

    return wrapper


@paramorator
def async_barrier(
    func: AsyncCallable[P, R], lock: AbstractAsyncContextManager
) -> CoroCallable[P, R]:
    """Decorate an async function to acquire a lock before executing it."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        async with lock:
            return await func(*args, **kwargs)

    return wrapper
