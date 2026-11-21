"""Player identity and career statistics: the Player utility class.

Wraps the NHL API's public player endpoints, providing structured access to
career totals, season-by-season splits, game logs, and featured stats. All
data-fetching properties are prefixed with ``_`` and trigger a network call
on first access; identity properties (``player_name``, ``current_team``, etc.)
are cheap dict lookups into the pre-fetched landing page payload.

Public class:
    Player: Resolves a player ID to identity metadata and on-demand career stats.
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
from functools import cached_property
import logging
from typing import TYPE_CHECKING, Any, Generic, Literal, overload

import polars as pl

from chickenstats.chicken_nhl._docstrings import (
    _PLAYER_CAREER_TOTALS_DOC,
    _PLAYER_GAME_LOGS_DOC,
    _PLAYER_SEASON_STATS_DOC,
    shared_doc,
)
from chickenstats.chicken_nhl.season import _GAME_TYPE_SESSIONS
from chickenstats.exceptions import InvalidInputError, PlayerDownloadError, _raise_for_status
from chickenstats.utilities import ChickenSession
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.types import FrameT, frame_property
from chickenstats.utilities.utilities import _to_backend, _to_polars, _validate_backend

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    from chickenstats.utilities.types import (
        AnyBackend,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://search.d3.nhle.com/api/v1/search/player"

_SEARCH_RESULT_SCHEMA = {
    "player_id": pl.Int64,
    "player_name": pl.String,
    "position_code": pl.String,
    "team_abbrev": pl.String,
    "last_team_abbrev": pl.String,
    "last_season_id": pl.Int64,
    "sweater_number": pl.Int64,
    "active": pl.Boolean,
    "height": pl.String,
    "height_in_inches": pl.Int64,
    "height_in_centimeters": pl.Int64,
    "weight_in_pounds": pl.Int64,
    "weight_in_kilograms": pl.Int64,
    "birth_city": pl.String,
    "birth_state_province": pl.String,
    "birth_country": pl.String,
}


@overload
def search_players(
    query: str,
    *,
    active: bool | None = None,
    limit: int = 25,
    backend: PolarsBackend = "polars",
    requests_session: ChickenSession | None = None,
) -> pl.DataFrame: ...
@overload
def search_players(
    query: str,
    *,
    active: bool | None = None,
    limit: int = 25,
    backend: PandasBackend,
    requests_session: ChickenSession | None = None,
) -> pd.DataFrame: ...
@overload
def search_players(
    query: str,
    *,
    active: bool | None = None,
    limit: int = 25,
    backend: PyarrowBackend,
    requests_session: ChickenSession | None = None,
) -> pa.Table: ...
@overload
def search_players(
    query: str,
    *,
    active: bool | None = None,
    limit: int = 25,
    backend: NarwhalsBackend,
    requests_session: ChickenSession | None = None,
) -> NarwhalsFrame: ...
@overload
def search_players(
    query: str,
    *,
    active: bool | None = None,
    limit: int = 25,
    backend: AnyBackend = "polars",
    requests_session: ChickenSession | None = None,
) -> Any: ...
def search_players(
    query: str,
    *,
    active: bool | None = None,
    limit: int = 25,
    backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
    requests_session: ChickenSession | None = None,
) -> Any:
    """Search for NHL players by name via the NHL's public player-search endpoint.

    Resolves a player's numeric ``api_id`` (required to construct ``Player``) from a
    name, so callers don't need to already know the ID. Matches on name
    substring/prefix — the NHL endpoint does not fuzzy-match misspellings, so a typo
    returns zero rows.

    Parameters:
        query (str): Player name (or partial name) to search for, e.g. ``"mcdavid"``.
        active (bool | None): Filter to active-roster players only (``True``),
            retired/inactive players only (``False``), or all players (``None``,
            default).
        limit (int): Maximum number of results to return. Default ``25``.
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            Output backend. Default ``"polars"``.
        requests_session (ChickenSession | None): ChickenSession to use for requests, e.g., with a custom user agent.
            Defaults to a new ChickenSession.

    Returns:
        DataFrame: One row per matching player, with columns ``player_id``,
            ``player_name``, ``position_code``, ``team_abbrev``, ``last_team_abbrev``,
            ``last_season_id``, ``sweater_number``, ``active``, ``height``,
            ``height_in_inches``, ``height_in_centimeters``, ``weight_in_pounds``,
            ``weight_in_kilograms``, ``birth_city``, ``birth_state_province``,
            ``birth_country``.

    Raises:
        NetworkError: If the NHL API answers with an error status.

    Examples:
        >>> from chickenstats.chicken_nhl import search_players, Player
        >>> results = search_players("mcdavid")
        >>> mcdavid = Player(results["player_id"][0])
    """
    _validate_backend(backend)

    params: dict[str, str | int] = {"culture": "en-us", "limit": limit, "q": query}
    if active is not None:
        params["active"] = "true" if active else "false"

    if requests_session is not None:
        response = requests_session.get(_SEARCH_URL, params=params)
    else:
        with ChickenSession() as session:
            response = session.get(_SEARCH_URL, params=params)
    _raise_for_status(response)
    results = response.json()

    records = [
        {
            "player_id": int(r["playerId"]),
            "player_name": r["name"],
            "position_code": r.get("positionCode"),
            "team_abbrev": r.get("teamAbbrev"),
            "last_team_abbrev": r.get("lastTeamAbbrev"),
            "last_season_id": int(r["lastSeasonId"]) if r.get("lastSeasonId") else None,
            "sweater_number": r.get("sweaterNumber"),
            "active": r.get("active"),
            "height": r.get("height"),
            "height_in_inches": r.get("heightInInches"),
            "height_in_centimeters": r.get("heightInCentimeters"),
            "weight_in_pounds": r.get("weightInPounds"),
            "weight_in_kilograms": r.get("weightInKilograms"),
            "birth_city": r.get("birthCity"),
            "birth_state_province": r.get("birthStateProvince"),
            "birth_country": r.get("birthCountry"),
        }
        for r in results
    ]

    df = pl.DataFrame(records, schema=_SEARCH_RESULT_SCHEMA)

    return _to_backend(df, backend)


_BIO_SCHEMA = {
    "player_id": pl.Int64,
    "player_name": pl.String,
    "position_code": pl.String,
    "shoots_catches": pl.String,
    "height_in_inches": pl.Int64,
    "weight_in_pounds": pl.Int64,
    "birth_date": pl.Date,
    "is_active": pl.Boolean,
}


@overload
def player_bios(
    player_ids: Iterable[int | str],
    *,
    backend: PolarsBackend = "polars",
    requests_session: ChickenSession | None = None,
    max_workers: int = 8,
) -> pl.DataFrame: ...
@overload
def player_bios(
    player_ids: Iterable[int | str],
    *,
    backend: PandasBackend,
    requests_session: ChickenSession | None = None,
    max_workers: int = 8,
) -> pd.DataFrame: ...
@overload
def player_bios(
    player_ids: Iterable[int | str],
    *,
    backend: PyarrowBackend,
    requests_session: ChickenSession | None = None,
    max_workers: int = 8,
) -> pa.Table: ...
@overload
def player_bios(
    player_ids: Iterable[int | str],
    *,
    backend: NarwhalsBackend,
    requests_session: ChickenSession | None = None,
    max_workers: int = 8,
) -> NarwhalsFrame: ...
@overload
def player_bios(
    player_ids: Iterable[int | str],
    *,
    backend: AnyBackend = "polars",
    requests_session: ChickenSession | None = None,
    max_workers: int = 8,
) -> Any: ...
def player_bios(
    player_ids: Iterable[int | str],
    *,
    backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
    requests_session: ChickenSession | None = None,
    max_workers: int = 8,
) -> Any:
    """Handedness, height, weight and birth date for many players, from their landing pages.

    One request per player, made ``max_workers`` at a time through one session. The NHL's
    game rosters do not carry these fields, and its team-season rosters leave out players
    who were not on a team when its season ended, so this reads each player's own page.

    Height and weight are the NHL's current values (for a retired player, their last listed
    ones), not their size in a given season.

    Parameters:
        player_ids (Iterable[int | str]): NHL API player IDs, e.g. the ``api_id`` values from
            ``Scraper.rosters``. Repeats are fetched once.
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            Output backend. Default ``"polars"``.
        requests_session (ChickenSession | None): ChickenSession to use for requests, e.g., with a
            custom user agent or a lower ``max_requests_per_second``. Defaults to a new
            ChickenSession, closed when the downloads end; a session passed in is left open.
        max_workers (int): Number of players downloaded at once. Default ``8``.

    Returns:
        DataFrame: One row per player, sorted by ``player_id``, with columns ``player_id``,
            ``player_name``, ``position_code``, ``shoots_catches`` (``"L"`` or ``"R"``; the
            catching hand for a goalie), ``height_in_inches``, ``weight_in_pounds``,
            ``birth_date`` and ``is_active``. A field the NHL does not list is null.

    Raises:
        PlayerDownloadError: When any player's page could not be downloaded after the
            session's retries. Every other player is still downloaded first, and the error's
            ``player_ids`` lists the ones that failed.

    Examples:
        >>> from chickenstats.chicken_nhl import player_bios
        >>> bios = player_bios([8478402, 8471214])
        >>> bios.select("player_name", "shoots_catches", "height_in_inches").to_dicts()[0]
        {'player_name': 'Alex Ovechkin', 'shoots_catches': 'R', 'height_in_inches': 75}
    """
    _validate_backend(backend)
    ids = list(dict.fromkeys(int(player_id) for player_id in player_ids))
    session = requests_session if requests_session is not None else ChickenSession()

    def fetch(player_id: int) -> dict:
        player = Player(player_id, requests_session=session)
        return {
            "player_id": player_id,
            "player_name": player.player_name,
            "position_code": player.position_code,
            "shoots_catches": player.shoots_catches,
            "height_in_inches": player.height_in_inches,
            "weight_in_pounds": player.weight_in_pounds,
            "birth_date": player.birth_date,
            "is_active": player.is_active,
        }

    records: list[dict] = []
    failed: dict[int, Exception] = {}
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch, player_id): player_id for player_id in ids}
            for future in as_completed(futures):
                try:
                    records.append(future.result())
                except Exception as exc:  # noqa: BLE001 -- collected, then raised once with every ID
                    failed[futures[future]] = exc
    finally:
        if requests_session is None:
            session.close()

    if failed:
        missing = sorted(failed)
        first = failed[missing[0]]
        raise PlayerDownloadError(
            f"Could not download {len(missing)} of {len(ids)} players' landing pages, e.g. {missing[0]}: "
            f"{type(first).__name__}: {first}",
            player_ids=missing,
        )

    df = pl.DataFrame(records, schema=_BIO_SCHEMA).sort("player_id")
    return _to_backend(df, backend)


_PROFILE_SCHEMA = {
    **_BIO_SCHEMA,
    "height_in_inches": pl.Float64,
    "weight_in_pounds": pl.Float64,
    "left_handed": pl.Int8,
    "age": pl.Float64,
}

_DAYS_PER_YEAR = 365.25


def _as_date(column: str, dtype: pl.DataType) -> pl.Expr:
    return pl.col(column).str.to_date() if dtype == pl.String else pl.col(column).cast(pl.Date)


@overload
def player_profiles(bios: Any, date: dt.date | str, *, backend: PolarsBackend = "polars") -> pl.DataFrame: ...
@overload
def player_profiles(bios: Any, date: dt.date | str, *, backend: PandasBackend) -> pd.DataFrame: ...
@overload
def player_profiles(bios: Any, date: dt.date | str, *, backend: PyarrowBackend) -> pa.Table: ...
@overload
def player_profiles(bios: Any, date: dt.date | str, *, backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def player_profiles(bios: Any, date: dt.date | str, *, backend: AnyBackend = "polars") -> Any: ...
def player_profiles(
    bios: Any, date: dt.date | str, *, backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars"
) -> Any:
    """Players' bios with a hand flag, height and weight as floats, and age on a date.

    Parameters:
        bios (DataFrame): ``player_bios`` output in any backend, or any frame with its
            ``player_id``, ``shoots_catches``, ``height_in_inches``, ``weight_in_pounds`` and
            ``birth_date`` columns, e.g. joined to the games each player played.
        date (dt.date | str): The date to give each player's age on, either one date for every
            row or the name of a date column in ``bios``, such as ``"game_date"``. A text column
            is read as ``YYYY-MM-DD``.
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            Output backend. Default ``"polars"``.

    Returns:
        DataFrame: ``bios`` with ``height_in_inches`` and ``weight_in_pounds`` as floats, and two
            columns added: ``left_handed``, 1 for a player who shoots or catches left, 0 for right and
            null otherwise, and ``age``, in years with a fraction, on ``date``. One row per
            ``player_id``, or per ``player_id`` and date when ``date`` names a column, keeping the first.

    Raises:
        InvalidInputError: When ``bios`` lacks a column the profile needs, or ``date`` names a
            column it does not have.

    Examples:
        >>> import datetime as dt
        >>> from chickenstats.chicken_nhl import player_bios, player_profiles
        >>> profiles = player_profiles(player_bios([8476887]), dt.date(2023, 10, 10))
        >>> profiles.select("left_handed", "height_in_inches", "age").to_dicts()
        [{'left_handed': 0, 'height_in_inches': 73.0, 'age': 29.15811088295688}]
    """
    _validate_backend(backend)
    df = _to_polars(bios)

    needed = ["player_id", "shoots_catches", "height_in_inches", "weight_in_pounds", "birth_date"]
    if isinstance(date, str):
        needed.append(date)
    missing = [column for column in needed if column not in df.columns]
    if missing:
        raise InvalidInputError(f"player_profiles needs the columns {missing}, which bios does not have")

    if isinstance(date, str):
        on, keys = _as_date(date, df.schema[date]), ["player_id", date]
    else:
        # A datetime is a date too, so it is cut to its day first
        day = date.date() if isinstance(date, dt.datetime) else date
        on, keys = pl.lit(day, dtype=pl.Date), ["player_id"]

    hand = pl.col("shoots_catches")
    df = df.unique(keys, keep="first", maintain_order=True).with_columns(
        pl.col("player_id").cast(pl.Int64),
        pl.col("height_in_inches", "weight_in_pounds").cast(pl.Float64),
        left_handed=pl.when(hand == "L").then(1).when(hand == "R").then(0).cast(pl.Int8),
        age=(on - _as_date("birth_date", df.schema["birth_date"])).dt.total_days() / _DAYS_PER_YEAR,
    )
    return _to_backend(df, backend)


# The NHL API key of each stat column
_STAT_KEYS = {
    "games_played": "gamesPlayed",
    "goals": "goals",
    "assists": "assists",
    "points": "points",
    "plus_minus": "plusMinus",
    "pim": "pim",
    "shots": "shots",
    "shifts": "shifts",
    "shooting_pct": "shootingPctg",
    "faceoff_pct": "faceoffWinningPctg",
    "power_play_goals": "powerPlayGoals",
    "power_play_points": "powerPlayPoints",
    "shorthanded_goals": "shorthandedGoals",
    "shorthanded_points": "shorthandedPoints",
    "game_winning_goals": "gameWinningGoals",
    "ot_goals": "otGoals",
    "avg_toi": "avgToi",
    "toi": "toi",
    "games_started": "gamesStarted",
    "decision": "decision",
    "wins": "wins",
    "losses": "losses",
    "ot_losses": "otLosses",
    "ties": "ties",
    "shots_against": "shotsAgainst",
    "goals_against": "goalsAgainst",
    "goals_against_avg": "goalsAgainstAvg",
    "save_pct": "savePctg",
    "shutouts": "shutouts",
}
_STAT_DTYPES: dict[str, type[pl.DataType]] = {
    **dict.fromkeys(_STAT_KEYS, pl.Int64),
    **dict.fromkeys(("shooting_pct", "faceoff_pct", "avg_toi", "toi", "goals_against_avg", "save_pct"), pl.Float64),
    "decision": pl.String,
}

_GAME_LOG_STATS = [
    "goals",
    "assists",
    "points",
    "plus_minus",
    "pim",
    "shots",
    "shifts",
    "power_play_goals",
    "power_play_points",
    "shorthanded_goals",
    "shorthanded_points",
    "game_winning_goals",
    "ot_goals",
    "toi",
    "games_started",
    "decision",
    "shots_against",
    "goals_against",
    "save_pct",
    "shutouts",
]
_TOTALS_STATS = [name for name in _STAT_KEYS if name not in ("shifts", "decision")]

_GAME_LOG_SCHEMA = {
    "player_id": pl.Int64,
    "season": pl.Int64,
    "session": pl.String,
    "game_id": pl.Int64,
    "game_date": pl.Date,
    "team": pl.String,
    "opponent": pl.String,
    "is_home": pl.Boolean,
    **{name: _STAT_DTYPES[name] for name in _GAME_LOG_STATS},
}
_SEASON_STATS_SCHEMA = {
    "player_id": pl.Int64,
    "season": pl.Int64,
    "session": pl.String,
    "league": pl.String,
    "team_name": pl.String,
    **{name: _STAT_DTYPES[name] for name in _TOTALS_STATS},
}
_CAREER_TOTALS_SCHEMA = {
    "player_id": pl.Int64,
    "session": pl.String,
    **{name: _STAT_DTYPES[name] for name in _TOTALS_STATS},
}


def _minutes(clock: str | None) -> float | None:
    """Minutes from an NHL clock reading such as ``"20:36"``, which can run past 60 minutes."""
    if not clock:
        return None
    minutes, seconds = clock.split(":")
    return int(minutes) + int(seconds) / 60


def _stats(record: dict, names: list[str]) -> dict:
    """The stat columns of one NHL API record, with its clock readings in minutes."""
    stats = {name: record.get(_STAT_KEYS[name]) for name in names}
    if "avg_toi" in stats:
        stats["avg_toi"] = _minutes(stats["avg_toi"])
    if "toi" in stats:
        # Season and career totals call a goalie's total timeOnIce
        stats["toi"] = _minutes(record.get("toi", record.get("timeOnIce")))
    return stats


class Player(Generic[FrameT]):
    """NHL player identity, current team and seasons played.

    Wraps the NHL API's public player endpoints. Pass a numeric player ID (the
    same ``api_id`` returned by ``Scraper.rosters``) to look up the player's
    name, current team and the seasons they have played.

    Parameters:
        player_id (int | str): The NHL API player ID (e.g. ``8478402`` for Connor McDavid).
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            DataFrame backend for ``game_logs``, ``season_stats`` and ``career_totals``. One of
            ``"polars"`` (default), ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.
        requests_session (ChickenSession | None): ChickenSession to use for requests, e.g., with a custom user agent.
            Defaults to a new ChickenSession.

    Attributes:
        player_id (int | str): Stored player ID.
        player_name (str): Full player name (first + last).
        first_name (str): First name.
        last_name (str): Last name.
        is_active (bool): Whether the player is currently on an NHL roster.
        position_code (str | None): Position code, e.g. ``"C"`` or ``"G"``.
        shoots_catches (str | None): ``"L"`` or ``"R"``: the shooting hand, or a goalie's catching hand.
        height_in_inches (int | None): Height in inches, the NHL's current value.
        weight_in_pounds (int | None): Weight in pounds, the NHL's current value, not a past season's.
        birth_date (datetime.date | None): Date of birth.
        current_team (str): Three-letter abbreviation of the player's current team.
        current_team_id (int): NHL API team ID for the player's current team.
        current_team_name (str): Common team name (e.g. ``"Predators"``).
        current_team_full_name (str): Full English team name (e.g. ``"Nashville Predators"``).
        current_team_full_name_fr (str): Full French name of the player's current team.
        player_info (dict): The landing page response without its stats sections.
        active_seasons (list): Regular-season season IDs the player has appeared in.
        playoff_seasons (list): Playoff season IDs the player has appeared in.
        game_logs (DataFrame): One row per game in the season the NHL API lists as current.
        season_stats (DataFrame): One row per season, session, league and team.
        career_totals (DataFrame): NHL career totals for the regular season and playoffs.

    Note:
        Nothing is downloaded until an attribute is first read. The identity and team
        attributes, ``season_stats`` and ``career_totals`` come from the player's landing page;
        ``active_seasons``, ``playoff_seasons`` and ``game_logs`` come from the current-season
        game log. Call ``prefetch()`` to download both at once.

    Examples:
        >>> from chickenstats.chicken_nhl import Player
        >>> player = Player(8478402)
        >>> player.player_name
        'Connor McDavid'
        >>> player.current_team
        'EDM'
        >>> player.active_seasons
        [20152016, ...]
        >>> player.career_totals["session"].to_list()
        ['R', 'P']
    """

    @overload
    def __init__(
        self: Player[pl.DataFrame],
        player_id: int | str,
        *,
        backend: PolarsBackend = "polars",
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Player[pd.DataFrame],
        player_id: int | str,
        *,
        backend: PandasBackend,
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Player[pa.Table],
        player_id: int | str,
        *,
        backend: PyarrowBackend,
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Player[NarwhalsFrame],
        player_id: int | str,
        *,
        backend: NarwhalsBackend,
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Player[Any],
        player_id: int | str,
        *,
        backend: AnyBackend = "polars",
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    def __init__(
        self,
        player_id: int | str,
        *,
        backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
        requests_session: ChickenSession | None = None,
    ):
        """Instantiates player endpoints and session — no network calls are made here."""
        self.backend = _validate_backend(backend)
        self.player_id = player_id

        self._base_api_url = "https://api-web.nhle.com/v1"
        self.base_url = f"{self._base_api_url}/player/{player_id}"
        self.landing_url = f"{self.base_url}/landing"
        self.current_game_log_url = f"{self.base_url}/game-log/now"

        self._requests_session = requests_session or ChickenSession()

    def __repr__(self) -> str:
        """Return string representation of the Player instance."""
        return f"Player(player_id={self.player_id!r}, backend={self.backend!r})"

    @cached_property
    def _landing_info(self) -> dict:
        """Fetches the player landing page from the NHL API."""
        response = self._requests_session.get(self.landing_url)
        _raise_for_status(response)
        return response.json()

    @cached_property
    def _current_game_logs(self) -> dict:
        """Fetches the current-season game log from the NHL API."""
        response = self._requests_session.get(self.current_game_log_url)
        _raise_for_status(response)
        return response.json()

    @cached_property
    def player_info(self) -> dict:
        """Basic player metadata, with stats keys excluded."""
        stats_keys = {"featuredStats", "careerTotals", "last5Games", "seasonTotals", "currentTeamRoster"}
        return {k: v for k, v in self._landing_info.items() if k not in stats_keys}

    @property
    def first_name(self) -> str:
        """Player's first name."""
        return self.player_info["firstName"]["default"]

    @property
    def last_name(self) -> str:
        """Player's last name."""
        return self.player_info["lastName"]["default"]

    @property
    def player_name(self) -> str:
        """Player's full name (first + last)."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        """Whether the player is currently active on an NHL roster."""
        return self.player_info["isActive"]

    @property
    def position_code(self) -> str | None:
        """Position code: ``"C"``, ``"L"``, ``"R"``, ``"D"`` or ``"G"``."""
        return self.player_info.get("position")

    @property
    def shoots_catches(self) -> str | None:
        """Handedness, ``"L"`` or ``"R"``: the shooting hand for a skater, the catching hand for a goalie."""
        return self.player_info.get("shootsCatches")

    @property
    def height_in_inches(self) -> int | None:
        """Height in inches, the NHL's current value."""
        return self.player_info.get("heightInInches")

    @property
    def weight_in_pounds(self) -> int | None:
        """Weight in pounds, the NHL's current value (a retired player's last listed one), not their weight in a given season."""
        return self.player_info.get("weightInPounds")

    @property
    def birth_date(self) -> dt.date | None:
        """Date of birth."""
        birth_date = self.player_info.get("birthDate")
        return dt.date.fromisoformat(birth_date) if birth_date else None

    @property
    def current_team_id(self) -> int | None:
        """NHL team ID for the player's current team, or None for a player with no team."""
        return self.player_info.get("currentTeamId")

    @property
    def current_team(self) -> str | None:
        """Three-letter abbreviation of the player's current team, or None for a player with no team."""
        return self.player_info.get("currentTeamAbbrev")

    @property
    def current_team_name(self) -> str | None:
        """Common name of the player's current team (e.g. 'Predators'), or None for a player with no team."""
        return (self.player_info.get("teamCommonName") or {}).get("default")

    @property
    def current_team_full_name(self) -> str | None:
        """Full English name of the player's current team (e.g. 'Nashville Predators'), or None for a player with no team."""
        return (self.player_info.get("fullTeamName") or {}).get("default")

    @property
    def current_team_full_name_fr(self) -> str | None:
        """Full French name of the player's current team, or None for a player with no team."""
        return (self.player_info.get("fullTeamName") or {}).get("fr")

    # Players with no NHL games lack featuredStats, careerTotals and last5Games
    @cached_property
    def _featured_stats(self) -> dict | None:
        """Raw featured-stats payload from the NHL API landing page, or None if the player has none."""
        return self._landing_info.get("featuredStats")

    @property
    def _current_featured_season(self) -> int | None:
        """Season ID of the current featured season from the featured-stats payload."""
        return self._featured_stats["season"] if self._featured_stats else None

    @property
    def _featured_regular_season_stats(self) -> dict | None:
        """Regular-season stat totals from the featured-stats payload."""
        return self._featured_stats["regularSeason"]["subSeason"] if self._featured_stats else None

    @property
    def _featured_career_stats(self) -> dict | None:
        """Career aggregate stat totals from the featured-stats payload."""
        return self._featured_stats["regularSeason"]["career"] if self._featured_stats else None

    @cached_property
    def _career_totals(self) -> dict | None:
        """Raw career-totals payload from the NHL API landing page, or None if the player has none."""
        return self._landing_info.get("careerTotals")

    @cached_property
    def _career_regular_season_stats(self) -> dict | None:
        """Raw regular-season career rows from the career-totals payload."""
        return self._career_totals["regularSeason"] if self._career_totals else None

    @property
    def _career_playoff_stats(self) -> dict | None:
        """Raw playoff career rows from the career-totals payload, or None if unavailable."""
        return self._career_totals.get("playoffs") if self._career_totals else None

    @property
    def _last_five_games(self) -> list:
        """Raw last-five-games entries from the NHL API landing page; empty if the player has none."""
        return self._landing_info.get("last5Games", [])

    @property
    def _season_totals(self) -> list:
        """Raw season-totals entries from the NHL API landing page; empty if the player has none."""
        return self._landing_info.get("seasonTotals", [])

    @property
    def _game_logs(self) -> list:
        """Raw game-log entries for the current season from the NHL API."""
        return self._current_game_logs["gameLog"]

    @frame_property
    @shared_doc(_PLAYER_GAME_LOGS_DOC)
    def game_logs(self) -> FrameT:
        """Game logs — docstring lives in _docstrings._PLAYER_GAME_LOGS_DOC."""
        logs = self._current_game_logs
        records = [
            {
                "player_id": int(self.player_id),
                "season": logs["seasonId"],
                "session": _GAME_TYPE_SESSIONS.get(logs["gameTypeId"]),
                "game_id": game["gameId"],
                "game_date": dt.date.fromisoformat(game["gameDate"]),
                "team": game["teamAbbrev"],
                "opponent": game["opponentAbbrev"],
                "is_home": game["homeRoadFlag"] == "H",
                **_stats(game, _GAME_LOG_STATS),
            }
            for game in logs["gameLog"]
        ]
        df = pl.DataFrame(records, schema=_GAME_LOG_SCHEMA).sort("game_date", "game_id")
        return _to_backend(df, self.backend)

    @frame_property
    @shared_doc(_PLAYER_SEASON_STATS_DOC)
    def season_stats(self) -> FrameT:
        """Season stats — docstring lives in _docstrings._PLAYER_SEASON_STATS_DOC."""
        records = [
            {
                "player_id": int(self.player_id),
                "season": season["season"],
                "session": _GAME_TYPE_SESSIONS.get(season["gameTypeId"]),
                "league": season["leagueAbbrev"],
                "team_name": season["teamName"]["default"],
                **_stats(season, _TOTALS_STATS),
            }
            for season in self._season_totals
        ]
        df = pl.DataFrame(records, schema=_SEASON_STATS_SCHEMA)
        return _to_backend(df, self.backend)

    @frame_property
    @shared_doc(_PLAYER_CAREER_TOTALS_DOC)
    def career_totals(self) -> FrameT:
        """Career totals — docstring lives in _docstrings._PLAYER_CAREER_TOTALS_DOC."""
        records = [
            {"player_id": int(self.player_id), "session": session, **_stats(totals, _TOTALS_STATS)}
            for session, totals in (("R", self._career_regular_season_stats), ("P", self._career_playoff_stats))
            if totals
        ]
        df = pl.DataFrame(records, schema=_CAREER_TOTALS_SCHEMA)
        return _to_backend(df, self.backend)

    @cached_property
    def _active_seasons_data(self) -> dict:
        """Season → game-type list mapping from the current game-log payload."""
        return {x["season"]: x["gameTypes"] for x in self._current_game_logs["playerStatsSeasons"]}

    @cached_property
    def active_seasons(self) -> list:
        """List of regular-season seasons the player has appeared in."""
        return [k for k, v in self._active_seasons_data.items() if 2 in v]

    @cached_property
    def playoff_seasons(self) -> list:
        """List of playoff seasons the player has appeared in."""
        return [k for k, v in self._active_seasons_data.items() if 3 in v]

    def prefetch(self) -> None:
        """Pre-fetch landing page and game log data concurrently."""

        def _get_landing():
            _ = self._landing_info

        def _get_logs():
            _ = self._current_game_logs

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(task) for task in [_get_landing, _get_logs]]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                    # Best effort; the property retries on access
                    logger.warning("Failed to fetch player data endpoint", exc_info=True)
