import sqlite3
from collections.abc import Callable

from backlite import _commands

CURRENT_VERSION = 1


def run(conn: sqlite3.Connection) -> None:
    """Try to migrate the database to the latest version and return whether it was successful."""
    version = _commands.get_metadata(conn, "version") or 0

    if version >= CURRENT_VERSION:
        return

    for i in range(version, CURRENT_VERSION):
        UPGRADES[i](conn)

    _commands.set_metadata(conn, "version", CURRENT_VERSION)


UPGRADES: list[Callable[[sqlite3.Connection], None]] = []


@UPGRADES.append
def v1(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value BLOB NOT NULL,
            accessed_at REAL NOT NULL DEFAULT (unixepoch('subsec')),
            access_count INTEGER NOT NULL DEFAULT 0,
            expires_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value JSON NOT NULL
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO metadata (key, value)
        VALUES ('total_value_size', 0)
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS total_value_size_on_insert
        AFTER INSERT ON cache
        BEGIN
            UPDATE metadata
            SET value = value + LENGTH(NEW.value)
            WHERE key = 'total_value_size';
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS total_value_size_on_delete
        AFTER DELETE ON cache
        BEGIN
            UPDATE metadata
            SET value = value - LENGTH(OLD.value)
            WHERE key = 'total_value_size';
        END
    """)
