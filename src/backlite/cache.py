import sqlite3
from collections.abc import Callable
from collections.abc import Collection
from collections.abc import Iterator
from collections.abc import Mapping
from contextlib import AbstractContextManager
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from backlite import _commands
from backlite import _migrations
from backlite.types import EVICTION_POLICIES
from backlite.types import CacheItem
from backlite.types import EvictionPolicy


class Cache:
    """A key-value store that evicts items based on a given policy."""

    def __init__(
        self,
        path: Path | str,
        *,
        size_limit: int = 1024**3,  # 1 GB
        eviction_policy: EvictionPolicy = "least-recently-used",
        default_expiration: timedelta | None = None,
        mkdir: bool = True,
    ) -> None:
        """Create a new cache.

        Args:
            path:
                The path to the SQLite database file. If the file does not exist, it will be
                created.
            size_limit:
                An approximate limit on the size of the cache. Approximate because the size of the
                cache is calculated based on the length of the stored values in bytes not the size
                of the SQLite file itself.
            eviction_policy:
                The eviction policy to use.
            default_expiration:
                The default expiration time for items in the cache. If not specified, items will
                never expire unless explicitly declared at the time of setting.
            mkdir:
                Whether to create the containing directory if it does not exist.
        """
        if eviction_policy not in EVICTION_POLICIES:
            msg = f"Invalid eviction policy: {eviction_policy!r}"
            raise ValueError(msg)

        path = Path(path)
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)

        sqlite3.connect(path)
        self._connect = _connector(path)
        self._eviction_policy: EvictionPolicy = eviction_policy
        self._size_limit = size_limit
        self._default_expiration = default_expiration

        self._init()

    def _init(self) -> None:
        with self._connect() as conn:
            _migrations.run(conn)
            _commands.evict_cache_items(
                conn,
                size_limit=self._size_limit,
                policy=self._eviction_policy,
            )

    def get_keys(self) -> list[str]:
        """Get the keys in the cache."""
        with self._connect() as conn:
            return _commands.get_cache_keys(conn)

    def get_one(self, key: str) -> CacheItem | None:
        """Get the value for the given key."""
        return self.get_many([key]).get(key)

    def get_many(self, keys: Collection[str] | None = None) -> Mapping[str, CacheItem]:
        """Get the value for the given key."""
        with self._connect() as conn:
            return _commands.get_cache_items(conn, keys)

    def set_one(self, key: str, item: CacheItem) -> None:
        """Set the value for the given key."""
        self.set_many({key: item})

    def set_many(self, items: Mapping[str, CacheItem]) -> None:
        """Set the value for the given key."""
        with self._connect() as cursor:
            items_size = sum(len(item["value"]) for item in items.values())
            # Evict items to make room for the new ones
            _commands.evict_cache_items(
                cursor,
                size_limit=self._size_limit - items_size,
                policy=self._eviction_policy,
            )
            # Then set the new items
            _commands.set_cache_items(cursor, items)
            # If the items are larger than the size limit evict again
            if items_size > self._size_limit:
                _commands.evict_cache_items(
                    cursor,
                    size_limit=self._size_limit,
                    policy=self._eviction_policy,
                )


def _prepare_items(
    items: Mapping[str, CacheItem],
    size_limit: int,
) -> tuple[Mapping[str, CacheItem], int]:
    """Prepare items to be set in the cache.

    Items that are too large are excluded.
    """
    size = 0
    to_set: dict[str, CacheItem] = {}
    for k, i in items.items():
        item_size = len(i["value"])
        if item_size > size_limit:
            continue
        size += item_size
        to_set[k] = i
    return to_set, size


def _connector(path: Path) -> Callable[[], AbstractContextManager[sqlite3.Connection]]:
    @contextmanager
    def connect() -> Iterator[sqlite3.Connection]:
        with sqlite3.connect(path) as conn:
            yield conn

    return connect
