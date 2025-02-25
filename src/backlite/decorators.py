import pickle
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Coroutine
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
) -> Callable[P, R]:
    """Decorate a function to cache its result."""
    sig = signature(func)

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        key = _param_hash_func(sig, args, kwargs)
        if (item := storage.get_one(key)) is not None:
            value = pickle.loads(item["value"])
        else:
            value = func(*args, **kwargs)
            storage.set_one(key, {"value": pickle.dumps(value), "expiration": expiration})
        return value

    return wrapper


@paramorator
def async_cached(
    func: AsyncCallable[P, R],
    storage: Cache,
    *,
    expiration: timedelta | None = None,
) -> CoroCallable[P, R]:
    """Decorate an async function to cache its result."""
    sig = signature(func)

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        key = _param_hash_func(sig, args, kwargs)
        if (item := storage.get_one(key)) is not None:
            value = pickle.loads(item["value"])
        else:
            value = await func(*args, **kwargs)
            storage.set_one(key, {"value": pickle.dumps(value), "expiration": expiration})
        return value

    return wrapper


def _param_hash_func(_: Signature, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    return str(hash((args, frozenset(kwargs.items()))))
