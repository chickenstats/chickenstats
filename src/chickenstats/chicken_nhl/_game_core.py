from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING, Literal

import polars as pl
import pytz

from chickenstats.exceptions import InvalidGameIDError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.utilities import ChickenSession, _to_backend
from chickenstats.chicken_nhl._game_utils import prefetch_concurrent, _get_score_adjustments


class _GameBase:
    """Type-checker stub — declares all cross-mixin attributes available on the Game object.

    Only populated under TYPE_CHECKING so there is zero runtime overhead.
    All game mixins inherit from this class so the ty type checker can resolve cross-mixin attribute references.
    """

    if TYPE_CHECKING:
        # Core metadata (provided by _GameCore.__init__)
        season: int
        session: str
        game_id: int
        home_team: dict
        away_team: dict
        game_date: str
        api_response: dict | None
        html_rosters_endpoint: str
        home_shifts_endpoint: str
        away_shifts_endpoint: str
        html_events_endpoint: str
        _requests_session: ChickenSession

        # Score-adjustment state (from _GameCore.__init__)
        _score_adjustments: dict

        # Cached properties — each defined in its respective mixin
        api_response: dict | None
        api_rosters: list
        api_events: list
        html_rosters: list
        html_events: list
        rosters: list
        changes: list
        shifts: list

        # Methods called across mixin boundaries
        def _fetch_api_data(self) -> None: ...
        def _fetch_html_events(self) -> list: ...
        def _fetch_html_rosters(self) -> list: ...
        def _fetch_shifts(self) -> list: ...
        def _finalize_dataframe(self, data: list, schema: pl.Schema) -> pl.DataFrame: ...


class _GameCore(_GameBase):
    def __init__(
        self,
        game_id: str | int | float,
        requests_session: ChickenSession | None = None,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
    ):
        """Instantiate a Game object for a given NHL game ID.

        Parameters:
            game_id: 10-digit NHL game ID, e.g., ``2019020684``. Accepts int, str, or float.
            requests_session: Optional shared ``ChickenSession`` for connection pooling when
                scraping multiple games. A new session is created if not provided.
            backend: DataFrame library to use for ``_df`` properties. One of ``"polars"``
                (default), ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.

        Raises:
            InvalidGameIDError: If ``game_id`` is not a 10-digit integer string.

        Examples:
            >>> from chickenstats.chicken_nhl import Game
            >>> game = Game(2019020684)
            >>> game.play_by_play

            Use a different DataFrame backend
            >>> game = Game(2019020684, backend="pandas")
            >>> game.play_by_play_df  # pandas DataFrame
        """
        if str(game_id).isdigit() is False or len(str(game_id)) != 10:
            raise InvalidGameIDError(f"{game_id!r} is not a valid game ID")

        self._backend: str = backend

        self.game_id: int = int(game_id)

        # Season derived from the first four digits of the game ID (the start year)
        year = int(str(self.game_id)[0:4])
        self.season: int = int(f"{year}{year + 1}")

        # Digits 5-6 of the game ID encode the session type:
        #   01 = PR (preseason), 02 = R (regular season), 03 = P (playoffs),
        #   19 = FO (Four Nations Faceoff, international mid-season competition, 2024-25+)
        game_sessions = {"01": "PR", "02": "R", "03": "P", "19": "FO"}
        game_session: str = str(self.game_id)[4:6]
        self.session: str = game_sessions[game_session]

        # Digits 5-10 form the HTML report ID used to construct nhl.com report URLs
        self.html_id: str = str(game_id)[4:]

        # NHL API endpoints (play-by-play is primary; landing is used as a fallback)
        self.api_endpoint: str = f"https://api-web.nhle.com/v1/gamecenter/{self.game_id}/play-by-play"
        self.api_endpoint_other: str = f"https://api-web.nhle.com/v1/gamecenter/{self.game_id}/landing"

        # NHL HTML report endpoints
        self.html_rosters_endpoint: str = f"https://www.nhl.com/scores/htmlreports/{self.season}/RO{self.html_id}.HTM"
        self.home_shifts_endpoint: str = f"https://www.nhl.com/scores/htmlreports/{self.season}/TH{self.html_id}.HTM"
        self.away_shifts_endpoint: str = f"https://www.nhl.com/scores/htmlreports/{self.season}/TV{self.html_id}.HTM"
        self.html_events_endpoint: str = f"https://www.nhl.com/scores/htmlreports/{self.season}/PL{self.html_id}.HTM"

        self._requests_session: ChickenSession = requests_session or ChickenSession()

        self.api_response: dict | None = None
        self.away_team: dict = {}
        self.home_team: dict = {}
        self.venue: str = ""
        self.game_date: str = ""
        self.start_time_et: str = ""
        self.tv_broadcasts: dict = {}
        self.game_state: str = ""
        self.game_schedule_state: str = ""
        self.time_remaining: str = ""
        self.seconds_remaining: str = ""
        self.running: bool = False
        self.in_intermission: bool = False
        self.current_period: int = 0
        self.current_period_type: str = ""

        self._score_adjustments = _get_score_adjustments()

        self._xg_fields = {}

        # Raw fetch caches — populated by prefetch() or lazily on first access
        self._raw_html_events: list | None = None
        self._raw_html_rosters: list | None = None
        self._raw_shifts: list | None = None

    def __repr__(self) -> str:
        """Return a string representation of the Game object."""
        return f"Game(game_id={self.game_id}, season={self.season}, session={self.session!r})"

    def _fetch_api_data(self) -> None:
        """Fetch the NHL API play-by-play response and populate game metadata.

        Idempotent — returns immediately if ``self.api_response`` is already populated,
        so it is safe to call multiple times (e.g., from different mixins or prefetch).

        Populates: ``api_response``, ``away_team``, ``home_team``, ``venue``,
        ``game_date``, ``start_time_et``, ``tv_broadcasts``, ``game_state``,
        ``game_schedule_state``, ``time_remaining``, ``seconds_remaining``,
        ``running``, ``in_intermission``, ``current_period``, ``current_period_type``.
        """
        if self.api_response is not None:
            return

        response: dict = self._requests_session.get(self.api_endpoint).json()
        self.api_response = response

        # Away team information
        away_team: dict = response["awayTeam"]
        if away_team["abbrev"] == "PHX":
            away_team["abbrev"] = "ARI"
        self.away_team = {
            "id": away_team["id"],
            "name": away_team["commonName"]["default"].upper(),
            "abbrev": away_team["abbrev"],
            "logo": away_team["logo"],
        }

        # Home team information
        home_team: dict = response["homeTeam"]
        if home_team["abbrev"] == "PHX":
            home_team["abbrev"] = "ARI"
        self.home_team = {
            "id": home_team["id"],
            "name": home_team["commonName"]["default"].upper(),
            "abbrev": home_team["abbrev"],
            "logo": home_team["logo"],
        }

        # Venue and Time information
        self.venue = response["venue"]["default"].upper()

        est = pytz.timezone("US/Eastern")
        utc = pytz.timezone("UTC")

        start_time_str = response["startTimeUTC"]
        if "Z" in start_time_str:
            start_time_str = start_time_str[:-1] + "+00:00"

        self._start_time_utc_dt = dt.fromisoformat(start_time_str).astimezone(utc)
        self._start_time_et_dt = self._start_time_utc_dt.astimezone(est)

        self.game_date = self._start_time_et_dt.strftime("%Y-%m-%d")
        self.start_time_et = self._start_time_et_dt.strftime("%H:%M")

        # Broadcast and State information
        self.tv_broadcasts = {x["id"]: {k: v for k, v in x.items() if k != "id"} for x in response["tvBroadcasts"]}
        self.game_state = response["gameState"]
        self.game_schedule_state = response["gameScheduleState"]

        # Clock information
        clock = response["clock"]
        self.time_remaining = clock.get("timeRemaining")
        self.seconds_remaining = clock.get("secondsRemaining")
        self.running = clock["running"]
        self.in_intermission = clock["inIntermission"]

        if response["gameState"] != "FUT":
            self.current_period = response["periodDescriptor"]["number"]
            self.current_period_type = response["periodDescriptor"]["periodType"]

    def prefetch(self) -> None:
        """Pre-fetch all raw network data in parallel to warm the cache.

        Calling this before accessing any property runs all independent network requests
        concurrently, so subsequent property accesses (api_events, html_events, shifts, etc.)
        use pre-cached results rather than triggering sequential lazy fetches.

        Examples:
            >>> from chickenstats.chicken_nhl import Game
            >>> game = Game(2023020001)
            >>> game.prefetch()  # all network I/O runs in parallel
            >>> game.play_by_play  # returns immediately from cache
        """
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_events, self._fetch_html_rosters, self._fetch_shifts)
        _ = self.api_events
        _ = self.api_rosters
        _ = self.html_events
        _ = self.html_rosters
        _ = self.shifts

    def _finalize_dataframe(self, data: list, schema: pl.Schema) -> pl.DataFrame:
        """Build a typed Polars DataFrame from ``data`` and convert it to the requested backend.

        Parameters:
            data: List of dicts produced by a scrape pipeline (e.g., ``play_by_play``).
            schema: Polars schema that enforces column names and dtypes, defined in
                ``validation_polars.py``.

        Returns:
            DataFrame in the backend specified at instantiation (polars, pandas, pyarrow,
            or narwhals).
        """
        df = pl.from_dicts(data=data, schema=schema)
        return _to_backend(df, self._backend)
