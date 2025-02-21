import sqlite3
from collections.abc import Collection
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import Any

from backlite.types import CacheItem
from backlite.types import EvictionPolicy


def get_cache_items(conn: sqlite3.Connection, keys: Collection[str]) -> Mapping[str, CacheItem]:
    """Get the values for the given keys."""
    cur = conn.execute(
        f"""
        SELECT key, value, expires_at
        FROM cache
        WHERE key IN ({", ".join("?" for _ in keys)})
        """,  # noqa: S608 (ok because values are not user input)
        tuple(keys),
    )
    result = {
        key: CacheItem(value=value, expires_at=datetime.fromtimestamp(expires_at, tz=UTC))
        if expires_at is not None
        else CacheItem(value=value)
        for key, value, expires_at in cur.fetchall()
    }
    conn.execute(
        f"""
        UPDATE cache
        SET accessed_at = unixepoch('subsec'),
            access_count = access_count + 1
        WHERE key IN ({", ".join("?" for _ in keys)})
        """,  # noqa: S608
        tuple(keys),
    )
    return result


def set_cache_items(conn: sqlite3.Connection, items: Mapping[str, CacheItem]) -> None:
    """Update the cache with the given values."""
    conn.executemany(
        """
        INSERT OR REPLACE INTO cache (key, value, expires_at)
        VALUES (?, ?, ?)
        """,
        [
            (
                key,
                value["value"],
                expires_at.timestamp()
                if (expires_at := value.get("expires_at")) is not None
                else None,
            )
            for key, value in items.items()
        ],
    )


def evict_from_cache(
    conn: sqlite3.Connection,
    *,
    size_limit: int,
    policy: EvictionPolicy,
) -> None:
    """Evict items from the cache until the total size is less than the max size."""
    # Cleanup expired items first
    conn.execute(
        "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < unixepoch('subsec')"
    )

    # Pick how to order the cache items when deciding which to evict
    order_by = _SORT_BY_POLICY[policy]

    # Delete items until the total size is less than the max size
    conn.execute(
        # This query performs a cumulative sum of the value lengths and deletes
        # all rows where the cumulative sum exceeds the cache size limit. The rows
        # are ordered such that the least recently used items are deleted first.
        f"""
        WITH cumsum AS (
            SELECT
                key,
                LENGTH(value) AS value_length,
                SUM(LENGTH(value)) OVER (
                    ORDER BY {order_by}
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_value_length
            FROM cache
        )
        DELETE FROM cache
        WHERE key IN (
            SELECT cache.key
            FROM cache
            JOIN cumsum ON cache.KEY = cumsum.KEY
            WHERE cumsum.cumulative_value_length > ?
            ORDER BY CACHE.{order_by}
        )
        """,  # noqa: S608
        (size_limit,),
    )


_SORT_BY_POLICY: Mapping[EvictionPolicy, str] = {
    "least-recently-used": "accessed_at DESC",
    "least-frequently-used": "access_count DESC",
}


def get_metadata(conn: sqlite3.Connection, key: str) -> Any | None:
    """Get the metadata value for the given key."""
    # check if metadata table exists
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'"
    ).fetchone()
    if table_exists is None:
        return None

    row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return row[0]


def set_metadata(conn: sqlite3.Connection, key: str, value: Any) -> None:
    """Set the metadata value for the given key."""
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", (key, value))
