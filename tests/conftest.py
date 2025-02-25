import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from backlite import Storage

CACHES_DIR = Path(__file__).parent / "caches"


@pytest.fixture(autouse=True)
def clean_caches_dir() -> Iterator[Path]:
    CACHES_DIR.mkdir(parents=True, exist_ok=True)
    yield CACHES_DIR
    shutil.rmtree(CACHES_DIR, ignore_errors=True)


class CleanCache(Storage):
    __init__ = (
        Storage.__init__
        if TYPE_CHECKING
        else lambda self, p, *a, **kw: super(CleanCache, self).__init__(CACHES_DIR / p, *a, **kw)
    )
