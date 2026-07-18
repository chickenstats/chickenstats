from __future__ import annotations

from datetime import datetime as dt
from typing import Literal
from zoneinfo import ZoneInfo

import polars as pl

from chickenstats.utilities.utilities import convert_to_list
from chickenstats.exceptions import InvalidSeasonError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.types import DataFrameT

# These are dictionaries of names that are used throughout the module
from chickenstats.chicken_nhl.validation_pydantic import ScheduleGame, StandingsTeam
from chickenstats.chicken_nhl.validation_polars import schedule_polars_schema, standings_polars_schema
from chickenstats.utilities.utilities import ChickenProgress, ChickenSession, _to_backend
from chickenstats.chicken_nhl._season_constants import regular_season_end_dates, _TEAMS_BY_YEAR

_SESSION_CODES: dict[str, int] = {"PR": 1, "R": 2, "P": 3, "FO": 19}


class Season:
    """Scrapes schedule and standings data.

    Helpful for pulling game IDs and scraping programmatically.

    Parameters:
        year (int or float or str):
            4-digit year identifier, the first year in the season, e.g., 2023
        standings_date (str | None):
            Scrapes the standings as of the given date. Format like YYYY-MM-DD
            (%Y-%m-%d in datetime formating). For the current season, defaults to the
            current date
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            DataFrame backend for all returned data. One of ``"polars"`` (default),
            ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.

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

    def __init__(
        self,
        year: str | int | float,
        standings_date: str | None = None,
        backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
    ):
        """Instantiates a Season object for a given year."""
        self._backend = backend

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

        self.teams = _TEAMS_BY_YEAR.get(first_year)

        if not self.teams:
            min_year, max_year = min(_TEAMS_BY_YEAR), max(_TEAMS_BY_YEAR)
            raise InvalidSeasonError(
                f"{first_year} is not a supported season year — supported range is {min_year}-{max_year}.",
                season=first_year,
            )

        self._schedule = []
        self._scraped_schedule_teams = []
        self._scraped_schedule = []
        self._standings = []
        self._requests_session = ChickenSession()
        self._season_str = str(self.season)[:4] + "-" + str(self.season)[6:8]

        if self.season == 20252026:
            self.standings_date = "now"
        elif not standings_date:
            self.standings_date = regular_season_end_dates[first_year]
        else:
            self.standings_date = standings_date

    def __repr__(self) -> str:
        """Return string representation of Season object."""
        return f"Season(season={self.season!r}, backend={self._backend!r})"

    def _finalize_dataframe(self, data, schema) -> DataFrameT:
        """Method to return a pandas or polars dataframe, depending on user preference."""
        df = pl.DataFrame(data=data, schema=schema)
        return _to_backend(df, self._backend)

    def _scrape_schedule(
        self,
        teams: list[str] | str | None = None,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> None:
        """Method to scrape the schedule from NHL API endpoint.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Season object
            >>> season = Season(2023)

            Before scraping the data, the storage objects are empty
            >>> season.schedule()  # Returns an empty DataFrame

            You can use the `_scrape_schedule` method to get any data
            >>> season._scrape_schedule()  # Scrapes all teams, all games available
            >>> season._schedule  # Returns schedule
        """
        schedule_list = []

        if teams not in self._scraped_schedule_teams:
            with ChickenProgress(disable=disable_progress_bar, transient=transient_progress_bar) as progress:
                if isinstance(teams, str):
                    schedule_teams = convert_to_list(obj=teams, object_type="team codes")

                elif isinstance(teams, list):
                    schedule_teams = teams.copy()

                pbar_stub = f"{self._season_str} schedule information"
                pbar_message = f"Downloading {self._season_str} schedule information..."

                sched_task = progress.add_task(pbar_message, total=len(schedule_teams))

                for team in schedule_teams:
                    if team in self._scraped_schedule_teams:
                        if team != schedule_teams[-1]:
                            pbar_message = f"Downloading {pbar_stub} for {team}..."
                        else:
                            pbar_message = f"Finished downloading {pbar_stub}"
                        progress.update(sched_task, description=pbar_message, advance=1, refresh=True)

                        continue

                    url = f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{self.season}"

                    raw_response = self._requests_session.get(url)
                    raw_response.raise_for_status()
                    response = raw_response.json()
                    if response["games"]:
                        games = [x for x in response["games"] if x["id"] not in self._scraped_schedule]
                        games = self._munge_schedule(games, sessions)
                        schedule_list.extend(games)
                        self._scraped_schedule_teams.append(team)
                        self._scraped_schedule.extend(x["game_id"] for x in games)
                    if team != schedule_teams[-1]:
                        pbar_message = f"Downloading {pbar_stub} for {team}..."
                    else:
                        pbar_message = f"Finished downloading {pbar_stub}"
                    progress.update(sched_task, description=pbar_message, advance=1, refresh=True)

        schedule_list = sorted(schedule_list, key=lambda x: (x["game_date_dt_local"], x["game_id"]))

        self._schedule.extend(schedule_list)

    @staticmethod
    def _munge_schedule(games: list[dict], sessions: list[str] | str | None) -> list[dict]:
        """Method to munge the schedule from NHL API endpoint.

        Nested within `_scrape_schedule` method.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/
        """
        returned_games = []

        for game in games:
            if not sessions:
                if int(game["gameType"]) not in [2, 3]:
                    continue

            else:
                if isinstance(sessions, list):
                    session_codes = [_SESSION_CODES[x] for x in sessions]

                if isinstance(sessions, str):
                    session_codes = [_SESSION_CODES[sessions]]

                if int(game["gameType"]) not in session_codes:
                    continue

            local_time = ZoneInfo(game["venueTimezone"])

            if "Z" in game["startTimeUTC"]:
                game["startTimeUTC"] = game["startTimeUTC"][:-1] + "+00:00"

            start_time_utc_dt: dt = dt.fromisoformat(game["startTimeUTC"])
            game_date_dt: dt = start_time_utc_dt.astimezone(local_time)

            start_time = game_date_dt.strftime("%H:%M")
            game_date = game_date_dt.strftime("%Y-%m-%d")

            game_info = {
                "season": game["season"],
                "session": game["gameType"],
                "game_id": game["id"],
                "game_date": game_date,
                "start_time": start_time,
                "game_state": game["gameState"],
                "home_team": game["homeTeam"]["abbrev"],
                "home_team_id": game["homeTeam"]["id"],
                "home_score": game["homeTeam"].get("score", 0),
                "away_team": game["awayTeam"]["abbrev"],
                "away_team_id": game["awayTeam"]["id"],
                "away_score": game["awayTeam"].get("score", 0),
                "venue": game["venue"]["default"].upper(),
                "venue_timezone": game["venueTimezone"],
                "neutral_site": int(game["neutralSite"]),
                "game_date_dt_local": game_date_dt,
                "game_date_dt_utc": start_time_utc_dt,
                "tv_broadcasts": game["tvBroadcasts"],
                "home_logo": game["homeTeam"].get("logo"),
                "home_logo_dark": game["homeTeam"].get("darkLogo"),
                "away_logo": game["awayTeam"].get("logo"),
                "away_logo_dark": game["awayTeam"].get("darkLogo"),
            }

            returned_games.append(ScheduleGame.model_validate(game_info).model_dump())

        return returned_games

    def schedule(
        self,
        teams: list[str] | str | None = None,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = False,
        transient_progress_bar: bool = False,
    ) -> DataFrameT:
        # noinspection GrazieInspection
        """Scrapes NHL schedule. Can return whole or season or subset of teams' schedules.

        Parameters:
            teams (list[str] | str | None):
                Three-letter team's schedule to scrape, e.g., NSH
            sessions (list[str] | str | None):
                Whether to scrape regular season ("R"), playoffs ("P"), pre-season ("PR"),
                 or 4 Nations Face Off ("FO"). If left blank, scrapes regular season and playoffs
            disable_progress_bar (bool):
                Whether to disable progress bar
            transient_progress_bar (bool):
                If ``True``, clears the progress bar from the terminal after it completes.
                Default ``False``.

        Returns:
            season (int):
                8-digit season identifier, e.g., 20232024
            session (str):
                Type of game played — regular season (R), playoffs (P), pre-season (PR),
                or 4 Nations Face Off (FO), e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020015
            game_date (str):
                Date the game is played, in local time, e.g., 2023-10-12
            start_time (str):
                Start time for the game in the home time zone, in military time, e.g., 19:00
            game_state (str):
                Status of the game, whether official or future, e.g., OFF
            home_team (str):
                Three-letter code for the home team, e.g., NSH
            home_team_id (int):
                Two-digit code assigned to the home franchise by the NHL, e.g., 18
            home_score (int):
                Number of goals scored by the home team, e.g., 3
            away_team (str):
                Three-letter code for the away team, e.g., SEA
            away_team_id (int):
                Two-digit code assigned to the away franchise by the NHL, e.g., 55
            away_score (int):
                Number of goals scored by the away team, e.g., 0
            venue (str):
                Name of the venue where game is / was played, e.g., BRIDGESTONE ARENA
            venue_timezone (str):
                Name of the venue timezone, e.g., US/Central
            neutral_site (int):
                Whether game is / was played at a neutral site location, e.g., 0
            game_date_dt_local (dt.datetime):
                Game date as datetime object, e.g., 2023-10-12 19:00:00-05:00
            game_date_dt_utc (dt.datetime):
                Game date as datetime object, e.g., 2023-10-12 19:00:00-05:00
            tv_broadcasts (list):
                Where the game was broadcast, as a list of dictionaries, e.g., [{'id': 386, 'market': 'A',
                'countryCode': 'US', 'network': 'ROOT-NW', 'sequenceNumber': 65}, {'id': 375, 'market': 'H',
                'countryCode': 'US', 'network': 'BSSO', 'sequenceNumber': 70}]
            home_logo (str):
                URL for the home logo, e.g., https://assets.nhle.com/logos/nhl/svg/NSH_light.svg
            home_logo_dark (str):
                URL for the dark version of the home logo, e.g., https://assets.nhle.com/logos/nhl/svg/NSH_dark.svg
            away_logo (str):
                URL for the home logo, e.g., https://assets.nhle.com/logos/nhl/svg/TBL_light.svg
            away_logo_dark (str):
                URL for the dark version of the home logo, e.g., https://assets.nhle.com/logos/nhl/svg/TBL_dark.svg

        Examples:
            Scrape schedule for all teams
            >>> season = Season(2023)
            >>> schedule = season.schedule()

            Get schedule for a single team
            >>> schedule = season.schedule("NSH")

        """
        if not teams:
            schedule_teams = self.teams

        else:
            schedule_teams = convert_to_list(teams, "team codes")

        scrape_teams = [x for x in (schedule_teams or []) if x not in self._scraped_schedule_teams]

        if scrape_teams:
            self._scrape_schedule(
                teams=scrape_teams,
                sessions=sessions,
                disable_progress_bar=disable_progress_bar,
                transient_progress_bar=transient_progress_bar,
            )

        return_list = [
            x
            for x in self._schedule
            if x["home_team"] in (schedule_teams or []) or x["away_team"] in (schedule_teams or [])
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
        """Function to munge standings from NHL API endpoint.

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
                "conference": team.get("conferenceName"),
                "date": team.get("date"),
                "division": team.get("divisionName"),
                "games_played": team.get("gamesPlayed"),
                "goal_differential": team.get("goalDifferential"),
                "goal_differential_pct": team.get("goalDifferentialPctg", 0),
                "goals_against": team.get("goalAgainst"),
                "goals_for": team.get("goalFor"),
                "goals_for_pct": team.get("goalsForPctg", 0),
                "home_games_played": team.get("homeGamesPlayed"),
                "home_goal_differential": team.get("homeGoalDifferential"),
                "home_goals_against": team.get("homeGoalsAgainst"),
                "home_goals_for": team.get("homeGoalsFor"),
                "home_losses": team.get("homeLosses"),
                "home_ot_losses": team.get("homeOtLosses"),
                "home_points": team.get("homePoints"),
                "home_wins": team.get("homeWins"),
                "home_regulation_wins": team.get("homeRegulationWins"),
                "home_ties": team.get("homeTies"),
                "l10_goal_differential": team.get("l10GoalDifferential"),
                "l10_goals_against": team.get("l10GoalsAgainst"),
                "l10_goals_for": team.get("l10GoalsFor"),
                "l10_losses": team.get("l10Losses"),
                "l10_ot_losses": team.get("l10OtLosses"),
                "l10_points": team.get("l10Points"),
                "l10_regulation_wins": team.get("l10RegulationWins"),
                "l10_ties": team.get("l10Ties"),
                "l10_wins": team.get("l10Wins"),
                "losses": team.get("losses"),
                "ot_losses": team.get("otLosses"),
                "points_pct": team.get("pointPctg", 0),
                "points": team.get("points"),
                "regulation_win_pct": team.get("regulationWinPctg", 0),
                "regulation_wins": team.get("regulationWins"),
                "road_games_played": team.get("roadGamesPlayed"),
                "road_goal_differential": team.get("roadGoalDifferential"),
                "road_goals_against": team.get("roadGoalsAgainst"),
                "road_goals_for": team.get("roadGoalsFor"),
                "road_losses": team.get("roadLosses"),
                "road_ot_losses": team.get("roadOtLosses"),
                "road_points": team.get("roadPoints"),
                "road_regulation_wins": team.get("roadRegulationWins"),
                "road_ties": team.get("roadTies"),
                "road_wins": team.get("roadWins"),
                "season": team.get("seasonId"),
                "shootoutLosses": team.get("shootoutLosses"),
                "shootout_wins": team.get("shootoutWins"),
                "streak_code": team.get("streakCode", ""),
                "streak_count": team.get("streakCount", 0),
                "team_name": team["teamName"]["default"],
                "team": team["teamAbbrev"]["default"],
                "team_logo": team.get("teamLogo"),
                "ties": team.get("ties"),
                "waivers_sequence": team.get("waiversSequence"),
                "wildcard_sequence": team.get("wildcardSequence"),
                "win_pct": team.get("winPctg", 0),
                "wins": team.get("wins"),
            }

            final_standings.append(StandingsTeam.model_validate(team_data).model_dump())

        self._standings = final_standings

    @property
    def standings(self) -> DataFrameT:
        """Pandas or Polars DataFrame of the standings from the NHL API.

        Returns:
            season (int):
                8-digit season identifier, e.g., 20232024
            date (str):
                Date standings scraped, e.g., 2024-04-08
            team (str):
                Three-letter team code, e.g., NSH
            team_name (str):
                Full team name, e.g., Nashville Predators
            conference (str):
                Name of the conference in which the team plays, e.g., Western
            division (str):
                Name of the division in which the team plays, e.g., Central
            games_played (int):
                Number of games played, e.g., 78
            points (int):
                Number of points accumulated, e.g., 94
            points_pct (float):
                Points percentage, e.g., 0.602564
            wins (int):
                Number of wins, e.g., 45
            regulation_wins (int):
                Number of wins in regulation time, e.g., 36
            shootout_wins (int):
                Number of wins by shootout, e.g., 3
            losses (int):
                Number of losses, e.g., 29
            ot_losses (int):
                Number of losses in overtime play, e.g., 4
            shootout_losses (int | np.nan):
                Number of losses due during shootout, e.g., NaN
            ties (int):
                Number of ties, e.g., 0
            win_pct (float):
                Win percentage, e.g., 0.576923
            regulation_win_pct (float):
                Win percentage in regulation time, e.g., 0.461538
            streak_code (str):
                Whether streak is a winning or losing streak, e.g., W
            streak_count (int):
                Number of games won or lost, e.g., 1
            goals_for (int):
                Number of goals scored, e.g., 253
            goals_against (int):
                Number of goals against, e.g., 235
            goals_for_pct (float):
                Goals scored per game played, e.g., 3.24359
            goal_differential (int):
                Difference in goals scored and goals allowed, e.g., 18
            goal_differential_pct (float):
                Difference in goals scored and goals allowed as a percentage of...something, e.g., 0.230769
            home_games_played (int):
                Number of home games played, e.g., 39
            home_points (int):
                Number of home points accumulated, e.g., 45
            home_goals_for (int):
                Number of goals scored in home games, e.g., 126
            home_goals_against (int):
                Number of goals allowed in home games, e.g., 118
            home_goal_differential (int):
                Difference in home goals scored and home goals allowed, e.g., 8
            home_wins (int):
                Number of wins at home, e.g., 22
            home_losses (int):
                Number of losses at home, e.g., 16
            home_ot_losses (int):
                Number of home losses in overtime, e.g., 1
            home_ties (int):
                Number of ties at home, e.g., 0
            home_regulation_wins (int):
                Number of wins at home in regulation, e.g., 17
            road_games_played (int):
                Number of games played on the road, e.g., 39
            road_points (int):
                Number of points accumulated on the road, e.g., 49
            road_goals_for (int):
                Number of goals scored on the road, e.g., 127
            road_goals_against (int):
                Number of goals allowed on the road, e.g., 117
            road_goal_differential (int):
                Difference in goals scored and goals allowed on the road, e.g., 10
            road_wins (int):
                Number of wins on the road, e.g., 23
            road_losses (int):
                Number of losses on the road, e.g., 13
            road_ot_losses (int):
                Number of losses on the road in overtime, e.g., 3
            road_ties (int):
                Number of ties on the road, e.g., 0
            road_regulation_wins (int):
                Number of wins on the road in regulation, e.g., 19
            l10_points (int):
                Number of points accumulated in last ten games, e.g., 12
            l10_goals_for (int):
                Number of goals scored in last ten games, e.g., 34
            l10_goals_against (int):
                Number of goals allowed in last ten games, e.g., 31
            l10_goal_differential (int):
                Difference in goals scored and allowed in last ten games, e.g., 3
            l10_wins (int):
                Number of wins in last ten games, e.g., 6
            l10_losses (int):
                Number of losses in last ten games, e.g., 4
            l10_ot_losses (int):
                Number of losses in overtime in last ten games, e.g., 0
            l10_ties (int):
                Number of  ties in last ten games, e.g., 0
            l10_regulation_wins (int):
                Number of wins in regulation in last ten games, e.g., 4
            team_logo (str):
                URL for the team logo, e.g., https://assets.nhle.com/logos/nhl/svg/NSH_light.svg
            wildcard_sequence (int):
                Order for wildcard rankings, e.g., 1
            waivers_sequence (int):
                Order for waiver wire, e.g., 19

        Examples:
            >>> season = Season(2023)
            >>> standings = season.standings

        """
        if not self._standings:
            self._scrape_standings()
            self._munge_standings()

        df = self._finalize_dataframe(data=self._standings, schema=standings_polars_schema)

        return df


def multi_season_schedule(
    years: list[str | int | float] | range,
    teams: list[str] | str | None = None,
    sessions: list[str] | str | None = None,
    backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
    disable_progress_bar: bool = False,
) -> DataFrameT:
    """Scrapes and combines the schedule across multiple seasons.

    Convenience wrapper around instantiating a ``Season`` per year and calling
    ``.schedule()`` on each — avoids the boilerplate of looping manually and
    concatenating game IDs yourself when working across several seasons.

    Parameters:
        years (list[str | int | float] | range):
            One year identifier per season to scrape, in any format accepted by
            ``Season.__init__`` (4-digit or 8-digit), e.g., ``[2021, 2022, 2023]``
            or ``range(2021, 2024)``.
        teams (list[str] | str | None):
            Three-letter team's schedule to scrape, e.g., NSH. Applied to every season.
        sessions (list[str] | str | None):
            Whether to scrape regular season ("R"), playoffs ("P"), pre-season ("PR"),
            or 4 Nations Face Off ("FO"). If left blank, scrapes regular season and playoffs.
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]):
            DataFrame backend for the returned data. One of ``"polars"`` (default),
            ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.
        disable_progress_bar (bool):
            Whether to disable the progress bar for each season's scrape.

    Returns:
        DataFrameT: Combined schedule across all requested seasons — same columns as
            ``Season.schedule()``, spanning multiple ``season`` values.

    Examples:
        Scrape the last three seasons for a single team
        >>> from chickenstats.chicken_nhl import multi_season_schedule
        >>> schedule = multi_season_schedule([2021, 2022, 2023], teams="NSH")
        >>> game_ids = schedule["game_id"].to_list()
    """
    frames = []

    for year in years:
        season = Season(year, backend="polars")
        season_schedule = season.schedule(teams=teams, sessions=sessions, disable_progress_bar=disable_progress_bar)
        frames.append(season_schedule)

    combined = pl.concat(frames) if frames else pl.DataFrame(schema=schedule_polars_schema)

    return _to_backend(combined, backend)
