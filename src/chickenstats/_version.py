"""The installed version of chickenstats, read once for everything that reports it."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("chickenstats")
except PackageNotFoundError:
    __version__ = "unknown"
