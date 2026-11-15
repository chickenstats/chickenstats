from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandera.errors
import requests

if TYPE_CHECKING:
    from pathlib import Path

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
    "NetworkError",
    "SchemaValidationError",
    "SaveFormatError",
    "NHLUnavailableError",
    "PlayerDownloadError",
    "APIDownloadError",
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


class InvalidInputError(ChickenstatsError, ValueError):
    """Raised when an unsupported input type or value is provided.

    It is also a `ValueError`, so `except ValueError` still catches it.
    """

    def __init__(self, message: str, obj: object = None, object_type: str | None = None):
        """Store the offending object and its expected type label alongside the error message."""
        super().__init__(message)
        self.obj = obj
        self.object_type = object_type


class InvalidGameIDError(InvalidInputError):
    """Raised when an invalid game ID is provided."""

    def __init__(self, message: str, game_id: object = None):
        """Store the offending game ID alongside the error message."""
        super().__init__(message, obj=game_id, object_type="game ID")
        self.game_id = game_id


class NetworkError(ChickenstatsError, requests.HTTPError):
    """Raised when the NHL or another site answers a request with an error status.

    It is also a `requests.HTTPError`, so `except requests.HTTPError` still catches it,
    and it keeps the failed `response` and `request`.
    """


def _raise_for_status(response: requests.Response) -> None:
    """Raise NetworkError for an error status, as `response.raise_for_status()` would raise HTTPError."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise NetworkError(*exc.args, response=exc.response, request=exc.request) from exc


class SchemaValidationError(ChickenstatsError, pandera.errors.SchemaError):
    """Raised when a DataFrame fails its pandera schema.

    It is also a `pandera.errors.SchemaError`, so `except pandera.errors.SchemaError`
    still catches it, and it keeps pandera's `schema`, `data`, `failure_cases`, `check`,
    `reason_code` and `column_name`.
    """

    def __init__(self, message: str, schema: Any = None, data: Any = None, **details: Any):
        """Store pandera's details of the failure alongside the error message."""
        super().__init__(schema, data, message, **details)

    @classmethod
    def _from_pandera(cls, exc: pandera.errors.SchemaError) -> SchemaValidationError:
        """Copy a pandera SchemaError's message and details."""
        error = cls(str(exc))
        error.__dict__.update(exc.__dict__)
        return error


class SaveFormatError(ChickenstatsError):
    """Raised when Scraper.load() finds data saved in a format this version of chickenstats cannot read."""

    def __init__(self, message: str, path: str | Path | None = None):
        """Store the save directory alongside the error message."""
        super().__init__(message)
        self.path = path


class NHLUnavailableError(ChickenstatsError):
    """Raised when several games in a row fail with network errors, as when the NHL's servers are down."""

    def __init__(self, message: str, game_ids: list[int] | None = None):
        """Store the game IDs that failed in a row alongside the error message."""
        super().__init__(message)
        self.game_ids = game_ids or []


class PlayerDownloadError(ChickenstatsError):
    """Raised when one or more players' landing pages could not be downloaded."""

    def __init__(self, message: str, player_ids: list[int]):
        """Store the IDs of the players that could not be downloaded alongside the error message."""
        super().__init__(message)
        self.player_ids = player_ids


class APIDownloadError(ChickenstatsError):
    """Raised when a page of a chickenstats API download still fails after its retries."""

    def __init__(self, message: str, offset: int, status: int | None = None):
        """Instantiates the error with the offset of the failed page and its HTTP status, if there was one."""
        super().__init__(message)
        self.offset = offset
        self.status = status


class AuthError(ChickenstatsError):
    """Raised when the chickenstats API has no login to use, or rejects the one it is given."""
