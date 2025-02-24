import sqlite3
import sys
from collections.abc import Callable

from backlite import _metadata

CURRENT_SCHEMA_VERSION = 1


def run(conn: sqlite3.Connection) -> None:
    """Migrate the database to the latest version."""
    schema_version = (
        _metadata.schema_version.get(conn) if _metadata.schema_version.exists(conn) else 0
    )

    if schema_version >= CURRENT_SCHEMA_VERSION:
        _truncate_if_py_version_changed(conn)
        return

    for i in range(schema_version, CURRENT_SCHEMA_VERSION):
        UPGRADES[i](conn)

    _metadata.py_version.set(conn, sys.version_info[:3])
    _metadata.schema_version.set(conn, CURRENT_SCHEMA_VERSION)


def _truncate_if_py_version_changed(conn: sqlite3.Connection) -> None:
    if sys.version_info[:3] != _metadata.py_version.get(conn):
        conn.execute("DELETE FROM cache")
        conn.execute("DELETE FROM metadata")
        _metadata.py_version.set(conn, sys.version_info[:3])


UPGRADES: list[Callable[[sqlite3.Connection], None]] = []


@UPGRADES.append
def v1(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value BLOB NOT NULL,
            accessed_at REAL NOT NULL DEFAULT (unixepoch('subsec')),
            accessed_count INTEGER NOT NULL DEFAULT 0,
            expires_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
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
