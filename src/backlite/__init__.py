from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from backlite.cache import Cache

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # nocov
    __version__ = "0.0.0"

__all__ = ("Cache",)
