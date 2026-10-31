from __future__ import annotations

import functools
import logging
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NamedTuple

import polars as pl
from pydantic import ValidationError
from requests.exceptions import RequestException

if TYPE_CHECKING:
    import pandas as pd

from chickenstats.chicken_nhl._game_core import FINAL_STATE
from chickenstats.chicken_nhl.game import Game
from chickenstats.exceptions import (
    ChickenstatsError,
    InvalidGameIDError,
    GameNotStartedError,
    InvalidInputError,
    NHLUnavailableError,
    ReportUnavailableError,
)
from chickenstats.chicken_nhl.validation_polars import (
    api_events_polars_schema,
    api_rosters_polars_schema,
    changes_polars_schema,
    html_events_polars_schema,
    html_rosters_polars_schema,
    pbp_polars_schema,
    pbp_ext_polars_schema,
    rosters_polars_schema,
    shifts_polars_schema,
    xg_polars_schema,
)
from chickenstats.utilities.enums import Backend, LinesLevels, StatsLevels, StintsLevels, TeamStatsLevels
from chickenstats.utilities.types import DataFrameT
from chickenstats.utilities.utilities import ChickenProgress, ChickenSession, _to_backend, convert_to_list


class _ScrapeSpec(NamedTuple):
    """Metadata for one raw scrape-data type; one entry per type in `_SCRAPE_REGISTRY`."""

    list_attr: str
    """Scraper attribute holding this type's frames as ``dict[int, pl.DataFrame]``, one per game scraped.

    A game whose scrape returned no rows is stored as an empty frame, so a game is stored once it is a key.
    """
    schema: dict
    """Polars schema for ``pl.from_dicts(..., schema=...)``."""
    pbar_label: str | None = None
    """Progress-bar label. ``None`` for ``play_by_play_ext``/``xg_fields``, produced only
    as a byproduct of a ``"play_by_play"`` scrape."""


# Every type a scrape can be asked for; play_by_play_ext and xg_fields come only with play_by_play
ScrapeType = Literal[
    "api_events", "api_rosters", "changes", "html_events", "html_rosters", "play_by_play", "shifts", "rosters"
]

_SCRAPE_REGISTRY: dict[str, _ScrapeSpec] = {
    "api_events": _ScrapeSpec("_api_events", api_events_polars_schema, "API events"),
    "api_rosters": _ScrapeSpec("_api_rosters", api_rosters_polars_schema, "API rosters"),
    "changes": _ScrapeSpec("_changes", changes_polars_schema, "changes"),
    "html_events": _ScrapeSpec("_html_events", html_events_polars_schema, "HTML events"),
    "html_rosters": _ScrapeSpec("_html_rosters", html_rosters_polars_schema, "HTML rosters"),
    "rosters": _ScrapeSpec("_rosters", rosters_polars_schema, "rosters"),
    "shifts": _ScrapeSpec("_shifts", shifts_polars_schema, "shifts"),
    "play_by_play": _ScrapeSpec("_play_by_play", pbp_polars_schema, "play-by-play data"),
    "play_by_play_ext": _ScrapeSpec("_play_by_play_ext", pbp_ext_polars_schema),
    "xg_fields": _ScrapeSpec("_xg_fields", xg_polars_schema),
}

# Pre-seedable leaf types, used by _seed_game_from_cache. Excludes the terminal
# play_by_play/play_by_play_ext/xg_fields outputs, which nothing else derives from.
_TERMINAL_KEYS = frozenset({"play_by_play", "play_by_play_ext", "xg_fields"})
_LEAF_ATTRS: dict[str, str] = {
    key: spec.list_attr for key, spec in _SCRAPE_REGISTRY.items() if key not in _TERMINAL_KEYS
}

logger = logging.getLogger(__name__)

# Network failures in a row before a scrape stops
MAX_NETWORK_FAILURES = 5


def _user_stacklevel() -> int:
    """The stacklevel, for a warning raised by the caller, of the first frame outside chickenstats.

    The Scraper warns from several calls deep, through properties and prep_* methods, so a fixed stacklevel
    points into the package for some of them. cached_property's frame in functools sits between a property and
    its caller, so it is skipped too.
    """
    skipped = (str(Path(__file__).resolve().parents[1]), functools.__file__)
    frame = sys._getframe(1)
    level = 1
    while frame is not None and frame.f_code.co_filename.startswith(skipped):
        frame = frame.f_back
        level += 1
    return level


def _is_network_failure(exc: BaseException) -> bool:
    """Whether a game failed because a request failed, rather than because of its data."""
    if isinstance(exc, RequestException):
        return True
    return isinstance(exc, ReportUnavailableError) and all(
        reason.startswith("request failed") for reason in exc.reports.values()
    )


# Keys of a scrape result that describe the game rather than hold one of its data types
_RESULT_META_KEYS = frozenset({"game_id", "game_state"})


def normalize_game_ids(game_ids: list[str | float | int] | pd.Series | str | float | int) -> list[int]:
    """Return the game IDs as a new list of ints, in order, each once."""
    normalized = []
    for value in convert_to_list(game_ids, "game ID"):
        try:
            number = float(value.strip()) if isinstance(value, str) else value
            game_id = int(number)
        except (TypeError, ValueError):
            raise InvalidGameIDError(f"Game ID {value!r} is not a whole number", game_id=value) from None

        if game_id != number:
            raise InvalidGameIDError(f"Game ID {value!r} is not a whole number", game_id=value)

        if game_id not in normalized:
            normalized.append(game_id)

    return normalized


class _ScraperBase:
    """Type-checker stub — declares all cross-mixin attributes available on the Scraper object.

    Only populated under TYPE_CHECKING so there is zero runtime overhead.
    All scraper mixins inherit from this class so ty can resolve cross-mixin attribute references.
    """

    if TYPE_CHECKING:
        # Core state (from _ScraperCore.__init__)
        game_ids: list
        _backend: str
        disable_progress_bar: bool
        transient_progress_bar: bool

        # Raw data caches (from _ScraperCore)
        _api_events: dict[int, pl.DataFrame]
        _api_rosters: dict[int, pl.DataFrame]
        _html_events: dict[int, pl.DataFrame]
        _html_rosters: dict[int, pl.DataFrame]
        _rosters: dict[int, pl.DataFrame]
        _shifts: dict[int, pl.DataFrame]
        _changes: dict[int, pl.DataFrame]
        _play_by_play: dict[int, pl.DataFrame]
        _play_by_play_ext: dict[int, pl.DataFrame]
        _xg_fields: dict[int, pl.DataFrame]
        _bad_games: list
        _failed_types: dict[int, set[str]]
        _failure_reasons: dict[int, str]
        _not_started: list[int]
        _game_states: dict[int, str]
        _final_types: dict[int, set[str]]
        _stale: set[int]

        # Aggregated stat frames (from _ScraperCore)
        _ind_stats: pl.DataFrame
        _oi_stats: pl.DataFrame
        _stats: pl.DataFrame
        _lines: pl.DataFrame
        _team_stats: pl.DataFrame
        _stints: pl.DataFrame
        _stats_levels: StatsLevels
        _lines_levels: LinesLevels
        _team_stats_levels: TeamStatsLevels
        _stints_levels: StintsLevels

        # Cached properties from _ScraperRawMixin
        play_by_play: pl.DataFrame
        play_by_play_ext: pl.DataFrame
        xg_fields: pl.DataFrame

        # Methods used across mixin boundaries
        def __init__(
            self,
            game_ids: list[str | float | int] | pd.Series | str | float | int,
            disable_progress_bar: bool = False,
            transient_progress_bar: bool = False,
            backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
            requests_session: ChickenSession | None = None,
        ) -> None: ...
        def _is_empty(self, df: pl.DataFrame) -> bool: ...
        def save(self, path: str | Path | None = None) -> Path: ...
        def _scrape(self, *scrape_types: ScrapeType, only: list[int] | None = None) -> None: ...
        def _finalize_dataframe(self, data: dict[int, pl.DataFrame], schema: object) -> DataFrameT: ...
        def _concat_stored(self, data: dict[int, pl.DataFrame], schema: object) -> pl.DataFrame: ...
        def _play_by_play_snapshot(self) -> tuple[pl.DataFrame, pl.DataFrame]: ...
        def _clear_results(self) -> None: ...

        def _fetched_final(self, game_id: int) -> bool: ...


class _ScraperCore(_ScraperBase):
    def __init__(
        self,
        game_ids: list[str | float | int] | pd.Series | str | float | int,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
        requests_session: ChickenSession | None = None,
    ):
        """Instantiate a Scraper for one or more game IDs.

        Parameters:
            game_ids (list[str | float | int] | pd.Series | str | float | int):
                One or more 10-digit NHL game identifiers, e.g., ``2023020001`` or
                ``[2023020001, 2023020002]``. Strings and floats holding a whole number
                are converted to int, and each game is kept once, in order.
            disable_progress_bar (bool):
                Suppress the Rich progress bar globally for this instance. Individual
                method calls accept a ``disable_progress_bar`` argument to override this
                on a per-call basis. Default ``False``.
            transient_progress_bar (bool):
                Clear the progress bar from the terminal after it completes rather than
                leaving it visible. Can be overridden per-call. Default ``False``.
            backend (str):
                DataFrame backend for all returned data. One of ``"polars"`` (default),
                ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.
            requests_session (ChickenSession | None):
                ChickenSession to use for requests, e.g., with a custom user agent. Defaults to a new ChickenSession.

        Raises:
            InvalidGameIDError: If a game ID is not a whole number.
        """
        self._backend: str = backend

        self.disable_progress_bar: bool = disable_progress_bar
        self.transient_progress_bar: bool = transient_progress_bar

        self.game_ids: list[int] = normalize_game_ids(game_ids)

        # Failure and game-state tracking
        self._bad_games: list = []
        self._failed_types: dict[int, set[str]] = {}
        self._failure_reasons: dict[int, str] = {}
        self._not_started: list[int] = []
        self._game_states: dict[int, str] = {}
        self._final_types: dict[int, set[str]] = {}
        self._stale: set[int] = set()

        self._requests_session: ChickenSession = requests_session or ChickenSession()

        # Each raw type's frames, keyed by game ID
        for spec in _SCRAPE_REGISTRY.values():
            setattr(self, spec.list_attr, {})

        dataframe = pl.DataFrame()

        self._ind_stats: pl.DataFrame = dataframe
        self._oi_stats: pl.DataFrame = dataframe
        self._zones: pl.DataFrame | pd.DataFrame = dataframe
        self._stats: pl.DataFrame = dataframe
        self._stats_levels: StatsLevels = StatsLevels()

        self._lines: pl.DataFrame = dataframe
        self._lines_levels: LinesLevels = LinesLevels()

        self._team_stats: pl.DataFrame = dataframe
        self._team_stats_levels: TeamStatsLevels = TeamStatsLevels()

        self._stints: pl.DataFrame = dataframe
        self._stints_levels: StintsLevels = StintsLevels()

    def __repr__(self) -> str:
        """Return a string representation of the Scraper object."""
        base = f"Scraper(game_ids={self.game_ids!r}, backend={self._backend!r})"
        if self._bad_games:
            return f"Scraper(game_ids={self.game_ids!r}, backend={self._backend!r}, failed_games={self._bad_games!r})"
        return base

    def __len__(self) -> int:
        """Return the number of game IDs tracked by this Scraper."""
        return len(self.game_ids)

    @property
    def failed_games(self) -> list:
        """Game IDs that failed to scrape, each once, in the order they first failed.

        A game stays listed until every data type that failed for it has been scraped.
        """
        return list(self._bad_games)

    @property
    def failure_reasons(self) -> dict[int, str]:
        """Why each game in :attr:`failed_games` last failed, as the error's class and message.

        Examples:
            >>> scraper = Scraper([2023020001])
            >>> pbp = scraper.play_by_play
            >>> scraper.failure_reasons
            {2023020001: 'ReportUnavailableError: Game 2023020001: the PL (HTTP 404) report could not be read ...'}
        """
        return dict(self._failure_reasons)

    @property
    def not_started_games(self) -> list[int]:
        """Game IDs that had not started when they were last scraped, in the order they were found.

        They are not in :attr:`failed_games`, and the next scrape fetches them again.

        Examples:
            >>> scraper = Scraper([2025021001])
            >>> pbp = scraper.play_by_play
            >>> scraper.not_started_games
            [2025021001]
        """
        return list(self._not_started)

    @property
    def game_states(self) -> dict[int, str]:
        """Each scraped game's NHL API state when it was last fetched, such as ``"LIVE"``, ``"FINAL"`` or ``"OFF"``.

        A game that has not been scraped, or failed every scrape, is not listed.

        Examples:
            >>> scraper = Scraper([2025020601, 2025020602])
            >>> pbp = scraper.play_by_play
            >>> scraper.game_states
            {2025020601: 'LIVE', 2025020602: 'OFF'}
        """
        return dict(self._game_states)

    @property
    def provisional_games(self) -> list[int]:
        """Scraped game IDs whose data can still change, in ``game_ids`` order.

        A game is final once every type stored for it was fetched when the game was ``"OFF"``. Until then
        :meth:`refresh` and the next scrape of any type fetch it again.

        Examples:
            >>> scraper = Scraper([2025020601, 2025020602])
            >>> pbp = scraper.play_by_play
            >>> scraper.provisional_games
            [2025020601]
        """
        stored = set()
        for spec in _SCRAPE_REGISTRY.values():
            stored.update(getattr(self, spec.list_attr))

        return [game_id for game_id in self.game_ids if game_id in stored and not self._fetched_final(game_id)]

    def _record_failure(self, game_id: int, scrape_type: str) -> None:
        """Note that scrape_type failed for game_id."""
        self._failed_types.setdefault(game_id, set()).add(scrape_type)
        if game_id not in self._bad_games:
            self._bad_games.append(game_id)

    def _record_success(self, game_id: int, scraped_types: set[str]) -> None:
        """Clear the types a successful scrape covered, and the game once none of its failures are left."""
        failed = self._failed_types.get(game_id)
        if failed is None:
            return
        failed -= scraped_types
        if not failed:
            del self._failed_types[game_id]
            self._failure_reasons.pop(game_id, None)
            self._bad_games.remove(game_id)

    def _is_empty(self, df) -> bool:
        """Return True if df has no rows."""
        return df.is_empty()

    def _is_final(self, game_id: int) -> bool:
        """Whether game_id's stored data was fetched once the game was final, so it is not fetched again."""
        return game_id not in self._stale and self._fetched_final(game_id)

    def _fetched_final(self, game_id: int) -> bool:
        """Whether every type stored for game_id was fetched at FINAL_STATE, whether or not refresh() is running."""
        stored = {key for key, spec in _SCRAPE_REGISTRY.items() if game_id in getattr(self, spec.list_attr)}
        return self._game_states.get(game_id) == FINAL_STATE and stored <= self._final_types.get(game_id, set())

    def _seed_game_from_cache(self, game: Game, game_id: int) -> None:
        """Write already-scraped/cached data for game_id into game.__dict__ to skip re-fetching.

        Only a final game is seeded: a game still provisional is fetched whole, so its types match.
        """
        if not self._is_final(game_id):
            return
        for prop, list_attr in _LEAF_ATTRS.items():
            frame = getattr(self, list_attr).get(game_id)
            if frame is not None and not frame.is_empty():
                game.__dict__[prop] = frame.to_dicts()

    def _scrape_single_game(self, game_id: int, scrape_types: tuple[ScrapeType, ...]) -> dict | Exception:
        """Fetch the data for scrape_types for a single game, from one Game.

        Returns a dict with ``game_id`` and every raw type the Game built, the by-products of the requested
        types included, or the exception that failed the game (the caller records it in ``self._bad_games``).
        ``"play_by_play"`` also returns play_by_play_ext and xg_fields.
        """
        try:
            game = Game(game_id, self._requests_session)
            self._seed_game_from_cache(game, game_id)

            for scrape_type in scrape_types:
                match scrape_type:
                    case "api_events":
                        # api_events and api_rosters share the same HTTP call
                        _ = game.api_events, game.api_rosters
                    case "api_rosters":
                        _ = game.api_rosters
                    case "html_events":
                        _ = game.html_events
                    case "html_rosters":
                        _ = game.html_rosters
                    case "rosters":
                        _ = game.rosters
                    case "shifts" | "changes":
                        _ = game.shifts, game.changes
                    case "play_by_play":
                        _ = game.play_by_play, game.api_events, game.html_events, game.rosters

            # Every raw type the Game built is returned
            result: dict = {"game_id": game_id}
            result.update({key: game.__dict__[key] for key in _LEAF_ATTRS if key in game.__dict__})
            if "play_by_play" in scrape_types:
                result.update(
                    play_by_play=game.play_by_play, play_by_play_ext=game.play_by_play_ext, xg_fields=game.xg_fields
                )

            if self._is_final(game_id):
                result["game_state"] = FINAL_STATE
            else:
                game._fetch_api_data()
                result["game_state"] = game.game_state
            return result

        except GameNotStartedError as exc:
            logger.info("Game %s has not started (state %s)", game_id, exc.game_state)
            return exc
        except (ChickenstatsError, RequestException, ValidationError) as exc:
            # Expected per-game failures: data-quality issues, network errors, bad payloads.
            logger.warning("Failed to scrape game %s: %s: %s", game_id, type(exc).__name__, exc)
            logger.debug("Traceback for game %s", game_id, exc_info=True)
            return exc
        except Exception as exc:  # noqa: BLE001
            # Unexpected error — likely a real bug; log louder but don't crash the batch.
            logger.error("Unexpected error scraping game %s", game_id, exc_info=True)
            return exc

    def _game_frames(self, game_id: int, result: dict) -> dict[str, pl.DataFrame] | None:
        """Build one game's frames from a scrape result, or return None if any of them cannot be built.

        A play-by-play scrape returns every raw type for the game, so a type already stored for a final game is
        left out. A game that was still provisional has every type replaced, so its types match.
        """
        final = self._is_final(game_id)
        try:
            frames = {}
            for key, value in result.items():
                if key in _RESULT_META_KEYS or (final and game_id in getattr(self, _SCRAPE_REGISTRY[key].list_attr)):
                    continue
                schema = _SCRAPE_REGISTRY[key].schema
                frames[key] = pl.from_dicts(value, schema=schema) if value else pl.DataFrame(schema=schema)
            return frames
        except Exception:  # noqa: BLE001
            logger.error("Unexpected error building the frames for game %s", game_id, exc_info=True)
            return None

    def _scrape(self, *scrape_types: ScrapeType, only: list[int] | None = None) -> None:
        """Scrape only the data needed for scrape_types for unscraped game IDs, or for the games in only.

        Each game is fetched through one Game for every type. A final game already stored for every type in
        scrape_types is not fetched again.

        Examples:
            First, instantiate the Scraper object
            >>> game_ids = list(range(2023020001, 2023020011))
            >>> scraper = Scraper(game_ids)

            You can use the _scrape method to get any data
            >>> scraper._scrape("html_events")
            >>> scraper._html_events  # Returns data as a list
            >>> scraper.html_events  # Returns data as a DataFrame
        """
        pbar_stubs = {key: spec.pbar_label for key, spec in _SCRAPE_REGISTRY.items() if spec.pbar_label is not None}

        # A game not yet final is fetched again
        stored = [getattr(self, _SCRAPE_REGISTRY[scrape_type].list_attr) for scrape_type in scrape_types]
        unscraped = [
            x
            for x in (self.game_ids if only is None else only)
            if any(x not in frames for frames in stored) or not self._is_final(x)
        ]

        if not unscraped:
            return

        failed_now: list[int] = []
        not_started_now: list[int] = []
        network_failures: list[int] = []

        # Not wrapped in `with self._requests_session:` — the session is shared for the
        # Scraper's whole lifetime, not just this call.
        with ChickenProgress(disable=self.disable_progress_bar, transient=self.transient_progress_bar) as progress:
            pbar_stub = ", ".join(pbar_stubs[scrape_type] for scrape_type in scrape_types)
            game_task = progress.add_task(f"Downloading {pbar_stub} for {unscraped[0]}...", total=len(unscraped))

            for idx, game_id in enumerate(unscraped):
                result = self._scrape_single_game(game_id, scrape_types)
                frames = None if isinstance(result, Exception) else self._game_frames(game_id, result)

                if frames is not None and not isinstance(result, Exception):
                    if any(game_id in getattr(self, _SCRAPE_REGISTRY[key].list_attr) for key in frames):
                        self._clear_results()
                    # Stored for every type it returned, or for none
                    for key, frame in frames.items():
                        getattr(self, _SCRAPE_REGISTRY[key].list_attr)[game_id] = frame
                    self._game_states[game_id] = result["game_state"]
                    # Not final until fetched at OFF
                    final_types = self._final_types.setdefault(game_id, set())
                    if result["game_state"] == FINAL_STATE:
                        final_types.update(frames)
                    else:
                        final_types.difference_update(frames)
                    self._record_success(game_id, set(scrape_types).union(result) - _RESULT_META_KEYS)
                    if game_id in self._not_started:
                        self._not_started.remove(game_id)
                elif isinstance(result, GameNotStartedError):
                    if game_id not in self._not_started:
                        self._not_started.append(game_id)
                    not_started_now.append(game_id)
                else:
                    for scrape_type in scrape_types:
                        self._record_failure(game_id, scrape_type)
                    if isinstance(result, Exception):
                        self._failure_reasons[game_id] = f"{type(result).__name__}: {result}"
                    else:
                        self._failure_reasons[game_id] = "its data could not be built into frames"
                    failed_now.append(game_id)

                if isinstance(result, Exception) and _is_network_failure(result):
                    network_failures.append(game_id)
                else:
                    network_failures = []

                if len(network_failures) >= MAX_NETWORK_FAILURES:
                    raise NHLUnavailableError(
                        f"The last {len(network_failures)} games failed with network errors: {network_failures}. "
                        "The NHL may be unavailable; every game scraped so far is kept, and calling again, or "
                        "refresh(), fetches the rest.",
                        game_ids=network_failures,
                    )

                if idx + 1 < len(unscraped):
                    next_message = f"Downloading {pbar_stub} for {unscraped[idx + 1]}..."
                else:
                    next_message = f"Finished downloading {pbar_stub}"

                progress.update(game_task, description=next_message, advance=1, refresh=True)

        if failed_now:
            warnings.warn(
                f"Failed to scrape {len(failed_now)} game(s): {failed_now}. "
                "Access scraper.failed_games for the full list and scraper.failure_reasons for why.",
                UserWarning,
                stacklevel=_user_stacklevel(),
            )
        if not_started_now:
            warnings.warn(
                f"{len(not_started_now)} game(s) have not started: {not_started_now}. Call scraper.refresh() "
                "once they start; access scraper.not_started_games for the full list.",
                UserWarning,
                stacklevel=_user_stacklevel(),
            )

    def _finalize_dataframe(self, data: dict[int, pl.DataFrame], schema) -> DataFrameT:
        """Concatenate one type's frames in ``game_ids`` order and return them in the configured backend format.

        Parameters:
            data (dict[int, pl.DataFrame]):
                Frames for one data type, keyed by game ID. Games not in ``game_ids`` are left out, and
                no frames return an empty frame with the given schema.
            schema:
                Polars schema used to initialize an empty DataFrame when ``data`` is
                empty, ensuring callers always receive a consistently-typed result.

        Returns:
            DataFrameT:
                All rows concatenated and converted to the backend selected at
                Scraper instantiation (``"polars"``, ``"pandas"``, ``"pyarrow"``,
                or ``"narwhals"``).
        """
        return _to_backend(self._concat_stored(data, schema), self._backend)

    def _concat_stored(self, data: dict[int, pl.DataFrame], schema) -> pl.DataFrame:
        """Concatenate one type's stored frames in ``game_ids`` order, as polars."""
        frames = [data[game_id] for game_id in self.game_ids if game_id in data]
        return pl.concat(frames) if frames else pl.DataFrame(schema=schema)

    def add_games(self, game_ids: list[int | str | float] | int) -> None:
        """Add games to the Scraper.

        Parameters:
            game_ids (list or int or float or str):
                List-like object of or single 10-digit game identifier, e.g., 2023020001

        Examples:
            Instantiate Scraper
            >>> game_ids = list(range(2023020001, 2023020011))
            >>> scraper = Scraper(game_ids)

            Scrape something
            >>> scraper.play_by_play

            Add games
            >>> scraper.add_games(2023020011)

            Scrape some more
            >>> scraper.play_by_play


        """
        existing = set(self.game_ids)
        new_ids = [x for x in normalize_game_ids(game_ids) if x not in existing]

        self.game_ids.extend(new_ids)

        self._clear_results()

    def _clear_results(self) -> None:
        """Clear every returned frame, raw and aggregated, so each is rebuilt on its next access."""
        for prop in _SCRAPE_REGISTRY:
            self.__dict__.pop(prop, None)

        empty = pl.DataFrame()
        self._ind_stats = empty
        self._oi_stats = empty
        self._stats = empty
        self._lines = empty
        self._team_stats = empty
        self._stints = empty

    def refresh(self, game_ids: list[int | str | float] | int | None = None) -> None:
        """Fetch games again and replace their rows.

        A game is fetched again for each data type the Scraper holds or failed to get for it; when play-by-play is
        among them, one play-by-play scrape replaces them all. A game's rows are replaced only when its new scrape
        succeeds: a game that fails again keeps its earlier rows and is listed in ``failed_games``. Every returned
        frame is rebuilt on its next access.

        Parameters:
            game_ids (list or int or float or str or None):
                Games to fetch again, which must already be in the Scraper. Default ``None`` fetches every game
                that is not final, that is, every game the API has not yet reported as ``OFF``, failed games
                included.

        Raises:
            InvalidInputError: If a game ID is not in the Scraper.

        Examples:
            Scrape tonight's games while they are in progress
            >>> scraper = Scraper([2025020601, 2025020602])
            >>> pbp = scraper.play_by_play

            Later, fetch the games that were not final yet
            >>> scraper.refresh()
            >>> pbp = scraper.play_by_play
        """
        if game_ids is None:
            targets = [game_id for game_id in self.game_ids if not self._is_final(game_id)]
        else:
            targets = normalize_game_ids(game_ids)
            unknown = [game_id for game_id in targets if game_id not in self.game_ids]
            if unknown:
                raise InvalidInputError(
                    f"Games {unknown} are not in this Scraper; add them with add_games()", obj=unknown
                )

        held = set()
        for game_id in targets:
            held |= self._failed_types.get(game_id, set())
            for key, spec in _SCRAPE_REGISTRY.items():
                if game_id in getattr(self, spec.list_attr):
                    held.add(key)

        # play_by_play_ext and xg_fields come only from a play-by-play scrape
        if held & _TERMINAL_KEYS:
            scrape_types = ["play_by_play"]
        else:
            scrape_types = [key for key in _SCRAPE_REGISTRY if key in held]

        self._stale.update(targets)
        try:
            # One Game per game, so each report is requested once
            self._scrape(*scrape_types, only=targets)  # ty: ignore[invalid-argument-type]
        finally:
            self._stale.difference_update(targets)

        self._clear_results()
