import sqlite3
from collections.abc import Collection
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime

from backlite._metadata import total_value_size
from backlite.types import CacheItem
from backlite.types import EvictionPolicy


def get_cache_keys(conn: sqlite3.Connection, keys: Collection[str] | None) -> set[str]:
    """Get the keys in the cache."""
    if not keys:
        rows = conn.execute("SELECT key FROM cache").fetchall()
    else:
        rows = conn.execute(
            f"SELECT key FROM cache WHERE key IN ({', '.join('?' for _ in keys)})",  # noqa: S608
            tuple(keys),
        ).fetchall()
    return {r[0] for r in rows}


def get_cache_items(
    conn: sqlite3.Connection,
    keys: Collection[str] | None,
) -> Mapping[str, CacheItem]:
    """Get the values for the given keys."""
    if keys is None:
        rows = conn.execute(
            """
            SELECT key, value, expires_at
            FROM cache
            WHERE expires_at IS NULL OR expires_at > unixepoch('subsec')
            """
        ).fetchall()
        keys = [r[0] for r in rows]
    else:
        rows = conn.execute(
            f"""
            SELECT key, value, expires_at
            FROM cache
            WHERE key IN ({", ".join("?" for _ in keys)})
            AND expires_at IS NULL OR expires_at > unixepoch('subsec')
            """,  # noqa: S608 (ok because values are not user input)
            tuple(keys),
        ).fetchall()
    now = datetime.now(tz=UTC)
    result = {
        key: CacheItem(value=value, expiration=datetime.fromtimestamp(expires_at, tz=UTC) - now)
        if expires_at is not None
        else CacheItem(value=value)
        for key, value, expires_at in rows
    }
    conn.execute(
        f"""
        UPDATE cache
        SET accessed_at = unixepoch('subsec'),
            accessed_count = accessed_count + 1
        WHERE key IN ({", ".join("?" for _ in keys)})
        """,  # noqa: S608
        tuple(keys),
    )
    return result


def set_cache_items(conn: sqlite3.Connection, items: Mapping[str, CacheItem]) -> None:
    """Update the cache with the given values."""
    now = datetime.now(tz=UTC)
    conn.executemany(
        """
        INSERT OR REPLACE INTO cache (key, value, expires_at)
        VALUES (?, ?, ?)
        """,
        [
            (
                key,
                value["value"],
                (now + expiration).timestamp()
                if (expiration := value.get("expiration")) is not None
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
    current_size = total_value_size.get(conn)

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
    "least-frequently-used": "accessed_count ASC",
}
