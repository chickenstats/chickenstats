from __future__ import annotations

__all__ = [
    "ChickenstatsError",
    "InvalidSeasonError",
    "InvalidGameIDError",
    "InvalidTeamError",
    "UnsupportedBackendError",
    "DataMismatchError",
    "GameNotStartedError",
    "ReportUnavailableError",
    "InvalidInputError",
    "CacheFormatError",
    "NHLUnavailableError",
    "AuthError",
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

    For example, EvolvingHockey CSV exports whose play-by-play and shifts files
    do not match, or a season in an unexpected format.
    """

    def __init__(self, message: str, game_id: int | str | float | None = None):
        """Store the affected game ID (if any) alongside the error message."""
        super().__init__(message)
        self.game_id = game_id


class GameNotStartedError(ChickenstatsError):
    """Raised when play-by-play is requested for a game that has not started yet."""

    def __init__(self, message: str, game_id: int | str | float | None = None, game_state: str | None = None):
        """Store the game ID and the API's game state alongside the error message."""
        super().__init__(message)
        self.game_id = game_id
        self.game_state = game_state


class ReportUnavailableError(ChickenstatsError):
    """Raised when one of an official (OFF) game's NHL reports could not be fetched or read."""

    def __init__(self, message: str, game_id: int | str | float | None = None, reports: dict | None = None):
        """Store the game ID and each failed report's reason alongside the error message."""
        super().__init__(message)
        self.game_id = game_id
        self.reports = reports or {}


class InvalidInputError(ChickenstatsError):
    """Raised when an unsupported input type or value is provided."""

    def __init__(self, message: str, obj: object = None, object_type: str | None = None):
        """Store the offending object and its expected type label alongside the error message."""
        super().__init__(message)
        self.obj = obj
        self.object_type = object_type


class CacheFormatError(ChickenstatsError):
    """Raised when a cache directory was written in a format this version of chickenstats cannot read."""

    def __init__(self, message: str, path: object = None):
        """Store the cache directory alongside the error message."""
        super().__init__(message)
        self.path = path


class NHLUnavailableError(ChickenstatsError):
    """Raised when several games in a row fail with network errors, as when the NHL's servers are down."""

    def __init__(self, message: str, game_ids: list[int] | None = None):
        """Store the game IDs that failed in a row alongside the error message."""
        super().__init__(message)
        self.game_ids = game_ids or []


class AuthError(ChickenstatsError):
    """Raised when the chickenstats API has no login to use, or rejects the one it is given."""
