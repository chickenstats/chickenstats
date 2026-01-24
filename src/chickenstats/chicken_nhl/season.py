from datetime import datetime as dt
from typing import Literal

import pandas as pd
import polars as pl
import pytz

from chickenstats.chicken_nhl._helpers import convert_to_list

# These are dictionaries of names that are used throughout the module
from chickenstats.chicken_nhl._validation import (
    ScheduleGame,
    ScheduleSchemaPolars,
    StandingsTeam,
    StandingsSchemaPolars,
)
from chickenstats.utilities.utilities import ChickenProgress, ChickenSession
from chickenstats.chicken_nhl._info import regular_season_end_dates

from fake_useragent import UserAgent

# Setting up the fake user agent list
browsers = ["Google", "Chrome", "Firefox", "Edge", "Opera", "Safari", "Android", "Yandex Browser", "Samsung Internet"]
ua = UserAgent()


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
        backend: Literal["pandas", "polars"] = "polars",
    ):
        """Instantiates a Season object for a given year."""
        self._backend = backend

        if len(str(year)) == 8:
            self.season = int(year)

        elif len(str(year)) == 4:
            self.season = int(f"{year}{int(year) + 1}")

        first_year = int(str(self.season)[0:4])

        teams_1917 = ["MTL", "MWN", "SEN"]  # "TAN"]

        teams_1918 = ["MTL", "SEN", "TAN"]

        teams_1919 = ["MTL", "QBD", "SEN", "TSP"]

        teams_1920 = ["HAM", "MTL", "SEN", "TSP"]

        teams_1924 = ["BOS", "HAM", "MMR", "MTL", "SEN", "TSP"]

        teams_1925 = ["BOS", "MMR", "MTL", "NYA", "PIR", "SEN", "TSP"]

        teams_1926 = ["BOS", "CHI", "DCG", "MMR", "MTL", "NYA", "NYR", "PIR", "SEN", "TSP"]

        teams_1927 = ["BOS", "CHI", "DCG", "MMR", "MTL", "NYA", "NYR", "PIR", "SEN", "TOR"]

        teams_1930 = ["BOS", "CHI", "DFL", "MMR", "MTL", "NYA", "NYR", "QUA", "SEN", "TOR"]

        teams_1931 = ["BOS", "CHI", "DFL", "MMR", "MTL", "NYA", "NYR", "TOR"]

        teams_1932 = ["BOS", "CHI", "DET", "MMR", "MTL", "NYA", "NYR", "SEN", "TOR"]

        teams_1934 = ["BOS", "CHI", "DET", "MMR", "MTL", "NYA", "NYR", "SLE", "TOR"]

        teams_1935 = ["BOS", "CHI", "DET", "MMR", "MTL", "NYA", "NYR", "TOR"]

        teams_1938 = ["BOS", "CHI", "DET", "MTL", "NYA", "NYR", "TOR"]

        teams_1941 = ["BOS", "BRK", "CHI", "DET", "MTL", "NYR", "TOR"]

        teams_1942 = ["BOS", "CHI", "DET", "MTL", "NYR", "TOR"]

        teams_1967 = ["BOS", "CHI", "DET", "LAK", "MNS", "MTL", "NYR", "OAK", "PHI", "PIT", "STL", "TOR"]

        teams_1970 = ["BOS", "BUF", "CGS", "CHI", "DET", "LAK", "MNS", "MTL", "NYR", "PHI", "PIT", "STL", "TOR", "VAN"]

        teams_1972 = [
            "AFM",
            "BOS",
            "BUF",
            "CGS",
            "CHI",
            "DET",
            "LAK",
            "MNS",
            "MTL",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "STL",
            "TOR",
            "VAN",
        ]

        teams_1974 = [
            "AFM",
            "BOS",
            "BUF",
            "CGS",
            "CHI",
            "DET",
            "KCS",
            "LAK",
            "MNS",
            "MTL",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "STL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_1976 = [
            "AFM",
            "BOS",
            "BUF",
            "CHI",
            "CLE",
            "CLR",
            "DET",
            "LAK",
            "MNS",
            "MTL",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "STL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_1978 = [
            "AFM",
            "BOS",
            "BUF",
            "CHI",
            "CLR",
            "DET",
            "LAK",
            "MNS",
            "MTL",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "STL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_1979 = [
            "AFM",
            "BOS",
            "BUF",
            "CHI",
            "CLR",
            "DET",
            "EDM",
            "HFD",
            "LAK",
            "MNS",
            "MTL",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "QUE",
            "STL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1980 = [
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "CLR",
            "DET",
            "EDM",
            "HFD",
            "LAK",
            "MNS",
            "MTL",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "QUE",
            "STL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1982 = [
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "DET",
            "EDM",
            "HFD",
            "LAK",
            "MNS",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "QUE",
            "STL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1991 = [
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "DET",
            "EDM",
            "HFD",
            "LAK",
            "MNS",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "PHI",
            "PIT",
            "QUE",
            "SJS",
            "STL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1992 = [
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "DET",
            "EDM",
            "HFD",
            "LAK",
            "MNS",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "QUE",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1993 = [
            "ANA",
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "HFD",
            "LAK",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "QUE",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1995 = [
            "ANA",
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "HFD",
            "LAK",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WIN",
            "WSH",
        ]

        teams_1996 = [
            "ANA",
            "BOS",
            "BUF",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "HFD",
            "LAK",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PHX",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_1997 = [
            "ANA",
            "BOS",
            "BUF",
            "CAR",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MTL",
            "NJD",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PHX",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_1998 = [
            "ANA",
            "BOS",
            "BUF",
            "CAR",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PHX",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_1999 = [
            "ANA",
            "ATL",
            "BOS",
            "BUF",
            "CAR",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PHX",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_2000 = [
            "ANA",
            "ATL",
            "BOS",
            "BUF",
            "CAR",
            "CBJ",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MIN",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PHX",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WSH",
        ]

        teams_2011 = [
            "ANA",
            "BOS",
            "BUF",
            "CAR",
            "CBJ",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MIN",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PHX",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WPG",
            "WSH",
        ]

        teams_2014 = [
            "ANA",
            "ARI",
            "BOS",
            "BUF",
            "CAR",
            "CBJ",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MIN",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "WPG",
            "WSH",
        ]

        teams_2017 = [
            "ANA",
            "ARI",
            "BOS",
            "BUF",
            "CAR",
            "CBJ",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MIN",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "VGK",
            "WPG",
            "WSH",
        ]

        teams_2021 = [
            "ANA",
            "ARI",
            "BOS",
            "BUF",
            "CAR",
            "CBJ",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FLA",
            "LAK",
            "MIN",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "SEA",
            "SJS",
            "STL",
            "TBL",
            "TOR",
            "VAN",
            "VGK",
            "WPG",
            "WSH",
        ]

        teams_2024 = [
            "ANA",
            "BOS",
            "BUF",
            "CAN",
            "CAR",
            "CBJ",
            "CGY",
            "CHI",
            "COL",
            "DAL",
            "DET",
            "EDM",
            "FIN",
            "FLA",
            "LAK",
            "MIN",
            "MTL",
            "NJD",
            "NSH",
            "NYI",
            "NYR",
            "OTT",
            "PHI",
            "PIT",
            "SEA",
            "SJS",
            "SWE",
            "STL",
            "TBL",
            "TOR",
            "USA",
            "UTA",
            "VAN",
            "VGK",
            "WPG",
            "WSH",
        ]

        self._teams_dict = {
            1917: teams_1917,
            1918: teams_1918,
            1919: teams_1919,
            1920: teams_1920,
            1921: teams_1920,
            1922: teams_1920,
            1923: teams_1920,
            1924: teams_1924,
            1925: teams_1925,
            1926: teams_1926,
            1927: teams_1927,
            1928: teams_1927,
            1929: teams_1927,
            1930: teams_1930,
            1931: teams_1931,
            1932: teams_1932,
            1933: teams_1932,
            1934: teams_1934,
            1935: teams_1935,
            1936: teams_1935,
            1937: teams_1935,
            1938: teams_1938,
            1939: teams_1938,
            1940: teams_1938,
            1941: teams_1941,
            1942: teams_1942,
            1943: teams_1942,
            1944: teams_1942,
            1945: teams_1942,
            1946: teams_1942,
            1947: teams_1942,
            1948: teams_1942,
            1949: teams_1942,
            1950: teams_1942,
            1951: teams_1942,
            1952: teams_1942,
            1953: teams_1942,
            1954: teams_1942,
            1955: teams_1942,
            1956: teams_1942,
            1957: teams_1942,
            1958: teams_1942,
            1959: teams_1942,
            1960: teams_1942,
            1961: teams_1942,
            1962: teams_1942,
            1963: teams_1942,
            1964: teams_1942,
            1965: teams_1942,
            1966: teams_1942,
            1967: teams_1967,
            1968: teams_1967,
            1969: teams_1967,
            1970: teams_1970,
            1971: teams_1970,
            1972: teams_1972,
            1973: teams_1972,
            1974: teams_1974,
            1975: teams_1974,
            1976: teams_1976,
            1977: teams_1976,
            1978: teams_1978,
            1979: teams_1979,
            1980: teams_1980,
            1981: teams_1980,
            1982: teams_1982,
            1983: teams_1982,
            1984: teams_1982,
            1985: teams_1982,
            1986: teams_1982,
            1987: teams_1982,
            1988: teams_1982,
            1989: teams_1982,
            1990: teams_1982,
            1991: teams_1991,
            1992: teams_1992,
            1993: teams_1993,
            1994: teams_1993,
            1995: teams_1995,
            1996: teams_1996,
            1997: teams_1997,
            1998: teams_1998,
            1999: teams_1999,
            2000: teams_2000,
            2001: teams_2000,
            2002: teams_2000,
            2003: teams_2000,
            2004: teams_2000,
            2005: teams_2000,
            2006: teams_2000,
            2007: teams_2000,
            2008: teams_2000,
            2009: teams_2000,
            2010: teams_2000,
            2011: teams_2011,
            2012: teams_2011,
            2013: teams_2011,
            2014: teams_2014,
            2015: teams_2014,
            2016: teams_2014,
            2017: teams_2017,
            2018: teams_2017,
            2019: teams_2017,
            2020: teams_2017,
            2021: teams_2021,
            2022: teams_2021,
            2023: teams_2021,
            2024: teams_2024,
            2025: teams_2024,
        }

        self.teams = self._teams_dict.get(first_year)

        if not self.teams:
            if first_year != list(self._teams_dict)[-1] + 1:
                raise Exception(f"{first_year} IS NOT SUPPORTED")

        self._schedule = []

        self._scraped_schedule_teams = []

        self._scraped_schedule = []

        self._standings = []

        self._requests_session = ChickenSession()

        self._season_str = str(self.season)[:4] + "-" + str(self.season)[6:8]

        self.random_user_agent = {"User-Agent": ua.random}

        if self.season == 20252026:
            self.standings_date = "now"

        elif not standings_date:
            self.standings_date = regular_season_end_dates[int(str(self.season)[:4])]

        else:
            self.standings_date = standings_date

    def _finalize_dataframe(self, data, schema):
        """Method to return a pandas or polars dataframe, depending on user preference."""
        if self._backend == "polars":
            df = pl.DataFrame(data=data, schema=schema)

        if self._backend == "pandas":
            df = pd.DataFrame(data)

        return df

    def _scrape_schedule(
        self, teams: list[str] | str | None = None, sessions: list[str] | str | None = None, disable_progress_bar=False
    ) -> None:
        """Method to scrape the schedule from NHL API endpoint.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Season object
            >>> season = Season(2023)

            Before scraping the data, any of the storage objects are None
            >>> season.schedule  # Returns an empty list

            You can use the `_scrape_schedule` method to get any data
            >>> season._scrape_schedule()  # Scrapes all teams, all games available
            >>> season._schedule  # Returns schedule
        """
        schedule_list = []

        if teams not in self._scraped_schedule_teams:
            with self._requests_session as s:
                with ChickenProgress(disable=disable_progress_bar) as progress:
                    if isinstance(teams, str):
                        schedule_teams = convert_to_list(obj=teams, object_type="team codes")

                    elif isinstance(teams, list):
                        schedule_teams = teams.copy()

                    pbar_stub = f"{self._season_str} schedule information"
                    pbar_message = f"Downloading {self._season_str} schedule information..."

                    sched_task = progress.add_task(pbar_message, total=len(schedule_teams))

                    for team in schedule_teams:
                        if team in self._scraped_schedule_teams:  # Not covered by tests
                            if team != schedule_teams[-1]:
                                pbar_message = f"Downloading {pbar_stub} for {team}..."
                            else:
                                pbar_message = f"Finished downloading {pbar_stub}"
                            progress.update(sched_task, description=pbar_message, advance=1, refresh=True)

                            continue

                        url = f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{self.season}"

                        response = s.get(url, headers=self.random_user_agent).json()
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
                session_dict = {"PR": 1, "R": 2, "P": 3, "FO": 19}

                if isinstance(sessions, list):
                    session_codes = [session_dict[x] for x in sessions]

                if isinstance(sessions, str):
                    session_codes = [session_dict[sessions]]

                if int(game["gameType"]) not in session_codes:
                    continue

            local_time = pytz.timezone(game["venueTimezone"])

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
    ) -> pd.DataFrame:
        # noinspection GrazieInspection
        """Scrapes NHL schedule. Can return whole or season or subset of teams' schedules.

        Parameters:
            teams (list[str] | str | None):
                Three-letter team's schedule to scrape, e.g., NSH
            sessions: (list[str] | str | None):
                Whether to scrape regular season ("R"), playoffs ("P"), pre-season ("PR"),
                 or 4 Nations Face Off ("FO"). If left blank, scrapes regular season and playoffs
            disable_progress_bar (bool):
                Whether to disable progress bar

        Returns:
            season (int):
                8-digit season identifier, e.g., 20232024
            session (int):
                Type of game played - pre-season (1), regular season (2), or playoffs (3), e.g., 2
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

        scrape_teams = [x for x in schedule_teams if x not in self._scraped_schedule_teams]

        if scrape_teams:
            self._scrape_schedule(teams=scrape_teams, sessions=sessions, disable_progress_bar=disable_progress_bar)

        return_list = [
            x for x in self._schedule if x["home_team"] in schedule_teams or x["away_team"] in schedule_teams
        ]

        return_list = sorted(return_list, key=lambda x: (x["game_date_dt_utc"], x["game_id"]))

        df = self._finalize_dataframe(data=return_list, schema=ScheduleSchemaPolars)

        return df

    def _scrape_standings(self):
        """Scrape standings from NHL API endpoint.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

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

        with self._requests_session as s:
            r = s.get(url, headers=self.random_user_agent).json()

        self._standings = r["standings"]

    def _munge_standings(self):
        """Function to munge standings from NHL API endpoint.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

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
    def standings(self):
        """Pandas DataFrame of the standings from the NHL API.

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

        df = self._finalize_dataframe(data=self._standings, schema=StandingsSchemaPolars)

        return df
