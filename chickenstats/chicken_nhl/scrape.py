import requests

from bs4 import BeautifulSoup

from datetime import datetime as dt
from datetime import timedelta, timezone
import pytz

import pandas as pd
import numpy as np
from requests.exceptions import RetryError
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)

from unidecode import unidecode
import re

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

# These are dictionaries of names that are used throughout the module
from chickenstats.chicken_nhl.info import (
    correct_names_dict,
    correct_api_names_dict,
    team_codes,
)
from chickenstats.chicken_nhl.fixes import (
    api_events_fixes,
    html_events_fixes,
    html_rosters_fixes,
)

from chickenstats.chicken_nhl.helpers import (
    s_session,
    hs_strip_html,  # from Harry Shromer's GitHub, lifted from Patrick Bacon
    convert_to_list,  # house-made for iterating
)


# Creating the game class
class Game:
    """
    Class instance for scraping play-by-play and other data for individual games. Utilized within Scraper.

    Parameters
    ----------
    game_id : int or float or str
        10-digit game identifier, e.g., 2023020001
    requests_session : requests.Session, optional
        If scraping multiple games, can provide single Session object to reduce stress on the API / HTML endpoints

    Attributes
    ----------
    play_by_play : list
        Description
    play_by_play_df : pd.DataFrame
        Description
    rosters : list
        Description
    rosters_df : pd.DataFrame
        Description
    changes : list
        Description
    changes_df : pd.DataFrame
        Description
    api_events : list
        Description
    api_events_df : pd.DataFrame
        Description
    api_rosters : list
        Description
    api_rosters_df : pd.DataFrame
        Description
    html_events : list
        Description
    html_events_df : pd.DataFrame
        Description
    html_rosters : list
        Description
    html_rosters_df : pd.DataFrame
        Description
    shifts : list
        Description
    shifts_df : pd.DataFrame
        Description
    game_id : int
        10-digit game identifier, e.g., 2023020001
    game_state : str
        Description
    game_schedule_state : str
        Description
    time_remaining : str
        Description
    seconds_remaining : str
        Description
    running : str
        Description
    in_intermission : str
        Description
    current_period : str
        Description
    current_period_type : str
        Description
    season : int
        Description
    session : str
        Description
    html_id : str
        Description
    game_date : str
        Description
    start_time_et : str
        Description
    venue : str
        Description
    tv_broadcasts : dict
        Description
    home_team : dict
        Description
    away_team : dict
        Description
    api_endpoint : str
        Description
    api_endpoint_other : str
        Description
    html_rosters_endpoint : str
        Description
    home_shifts_endpoint : str
        Description
    away_shifts_endpoint : str
        Description
    html_events_endpoint : str
        Description

    Examples
    --------
    >>> game = Game(2023020001)

    Scrape play-by-play information
    >>> pbp = game.play_by_play # Returns the data as a list

    Get play-by-play as a Pandas DataFrame
    >>> pbp_df = game.play_by_play_df   # Returns the data as a Pandas DataFrame

    The object stores information from each component of the play-by-play data
    >>> shifts = game.shifts    # Returns a list of shifts
    >>> rosters = game.rosters  # Returns a list of players from both API & HTML endpoints
    >>> changes = game.changes  # Returns a list of changes constructed from shifts & roster data

    Data can also be returned as a Pandas DataFrame, rather than a list
    >>> shifts_df = game.shifts_df # Same as above, but as Pandas DataFrame

    Access data from API or HTML endpoints, or both
    >>> api_events = game.api_events
    >>> api_rosters = game.api_rosters
    >>> html_events = game.html_events
    >>> html_rosters = game.html_rosters

    The Game object is fairly rich with information
    >>> game_date = game.game_date
    >>> home_team = game.home_team
    >>> game_state = game.game_state
    >>> seconds_remaining = game.seconds_remaining

    """

    def __init__(
        self,
        game_id: str | int | float,
        requests_session: requests.Session | None = None,
    ):
        if str(game_id).isdigit() is False or len(str(game_id)) != 10:
            raise Exception(f"{game_id} IS NOT A VALID GAME ID")

        # Game ID
        self.game_id: int = int(game_id)

        # season
        year = int(str(self.game_id)[0:4])
        self.season: int = int(f"{year}{year + 1}")

        # game session
        game_sessions = {"O1": "PR", "02": "R", "03": "P"}
        game_session = str(self.game_id)[4:6]
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
        url = (
            f"https://www.nhl.com/scores/htmlreports/{self.season}/RO{self.html_id}.HTM"
        )
        self.html_rosters_endpoint: str = url

        # shifts endpoints
        home_url = (
            f"https://www.nhl.com/scores/htmlreports/{self.season}/TH{self.html_id}.HTM"
        )
        self.home_shifts_endpoint: str = home_url

        away_url = (
            f"https://www.nhl.com/scores/htmlreports/{self.season}/TV{self.html_id}.HTM"
        )
        self.away_shifts_endpoint: str = away_url

        # HTML events endpoint
        url = (
            f"https://www.nhl.com/scores/htmlreports/{self.season}/PL{self.html_id}.HTM"
        )
        self.html_events_endpoint: str = url

        # requests session
        if requests_session is None:
            self._requests_session = s_session()
        else:
            self._requests_session = requests_session

        # Downloading information from NHL api
        response: dict = self._requests_session.get(self.api_endpoint).json()
        self.api_response: dict = response

        # Away team information
        away_team = response["awayTeam"]

        if away_team["abbrev"] == "PHX":
            away_team["abbrev"] = "ARI"

        self.away_team = {
            "id": away_team["id"],
            "name": away_team["name"]["default"].upper(),
            "abbrev": away_team["abbrev"],
            "logo": away_team["logo"],
        }

        # Home team information
        home_team = response["homeTeam"]

        if home_team["abbrev"] == "PHX":
            home_team["abbrev"] = "ARI"

        self.home_team = {
            "id": home_team["id"],
            "name": home_team["name"]["default"].upper(),
            "abbrev": home_team["abbrev"],
            "logo": home_team["logo"],
        }

        # Venue information
        self.venue: str = response["venue"]["default"].upper()

        est = pytz.timezone("US/Eastern")

        # Start time information
        # .fromtimestamp(timestamp, timezone.utc)

        if "Z" in response["startTimeUTC"]:
            response["startTimeUTC"] = response["startTimeUTC"][:-1] + "+00:00"

        self._start_time_utc_dt: dt = dt.fromisoformat(
            response["startTimeUTC"]
        ).astimezone(timezone.utc)
        self._start_time_et_dt: dt = self._start_time_utc_dt.astimezone(est)

        # Game date and start time as strings
        self.game_date = self._start_time_et_dt.strftime("%Y-%m-%d")
        self.start_time_et = self._start_time_et_dt.strftime(
            "%H:%M"
        )  # Consider start time local?

        # Broadcast information
        broadcasts = {
            x["id"]: {k: v for k, v in x.items() if k != "id"}
            for x in response["tvBroadcasts"]
        }
        self.tv_broadcasts = broadcasts

        # Game status
        self.game_state = response["gameState"]

        # Whether game is finalized in the schedule or not
        self.game_schedule_state = response["gameScheduleState"]

        # Clock information
        clock = response["clock"]

        self.time_remaining = clock.get("timeRemaining")
        self.seconds_remaining = clock.get("secondsRemaining")
        self.running = clock["running"]
        self.in_intermission = clock["inIntermission"]

        # Period information
        if response["gameState"] != "FUT":
            self.current_period = response["periodDescriptor"]["number"]
            self.current_period_type = response["periodDescriptor"]["periodType"]

        # Setting up placeholders for data storage
        self._api_events = None
        self._api_rosters = None
        self._changes = None
        self._html_events = None
        self._html_rosters = None
        self._play_by_play = None
        self._rosters = None
        self._shifts = None

    def _munge_api_events(self) -> None:
        """Method to munge events from API endpoint. Updates self._api_events"""

        self._api_events = self.api_response["plays"].copy()

        rosters = {x["api_id"]: x for x in self._api_rosters}

        teams_dict = {
            self.home_team["id"]: self.home_team["abbrev"],
            self.away_team["id"]: self.away_team["abbrev"],
        }

        event_list = []

        for event in self._api_events:
            time_split = event["timeInPeriod"].split(":")

            period = int(event["period"])
            period_seconds = (int(time_split[0]) * 60) + int(time_split[1])

            if self.session == "R" and period == 5:
                game_seconds = 3900

            else:
                game_seconds = ((period - 1) * 1200) + period_seconds

            event_info = {}

            new_values = {
                "season": self.season,
                "session": self.session,
                "game_id": self.game_id,
                "event_idx": event["sortOrder"],
                "period": period,
                "period_seconds": period_seconds,
                "game_seconds": game_seconds,
                "event": event["typeDescKey"],
                "event_code": event["typeCode"],
                "strength": event.get("situationCode"),
                "home_team_defending_side": event.get("homeTeamDefendingSide"),
            }

            event_info.update(new_values)

            if event_info["event"] == "period-start":
                event_info["event"] = "PSTR"

            if event_info["event"] == "period-end":
                event_info["event"] = "PEND"

            if event_info["event"] == "game-end":
                event_info["event"] = "GEND"

            if event_info["event"] == "shootout-complete":
                event_info["event"] = "SOC"

            if event.get("details"):
                new_values = {
                    "event_team": teams_dict.get(
                        event["details"].get("eventOwnerTeamId")
                    ),
                    "coords_x": event["details"].get("xCoord"),
                    "coords_y": event["details"].get("yCoord"),
                    "zone": event["details"].get("zoneCode"),
                    "event_team_id": event["details"].get("eventOwnerTeamId"),
                }

                event_info.update(new_values)

                if event_info["event"] == "faceoff":
                    event_info["player_1_api_id"] = event["details"]["winningPlayerId"]
                    event_info["player_1_type"] = "WINNER"
                    event_info["player_2_api_id"] = event["details"]["losingPlayerId"]
                    event_info["player_2_type"] = "LOSER"

                    event_info["event"] = "FAC"

                if event_info["event"] == "stoppage":
                    event_info["stoppage_reason"] = (
                        event["details"]["reason"].replace("-", " ").upper()
                    )
                    event_info["stoppage_reason_secondary"] = (
                        event["details"]
                        .get("secondaryReason", "")
                        .replace("-", " ")
                        .upper()
                    )

                    event_info["event"] = "STOP"

                if event_info["event"] == "hit":
                    event_info["player_1_api_id"] = event["details"]["hittingPlayerId"]
                    event_info["player_1_type"] = "HITTER"
                    event_info["player_2_api_id"] = event["details"]["hitteePlayerId"]
                    event_info["player_2_type"] = "HITTEE"

                    event_info["event"] = "HIT"

                if event_info["event"] == "giveaway":
                    event_info["player_1_api_id"] = event["details"]["playerId"]
                    event_info["player_1_type"] = "GIVER"

                    event_info["event"] = "GIVE"

                if event_info["event"] == "shot-on-goal":
                    event_info["player_1_api_id"] = event["details"]["shootingPlayerId"]
                    event_info["player_1_type"] = "SHOOTER"
                    event_info["opp_goalie_api_id"] = event["details"].get(
                        "goalieInNetId", "EMPTY NET"
                    )
                    event_info["shot_type"] = (
                        event["details"].get("shotType", "WRIST").upper()
                    )

                    event_info["event"] = "SHOT"

                if event_info["event"] == "takeaway":
                    event_info["player_1_api_id"] = event["details"]["playerId"]
                    event_info["player_1_type"] = "TAKER"

                    event_info["event"] = "TAKE"

                if event_info["event"] == "missed-shot":
                    event_info["player_1_api_id"] = event["details"]["shootingPlayerId"]
                    event_info["player_1_type"] = "SHOOTER"
                    event_info["opp_goalie_api_id"] = event["details"].get(
                        "goalieInNetId", "EMPTY NET"
                    )
                    event_info["shot_type"] = (
                        event["details"].get("shotType", "WRIST").upper()
                    )
                    event_info["miss_reason"] = (
                        event["details"].get("reason", "").replace("-", " ").upper()
                    )

                    event_info["event"] = "MISS"

                if event_info["event"] == "blocked-shot":
                    event_info["player_1_api_id"] = event["details"].get(
                        "blockingPlayerId"
                    )
                    event_info["player_1_type"] = "BLOCKER"

                    if event_info["player_1_api_id"] is None:
                        event_info["event_team"] = "OTHER"
                        event_info["player_1"] = "REFEREE"
                        event_info["player_1_api_id"] = "REFEREE"
                        event_info["player_1_eh_id"] = "REFEREE"

                    event_info["player_2_api_id"] = event["details"]["shootingPlayerId"]
                    event_info["player_2_type"] = "SHOOTER"

                    event_info["event"] = "BLOCK"

                if event_info["event"] == "goal":
                    event_info["player_1_api_id"] = event["details"]["scoringPlayerId"]
                    event_info["player_1_type"] = "GOAL SCORER"
                    event_info["player_2_api_id"] = event["details"].get(
                        "assist1PlayerId"
                    )

                    event_info["player_2_type"] = "PRIMARY ASSIST"
                    event_info["player_3_api_id"] = event["details"].get(
                        "assist2PlayerId"
                    )
                    event_info["player_3_type"] = "SECONDARY ASSIST"

                    event_info["opp_goalie_api_id"] = event["details"].get(
                        "goalieInNetId", "EMPTY NET"
                    )
                    event_info["shot_type"] = (
                        event["details"].get("shotType", "WRIST").upper()
                    )

                    event_info["event"] = "GOAL"

                if event_info["event"] == "penalty":
                    event_info["penalty_type"] = event["details"]["typeCode"]
                    event_info["penalty_reason"] = event["details"]["descKey"].upper()
                    event_info["penalty_duration"] = event["details"].get("duration")

                    if (
                        event_info["penalty_type"] == "BEN"
                        and event["details"].get("committedByPlayerId") is None
                    ):
                        event_info["player_1"] = "BENCH"
                        event_info["player_1_api_id"] = "BENCH"
                        event_info["player_1_eh_id"] = "BENCH"
                        event_info["player_1_type"] = "COMMITTED BY"
                        event_info["player_2_api_id"] = event["details"].get(
                            "servedByPlayerId"
                        )
                        event_info["player_2_type"] = "SERVED BY"

                    elif (
                        "HEAD-COACH" in event_info["penalty_reason"]
                        or "TEAM-STAFF" in event_info["penalty_reason"]
                    ) and event["details"].get("committedByPlayerId") is None:
                        event_info["player_1"] = "BENCH"
                        event_info["player_1_api_id"] = "BENCH"
                        event_info["player_1_eh_id"] = "BENCH"
                        event_info["player_1_type"] = "COMMITTED BY"
                        event_info["player_2_api_id"] = event["details"].get(
                            "servedByPlayerId"
                        )
                        event_info["player_2_type"] = "SERVED BY"

                    else:
                        event_info["player_1_api_id"] = event["details"].get(
                            "committedByPlayerId"
                        )
                        event_info["player_1_type"] = "COMMITTED BY"
                        event_info["player_2_api_id"] = event["details"].get(
                            "drawnByPlayerId"
                        )
                        event_info["player_2_type"] = "DRAWN BY"

                        if event_info["player_2_api_id"] is None:
                            event_info["player_2_api_id"] = event["details"].get(
                                "servedByPlayerId"
                            )
                            event_info["player_2_type"] = "SERVED BY"

                        else:
                            event_info["player_3_api_id"] = event["details"].get(
                                "servedByPlayerId"
                            )
                            event_info["player_3_type"] = "SERVED BY"

                    event_info["event"] = "PENL"

                if event_info["event"] == "delayed-penalty":
                    event_info["event"] = "DELPEN"

                if event_info["event"] == "failed-shot-attempt":
                    event_info["player_1_api_id"] = event["details"]["shootingPlayerId"]
                    event_info["player_1_type"] = "SHOOTER"
                    event_info["opp_goalie_api_id"] = event["details"]["goalieInNetId"]

                    event_info["event"] = "MISS"

            event_info = api_events_fixes(self.game_id, event_info)

            player_cols = [
                "player_1_api_id",
                "player_2_api_id",
                "player_3_api_id",
                "opp_goalie_api_id",
            ]

            for player_col in player_cols:
                if player_col not in event_info.keys():
                    continue

                elif event_info[player_col] is None:
                    continue

                elif event_info[player_col] == "BENCH":
                    continue

                elif event_info[player_col] == "REFEREE":
                    continue

                else:
                    player_info = rosters.get(event_info[player_col], {})

                    new_cols = {
                        player_col.replace("_api_id", ""): player_info.get(
                            "player_name"
                        ),
                        player_col.replace("_api_id", "_eh_id"): player_info.get(
                            "eh_id"
                        ),
                        player_col.replace("_api_id", "_team_jersey"): player_info.get(
                            "team_jersey"
                        ),
                        player_col.replace("_api_id", "_position"): player_info.get(
                            "position"
                        ),
                    }

                    event_info.update(new_cols)

            event_list.append(event_info)

        for event in event_list:
            if "version" in event.keys():
                continue

            other_events = [
                x
                for x in event_list
                if x != event
                and x["event"] == event["event"]
                and x["game_seconds"] == event["game_seconds"]
                and x.get("player_1") is not None
                and x["period"] == event["period"]
                and x.get("player_1_api_id") == event.get("player_1_api_id")
            ]

            version = 1

            event["version"] = 1

            if len(other_events) > 0:
                for idx, other_event in enumerate(other_events):
                    if "version" not in other_event.keys():
                        version += 1

                        other_event["version"] = version

        self._api_events = event_list

    def _finalize_api_events(self) -> pd.DataFrame:
        """Method that creates and returns Pandas DataFrame from self._api_events"""

        df = pd.DataFrame(self._api_events)

        cols = [
            "season",
            "session",
            "game_id",
            "event_team",
            "event_idx",
            "period",
            "period_seconds",
            "game_seconds",
            "event",
            "event_code",
            "strength",
            "coords_x",
            "coords_y",
            "zone",
            "player_1",
            "player_1_eh_id",
            "player_1_api_id",
            "player_1_position",
            "player_1_team_jersey",
            "player_1_type",
            "player_2",
            "player_2_eh_id",
            "player_2_api_id",
            "player_2_position",
            "player_2_team_jersey",
            "player_2_type",
            "player_3",
            "player_3_eh_id",
            "player_3_api_id",
            "player_3_position",
            "player_3_team_jersey",
            "player_3_type",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "opp_goalie_team_jersey",
            "shot_type",
            "miss_reason",
            "penalty_reason",
            "penalty_duration",
            "penalty_type",
            "stoppage_reason",
            "stoppage_reason_secondary",
            "home_team_defending_side",
            "version",
        ]

        cols = [x for x in cols if x in df.columns]

        df = df[cols]

        return df

    @property
    def api_events(self) -> list:
        """List of events scraped from API endpoint"""

        if self._api_rosters is None:
            self._munge_api_rosters()

        if self._api_events is None:
            self._munge_api_events()

        return self._api_events

    @property
    def api_events_df(self) -> pd.DataFrame:
        """Pandas Dataframe of events scraped from API endpoint"""

        if self._api_rosters is None:
            self._munge_api_rosters()

        if self._api_events is None:
            self._munge_api_events()

        return self._finalize_api_events()

    def _munge_api_rosters(self) -> None:
        """Method to munge list of players from API  endpoint. Updates self._api_rosters"""

        players = []

        team_info = {
            self.home_team["id"]: {"venue": "HOME", "team": self.home_team["abbrev"]},
            self.away_team["id"]: {"venue": "AWAY", "team": self.away_team["abbrev"]},
        }

        for player in self.api_response["rosterSpots"]:
            first_name = (
                unidecode(player["firstName"]["default"])
                .encode("latin")
                .decode("utf=8")
                .upper()
                .strip()
            )

            last_name = (
                unidecode(player["lastName"]["default"])
                .encode("latin")
                .decode("utf=8")
                .upper()
                .strip()
            )

            player_name = first_name + " " + last_name

            player_name = (
                player_name.replace("ALEXANDRE", "ALEX")
                .replace("ALEXANDER", "ALEX")
                .replace("CHRISTOPHER", "CHRIS")
            )

            player_name = correct_names_dict.get(player_name, player_name)

            eh_id = (
                player_name.split(" ", 1)[0] + "." + player_name.split(" ", 1)[1]
            ).replace("..", ".")

            eh_id = correct_api_names_dict.get(player["playerId"], eh_id)

            team = team_info[player["teamId"]]

            player_info = {
                "season": self.season,
                "session": self.session,
                "game_id": self.game_id,
                "team": team["team"],
                "team_venue": team["venue"],
                "player_name": player_name,
                "first_name": first_name,
                "last_name": last_name,
                "api_id": player["playerId"],
                "eh_id": correct_api_names_dict.get(player["playerId"], eh_id),
                "team_jersey": team["team"] + str(player["sweaterNumber"]),
                "jersey": player["sweaterNumber"],
                "position": player["positionCode"],
                "headshot_url": player.get("headshot", np.nan),
            }

            players.append(player_info)

        if self.game_id == 2013020971:
            new_player = {
                "season": self.season,
                "session": self.session,
                "game_id": self.game_id,
                "team": "CBJ",
                "team_venue": "AWAY",
                "player_name": "NATHAN HORTON",
                "first_name": "NATHAN",
                "last_name": "HORTON",
                "api_id": 8470596,
                "eh_id": "NATHAN.HORTON",
                "team_jersey": "CBJ8",
                "jersey": 8,
                "position": "R",
                "headshot_url": np.nan,
            }

            players.append(new_player)

        self._api_rosters = players

    def _finalize_api_rosters(self) -> pd.DataFrame:
        """Method that creates and returns a Pandas DataFrame from self._api_rosters"""

        df = pd.DataFrame(self._api_rosters)

        columns = [
            "season",
            "session",
            "game_id",
            "team",
            "team_venue",
            "player_name",
            "api_id",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "first_name",
            "last_name",
            "headshot_url",
        ]

        columns = [x for x in columns if x in df.columns]

        df = df[columns]

        return df

    @property
    def api_rosters(self) -> list:
        """List of players scraped from API endpoint"""

        if self._api_rosters is None:
            self._munge_api_rosters()

        return self._api_rosters

    @property
    def api_rosters_df(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from API endpoint"""

        if self._api_rosters is None:
            self._munge_api_rosters()

        return self._finalize_api_rosters()

    def _munge_changes(self) -> None:
        """Method to munge list of changes from HTML shifts & rosters endpoints. Updates self._changes"""

        game_id = self.game_id
        season = self.season
        game_session = self.session
        shifts = self._shifts

        game_list = []

        periods = np.unique([x["period"] for x in shifts]).tolist()

        teams = ["HOME", "AWAY"]

        for period in periods:
            max([x["end_time_seconds"] for x in shifts if x["period"] == period])

            for team in teams:
                changes_dict = {}

                changes_on = np.unique(
                    [
                        x["start_time_seconds"]
                        for x in shifts
                        if x["period"] == period and x["team_venue"] == team
                    ]
                ).tolist()

                for change_on in changes_on:
                    players_on = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["start_time_seconds"] == change_on
                        and x["team_venue"] == team
                    ]

                    players_on = sorted(players_on, key=lambda k: (k["jersey"]))

                    f_positions = ["L", "C", "R"]

                    forwards_on = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["start_time_seconds"] == change_on
                        and x["team_venue"] == team
                        and x["position"] in f_positions
                    ]

                    forwards_on = sorted(forwards_on, key=lambda k: (k["jersey"]))

                    defense_on = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["start_time_seconds"] == change_on
                        and x["team_venue"] == team
                        and x["position"] == "D"
                    ]

                    defense_on = sorted(defense_on, key=lambda k: (k["jersey"]))

                    goalies_on = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["start_time_seconds"] == change_on
                        and x["team_venue"] == team
                        and x["position"] == "G"
                    ]

                    goalies_on = sorted(goalies_on, key=lambda k: (k["jersey"]))

                    new_values = {
                        "season": season,
                        "session": game_session,
                        "game_id": game_id,
                        "event": "CHANGE",
                        "event_team": players_on[0]["team"],
                        "is_home": players_on[0]["is_home"],
                        "is_away": players_on[0]["is_away"],
                        "team_venue": team,
                        "period": period,
                        "period_time": players_on[0]["start_time"],
                        "period_seconds": players_on[0]["start_time_seconds"],
                        "change_on_count": len(players_on),
                        "change_off_count": 0,
                        "change_on_jersey": [x["team_jersey"] for x in players_on],
                        "change_on": [x["player_name"] for x in players_on],
                        "change_on_id": [x["eh_id"] for x in players_on],
                        "change_on_positions": [x["position"] for x in players_on],
                        "change_off_jersey": "",
                        "change_off": "",
                        "change_off_id": "",
                        "change_off_positions": "",
                        "change_on_forwards_count": len(forwards_on),
                        "change_off_forwards_count": 0,
                        "change_on_forwards_jersey": [
                            x["team_jersey"] for x in forwards_on
                        ],
                        "change_on_forwards": [x["player_name"] for x in forwards_on],
                        "change_on_forwards_id": [x["eh_id"] for x in forwards_on],
                        "change_off_forwards_jersey": "",
                        "change_off_forwards": "",
                        "change_off_forwards_id": "",
                        "change_on_defense_count": len(defense_on),
                        "change_off_defense_count": 0,
                        "change_on_defense_jersey": [
                            x["team_jersey"] for x in defense_on
                        ],
                        "change_on_defense": [x["player_name"] for x in defense_on],
                        "change_on_defense_id": [x["eh_id"] for x in defense_on],
                        "change_off_defense_jersey": "",
                        "change_off_defense": "",
                        "change_off_defense_id": "",
                        "change_on_goalie_count": len(goalies_on),
                        "change_off_goalie_count": 0,
                        "change_on_goalie_jersey": [
                            x["team_jersey"] for x in goalies_on
                        ],
                        "change_on_goalie": [x["player_name"] for x in goalies_on],
                        "change_on_goalie_id": [x["eh_id"] for x in goalies_on],
                        "change_off_goalie_jersey": "",
                        "change_off_goalie": "",
                        "change_off_goalie_id": "",
                    }

                    changes_dict.update({change_on: new_values})

                changes_off = np.unique(
                    [
                        x["end_time_seconds"]
                        for x in shifts
                        if x["period"] == period and x["team_venue"] == team
                    ]
                ).tolist()

                for change_off in changes_off:
                    players_off = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["end_time_seconds"] == change_off
                        and x["team_venue"] == team
                    ]

                    players_off = sorted(players_off, key=lambda k: (k["jersey"]))

                    f_positions = ["L", "C", "R"]

                    forwards_off = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["end_time_seconds"] == change_off
                        and x["team_venue"] == team
                        and x["position"] in f_positions
                    ]

                    forwards_off = sorted(forwards_off, key=lambda k: (k["jersey"]))

                    defense_off = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["end_time_seconds"] == change_off
                        and x["team_venue"] == team
                        and x["position"] == "D"
                    ]

                    defense_off = sorted(defense_off, key=lambda k: (k["jersey"]))

                    goalies_off = [
                        x
                        for x in shifts
                        if x["period"] == period
                        and x["end_time_seconds"] == change_off
                        and x["team_venue"] == team
                        and x["position"] == "G"
                    ]

                    goalies_off = sorted(goalies_off, key=lambda k: (k["jersey"]))

                    new_values = {
                        "season": season,
                        "session": game_session,
                        "game_id": game_id,
                        "event": "CHANGE",
                        "event_team": players_off[0]["team"],
                        "team_venue": team,
                        "is_home": players_off[0]["is_home"],
                        "is_away": players_off[0]["is_away"],
                        "period": period,
                        "period_time": players_off[0]["end_time"],
                        "period_seconds": players_off[0]["end_time_seconds"],
                        "change_off_count": len(players_off),
                        "change_off_jersey": [x["team_jersey"] for x in players_off],
                        "change_off": [x["player_name"] for x in players_off],
                        "change_off_id": [x["eh_id"] for x in players_off],
                        "change_off_positions": [x["position"] for x in players_off],
                        "change_off_forwards_count": len(forwards_off),
                        "change_off_forwards_jersey": [
                            x["team_jersey"] for x in forwards_off
                        ],
                        "change_off_forwards": [x["player_name"] for x in forwards_off],
                        "change_off_forwards_id": [x["eh_id"] for x in forwards_off],
                        "change_off_defense_count": len(defense_off),
                        "change_off_defense_jersey": [
                            x["team_jersey"] for x in defense_off
                        ],
                        "change_off_defense": [x["player_name"] for x in defense_off],
                        "change_off_defense_id": [x["eh_id"] for x in defense_off],
                        "change_off_goalie_count": len(goalies_off),
                        "change_off_goalie_jersey": [
                            x["team_jersey"] for x in goalies_off
                        ],
                        "change_off_goalie": [x["player_name"] for x in goalies_off],
                        "change_off_goalie_id": [x["eh_id"] for x in goalies_off],
                    }

                    if change_off in changes_on:
                        changes_dict[change_off].update(new_values)

                    else:
                        new_values.update(
                            {
                                "change_on_count": 0,
                                "change_on_forwards_count": 0,
                                "change_on_defense_count": 0,
                                "change_on_goalie_count": 0,
                            }
                        )

                        changes_dict[change_off] = new_values

                game_list.extend(list(changes_dict.values()))

        game_list = sorted(
            game_list, key=lambda k: (k["period"], k["period_seconds"], k["is_away"])
        )

        for change in game_list:
            players_on = ", ".join(change.get("change_on", []))

            players_off = ", ".join(change.get("change_off", []))

            on_num = len(change.get("change_on", []))

            off_num = len(change.get("change_off", []))

            if on_num > 0 and off_num > 0:
                change[
                    "description"
                ] = f"PLAYERS ON: {players_on} / PLAYERS OFF: {players_off}"

            if on_num > 0 and off_num == 0:
                change["description"] = f"PLAYERS ON: {players_on}"

            if off_num > 0 and on_num == 0:
                change["description"] = f"PLAYERS OFF: {players_off}"

            if change["period"] == 5 and game_session == "R":
                change["game_seconds"] = 3900 + change["period_seconds"]

            else:
                change["game_seconds"] = (int(change["period"]) - 1) * 1200 + change[
                    "period_seconds"
                ]

            if change["is_home"] == 1:
                change["event_type"] = "HOME CHANGE"

            else:
                change["event_type"] = "AWAY CHANGE"

        self._changes = game_list

    def _finalize_changes(self) -> pd.DataFrame:
        """Method that creates and returns a Pandas DataFrame from self._changes"""

        list_fields = [
            "change_on_jersey",
            "change_on",
            "change_on_id",
            "change_on_positions",
            "change_off_jersey",
            "change_off",
            "change_off_id",
            "change_off_positions",
            "change_on_forwards_jersey",
            "change_on_forwards",
            "change_on_forwards_id",
            "change_off_forwards_jersey",
            "change_off_forwards",
            "change_off_forwards_id",
            "change_on_defense_jersey",
            "change_on_defense",
            "change_on_defense_id",
            "change_off_defense_jersey",
            "change_off_defense",
            "change_off_defense_id",
            "change_on_goalie_jersey",
            "change_on_goalie",
            "change_on_goalie_id",
            "change_off_goalie_jersey",
            "change_off_goalie",
            "change_off_goalie_id",
        ]

        changes = [x.copy() for x in self._changes]

        for change in changes:
            for list_field in list_fields:
                change[list_field] = ", ".join(change.get(list_field, ""))

        df = pd.DataFrame(changes)

        column_order = [
            "season",
            "session",
            "game_id",
            "event_team",
            "event_team_name",
            "team_venue",
            "event",
            "event_type",
            "description",
            "period",
            "period_seconds",
            "game_seconds",
            "change_on_count",
            "change_off_count",
            "change_on_jersey",
            "change_on",
            "change_on_id",
            "change_on_positions",
            "change_off_jersey",
            "change_off",
            "change_off_id",
            "change_off_positions",
            "change_on_forwards_count",
            "change_off_forwards_count",
            "change_on_forwards_jersey",
            "change_on_forwards",
            "change_on_forwards_id",
            "change_off_forwards_jersey",
            "change_off_forwards",
            "change_off_forwards_id",
            "change_on_defense_count",
            "change_off_defense_count",
            "change_on_defense_jersey",
            "change_on_defense",
            "change_on_defense_id",
            "change_off_defense_jersey",
            "change_off_defense",
            "change_off_defense_id",
            "change_on_goalie_count",
            "change_off_goalie_count",
            "change_on_goalie_jersey",
            "change_on_goalie",
            "change_on_goalie_id",
            "change_off_goalie_jersey",
            "change_off_goalie",
            "change_off_goalie_id",
            "is_home",
        ]

        column_order = [x for x in column_order if x in df.columns]

        df = df[column_order].replace("", np.nan).replace(" ", np.nan)

        return df

    @property
    def changes(self) -> list:
        """List of changes scraped from API endpoint"""

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        if self._shifts is None:
            self._scrape_shifts()
            self._munge_shifts()

        if self._changes is None:
            self._munge_changes()

        return self._changes

    @property
    def changes_df(self) -> pd.DataFrame:
        """Pandas Dataframe of changes scraped from HTML shifts & roster endpoints"""

        if self._changes is None:
            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            if self._shifts is None:
                self._scrape_shifts()
                self._munge_shifts()

            self._munge_changes()

        return self._finalize_changes()

    def _scrape_html_events(self) -> None:
        """Method for scraping events from HTML endpoint. Updates self._html_events"""

        url = self.html_events_endpoint

        s = self._requests_session

        try:
            response = s.get(url)
        except RetryError:
            return None

        soup = BeautifulSoup(response.content.decode("ISO-8859-1"), "lxml")

        events = []

        if soup.find("html") is None:
            return None

        tds = soup.find_all("td", {"class": re.compile(".*bborder.*")})

        events_data = hs_strip_html(tds)

        events_data = [
            unidecode(x).replace("\n ", ", ").replace("\n", "") for x in events_data
        ]

        length = int(len(events_data) / 8)

        events_data = np.array(events_data).reshape(length, 8)

        for idx, event in enumerate(events_data):
            column_names = [
                "event_idx",
                "period",
                "strength",
                "time",
                "event",
                "description",
                "away_skaters",
                "home_skaters",
            ]

            if "#" in event:
                continue

            else:
                event = dict(zip(column_names, event))

                new_values = {
                    "season": self.season,
                    "session": self.session,
                    "game_id": self.game_id,
                    "event_idx": int(event["event_idx"]),
                    "description": unidecode(event["description"]).upper(),
                    "period": event["period"],
                }

                event.update(new_values)

                # This event is missing from the API and doesn't have a player in the HTML endpoint

                if self.game_id == 2022020194 and event["event_idx"] == 134:
                    continue

                if self.game_id == 2022020673 and event["event_idx"] == 208:
                    continue

                events.append(event)

        self._html_events = events

    def _munge_html_events(self) -> None:
        """Method to munge list of events from HTML endpoint. Updates self._html_events"""

        game_session = self.session

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        roster = self._html_rosters

        # Compiling regex expressions to save time later

        event_team_re = re.compile(r"^([A-Z]{3}|[A-Z]\.[A-Z])")
        numbers_re = re.compile(r"#([0-9]{1,2})")
        event_players_re = re.compile(r"([A-Z]{3}\s+#[0-9]{1,2})")
        re.compile(r"([A-Z]{1,2})")
        fo_team_re = re.compile(r"([A-Z]{3}) WON")
        block_team_re = re.compile(r"BLOCKED BY\s+([A-Z]{3})")
        re.compile(r"(\d+)")
        zone_re = re.compile(r"([A-Za-z]{3}). ZONE")
        penalty_re = re.compile(
            r"([A-Za-z]*|[A-Za-z]*-[A-Za-z]*|[A-Za-z]*\s+\(.*\))\s*\("
        )
        penalty_length_re = re.compile(r"(\d+) MIN")
        shot_re = re.compile(r",\s+([A-za-z]*|[A-za-z]*-[A-za-z]*)\s+,")
        distance_re = re.compile(r"(\d+) FT")
        served_re = re.compile(r"([A-Z]{3})\s.+SERVED BY: #([0-9]+)")
        # served_drawn_re = re.compile('([A-Z]{3})\s#.*\sSERVED BY: #([0-9]+)')
        drawn_re = re.compile(r"DRAWN BY: ([A-Z]{3}) #([0-9]+)")

        actives = {
            player["team_jersey"]: player
            for player in roster
            if player["status"] == "ACTIVE"
        }

        scratches = {
            player["team_jersey"]: player
            for player in roster
            if player["status"] == "SCRATCH"
        }

        for event in self._html_events:
            non_descripts = {
                "PGSTR": "PRE-GAME START",
                "PGEND": "PRE-GAME END",
                "ANTHEM": "NATIONAL ANTHEM",
                "EISTR": "EARLY INTERMISSION START",
                "EIEND": "EARLY INTERMISSION END",
            }

            if event["event"] in list(non_descripts.keys()):
                event["description"] = non_descripts[event["event"]]

            # Replacing the team names with three-letter codes from API endpoint

            new_team_names = {
                "L.A": "LAK",
                "N.J": "NJD",
                "S.J": "SJS",
                "T.B": "TBL",
                "PHX": "ARI",
            }

            for old_name, new_name in new_team_names.items():
                event["description"] = (
                    event["description"].replace(old_name, new_name).upper()
                )

            event = html_events_fixes(self.game_id, event)

            if event["event"] == "PEND" and event["time"] == "-16:0-120:00":
                goals = [
                    x
                    for x in self._html_events
                    if x["period"] == event["period"] and x["event"] == "GOAL"
                ]

                if len(goals) == 0:
                    if int(event["period"]) == 4 and event["session"] == "R":
                        event["time"] = event["time"].replace(
                            "-16:0-120:00", "5:000:00"
                        )

                    else:
                        event["time"] = event["time"].replace(
                            "-16:0-120:00", "20:000:00"
                        )

                elif len(goals) > 0:
                    goal = goals[-1]

                    event["time"] = event["time"].replace("-16:0-120:00", goal["time"])

            non_team_events = [
                "STOP",
                "ANTHEM",
                "PGSTR",
                "PGEND",
                "PSTR",
                "PEND",
                "EISTR",
                "EIEND",
                "GEND",
                "SOC",
                "PBOX",
            ]

            if event["event"] not in non_team_events:
                try:
                    event["event_team"] = re.search(
                        event_team_re, event["description"]
                    ).group(1)

                    if event["event_team"] == "LEA":
                        event["event_team"] = ""

                except AttributeError:
                    continue

            if event["event"] == "FAC":
                event["event_team"] = re.search(fo_team_re, event["description"]).group(
                    1
                )

            if event["event"] == "BLOCK" and "BLOCKED BY" in event["description"]:
                event["event_team"] = re.search(
                    block_team_re, event["description"]
                ).group(1)

            event["period"] = int(event["period"])

            time_split = event["time"].split(":")

            event["period_time"] = time_split[0] + ":" + time_split[1][:2]

            event["period_seconds"] = (
                60 * int(event["period_time"].split(":")[0])
            ) + int(event["period_time"].split(":")[1])

            event["game_seconds"] = (int(event["period"]) - 1) * 1200 + event[
                "period_seconds"
            ]

            if event["period"] == 5 and game_session == "R":
                event["game_seconds"] = 3900 + event["period_seconds"]

            event_list = ["GOAL", "SHOT", "TAKE", "GIVE"]

            if event["event"] in event_list:
                event_players = [
                    event["event_team"] + num
                    for num in re.findall(numbers_re, event["description"])
                ]

            else:
                event_players = re.findall(event_players_re, event["description"])

            if event["event"] == "FAC" and event["event_team"] not in event_players[0]:
                event_players[0], event_players[1] = event_players[1], event_players[0]

            if event["event"] == "BLOCK" and "TEAMMATE" in event["description"]:
                event["event_team"] = event["description"][:3]

                event_players.insert(0, "TEAMMATE")

            elif (
                event["event"] == "BLOCK" and "BLOCKED BY OTHER" in event["description"]
            ):
                event["event_team"] = "OTHER"

                event_players.insert(0, "REFEREE")

            elif (
                event["event"] == "BLOCK"
                and event["event_team"] not in event_players[0]
            ):
                event_players[0], event_players[1] = event_players[1], event_players[0]

            for idx, event_player in enumerate(event_players):
                num = idx + 1

                event_player = event_player.replace(" #", "")

                if event_player == "TEAMMATE":
                    player_name = "TEAMMATE"
                    eh_id = "TEAMMATE"
                    position = np.nan

                elif event_player == "REFEREE":
                    player_name = "REFEREE"
                    eh_id = "REFEREE"
                    position = np.nan

                else:
                    try:
                        player_name = actives[event_player]["player_name"]
                        eh_id = actives[event_player]["eh_id"]
                        position = actives[event_player]["position"]

                    except KeyError:
                        player_name = scratches[event_player]["player_name"]
                        eh_id = scratches[event_player]["eh_id"]
                        position = scratches[event_player]["position"]

                new_values = {
                    f"player_{num}": player_name,
                    f"player_{num}_eh_id": eh_id,
                    f"player_{num}_position": position,
                }

                event.update(new_values)

            try:
                event["zone"] = (
                    re.search(zone_re, event["description"]).group(1).upper()
                )

                if "BLOCK" in event["event"] and event["zone"] == "DEF":
                    event["zone"] = "OFF"

            except AttributeError:
                pass

            if event["event"] == "PENL":
                if (
                    "TEAM" in event["description"]
                    and "SERVED BY" in event["description"]
                ) or ("HEAD COACH" in event["description"]):
                    event["player_1"] = "BENCH"

                    event["player_1_eh_id"] = "BENCH"

                    event["player_1_position"] = ""

                    try:
                        served_by = re.search(served_re, event["description"])

                        name = served_by.group(1) + str(served_by.group(2))

                    except AttributeError:
                        try:
                            drawn_by = re.search(drawn_re, event["description"])

                            name = drawn_by.group(1) + str(drawn_by.group(2))

                        except AttributeError:
                            continue

                    event["player_2"] = actives[name]["player_name"]

                    event["player_2_eh_id"] = actives[name]["eh_id"]

                    event["player_2_position"] = actives[name]["position"]

                if (
                    "SERVED BY" in event["description"]
                    and "DRAWN BY" in event["description"]
                ):
                    try:
                        drawn_by = re.search(drawn_re, event["description"])

                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))

                        event["player_2"] = actives[drawn_name]["player_name"]

                        event["player_2_eh_id"] = actives[drawn_name]["eh_id"]

                        event["player_2_position"] = actives[drawn_name]["position"]

                        if event["player_1_eh_id"] == event["player_2_eh_id"]:
                            event["player_1"] = "BENCH"
                            event["player_1_eh_id"] = "BENCH"
                            event["player_1_position"] = np.nan

                        served_by = re.search(served_re, event["description"])

                        served_name = served_by.group(1) + str(served_by.group(2))

                        event["player_3"] = actives[served_name]["player_name"]

                        event["player_3_eh_id"] = actives[served_name]["eh_id"]

                        event["player_3_position"] = actives[served_name]["position"]

                        if (
                            "TEAM" in event["description"]
                            or "HEAD COACH" in event["description"]
                        ):
                            event["player_2"], event["player_3"] = (
                                event["player_3"],
                                event["player_2"],
                            )

                            event["player_2_eh_id"], event["player_3_eh_id"] = (
                                event["player_3_eh_id"],
                                event["player_2_eh_id"],
                            )

                            event["player_2_position"], event["player_3_position"] = (
                                event["player_3_position"],
                                event["player_2_position"],
                            )

                    except AttributeError:
                        pass

                elif "SERVED BY" in event["description"]:
                    try:
                        served_by = re.search(served_re, event["description"])

                        served_name = served_by.group(1) + str(served_by.group(2))

                        event["player_2"] = actives[served_name]["player_name"]

                        event["player_2_eh_id"] = actives[served_name]["eh_id"]

                        event["player_2_position"] = actives[served_name]["position"]

                    except AttributeError:
                        pass

                elif "DRAWN BY" in event["description"]:
                    try:
                        drawn_by = re.search(drawn_re, event["description"])

                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))

                        event["player_2"] = actives[drawn_name]["player_name"]

                        event["player_2_eh_id"] = actives[drawn_name]["eh_id"]

                        event["player_2_position"] = actives[drawn_name]["position"]

                    except AttributeError:
                        pass

                if "player_1" not in event.keys():
                    new_values = {
                        "player_1": "BENCH",
                        "player_1_eh_id": "BENCH",
                        "player_1_position": "",
                    }

                    event.update(new_values)

                try:
                    event["penalty_length"] = int(
                        re.search(penalty_length_re, event["description"]).group(1)
                    )

                except TypeError:
                    pass

                try:
                    event["penalty"] = (
                        re.search(penalty_re, event["description"]).group(1).upper()
                    )

                except AttributeError:
                    continue

                if (
                    "INTERFERENCE" in event["description"]
                    and "GOALKEEPER" in event["description"]
                ):
                    event["penalty"] = "GOALKEEPER INTERFERENCE"

                elif (
                    "CROSS" in event["description"]
                    and "CHECKING" in event["description"]
                ):
                    event["penalty"] = "CROSS-CHECKING"

                elif (
                    "DELAY" in event["description"]
                    and "GAME" in event["description"]
                    and "PUCK OVER" in event["description"]
                ):
                    event["penalty"] = "DELAY OF GAME - PUCK OVER GLASS"

                elif (
                    "DELAY" in event["description"]
                    and "GAME" in event["description"]
                    and "FO VIOL" in event["description"]
                ):
                    event["penalty"] = "DELAY OF GAME - FACEOFF VIOLATION"

                elif (
                    "DELAY" in event["description"]
                    and "GAME" in event["description"]
                    and "EQUIPMENT" in event["description"]
                ):
                    event["penalty"] = "DELAY OF GAME - EQUIPMENT"

                elif (
                    "DELAY" in event["description"]
                    and "GAME" in event["description"]
                    and "UNSUCC" in event["description"]
                ):
                    event["penalty"] = "DELAY OF GAME - UNSUCCESSFUL CHALLENGE"

                elif (
                    "DELAY" in event["description"]
                    and "GAME" in event["description"]
                    and "SMOTHERING" in event["description"]
                ):
                    event["penalty"] = "DELAY OF GAME - SMOTHERING THE PUCK"

                elif (
                    "ILLEGAL" in event["description"]
                    and "CHECK" in event["description"]
                    and "HEAD" in event["description"]
                ):
                    event["penalty"] = "ILLEGAL CHECK TO HEAD"

                elif (
                    "HIGH-STICKING" in event["description"]
                    and "- DOUBLE" in event["description"]
                ):
                    event["penalty"] = "HIGH-STICKING - DOUBLE MINOR"

                elif "GAME MISCONDUCT" in event["description"]:
                    event["penalty"] = "GAME MISCONDUCT"

                elif "MATCH PENALTY" in event["description"]:
                    event["penalty"] = "MATCH PENALTY"

                elif (
                    "NET" in event["description"]
                    and "DISPLACED" in event["description"]
                ):
                    event["penalty"] = "DISPLACED NET"

                elif (
                    "THROW" in event["description"]
                    and "OBJECT" in event["description"]
                    and "AT PUCK" in event["description"]
                ):
                    event["penalty"] = "THROWING OBJECT AT PUCK"

                elif (
                    "INSTIGATOR" in event["description"]
                    and "FACE SHIELD" in event["description"]
                ):
                    event["penalty"] = "INSTIGATOR - FACE SHIELD"

                elif "GOALIE LEAVE CREASE" in event["description"]:
                    event["penalty"] = "LEAVING THE CREASE"

                elif (
                    "REMOVING" in event["description"]
                    and "HELMET" in event["description"]
                ):
                    event["penalty"] = "REMOVING OPPONENT HELMET"

                elif (
                    "BROKEN" in event["description"] and "STICK" in event["description"]
                ):
                    event["penalty"] = "HOLDING BROKEN STICK"

                elif (
                    "HOOKING" in event["description"]
                    and "BREAKAWAY" in event["description"]
                ):
                    event["penalty"] = "HOOKING - BREAKAWAY"

                elif (
                    "HOLDING" in event["description"]
                    and "BREAKAWAY" in event["description"]
                ):
                    event["penalty"] = "HOLDING - BREAKAWAY"

                elif (
                    "TRIPPING" in event["description"]
                    and "BREAKAWAY" in event["description"]
                ):
                    event["penalty"] = "TRIPPING - BREAKAWAY"

                elif (
                    "SLASH" in event["description"]
                    and "BREAKAWAY" in event["description"]
                ):
                    event["penalty"] = "SLASHING - BREAKAWAY"

                elif "TEAM TOO MANY" in event["description"]:
                    event["penalty"] = "TOO MANY MEN ON THE ICE"

                elif (
                    "HOLDING" in event["description"]
                    and "STICK" in event["description"]
                ):
                    event["penalty"] = "HOLDING THE STICK"

                elif (
                    "THROWING" in event["description"]
                    and "STICK" in event["description"]
                ):
                    event["penalty"] = "THROWING STICK"

                elif (
                    "CLOSING" in event["description"] and "HAND" in event["description"]
                ):
                    event["penalty"] = "CLOSING HAND ON PUCK"

                elif (
                    "ABUSE" in event["description"]
                    and "OFFICIALS" in event["description"]
                ):
                    event["penalty"] = "ABUSE OF OFFICIALS"

                elif "UNSPORTSMANLIKE CONDUCT" in event["description"]:
                    event["penalty"] = "UNSPORTSMANLIKE CONDUCT"

                elif (
                    "PUCK" in event["description"]
                    and "THROWN" in event["description"]
                    and "FWD" in event["description"]
                ):
                    event["penalty"] = "PUCK THROWN FORWARD - GOALKEEPER"

                elif "DELAY" in event["description"] and "GAME" in event["description"]:
                    event["penalty"] = "DELAY OF GAME"

                elif event["penalty"] == "MISCONDUCT":
                    event["penalty"] = "GAME MISCONDUCT"

            shot_events = ["GOAL", "SHOT", "MISS", "BLOCK"]

            if event["event"] in shot_events:
                try:
                    event["shot_type"] = (
                        re.search(shot_re, event["description"]).group(1).upper()
                    )

                except AttributeError:
                    event["shot_type"] = "WRIST"

                    pass

                if "BETWEEN LEGS" in event["description"]:
                    event["shot_type"] = "BETWEEN LEGS"

            try:
                event["pbp_distance"] = int(
                    re.search(distance_re, event["description"]).group(1)
                )

            except AttributeError:
                if event["event"] in ["GOAL", "SHOT", "MISS"]:
                    event["pbp_distance"] = 0

                pass

        self._html_events = sorted(self._html_events, key=lambda k: (k["event_idx"]))

        for event in self._html_events:
            if "period_seconds" not in event.keys():
                if "time" in event.keys():
                    event["period"] = int(event["period"])

                    time_split = event["time"].split(":")

                    event["period_time"] = time_split[0] + ":" + time_split[1][:2]

                    event["period_seconds"] = (
                        60 * int(event["period_time"].split(":")[0])
                    ) + int(event["period_time"].split(":")[1])

            if "game_seconds" not in event.keys():
                event["game_seconds"] = (int(event["period"]) - 1) * 1200 + event[
                    "period_seconds"
                ]

                if event["period"] == 5 and event["session"] == "R":
                    event["game_seconds"] = 3900 + event["period_seconds"]

            if "version" not in event.keys():
                other_events = [
                    x
                    for x in self._html_events
                    if x != event
                    and x["event"] == event["event"]
                    and x.get("game_seconds") == event["game_seconds"]
                    and x["period"] == event["period"]
                    and x.get("player_1_eh_id") is not None
                    and event.get("player_1_eh_id") is not None
                    and x["player_1_eh_id"] == event["player_1_eh_id"]
                ]

                version = 1

                event["version"] = version

                if len(other_events) > 0:
                    for idx, other_event in enumerate(other_events):
                        if "version" not in other_event.keys():
                            version += 1

                            other_event["version"] = version

    def _finalize_html_events(self) -> pd.DataFrame:
        """Method that creates and returns a Pandas DataFrame from self._html_events"""

        df = pd.DataFrame(self._html_events)

        columns = [
            "season",
            "session",
            "game_id",
            "event_team",
            "event_idx",
            "period",
            "period_seconds",
            "game_seconds",
            "event",
            "description",
            "strength",
            "zone",
            "player_1",
            "player_1_eh_id",
            "player_1_position",
            "player_2",
            "player_2_eh_id",
            "player_2_position",
            "player_3",
            "player_3_eh_id",
            "player_3_position",
            "pbp_distance",
            "shot_type",
            "penalty",
            "penalty_length",
            "version",
        ]

        column_order = [x for x in columns if x in df.columns]

        df = df[column_order]

        df = df.replace("", np.nan).replace(" ", np.nan)

        return df

    @property
    def html_events(self) -> list:
        """List of events scraped from HTML endpoint"""

        if self._html_events is None:
            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._scrape_html_events()
            self._munge_html_events()

        return self._html_events

    @property
    def html_events_df(self) -> pd.DataFrame:
        """Pandas Dataframe of events scraped from HTML endpoint"""

        if self._html_events is None:
            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._scrape_html_events()
            self._munge_html_events()

        return self._finalize_html_events()

    def _scrape_html_rosters(self) -> None:
        """Method for scraping players from HTML endpoint. Updates self._html_rosters"""

        # URL and scraping url

        url = self.html_rosters_endpoint

        s = self._requests_session

        try:
            page = s.get(url)
        except RetryError:
            return None

        # Continue if status code is bad

        if page.status_code == 404:
            return None

        # Reading the HTML file using beautiful soup package

        soup = BeautifulSoup(
            page.content.decode("ISO-8859-1"), "lxml", multi_valued_attributes=None
        )

        # Information for reading the HTML data

        td_dict = {
            "align": "center",
            "class": ["teamHeading + border", "teamHeading + border "],
            "width": "50%",
        }

        # Finding all active players in the html file

        teamsoup = soup.find_all("td", td_dict)

        # Dictionary for finding each team's table in the HTML file

        table_dict = {
            "align": "center",
            "border": "0",
            "cellpadding": "0",
            "cellspacing": "0",
            "width": "100%",
            "xmlns:ext": "",
        }

        # Dictionary to collect the team names

        team_names = {}

        # Dictionary to collect the team tables from the HTML data for iterating

        team_soup_list = []

        # List of teams for iterating

        team_list = ["away", "home"]

        # List to collect the player dictionaries during iteration

        player_list = []

        # Iterating through the home and away teams to collect names and tables

        for idx, team in enumerate(team_list):
            # Collecting team names

            team_name = unidecode(
                teamsoup[idx].get_text().encode("latin-1").decode("utf-8")
            ).upper()

            # Correcting the Coyotes team name

            if team_name == "PHOENIX COYOTES":
                team_name = "ARIZONA COYOTES"

            team_names.update({team: team_name})

            # Collecting tables of active players

            team_soup_list.append(
                (soup.find_all("table", table_dict))[idx].find_all("td")
            )

        # Iterating through the team's tables of active players

        for idx, team_soup in enumerate(team_soup_list):
            table_dict = {
                "align": "center",
                "border": "0",
                "cellpadding": "0",
                "cellspacing": "0",
                "width": "100%",
                "xmlns:ext": "",
            }

            stuff = soup.find_all("table", table_dict)[idx].find_all(
                "td", {"class": "bold"}
            )

            starters = list(np.reshape(stuff, (int(len(stuff) / 3), 3))[:, 2])

            # Getting length to create numpy array

            length = int(len(team_soup) / 3)

            # Creating a numpy array from the data, chopping off the headers to create my own

            active_array = np.array(team_soup).reshape(length, 3)

            # Getting original headers

            og_headers = active_array[0]

            if "Name" not in og_headers and "Nom/Name" not in og_headers:
                continue

            # Chop off the headers to create my own

            actives = active_array[1:]

            # Iterating through each player, or row in the array

            for player in actives:
                # New headers for the data. Original headers | ['#', 'Pos', 'Name']

                if len(player) == 3:
                    headers = ["jersey", "position", "player_name"]

                # Sometimes headers are missing

                else:
                    headers = ["jersey", "player_name"]

                # Creating dictionary with headers as keys from the player data

                player = dict(zip(headers, player))

                # Adding new values to the player dictionary

                new_values = {
                    "team_name": team_names.get(team_list[idx]),
                    "team_venue": team_list[idx].upper(),
                    "status": "ACTIVE",
                }

                if player["player_name"] in starters:
                    player["starter"] = 1

                else:
                    player["starter"] = 0

                player["player_name"] = (
                    re.sub(r"\(\s?(.*)\)", "", player["player_name"])
                    .strip()
                    .encode("latin-1")
                    .decode("utf-8")
                    .upper()
                )

                player["player_name"] = unidecode(player["player_name"])

                if "position" not in headers:
                    player["position"] = np.nan

                # Update the player's dictionary with new values

                player.update(new_values)

                # Append player dictionary to list of players

                player_list.append(player)

        # Check if scratches are present

        if len(soup.find_all("table", table_dict)) > 2:
            # If scratches are present, iterate through the team's scratch tables

            for idx, team in enumerate(team_list):
                # Getting team's scratches from HTML

                scratch_soup = (soup.find_all("table", table_dict))[idx + 2].find_all(
                    "td"
                )

                # Checking to see if there is at least one set of scratches (first row are headers)

                if len(scratch_soup) > 1:
                    # Getting the number of scratches

                    length = int(len(scratch_soup) / 3)

                    # Creating numpy array of scratches, removing headers

                    scratches = np.array(scratch_soup).reshape(length, 3)[1:]

                    # Iterating through the array

                    for player in scratches:
                        # New headers for the data. Original headers | ['#', 'Pos', 'Name']

                        if len(player) == 3:
                            headers = ["jersey", "position", "player_name"]

                        # Sometimes headers are missing

                        else:
                            headers = ["jersey", "player_name"]

                        # Creating dictionary with headers as keys from the player data

                        player = dict(zip(headers, player))

                        # Adding new values to the player dictionary

                        new_values = {
                            "team_name": team_names.get(team_list[idx]),
                            "team_venue": team_list[idx].upper(),
                            "starter": 0,
                            "status": "SCRATCH",
                        }

                        if "position" not in headers:
                            player["position"] = np.nan

                        player["player_name"] = (
                            re.sub(r"\(\s?(.*)\)", "", player["player_name"])
                            .strip()
                            .encode("latin-1")
                            .decode("utf-8")
                            .upper()
                        )

                        player["player_name"] = unidecode(player["player_name"])

                        # Updating player dictionary

                        player.update(new_values)

                        # Appending the player dictionary to the player list

                        player_list.append(player)

        self._html_rosters = player_list

    def _munge_html_rosters(self) -> None:
        """Method to munge list of players from HTML endpoint. Updates self._html_rosters"""

        season = self.season
        game_session = self.session

        # Iterating through each player to change information

        for player in self._html_rosters:
            # Fixing jersey data type

            player = html_rosters_fixes(self.game_id, player)

            player["jersey"] = int(player["jersey"])

            # Adding new values in a batch

            new_values = {
                "season": int(season),
                "session": game_session,
                "game_id": self.game_id,
            }

            player.update(new_values)

            player["player_name"] = (
                player["player_name"]
                .replace("ALEXANDRE", "ALEX")
                .replace("ALEXANDER", "ALEX")
                .replace("CHRISTOPHER", "CHRIS")
            )

            player["player_name"] = correct_names_dict.get(
                player["player_name"], player["player_name"]
            )

            # Creating Evolving Hockey ID

            player["eh_id"] = unidecode(player["player_name"])

            name_split = player["eh_id"].split(" ", maxsplit=1)

            player["eh_id"] = f"{name_split[0]}.{name_split[1]}"

            player["eh_id"] = player["eh_id"].replace("..", ".")

            # Correcting Evolving Hockey IDs for duplicates

            duplicates = {
                "SEBASTIAN.AHO": player["position"] == "D",
                "COLIN.WHITE": player["season"] >= 20162017,
                "SEAN.COLLINS": player["position"] != "D",
                "ALEX.PICARD": player["position"] != "D",
                "ERIK.GUSTAFSSON": player["season"] >= 20152016,
                "MIKKO.LEHTONEN": player["season"] >= 20202021,
                "NATHAN.SMITH": player["season"] >= 20212022,
                "DANIIL.TARASOV": player["position"] == "G",
            }

            # Iterating through the duplicate names and conditions

            for duplicate_name, condition in duplicates.items():
                if player["eh_id"] == duplicate_name and condition:
                    player["eh_id"] = f"{duplicate_name}2"

            # Something weird with Colin White

            if player["eh_id"] == "COLIN.":
                player["eh_id"] = "COLIN.WHITE2"

            player["team"] = team_codes.get(player["team_name"])

            player["team_jersey"] = f"{player['team']}{player['jersey']}"

    def _finalize_html_rosters(self) -> pd.DataFrame:
        """ "Method that creates and returns a Pandas DataFrame from self._html_rosters"""

        df = pd.DataFrame(self._html_rosters)

        column_order = [
            "season",
            "session",
            "game_id",
            "team",
            "team_name",
            "team_venue",
            "player_name",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "starter",
            "status",
        ]

        column_order = [x for x in column_order if x in df.columns]

        df = df[column_order]

        return df

    @property
    def html_rosters(self) -> list:
        """List of players scraped from HTML endpoint"""

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        return self._html_rosters

    @property
    def html_rosters_df(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from HTML endpoint"""

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        return self._finalize_html_rosters()

    def _combine_events(self) -> None:
        """Method to combine API and HTML events. Updates self._play_by_play"""

        html_events = self._html_events
        api_events = self._api_events

        game_list = []

        for event in html_events:
            if event["event"] == "EGPID":
                continue

            event_data = {}

            event_data.update(event)

            non_team_events = [
                "STOP",
                "ANTHEM",
                "PGSTR",
                "PGEND",
                "PSTR",
                "PEND",
                "EISTR",
                "EIEND",
                "GEND",
                "SOC",
                "EGT",
                "PBOX",
                "PRDY",
                "POFF",
                "GOFF",
            ]

            if event["event"] in non_team_events:
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                    and x["version"] == event["version"]
                ]

            elif event["event"] == "CHL" and event.get("event_team") is None:
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                    and x["version"] == event["version"]
                ]

            elif event["event"] == "CHL" and event.get("event_team") is not None:
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x.get("event_team") is not None
                    and event.get("event_team") is not None
                    and x["event_team"] == event["event_team"]
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                    and x["version"] == event["version"]
                ]

            elif event["event"] == "PENL":
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x["event_team"] == event["event_team"]
                    and x["player_1_eh_id"] == event["player_1_eh_id"]
                    and x.get("player_2_eh_id") == event.get("player_2_eh_id")
                    and x.get("player_3_eh_id") == event.get("player_3_eh_id")
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                ]

            elif event["event"] == "BLOCK" and event["player_1"] == "TEAMMATE":
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x.get("event_team") is not None
                    and event.get("event_team") is not None
                    and x["event_team"] == event["event_team"]
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                    and x["version"] == event["version"]
                ]

            else:
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x.get("event_team") is not None
                    and event.get("event_team") is not None
                    and x["event_team"] == event["event_team"]
                    and x.get("player_1_eh_id") is not None
                    and event.get("player_1_eh_id") is not None
                    and x["player_1_eh_id"] == event["player_1_eh_id"]
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                    and x["version"] == event["version"]
                ]

            if event["event"] == "FAC" and len(api_matches) == 0:
                api_matches = [
                    x
                    for x in api_events
                    if x["event"] == event["event"]
                    and x["period"] == event["period"]
                    and x["period_seconds"] == event["period_seconds"]
                    and x["version"] == event["version"]
                ]

            if len(api_matches) == 0:
                game_list.append(event_data)

                continue

            elif len(api_matches) == 1:
                api_match = api_matches[0]

                new_values = {
                    "event_idx_api": api_match.get("event_idx"),
                    "coords_x": api_match.get("coords_x"),
                    "coords_y": api_match.get("coords_y"),
                    "player_1_eh_id_api": api_match.get("player_1_eh_id"),
                    "player_1_api_id": api_match.get("player_1_api_id"),
                    "player_1_type": api_match.get("player_1_type"),
                    "player_2_eh_id_api": api_match.get("player_2_eh_id"),
                    "player_2_api_id": api_match.get("player_2_api_id"),
                    "player_2_type": api_match.get("player_2_type"),
                    "player_3_eh_id_api": api_match.get("player_3_eh_id"),
                    "player_3_api_id": api_match.get("player_3_api_id"),
                    "player_3_type": api_match.get("player_3_type"),
                    "version_api": api_match.get("version", 1),
                }

                event_data.update(new_values)

                if event["event"] == "BLOCK" and event["player_1"] == "TEAMMATE":
                    new_values = {
                        "player_1": api_match.get("player_1", event["player_1"]),
                        "player_1_eh_id": api_match.get(
                            "player_1_eh_id", event["player_1_eh_id"]
                        ),
                        "player_1_position": api_match.get(
                            "player_1_position", event["player_1_position"]
                        ),
                    }

                    event_data.update(new_values)

                game_list.append(event_data)

        game_list.extend(self._changes)

        for event in game_list:
            new_values = {
                "game_date": self.game_date,
                "home_team": self.home_team["abbrev"],
                "away_team": self.away_team["abbrev"],
            }

            event.update(new_values)

            if "version" not in event.keys():
                event["version"] = 1

            if event["period"] == 5 and event["session"] == "R":
                event["sort_value"] = event["event_idx"]

            else:
                sort_dict = {
                    "PGSTR": 1,
                    "PGEND": 2,
                    "ANTHEM": 3,
                    "EGT": 3,
                    "CHL": 3,
                    "DELPEN": 3,
                    "BLOCK": 3,
                    "GIVE": 3,
                    "HIT": 3,
                    "MISS": 3,
                    "SHOT": 3,
                    "TAKE": 3,
                    "GOAL": 5,
                    "STOP": 6,
                    "PENL": 7,
                    "PBOX": 7,
                    "PSTR": 7,
                    "CHANGE": 8,
                    "EISTR": 9,
                    "EIEND": 10,
                    "FAC": 12,
                    "PEND": 13,
                    "SOC": 14,
                    "GEND": 15,
                    "GOFF": 16,
                }

                event["sort_value"] = sort_dict[event["event"]]

        game_list = sorted(
            game_list, key=lambda k: (k["period"], k["period_seconds"], k["sort_value"])
        )  # , k['version']

        self._play_by_play = game_list

    def _munge_play_by_play(self) -> None:
        """Method to munge list of events and changes for play-by-play. Updates self._play_by_play"""

        game_session = self.session

        home_score = 0

        away_score = 0

        for event in self._play_by_play:
            if event.get("event_team") == event["home_team"]:
                event["opp_team"] = event["away_team"]

            elif event.get("event_team") == event["away_team"]:
                event["opp_team"] = event["home_team"]

            event["home_forwards_eh_id"] = []
            event["home_forwards_api_id"] = []
            event["home_forwards"] = []
            event["home_forwards_positions"] = []

            event["home_defense_eh_id"] = []
            event["home_defense_api_id"] = []
            event["home_defense"] = []
            event["home_defense_positions"] = []

            event["home_goalie_eh_id"] = []
            event["home_goalie_api_id"] = []
            event["home_goalie"] = []

            event["away_forwards_eh_id"] = []
            event["away_forwards_api_id"] = []
            event["away_forwards"] = []
            event["away_forwards_positions"] = []

            event["away_defense_eh_id"] = []
            event["away_defense_api_id"] = []
            event["away_defense"] = []
            event["away_defense_positions"] = []

            event["away_goalie_eh_id"] = []
            event["away_goalie_api_id"] = []
            event["away_goalie"] = []

            if event["event"] == "GOAL" and event["event_team"] == event["home_team"]:
                if game_session == "R" and event["period"] != 5:
                    home_score += 1

                elif game_session == "R" and event["period"] == 5:
                    ot_events = [
                        x
                        for x in self._play_by_play
                        if x["event"] in ["GOAL", "SHOT", "MISS"] and x["period"] == 5
                    ]

                    home_goals = [
                        x
                        for x in self._play_by_play
                        if x["event"] == "GOAL"
                        and x["period"] == 5
                        and x["event_team"] == event["home_team"]
                    ]

                    away_goals = [
                        x
                        for x in self._play_by_play
                        if x["event"] == "GOAL"
                        and x["period"] == 5
                        and x["event_team"] == event["away_team"]
                    ]

                    if event == ot_events[-1] and len(home_goals) > len(away_goals):
                        home_score += 1

                else:
                    home_score += 1

            elif event["event"] == "GOAL" and event["event_team"] == event["away_team"]:
                if game_session == "R" and event["period"] != 5:
                    away_score += 1

                elif game_session == "R" and event["period"] == 5:
                    ot_events = [
                        x
                        for x in self._play_by_play
                        if x["event"] in ["GOAL", "SHOT", "MISS"] and x["period"] == 5
                    ]

                    home_goals = [
                        x
                        for x in self._play_by_play
                        if x["event"] == "GOAL"
                        and x["period"] == 5
                        and x["event_team"] == event["home_team"]
                    ]

                    away_goals = [
                        x
                        for x in self._play_by_play
                        if x["event"] == "GOAL"
                        and x["period"] == 5
                        and x["event_team"] == event["away_team"]
                    ]

                    if event == ot_events[-1] and len(away_goals) > len(home_goals):
                        away_score += 1

                else:
                    away_score += 1

            event["home_score"] = home_score
            event["home_score_diff"] = home_score - away_score

            event["away_score"] = away_score
            event["away_score_diff"] = away_score - home_score

            event["score_state"] = f"{home_score}v{away_score}"
            event["score_diff"] = home_score - away_score

        roster = [x for x in self._rosters if x["status"] == "ACTIVE"]

        roster = sorted(roster, key=lambda k: (k["team_venue"], k["jersey"]))

        for player in roster:
            counter = 0

            for event in self._play_by_play:
                if (
                    event.get("event_team", "NaN") in player["team_jersey"]
                    and event["event"] == "CHANGE"
                    and event.get("change_on") is not None
                ):
                    players_on = [
                        x
                        for x in event["change_on_jersey"]
                        if x == player["team_jersey"]
                    ]

                    if len(players_on) > 0:
                        counter += 1

                if (
                    event.get("event_team", "NaN") in player["team_jersey"]
                    and event["event"] == "CHANGE"
                    and event.get("change_off") is not None
                ):
                    players_off = [
                        x
                        for x in event["change_off_jersey"]
                        if x == player["team_jersey"]
                    ]

                    if len(players_off) > 0:
                        counter -= 1

                if counter > 0:
                    forwards = ["L", "C", "R"]

                    if player["team_venue"] == "HOME":
                        if player["position"] in forwards:
                            event["home_forwards_eh_id"].append(player["eh_id"])
                            event["home_forwards_api_id"].append(str(player["api_id"]))
                            event["home_forwards"].append(player["player_name"])
                            event["home_forwards_positions"].append(player["position"])

                        elif player["position"] == "D":
                            event["home_defense_eh_id"].append(player["eh_id"])
                            event["home_defense_api_id"].append(str(player["api_id"]))
                            event["home_defense"].append(player["player_name"])
                            event["home_defense_positions"].append(player["position"])

                        elif player["position"] == "G":
                            event["home_goalie_eh_id"].append(player["eh_id"])
                            event["home_goalie_api_id"].append(str(player["api_id"]))
                            event["home_goalie"].append(player["player_name"])

                    else:
                        if player["position"] in forwards:
                            event["away_forwards_eh_id"].append(player["eh_id"])
                            event["away_forwards_api_id"].append(str(player["api_id"]))
                            event["away_forwards"].append(player["player_name"])

                        elif player["position"] == "D":
                            event["away_defense_eh_id"].append(player["eh_id"])
                            event["away_defense_api_id"].append(str(player["api_id"]))
                            event["away_defense"].append(player["player_name"])
                            event["away_defense_positions"].append(player["position"])

                        elif player["position"] == "G":
                            event["away_goalie_eh_id"].append(player["eh_id"])
                            event["away_goalie_api_id"].append(str(player["api_id"]))
                            event["away_goalie"].append(player["player_name"])

        # Instantiating shapely objects for high-danger and danger area computations

        high_danger1 = Polygon(np.array([[69, -9], [89, -9], [89, 9], [69, 9]]))
        high_danger2 = Polygon(np.array([[-69, -9], [-89, -9], [-89, 9], [-69, 9]]))

        danger1 = Polygon(
            np.array(
                [
                    [89, 9],
                    [89, -9],
                    [69, -22],
                    [54, -22],
                    [54, -9],
                    [44, -9],
                    [44, 9],
                    [54, 9],
                    [54, 22],
                    [69, 22],
                ]
            )
        )
        danger2 = Polygon(
            np.array(
                [
                    [-89, 9],
                    [-89, -9],
                    [-69, -22],
                    [-54, -22],
                    [-54, -9],
                    [-44, -9],
                    [-44, 9],
                    [-54, 9],
                    [-54, 22],
                    [-69, 22],
                ]
            )
        )

        for idx, event in enumerate(self._play_by_play):
            if idx == 0:
                event_length_idx = 0

            else:
                event_length_idx = idx - 1

            new_values = {
                "event_idx": idx + 1,
                "event_length": event["game_seconds"]
                - self._play_by_play[event_length_idx]["game_seconds"],
                "home_on_eh_id": event["home_forwards_eh_id"]
                + event["home_defense_eh_id"],
                "home_on_api_id": event["home_forwards_api_id"]
                + event["home_defense_api_id"],
                "home_on": event["home_forwards"] + event["home_defense"],
                "home_on_positions": event["home_forwards_positions"]
                + event["home_defense_positions"],
                "away_on_eh_id": event["away_forwards_eh_id"]
                + event["away_defense_eh_id"],
                "away_on_api_id": event["away_forwards_api_id"]
                + event["away_defense_api_id"],
                "away_on": event["away_forwards"] + event["away_defense"],
                "away_on_positions": event["away_forwards_positions"]
                + event["away_defense_positions"],
            }

            event.update(new_values)

            if event.get("event_team") == event["home_team"]:
                event["is_home"] = 1

            else:
                event["is_home"] = 0

            if event.get("event_team") == event["away_team"]:
                event["is_away"] = 1

            else:
                event["is_away"] = 0

            if (
                event.get("coords_x") is not None
                and event.get("coords_x") != ""
                and event.get("coords_y") is not None
                and event.get("coords_y") != ""
            ):
                # Fixing event angle and distance for errors

                is_fenwick = event["event"] in ["GOAL", "SHOT", "MISS"]
                is_long_distance = event.get("pbp_distance", 0) > 89
                x_is_neg = event.get("coords_x", 0) < 0
                x_is_pos = event.get("coords_x", 0) > 0
                bad_shots = event.get("shot_type", "WRIST") not in [
                    "TIP-IN",
                    "WRAP-AROUND",
                    "WRAP",
                    "DEFLECTED",
                    "BAT",
                    "BETWEEN LEGS",
                    "POKE",
                ]
                zone_cond = (
                    event.get("pbp_distance", 0) > 89 and event.get("zone") == "OFF"
                )

                x_is_neg_conds = (
                    is_fenwick
                    & is_long_distance
                    & x_is_neg
                    & bad_shots
                    & ~int(zone_cond)
                )
                x_is_pos_conds = (
                    is_fenwick
                    & is_long_distance
                    & x_is_pos
                    & bad_shots
                    & ~int(zone_cond)
                )

                if x_is_neg_conds is True:
                    event["event_distance"] = (
                        (abs(event["coords_x"]) + 89) ** 2 + event["coords_y"] ** 2
                    ) ** (1 / 2)

                    try:
                        event["event_angle"] = np.degrees(
                            abs(
                                np.arctan(
                                    event["coords_y"] / (abs(event["coords_x"] + 89))
                                )
                            )
                        )

                    except ZeroDivisionError:
                        event["event_angle"] = np.degrees(abs(np.arctan(np.nan)))

                elif x_is_pos_conds is True:
                    event["event_distance"] = (
                        (event["coords_x"] + 89) ** 2 + event["coords_y"] ** 2
                    ) ** (1 / 2)

                    try:
                        event["event_angle"] = np.degrees(
                            abs(np.arctan(event["coords_y"] / (event["coords_x"] + 89)))
                        )

                    except ZeroDivisionError:
                        event["event_angle"] = np.degrees(abs(np.arctan(np.nan)))

                else:
                    event["event_distance"] = (
                        (89 - abs(event["coords_x"])) ** 2 + event["coords_y"] ** 2
                    ) ** (1 / 2)

                    try:
                        event["event_angle"] = np.degrees(
                            abs(
                                np.arctan(
                                    event["coords_y"] / (89 - abs(event["coords_x"]))
                                )
                            )
                        )

                    except ZeroDivisionError:
                        event["event_angle"] = np.degrees(abs(np.arctan(np.nan)))

            if (
                event["event"] in ["GOAL", "SHOT", "MISS"]
                and event.get("zone") == "DEF"
                and event.get("event_distance", 0) <= 64
            ):
                event["zone"] = "OFF"

            if event["event"] in ["GOAL", "SHOT", "MISS"]:
                if event.get("zone") == "OFF":
                    if (
                        event.get("coords_x") is not None
                        and event.get("coords_y") is not None
                    ):
                        shot_coords = Point(event["coords_x"], event["coords_y"])

                        if danger1.contains(shot_coords) or danger2.contains(
                            shot_coords
                        ):
                            event["danger"] = 1

                        else:
                            event["danger"] = 0

                        if high_danger1.contains(shot_coords) or high_danger2.contains(
                            shot_coords
                        ):
                            event["high_danger"] = 1

                            event["danger"] = 0

                        else:
                            event["high_danger"] = 0

                    else:
                        event["high_danger"] = 0

                        event["danger"] = 0

                else:
                    event["high_danger"] = 0

                    event["danger"] = 0

            event["home_skaters"] = len(event["home_on_eh_id"])

            event["away_skaters"] = len(event["away_on_eh_id"])

            if not event["home_goalie"]:
                home_on = "E"

            else:
                home_on = event["home_skaters"]

            if not event["away_goalie"]:
                away_on = "E"

            else:
                away_on = event["away_skaters"]

            event["strength_state"] = f"{home_on}v{away_on}"

            if "PENALTY SHOT" in event["description"]:
                event["strength_state"] = "1v0"

            if event.get("event_team") == event["home_team"]:
                new_values = {
                    "strength_state": f"{home_on}v{away_on}",
                    "score_state": f"{event['home_score']}v{event['away_score']}",
                    "score_diff": event["home_score_diff"],
                    "event_team_skaters": event["home_skaters"],
                    "teammates_eh_id": event["home_on_eh_id"],
                    "teammates_api_id": event["home_on_api_id"],
                    "teammates": event["home_on"],
                    "teammates_positions": event["home_on_positions"],
                    "forwards_eh_id": event["home_forwards_eh_id"],
                    "forwards_api_id": event["home_forwards_api_id"],
                    "forwards": event["home_forwards"],
                    "defense_eh_id": event["home_defense_eh_id"],
                    "defense_api_id": event["home_defense_api_id"],
                    "defense": event["home_defense"],
                    "own_goalie_eh_id": event["home_goalie_eh_id"],
                    "own_goalie_api_id": event["home_goalie_api_id"],
                    "own_goalie": event["home_goalie"],
                    "opp_strength_state": f"{away_on}v{home_on}",
                    "opp_score_state": f"{event['away_score']}v{event['home_score']}",
                    "opp_score_diff": event["away_score_diff"],
                    "opp_team_skaters": event["away_skaters"],
                    "opp_team_on_eh_id": event["away_on_eh_id"],
                    "opp_team_on_api_id": event["away_on_api_id"],
                    "opp_team_on": event["away_on"],
                    "opp_forwards_eh_id": event["away_forwards_eh_id"],
                    "opp_forwards_api_id": event["away_forwards_api_id"],
                    "opp_forwards": event["away_forwards"],
                    "opp_defense_eh_id": event["away_defense_eh_id"],
                    "opp_defense_api_id": event["away_defense_api_id"],
                    "opp_defense": event["away_defense"],
                    "opp_goalie_eh_id": event["away_goalie_eh_id"],
                    "opp_goalie_api_id": event["away_goalie_api_id"],
                    "opp_goalie": event["away_goalie"],
                }

                event.update(new_values)

            elif event.get("event_team") == event["away_team"]:
                new_values = {
                    "strength_state": f"{away_on}v{home_on}",
                    "score_state": f"{event['away_score']}v{event['home_score']}",
                    "score_diff": event["away_score_diff"],
                    "event_team_skaters": event["away_skaters"],
                    "teammates_eh_id": event["away_on_eh_id"],
                    "teammates_api_id": event["away_on_api_id"],
                    "teammates": event["away_on"],
                    "teammates_positions": event["away_on_positions"],
                    "forwards_eh_id": event["away_forwards_eh_id"],
                    "forwards_api_id": event["away_forwards_api_id"],
                    "forwards": event["away_forwards"],
                    "defense_eh_id": event["away_defense_eh_id"],
                    "defense_api_id": event["away_defense_api_id"],
                    "defense": event["away_defense"],
                    "own_goalie_eh_id": event["away_goalie_eh_id"],
                    "own_goalie_api_id": event["away_goalie_api_id"],
                    "own_goalie": event["away_goalie"],
                    "opp_strength_state": f"{home_on}v{away_on}",
                    "opp_score_state": f"{event['home_score']}v{event['away_score']}",
                    "opp_score_diff": event["home_score_diff"],
                    "opp_team_skaters": event["home_skaters"],
                    "opp_team_on_eh_id": event["home_on_eh_id"],
                    "opp_team_on_api_id": event["home_on_api_id"],
                    "opp_team_on": event["home_on"],
                    "opp_team_on_positions": event["home_on_positions"],
                    "opp_forwards_eh_id": event["home_forwards_eh_id"],
                    "opp_forwards_api_id": event["home_forwards_api_id"],
                    "opp_forwards": event["home_forwards"],
                    "opp_defense_eh_id": event["home_defense_eh_id"],
                    "opp_defense_api_id": event["home_defense_api_id"],
                    "opp_defense": event["home_defense"],
                    "opp_goalie_eh_id": event["home_goalie_eh_id"],
                    "opp_goalie_api_id": event["home_goalie_api_id"],
                    "opp_goalie": event["home_goalie"],
                }

                event.update(new_values)

            if (event["home_skaters"] > 5 and event["home_goalie"] != []) or (
                event["away_skaters"] > 5 and event["away_goalie"] != []
            ):
                event["strength_state"] = "ILLEGAL"

                event["opp_strength_state"] = "ILLEGAL"

            if event["period"] == 5 and event["session"] == "R":
                event["strength_state"] = "1v0"

            if event["event"] == "CHANGE":
                faceoffs = [
                    x
                    for x in self._play_by_play
                    if (
                        x["event"] == "FAC"
                        and x["game_seconds"] == event["game_seconds"]
                        and x["period"] == event["period"]
                    )
                ]

                if len(faceoffs) > 0:
                    game_seconds_list = [x["game_seconds"] for x in self._play_by_play]

                    max_seconds = max(game_seconds_list)

                    bad_seconds = [0, 1200, 2400, 3600, 3900, max_seconds]

                    if event["game_seconds"] not in bad_seconds:
                        event["coords_x"] = faceoffs[0].get("coords_x", "")

                        event["coords_y"] = faceoffs[0].get("coords_y", "")

                        if event["event_team"] == faceoffs[0]["event_team"]:
                            event["zone_start"] = faceoffs[0]["zone"]

                        else:
                            zones = {"OFF": "DEF", "DEF": "OFF", "NEU": "NEU"}

                            event["zone_start"] = zones[faceoffs[0]["zone"]]

                else:
                    event["zone_start"] = "OTF"

            event_dummies = [
                "block",
                "change",
                "chl",
                "fac",
                "give",
                "goal",
                "hit",
                "miss",
                "penl",
                "shot",
                "stop",
                "take",
            ]

            for event_dummy in event_dummies:
                if event["event"].lower() == event_dummy:
                    event[event_dummy] = 1

                else:
                    event[event_dummy] = 0

            if event["event"] == "GOAL" or event["event"] == "SHOT":
                event["shot"] = 1

            fenwick_events = ["SHOT", "GOAL", "MISS"]

            if event["event"] in fenwick_events:
                event["fenwick"] = 1

            else:
                event["fenwick"] = 0

            corsi_events = fenwick_events + ["BLOCK"]

            if event["event"] in corsi_events:
                event["corsi"] = 1

            else:
                event["corsi"] = 0

            if event["event"] == "FAC":
                if event["zone"] == "OFF":
                    event["ozf"] = 1

                else:
                    event["ozf"] = 0

                if event["zone"] == "DEF":
                    event["dzf"] = 1

                else:
                    event["dzf"] = 0

                if event["zone"] == "NEU":
                    event["nzf"] = 1

                else:
                    event["nzf"] = 0

            else:
                event["ozf"] = 0
                event["nzf"] = 0
                event["dzf"] = 0

            if event["event"] == "CHANGE" and event.get("zone_start") is not None:
                if event["zone_start"] == "OFF":
                    event["ozc"] = 1

                else:
                    event["ozc"] = 0

                if event["zone_start"] == "DEF":
                    event["dzc"] = 1

                else:
                    event["dzc"] = 0

                if event["zone_start"] == "NEU":
                    event["nzc"] = 1

                else:
                    event["nzc"] = 0

                if event["zone_start"] == "OTF":
                    event["otf"] = 1

                else:
                    event["otf"] = 0

            else:
                event["ozc"] = 0
                event["nzc"] = 0
                event["dzc"] = 0
                event["otf"] = 0

            if event["event"] == "PENL":
                penalty_lengths = [0, 2, 4, 5, 10]

                for penalty_length in penalty_lengths:
                    if event.get("penalty_length") == penalty_length:
                        event[f"pen{penalty_length}"] = 1

                    else:
                        event[f"pen{penalty_length}"] = 0

            else:
                event["pen0"] = 0
                event["pen2"] = 0
                event["pen4"] = 0
                event["pen5"] = 0
                event["pen10"] = 0

    def _finalize_play_by_play(self) -> pd.DataFrame:
        """Method that creates and returns a Pandas DataFrame from self._play_by_play"""

        list_fields = [
            "home_on",
            "home_on_eh_id",
            "home_on_api_id",
            "home_on_positions",
            "home_forwards",
            "home_forwards_eh_id",
            "home_forwards_api_id",
            "home_forwards_positions",
            "home_defense",
            "home_defense_eh_id",
            "home_defense_api_id",
            "home_defense_positions",
            "home_goalie",
            "home_goalie_eh_id",
            "home_goalie_api_id",
            "away_on",
            "away_on_eh_id",
            "away_on_api_id",
            "away_on_positions",
            "away_forwards",
            "away_forwards_eh_id",
            "away_forwards_api_id",
            "away_forwards_positions",
            "away_defense",
            "away_defense_eh_id",
            "away_defense_api_id",
            "away_defense_positions",
            "away_goalie",
            "away_goalie_eh_id",
            "away_goalie_api_id",
            "teammates",
            "teammates_eh_id",
            "teammates_api_id",
            "teammates_positions",
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_team_on",
            "opp_team_on_eh_id",
            "opp_team_on_api_id",
            "opp_team_on_positions",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "change_on",
            "change_on_eh_id",
            "change_on_positions",
            "change_off",
            "change_off_eh_id",
            "change_off_positions",
            "change_on_forwards",
            "change_on_forwards_eh_id",
            "change_off_forwards",
            "change_off_forwards_eh_id",
            "change_on_defense",
            "change_on_defense_eh_id",
            "change_off_defense",
            "change_off_defense_eh_id",
            "change_on_goalie",
            "change_on_goalie_eh_id",
            "change_off_goalie",
            "change_off_goalie_eh_id",
        ]

        events = [x.copy() for x in self._play_by_play]

        for event in events:
            for list_field in [x for x in list_fields if x in event.keys()]:
                event[list_field] = ", ".join(event[list_field])

        df = pd.DataFrame(events)

        goalie_cols = [
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "home_goalie",
            "home_goalie_eh_id",
            "home_goalie_api_id",
            "away_goalie",
            "away_goalie_eh_id",
            "away_goalie_api_id",
        ]

        df[goalie_cols] = df[goalie_cols].fillna("EMPTY NET")

        df = df.replace("", np.nan).replace(" ", np.nan)

        columns = [
            "season",
            "session",
            "game_id",
            "game_date",
            "event_idx",
            "period",
            "period_seconds",
            "game_seconds",
            "strength_state",
            "score_state",
            "score_diff",
            "event_team",
            "opp_team",
            "event",
            "description",
            "zone",
            "coords_x",
            "coords_y",
            "danger",
            "high_danger",
            "player_1",
            "player_1_eh_id",
            "player_1_eh_id_api",
            "player_1_api_id",
            "player_1_position",
            "player_1_type",
            "player_2",
            "player_2_eh_id",
            "player_2_eh_id_api",
            "player_2_api_id",
            "player_2_position",
            "player_2_type",
            "player_3",
            "player_3_eh_id",
            "player_3_eh_id_api",
            "player_3_api_id",
            "player_3_position",
            "player_3_type",
            "shot_type",
            "event_length",
            "event_distance",
            "event_angle",
            "pbp_distance",
            "event_detail",
            "penalty",
            "penalty_length",
            "penalty_severity",
            "home_score",
            "home_score_diff",
            "away_score",
            "away_score_diff",
            "is_home",
            "is_away",
            "home_team",
            "away_team",
            "home_skaters",
            "away_skaters",
            "event_team_skaters",
            "teammates",
            "teammates_eh_id",
            "teammates_api_id",
            "teammates_positions",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "opp_strength_state",
            "opp_score_state",
            "opp_score_diff",
            "opp_team_skaters",
            "opp_team_on",
            "opp_team_on_eh_id",
            "opp_team_on_api_id",
            "opp_team_on_positions",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "home_on",
            "home_on_eh_id",
            "home_on_api_id",
            "home_on_positions",
            "home_goalie",
            "home_goalie_eh_id",
            "home_goalie_api_id",
            "home_forwards",
            "home_forwards_eh_id",
            "home_forwards_api_id",
            "home_defense",
            "home_defense_eh_id",
            "home_defense_api_id",
            "away_on",
            "away_on_eh_id",
            "away_on_api_id",
            "away_on_positions",
            "away_goalie",
            "away_goalie_eh_id",
            "away_goalie_api_id",
            "away_forwards",
            "away_forwards_eh_id",
            "away_forwards_api_id",
            "away_defense",
            "away_defense_eh_id",
            "away_defense_api_id",
            "zone_start",
            "change_on_count",
            "change_off_count",
            "change_on",
            "change_on_id",
            "change_on_positions",
            "change_off",
            "change_off_id",
            "change_off_positions",
            "change_on_forwards_count",
            "change_off_forwards_count",
            "change_on_forwards",
            "change_on_forwards_id",
            "change_off_forwards",
            "change_off_forwards_id",
            "change_on_defense_count",
            "change_off_defense_count",
            "change_on_defense",
            "change_on_defense_id",
            "change_off_defense",
            "change_off_defense_id",
            "change_on_goalie_count",
            "change_off_goalie_count",
            "change_on_goalie",
            "change_on_goalie_id",
            "change_off_goalie",
            "change_off_goalie_id",
            "version",
            "block",
            "change",
            "chl",
            "corsi",
            "fac",
            "fenwick",
            "give",
            "goal",
            "hit",
            "miss",
            "penl",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
            "shot",
            "stop",
            "take",
            "dzf",
            "nzf",
            "ozf",
            "dzc",
            "nzc",
            "ozc",
            "otf",
        ]

        columns = [x for x in columns if x in df.columns]

        df = df[columns]

        return df

    @property
    def play_by_play(self) -> list:
        """List of events in play-by-play"""

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        if self._html_events is None:
            self._scrape_html_events()
            self._munge_html_events()

        if self._changes is None:
            self._scrape_shifts()
            self._munge_shifts()

            self._munge_changes()

        if self._api_rosters is None:
            self._munge_api_rosters()

        if self._rosters is None:
            self._combine_rosters()

        if self._api_events is None:
            self._munge_api_events()

        if self._play_by_play is None:
            self._combine_events()
            self._munge_play_by_play()

        return self._play_by_play

    @property
    def play_by_play_df(self) -> pd.DataFrame:
        """Pandas Dataframe of play-by-play data"""

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        if self._html_events is None:
            self._scrape_html_events()
            self._munge_html_events()

        if self._changes is None:
            self._scrape_shifts()
            self._munge_shifts()

            self._munge_changes()

        if self._api_rosters is None:
            self._munge_api_rosters()

        if self._rosters is None:
            self._combine_rosters()

        if self._api_events is None:
            self._munge_api_events()

        if self._play_by_play is None:
            self._combine_events()
            self._munge_play_by_play()

        return self._finalize_play_by_play()

    def _combine_rosters(self) -> None:
        """Method to combine API and HTML rosters. Updates self._rosters"""

        html_rosters = self._html_rosters
        api_rosters = self._api_rosters

        api_rosters_dict = {x["team_jersey"]: x for x in api_rosters}

        players = []

        for player in html_rosters:
            if player["status"] == "ACTIVE":
                api_info = api_rosters_dict[player["team_jersey"]]

            else:
                api_info = {
                    "api_id": 0,
                    "headshot_url": "",
                }

            player_info = {}

            player_info.update(player)

            new_values = {
                "api_id": api_info["api_id"],
                "headshot_url": api_info["headshot_url"],
            }

            player_info.update(new_values)

            players.append(player_info)

        self._rosters = players

    def _finalize_rosters(self) -> pd.DataFrame:
        """Method that creates and returns a Pandas DataFrame from self._rosters"""

        df = pd.DataFrame(self._rosters)

        columns = [
            "season",
            "session",
            "game_id",
            "team",
            "team_venue",
            "player_name",
            "api_id",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "starter",
            "status",
            "headshot_url",
        ]

        columns = [x for x in columns if x in df.columns]

        df = df[columns]

        return df

    @property
    def rosters(self) -> list:
        """List of players scraped from API & HTML endpoints"""

        if self._api_rosters is None:
            self._munge_api_rosters()

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        if self._rosters is None:
            self._combine_rosters()

        return self._rosters

    @property
    def rosters_df(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from API & HTML endpoints"""

        if self._rosters is None:
            if self._api_rosters is None:
                self._munge_api_rosters()

            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._combine_rosters()

        return self._finalize_rosters()

    def _scrape_shifts(self) -> None:
        """Method for scraping shifts from HTML endpoint. Updates self._shifts"""

        # Creating basic information from game ID
        season = self.season
        game_session = self.session
        game_id = self.game_id

        # This is the list for collecting all the game information for the end

        game_list = []

        # Dictionary of urls for scraping

        urls_dict = {
            "HOME": self.home_shifts_endpoint,
            "AWAY": self.away_shifts_endpoint,
        }

        # Iterating through the url dictionary

        for team_venue, url in urls_dict.items():
            response = requests.get(url)

            soup = BeautifulSoup(
                response.content.decode("ISO-8859-1"),
                "lxml",
                multi_valued_attributes=None,
            )

            # Getting team names from the HTML Data

            team_name = soup.find(
                "td", {"align": "center", "class": "teamHeading + border"}
            )

            # Converting team names to proper format

            if team_name is None:
                continue

            team_name = unidecode(team_name.get_text())

            if team_name == "PHOENIX COYOTES":
                team_name = "ARIZONA COYOTES"

            elif "CANADIENS" in team_name:
                team_name = "MONTREAL CANADIENS"

            # Getting players from the HTML data

            players = soup.find_all(
                "td", {"class": ["playerHeading + border", "lborder + bborder"]}
            )

            # Creating a dictionary to collect the players' information

            players_dict = {}

            # Iterating through the players

            for player in players:
                # Getting player's data

                data = player.get_text()

                # If there is a name in the data, get the information

                if ", " in data:
                    name = data.split(",", 1)

                    jersey = name[0].split(" ")[0].strip()

                    last_name = name[0].split(" ", 1)[1].strip()

                    first_name = re.sub(r"\(\s?(.+)\)", "", name[1]).strip()

                    full_name = f"{first_name} {last_name}"

                    if full_name == " ":
                        continue

                    new_values = {
                        full_name: {
                            "player_name": full_name,
                            "jersey": jersey,
                            "shifts": [],
                        }
                    }

                    players_dict.update(new_values)

                # If there is not a name it is likely because these are shift information, not player information

                else:
                    if full_name == " ":
                        continue

                    # Extend the player's shift information with the shift data

                    players_dict[full_name]["shifts"].extend([data])

            # Iterating through the player's dictionary,
            # which has a key of the player's name and an array of shift-arrays

            for player, shifts in players_dict.items():
                # Getting the number of shifts

                length = int(len(np.array(shifts["shifts"])) / 5)

                # Reshaping the shift data into fields and values

                for number, shift in enumerate(
                    np.array(shifts["shifts"]).reshape(length, 5)
                ):
                    # Adding header values to the shift data

                    headers = [
                        "shift_count",
                        "period",
                        "shift_start",
                        "shift_end",
                        "duration",
                    ]

                    # Creating a dictionary from the headers and the shift data

                    shift_dict = dict(zip(headers, shift.flatten()))

                    # Adding other data to the shift dictionary

                    new_values = {
                        "season": season,
                        "session": game_session,
                        "game_id": game_id,
                        "team_name": team_name,
                        "team": team_codes[team_name],
                        "team_venue": team_venue.upper(),
                        "player_name": unidecode(shifts["player_name"]).upper(),
                        "team_jersey": f"{team_codes[team_name]}{shifts['jersey']}",
                        "jersey": int(shifts["jersey"]),
                        "period": int(
                            shift_dict["period"].replace("OT", "4").replace("SO", "5")
                        ),
                        "shift_count": int(shift_dict["shift_count"]),
                        "shift_start": unidecode(shift_dict["shift_start"]).strip(),
                        "start_time": unidecode(shift_dict["shift_start"])
                        .strip()
                        .split("/", 1)[0]
                        .strip(),
                        "shift_end": unidecode(shift_dict["shift_end"]).strip(),
                        "end_time": unidecode(shift_dict["shift_end"])
                        .strip()
                        .split("/", 1)[0]
                        .strip(),
                    }

                    shift_dict.update(new_values)

                    # Appending the shift dictionary to the list of shift dictionaries

                    if shift_dict["start_time"] != "31:23":
                        game_list.append(shift_dict)

        self._shifts = game_list

    def _munge_shifts(self) -> None:
        """Method to munge list of shifts from HTML endpoint. Updates self._shifts"""

        season = self.season
        game_session = self.session

        # Iterating through the lists of shifts

        roster = self._html_rosters

        actives = {x["team_jersey"]: x for x in roster if x["status"] == "ACTIVE"}
        scratches = {x["team_jersey"]: x for x in roster if x["status"] == "SCRATCH"}

        if self.game_id == 2020020860:
            new_shifts = {
                "DAL29": 5,
                "CHI60": 4,
                "DAL14": 27,
                "DAL21": 22,
                "DAL3": 28,
                "CHI5": 27,
                "CHI88": 26,
                "CHI12": 26,
            }

            for new_player, shift_count in new_shifts.items():
                new_player_info = actives[new_player]

                new_goalies = ["DAL29", "CHI60"]

                if new_player in new_goalies:
                    shift_start = "0:00 / 5:00"
                    shift_end = "4:30 / 0:30"
                    duration = "4:30"
                    start_time = "0:00"
                    end_time = "4:30"

                new_players = ["DAL14", "DAL21", "DAL3", "CHI5"]

                if new_player in new_players:
                    shift_start = "3:47 / 1:13"
                    shift_end = "4:30 / 0:30"
                    duration = "00:43"
                    start_time = "3:47"
                    end_time = "4:30"

                if new_player == "CHI88":
                    shift_start = "3:51 / 1:09"
                    shift_end = "4:30 / 0:30"
                    duration = "00:39"
                    start_time = "3:51"
                    end_time = "4:30"

                if new_player == "CHI12":
                    shift_start = "4:14 / 0:46"
                    shift_end = "4:30 / 0:30"
                    duration = "00:16"
                    start_time = "4:14"
                    end_time = "4:30"

                new_shift = {
                    "shift_count": shift_count,
                    "period": 4,
                    "shift_start": shift_start,
                    "shift_end": shift_end,
                    "duration": duration,
                    "season": 20202021,
                    "session": "R",
                    "game_id": self.game_id,
                    "team_name": new_player_info["team_name"],
                    "team": new_player_info["team"],
                    "team_venue": new_player_info["team_venue"],
                    "player_name": new_player_info["player_name"],
                    "team_jersey": new_player_info["team_jersey"],
                    "jersey": new_player_info["jersey"],
                    "start_time": start_time,
                    "end_time": end_time,
                }

                self._shifts.append(new_shift)

        for shift in self._shifts:
            # Get active players and store them in a new dictionary with team jersey as key
            # and other info as a value-dictionary

            shift["eh_id"] = actives.get(
                shift["team_jersey"], scratches.get(shift["team_jersey"])
            )["eh_id"]

            shift["position"] = actives.get(
                shift["team_jersey"], scratches.get(shift["team_jersey"])
            )["position"]

            # Replacing some player names

            shift["player_name"] = (
                shift["player_name"]
                .replace("ALEXANDRE", "ALEX")
                .replace("ALEXANDER", "ALEX")
                .replace("CHRISTOPHER", "CHRIS")
            )

            shift["player_name"] = correct_names_dict.get(
                shift["player_name"], shift["player_name"]
            )

            # Adding seconds columns

            cols = ["start_time", "end_time", "duration"]

            for col in cols:
                time_split = shift[col].split(":", 1)

                # Sometimes the shift value can be blank, if it is, we'll skip the field and fix later

                try:
                    shift[f"{col}_seconds"] = 60 * int(time_split[0]) + int(
                        time_split[1]
                    )

                except ValueError:
                    continue

            # Fixing end time if it is blank or empty

            if shift["end_time"] == " " or shift["end_time"] == "":
                # Calculating end time based on duration seconds

                shift["end_time_seconds"] = (
                    shift["start_time_seconds"] + shift["duration_seconds"]
                )

                # Creating end time based on time delta

                shift["end_time"] = str(
                    timedelta(seconds=shift["end_time_seconds"])
                ).split(":", 1)[1]

            # If the shift start is after the shift end, we need to fix the error

            if shift["start_time_seconds"] > shift["end_time_seconds"]:
                # Creating new values based on game session and period

                if shift["period"] < 4:
                    # Setting the end time

                    shift["end_time"] = "20:00"

                    # Setting the end time in seconds

                    shift["end_time_seconds"] = 1200

                    # Setting the shift end

                    shift["shift_end"] = "20:00 / 0:00"

                    # Setting duration and duration in seconds

                    shift["duration_seconds"] = (
                        shift["end_time_seconds"] - shift["start_time_seconds"]
                    )

                    shift["duration"] = str(
                        timedelta(seconds=shift["duration_seconds"])
                    ).split(":", 1)[1]

                else:
                    if game_session == "P":
                        total_seconds = 1200

                    else:
                        total_seconds = 300

                    # Need to get the end period to get the end time in seconds

                    max_period = max(
                        [
                            int(shift["period"])
                            for shift in self._shifts
                            if shift["period"] != " "
                        ]
                    )

                    # Getting the end time in seconds for the final period

                    max_seconds = max(
                        [
                            shift["end_time_seconds"]
                            for shift in self._shifts
                            if "end_time_seconds" in shift.keys()
                            and shift["period"] == max_period
                        ]
                    )

                    shift["end_time_seconds"] = max_seconds

                    # Setting end time

                    end_time = str(timedelta(seconds=max_seconds)).split(":", 1)[1]

                    # Setting remainder time

                    remainder = str(
                        timedelta(seconds=(total_seconds - max_seconds))
                    ).split(":", 1)[1]

                    shift["end_time"] = end_time

                    shift["shift_end"] = f"{end_time} / {remainder}"

            # Setting goalie values

            if shift["position"] == "G":
                shift["goalie"] = 1

            else:
                shift["goalie"] = 0

            # Setting home and away values

            if shift["team_venue"] == "HOME":
                shift["is_home"] = 1

                shift["is_away"] = 0

            else:
                shift["is_home"] = 0

                shift["is_away"] = 1

        periods = np.unique([x["period"] for x in self._shifts]).tolist()

        # Setting list of teams to iterate through while iterating through the periods

        teams = ["HOME", "AWAY"]

        for period in periods:
            # Getting max seconds for the period

            max_seconds = max(
                [
                    int(x["end_time_seconds"])
                    for x in self._shifts
                    if x["period"] == period
                ]
            )

            # Iterating through home and away teams

            for team in teams:
                # Getting the team's goalies for the game

                team_goalies = [
                    x
                    for x in self._shifts
                    if x["goalie"] == 1 and x["team_venue"] == team
                ]

                # Getting the goalies for the period

                goalies = [
                    x
                    for x in self._shifts
                    if x["goalie"] == 1
                    and x["team_venue"] == team
                    and x["period"] == period
                ]

                # If there are no goalies changing during the period, we need to add them

                if len(goalies) < 1:
                    if period == 1:
                        if len(team_goalies) < 1:
                            first_goalie = {}

                            starter = [
                                x
                                for x in actives.values()
                                if x["position"] == "G"
                                and x["team_venue"] == team
                                and x["starter"] == 1
                            ][0]

                            new_values = {
                                "season": season,
                                "session": game_session,
                                "game_id": self.game_id,
                                "period": period,
                                "team_venue": team,
                                "goalie": 1,
                                "shift_count": 1,
                            }

                            new_values.update(starter)

                            if team == "HOME":
                                new_values.update({"is_home": 1, "is_away": 0})

                            else:
                                new_values.update({"is_away": 1, "is_home": 0})

                            first_goalie.update(new_values)

                        else:
                            first_goalie = team_goalies[0]

                        # Initial dictionary is set using data from the first goalie to appear

                        goalie_shift = dict(first_goalie)

                    else:
                        # Initial dictionary is set using data from the pervious goalie to appear

                        prev_goalie = [
                            x for x in team_goalies if x["period"] == (period - 1)
                        ][-1]

                        goalie_shift = dict(prev_goalie)

                    # Setting goalie shift number so we can identify later

                    goalie_shift["number"] = 0

                    # Setting the period for the current period

                    goalie_shift["period"] = period

                    # Setting the start time

                    goalie_shift["start_time"] = "0:00"

                    # Setting the start time in seconds

                    goalie_shift["start_time_seconds"] = 0

                    # If during regular time

                    if period < 4:
                        # Setting shift start value

                        goalie_shift["shift_start"] = "0:00 / 20:00"

                        if max_seconds < 1200:
                            # Setting end time value

                            goalie_shift["end_time"] = "20:00"

                            # Setting end time in seconds

                            goalie_shift["end_time_seconds"] = 1200

                            # Setting the duration, assuming they were out there the whole time

                            goalie_shift["duration"] = "20:00"

                            # Setting the duration in seconds, assuming they were out there the whole time

                            goalie_shift["duration_seconds"] = 1200

                            # Setting the shift end value

                            goalie_shift["shift_end"] = "20:00 / 0:00"

                    # If the period is greater than 3

                    else:
                        # Need to account for whether regular season or playoffs

                        if game_session == "P":
                            goalie_shift["shift_start"] = "0:00 / 20:00"

                            total_seconds = 1200

                        else:
                            goalie_shift["shift_start"] = "0:00 / 5:00"

                            total_seconds = 300

                        if max_seconds < total_seconds:
                            # Getting end time

                            end_time = str(timedelta(seconds=max_seconds)).split(
                                ":", 1
                            )[1]

                            # Getting remainder time

                            remainder = str(
                                timedelta(seconds=(total_seconds - max_seconds))
                            ).split(":", 1)[1]

                            # Setting values

                            goalie_shift["end_time_seconds"] = max_seconds

                            goalie_shift["end_time"] = end_time

                            goalie_shift["shift_end"] = f"{end_time} / {remainder}"

                    # Appending the new goalie shift to the game list

                    self._shifts.append(goalie_shift)

            # Iterating through the shifts

            for shift in self._shifts:
                # Fixing goalie errors

                if (
                    shift["goalie"] == 1
                    and shift["period"] == period
                    and shift["shift_end"] == "0:00 / 0:00"
                ):
                    if period < 4:
                        shift["shift_end"] = "20:00 / 0:00"

                        shift["end_time"] = "20:00"

                        shift["end_time_seconds"] = 1200

                    else:
                        if game_session == "R":
                            total_seconds = 300

                        else:
                            total_seconds = 1200

                        end_time = str(timedelta(seconds=max_seconds)).split(":", 1)[1]

                        remainder = str(
                            timedelta(seconds=(total_seconds - max_seconds))
                        ).split(":", 1)[1]

                        shift["end_time_seconds"] = max_seconds

                        shift["end_time"] = end_time

                        shift["shift_end"] = f"{end_time} / {remainder}"

    def _finalize_shifts(self) -> pd.DataFrame:
        """ "Method that creates and returns a Pandas DataFrame from self._shifts"""

        df = pd.DataFrame(self._shifts)

        column_order = [
            "season",
            "session",
            "game_id",
            "team",
            "team_name",
            "team_venue",
            "player_name",
            "eh_id",
            "team_jersey",
            "position",
            "jersey",
            "shift_count",
            "period",
            "start_time",
            "end_time",
            "duration",
            "start_time_seconds",
            "end_time_seconds",
            "duration_seconds",
            "shift_start",
            "shift_end",
            "goalie",
            "is_home",
        ]

        column_order = [x for x in column_order if x in df.columns]

        df = df[column_order].replace("", np.nan).replace(" ", np.nan)

        return df

    @property
    def shifts(self) -> list:
        """List of shifts scraped from HTML endpoint"""

        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        if self._shifts is None:
            self._scrape_shifts()
            self._munge_shifts()

        return self._shifts

    @property
    def shifts_df(self) -> pd.DataFrame:
        """Pandas Dataframe of shifts scraped from HTML endpoint"""

        if self._shifts is None:
            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._scrape_shifts()
            self._munge_shifts()

        return self._finalize_shifts()


class Scraper:
    """
    Class instance for scraping play-by-play and other data for NHL games.

    Parameters
    ----------
    game_ids : list-like object or int or float or str
        List of 10-digit game identifier, e.g., [2023020001, 2023020002, 2023020003]

    Attributes
    ----------
    play_by_play : pd.DataFrame
        Description


    Examples
    --------
    >>> game_ids = list(range(2023020001, 2023020011))
    >>> scraper = Scraper(game_ids)

    Scrape play-by-play information
    >>> pbp = scraper.play_by_play

    The object stores information from each component of the play-by-play data
    >>> shifts = scraper.shifts
    >>> rosters = scraper.rosters
    >>> changes = scraper.changes

    Access data from API or HTML endpoints, or both
    >>> api_events = scraper.api_events
    >>> api_rosters = scraper.api_rosters
    >>> html_events = scraper.html_events
    >>> html_rosters = scraper.html_rosters

    """

    def __init__(self, game_ids: list | str | float | int):
        game_ids = convert_to_list(game_ids, "game ID")

        self.game_ids = game_ids
        self._scraped_games = []
        self._bad_games = []

        self._requests_session = s_session()

        self._api_events = []
        self._scraped_api_events = []

        self._api_rosters = []
        self._scraped_api_rosters = []

        self._changes = []
        self._scraped_changes = []

        self._html_events = []
        self._scraped_html_events = []

        self._html_rosters = []
        self._scraped_html_rosters = []

        self._rosters = []
        self._scraped_rosters = []

        self._shifts = []
        self._scraped_shifts = []

        self._play_by_play = []
        self._scraped_play_by_play = []

    def _scrape(self, scrape_type: str) -> None:
        scrape_types = [
            "api_events",
            "api_rosters",
            "changes",
            "html_events",
            "html_rosters",
            "play_by_play",
            "shifts",
            "rosters",
        ]

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

        if scrape_type not in scrape_types:
            raise Exception("Scrape type is not supported")

        with self._requests_session as s:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                SpinnerColumn(),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("•"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
            ) as progress:
                pbar_stub = pbar_stubs[scrape_type]

                pbar_message = f"Downloading {pbar_stub} for {self.game_ids[0]}..."

                game_task = progress.add_task(pbar_message, total=len(self.game_ids))

                for idx, game_id in enumerate(self.game_ids):
                    game = Game(game_id, s)

                    if scrape_type == "api_events":
                        if game_id in self._scraped_api_events:
                            continue

                        if game_id in self._scraped_api_rosters:
                            game._api_rosters = [
                                x for x in self._api_rosters if x["game_id"] == game_id
                            ]

                        if game_id not in self._scraped_api_events:
                            self._api_events.extend(game.api_events)
                            self._scraped_api_events.append(game_id)

                        if game_id not in self._scraped_api_rosters:
                            self._api_rosters.extend(game.api_rosters)
                            self._scraped_api_rosters.append(game_id)

                    if scrape_type == "api_rosters":
                        if game_id in self._scraped_api_rosters:
                            continue

                        if game_id not in self._scraped_api_rosters:
                            self._api_rosters.extend(game.api_rosters)
                            self._scraped_api_rosters.append(game_id)

                    if scrape_type == "changes":
                        if game_id in self._scraped_changes:
                            continue

                        if game_id in self._scraped_html_rosters:
                            game._html_rosters = [
                                x for x in self._html_rosters if x["game_id"] == game_id
                            ]

                        if game_id in self._scraped_shifts:
                            game._shifts = [
                                x for x in self._shifts if x["game_id"] == game_id
                            ]

                        if game_id not in self._scraped_changes:
                            self._changes.extend(game.changes)
                            self._scraped_changes.append(game_id)

                        if game_id not in self._scraped_html_rosters:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                        if game_id not in self._scraped_shifts:
                            self._shifts.extend(game.shifts)
                            self._scraped_shifts.append(game_id)

                    if scrape_type == "html_events":
                        if game_id in self._scraped_html_events:
                            continue

                        if game_id in self._scraped_html_rosters:
                            game._html_rosters = [
                                x for x in self._html_rosters if x["game_id"] == game_id
                            ]

                        if game_id not in self._scraped_html_events:
                            self._html_events.extend(game.html_events)
                            self._scraped_html_events.append(game_id)

                        if game_id not in self._scraped_html_rosters:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                    if scrape_type == "html_rosters":
                        if game_id in self._scraped_html_rosters:
                            continue

                        if game_id not in self._scraped_html_rosters:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                    if scrape_type == "play_by_play":
                        if game_id in self._scraped_play_by_play:
                            continue

                        if game_id in self._scraped_rosters:
                            game._rosters = [
                                x for x in self._rosters if x["game_id"] == game_id
                            ]

                        else:
                            if game_id in self._scraped_html_rosters:
                                game._html_rosters = [
                                    x
                                    for x in self._html_rosters
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                            if game_id in self._scraped_api_rosters:
                                game._api_rosters = [
                                    x
                                    for x in self._api_rosters
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._api_rosters.extend(game.api_rosters)
                                self._scraped_api_rosters.append(game_id)

                            self._rosters.extend(game.rosters)
                            self._scraped_rosters.append(game_id)

                        if game_id in self._scraped_changes:
                            game._changes = [
                                x for x in self._changes if x["game_id"] == game_id
                            ]

                        else:
                            if game_id in self._scraped_shifts:
                                game._shifts = [
                                    x for x in self._shifts if x["game_id"] == game_id
                                ]

                            else:
                                self._shifts.extend(game.shifts)
                                self._scraped_shifts.append(game_id)

                            self._changes.extend(game.changes)
                            self._scraped_changes.append(game_id)

                        if game_id in self._scraped_html_events:
                            game._html_events = [
                                x for x in self._html_events if x["game_id"] == game_id
                            ]

                        else:
                            self._html_events.extend(game.html_events)
                            self._scraped_html_events.append(game_id)

                        if game_id in self._scraped_api_events:
                            game._api_events = [
                                x for x in self._api_events if x["game_id"] == game_id
                            ]

                        else:
                            self._api_events.extend(game.api_events)
                            self._scraped_api_events.append(game_id)

                        if game_id not in self._scraped_play_by_play:
                            self._play_by_play.extend(game.play_by_play)
                            self._scraped_play_by_play.append(game_id)

                    if scrape_type == "rosters":
                        if game_id in self._scraped_rosters:
                            continue

                        if game_id in self._scraped_html_rosters:
                            game._html_rosters = [
                                x for x in self._html_rosters if x["game_id"] == game_id
                            ]

                        if game_id in self._scraped_api_rosters:
                            game._api_rosters = [
                                x for x in self._api_rosters if x["game_id"] == game_id
                            ]

                        if game_id not in self._scraped_rosters:
                            self._rosters.extend(game.rosters)
                            self._scraped_rosters.append(game_id)

                        if game_id not in self._scraped_html_rosters:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                        if game_id not in self._scraped_api_rosters:
                            self._api_rosters.extend(game.api_rosters)
                            self._scraped_api_rosters.append(game_id)

                    if scrape_type == "shifts":
                        if game_id in self._scraped_shifts:
                            continue

                        if game_id in self._scraped_html_rosters:
                            game._html_rosters = [
                                x for x in self._html_rosters if x["game_id"] == game_id
                            ]

                        if game_id not in self._scraped_shifts:
                            self._shifts.extend(game.shifts)
                            self._scraped_shifts.append(game_id)

                        if game_id not in self._scraped_html_rosters:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                    if game_id != self.game_ids[-1]:
                        pbar_message = (
                            f"Downloading {pbar_stub} for {self.game_ids[idx + 1]}..."
                        )

                    else:
                        pbar_message = f"Finished downloading {pbar_stub}"

                    progress.update(
                        game_task, description=pbar_message, advance=1, refresh=True
                    )

    def add_games(self, game_ids: list[int | str | float]) -> None:
        game_ids = [int(x) for x in game_ids if x not in self.game_ids]

        self.game_ids.extend(game_ids)

    def _finalize_api_events(self) -> pd.DataFrame:
        df = pd.DataFrame(self._api_events)

        cols = [
            "season",
            "session",
            "game_id",
            "event_team",
            "event_idx",
            "period",
            "period_seconds",
            "game_seconds",
            "event",
            "event_code",
            "strength",
            "coords_x",
            "coords_y",
            "zone",
            "player_1",
            "player_1_eh_id",
            "player_1_api_id",
            "player_1_position",
            "player_1_team_jersey",
            "player_2",
            "player_2_eh_id",
            "player_2_api_id",
            "player_2_position",
            "player_2_team_jersey",
            "player_3",
            "player_3_eh_id",
            "player_3_api_id",
            "player_3_position",
            "player_3_team_jersey",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "opp_goalie_team_jersey",
            "shot_type",
            "miss_reason",
            "penalty_reason",
            "penalty_duration",
            "penalty_type",
            "stoppage_reason",
            "stoppage_reason_secondary",
            "home_team_defending_side",
            "version",
        ]

        cols = [x for x in cols if x in df.columns]

        df = df[cols]

        return df

    @property
    def api_events(self) -> pd.DataFrame:
        if not self._api_events:
            self._scrape("api_events")

        return self._finalize_api_events()

    def _finalize_api_rosters(self) -> pd.DataFrame:
        df = pd.DataFrame(self._api_rosters)

        columns = [
            "season",
            "session",
            "game_id",
            "team",
            "team_venue",
            "player_name",
            "api_id",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "first_name",
            "last_name",
            "headshot_url",
        ]

        columns = [x for x in columns if x in df.columns]

        df = df[columns]

        return df

    @property
    def api_rosters(self) -> pd.DataFrame:
        if not self._api_rosters:
            self._scrape("api_rosters")

        return self._finalize_api_rosters()

    def _finalize_changes(self) -> pd.DataFrame:
        """Function to convert dictionary to dataframe for user"""

        list_fields = [
            "change_on_jersey",
            "change_on",
            "change_on_id",
            "change_on_positions",
            "change_off_jersey",
            "change_off",
            "change_off_id",
            "change_off_positions",
            "change_on_forwards_jersey",
            "change_on_forwards",
            "change_on_forwards_id",
            "change_off_forwards_jersey",
            "change_off_forwards",
            "change_off_forwards_id",
            "change_on_defense_jersey",
            "change_on_defense",
            "change_on_defense_id",
            "change_off_defense_jersey",
            "change_off_defense",
            "change_off_defense_id",
            "change_on_goalie_jersey",
            "change_on_goalie",
            "change_on_goalie_id",
            "change_off_goalie_jersey",
            "change_off_goalie",
            "change_off_goalie_id",
        ]

        changes = [x.copy() for x in self._changes]

        for change in changes:
            for list_field in list_fields:
                change[list_field] = ", ".join(change.get(list_field, ""))

        df = pd.DataFrame(changes)

        column_order = [
            "season",
            "session",
            "game_id",
            "event_team",
            "event_team_name",
            "team_venue",
            "event",
            "event_type",
            "description",
            "period",
            "period_seconds",
            "game_seconds",
            "change_on_count",
            "change_off_count",
            "change_on_jersey",
            "change_on",
            "change_on_id",
            "change_on_positions",
            "change_off_jersey",
            "change_off",
            "change_off_id",
            "change_off_positions",
            "change_on_forwards_count",
            "change_off_forwards_count",
            "change_on_forwards_jersey",
            "change_on_forwards",
            "change_on_forwards_id",
            "change_off_forwards_jersey",
            "change_off_forwards",
            "change_off_forwards_id",
            "change_on_defense_count",
            "change_off_defense_count",
            "change_on_defense_jersey",
            "change_on_defense",
            "change_on_defense_id",
            "change_off_defense_jersey",
            "change_off_defense",
            "change_off_defense_id",
            "change_on_goalie_count",
            "change_off_goalie_count",
            "change_on_goalie_jersey",
            "change_on_goalie",
            "change_on_goalie_id",
            "change_off_goalie_jersey",
            "change_off_goalie",
            "change_off_goalie_id",
            "is_home",
        ]

        column_order = [x for x in column_order if x in df.columns]

        df = df[column_order].replace("", np.nan).replace(" ", np.nan)

        return df

    @property
    def changes(self) -> pd.DataFrame:
        if not self._changes:
            self._scrape("changes")

        return self._finalize_changes()

    def _finalize_html_events(self) -> pd.DataFrame:
        """Finalize HTML events to return a dataframe"""

        df = pd.DataFrame(self._html_events)

        columns = [
            "season",
            "session",
            "game_id",
            "event_team",
            "event_idx",
            "period",
            "period_seconds",
            "game_seconds",
            "event",
            "description",
            "strength",
            "zone",
            "player_1",
            "player_1_eh_id",
            "player_1_position",
            "player_2",
            "player_2_eh_id",
            "player_2_position",
            "player_3",
            "player_3_eh_id",
            "player_3_position",
            "pbp_distance",
            "shot_type",
            "penalty",
            "penalty_length",
            "version",
        ]

        column_order = [x for x in columns if x in df.columns]

        df = df[column_order]

        df = df.replace("", np.nan).replace(" ", np.nan)

        return df

    @property
    def html_events(self) -> pd.DataFrame:
        if not self._html_events:
            self._scrape("html_events")

        return self._finalize_html_events()

    def _finalize_html_rosters(self) -> pd.DataFrame:
        """Function to finalize the HTML rosters to a dataframe that is returned"""

        df = pd.DataFrame(self._html_rosters)

        column_order = [
            "season",
            "session",
            "game_id",
            "team",
            "team_name",
            "team_venue",
            "player_name",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "starter",
            "status",
        ]

        column_order = [x for x in column_order if x in df.columns]

        df = df[column_order]

        return df

    @property
    def html_rosters(self) -> pd.DataFrame:
        if not self._html_rosters:
            self._scrape("html_rosters")

        return self._finalize_html_rosters()

    def _finalize_play_by_play(self) -> pd.DataFrame:
        """Method that creates and returns a Pandas DataFrame from self._play_by_play"""

        list_fields = [
            "home_on",
            "home_on_eh_id",
            "home_on_api_id",
            "home_on_positions",
            "home_forwards",
            "home_forwards_eh_id",
            "home_forwards_api_id",
            "home_forwards_positions",
            "home_defense",
            "home_defense_eh_id",
            "home_defense_api_id",
            "home_defense_positions",
            "home_goalie",
            "home_goalie_eh_id",
            "home_goalie_api_id",
            "away_on",
            "away_on_eh_id",
            "away_on_api_id",
            "away_on_positions",
            "away_forwards",
            "away_forwards_eh_id",
            "away_forwards_api_id",
            "away_forwards_positions",
            "away_defense",
            "away_defense_eh_id",
            "away_defense_api_id",
            "away_defense_positions",
            "away_goalie",
            "away_goalie_eh_id",
            "away_goalie_api_id",
            "teammates",
            "teammates_eh_id",
            "teammates_api_id",
            "teammates_positions",
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_team_on",
            "opp_team_on_eh_id",
            "opp_team_on_api_id",
            "opp_team_on_positions",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "change_on",
            "change_on_eh_id",
            "change_on_positions",
            "change_off",
            "change_off_eh_id",
            "change_off_positions",
            "change_on_forwards",
            "change_on_forwards_eh_id",
            "change_off_forwards",
            "change_off_forwards_eh_id",
            "change_on_defense",
            "change_on_defense_eh_id",
            "change_off_defense",
            "change_off_defense_eh_id",
            "change_on_goalie",
            "change_on_goalie_eh_id",
            "change_off_goalie",
            "change_off_goalie_eh_id",
        ]

        events = [x.copy() for x in self._play_by_play]

        for event in events:
            for list_field in [x for x in list_fields if x in event.keys()]:
                event[list_field] = ", ".join(event[list_field])

        df = pd.DataFrame(events)

        goalie_cols = [
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "home_goalie",
            "home_goalie_eh_id",
            "home_goalie_api_id",
            "away_goalie",
            "away_goalie_eh_id",
            "away_goalie_api_id",
        ]

        df[goalie_cols] = df[goalie_cols].fillna("EMPTY NET")

        df = df.replace("", np.nan).replace(" ", np.nan)

        columns = [
            "season",
            "session",
            "game_id",
            "game_date",
            "event_idx",
            "period",
            "period_seconds",
            "game_seconds",
            "strength_state",
            "score_state",
            "score_diff",
            "event_team",
            "opp_team",
            "event",
            "description",
            "zone",
            "coords_x",
            "coords_y",
            "danger",
            "high_danger",
            "player_1",
            "player_1_eh_id",
            "player_1_eh_id_api",
            "player_1_api_id",
            "player_1_position",
            "player_1_type",
            "player_2",
            "player_2_eh_id",
            "player_2_eh_id_api",
            "player_2_api_id",
            "player_2_position",
            "player_2_type",
            "player_3",
            "player_3_eh_id",
            "player_3_eh_id_api",
            "player_3_api_id",
            "player_3_position",
            "player_3_type",
            "shot_type",
            "event_length",
            "event_distance",
            "event_angle",
            "pbp_distance",
            "event_detail",
            "penalty",
            "penalty_length",
            "penalty_severity",
            "home_score",
            "home_score_diff",
            "away_score",
            "away_score_diff",
            "is_home",
            "is_away",
            "home_team",
            "away_team",
            "home_skaters",
            "away_skaters",
            "event_team_skaters",
            "teammates",
            "teammates_eh_id",
            "teammates_api_id",
            "teammates_positions",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "opp_strength_state",
            "opp_score_state",
            "opp_score_diff",
            "opp_team_skaters",
            "opp_team_on",
            "opp_team_on_eh_id",
            "opp_team_on_api_id",
            "opp_team_on_positions",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "home_on",
            "home_on_eh_id",
            "home_on_api_id",
            "home_on_positions",
            "home_goalie",
            "home_goalie_eh_id",
            "home_goalie_api_id",
            "home_forwards",
            "home_forwards_eh_id",
            "home_forwards_api_id",
            "home_defense",
            "home_defense_eh_id",
            "home_defense_api_id",
            "away_on",
            "away_on_eh_id",
            "away_on_api_id",
            "away_on_positions",
            "away_goalie",
            "away_goalie_eh_id",
            "away_goalie_api_id",
            "away_forwards",
            "away_forwards_eh_id",
            "away_forwards_api_id",
            "away_defense",
            "away_defense_eh_id",
            "away_defense_api_id",
            "zone_start",
            "change_on_count",
            "change_off_count",
            "change_on",
            "change_on_id",
            "change_on_positions",
            "change_off",
            "change_off_id",
            "change_off_positions",
            "change_on_forwards_count",
            "change_off_forwards_count",
            "change_on_forwards",
            "change_on_forwards_id",
            "change_off_forwards",
            "change_off_forwards_id",
            "change_on_defense_count",
            "change_off_defense_count",
            "change_on_defense",
            "change_on_defense_id",
            "change_off_defense",
            "change_off_defense_id",
            "change_on_goalie_count",
            "change_off_goalie_count",
            "change_on_goalie",
            "change_on_goalie_id",
            "change_off_goalie",
            "change_off_goalie_id",
            "version",
            "block",
            "change",
            "chl",
            "corsi",
            "fac",
            "fenwick",
            "give",
            "goal",
            "hit",
            "miss",
            "penl",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
            "shot",
            "stop",
            "take",
            "dzf",
            "nzf",
            "ozf",
            "dzc",
            "nzc",
            "ozc",
            "otf",
        ]

        columns = [x for x in columns if x in df.columns]

        df = df[columns]

        return df

    @property
    def play_by_play(self) -> pd.DataFrame:
        if not self._play_by_play:
            self._scrape("play_by_play")

        return self._finalize_play_by_play()

    def _finalize_rosters(self) -> pd.DataFrame:
        df = pd.DataFrame(self._rosters)

        columns = [
            "season",
            "session",
            "game_id",
            "team",
            "team_venue",
            "player_name",
            "api_id",
            "eh_id",
            "team_jersey",
            "jersey",
            "position",
            "starter",
            "status",
            "headshot_url",
        ]

        columns = [x for x in columns if x in df.columns]

        df = df[columns]

        return df

    @property
    def rosters(self) -> pd.DataFrame:
        if not self._rosters:
            self._scrape("rosters")

        return self._finalize_rosters()

    def _finalize_shifts(self) -> pd.DataFrame:
        """Function to prep the shifts as a dataframe for the user"""

        df = pd.DataFrame(self._shifts)

        column_order = [
            "season",
            "session",
            "game_id",
            "team",
            "team_name",
            "team_venue",
            "player_name",
            "eh_id",
            "team_jersey",
            "position",
            "jersey",
            "shift_count",
            "period",
            "start_time",
            "end_time",
            "duration",
            "start_time_seconds",
            "end_time_seconds",
            "duration_seconds",
            "shift_start",
            "shift_end",
            "goalie",
            "is_home",
        ]

        column_order = [x for x in column_order if x in df.columns]

        df = df[column_order].replace("", np.nan).replace(" ", np.nan)

        return df

    @property
    def shifts(self) -> pd.DataFrame:
        if not self._shifts:
            self._scrape("shifts")

        return self._finalize_shifts()


class Season:
    def __init__(self, year: str | int | float):
        if len(str(year)) == 8:
            self.season = int(year)

        elif len(str(year)) == 4:
            self.season = int(f"{year}{int(year) + 1}")

        first_year = int(str(self.season)[0:4])

        teams_1917 = ["MTL", "MWN", "SEN", "TAN"]

        teams_1918 = ["MTL", "SEN", "TAN"]

        teams_1919 = ["MTL", "QBD", "SEN", "TSP"]

        teams_1920 = ["HAM", "MTL", "SEN", "TSP"]

        teams_1924 = ["BOS", "HAM", "MMR", "MTL", "SEN", "TSP"]

        teams_1925 = ["BOS", "MMR", "MTL", "NYA", "PIR", "SEN", "TSP"]

        teams_1926 = [
            "BOS",
            "CHI",
            "DCG",
            "MMR",
            "MTL",
            "NYA",
            "NYR",
            "PIR",
            "SEN",
            "TSP",
        ]

        teams_1927 = [
            "BOS",
            "CHI",
            "DCG",
            "MMR",
            "MTL",
            "NYA",
            "NYR",
            "PIR",
            "SEN",
            "TOR",
        ]

        teams_1930 = [
            "BOS",
            "CHI",
            "DFL",
            "MMR",
            "MTL",
            "NYA",
            "NYR",
            "QUA",
            "SEN",
            "TOR",
        ]

        teams_1931 = ["BOS", "CHI", "DFL", "MMR", "MTL", "NYA", "NYR", "TOR"]

        teams_1932 = ["BOS", "CHI", "DET", "MMR", "MTL", "NYA", "NYR", "SEN", "TOR"]

        teams_1934 = ["BOS", "CHI", "DET", "MMR", "MTL", "NYA", "NYR", "SLE", "TOR"]

        teams_1935 = ["BOS", "CHI", "DET", "MMR", "MTL", "NYA", "NYR", "TOR"]

        teams_1938 = ["BOS", "CHI", "DET", "MTL", "NYA", "NYR", "TOR"]

        teams_1941 = ["BOS", "BRK", "CHI", "DET", "MTL", "NYR", "TOR"]

        teams_1942 = ["BOS", "CHI", "DET", "MTL", "NYR", "TOR"]

        teams_1967 = [
            "BOS",
            "CHI",
            "DET",
            "LAK",
            "MNS",
            "MTL",
            "NYR",
            "OAK",
            "PHI",
            "PIT",
            "STL",
            "TOR",
        ]

        teams_1970 = [
            "BOS",
            "BUF",
            "CGS",
            "CHI",
            "DET",
            "LAK",
            "MNS",
            "MTL",
            "NYR",
            "PHI",
            "PIT",
            "STL",
            "TOR",
            "VAN",
        ]

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
        }

        self.teams = self._teams_dict.get(first_year)

        if self._teams_dict.get(first_year) is None:
            raise Exception(f"{first_year} IS NOT SUPPORTED")

        self._scraped_schedule_teams = []

        self._scraped_schedule = []

        self._requests_session = s_session()

        self._season_str = str(self.season)[:4] + "-" + str(self.season)[6:8]

    def _scrape_schedule(self, team_schedule: str = "all") -> None:
        schedule_list = []

        if team_schedule not in self._scraped_schedule_teams:
            with self._requests_session as s:
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    SpinnerColumn(),
                    BarColumn(),
                    TaskProgressColumn(),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    TextColumn("•"),
                    TimeRemainingColumn(),
                ) as progress:
                    if team_schedule == "all":
                        teams = self.teams

                        pbar_stub = f"{self._season_str} schedule information"

                        pbar_message = f"Downloading {pbar_stub} for all teams..."

                        sched_task = progress.add_task(pbar_message, total=len(teams))

                        for team in teams:
                            if team in self._scraped_schedule_teams:
                                if team != teams[-1]:
                                    pbar_message = (
                                        f"Downloading {pbar_stub} for {team}..."
                                    )
                                else:
                                    pbar_message = f"Finished downloading {pbar_stub}"
                                progress.update(
                                    sched_task,
                                    description=pbar_message,
                                    advance=1,
                                    refresh=True,
                                )

                                continue

                            url = f"https://api-web.nhle.com/v1/club-schedule-season/{team}/{self.season}"

                            response = s.get(url).json()

                            if response["games"]:
                                games = [
                                    x
                                    for x in response["games"]
                                    if x["id"] not in self._scraped_schedule
                                ]
                                games = self._munge_schedule(games)
                                schedule_list.extend(games)
                                self._scraped_schedule_teams.append(team)
                                self._scraped_schedule.extend(
                                    x["game_id"] for x in games
                                )

                            if team != teams[-1]:
                                pbar_message = f"Downloading {pbar_stub} for {team}..."
                            else:
                                pbar_message = f"Finished downloading {pbar_stub}"
                            progress.update(
                                sched_task,
                                description=pbar_message,
                                advance=1,
                                refresh=True,
                            )
                    else:
                        if team_schedule not in self._scraped_schedule_teams:
                            pbar_stub = f"{self._season_str} schedule information for {team_schedule}"
                            pbar_message = f"Downloading {pbar_stub}..."
                            sched_task = progress.add_task(pbar_message, total=1)

                            url = f"https://api-web.nhle.com/v1/club-schedule-season/{team_schedule}/{self.season}"
                            response = s.get(url).json()

                            if response["games"]:
                                games = [
                                    x
                                    for x in response["games"]
                                    if x["id"] not in self._scraped_schedule
                                ]
                                games = self._munge_schedule(games)
                                schedule_list.extend(games)
                                self._scraped_schedule.extend(
                                    x["game_id"] for x in games
                                )
                                self._scraped_schedule_teams.append(team_schedule)

                            pbar_message = f"Finished downloading {pbar_stub}"
                            progress.update(
                                sched_task,
                                description=pbar_message,
                                advance=1,
                                refresh=True,
                            )

        schedule_list = sorted(
            schedule_list, key=lambda x: (x["game_date_dt"], x["game_id"])
        )

        self._schedule = schedule_list

    @staticmethod
    def _munge_schedule(games: list[dict]) -> list[dict]:
        returned_games = []

        for game in games:
            local_time = pytz.timezone(game["venueTimezone"])

            if "Z" in game["startTimeUTC"]:
                game["startTimeUTC"] = game["startTimeUTC"][:-1] + "+00:00"

            start_time_utc_dt: dt = dt.fromisoformat(game["startTimeUTC"])
            game_date_dt: dt = start_time_utc_dt.astimezone(local_time)

            start_time = game_date_dt.strftime("%H:%M")
            game_date = game_date_dt.strftime("%Y-%m-%d")

            game_info = {}

            new_values = {
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
                "game_date_dt": game_date_dt,
                "tv_broadcasts": game["tvBroadcasts"],
                "home_logo": game["homeTeam"].get("logo"),
                "home_logo_dark": game["homeTeam"].get("darkLogo"),
                "away_logo": game["awayTeam"].get("logo"),
                "away_logo_dark": game["awayTeam"].get("darkLogo"),
            }

            game_info.update(new_values)

            returned_games.append(game_info)

        return returned_games

    @staticmethod
    def _finalize_schedule(games: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(games)

        return df

    def schedule(self, team_schedule: str = "all") -> pd.DataFrame:
        if team_schedule not in self._scraped_schedule_teams:
            self._scrape_schedule(team_schedule=team_schedule)

        if team_schedule != "all":
            return_list = [
                x
                for x in self._schedule
                if x["home_team"] == team_schedule or x["away_team"] == team_schedule
            ]

            return_list = sorted(
                return_list, key=lambda x: (x["game_date_dt"], x["game_id"])
            )

            return self._finalize_schedule(return_list)

        else:
            return self._finalize_schedule(self._schedule)
