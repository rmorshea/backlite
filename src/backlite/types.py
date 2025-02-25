from datetime import timedelta
from inspect import Signature
from typing import Any
from typing import Literal
from typing import Protocol
from typing import Required
from typing import TypedDict
from typing import get_args

EvictionPolicy = Literal[
    "least-recently-used",
    "least-frequently-used",
]
"""Defines the possible eviction policies for the cache."""

EVICTION_POLICIES: set[EvictionPolicy] = set(get_args(EvictionPolicy))
"""A set of all possible eviction policies."""


class CacheItem(TypedDict, total=False):
    """A cache item."""

    value: Required[bytes]
    """The value of the item."""
    expiration: timedelta | None
    """The time until the item expires."""


class ParamHashFunc(Protocol):
    """A function that generates a hash for the given parameters."""

    def __call__(self, sig: Signature, args: tuple[Any, ...], kwargs: dict[str, Any], /) -> str:
        """Generate a hash for the given parameters.

        Args:
            sig: The signature of the function.
            args: The positional arguments of the function.
            kwargs: The keyword arguments of the function.

        Returns:
            A hash for the given parameters.
        """
        ...
