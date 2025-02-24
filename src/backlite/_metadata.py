import json
import sqlite3
from collections.abc import Callable
from typing import Generic
from typing import TypeVar
from typing import cast

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)
T_co = TypeVar("T_co", covariant=True)


class Metadata(Generic[T]):
    """A protocol for a metadata getter."""

    def __init__(self, key: str, dump: Callable[[T], str], load: Callable[[str], T]) -> None:
        self.key = key
        self.dump = dump
        self.load = load

    def get(self, conn: sqlite3.Connection) -> T:
        """Get the metadata value."""
        if row := conn.execute("SELECT value FROM metadata WHERE key = ?", (self.key,)).fetchone():
            return self.load(row[0])
        else:
            msg = f"Metadata key {self.key!r} not found"
            raise ValueError(msg)

    def set(self, conn: sqlite3.Connection, value: T) -> None:
        """Set the metadata value."""
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (self.key, self.dump(value)),
        )

    def exists(self, conn: sqlite3.Connection) -> bool:
        """Check if the metadata key exists."""
        return (
            # check table exists
            conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'",
            ).fetchone()
            is not None
            # check key exists
            and conn.execute("SELECT 1 FROM metadata WHERE key = ?", (self.key,)).fetchone()
            is not None
        )


schema_version = Metadata("schema_version", str, int)
"""The schema version of the database."""

py_version = Metadata(
    "py_version",
    lambda v: json.dumps(v),
    lambda s: cast("tuple[int, int, int]", tuple(json.loads(s))),
)
"""The Python version used to create the database."""


total_value_size = Metadata("total_value_size", str, int)
"""The total size of all values in the cache."""
