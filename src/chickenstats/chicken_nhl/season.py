from __future__ import annotations

import warnings
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any, Generic, Literal, overload
from zoneinfo import ZoneInfo

import polars as pl

from chickenstats.utilities.utilities import convert_to_list
from chickenstats.exceptions import InvalidInputError, InvalidSeasonError, InvalidTeamError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.types import DataFrameT, FrameT

from chickenstats.chicken_nhl.validation_pydantic import ScheduleGame, StandingsTeam
from chickenstats.chicken_nhl.validation_polars import schedule_polars_schema, standings_polars_schema
from chickenstats.utilities.utilities import (
    ChickenProgress,
    ChickenSession,
    _to_backend,
    _to_polars,
    _detect_backend,
    _validate_backend,
)
from chickenstats.chicken_nhl._docstrings import _SEASON_SCHEDULE_DOC, _SEASON_STANDINGS_DOC, shared_doc
from chickenstats.chicken_nhl._season_constants import _CANCELED_SEASONS, _TEAMS_BY_YEAR, regular_season_end_dates

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    from chickenstats.utilities.types import (
        AnyBackend,
        InputFrameT,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )

# NHL game types in each session; the 4 Nations Face-Off final is game type 20
_SESSION_CODES: dict[str, set[int]] = {"PR": {1}, "R": {2}, "P": {3}, "FO": {19, 20}}
_GAME_TYPE_SESSIONS: dict[int, str] = {code: session for session, codes in _SESSION_CODES.items() for code in codes}

# Standings fields and their NHL API keys; team and team_name are read separately
_STANDINGS_FIELDS: dict[str, str] = {
    "conference": "conferenceName",
    "date": "date",
    "division": "divisionName",
    "games_played": "gamesPlayed",
    "goal_differential": "goalDifferential",
    "goal_differential_pct": "goalDifferentialPctg",
    "goals_against": "goalAgainst",
    "goals_for": "goalFor",
    "goals_for_pct": "goalsForPctg",
    "home_games_played": "homeGamesPlayed",
    "home_goal_differential": "homeGoalDifferential",
    "home_goals_against": "homeGoalsAgainst",
    "home_goals_for": "homeGoalsFor",
    "home_losses": "homeLosses",
    "home_ot_losses": "homeOtLosses",
    "home_points": "homePoints",
    "home_wins": "homeWins",
    "home_regulation_wins": "homeRegulationWins",
    "home_ties": "homeTies",
    "l10_goal_differential": "l10GoalDifferential",
    "l10_goals_against": "l10GoalsAgainst",
    "l10_goals_for": "l10GoalsFor",
    "l10_losses": "l10Losses",
    "l10_ot_losses": "l10OtLosses",
    "l10_points": "l10Points",
    "l10_regulation_wins": "l10RegulationWins",
    "l10_ties": "l10Ties",
    "l10_wins": "l10Wins",
    "losses": "losses",
    "ot_losses": "otLosses",
    "points_pct": "pointPctg",
    "points": "points",
    "regulation_win_pct": "regulationWinPctg",
    "regulation_wins": "regulationWins",
    "road_games_played": "roadGamesPlayed",
    "road_goal_differential": "roadGoalDifferential",
    "road_goals_against": "roadGoalsAgainst",
    "road_goals_for": "roadGoalsFor",
    "road_losses": "roadLosses",
    "road_ot_losses": "roadOtLosses",
    "road_points": "roadPoints",
    "road_regulation_wins": "roadRegulationWins",
    "road_ties": "roadTies",
    "road_wins": "roadWins",
    "season": "seasonId",
    "shootout_losses": "shootoutLosses",
    "shootout_wins": "shootoutWins",
    "streak_code": "streakCode",
    "streak_count": "streakCount",
    "team_logo": "teamLogo",
    "ties": "ties",
    "waivers_sequence": "waiversSequence",
    "wildcard_sequence": "wildcardSequence",
    "win_pct": "winPctg",
    "wins": "wins",
}

# Fields that fall back to zero, rather than None, when the NHL API leaves them out.
_STANDINGS_DEFAULTS: dict[str, int] = {
    "goal_differential_pct": 0,
    "goals_for_pct": 0,
    "points_pct": 0,
    "regulation_win_pct": 0,
    "streak_count": 0,
    "win_pct": 0,
}


def _session_codes(sessions: list[str] | str | None) -> set[int]:
    """The NHL game types the sessions argument asks for; regular season and playoffs when it is empty."""
    if not sessions:
        return _SESSION_CODES["R"] | _SESSION_CODES["P"]

    codes = set()
    for session in convert_to_list(sessions, object_type="sessions"):
        if session not in _SESSION_CODES:
            raise InvalidInputError(f"session must be one of {list(_SESSION_CODES)}, got {session!r}", obj=session)
        codes |= _SESSION_CODES[session]
    return codes


class Season(Generic[FrameT]):
    """Scrapes schedule and standings data.

    Helpful for pulling game IDs and scraping programmatically.

    Parameters:
        year (int or float or str):
            4-digit year identifier, the first year in the season, e.g., 2023
        standings_date (str | None):
            Scrapes the standings as of the given date. Format like YYYY-MM-DD
            (%Y-%m-%d in datetime formatting). For the current season, defaults to the
            current date
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            DataFrame backend for all returned data. One of ``"polars"`` (default),
            ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.
        requests_session (ChickenSession | None):
            ChickenSession to use for requests, e.g., with a custom user agent. Defaults to a new ChickenSession.

    Attributes:
        season (int):
            8-digit year identifier, the year entered, plus 1, e.g., 20232024

    Examples:
        First, instantiate the Season object
        >>> season = Season(2023)

        Scrape schedule information
        >>> nsh_schedule = season.schedule("NSH")  # Returns the schedule for the Nashville Predators

        Scrape standings information
        >>> standings = season.standings  # Returns the latest standings for that season

    """

    @overload
    def __init__(
        self: Season[pl.DataFrame],
        year: str | int | float,
        *,
        standings_date: str | None = None,
        backend: PolarsBackend = "polars",
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Season[pd.DataFrame],
        year: str | int | float,
        *,
        standings_date: str | None = None,
        backend: PandasBackend,
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Season[pa.Table],
        year: str | int | float,
        *,
        standings_date: str | None = None,
        backend: PyarrowBackend,
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Season[NarwhalsFrame],
        year: str | int | float,
        *,
        standings_date: str | None = None,
        backend: NarwhalsBackend,
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: Season[Any],
        year: str | int | float,
        *,
        standings_date: str | None = None,
        backend: AnyBackend = "polars",
        requests_session: ChickenSession | None = None,
    ) -> None: ...
    def __init__(
        self,
        year: str | int | float,
        *,
        standings_date: str | None = None,
        backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
        requests_session: ChickenSession | None = None,
    ):
        """Instantiates a Season object for a given year."""
        self._backend = _validate_backend(backend)

        if isinstance(year, float):
            year = int(year)

        year_str = str(year)

        if len(year_str) == 8:
            self.season = int(year_str)

        elif len(year_str) == 4:
            self.season = int(f"{year_str}{int(year_str) + 1}")

        else:
            raise InvalidSeasonError(
                f"'{year}' is not a valid season year format — expected a 4-digit year (e.g. 2023) "
                "or an 8-digit season (e.g. 20232024).",
                season=year,
            )

        first_year = int(str(self.season)[0:4])

        if first_year in _CANCELED_SEASONS:
            raise InvalidSeasonError(f"No {first_year} season: {_CANCELED_SEASONS[first_year]}.", season=first_year)

        min_year, max_year = min(_TEAMS_BY_YEAR), max(_TEAMS_BY_YEAR)

        if first_year > max_year:
            warnings.warn(
                f"chickenstats has no team list for {first_year}, so Season uses the {max_year} list. "
                "Upgrading chickenstats may give a newer one.",
                UserWarning,
                stacklevel=2,
            )

        self.teams: list[str] = _TEAMS_BY_YEAR.get(min(first_year, max_year), [])

        if not self.teams:
            raise InvalidSeasonError(
                f"{first_year} is not a supported season year — the earliest supported year is {min_year}.",
                season=first_year,
            )

        self._schedule = []
        self._scraped_schedule_teams = []
        self._scraped_schedule = []
        self._standings = []
        self._requests_session = requests_session or ChickenSession()
        self._season_str = str(self.season)[:4] + "-" + str(self.season)[6:8]

        # Final standings for a finished season, live ones otherwise; future dates return nothing
        end_date = regular_season_end_dates.get(first_year)
        today = dt.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

        if standings_date:
            self.standings_date = standings_date
        elif end_date is None or end_date >= today:
            self.standings_date = "now"
        else:
            self.standings_date = end_date

    def __repr__(self) -> str:
        """Return string representation of Season object."""
        return f"Season(season={self.season!r}, backend={self._backend!r})"

    def _finalize_dataframe(self, data, schema) -> FrameT:
        """Return a DataFrame in the configured backend."""
        df = pl.DataFrame(data=data, schema=schema)
        return _to_backend(df, self._backend)

    def _scrape_schedule(
        self,
        teams: list[str] | str | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> None:
        """Scrape every game type in each team's schedule from the NHL API.

        For more information and usage, see
        https://docs.chickenstats.com/contribute/

        Examples:
            First, instantiate the Season object
            >>> season = Season(2023)

            Before scraping the data, the storage objects are empty
            >>> season.schedule()  # Returns an empty DataFrame

            You can use the `_scrape_schedule` method to get any data
            >>> season._scrape_schedule()  # Scrapes all teams, all games available
            >>> season._schedule  # Returns schedule
        """
        with ChickenProgress(disable=disable_progress_bar, transient=transient_progress_bar) as progress:
            if teams is None:
                schedule_teams = self.teams

            elif isinstance(teams, str):
                schedule_teams = convert_to_list(obj=teams, object_type="team codes")

            else:
                schedule_teams = teams.copy()

            pbar_stub = f"{self._season_str} schedule information"
            pbar_message = f"Downloading {self._season_str} schedule information..."

            sched_task = progress.add_task(pbar_message, total=len(schedule_teams))

            for team in schedule_teams:
                if team not in self._scraped_schedule_teams:
                    url = f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{self.season}"

                    raw_response = self._requests_session.get(url)
                    raw_response.raise_for_status()
                    response = raw_response.json()
                    games = self._munge_schedule(
                        [x for x in response["games"] if x["id"] not in self._scraped_schedule]
                    )
                    self._schedule.extend(games)
                    self._scraped_schedule.extend(x["game_id"] for x in games)
                    self._scraped_schedule_teams.append(team)

                if team != schedule_teams[-1]:
                    pbar_message = f"Downloading {pbar_stub} for {team}..."
                else:
                    pbar_message = f"Finished downloading {pbar_stub}"
                progress.update(sched_task, description=pbar_message, advance=1, refresh=True)

    @staticmethod
    def _munge_schedule(games: list[dict]) -> list[dict]:
        """Munge every game in a schedule from the NHL API, whatever its game type. Called from `_scrape_schedule`.

        For more information and usage, see
        https://docs.chickenstats.com/contribute/
        """
        returned_games = []

        for game in games:
            local_time = ZoneInfo(game["venueTimezone"])

            if "Z" in game["startTimeUTC"]:
                game["startTimeUTC"] = game["startTimeUTC"][:-1] + "+00:00"

            start_time_utc_dt: dt = dt.fromisoformat(game["startTimeUTC"])
            game_date_dt: dt = start_time_utc_dt.astimezone(local_time)

            start_time = game_date_dt.strftime("%H:%M")
            game_date = game_date_dt.strftime("%Y-%m-%d")

            game_info = {
                "season": game["season"],
                # Null for a game type outside every session, e.g., the All-Star Game
                "session": _GAME_TYPE_SESSIONS.get(game["gameType"]),
                "game_type": game["gameType"],
                "game_id": game["id"],
                "game_date": game_date,
                "start_time": start_time,
                "game_state": game["gameState"],
                "home_team": game["homeTeam"]["abbrev"],
                "home_team_id": game["homeTeam"]["id"],
                # A game that has not started has no score, not 0-0
                "home_score": game["homeTeam"].get("score"),
                "away_team": game["awayTeam"]["abbrev"],
                "away_team_id": game["awayTeam"]["id"],
                "away_score": game["awayTeam"].get("score"),
                "venue": game["venue"]["default"].upper(),
                "venue_timezone": game["venueTimezone"],
                "neutral_site": int(game["neutralSite"]),
                # Naive local time; venue_timezone names the zone
                "game_date_dt_local": game_date_dt.replace(tzinfo=None),
                "game_date_dt_utc": start_time_utc_dt,
                "tv_broadcasts": game["tvBroadcasts"],
                "home_logo": game["homeTeam"].get("logo"),
                "home_logo_dark": game["homeTeam"].get("darkLogo"),
                "away_logo": game["awayTeam"].get("logo"),
                "away_logo_dark": game["awayTeam"].get("darkLogo"),
            }

            returned_games.append(ScheduleGame.model_validate(game_info).model_dump())

        return returned_games

    @shared_doc(_SEASON_SCHEDULE_DOC)
    def schedule(
        self,
        teams: list[str] | str | None = None,
        *,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> FrameT:
        """Schedule — docstring lives in _docstrings._SEASON_SCHEDULE_DOC."""
        if not teams:
            schedule_teams = self.teams

        else:
            schedule_teams = [team.upper() for team in convert_to_list(teams, object_type="team codes")]
            unknown = [team for team in schedule_teams if team not in self.teams]
            if unknown:
                raise InvalidTeamError(
                    f"{', '.join(unknown)} did not play in {self._season_str}; the teams that did are "
                    f"{', '.join(self.teams)}",
                    team_code=unknown[0],
                )

        session_codes = _session_codes(sessions)

        scrape_teams = [x for x in schedule_teams if x not in self._scraped_schedule_teams]

        if scrape_teams:
            self._scrape_schedule(
                teams=scrape_teams,
                disable_progress_bar=disable_progress_bar,
                transient_progress_bar=transient_progress_bar,
            )

        return_list = [
            x
            for x in self._schedule
            if x["game_type"] in session_codes
            and (x["home_team"] in schedule_teams or x["away_team"] in schedule_teams)
        ]

        return_list = sorted(return_list, key=lambda x: (x["game_date_dt_utc"], x["game_id"]))

        df = self._finalize_dataframe(data=return_list, schema=schedule_polars_schema)

        return df

    def _scrape_standings(self):
        """Scrape standings from NHL API endpoint.

        Examples:
            First, instantiate the Season object
            >>> season = Season(2023)

            Before scraping the data, any of the storage objects are None
            >>> season._standings  # Returns an empty list

            You can use the `_scrape_standings` method to get any data
            >>> season._scrape_standings()  # Scrapes all teams, all games available
            >>> season._standings  # Returns raw standings data

            However, then need to manually clean the data
            >>> season._munge_standings()
            >>> season._standings  # Returns standings data
        """
        url = f"https://api-web.nhle.com/v1/standings/{self.standings_date}"

        response = self._requests_session.get(url)
        response.raise_for_status()
        r = response.json()

        self._standings = r["standings"]

    def _munge_standings(self):
        """Munge standings from the NHL API.

        Examples:
            First, instantiate the Season object
            >>> season = Season(2023)

            Before scraping the data, any of the storage objects are None
            >>> season._standings  # Returns an empty list

            You can use the `_scrape_standings` method to get any data
            >>> season._scrape_standings()  # Scrapes all teams, all games available
            >>> season._standings  # Returns raw standings data

            However, then need to manually clean the data
            >>> season._munge_standings()
            >>> season._standings  # Returns standings data
        """
        final_standings = []

        for team in self._standings:
            team_data = {
                field: team.get(key, _STANDINGS_DEFAULTS.get(field)) for field, key in _STANDINGS_FIELDS.items()
            }
            team_data["team_name"] = team["teamName"]["default"]
            team_data["team"] = team["teamAbbrev"]["default"]

            final_standings.append(StandingsTeam.model_validate(team_data).model_dump())

        self._standings = final_standings

    @property
    @shared_doc(_SEASON_STANDINGS_DOC)
    def standings(self) -> FrameT:
        """Standings — docstring lives in _docstrings._SEASON_STANDINGS_DOC."""
        if not self._standings:
            self._scrape_standings()
            self._munge_standings()

        df = self._finalize_dataframe(data=self._standings, schema=standings_polars_schema)

        return df


@overload
def multi_season_schedule(
    years: list[str | int | float] | range | str | int | float,
    *,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: PolarsBackend = "polars",
    disable_progress_bar: bool = False,
    requests_session: ChickenSession | None = None,
) -> pl.DataFrame: ...
@overload
def multi_season_schedule(
    years: list[str | int | float] | range | str | int | float,
    *,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: PandasBackend,
    disable_progress_bar: bool = False,
    requests_session: ChickenSession | None = None,
) -> pd.DataFrame: ...
@overload
def multi_season_schedule(
    years: list[str | int | float] | range | str | int | float,
    *,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: PyarrowBackend,
    disable_progress_bar: bool = False,
    requests_session: ChickenSession | None = None,
) -> pa.Table: ...
@overload
def multi_season_schedule(
    years: list[str | int | float] | range | str | int | float,
    *,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: NarwhalsBackend,
    disable_progress_bar: bool = False,
    requests_session: ChickenSession | None = None,
) -> NarwhalsFrame: ...
@overload
def multi_season_schedule(
    years: list[str | int | float] | range | str | int | float,
    *,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: AnyBackend = "polars",
    disable_progress_bar: bool = False,
    requests_session: ChickenSession | None = None,
) -> Any: ...
def multi_season_schedule(
    years: list[str | int | float] | range | str | int | float,
    *,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
    disable_progress_bar: bool = False,
    requests_session: ChickenSession | None = None,
) -> Any:
    """Scrapes and combines the schedule across multiple seasons.

    Convenience wrapper around instantiating a ``Season`` per year and calling
    ``.schedule()`` on each — avoids the boilerplate of looping manually and
    concatenating game IDs yourself when working across several seasons.

    Parameters:
        years (list[str | int | float] | range | str | int | float):
            One year identifier per season to scrape, in any format accepted by
            ``Season.__init__`` (4-digit or 8-digit), e.g., ``[2021, 2022, 2023]``,
            ``range(2021, 2024)`` or a single year.
        teams (list[str] | str | None):
            Three-letter team's schedule to scrape, e.g., NSH. Applied to every season; a team
            is skipped, with a warning, in a season it did not play.
        sessions (list[str] | str | None):
            Whether to scrape regular season ("R"), playoffs ("P"), pre-season ("PR"),
            or 4 Nations Face Off ("FO"). If left blank, scrapes regular season and playoffs.
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            DataFrame backend for the returned data. One of ``"polars"`` (default),
            ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.
        disable_progress_bar (bool):
            Whether to disable the progress bar for each season's scrape.
        requests_session (ChickenSession | None):
            ChickenSession to use for requests, e.g., with a custom user agent. Defaults to a new ChickenSession.

    Returns:
        DataFrameT: Combined schedule across all requested seasons — same columns as
            ``Season.schedule()``, spanning multiple ``season`` values.

    Examples:
        Scrape the last three seasons for a single team
        >>> from chickenstats.chicken_nhl import multi_season_schedule
        >>> schedule = multi_season_schedule([2021, 2022, 2023], teams="NSH")
        >>> game_ids = schedule["game_id"].to_list()
    """
    _validate_backend(backend)

    if isinstance(years, str | int | float):
        years = [years]
    team_list = [team.upper() for team in convert_to_list(teams, object_type="team codes")] if teams else None
    requests_session = requests_session or ChickenSession()

    frames = []

    for year in years:
        first_year = int(str(int(year))[:4])
        if first_year in _CANCELED_SEASONS:
            warnings.warn(f"Skipping {first_year}: {_CANCELED_SEASONS[first_year]}", UserWarning, stacklevel=2)
            continue
        season = Season(year, backend="polars", requests_session=requests_session)

        season_teams = None
        if team_list:
            season_teams = [team for team in team_list if team in season.teams]
            skipped = [team for team in team_list if team not in season_teams]
            if skipped:
                warnings.warn(
                    f"Skipping {', '.join(skipped)} in {season._season_str}, which they did not play",
                    UserWarning,
                    stacklevel=2,
                )
            if not season_teams:
                continue

        season_schedule = season.schedule(
            teams=season_teams, sessions=sessions, disable_progress_bar=disable_progress_bar
        )
        frames.append(season_schedule)

    if team_list and not frames:
        raise InvalidTeamError(
            f"{', '.join(team_list)} did not play in any of the seasons requested", team_code=team_list[0]
        )

    combined = pl.concat(frames) if frames else pl.DataFrame(schema=schedule_polars_schema)

    return _to_backend(combined, backend)


def _teams_with_partial_schedules(long_df: pl.DataFrame) -> list[str]:
    """The teams with under half the regular-season games of the busiest team in a season.

    The playoffs are left out, since a team knocked out early plays far fewer games than the champion.
    """
    games = long_df.filter(pl.col("session") == "R") if "session" in long_df.columns else long_df
    keys = ["season"] if "season" in long_df.columns else [pl.lit(0).alias("season")]
    counts = games.group_by(*keys, "team").len()

    return sorted(counts.filter(pl.col("len") * 2 < pl.col("len").max().over("season"))["team"].unique())


@overload
def add_schedule_context(schedule: InputFrameT, *, backend: None = None) -> InputFrameT: ...
@overload
def add_schedule_context(schedule: DataFrameT, *, backend: PolarsBackend) -> pl.DataFrame: ...
@overload
def add_schedule_context(schedule: DataFrameT, *, backend: PandasBackend) -> pd.DataFrame: ...
@overload
def add_schedule_context(schedule: DataFrameT, *, backend: PyarrowBackend) -> pa.Table: ...
@overload
def add_schedule_context(schedule: DataFrameT, *, backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def add_schedule_context(schedule: DataFrameT, *, backend: AnyBackend | None = None) -> Any: ...
def add_schedule_context(
    schedule: DataFrameT, *, backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] | None = None
) -> Any:
    """Add rest-day and back-to-back context for each team in a schedule.

    Returns a long-format DataFrame keyed on ``(game_id, team)`` — one row per team per
    game, twice as many rows as the input schedule — rather than adding `home_*`/`away_*`
    -suffixed columns to the wide schedule shape. Join it back onto `game_id`/`team` (or
    `game_id`/`home_team`/`away_team`) to attach context to play-by-play or stats output.

    Rest days are the number of calendar days since that team's previous game found
    anywhere in ``schedule``, so a team's first game in the input has null rest days (no
    earlier game to diff against) — if ``schedule`` spans multiple seasons (e.g.
    ``multi_season_schedule()`` output), a season opener's rest days reflect the (large)
    gap since the prior season's last game rather than being null.

    A team's rest is only right when all of its games are in ``schedule``. ``Season.schedule("NSH")``
    holds every Nashville game but only a few of each opponent's, so their rest days are too long
    and their back-to-backs are missed. A warning names how many teams this affects.

    Strength-of-schedule (e.g. opponent quality) is out of scope here — it needs a
    "team strength" metric that isn't buildable from schedule data alone.

    Parameters:
        schedule (DataFrameT): Schedule DataFrame from ``Season.schedule()`` or
            ``multi_season_schedule()`` (or any DataFrame with ``game_id``, ``game_date``,
            ``home_team``, ``away_team`` columns).
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] | None):
            Output backend. Defaults to the input ``schedule``'s own backend.

    Returns:
        DataFrameT: Long-format DataFrame with columns ``game_id``, ``season``,
            ``session``, ``game_date``, ``team``, ``opp_team``, ``home_away``,
            ``rest_days``, ``back_to_back``.

    Warns:
        UserWarning: If a team has under half the regular-season games of the busiest team in a
            season, which means the schedule does not hold all of its games.

    Examples:
        >>> import polars as pl
        >>> from chickenstats.chicken_nhl import Season, add_schedule_context
        >>> schedule = Season(2023).schedule()
        >>> context = add_schedule_context(schedule)
        >>> nsh_context = context.filter(pl.col("team") == "NSH")
    """
    output_backend = _validate_backend(backend or _detect_backend(schedule))
    df = _to_polars(schedule)

    keep_cols = [c for c in ("season", "session", "game_id", "game_date") if c in df.columns]

    home = df.select(
        *keep_cols,
        pl.col("home_team").alias("team"),
        pl.col("away_team").alias("opp_team"),
        pl.lit("home").alias("home_away"),
    )
    away = df.select(
        *keep_cols,
        pl.col("away_team").alias("team"),
        pl.col("home_team").alias("opp_team"),
        pl.lit("away").alias("home_away"),
    )

    long_df = pl.concat([home, away]).sort(["team", "game_date", "game_id"])

    partial = _teams_with_partial_schedules(long_df)
    if partial:
        warnings.warn(
            f"The schedule looks incomplete for {len(partial)} teams, such as {partial[0]}, so their rest days "
            "are too long. Pass every team's games to get their rest right.",
            UserWarning,
            stacklevel=2,
        )

    long_df = long_df.with_columns(pl.col("game_date").str.to_date().alias("_game_date_parsed"))
    long_df = long_df.with_columns(
        (pl.col("_game_date_parsed") - pl.col("_game_date_parsed").shift(1).over("team"))
        .dt.total_days()
        .alias("rest_days")
    ).drop("_game_date_parsed")
    long_df = long_df.with_columns((pl.col("rest_days") == 1).alias("back_to_back"))

    return _to_backend(long_df, output_backend)
