from datetime import datetime
from typing import Literal
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
    expires_at: datetime | None
    """The time at which the item expires."""
