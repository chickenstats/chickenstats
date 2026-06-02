from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Literal

import narwhals as nw
import polars as pl

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

from chickenstats.chicken_nhl.game import Game
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
from chickenstats.utilities.enums import Backend, LinesLevels, StatsLevels, TeamStatsLevels
from chickenstats.utilities.utilities import ChickenProgress, ChickenSession, _to_backend, convert_to_list

# Map result keys to their polars schemas for incremental DataFrame conversion
_SCRAPE_SCHEMAS: dict[str, dict] = {
    "api_events": api_events_polars_schema,
    "api_rosters": api_rosters_polars_schema,
    "changes": changes_polars_schema,
    "html_events": html_events_polars_schema,
    "html_rosters": html_rosters_polars_schema,
    "rosters": rosters_polars_schema,
    "shifts": shifts_polars_schema,
    "play_by_play": pbp_polars_schema,
    "play_by_play_ext": pbp_ext_polars_schema,
    "xg_fields": xg_polars_schema,
}

logger = logging.getLogger(__name__)


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
        _api_events: list[pl.DataFrame]
        _api_rosters: list[pl.DataFrame]
        _html_events: list[pl.DataFrame]
        _html_rosters: list[pl.DataFrame]
        _rosters: list[pl.DataFrame]
        _shifts: list[pl.DataFrame]
        _changes: list[pl.DataFrame]
        _play_by_play: list[pl.DataFrame]
        _play_by_play_ext: list[pl.DataFrame]
        _xg_fields: list[pl.DataFrame]
        _scraped_play_by_play: set[int]

        # Aggregated stat frames (from _ScraperCore)
        _ind_stats: pl.DataFrame
        _oi_stats: pl.DataFrame
        _stats: pl.DataFrame
        _lines: pl.DataFrame
        _team_stats: pl.DataFrame
        _stats_levels: StatsLevels
        _lines_levels: LinesLevels
        _team_stats_levels: TeamStatsLevels

        # Cached properties from _ScraperRawMixin
        play_by_play: pl.DataFrame
        play_by_play_ext: pl.DataFrame
        xg_fields: pl.DataFrame

        # Methods used across mixin boundaries
        def _is_empty(self, df: pl.DataFrame) -> bool: ...
        def _scrape(
            self,
            scrape_type: Literal[
                "api_events",
                "api_rosters",
                "changes",
                "html_events",
                "html_rosters",
                "play_by_play",
                "shifts",
                "rosters",
            ],
        ) -> None: ...
        def _finalize_dataframe(
            self, data: list[pl.DataFrame], schema: object
        ) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame: ...


class _ScraperCore(_ScraperBase):
    def __init__(
        self,
        game_ids: list[str | float | int] | pd.Series | str | float | int,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
    ):
        """Instantiate a Scraper for one or more game IDs.

        Parameters:
            game_ids (list[str | float | int] | pd.Series | str | float | int):
                One or more 10-digit NHL game identifiers, e.g., ``2023020001`` or
                ``[2023020001, 2023020002]``. Strings and floats are coerced to int.
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
        """
        game_ids = convert_to_list(game_ids, "game ID")

        self._backend: str = backend

        self.disable_progress_bar: bool = disable_progress_bar
        self.transient_progress_bar: bool = transient_progress_bar

        self.game_ids: list = game_ids
        self._bad_games: list = []

        self._requests_session: ChickenSession = ChickenSession()

        self._api_events: list[pl.DataFrame] = []
        self._scraped_api_events: set[int] = set()

        self._api_rosters: list[pl.DataFrame] = []
        self._scraped_api_rosters: set[int] = set()

        self._changes: list[pl.DataFrame] = []
        self._scraped_changes: set[int] = set()

        self._html_events: list[pl.DataFrame] = []
        self._scraped_html_events: set[int] = set()

        self._html_rosters: list[pl.DataFrame] = []
        self._scraped_html_rosters: set[int] = set()

        self._rosters: list[pl.DataFrame] = []
        self._scraped_rosters: set[int] = set()

        self._shifts: list[pl.DataFrame] = []
        self._scraped_shifts: set[int] = set()

        self._play_by_play: list[pl.DataFrame] = []
        self._play_by_play_ext: list[pl.DataFrame] = []
        self._xg_fields: list[pl.DataFrame] = []
        self._scraped_play_by_play: set[int] = set()

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
        """Game IDs that failed to scrape."""
        return self._bad_games

    def _is_empty(self, df) -> bool:
        """Return True if df has no rows."""
        return df.is_empty()

    def _scrape_single_game(
        self,
        game_id: int,
        scrape_type: Literal[
            "api_events", "api_rosters", "changes", "html_events", "html_rosters", "play_by_play", "shifts", "rosters"
        ],
    ) -> dict | None:
        """Fetch only the data required for scrape_type for a single game.

        Returns a dict with ``game_id`` and the relevant data keys, or ``None`` on
        failure (the game ID is appended to ``self._bad_games`` by the caller).

        Note:
            The ``"play_by_play"`` scrape type is a superset fetch: in addition to
            ``play_by_play`` and ``play_by_play_ext`` it also returns all raw component
            data (``api_events``, ``api_rosters``, ``html_events``, ``html_rosters``,
            ``rosters``, ``shifts``, ``changes``), so a single ``play_by_play`` scrape
            populates every raw-data cache at once.
        """
        try:
            game = Game(game_id, self._requests_session)

            match scrape_type:
                case "api_events":
                    # api_events and api_rosters share the same HTTP call
                    return {"game_id": game_id, "api_events": game.api_events, "api_rosters": game.api_rosters}
                case "api_rosters":
                    return {"game_id": game_id, "api_rosters": game.api_rosters}
                case "html_events":
                    return {"game_id": game_id, "html_events": game.html_events}
                case "html_rosters":
                    return {"game_id": game_id, "html_rosters": game.html_rosters}
                case "rosters":
                    return {"game_id": game_id, "rosters": game.rosters}
                case "shifts":
                    return {"game_id": game_id, "shifts": game.shifts, "changes": game.changes}
                case "changes":
                    return {"game_id": game_id, "changes": game.changes, "shifts": game.shifts}
                case "play_by_play":
                    return {
                        "game_id": game_id,
                        "play_by_play": game.play_by_play,
                        "play_by_play_ext": game.play_by_play_ext,
                        "xg_fields": game.xg_fields,
                        "api_events": game.api_events,
                        "api_rosters": game.api_rosters,
                        "html_events": game.html_events,
                        "html_rosters": game.html_rosters,
                        "rosters": game.rosters,
                        "shifts": game.shifts,
                        "changes": game.changes,
                    }

        except Exception:  # noqa: BLE001
            logger.warning("Failed to scrape game %s", game_id, exc_info=True)
            return None

    def _scrape(
        self,
        scrape_type: Literal[
            "api_events", "api_rosters", "changes", "html_events", "html_rosters", "play_by_play", "shifts", "rosters"
        ],
    ) -> None:
        """Scrape only the data needed for scrape_type for unscraped game IDs.

        Uses the type-specific _scraped_* list to determine which games still need
        fetching, so previously scraped games are not re-fetched.

        Examples:
            First, instantiate the Scraper object
            >>> game_ids = list(range(2023020001, 2023020011))
            >>> scraper = Scraper(game_ids)

            You can use the _scrape method to get any data
            >>> scraper._scrape("html_events")
            >>> scraper._html_events  # Returns data as a list
            >>> scraper.html_events  # Returns data as a DataFrame
        """
        pbar_stubs = {
            "api_events": "API events",
            "api_rosters": "API rosters",
            "changes": "changes",
            "html_events": "HTML events",
            "html_rosters": "HTML rosters",
            "play_by_play": "play-by-play data",
            "shifts": "shifts",
            "rosters": "rosters",
        }

        # Map each scrape_type to the tracking list that gates re-fetching
        scraped_tracker = {
            "api_events": self._scraped_api_events,
            "api_rosters": self._scraped_api_rosters,
            "changes": self._scraped_changes,
            "html_events": self._scraped_html_events,
            "html_rosters": self._scraped_html_rosters,
            "play_by_play": self._scraped_play_by_play,
            "shifts": self._scraped_shifts,
            "rosters": self._scraped_rosters,
        }

        unscraped = [x for x in self.game_ids if x not in scraped_tracker[scrape_type]]

        if not unscraped:
            return

        # Map result keys to (internal list, scraped tracker list) pairs
        result_targets = {
            "api_events": (self._api_events, self._scraped_api_events),
            "api_rosters": (self._api_rosters, self._scraped_api_rosters),
            "html_events": (self._html_events, self._scraped_html_events),
            "html_rosters": (self._html_rosters, self._scraped_html_rosters),
            "rosters": (self._rosters, self._scraped_rosters),
            "shifts": (self._shifts, self._scraped_shifts),
            "changes": (self._changes, self._scraped_changes),
            "play_by_play": (self._play_by_play, self._scraped_play_by_play),
            "play_by_play_ext": (self._play_by_play_ext, self._scraped_play_by_play),
            "xg_fields": (self._xg_fields, self._scraped_play_by_play),
        }

        prev_failed = set(self._bad_games)

        with self._requests_session:
            with ChickenProgress(disable=self.disable_progress_bar, transient=self.transient_progress_bar) as progress:
                pbar_stub = pbar_stubs[scrape_type]
                game_task = progress.add_task(f"Downloading {pbar_stub} for {unscraped[0]}...", total=len(unscraped))

                for idx, game_id in enumerate(unscraped):
                    result = self._scrape_single_game(game_id, scrape_type)

                    if result is not None:
                        for key, value in result.items():
                            if key == "game_id":
                                continue
                            data_list, scraped_list = result_targets[key]
                            if value:
                                data_list.append(pl.from_dicts(value, schema=_SCRAPE_SCHEMAS[key]))
                            scraped_list.add(game_id)
                    else:
                        self._bad_games.append(game_id)

                    if idx + 1 < len(unscraped):
                        next_message = f"Downloading {pbar_stub} for {unscraped[idx + 1]}..."
                    else:
                        next_message = f"Finished downloading {pbar_stub}"

                    progress.update(game_task, description=next_message, advance=1, refresh=True)

        newly_failed = [g for g in self._bad_games if g not in prev_failed]
        if newly_failed:
            warnings.warn(
                f"Failed to scrape {len(newly_failed)} game(s): {newly_failed}. "
                "Access scraper.failed_games for the full list.",
                UserWarning,
                stacklevel=2,
            )

    def _finalize_dataframe(
        self, data: list[pl.DataFrame], schema
    ) -> pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
        """Concatenate raw data frames and return in the configured backend format.

        Parameters:
            data (list[pl.DataFrame]):
                Frames collected across all scraped games for one data type.
                Empty list returns an empty frame with the given schema.
            schema:
                Polars schema used to initialise an empty DataFrame when ``data`` is
                empty, ensuring callers always receive a consistently-typed result.

        Returns:
            pl.DataFrame | pd.DataFrame | pa.Table | nw.DataFrame:
                All rows concatenated and converted to the backend selected at
                Scraper instantiation (``"polars"``, ``"pandas"``, ``"pyarrow"``,
                or ``"narwhals"``).
        """
        df = pl.concat(data) if data else pl.DataFrame(schema=schema)
        return _to_backend(df, self._backend)

    def add_games(self, game_ids: list[int | str | float] | int) -> None:
        """Method to add games to the Scraper.

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
        existing = set(self.game_ids)  # Not covered by tests
        game_ids = [
            int(x) for x in convert_to_list(game_ids, "game ID") if int(x) not in existing
        ]  # Not covered by tests

        self.game_ids.extend(game_ids)  # Not covered by tests

        for prop in (  # Not covered by tests
            "api_events",
            "api_rosters",
            "changes",
            "html_events",
            "html_rosters",
            "play_by_play",
            "play_by_play_ext",
            "xg_fields",
            "rosters",
            "shifts",
        ):
            self.__dict__.pop(prop, None)  # Not covered by tests
