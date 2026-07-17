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

    def __init__(self, message: str, season: int | str | None = None):
        """Store the offending season value alongside the error message."""
        super().__init__(message)
        self.season = season


class InvalidGameIDError(ChickenstatsError):
    """Raised when an invalid game ID is provided."""

    def __init__(self, message: str, game_id: int | str | float | None = None):
        """Store the offending game ID alongside the error message."""
        super().__init__(message)
        self.game_id = game_id


class InvalidTeamError(ChickenstatsError):
    """Raised when an invalid team code or name is provided."""

    def __init__(self, message: str, team_code: str | None = None, team_name: str | None = None):
        """Store the offending team code/name alongside the error message."""
        super().__init__(message)
        self.team_code = team_code
        self.team_name = team_name


class UnsupportedBackendError(ChickenstatsError):
    """Raised when an unsupported backend is specified."""


class DataMismatchError(ChickenstatsError):
    """Raised when input data fails a consistency check.

    Covers both mismatched EvolvingHockey CSV exports (e.g. play-by-play and
    shifts files with different row counts) and internal chicken_nhl
    play-by-play merge/state-tracking/xG-calculation failures for a specific
    game.
    """

    def __init__(self, message: str, game_id: int | str | float | None = None):
        """Store the affected game ID (if any) alongside the error message."""
        super().__init__(message)
        self.game_id = game_id


class InvalidInputError(ChickenstatsError):
    """Raised when an unsupported input type or value is provided."""

    def __init__(self, message: str, obj: object = None, object_type: str | None = None):
        """Store the offending object and its expected type label alongside the error message."""
        super().__init__(message)
        self.obj = obj
        self.object_type = object_type
