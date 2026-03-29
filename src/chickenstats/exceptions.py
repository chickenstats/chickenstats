from __future__ import annotations

__all__ = [
    "ChickenstatsError",
    "InvalidSeasonError",
    "InvalidGameIDError",
    "InvalidTeamError",
    "UnsupportedBackendError",
    "DataMismatchError",
    "InvalidInputError",
]


class ChickenstatsError(Exception):
    """Base exception for chickenstats."""


class InvalidSeasonError(ChickenstatsError):
    """Raised when an unsupported season year is provided."""


class InvalidGameIDError(ChickenstatsError):
    """Raised when an invalid game ID is provided."""


class InvalidTeamError(ChickenstatsError):
    """Raised when an invalid team code or name is provided."""


class UnsupportedBackendError(ChickenstatsError):
    """Raised when an unsupported backend is specified."""


class DataMismatchError(ChickenstatsError):
    """Raised when input data files do not match."""


class InvalidInputError(ChickenstatsError):
    """Raised when an unsupported input type or value is provided."""
