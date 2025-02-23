import sqlite3
import sys
from collections.abc import Callable

from backlite import _commands

CURRENT_VERSION = 1

LIB_VERSION_META_KEY = "lib_version"
PY_VERSION_META_KEY = "py_version"
TOTAL_VALUE_SIZE_META_KEY = "total_value_size"


def run(conn: sqlite3.Connection) -> None:
    """Migrate the database to the latest version."""
    lib_version = _commands.get_metadata(conn, LIB_VERSION_META_KEY) or 0

    if lib_version >= CURRENT_VERSION:
        _truncate_if_py_version_changed(conn)
        return

    for i in range(lib_version, CURRENT_VERSION):
        UPGRADES[i](conn)

    _commands.set_metadata(conn, "lib_version", CURRENT_VERSION)


def _truncate_if_py_version_changed(conn: sqlite3.Connection) -> None:
    if sys.version_info != _commands.get_metadata(conn, PY_VERSION_META_KEY):
        conn.execute("DELETE FROM cache")
        conn.execute("DELETE FROM metadata")
        conn.execute("VACUUM")
        _commands.set_metadata(conn, PY_VERSION_META_KEY, sys.version_info)


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
