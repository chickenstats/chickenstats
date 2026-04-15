from __future__ import annotations

from datetime import datetime as dt
from typing import TYPE_CHECKING, Literal

import narwhals as nw
import polars as pl
import pytz

from chickenstats.exceptions import InvalidGameIDError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.utilities import ChickenSession, _to_backend
from chickenstats.chicken_nhl._game_utils import _get_model, prefetch_concurrent, _get_score_adjustments

model_version = "0.1.1"


class _GameBase:
    """Type-checker stub — declares all cross-mixin attributes available on the Game object.

    Only populated under TYPE_CHECKING so there is zero runtime overhead.
    All game mixins inherit from this class so ty can resolve cross-mixin attribute references.
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

        # xG models and score-adjustment state (from _GameCore.__init__)
        from xgboost import XGBClassifier

        _sh_model: XGBClassifier
        _pp_model: XGBClassifier
        _es_model: XGBClassifier
        _ef_model: XGBClassifier
        _ea_model: XGBClassifier
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
        def _finalize_dataframe(self, data: list, schema: object) -> pl.DataFrame: ...


class _GameCore(_GameBase):
    def __init__(
        self,
        game_id: str | int | float,
        requests_session: ChickenSession | None = None,
        backend: Backend | Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
    ):
        """Instantiates a Game object for a given game ID.

        If nested, you can provide a requests.Session object to optimize speed.
        """
        if str(game_id).isdigit() is False or len(str(game_id)) != 10:
            raise InvalidGameIDError(f"{game_id!r} is not a valid game ID")

        self._backend: str = backend

        # Game ID
        self.game_id: int = int(game_id)

        # season
        year = int(str(self.game_id)[0:4])
        self.season: int = int(f"{year}{year + 1}")

        # game session
        game_sessions = {"01": "PR", "02": "R", "03": "P", "19": "FO"}
        game_session: str = str(self.game_id)[4:6]
        self.session: str = game_sessions[game_session]

        # HTML game ID
        self.html_id: str = str(game_id)[4:]

        # Live endpoint for many things
        url = f"https://api-web.nhle.com/v1/gamecenter/{self.game_id}/play-by-play"
        self.api_endpoint: str = url

        # Alternative live endpoint
        url = f"https://api-web.nhle.com/v1/gamecenter/{self.game_id}/landing"
        self.api_endpoint_other = url

        # HTML rosters endpoint
        url = f"https://www.nhl.com/scores/htmlreports/{self.season}/RO{self.html_id}.HTM"
        self.html_rosters_endpoint: str = url

        # shifts endpoints
        home_url = f"https://www.nhl.com/scores/htmlreports/{self.season}/TH{self.html_id}.HTM"
        self.home_shifts_endpoint: str = home_url

        away_url = f"https://www.nhl.com/scores/htmlreports/{self.season}/TV{self.html_id}.HTM"
        self.away_shifts_endpoint: str = away_url

        # HTML events endpoint
        url = f"https://www.nhl.com/scores/htmlreports/{self.season}/PL{self.html_id}.HTM"
        self.html_events_endpoint: str = url

        # requests session
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

        self._es_model = _get_model("even-strength", model_version)
        self._pp_model = _get_model("powerplay", model_version)
        self._sh_model = _get_model("shorthanded", model_version)
        self._ef_model = _get_model("empty-for", model_version)
        self._ea_model = _get_model("empty-against", model_version)
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
        """Method for fetching API data and metadata."""
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

    def _finalize_dataframe(self, data, schema):
        """Method to return a pandas or polars dataframe, depending on user preference."""
        df = pl.from_dicts(data=data, schema=schema)
        return _to_backend(df, self._backend)
