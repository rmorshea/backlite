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


def evict_cache_items(
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

    # Get the current size of the cache
    current_size = get_metadata(conn, "total_value_size") or 0

    # If the current size is already less than the limit, do nothing
    if current_size <= size_limit:
        return

    # Pick the keys to evict based on the policy
    keys_to_evict: list[str] = []
    order_by = _SORT_BY_POLICY[policy]
    for key, size in conn.execute(
        f"SELECT key, LENGTH(value) FROM cache ORDER BY {order_by}"  # noqa: S608
    ).fetchall():
        keys_to_evict.append(key)
        current_size -= size
        if current_size <= size_limit:
            break

    # Evict the items
    conn.execute(
        f"DELETE FROM cache WHERE key IN ({', '.join('?' for _ in keys_to_evict)})",  # noqa: S608
        tuple(keys_to_evict),
    )


_SORT_BY_POLICY: Mapping[EvictionPolicy, str] = {
    "least-recently-used": "accessed_at ASC",
    "least-frequently-used": "access_count ASC",
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
