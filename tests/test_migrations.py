import sqlite3
import sys
from pathlib import Path

from backlite import _commands as commands
from backlite import _metadata as metadata
from backlite import _migrations as migrations
from backlite.types import CacheItem


def test_truncate_on_py_version_change(clean_caches_dir: Path):
    with sqlite3.connect(clean_caches_dir / "test.db") as conn:
        migrations.run(conn)

        items = {"key": CacheItem(value=b"Hello, World!")}
        commands.set_cache_items(conn, items)
        assert commands.get_cache_items(conn, ["key"]) == items

        assert metadata.py_version.get(conn) == sys.version_info[:3]
        # Simulate a Python version change
        metadata.py_version.set(conn, (3, 8, 0))

        migrations.run(conn)
        assert metadata.py_version.get(conn) == sys.version_info[:3]
        assert commands.get_cache_items(conn, ["key"]) == {}
