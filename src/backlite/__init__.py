from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from backlite.decorators import async_cached
from backlite.decorators import cached
from backlite.storage import Storage
from backlite.types import EVICTION_POLICIES
from backlite.types import CacheItem
from backlite.types import EvictionPolicy
from backlite.types import ParamHashFunc

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"

__all__ = (
    "EVICTION_POLICIES",
    "CacheItem",
    "EvictionPolicy",
    "ParamHashFunc",
    "Storage",
    "async_cached",
    "cached",
)
