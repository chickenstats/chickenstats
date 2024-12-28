import requests

from bs4 import BeautifulSoup

from datetime import datetime as dt
from datetime import timedelta, timezone
import pytz

import pandas as pd
import numpy as np
from pydantic_core._pydantic_core import ValidationError
from requests.exceptions import RetryError

from unidecode import unidecode
import re

from typing import Literal

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
    rosters_fixes,
)

from chickenstats.chicken_nhl.helpers import (
    hs_strip_html,
    convert_to_list,
    load_model,
    prep_p60,
    prep_oi_percent,
)

from chickenstats.chicken_nhl.validation import (
    APIEvent,
    APIRosterPlayer,
    ChangeEvent,
    HTMLEvent,
    HTMLRosterPlayer,
    RosterPlayer,
    PlayerShift,
    PBPEvent,
    PBPEventExt,
    XGFields,
    IndStatSchema,
    OIStatSchema,
    StatSchema,
    ScheduleGame,
    StandingsTeam,
    LineSchema,
    TeamStatSchema,
)

from chickenstats.utilities.utilities import (
    ChickenSession,
    ChickenProgress,
    ChickenProgressIndeterminate,
)

model_version = "0.1.1"

es_model = load_model("even-strength", model_version)
pp_model = load_model("powerplay", model_version)
sh_model = load_model("shorthanded", model_version)
ea_model = load_model("empty-against", model_version)
ef_model = load_model("empty-for", model_version)


class Game:
    """Class instance for scraping play-by-play and other data for individual games. Utilized within Scraper.

    Parameters:
        game_id (int or float or str):
            10-digit game identifier, e.g., 2023020001
        requests_session (requests.Session, optional):
            If scraping multiple games, can provide single Session object to reduce stress on the API / HTML endpoints

    Attributes:
        game_id (int):
            10-digit game identifier, e.g., 2019020684
        game_state (str):
            Whether game is scheduled, started, finished, or official, e.g., OFF
        game_schedule_state (str):
            Whether the game has been scheduled, e.g., OK
        current_period (int):
            Current period, or if game has finished, then latest period, e.g., 3
        current_period_type (str):
            Whether period is regular or overtime, e.g., REG
        time_remaining (str):
            Amount of time remaining in the game, e.g., '00:00'
        seconds_remaining (int):
            Amounting of time remaining in the game in seconds, e.g., 0
        running (bool):
            Whether the game is currently running, e.g., False
        in_intermission (bool):
            Whether the game is currently in intermission, e.g., False
        season (int):
            Season in which the game was played, e.g., 20192020
        session (str):
            Whether the game is regular season, playoffs, or pre-season, e.g., R
        html_id (str):
            Game ID used for scraping HTML endpoints, e.g., 020684
        game_date (str):
            Date game was played, e.g., 2020-01-09
        start_time_et (str):
            Start time in Eastern timezone, regardless of venue, e.g., 20:30
        venue (str):
            Venue name, e.g., UNITED CENTER
        tv_broadcasts (dict):
            TV broadcasts information, e.g., {141: {'market': 'A', 'countryCode': 'US', 'network': 'FS-TN'}, ...}
        home_team (dict):
            Home team information, e.g., {'id': 16, 'name': 'BLACKHAWKS', 'abbrev': 'CHI', ...}
        away_team (dict):
            Away team information, e.g., {'id': 18, 'name': 'PREDATORS', 'abbrev': 'NSH', ...}
        api_endpoint (str):
            URL for accessing play-by-play and API rosters, e.g.,
            'https://api-web.nhle.com/v1/gamecenter/2019020684/play-by-play'
        api_endpoint_other (str):
            URL for accessing other game information, e.g.,
            'https://api-web.nhle.com/v1/gamecenter/2019020684/landing'
        html_rosters_endpoint (str):
            URL for accessing rosters from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/RO020684.HTM'
        home_shifts_endpoint (str):
            URL for accessing home shifts from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/TH020684.HTM'
        away_shifts_endpoint (str):
            URL for accessing away shifts from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/TV020684.HTM'
        html_events_endpoint (str):
            URL for accessing events from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/PL020684.HTM'

    Note:
        You can return any of the properties as a Pandas DataFrame by appending '_df' to the property

    Examples:
        First, instantiate the Game object
        >>> game = Game(2023020001)

        Scrape play-by-play information
        >>> pbp = game.play_by_play  # Returns the data as a list

        Get play-by-play as a Pandas DataFrame
        >>> pbp_df = game.play_by_play_df  # Returns the data as a Pandas DataFrame

        The object stores information from each component of the play-by-play data
        >>> shifts = game.shifts  # Returns a list of shifts
        >>> rosters = (
        ...     game.rosters
        ... )  # Returns a list of players from both API & HTML endpoints
        >>> changes = (
        ...     game.changes
        ... )  # Returns a list of changes constructed from shifts & roster data

        Data can also be returned as a Pandas DataFrame, rather than a list
        >>> shifts_df = game.shifts_df  # Same as above, but as Pandas DataFrame

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

    # TODO: Add play_by_play_ext information to documentation
    # TODO: Check that documentation reflects roster changes

    def __init__(
        self,
        game_id: str | int | float,
        requests_session: requests.Session | None = None,
    ):
        """Instantiates a Game object for a given game ID.

        If nested, you can provide a requests.Session object to optimize speed.
        """
        if str(game_id).isdigit() is False or len(str(game_id)) != 10:
            raise Exception(f"{game_id} IS NOT A VALID GAME ID")

        # Game ID
        self.game_id: int = int(game_id)

        # season
        year = int(str(self.game_id)[0:4])
        self.season: int = int(f"{year}{year + 1}")

        # game session
        game_sessions = {"01": "PR", "02": "R", "03": "P"}
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
            self._requests_session = ChickenSession()
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
            "name": away_team["commonName"]["default"].upper(),
            "abbrev": away_team["abbrev"],
            "logo": away_team["logo"],
        }

        # Home team information
        home_team = response["homeTeam"]

        if home_team["abbrev"] == "PHX":
            home_team["abbrev"] = "ARI"

        self.home_team = {
            "id": home_team["id"],
            "name": home_team["commonName"]["default"].upper(),
            "abbrev": home_team["abbrev"],
            "logo": home_team["logo"],
        }

        # Venue information
        self.venue: str = response["venue"]["default"].upper()

        est = pytz.timezone("US/Eastern")

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

        self._es_model = es_model
        self._pp_model = pp_model
        self._sh_model = sh_model
        self._ef_model = ef_model
        self._ea_model = ea_model

        # Setting up placeholders for data storage
        self._api_events = None
        self._api_rosters = None
        self._changes = None
        self._html_events = None
        self._html_rosters = None
        self._play_by_play = None
        self._play_by_play_ext = None
        self._pred_goal = None
        self._rosters = None
        self._shifts = None

        self._xg_fields = {}

    def _munge_api_events(self) -> None:
        """Method to munge events from API endpoint. Updates self._api_events.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._api_events is None
            >>> game._api_events  # Returns None

            However, you can access the raw events from the API feed
            >>> game.api_response["plays"]

            Once you've cleaned the data using `_munge_api_events`, it's then available from
            game._api_events, or game.api_events, which is the preferred method of accessing the data

            >>> game._munge_api_events()  # Cleans the raw data from game.api_response['plays']
            >>> game._api_events  # Returns clean API events data
            >>> game.api_events  # Also returns clean API events data, preferred method of accessing
        """
        self._api_events = [x for x in self.api_response["plays"]]

        rosters = {x["api_id"]: x for x in self._api_rosters}

        teams_dict = {
            self.home_team["id"]: self.home_team["abbrev"],
            self.away_team["id"]: self.away_team["abbrev"],
        }

        event_list = []

        for event in self._api_events:
            time_split = event["timeInPeriod"].split(":")

            period = int(event["periodDescriptor"]["number"])
            period_type = event["periodDescriptor"]["periodType"]
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
                "period_type": period_type,
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
                        "goalieInNetId", "EMPTY_NET"
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

                    if event_info["player_1_api_id"] is None:  # Not covered by tests
                        event_info["event_team"] = "OTHER"
                        event_info["player_1"] = "REFEREE"
                        event_info["player_1_api_id"] = None
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

                    if event_info["player_2_api_id"] is not None:
                        event_info["player_2_type"] = "PRIMARY ASSIST"

                    event_info["player_3_api_id"] = event["details"].get(
                        "assist2PlayerId"
                    )

                    if event_info["player_3_api_id"] is not None:
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
                        event_info["player_1_api_id"] = None
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
                        event_info["player_1_api_id"] = None
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

                if event_info["event"] == "failed-shot-attempt":  # Not covered by tests
                    event_info["player_1_api_id"] = event["details"]["shootingPlayerId"]
                    event_info["player_1_type"] = "SHOOTER"
                    event_info["opp_goalie_api_id"] = event["details"].get(
                        "goalieInNetId", "EMPTY NET"
                    )

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

                elif event_info[player_col] == "REFEREE":  # Not covered by tests
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

            if event_info["event"] == "BLOCK":
                player_1_team = event_info.get("player_1_team_jersey")

                if player_1_team:
                    player_1_team = player_1_team[:3]
                    event_info["event_team"] = player_1_team

            event_list.append(event_info)

        final_events = []

        for event in event_list:
            other_events = [
                x
                for x in event_list
                # if x != event
                if x["event"] == event["event"]
                and x["game_seconds"] == event["game_seconds"]
                and x.get("player_1") is not None
                and x["period"] == event["period"]
                and x.get("player_1_api_id") == event.get("player_1_api_id")
            ]

            event["version"] = 1

            if len(other_events) > 0:
                for idx, other_event in enumerate(other_events):
                    if event == other_events[0]:
                        continue

                    version = idx + 1
                    event["version"] = version

            final_events.append(APIEvent.model_validate(event).model_dump())

        self._api_events = final_events

    @property
    def api_events(self) -> list:
        """List of events scraped from API endpoint. Each event is a dictionary with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).api_events_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 689
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            event_code (str):
                Code to indicate type of event that occured, e.g., 505
            description (str | None):
                Description of the event, e.g., None
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., D
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_team_jersey (str):
                Combination of team and jersey used for player identification purposes, e.g, NSH35
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_2_api_id (str | None):
                NHL API ID for player_2, e.g., None
            player_2_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            player_3_api_id (str | None):
                NHL API ID for player_3, e.g., None
            player_3_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            strength (int):
                Code to indication strength state, e.g., 1560
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            miss_reason (str | None):
                Reason shot missed, e.g., None
            opp_goalie (str | None):
                Opposing goalie, e.g., None
            opp_goalie_eh_id (str | None):
                Evolving Hockey ID for opposing goalie, e.g., None
            opp_goalie_api_id (str | None):
                NHL API ID for opposing goalie, e.g., None
            opp_goalie_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            event_team_id (int):
                NHL ID for the event team, e.g., 18
            stoppage_reason (str | None):
                Reason the play was stopped, e.g., None
            stoppage_reason_secondary (str | None):
                Secondary reason play was stopped, e.g., None
            penalty_type (str | None):
                Type of penalty taken, e.g., None
            penalty_reason (str | None):
                Reason for the penalty, e.g., None
            penalty_duration (int | None):
                Duration of the penalty, e.g., None
            home_team_defending_side (str):
                Side of the ice the home team is defending, e.g., right
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.api_events

        """
        if self._api_events is None:
            if self._api_rosters is None:
                self._munge_api_rosters()

            self._munge_api_events()

        return self._api_events

    @property
    def api_events_df(self) -> pd.DataFrame:
        """Pandas Dataframe of events scraped from API endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 689
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            event_code (str):
                Code to indicate type of event that occured, e.g., 505
            description (str | None):
                Description of the event, e.g., None
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., D
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_team_jersey (str):
                Combination of team and jersey used for player identification purposes, e.g, NSH35
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_2_api_id (str | None):
                NHL API ID for player_2, e.g., None
            player_2_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            player_3_api_id (str | None):
                NHL API ID for player_3, e.g., None
            player_3_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            strength (int):
                Code to indication strength state, e.g., 1560
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            miss_reason (str | None):
                Reason shot missed, e.g., None
            opp_goalie (str | None):
                Opposing goalie, e.g., None
            opp_goalie_eh_id (str | None):
                Evolving Hockey ID for opposing goalie, e.g., None
            opp_goalie_api_id (str | None):
                NHL API ID for opposing goalie, e.g., None
            opp_goalie_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            event_team_id (int):
                NHL ID for the event team, e.g., 18
            stoppage_reason (str | None):
                Reason the play was stopped, e.g., None
            stoppage_reason_secondary (str | None):
                Secondary reason play was stopped, e.g., None
            penalty_type (str | None):
                Type of penalty taken, e.g., None
            penalty_reason (str | None):
                Reason for the penalty, e.g., None
            penalty_duration (int | None):
                Duration of the penalty, e.g., None
            home_team_defending_side (str):
                Side of the ice the home team is defending, e.g., right
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.api_events_df
        """
        if self._api_events is None:
            if self._api_rosters is None:
                self._munge_api_rosters()

            self._munge_api_events()

        return pd.DataFrame(self._api_events)

    def _munge_api_rosters(self) -> None:
        """Method to munge list of players from API  endpoint. Updates self._api_rosters.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._api_rosters is None
            >>> game._rosters  # Returns None

            However, you can access the raw roster data from the API feed
            >>> game.api_response["rosterSpots"]

            Once you've cleaned the data using `_munge_api_rosters`, it's then available from
            game._api_rosters, or game.api_rosters, which is the preferred method of accesing the data

            >>> game._munge_api_rosters()  # Cleans the raw data from game.api_response['plays']
            >>> game._api_rosters  # Returns clean API rosters data
            >>> game.api_rosters  # Also returns clean API rosters data, preferred method of accessing
        """
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
                "headshot_url": player.get("headshot", ""),
            }

            players.append(APIRosterPlayer.model_validate(player_info).model_dump())

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
                "headshot_url": "",
            }

            players.append(APIRosterPlayer.model_validate(new_player).model_dump())

        players = sorted(players, key=lambda k: (k["team_venue"], k["player_name"]))

        self._api_rosters = players

    @property
    def api_rosters(self) -> list:
        """List of players scraped from API endpoint. Returns a dictionary of players with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).api_rosters_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            first_name (str):
                Player's first name, e.g., FILIP
            last_name (str):
                Player's last name, e.g., FORSBERG
            headshot_url (str):
                URL to retreive player's headshot

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.api_rosters
        """
        if self._api_rosters is None:
            self._munge_api_rosters()

        return self._api_rosters

    @property
    def api_rosters_df(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from API endpoint.

        Returns:
            Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            first_name (str):
                Player's first name, e.g., FILIP
            last_name (str):
                Player's last name, e.g., FORSBERG
            headshot_url (str):
                URL to retreive player's headshot

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.api_rosters_df
        """
        if self._api_rosters is None:
            self._munge_api_rosters()

        return pd.DataFrame(self._api_rosters)

    def _munge_changes(self) -> None:
        """Method to munge list of changes from HTML shifts & rosters endpoints. Updates self._changes.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._changes is None
            >>> game._changes  # Returns None

            Once you scrape the shifts data, you can access it in raw form, prior to any processing
            >>> game._scrape_shifts()  # Scrapes raw data and adds it to game._shifts
            >>> game.shifts  # Returns cleaned shifts data
            >>> game.shifts_df  # Same, but a Pandas DataFrame

            You then have to manually clean the data to convert it to changes
            >>> game._munge_shifts()  # Necessary before munging the changes
            >>> game._munge_changes()
            >>> game.changes  # Returns cleaned changes data
            >>> game.changes_df  # Same but a Pandas DataFrame
        """
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
                        "change_on_eh_id": [x["eh_id"] for x in players_on],
                        "change_on_api_id": [str(x["api_id"]) for x in players_on],
                        "change_on_positions": [x["position"] for x in players_on],
                        "change_off_jersey": "",
                        "change_off": "",
                        "change_off_eh_id": "",
                        "change_off_api_id": "",
                        "change_off_positions": "",
                        "change_on_forwards_count": len(forwards_on),
                        "change_off_forwards_count": 0,
                        "change_on_forwards_jersey": [
                            x["team_jersey"] for x in forwards_on
                        ],
                        "change_on_forwards": [x["player_name"] for x in forwards_on],
                        "change_on_forwards_eh_id": [x["eh_id"] for x in forwards_on],
                        "change_on_forwards_api_id": [
                            str(x["api_id"]) for x in forwards_on
                        ],
                        "change_off_forwards_jersey": "",
                        "change_off_forwards": "",
                        "change_off_forwards_eh_id": "",
                        "change_off_forwards_api_id": "",
                        "change_on_defense_count": len(defense_on),
                        "change_off_defense_count": 0,
                        "change_on_defense_jersey": [
                            x["team_jersey"] for x in defense_on
                        ],
                        "change_on_defense": [x["player_name"] for x in defense_on],
                        "change_on_defense_eh_id": [x["eh_id"] for x in defense_on],
                        "change_on_defense_api_id": [
                            str(x["api_id"]) for x in defense_on
                        ],
                        "change_off_defense_jersey": "",
                        "change_off_defense": "",
                        "change_off_defense_eh_id": "",
                        "change_off_defense_api_id": "",
                        "change_on_goalie_count": len(goalies_on),
                        "change_off_goalie_count": 0,
                        "change_on_goalie_jersey": [
                            x["team_jersey"] for x in goalies_on
                        ],
                        "change_on_goalie": [x["player_name"] for x in goalies_on],
                        "change_on_goalie_eh_id": [x["eh_id"] for x in goalies_on],
                        "change_on_goalie_api_id": [
                            str(x["api_id"]) for x in goalies_on
                        ],
                        "change_off_goalie_jersey": "",
                        "change_off_goalie": "",
                        "change_off_goalie_eh_id": "",
                        "change_off_goalie_api_id": "",
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
                        "change_off_eh_id": [x["eh_id"] for x in players_off],
                        "change_off_api_id": [str(x["api_id"]) for x in players_off],
                        "change_off_positions": [x["position"] for x in players_off],
                        "change_off_forwards_count": len(forwards_off),
                        "change_off_forwards_jersey": [
                            x["team_jersey"] for x in forwards_off
                        ],
                        "change_off_forwards": [x["player_name"] for x in forwards_off],
                        "change_off_forwards_eh_id": [x["eh_id"] for x in forwards_off],
                        "change_off_forwards_api_id": [
                            str(x["api_id"]) for x in forwards_off
                        ],
                        "change_off_defense_count": len(defense_off),
                        "change_off_defense_jersey": [
                            x["team_jersey"] for x in defense_off
                        ],
                        "change_off_defense": [x["player_name"] for x in defense_off],
                        "change_off_defense_eh_id": [x["eh_id"] for x in defense_off],
                        "change_off_defense_api_id": [
                            str(x["api_id"]) for x in defense_off
                        ],
                        "change_off_goalie_count": len(goalies_off),
                        "change_off_goalie_jersey": [
                            x["team_jersey"] for x in goalies_off
                        ],
                        "change_off_goalie": [x["player_name"] for x in goalies_off],
                        "change_off_goalie_eh_id": [x["eh_id"] for x in goalies_off],
                        "change_off_goalie_api_id": [
                            str(x["api_id"]) for x in goalies_off
                        ],
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

        final_changes = []

        for change in game_list:
            players_on = ", ".join(change.get("change_on", []))

            players_off = ", ".join(change.get("change_off", []))

            on_num = len(change.get("change_on", []))

            off_num = len(change.get("change_off", []))

            if on_num > 0 and off_num > 0:
                change["description"] = (
                    f"PLAYERS ON: {players_on} / PLAYERS OFF: {players_off}"
                )

            if on_num > 0 and off_num == 0:
                change["description"] = f"PLAYERS ON: {players_on}"

            if off_num > 0 and on_num == 0:
                change["description"] = f"PLAYERS OFF: {players_off}"

            if change["period"] == 5 and game_session == "R":  # Not covered by tests
                change["game_seconds"] = 3900 + change["period_seconds"]

            else:
                change["game_seconds"] = (int(change["period"]) - 1) * 1200 + change[
                    "period_seconds"
                ]

            if change["is_home"] == 1:
                change["event_type"] = "HOME CHANGE"

            else:
                change["event_type"] = "AWAY CHANGE"

            final_changes.append(ChangeEvent.model_validate(change).model_dump())

        self._changes = final_changes

    @property
    def changes(self) -> list:
        """List of changes scraped from API endpoint. Each change is a dictionary with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).changes_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., CHANGE
            event_type (str):
                Type of change that occurred, e.g., AWAY CHANGE
            description (str | None):
                Description of the event, e.g.,
                PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
                / PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            change_on_count (int):
                Number of players on, e.g., 4
            change_off_count (int):
                Number of players off, e.g., 4
            change_on (str):
                Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_jersey (str):
                Combination of jerseys and numbers for the players on, e.g., NSH14, NSH19, NSH64, NSH95
            change_on_eh_id (str):
                Evolving Hockey IDs of the players on, e.g.,
                MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_on_positions (str):
                Positions of the players on, e.g., D, C, C, C
            change_off (str):
                Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_jersey (str):
                Combination of jerseys and numbers for the players off, e.g., NSH7, NSH9, NSH33, NSH92
            change_off_eh_id (str):
                Evolving Hockey IDs of the players off, e.g.,
                YANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_off_positions (str):
                Positions of the players off, e.g., D, L, L, C
            change_on_forwards_count (int):
                Number of forwards on, e.g.,
            change_off_forwards_count (int):
                Number of forwards off, e.g., 3
            change_on_forwards (str):
                Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards on, e.g., NSH19, NSH64, NSH95
            change_on_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards on, e.g.,
                CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_off_forwards (str):
                Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards off, e.g., NSH9, NSH33, NSH92
            change_off_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards off, e.g.,
                FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_on_defense_count (int):
                Number of defense on, e.g., 1
            change_off_defense_count (int):
                Number of defense off, e.g., 1
            change_on_defense (str):
                Names of defense on, e.g., MATTIAS EKHOLM
            change_on_defense_jersey (str):
                Combination of jerseys and numbers for the defense on, e.g., NSH14
            change_on_defense_eh_id (str):
                Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM
            change_off_defense (str):
                Names of defense off, e.g., YANNICK WEBER
            change_off_defense_jersey (str):
                Combination of jerseys and numbers for the defense off, e.g., NSH7
            change_off_defebse_eh_id (str):
                Evolving Hockey IDs of the defebse off, e.g., YANNICK.WEBER
            change_on_goalie_count (int):
                Number of goalies on, e.g., 0
            change_off_goalie_count (int):
                Number of goalies off, e.g., 0
            change_on_goalies (str):
                Names of goalies on, e.g., None
            change_on_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies on, e.g., None
            change_on_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies on, e.g., None
            change_off_goalies (str):
                Names of goalies off, e.g., None
            change_off_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies off, e.g., None
            change_off_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies off, e.g., None
            is_home (int):
                Dummy indicator whether change team is home, e.g., 0
            is_away (int):
                Dummy indicator whether change team is away, e.g., 1
            team_venue (str):
                Whether team is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.changes

        """
        # TODO: Add API ID columns to documentation

        if self._changes is None:
            if self._rosters is None:
                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                if self._api_rosters is None:
                    self._munge_api_rosters()

                self._combine_rosters()

            if self._shifts is None:
                self._scrape_shifts()
                self._munge_shifts()

            self._munge_changes()

        return self._changes

    @property
    def changes_df(self) -> pd.DataFrame:
        """Pandas Dataframe of changes scraped from HTML shifts & roster endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., CHANGE
            event_type (str):
                Type of change that occurred, e.g., AWAY CHANGE
            description (str | None):
                Description of the event, e.g.,
                PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
                / PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            change_on_count (int):
                Number of players on, e.g., 4
            change_off_count (int):
                Number of players off, e.g., 4
            change_on (str):
                Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_jersey (str):
                Combination of jerseys and numbers for the players on, e.g., NSH14, NSH19, NSH64, NSH95
            change_on_eh_id (str):
                Evolving Hockey IDs of the players on, e.g.,
                MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_on_positions (str):
                Positions of the players on, e.g., D, C, C, C
            change_off (str):
                Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_jersey (str):
                Combination of jerseys and numbers for the players off, e.g., NSH7, NSH9, NSH33, NSH92
            change_off_eh_id (str):
                Evolving Hockey IDs of the players off, e.g.,
                YANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_off_positions (str):
                Positions of the players off, e.g., D, L, L, C
            change_on_forwards_count (int):
                Number of forwards on, e.g.,
            change_off_forwards_count (int):
                Number of forwards off, e.g., 3
            change_on_forwards (str):
                Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards on, e.g., NSH19, NSH64, NSH95
            change_on_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards on, e.g.,
                CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_off_forwards (str):
                Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards off, e.g., NSH9, NSH33, NSH92
            change_off_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards off, e.g.,
                FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_on_defense_count (int):
                Number of defense on, e.g., 1
            change_off_defense_count (int):
                Number of defense off, e.g., 1
            change_on_defense (str):
                Names of defense on, e.g., MATTIAS EKHOLM
            change_on_defense_jersey (str):
                Combination of jerseys and numbers for the defense on, e.g., NSH14
            change_on_defense_eh_id (str):
                Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM
            change_off_defense (str):
                Names of defense off, e.g., YANNICK WEBER
            change_off_defense_jersey (str):
                Combination of jerseys and numbers for the defense off, e.g., NSH7
            change_off_defebse_eh_id (str):
                Evolving Hockey IDs of the defebse off, e.g., YANNICK.WEBER
            change_on_goalie_count (int):
                Number of goalies on, e.g., 0
            change_off_goalie_count (int):
                Number of goalies off, e.g., 0
            change_on_goalies (str):
                Names of goalies on, e.g., None
            change_on_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies on, e.g., None
            change_on_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies on, e.g., None
            change_off_goalies (str):
                Names of goalies off, e.g., None
            change_off_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies off, e.g., None
            change_off_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies off, e.g., None
            is_home (int):
                Dummy indicator whether change team is home, e.g., 0
            is_away (int):
                Dummy indicator whether change team is away, e.g., 1
            team_venue (str):
                Whether team is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.changes_df

        """
        # TODO: Add API ID columns to documentation

        if self._changes is None:
            if self._rosters is None:
                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                if self._api_rosters is None:
                    self._munge_api_rosters()

                self._combine_rosters()

            if self._shifts is None:
                self._scrape_shifts()
                self._munge_shifts()

            self._munge_changes()

        return pd.DataFrame(self._changes)

    def _scrape_html_events(self) -> None:
        """Method for scraping events from HTML endpoint. Updates self._html_events.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._html_events is None
            >>> game._html_events  # Returns None

            Once you scrape the data, you can access it in raw form, prior to any processing
            >>> game._scrape_html_events()  # Scrapes raw data and adds it to game._html_events
            >>> game.html_events  # Returns raw events, prior to processing
            >>> game.html_events_df  # Same, but a Pandas DataFrame

            You then have to manually clean the data
            >>> game._munge_html_events()
            >>> game.html_events  # Returns cleaned events data
            >>> game.html_events_df  # Same but a Pandas DataFrame
        """
        url = self.html_events_endpoint

        s = self._requests_session

        try:
            response = s.get(url)
        except RetryError:  # Not covered by tests
            return None

        soup = BeautifulSoup(response.content.decode("ISO-8859-1"), "lxml")

        events = []

        if soup.find("html") is None:  # Not covered by tests
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
        """Method to munge list of events from HTML endpoint. Updates self._html_events.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._html_events is None
            >>> game._html_events  # Returns None

            Once you scrape the data, you can access it in raw form, prior to any processing
            >>> game._scrape_html_events()  # Scrapes raw data and adds it to game._html_events
            >>> game.html_events  # Returns raw events, prior to processing
            >>> game.html_events_df  # Same, but a Pandas DataFrame

            You then have to manually clean the data
            >>> game._munge_html_events()
            >>> game.html_events  # Returns cleaned events data
            >>> game.html_events_df  # Same but a Pandas DataFrame
        """
        game_session = self.session

        if self._html_rosters is None:  # Not covered by tests
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
        shot_re = re.compile(r",\s+([A-Za-z]*|[A-Za-z]*-[A-Za-z]*)\s*,")
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
                "SPC": "PUCK IN CROWD",
                "GOFF": "GAME OFFICIAL",
                "EGT": "EMERGENCY GOALTENDER"
            }

            if event["event"] in list(non_descripts.keys()):
                event["description"] = non_descripts[event["event"]]

                if event["event"] == "SPC":
                    event["event"] = "STOP"

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

            if (
                event["event"] == "PEND" and event["time"] == "-16:0-120:00"
            ):  # Not covered by tests
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

                    if event["event_team"] == "LEA":  # Not covered by tests
                        event["event_team"] = ""

                except AttributeError:
                    continue

            if event["event"] == "FAC":
                try:
                    event["event_team"] = re.search(
                        fo_team_re, event["description"]
                    ).group(1)

                except AttributeError:
                    event["event_team"] = None

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
            ):  # Not covered by tests
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
                    position = None

                elif event_player == "REFEREE":  # Not covered by tests
                    player_name = "REFEREE"
                    eh_id = "REFEREE"
                    position = None

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

                    event["player_1_position"] = None

                    try:
                        served_by = re.search(served_re, event["description"])

                        name = served_by.group(1) + str(served_by.group(2))

                    except AttributeError:  # Not covered by tests
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
                            event["player_1_position"] = None

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

                    except AttributeError:  # Not covered by tests
                        pass

                elif "SERVED BY" in event["description"]:
                    try:
                        served_by = re.search(served_re, event["description"])

                        served_name = served_by.group(1) + str(served_by.group(2))

                        event["player_2"] = actives[served_name]["player_name"]

                        event["player_2_eh_id"] = actives[served_name]["eh_id"]

                        event["player_2_position"] = actives[served_name]["position"]

                    except AttributeError:  # Not covered by tests
                        pass

                elif "DRAWN BY" in event["description"]:
                    try:
                        drawn_by = re.search(drawn_re, event["description"])

                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))

                        event["player_2"] = actives[drawn_name]["player_name"]

                        event["player_2_eh_id"] = actives[drawn_name]["eh_id"]

                        event["player_2_position"] = actives[drawn_name]["position"]

                    except AttributeError:  # Not covered by tests
                        pass

                if "player_1" not in event.keys():  # Not covered by tests
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

                except TypeError:  # Not covered by tests
                    pass

                try:
                    event["penalty"] = (
                        re.search(penalty_re, event["description"]).group(1).upper()
                    )

                except AttributeError:  # Not covered by tests
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
                ):  # Not covered by tests
                    event["penalty"] = "DELAY OF GAME - FACEOFF VIOLATION"

                elif (
                    "DELAY" in event["description"]
                    and "GAME" in event["description"]
                    and "EQUIPMENT" in event["description"]
                ):  # Not covered by tests
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
                ):  # Not covered by tests
                    event["penalty"] = "DELAY OF GAME - SMOTHERING THE PUCK"

                elif (
                    "ILLEGAL" in event["description"]
                    and "CHECK" in event["description"]
                    and "HEAD" in event["description"]
                ):  # Not covered by tests
                    event["penalty"] = "ILLEGAL CHECK TO HEAD"

                elif (
                    "HIGH-STICKING" in event["description"]
                    and "- DOUBLE" in event["description"]
                ):  # Not covered by tests
                    event["penalty"] = "HIGH-STICKING - DOUBLE MINOR"

                elif "GAME MISCONDUCT" in event["description"]:
                    event["penalty"] = "GAME MISCONDUCT"

                elif "MATCH PENALTY" in event["description"]:
                    event["penalty"] = "MATCH PENALTY"

                elif (
                    "NET" in event["description"]
                    and "DISPLACED" in event["description"]
                ):  # Not covered by tests
                    event["penalty"] = "DISPLACED NET"

                elif (
                    "THROW" in event["description"]
                    and "OBJECT" in event["description"]
                    and "AT PUCK" in event["description"]
                ):  # Not covered by tests
                    event["penalty"] = "THROWING OBJECT AT PUCK"

                elif (
                    "INSTIGATOR" in event["description"]
                    and "FACE SHIELD" in event["description"]
                ):  # Not covered by tests
                    event["penalty"] = "INSTIGATOR - FACE SHIELD"

                elif "GOALIE LEAVE CREASE" in event["description"]:
                    event["penalty"] = "LEAVING THE CREASE"

                elif (
                    "REMOVING" in event["description"]
                    and "HELMET" in event["description"]
                ):  # Not covered by tests
                    event["penalty"] = "REMOVING OPPONENT HELMET"

                elif (
                    "BROKEN" in event["description"] and "STICK" in event["description"]
                ):  # Not covered by tests
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
                ):  # Not covered by tests
                    event["penalty"] = "TRIPPING - BREAKAWAY"

                elif (
                    "SLASH" in event["description"]
                    and "BREAKAWAY" in event["description"]
                ):  # Not covered by tests
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
                ):  # Not covered by tests
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
                ):  # Not covered by tests
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

                if "BETWEEN LEGS" in event["description"]:  # Not covered by tests
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

        final_events = []

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
                    # if x != event
                    if x["event"] == event["event"]
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
                        if event == other_events[0]:
                            continue

                        version = idx + 1
                        event["version"] = version

            final_events.append(HTMLEvent.model_validate(event).model_dump())

        self._html_events = final_events

    @property
    def html_events(self) -> list:
        """List of events scraped from HTML endpoint. Each event is a dictionary with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).html_events_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 331
            period (int):
                Period number of the event, e.g., 3
            period_time (str):
                Time elapsed in the period, e.g., 19:38
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            penalty_length (str | None):
                Duration of the penalty, e.g., None
            penalty (str | None):
                Reason for the penalty, e.g., None
            strength (str | None):
                Code to indication strength state, e.g., EV
            away_skaters (str):
                Away skaters on-ice, e.g., 13C, 19C, 64C, 14D, 59D, 35G
            home_skaters (str):
                Home skaters on-ice, e.g., 19C, 77C, 12R, 88R, 2D, 56D
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.html_events

        """
        if self._html_events is None:
            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._scrape_html_events()
            self._munge_html_events()

        return self._html_events

    @property
    def html_events_df(self) -> pd.DataFrame:
        """Pandas Dataframe of events scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 331
            period (int):
                Period number of the event, e.g., 3
            period_time (str):
                Time elapsed in the period, e.g., 19:38
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            penalty_length (str | None):
                Duration of the penalty, e.g., None
            penalty (str | None):
                Reason for the penalty, e.g., None
            strength (str | None):
                Code to indication strength state, e.g., EV
            away_skaters (str):
                Away skaters on-ice, e.g., 13C, 19C, 64C, 14D, 59D, 35G
            home_skaters (str):
                Home skaters on-ice, e.g., 19C, 77C, 12R, 88R, 2D, 56D
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.html_events_df

        """
        if self._html_events is None:
            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._scrape_html_events()
            self._munge_html_events()

        return pd.DataFrame(self._html_events)

    def _scrape_html_rosters(self) -> None:
        """Method for scraping players from HTML endpoint. Updates self._html_rosters.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._html_rosters is None
            >>> game._html_rosters  # Returns None

            Once you scrape the data, you can access it in raw form, prior to any processing
            >>> game._scrape_html_rosters()  # Scrapes raw data and adds it to game._html_rosters
            >>> game.html_rosters  # Returns raw rosters, prior to processing
            >>> game.html_rosters_df  # Same, but a Pandas DataFrame

            You then have to manually clean the data
            >>> game._munge_html_rosters()
            >>> game.html_rosters  # Returns cleaned rosters data
            >>> game.html_rosters_df  # Same but a Pandas DataFrame
        """
        # URL and scraping url

        url = self.html_rosters_endpoint

        s = self._requests_session

        try:
            page = s.get(url)
        except RetryError:  # Not covered by tests
            return None

        # Continue if status code is bad

        if page.status_code == 404:  # Not covered by tests
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

            if (
                "Name" not in og_headers and "Nom/Name" not in og_headers
            ):  # Not covered by tests
                continue

            # Chop off the headers to create my own

            actives = active_array[1:]

            # Iterating through each player, or row in the array

            for player in actives:
                # New headers for the data. Original headers | ['#', 'Pos', 'Name']

                if len(player) == 3:
                    headers = ["jersey", "position", "player_name"]

                # Sometimes headers are missing

                else:  # Not covered by tests
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

                if "position" not in headers:  # Not covered by tests
                    player["position"] = None

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

                        else:  # Not covered by tests
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

                        if "position" not in headers:  # Not covered by tests
                            player["position"] = None

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
        """Method to munge list of players from HTML endpoint. Updates self._html_rosters.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._html_rosters is None
            >>> game._html_rosters  # Returns None

            Once you scrape the data, you can access it in raw form, prior to any processing
            >>> game._scrape_html_rosters()  # Scrapes raw data and adds it to game._html_rosters
            >>> game.html_rosters  # Returns raw rosters, prior to processing
            >>> game.html_rosters_df  # Same, but a Pandas DataFrame

            You then have to manually clean the data
            >>> game._munge_html_rosters()
            >>> game.html_rosters  # Returns cleaned rosters data
            >>> game.html_rosters_df  # Same but a Pandas DataFrame
        """
        season = self.season
        game_session = self.session

        # Iterating through each player to change information

        final_rosters = []

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

            if player["eh_id"] == "COLIN.":  # Not covered by tests
                player["eh_id"] = "COLIN.WHITE2"

            player["team"] = team_codes.get(player["team_name"])

            player["team_jersey"] = f"{player['team']}{player['jersey']}"

            final_rosters.append(HTMLRosterPlayer.model_validate(player).model_dump())

        self._html_rosters = final_rosters

        self._html_rosters = sorted(
            self._html_rosters,
            key=lambda k: (k["team_venue"], k["status"], k["player_name"]),
        )

    @property
    def html_rosters(self) -> list:
        """List of players scraped from HTML endpoint. Returns a dictionary of players with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).html_rosters_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.html_rosters

        """
        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        return self._html_rosters

    @property
    def html_rosters_df(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.html_rosters_df

        """
        if self._html_rosters is None:
            self._scrape_html_rosters()
            self._munge_html_rosters()

        return pd.DataFrame(self._html_rosters)

    def _combine_events(self) -> None:
        """Method to combine API and HTML events. Updates self._play_by_play.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First instantiate the Game object
            >>> game = Game(2023020001)

            Requires all other data sources to be clean

            HTML rosters
            >>> game._scrape_html_rosters()
            >>> game._munge_html_rosters()

            API rosters
            >>> game._munge_api_rosters()

            Combined rosters
            >>> game._combine_rosters()

            HTML events
            >>> game._scrape_html_events()  # Scrapes events from HTML feed
            >>> game._munge_html_events()  # Preps raw events, updates game._html_events

            API events
            >>> game._munge_api_events()  # Preps raw events, updates game._api_events

            Shifts and changes
            >>> game._scrape_html_events()  # Scrapes shifts from HTML feed
            >>> game._munge_shifts()  # Preps raw shifts, updates game._shifts
            >>> game._munge_changes()  # Preps changes

            Combines them all
            >>> game._combine_events()  # Combines raw events, into game._play_by_play

            Data can then be manually cleaned
            >>> game._munge_play_by_play()
            >>> game._prep_xg()
            >>> game._play_by_play  # Returns cleaned data
        """
        html_events = self._html_events
        api_events = self._api_events

        game_list = []

        for event in html_events:
            if event["event"] == "EGPID":  # Not covered by tests
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

            elif (
                event["event"] == "CHL" and event.get("event_team") is None
            ):  # Not covered by tests
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

            elif (
                event["event"] == "BLOCK" and event["player_1"] == "TEAMMATE"
            ):  # Not covered by tests
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

            if (
                event["event"] == "FAC" and len(api_matches) == 0
            ):  # Not covered by tests
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

                if (
                    event["event"] == "BLOCK" and event["player_1"] == "TEAMMATE"
                ):  # Not covered by tests
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

            if event["period"] == 5 and event["session"] == "R":  # Not covered by tests
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
        """Method to munge list of events and changes for play-by-play. Updates self._play_by_play.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Requires clean events from the shifts, API events, and HTML events feeds

            HTML events
            >>> game._scrape_html_events()  # Scrapes events from HTML feed
            >>> game._munge_html_events()  # Preps raw events, updates game._html_events

            API events
            >>> game._munge_api_events()  # Preps raw events, updates game._api_events

            Shifts and changes
            >>> game._scrape_html_events()  # Scrapes shifts from HTML feed
            >>> game._munge_shifts()  # Preps raw shifts, updates game._shifts
            >>> game._munge_changes()  # Preps changes

            Combines them all
            >>> game._combine_events()  # Combines raw events, into game._play_by_play

            Data can then be manually cleaned
            >>> game._munge_play_by_play()
            >>> game._prep_xg()
            >>> game._play_by_play  # Returns cleaned data
        """
        game_session = self.session

        home_score = 0

        away_score = 0

        for idx, event in enumerate(self._play_by_play):
            if event.get("event_team") == event["home_team"]:
                event["opp_team"] = event["away_team"]

            elif event.get("event_team") == event["away_team"]:
                event["opp_team"] = event["home_team"]

            else:
                event["event_team"] = event["home_team"]
                event["opp_team"] = event["away_team"]

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

            if (
                self._play_by_play[(idx - 1)]["event"] == "GOAL"
                and self._play_by_play[(idx - 1)]["event_team"] == event["home_team"]
            ):
                if game_session == "R" and event["period"] != 5:
                    home_score += 1

                elif (
                    game_session == "R" and event["period"] == 5
                ):  # Not covered by tests
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

            elif (
                self._play_by_play[(idx - 1)]["event"] == "GOAL"
                and self._play_by_play[(idx - 1)]["event_team"] == event["away_team"]
            ):
                if game_session == "R" and event["period"] != 5:
                    away_score += 1

                elif (
                    game_session == "R" and event["period"] == 5
                ):  # Not covered by tests
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
                        for x in event["change_on_jersey"].split(", ")
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
                        for x in event["change_off_jersey"].split(", ")
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
                            event["away_forwards_positions"].append(player["position"])

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

        final_events = []
        final_events_ext = []

        for idx, event in enumerate(self._play_by_play):
            if event == self._play_by_play[-1]:
                event_length_idx = idx

            else:
                event_length_idx = idx + 1

            new_values = {
                "event_idx": idx + 1,
                "event_length": self._play_by_play[event_length_idx]["game_seconds"]
                - event["game_seconds"],
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
                is_long_distance = (
                    event["pbp_distance"] is not None
                    and event.get("pbp_distance", 0) > 89
                )
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

                zone_cond = event.get("zone") != "OFF"

                x_is_neg_conds = (
                    is_fenwick & is_long_distance & x_is_neg & bad_shots & zone_cond
                )

                x_is_pos_conds = (
                    is_fenwick & is_long_distance & x_is_pos & bad_shots & zone_cond
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

                    except ZeroDivisionError:  # Not covered by tests
                        event["event_angle"] = np.degrees(abs(np.arctan(np.nan)))

                elif x_is_pos_conds is True:
                    event["event_distance"] = (
                        (event["coords_x"] + 89) ** 2 + event["coords_y"] ** 2
                    ) ** (1 / 2)

                    try:
                        event["event_angle"] = np.degrees(
                            abs(np.arctan(event["coords_y"] / (event["coords_x"] + 89)))
                        )

                    except ZeroDivisionError:  # Not covered by tests
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
            ):  # Not covered by tests
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

            event["home_forwards_count"] = len(event["home_forwards"])
            event["home_defense_count"] = len(event["home_defense"])

            if event["home_skaters"] > 0:
                event["home_forwards_percent"] = (
                    event["home_forwards_count"] / event["home_skaters"]
                )

            else:
                event["home_forwards_percent"] = 0

            event["away_forwards_count"] = len(event["away_forwards"])
            event["away_defense_count"] = len(event["away_defense"])

            if event["away_skaters"] > 0:
                event["away_forwards_percent"] = (
                    event["away_forwards_count"] / event["away_skaters"]
                )

            else:
                event["away_forwards_percent"] = 0

            if not event["home_goalie"]:
                home_on = "E"

            else:
                home_on = event["home_skaters"]

            if not event["away_goalie"]:
                away_on = "E"

            else:
                away_on = event["away_skaters"]

            event["strength_state"] = f"{home_on}v{away_on}"

            if event.get("event_team") == event["home_team"] or not event.get(
                "event_team"
            ):
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
                    "forwards_count": event["home_forwards_count"],
                    "forwards_percent": event["home_forwards_percent"],
                    "defense_eh_id": event["home_defense_eh_id"],
                    "defense_api_id": event["home_defense_api_id"],
                    "defense": event["home_defense"],
                    "defense_count": event["home_defense_count"],
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
                    "opp_team_on_positions": event["away_on_positions"],
                    "opp_forwards_eh_id": event["away_forwards_eh_id"],
                    "opp_forwards_api_id": event["away_forwards_api_id"],
                    "opp_forwards": event["away_forwards"],
                    "opp_forwards_count": event["away_forwards_count"],
                    "opp_forwards_percent": event["away_forwards_percent"],
                    "opp_defense_eh_id": event["away_defense_eh_id"],
                    "opp_defense_api_id": event["away_defense_api_id"],
                    "opp_defense": event["away_defense"],
                    "opp_defense_count": event["away_defense_count"],
                    "opp_goalie_eh_id": event["away_goalie_eh_id"],
                    "opp_goalie_api_id": event["away_goalie_api_id"],
                    "opp_goalie": event["away_goalie"],
                }

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
                    "forwards_count": event["away_forwards_count"],
                    "forwards_percent": event["away_forwards_percent"],
                    "defense_eh_id": event["away_defense_eh_id"],
                    "defense_api_id": event["away_defense_api_id"],
                    "defense": event["away_defense"],
                    "defense_count": event["away_defense_count"],
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
                    "opp_forwards_count": event["home_forwards_count"],
                    "opp_forwards_percent": event["home_forwards_percent"],
                    "opp_defense_eh_id": event["home_defense_eh_id"],
                    "opp_defense_api_id": event["home_defense_api_id"],
                    "opp_defense": event["home_defense"],
                    "opp_defense_count": event["home_defense_count"],
                    "opp_goalie_eh_id": event["home_goalie_eh_id"],
                    "opp_goalie_api_id": event["home_goalie_api_id"],
                    "opp_goalie": event["home_goalie"],
                }

            event.update(new_values)

            event_team_lists = {
                "event_on_x": event.get("teammates", []),
                "event_on_x_eh_id": event.get("teammates_eh_id", []),
                "event_on_x_api_id": event.get("teammates_api_id", []),
                "event_on_x_pos": event.get("teammates_positions", []),
            }

            if event.get("own_goalie"):
                event_team_lists.update(
                    {
                        "event_on_x": event["teammates"] + event["own_goalie"],
                        "event_on_x_eh_id": event["teammates_eh_id"]
                        + event["own_goalie_eh_id"],
                        "event_on_x_api_id": event["teammates_api_id"]
                        + event["own_goalie_api_id"],
                        "event_on_x_pos": event["teammates_positions"] + ["G"],
                    }
                )

            for list_name, event_team_list in event_team_lists.items():
                for player_num, player in enumerate(event_team_list):
                    col_name = list_name.replace("x", str(player_num + 1))
                    event[col_name] = player

            opp_team_lists = {
                "opp_on_x": event.get("opp_team_on", []),
                "opp_on_x_eh_id": event.get("opp_team_on_eh_id", []),
                "opp_on_x_api_id": event.get("opp_team_on_api_id", []),
                "opp_on_x_pos": event.get("opp_team_on_positions", []),
            }

            if event.get("opp_goalie"):
                opp_team_lists.update(
                    {
                        "opp_on_x": event["opp_team_on"] + event["opp_goalie"],
                        "opp_on_x_eh_id": event["opp_team_on_eh_id"]
                        + event["opp_goalie_eh_id"],
                        "opp_on_x_api_id": event["opp_team_on_api_id"]
                        + event["opp_goalie_api_id"],
                        "opp_on_x_pos": event["opp_team_on_positions"] + ["G"],
                    }
                )

            for list_name, opp_team_list in opp_team_lists.items():
                for player_num, player in enumerate(opp_team_list):
                    col_name = list_name.replace("x", str(player_num + 1))
                    event[col_name] = player

            if event["event"] == "CHANGE":
                if event["change_on"]:
                    change_on_lists = {
                        "change_on_x": event.get("change_on", "").split(", "),
                        "change_on_x_eh_id": event.get("change_on_eh_id", "").split(
                            ", "
                        ),
                        "change_on_x_api_id": event.get("change_on_api_id", "").split(
                            ", "
                        ),
                        "change_on_x_pos": event.get("change_on_positions", "").split(
                            ", "
                        ),
                    }

                    for list_name, change_on_list in change_on_lists.items():
                        for player_num, player in enumerate(change_on_list):
                            col_name = list_name.replace("x", str(player_num + 1))
                            event[col_name] = player

                if event["change_off"]:
                    change_off_lists = {
                        "change_off_x": event.get("change_off", "").split(", "),
                        "change_off_x_eh_id": event.get("change_off_eh_id", "").split(
                            ", "
                        ),
                        "change_off_x_api_id": event.get("change_off_api_id", "").split(
                            ", "
                        ),
                        "change_off_x_pos": event.get("change_off_positions", "").split(
                            ", "
                        ),
                    }

                    for list_name, change_off_list in change_off_lists.items():
                        for player_num, player in enumerate(change_off_list):
                            col_name = list_name.replace("x", str(player_num + 1))
                            event[col_name] = player

            if "PENALTY SHOT" in event["description"]:
                event["strength_state"] = "1v0"

            if (event["home_skaters"] > 5 and event["home_goalie"] != []) or (
                event["away_skaters"] > 5 and event["away_goalie"] != []
            ):
                event["strength_state"] = "ILLEGAL"

                event["opp_strength_state"] = "ILLEGAL"

            if event["period"] == 5 and event["session"] == "R":  # Not covered by tests
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
                    # game_seconds_list = [x["game_seconds"] for x in self._play_by_play]

                    # max_seconds = max(game_seconds_list)

                    bad_seconds = []  # [0, 1200, 2400, 3600, 3900, max_seconds]

                    if event["game_seconds"] not in bad_seconds:
                        event["coords_x"] = faceoffs[0].get("coords_x", "")

                        event["coords_y"] = faceoffs[0].get("coords_y", "")

                        if event["event_team"] == faceoffs[0]["event_team"]:
                            event["zone_start"] = faceoffs[0]["zone"]

                        else:
                            zones = {"OFF": "DEF", "DEF": "OFF", "NEU": "NEU"}

                            event["zone_start"] = zones.get(faceoffs[0]["zone"])

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

            if event.get("high_danger") == 1:
                if event["event"] in ["GOAL", "SHOT", "MISS"]:
                    event["hd_fenwick"] = 1

                if event["event"] == "GOAL":
                    event["hd_goal"] = 1
                    event["hd_shot"] = 1

                if event["event"] == "SHOT":
                    event["hd_shot"] = 1

                if event["event"] == "MISS":
                    event["hd_miss"] = 1

            else:
                event["hd_goal"] = 0
                event["hd_shot"] = 0
                event["hd_miss"] = 0
                event["hd_fenwick"] = 0

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

            if event["event"] == "CHANGE" and event.get("zone_start"):
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

            if (
                event["event"] == "BLOCK"
                and "BLOCKED BY TEAMMATE" in event["description"]
            ):  # Not covered by tests
                event["teammate_block"] = 1
                event["block"] = 0
            else:
                event["teammate_block"] = 0

            game_id_str = str(event["game_id"])
            event_idx_str = str(event["event_idx"])

            if len(event_idx_str) == 1:
                event_id = game_id_str + "000" + event_idx_str

            elif len(event_idx_str) == 2:
                event_id = game_id_str + "00" + event_idx_str

            elif len(event_idx_str) == 3:
                event_id = game_id_str + "0" + event_idx_str

            elif len(event_idx_str) == 4:  # Not covered by tests
                event_id = game_id_str + event_idx_str

            event["id"] = int(event_id)

            final_events.append(PBPEvent.model_validate(event).model_dump())
            final_events_ext.append(PBPEventExt.model_validate(event).model_dump())

        self._play_by_play = final_events
        self._play_by_play_ext = final_events_ext

    def _prep_xg(self):
        """Method to add xG predictions to play-by-play data. Updates self._play_by_play.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Requires clean events from the shifts, API events, and HTML events feeds

            HTML events
            >>> game._scrape_html_events()  # Scrapes events from HTML feed
            >>> game._munge_html_events()  # Preps raw events, updates game._html_events

            API events
            >>> game._munge_api_events()  # Preps raw events, updates game._api_events

            Shifts and changes
            >>> game._scrape_html_events()  # Scrapes shifts from HTML feed
            >>> game._munge_shifts()  # Preps raw shifts, updates game._shifts
            >>> game._munge_changes()  # Preps changes

            Combines them all
            >>> game._combine_events()  # Combines raw events, into game._play_by_play

            Data can then be manually cleaned
            >>> game._munge_play_by_play()
            >>> game._prep_xg()
            >>> game._play_by_play  # Returns cleaned data
        """
        plays = self._play_by_play

        even_strengths = ["5v5", "4v4", "3v3"]
        powerplay_strengths = ["5v4", "4v3", "5v3"]
        shorthanded_strengths = ["4v5", "3v4", "3v5"]
        empty_for_strengths = ["Ev5", "Ev4", "Ev3"]
        empty_against_strengths = ["5vE", "4vE", "3vE"]

        important_events = [
            "SHOT",
            "FAC",
            "HIT",
            "BLOCK",
            "MISS",
            "GIVE",
            "TAKE",
            # "PENL",
            "GOAL",
        ]

        xg_plays = [
            x
            for x in plays
            if x["event"] in important_events
            and x["strength_state"] != "1v0"
            and x["strength_state"] != "EvE"
            and x["coords_x"] is not None
            and x["coords_y"] is not None
        ]

        xg_idxs = [x["event_idx"] for x in xg_plays]

        non_xg_plays = [x for x in plays if x["event_idx"] not in xg_idxs]

        for play in non_xg_plays:
            play["pred_goal"] = 0.0

        for idx, play in enumerate(xg_plays):
            if play["event"] not in ["GOAL", "SHOT", "MISS"]:
                play["pred_goal"] = 0.0
                continue

            xg_fields = {
                "period": play["period"],
                "period_seconds": play["period_seconds"],
                "score_diff": play["score_diff"],
                "danger": play["danger"],
                "high_danger": play["danger"],
                "event_distance": play["event_distance"],
                "event_angle": play["event_angle"],
                "is_home": play["is_home"],
                # "forwards_count": play["forwards_count"],
                # "forwards_percent": play["forwards_percent"],
                # "opp_forwards_count": play["opp_forwards_count"],
                # "opp_forwards_percent": play["opp_forwards_percent"],
            }

            if play.get("player_1_position") in ["L", "C", "R"]:
                xg_fields["position_f"] = 1
                xg_fields["position_d"] = 0
                xg_fields["position_g"] = 0

            if play.get("player_1_position") == "D":
                xg_fields["position_f"] = 0
                xg_fields["position_d"] = 1
                xg_fields["position_g"] = 0

            if play.get("player_1_position") == "G":
                xg_fields["position_f"] = 0
                xg_fields["position_d"] = 0
                xg_fields["position_g"] = 1

            shot_types = [
                "backhand",
                "bat",
                "between_legs",
                "cradle",
                "deflected",
                "poke",
                "slap",
                "snap",
                "tip_in",
                "wrap_around",
                "wrist",
            ]

            for shot_type in shot_types:
                if play["shot_type"] == shot_type.upper().replace("_", "-"):
                    xg_fields.update({shot_type: 1})

                else:
                    xg_fields.update({shot_type: 0})

            if (
                idx == 0 or xg_plays[idx - 1]["period"] != play["period"]
            ):  # Not covered by tests
                new_fields = [
                    "is_rebound",
                    "rush_attempt",
                    "seconds_since_last",
                    "event_type_last",
                    "distance_from_last",
                    "prior_shot_same",
                    "prior_miss_same",
                    "prior_block_same",
                    "prior_give_same",
                    "prior_take_same",
                    "prior_hit_same",
                    "prior_shot_opp",
                    "prior_miss_opp",
                    "prior_block_opp",
                    "prior_give_opp",
                    "prior_take_opp",
                    "prior_hit_opp",
                    "prior_face",
                ]

                new_fields = {x: 0 for x in new_fields}

                xg_fields.update(new_fields)

            else:
                previous_play = xg_plays[idx - 1]

                seconds_since_last = (
                    play["game_seconds"] - previous_play["game_seconds"]
                )

                xg_fields["seconds_since_last"] = seconds_since_last

                event_team_last = previous_play["event_team"]
                event_type_last = previous_play["event"]
                coords_x_last = previous_play["coords_x"]
                coords_y_last = previous_play["coords_y"]
                zone_last = previous_play["zone"]

                distance_from_last = (
                    (play["coords_x"] - coords_x_last) ** 2
                    + (play["coords_y"] - coords_y_last) ** 2
                ) ** (1 / 2)

                xg_fields["distance_from_last"] = distance_from_last

                same_team_as_last = play["event_team"] == event_team_last
                not_same_team_as_last = play["event_team"] != event_team_last

                last_is_shot = previous_play["event"] == "SHOT"
                last_is_miss = previous_play["event"] == "MISS"
                last_is_block = previous_play["event"] == "BLOCK"
                last_is_give = previous_play["event"] == "GIVE"
                last_is_take = previous_play["event"] == "TAKE"
                last_is_hit = previous_play["event"] == "HIT"
                last_is_face = previous_play["event"] == "FACE"

                if last_is_shot & same_team_as_last:
                    xg_fields["prior_shot_same"] = 1
                else:
                    xg_fields["prior_shot_same"] = 0

                if last_is_miss & same_team_as_last:
                    xg_fields["prior_miss_same"] = 1
                else:
                    xg_fields["prior_miss_same"] = 0

                if last_is_block & same_team_as_last:
                    xg_fields["prior_block_same"] = 1
                else:
                    xg_fields["prior_block_same"] = 0

                if last_is_give & same_team_as_last:
                    xg_fields["prior_give_same"] = 1
                else:
                    xg_fields["prior_give_same"] = 0

                if last_is_take & same_team_as_last:
                    xg_fields["prior_take_same"] = 1
                else:
                    xg_fields["prior_take_same"] = 0

                if last_is_hit & same_team_as_last:
                    xg_fields["prior_hit_same"] = 1
                else:
                    xg_fields["prior_hit_same"] = 0

                if last_is_shot & not_same_team_as_last:
                    xg_fields["prior_shot_opp"] = 1
                else:
                    xg_fields["prior_shot_opp"] = 0

                if last_is_miss & not_same_team_as_last:
                    xg_fields["prior_miss_opp"] = 1
                else:
                    xg_fields["prior_miss_opp"] = 0

                if last_is_block & not_same_team_as_last:
                    xg_fields["prior_block_opp"] = 1
                else:
                    xg_fields["prior_block_opp"] = 0

                if last_is_give & not_same_team_as_last:
                    xg_fields["prior_give_opp"] = 1
                else:
                    xg_fields["prior_give_opp"] = 0

                if last_is_take & not_same_team_as_last:
                    xg_fields["prior_take_opp"] = 1
                else:
                    xg_fields["prior_take_opp"] = 0

                if last_is_hit & not_same_team_as_last:
                    xg_fields["prior_hit_opp"] = 1
                else:
                    xg_fields["prior_hit_opp"] = 0

                if last_is_face:  # Not covered by tests
                    xg_fields["prior_face"] = 1
                else:
                    xg_fields["prior_face"] = 0

                if play["score_diff"] > 4:
                    xg_fields["score_diff"] = 4

                elif play["score_diff"] < -4:
                    xg_fields["score_diff"] = -4

                if (
                    event_type_last in ["SHOT", "MISS"]
                    and same_team_as_last
                    and xg_fields["seconds_since_last"] <= 3
                ) or (
                    event_type_last == "BLOCK"
                    and not_same_team_as_last
                    and xg_fields["seconds_since_last"] <= 3
                ):
                    xg_fields["is_rebound"] = 1

                else:
                    xg_fields["is_rebound"] = 0

                if xg_fields["seconds_since_last"] <= 4 and zone_last == "NEU":
                    xg_fields["rush_attempt"] = 1

                else:
                    xg_fields["rush_attempt"] = 0

            strength_states_list = [
                even_strengths,
                powerplay_strengths,
                shorthanded_strengths,
                empty_for_strengths,
                empty_against_strengths,
            ]

            strength_states_flat = [
                strength_state
                for strength_states in strength_states_list
                for strength_state in strength_states
            ]

            if play["strength_state"] not in strength_states_flat:
                play["pred_goal"] = 0.0
                continue

            for strength_states in strength_states_list:
                if play["strength_state"] in strength_states:
                    for strength_state in strength_states:
                        if play["strength_state"] == strength_state:
                            xg_fields[f"strength_state_{strength_state}"] = 1

                        else:
                            xg_fields[f"strength_state_{strength_state}"] = 0

            xg_fields = XGFields.model_validate(xg_fields).model_dump(
                exclude_unset=True
            )
            xg_data = np.array(list(xg_fields.values()), ndmin=2)

            self._xg_fields.update({play["event_idx"]: xg_data})

            if play["strength_state"] in even_strengths:
                preds = self._es_model.predict_proba(xg_data)

            if play["strength_state"] in powerplay_strengths:
                preds = self._pp_model.predict_proba(xg_data)

            if play["strength_state"] in shorthanded_strengths:
                preds = self._sh_model.predict_proba(xg_data)

            if play["strength_state"] in empty_for_strengths:
                preds = self._ef_model.predict_proba(xg_data)

            if play["strength_state"] in empty_against_strengths:
                preds = self._ea_model.predict_proba(xg_data)

            pred_goal = preds[:, 1][0]
            play["pred_goal"] = pred_goal

        new_plays = xg_plays + non_xg_plays

        new_plays = sorted(new_plays, key=lambda x: x["event_idx"])

        self._play_by_play = new_plays

    @property
    def play_by_play(self) -> list:
        """List of events in play-by-play. Each event is a dictionary with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).play_by_play_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed since previous event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_api_id (list | str | None):
                NHL API IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_api_id (list | str | None):
                NHL API IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_on_forwards_api_id (list | str | None):
                NHL API IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_off_forwards_api_id (list | str | None):
                NHL API IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_on_defense_api_id (list | str | None):
                NHL API IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_off_defense_api_id (list | str | None):
                NHL API IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_on_goalie_api_id (list | str | None):
                NHL API ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            change_off_goalie_api_id (list | str | None):
                NHL API ID of the goalie off, e.g., None
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.play_by_play

        """
        if self._play_by_play is None:
            if self._rosters is None:
                if self._api_rosters is None:
                    self._munge_api_rosters()

                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                self._combine_rosters()

            if self._changes is None:
                self._scrape_shifts()
                self._munge_shifts()

                self._munge_changes()

            if self._html_events is None:
                self._scrape_html_events()
                self._munge_html_events()

            if self._api_events is None:
                self._munge_api_events()

            self._combine_events()
            self._munge_play_by_play()
            self._prep_xg()

        return self._play_by_play

    @property
    def play_by_play_ext(self) -> list:
        """List of additional columns used for aggregating on-ice statistics.

        Returns:
            id (int):
                Unique play identifier, the equivalent of the game ID and event_idx concatenated
            event_idx (int):
                Index ID for event
            event_on_1 (str | None):
                Player name
            event_on_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_1_api_id (int | None):
                ID used for matching NHL API data
            event_on_1_pos (str | None):
                Player position
            event_on_2 (str | None):
                Player name
            event_on_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_2_api_id (int | None):
                ID used for matching NHL API data
            event_on_2_pos (str | None):
                Player position
            event_on_3 (str | None):
                Player name
            event_on_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_3_api_id (int | None):
                ID used for matching NHL API data
            event_on_3_pos (str | None):
                Player position
            event_on_4 (str | None):
                Player name
            event_on_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_4_api_id (int | None):
                ID used for matching NHL API data
            event_on_4_pos (str | None):
                Player position
            event_on_5 (str | None):
                Player name
            event_on_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_5_api_id (int | None):
                ID used for matching NHL API data
            event_on_5_pos (str | None):
                Player position
            event_on_6 (str | None):
                Player name
            event_on_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_6_api_id (int | None):
                ID used for matching NHL API data
            event_on_6_pos (str | None):
                Player position
            event_on_7 (str | None):
                Player name
            event_on_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            event_on_7_api_id (int | None):
                ID used for matching NHL API data
            event_on_7_pos (str | None):
                Player position
            opp_on_1 (str | None):
                Player name
            opp_on_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_1_api_id (int | None):
                ID used for matching NHL API data
            opp_on_1_pos (str | None):
                Player position
            opp_on_2 (str | None):
                Player name
            opp_on_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_2_api_id (int | None):
                ID used for matching NHL API data
            opp_on_2_pos (str | None):
                Player position
            opp_on_3 (str | None):
                Player name
            opp_on_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_3_api_id (int | None):
                ID used for matching NHL API data
            opp_on_3_pos (str | None):
                Player position
            opp_on_4 (str | None):
                Player name
            opp_on_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_4_api_id (int | None):
                ID used for matching NHL API data
            opp_on_4_pos (str | None):
                Player position
            opp_on_5 (str | None):
                Player name
            opp_on_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_5_api_id (int | None):
                ID used for matching NHL API data
            opp_on_5_pos (str | None):
                Player position
            opp_on_6 (str | None):
                Player name
            opp_on_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_6_api_id (int | None):
                ID used for matching NHL API data
            opp_on_6_pos (str | None):
                Player position
            opp_on_7 (str | None):
                Player name
            opp_on_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            opp_on_7_api_id (int | None):
                ID used for matching NHL API data
            opp_on_7_pos (str | None):
                Player position
            change_on_1 (str | None):
                Player name
            change_on_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_1_api_id (int | None):
                ID used for matching NHL API data
            change_on_1_pos (str | None):
                Player position
            change_on_2 (str | None):
                Player name
            change_on_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_2_api_id (int | None):
                ID used for matching NHL API data
            change_on_2_pos (str | None):
                Player position
            change_on_3 (str | None):
                Player name
            change_on_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_3_api_id (int | None):
                ID used for matching NHL API data
            change_on_3_pos (str | None):
                Player position
            change_on_4 (str | None):
                Player name
            change_on_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_4_api_id (int | None):
                ID used for matching NHL API data
            change_on_4_pos (str | None):
                Player position
            change_on_5 (str | None):
                Player name
            change_on_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_5_api_id (int | None):
                ID used for matching NHL API data
            change_on_5_pos (str | None):
                Player position
            change_on_6 (str | None):
                Player name
            change_on_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_6_api_id (int | None):
                ID used for matching NHL API data
            change_on_6_pos (str | None):
                Player position
            change_on_7 (str | None):
                Player name
            change_on_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_on_7_api_id (int | None):
                ID used for matching NHL API data
            change_on_7_pos (str | None):
                Player position
            change_off_1 (str | None):
                Player name
            change_off_1_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_1_api_id (int | None):
                ID used for matching NHL API data
            change_off_1_pos (str | None):
                Player position
            change_off_2 (str | None):
                Player name
            change_off_2_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_2_api_id (int | None):
                ID used for matching NHL API data
            change_off_2_pos (str | None):
                Player position
            change_off_3 (str | None):
                Player name
            change_off_3_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_3_api_id (int | None):
                ID used for matching NHL API data
            change_off_3_pos (str | None):
                Player position
            change_off_4 (str | None):
                Player name
            change_off_4_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_4_api_id (int | None):
                ID used for matching NHL API data
            change_off_4_pos (str | None):
                Player position
            change_off_5 (str | None):
                Player name
            change_off_5_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_5_api_id (int | None):
                ID used for matching NHL API data
            change_off_5_pos (str | None):
                Player position
            change_off_6 (str | None):
                Player name
            change_off_6_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_6_api_id (int | None):
                ID used for matching NHL API data
            change_off_6_pos (str | None):
                Player position
            change_off_7 (str | None):
                Player name
            change_off_7_eh_id (str | None):
                ID used for matching with Evolving Hockey data
            change_off_7_api_id (int | None):
                ID used for matching NHL API data
            change_off_7_pos (str | None):
                Player position

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.play_by_play_ext

        """
        if self._play_by_play is None:
            if self._rosters is None:
                if self._api_rosters is None:
                    self._munge_api_rosters()

                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                self._combine_rosters()

            if self._changes is None:
                self._scrape_shifts()
                self._munge_shifts()

                self._munge_changes()

            if self._html_events is None:
                self._scrape_html_events()
                self._munge_html_events()

            if self._api_events is None:
                self._munge_api_events()

            self._combine_events()
            self._munge_play_by_play()
            self._prep_xg()

        return self._play_by_play_ext

    @property
    def play_by_play_df(self) -> pd.DataFrame:
        """Pandas Dataframe of play-by-play data.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed since previous event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.play_by_play_df

        """
        if self._play_by_play is None:
            if self._rosters is None:
                if self._api_rosters is None:
                    self._munge_api_rosters()

                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                self._combine_rosters()

            if self._changes is None:
                self._scrape_shifts()
                self._munge_shifts()

                self._munge_changes()

            if self._html_events is None:
                self._scrape_html_events()
                self._munge_html_events()

            if self._api_events is None:
                self._munge_api_events()

            self._combine_events()
            self._munge_play_by_play()
            self._prep_xg()

        return pd.DataFrame(self._play_by_play)

    def _combine_rosters(self) -> None:
        """Method to combine API and HTML rosters. Updates self._rosters.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Requires clean rosters from the API and HTML feeds

            HTML rosters
            >>> game._scrape_html_rosters()
            >>> game._munge_html_rosters()

            API rosters
            >>> game._munge_api_rosters()

            Combined rosters
            >>> game._combine_rosters()

            However, the combined rosters do not need to be manually cleaned - data are
            cleaned at the level of their respective source
            >>> game._rosters  # Returns clean rosters if all of the above have been performed

        """
        html_rosters = self._html_rosters
        api_rosters = self._api_rosters

        api_rosters_dict = {x["team_jersey"]: x for x in api_rosters}

        players = []

        for player in html_rosters:
            if player["status"] == "ACTIVE":
                api_info = api_rosters_dict[player["team_jersey"]]

            else:
                api_info = {"api_id": None, "headshot_url": None}

            player_info = {}

            player_info.update(player)

            new_values = {
                "api_id": api_info["api_id"],
                "headshot_url": api_info["headshot_url"],
            }

            player_info.update(new_values)

            player_info = rosters_fixes(self.game_id, player_info)

            players.append(RosterPlayer.model_validate(player_info).model_dump())

        self._rosters = players

    @property
    def rosters(self) -> list:
        """List of players scraped from API & HTML endpoints. Returns a dictionary of players with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).rosters_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            api_id (int | None):
                Player's NHL API ID, e.g., 8476887
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE
            headshot_url (str | None):
                URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.rosters

        """
        if self._rosters is None:
            if self._api_rosters is None:
                self._munge_api_rosters()

            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._combine_rosters()

        return self._rosters

    @property
    def rosters_df(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from API & HTML endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            api_id (int | None):
                Player's NHL API ID, e.g., 8476887
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE
            headshot_url (str | None):
                URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.rosters_df

        """
        if self._rosters is None:
            if self._api_rosters is None:
                self._munge_api_rosters()

            if self._html_rosters is None:
                self._scrape_html_rosters()
                self._munge_html_rosters()

            self._combine_rosters()

        return pd.DataFrame(self._rosters)

    def _scrape_shifts(self) -> None:
        """Method for scraping shifts from HTML endpoint. Updates self._shifts.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/

        Examples:
            First, instantiate the Game object
            >>> game = Game(2023020001)

            Before cleaning the data, game._shifts is None
            >>> game._shifts  # Returns None

            Once you scrape the data, you can access it in raw form, prior to any processing
            >>> game._scrape_shifts()  # Scrapes raw data and adds it to game._shifts
            >>> game.shifts  # Returns cleaned shifts data
            >>> game.shifts_df  # Same, but a Pandas DataFrame

            You then have to manually clean the data
            >>> game._munge_shifts()
            >>> game.shifts  # Returns cleaned shifts data
            >>> game.shifts_df  # Same but a Pandas DataFrame
        """
        # Creating basic information from game ID
        season = self.season
        game_session = self.session
        game_id = self.game_id
        s = self._requests_session

        # This is the list for collecting all the game information for the end

        game_list = []

        # Dictionary of urls for scraping

        urls_dict = {
            "HOME": self.home_shifts_endpoint,
            "AWAY": self.away_shifts_endpoint,
        }

        # Iterating through the url dictionary

        for team_venue, url in urls_dict.items():
            response = s.get(url)

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

            if team_name is None:  # Not covered by tests
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

                    if full_name == " ":  # Not covered by tests
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
                    if full_name == " ":  # Not covered by tests
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
        """Method to munge list of shifts from HTML endpoint. Updates self._shifts."""
        season = self.season
        game_session = self.session

        # Iterating through the lists of shifts

        roster = self._rosters

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

            shift["api_id"] = actives.get(
                shift["team_jersey"], scratches.get(shift["team_jersey"])
            )["api_id"]

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

                except ValueError:  # Not covered by tests
                    continue

            # Fixing end time if it is blank or empty

            if (
                shift["end_time"] == " " or shift["end_time"] == ""
            ):  # Not covered by tests
                # Calculating end time based on duration seconds

                shift["end_time_seconds"] = (
                    shift["start_time_seconds"] + shift["duration_seconds"]
                )

                # Creating end time based on time delta

                shift["end_time"] = str(
                    timedelta(seconds=shift["end_time_seconds"])
                ).split(":", 1)[1]

            # If the shift start is after the shift end, we need to fix the error

            if (
                shift["start_time_seconds"] > shift["end_time_seconds"]
            ):  # Not covered by tests
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

                if len(goalies) < 1:  # Not covered by tests
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
                    and (
                        not shift.get("shift_end")
                        or shift["shift_end"] == "0:00 / 0:00"
                    )
                ):  # Not covered by tests
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

                    # Setting duration and duration in seconds

                    shift["duration_seconds"] = (
                        shift["end_time_seconds"] - shift["start_time_seconds"]
                    )

                    shift["duration"] = str(
                        timedelta(seconds=shift["duration_seconds"])
                    ).split(":", 1)[1]

        self._shifts = [
            PlayerShift.model_validate(shift).model_dump() for shift in self._shifts
        ]

    @property
    def shifts(self) -> list:
        """List of shifts scraped from HTML endpoint. Returns a dictionary of player - shifts with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).shifts_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            jersey (int):
                Player's jersey number, e.g., 9
            shift_count (int):
                Shift number for that player, e.g., 1
            period (int):
                Period number for the shift, e.g., 1
            start_time (str):
                Time shift started, e.g., 0:00
            end_time (str):
                Time shift ended, e.g., 0:18
            duration (str):
                Length of shift, e.g, 00:18
            start_time_seconds (int):
                Time shift started in seconds, e.g., 0
            end_time_seconds (int):
                Time shift ended in seconds, e.g., 18
            duration_seconds (int):
                Length of shift in seconds, e.g., 18
            shift_start (str):
                Time the shift started as the original string, e.g., 0:00 / 20:00
            shift_end (str):
                Time the shift ended as the original string, e.g., 0:18 / 19:42
            goalie (int):
                Whether player is a goalie, e.g., 0
            is_home (int):
                Whether player is home e.g., 0
            is_away (int):
                Whether player is away, e.g., 1
            team_venue (str):
                Whether player is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.shifts

        """
        # TODO: Add API ID to documentation

        if self._shifts is None:
            if self._rosters is None:
                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                if self._api_rosters is None:
                    self._munge_api_rosters()

                self._combine_rosters()

            self._scrape_shifts()
            self._munge_shifts()

        return self._shifts

    @property
    def shifts_df(self) -> pd.DataFrame:
        """Pandas Dataframe of shifts scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            jersey (int):
                Player's jersey number, e.g., 9
            shift_count (int):
                Shift number for that player, e.g., 1
            period (int):
                Period number for the shift, e.g., 1
            start_time (str):
                Time shift started, e.g., 0:00
            end_time (str):
                Time shift ended, e.g., 0:18
            duration (str):
                Length of shift, e.g, 00:18
            start_time_seconds (int):
                Time shift started in seconds, e.g., 0
            end_time_seconds (int):
                Time shift ended in seconds, e.g., 18
            duration_seconds (int):
                Length of shift in seconds, e.g., 18
            shift_start (str):
                Time the shift started as the original string, e.g., 0:00 / 20:00
            shift_end (str):
                Time the shift ended as the original string, e.g., 0:18 / 19:42
            goalie (int):
                Whether player is a goalie, e.g., 0
            is_home (int):
                Whether player is home e.g., 0
            is_away (int):
                Whether player is away, e.g., 1
            team_venue (str):
                Whether player is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.shifts_df

        """
        # TODO: Add API ID to documentation

        if self._shifts is None:
            if self._rosters is None:
                if self._html_rosters is None:
                    self._scrape_html_rosters()
                    self._munge_html_rosters()

                if self._api_rosters is None:
                    self._munge_api_rosters()

                self._combine_rosters()

            self._scrape_shifts()
            self._munge_shifts()

        return pd.DataFrame(self._shifts)


class Scraper:
    """Class instance for scraping play-by-play and other data for NHL games.

    Parameters:
        game_ids (list[str | float | int] | pd.Series | str | float | int):
            List of 10-digit game identifier, e.g., `[2023020001, 2023020002, 2023020003]`
        disable_progress_bar (bool):
            If true, disables the progress bar

    Attributes:
        game_ids (list):
            Game IDs that the Scraper will access, e.g., `[2023020001, 2023020002, 2023020003]`

    Examples:
        First, instantiate the Scraper object
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

    def __init__(
        self,
        game_ids: list[str | float | int] | pd.Series | str | float | int,
        disable_progress_bar: bool = False,
    ):
        """Instantiates a Scraper object for a given game ID or list / list-like object of game IDs."""
        game_ids = convert_to_list(game_ids, "game ID")

        self.disable_progress_bar = False

        if disable_progress_bar:
            self.disable_progress_bar = True

        self.game_ids: list = game_ids
        self._scraped_games: list = []
        self._bad_games: list = []

        self._requests_session = ChickenSession()

        self._api_events: list = []
        self._scraped_api_events: list = []

        self._api_rosters: list = []
        self._scraped_api_rosters: list = []

        self._changes: list = []
        self._scraped_changes: list = []

        self._html_events: list = []
        self._scraped_html_events: list = []

        self._html_rosters: list = []
        self._scraped_html_rosters: list = []

        self._rosters: list = []
        self._scraped_rosters: list = []

        self._shifts: list = []
        self._scraped_shifts: list = []

        self._play_by_play: list = []
        self._play_by_play_ext: list = []
        self._scraped_play_by_play: list = []

        self._ind_stats: pd.DataFrame = pd.DataFrame()
        self._oi_stats: pd.DataFrame = pd.DataFrame()
        self._zones: pd.DataFrame = pd.DataFrame()
        self._stats: pd.DataFrame = pd.DataFrame()
        self._stats_levels: dict = {
            "level": None,
            "score": None,
            "teammates": None,
            "opposition": None,
        }

        self._lines: pd.DataFrame = pd.DataFrame()
        self._lines_levels: dict = {
            "position": None,
            "level": None,
            "score": None,
            "teammates": None,
            "opposition": None,
        }

        self._team_stats: pd.DataFrame = pd.DataFrame()
        self._team_stats_levels: dict = {
            "level": None,
            "score": None,
            "strengths": None,
            "opposition": None,
        }

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
    ) -> None:
        """Method for scraping any data. Iterates through a list of game IDs using Game objects.

        For more information and usage, see https://chickenstats.com/latest/contribute/contribute/.

        Examples:
            First, instantiate the Scraper object
            >>> game_ids = list(range(2023020001, 2023020011))
            >>> scraper = Scraper(game_ids)

            Before scraping the data, any of the storage objects are None
            >>> scraper._shifts  # Returns None
            >>> scraper._play_by_play  # Also returns None

            You can use the `_scrape` method to get any data
            >>> scraper._scrape("html_events")
            >>> scraper._html_events  # Returns data as a list
            >>> scraper.html_events  # Returns data as a Pandas DataFrame
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

        if scrape_type == "api_events":
            game_ids = [x for x in self.game_ids if x not in self._scraped_api_events]

        if scrape_type == "api_rosters":
            game_ids = [x for x in self.game_ids if x not in self._scraped_api_rosters]

        if scrape_type == "changes":
            game_ids = [x for x in self.game_ids if x not in self._scraped_changes]

        if scrape_type == "html_events":
            game_ids = [x for x in self.game_ids if x not in self._scraped_html_events]

        if scrape_type == "html_rosters":
            game_ids = [x for x in self.game_ids if x not in self._scraped_html_rosters]

        if scrape_type == "play_by_play":
            game_ids = [x for x in self.game_ids if x not in self._scraped_play_by_play]

        if scrape_type == "shifts":
            game_ids = [x for x in self.game_ids if x not in self._scraped_rosters]

        if scrape_type == "rosters":
            game_ids = [x for x in self.game_ids if x not in self._scraped_rosters]

        with self._requests_session as s:
            with ChickenProgress(disable=self.disable_progress_bar) as progress:
                pbar_stub = pbar_stubs[scrape_type]

                pbar_message = f"Downloading {pbar_stub} for {game_ids[0]}..."

                game_task = progress.add_task(pbar_message, total=len(game_ids))

                for idx, game_id in enumerate(game_ids):
                    game = Game(game_id, s)

                    if scrape_type == "api_events":
                        if game_id in self._scraped_api_events:  # Not covered by tests
                            continue

                        else:
                            if (
                                game_id in self._scraped_api_rosters
                            ):  # Not covered by tests
                                game._api_rosters = [
                                    x
                                    for x in self._api_rosters
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._api_rosters.extend(game.api_rosters)
                                self._scraped_api_rosters.append(game_id)

                            self._api_events.extend(game.api_events)
                            self._scraped_api_events.append(game_id)

                    if scrape_type == "api_rosters":
                        if game_id in self._scraped_api_rosters:  # Not covered by tests
                            continue

                        else:
                            self._api_rosters.extend(game.api_rosters)
                            self._scraped_api_rosters.append(game_id)

                    if scrape_type == "changes":
                        if game_id in self._scraped_changes:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:  # Not covered by tests
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

                            if game_id in self._scraped_shifts:  # Not covered by tests
                                game._shifts = [
                                    x for x in self._shifts if x["game_id"] == game_id
                                ]

                            else:
                                self._shifts.extend(game.shifts)
                                self._scraped_shifts.append(game_id)

                            self._changes.extend(game.changes)
                            self._scraped_changes.append(game_id)

                    if scrape_type == "html_events":
                        if game_id in self._scraped_html_events:  # Not covered by tests
                            continue

                        else:
                            if (
                                game_id in self._scraped_html_rosters
                            ):  # Not covered by tests
                                game._html_rosters = [
                                    x
                                    for x in self._html_rosters
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                            self._html_events.extend(game.html_events)
                            self._scraped_html_events.append(game_id)

                    if scrape_type == "html_rosters":
                        if (
                            game_id in self._scraped_html_rosters
                        ):  # Not covered by tests
                            continue

                        else:
                            self._html_rosters.extend(game.html_rosters)
                            self._scraped_html_rosters.append(game_id)

                    if scrape_type == "play_by_play":
                        if (
                            game_id in self._scraped_play_by_play
                        ):  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:  # Not covered by tests
                                game._rosters = [
                                    x for x in self._rosters if x["game_id"] == game_id
                                ]

                            else:
                                if (
                                    game_id in self._scraped_html_rosters
                                ):  # Not covered by tests
                                    game._html_rosters = [
                                        x
                                        for x in self._html_rosters
                                        if x["game_id"] == game_id
                                    ]

                                else:
                                    self._html_rosters.extend(game.html_rosters)
                                    self._scraped_html_rosters.append(game_id)

                                if (
                                    game_id in self._scraped_api_rosters
                                ):  # Not covered by tests
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

                            if game_id in self._scraped_changes:  # Not covered by tests
                                game._changes = [
                                    x for x in self._changes if x["game_id"] == game_id
                                ]

                            else:
                                if (
                                    game_id in self._scraped_shifts
                                ):  # Not covered by tests
                                    game._shifts = [
                                        x
                                        for x in self._shifts
                                        if x["game_id"] == game_id
                                    ]

                                else:
                                    self._shifts.extend(game.shifts)
                                    self._scraped_shifts.append(game_id)

                                self._changes.extend(game.changes)
                                self._scraped_changes.append(game_id)

                            if (
                                game_id in self._scraped_html_events
                            ):  # Not covered by tests
                                game._html_events = [
                                    x
                                    for x in self._html_events
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._html_events.extend(game.html_events)
                                self._scraped_html_events.append(game_id)

                            if (
                                game_id in self._scraped_api_events
                            ):  # Not covered by tests
                                game._api_events = [
                                    x
                                    for x in self._api_events
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._api_events.extend(game.api_events)
                                self._scraped_api_events.append(game_id)

                            self._play_by_play.extend(game.play_by_play)
                            self._play_by_play_ext.extend(game.play_by_play_ext)
                            self._scraped_play_by_play.append(game_id)

                    if scrape_type == "rosters":
                        if game_id in self._scraped_rosters:  # Not covered by tests
                            continue

                        else:
                            if (
                                game_id in self._scraped_html_rosters
                            ):  # Not covered by tests
                                game._html_rosters = [
                                    x
                                    for x in self._html_rosters
                                    if x["game_id"] == game_id
                                ]

                            else:
                                self._html_rosters.extend(game.html_rosters)
                                self._scraped_html_rosters.append(game_id)

                            if (
                                game_id in self._scraped_api_rosters
                            ):  # Not covered by tests
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

                    if scrape_type == "shifts":
                        if game_id in self._scraped_shifts:  # Not covered by tests
                            continue

                        else:
                            if game_id in self._scraped_rosters:
                                game._rosters = [
                                    x for x in self._rosters if x["game_id"] == game_id
                                ]

                            else:
                                if (
                                    game_id in self._scraped_html_rosters
                                ):  # Not covered by tests
                                    game._html_rosters = [
                                        x
                                        for x in self._html_rosters
                                        if x["game_id"] == game_id
                                    ]
                                else:
                                    self._html_rosters.extend(game.html_rosters)
                                    self._scraped_html_rosters.append(game_id)

                                if (
                                    game_id in self._scraped_api_rosters
                                ):  # Not covered by tests
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

                            self._shifts.extend(game.shifts)
                            self._scraped_shifts.append(game_id)

                    if game_id != self.game_ids[-1]:
                        pbar_message = (
                            f"Downloading {pbar_stub} for {self.game_ids[idx + 1]}..."
                        )

                    else:
                        pbar_message = f"Finished downloading {pbar_stub}"

                    progress.update(
                        game_task, description=pbar_message, advance=1, refresh=True
                    )

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
        if isinstance(game_ids, str) or isinstance(
            game_ids, int
        ):  # Not covered by tests
            game_ids = [game_ids]

        game_ids = [
            int(x) for x in game_ids if x not in self.game_ids
        ]  # Not covered by tests

        self.game_ids.extend(game_ids)  # Not covered by tests

    @property
    def api_events(self) -> pd.DataFrame:
        """Pandas DataFrame of events scraped from API endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 689
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            event_code (str):
                Code to indicate type of event that occured, e.g., 505
            description (str | None):
                Description of the event, e.g., None
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., D
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_team_jersey (str):
                Combination of team and jersey used for player identification purposes, e.g, NSH35
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_2_api_id (str | None):
                NHL API ID for player_2, e.g., None
            player_2_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            player_3_api_id (str | None):
                NHL API ID for player_3, e.g., None
            player_3_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            strength (int):
                Code to indication strength state, e.g., 1560
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            miss_reason (str | None):
                Reason shot missed, e.g., None
            opp_goalie (str | None):
                Opposing goalie, e.g., None
            opp_goalie_eh_id (str | None):
                Evolving Hockey ID for opposing goalie, e.g., None
            opp_goalie_api_id (str | None):
                NHL API ID for opposing goalie, e.g., None
            opp_goalie_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            event_team_id (int):
                NHL ID for the event team, e.g., 18
            stoppage_reason (str | None):
                Reason the play was stopped, e.g., None
            stoppage_reason_secondary (str | None):
                Secondary reason play was stopped, e.g., None
            penalty_type (str | None):
                Type of penalty taken, e.g., None
            penalty_reason (str | None):
                Reason for the penalty, e.g., None
            penalty_duration (int | None):
                Duration of the penalty, e.g., None
            home_team_defending_side (str):
                Side of the ice the home team is defending, e.g., right
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.api_events

        """
        if not self._api_events:
            self._scrape("api_events")

        return pd.DataFrame(self._api_events)

    @property
    def api_rosters(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from API endpoint.

        Returns:
            Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            first_name (str):
                Player's first name, e.g., FILIP
            last_name (str):
                Player's last name, e.g., FORSBERG
            headshot_url (str):
                URL to retreive player's headshot

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.api_rosters
        """
        if not self._api_rosters:
            self._scrape("api_rosters")

        return pd.DataFrame(self._api_rosters)

    @property
    def changes(self) -> pd.DataFrame:
        """Pandas Dataframe of changes scraped from HTML shifts & roster endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., CHANGE
            event_type (str):
                Type of change that occurred, e.g., AWAY CHANGE
            description (str | None):
                Description of the event, e.g.,
                PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
                / PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            change_on_count (int):
                Number of players on, e.g., 4
            change_off_count (int):
                Number of players off, e.g., 4
            change_on (str):
                Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_jersey (str):
                Combination of jerseys and numbers for the players on, e.g., NSH14, NSH19, NSH64, NSH95
            change_on_eh_id (str):
                Evolving Hockey IDs of the players on, e.g.,
                MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_on_positions (str):
                Positions of the players on, e.g., D, C, C, C
            change_off (str):
                Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_jersey (str):
                Combination of jerseys and numbers for the players off, e.g., NSH7, NSH9, NSH33, NSH92
            change_off_eh_id (str):
                Evolving Hockey IDs of the players off, e.g.,
                YANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_off_positions (str):
                Positions of the players off, e.g., D, L, L, C
            change_on_forwards_count (int):
                Number of forwards on, e.g.,
            change_off_forwards_count (int):
                Number of forwards off, e.g., 3
            change_on_forwards (str):
                Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards on, e.g., NSH19, NSH64, NSH95
            change_on_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards on, e.g.,
                CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_off_forwards (str):
                Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards off, e.g., NSH9, NSH33, NSH92
            change_off_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards off, e.g.,
                FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_on_defense_count (int):
                Number of defense on, e.g., 1
            change_off_defense_count (int):
                Number of defense off, e.g., 1
            change_on_defense (str):
                Names of defense on, e.g., MATTIAS EKHOLM
            change_on_defense_jersey (str):
                Combination of jerseys and numbers for the defense on, e.g., NSH14
            change_on_defense_eh_id (str):
                Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM
            change_off_defense (str):
                Names of defense off, e.g., YANNICK WEBER
            change_off_defense_jersey (str):
                Combination of jerseys and numbers for the defense off, e.g., NSH7
            change_off_defebse_eh_id (str):
                Evolving Hockey IDs of the defebse off, e.g., YANNICK.WEBER
            change_on_goalie_count (int):
                Number of goalies on, e.g., 0
            change_off_goalie_count (int):
                Number of goalies off, e.g., 0
            change_on_goalies (str):
                Names of goalies on, e.g., None
            change_on_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies on, e.g., None
            change_on_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies on, e.g., None
            change_off_goalies (str):
                Names of goalies off, e.g., None
            change_off_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies off, e.g., None
            change_off_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies off, e.g., None
            is_home (int):
                Dummy indicator whether change team is home, e.g., 0
            is_away (int):
                Dummy indicator whether change team is away, e.g., 1
            team_venue (str):
                Whether team is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.changes
        """
        # TODO: Add API ID columns to documentation

        if not self._changes:
            self._scrape("changes")

        return pd.DataFrame(self._changes)

    @property
    def html_events(self) -> pd.DataFrame:
        """Pandas Dataframe of events scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 331
            period (int):
                Period number of the event, e.g., 3
            period_time (str):
                Time elapsed in the period, e.g., 19:38
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            penalty_length (str | None):
                Duration of the penalty, e.g., None
            penalty (str | None):
                Reason for the penalty, e.g., None
            strength (str | None):
                Code to indication strength state, e.g., EV
            away_skaters (str):
                Away skaters on-ice, e.g., 13C, 19C, 64C, 14D, 59D, 35G
            home_skaters (str):
                Home skaters on-ice, e.g., 19C, 77C, 12R, 88R, 2D, 56D
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.html_events

        """
        if not self._html_events:
            self._scrape("html_events")

        return pd.DataFrame(self._html_events)

    @property
    def html_rosters(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.html_rosters

        """
        if not self._html_rosters:
            self._scrape("html_rosters")

        return pd.DataFrame(self._html_rosters)

    @property
    def play_by_play(self) -> pd.DataFrame:
        """Pandas Dataframe of play-by-play data.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed since previous event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.play_by_play

        """
        # TODO: Add change on / change off API ID columns to documentation

        if self.game_ids != self._scraped_play_by_play:
            self._scrape("play_by_play")

        return pd.DataFrame(self._play_by_play)

    @property
    def play_by_play_ext(self) -> pd.DataFrame:
        """Pandas Dataframe of play-by-play data.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            game_date (str):
                Date game was played, e.g., 2020-01-09
            event_idx (int):
                Index ID for event, e.g., 667
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            strength_state (str):
                Strength state, e.g., 5vE
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            opp_team (str):
                Opposing team, e.g., CHI
            event (str):
                Type of event that occurred, e.g., GOAL
            description (str | None):
                Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., DEF
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            danger (int):
                Whether shot event occurred from danger area, e.g., 0
            high_danger (int):
                Whether shot event occurred from high-danger area, e.g., 0
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_eh_id_api (str):
                Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_eh_id_api (str | None):
                Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None
            player_2_api_id (int | None):
                NHL API ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_eh_id_api (str | None):
                Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None
            player_3_api_id (int | None):
                NHL API ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            score_state (str):
                Score of the game from event team's perspective, e.g., 4v2
            score_diff (int):
                Score differential from event team's perspective, e.g., 2
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed since previous event, e.g., 5
            event_distance (float | None):
                Calculated distance of event from goal, e.g, 185.32673849177834
            pbp_distance (int):
                Distance of event from goal from description, e.g., 185
            event_angle (float | None):
                Angle of event towards goal, e.g., 57.52880770915151
            penalty (str | None):
                Name of penalty, e.g., None
            penalty_length (int | None):
                Duration of penalty, e.g., None
            home_score (int):
                Home team's score, e.g., 2
            home_score_diff (int):
                Home team's score differential, e.g., -2
            away_score (int):
                Away team's score, e.g., 4
            away_score_diff (int):
                Away team's score differential, e.g., 2
            is_home (int):
                Whether event team is home, e.g., 0
            is_away (int):
                Whether event is away, e.g., 1
            home_team (str):
                Home team, e.g., CHI
            away_team (str):
                Away team, e.g., NSH
            home_skaters (int):
                Number of home team skaters on-ice (excl. goalies), e.g., 6
            away_skaters (int):
                Number of away team skaters on-ice (excl. goalies), e.g., 5
            home_on (list | str | None):
                Name of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            home_on_eh_id (list | str | None):
                Evolving Hockey IDs of home team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_on_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            home_on_positions (list | str | None):
                Positions of home team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            away_on (list | str | None):
                Name of away team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            away_on_eh_id (list | str | None):
                Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            away_on_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            away_on_positions (list | str | None):
                Positions of away team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            event_team_skaters (int | None):
                Number of event team skaters on-ice (excl. goalies), e.g., 5
            teammates (list | str | None):
                Name of event team's skaters on-ice (excl. goalies), e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND, MATTIAS EKHOLM, ROMAN JOSI
            teammates_eh_id (list | str | None):
                Evolving Hockey IDs of event team's skaters on-ice (excl. goalies), e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND, MATTIAS.EKHOLM, ROMAN.JOSI
            teammates_api_id (list | str | None = None):
                NHL API IDs of event team's skaters on-ice (excl. goalies), e.g.,
                8474009, 8475714, 8475798, 8475218, 8474600
            teammates_positions (list | str | None):
                Positions of event team's skaters on-ice (excl. goalies), e.g., C, C, C, D, D
            own_goalie (list | str | None):
                Name of the event team's goalie, e.g., PEKKA RINNE
            own_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE
            own_goalie_api_id (list | str | None):
                NHL API ID of the event team's goalie, e.g., 8471469
            forwards (list | str | None):
                Name of event team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            forwards_eh_id (list | str | None):
                Evolving Hockey IDs of event team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            forwards_api_id (list | str | None):
                NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            opp_strength_state (str | None):
                Strength state from opposing team's perspective, e.g., Ev5
            opp_score_state (str | None):
                Score state from opposing team's perspective, e.g., 2v4
            opp_score_diff (int | None):
                Score differential from opposing team's perspective, e.g., -2
            opp_team_skaters (int | None):
                Number of opposing team skaters on-ice (excl. goalies), e.g., 6
            opp_team_on (list | str | None):
                Name of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE, DUNCAN KEITH, ERIK GUSTAFSSON
            opp_team_on_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE, DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_team_on_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice (excl. goalies), e.g.,
                8479337, 8473604, 8481523, 8474141, 8470281, 8476979
            opp_team_on_positions (list | str | None):
                Positions of opposing team's skaters on-ice (excl. goalies), e.g., R, C, C, R, D, D
            opp_goalie (list | str | None):
                Name of the opposing team's goalie, e.g., None
            opp_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the opposing team's goalie, e.g., None
            opp_goalie_api_id (list | str | None):
                NHL API ID of the opposing team's goalie, e.g., None
            opp_forwards (list | str | None):
                Name of opposing team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            opp_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            opp_forwards_api_id (list | str | None):
                NHL API IDs of opposing team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_goalie (list | str | None):
                Name of the home team's goalie, e.g., None
            home_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the home team's goalie, e.g., None
            home_goalie_api_id (list | str | None):
                NHL API ID of the home team's goalie, e.g., None
            away_forwards (list | str | None):
                Name of away team's forwards on-ice, e.g.,
                NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
            away_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of away team's forwards on-ice, e.g.,
                NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
            away_forwards_api_id (list | str | None):
                NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_goalie (list | str | None):
                Name of the away team's goalie, e.g., PEKKA RINNE
            away_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE
            away_goalie_api_id (list | str | None):
                NHL API ID of the away team's goalie, e.g., 8471469
            change_on_count (int | None):
                Number of players on, e.g., None
            change_off_count (int | None):
                Number of players off, e.g., None
            change_on (list | str | None):
                Names of the players on, e.g., None
            change_on_eh_id (list | str | None):
                Evolving Hockey IDs of the players on, e.g., None
            change_on_positions (list | str | None):
                Postions of the players on, e.g., None
            change_off (list | str | None):
                Names of the players off, e.g., None
            change_off_eh_id (list | str | None):
                Evolving Hockey IDs of the players off, e.g., None
            change_off_positions (list | str | None):
                Positions of the players off, e.g., None
            change_on_forwards_count (int | None):
                Number of forwards changing on, e.g., None
            change_off_forwards_count (int | None):
                Number of forwards off, e.g., None
            change_on_forwards (list | str | None):
                Names of the forwards on, e.g., None
            change_on_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards on, e.g., None
            change_off_forwards (list | str | None):
                Names of the forwards off, e.g., None
            change_off_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of the forwards off, e.g., None
            change_on_defense_count (int | None):
                Number of defense on, e.g., None
            change_off_defense_count (int | None):
                Number of defense off, e.g., None
            change_on_defense (list | str | None):
                Names of the defense on, e.g., None
            change_on_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense on, e.g., None
            change_off_defense (list | str | None):
                Names of the defense off, e.g., None
            change_off_defense_eh_id (list | str | None):
                Evolving Hockey IDs of the defense off, e.g., None
            change_on_goalie_count (int | None):
                Number of goalies on, e.g., None
            change_off_goalie_count (int | None):
                Number of goalies off, e.g., None
            change_on_goalie (list | str | None):
                Name of goalie on, e.g., None
            change_on_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie on, e.g., None
            change_off_goalie (list | str | None):
                Name of the goalie off, e.g., None
            change_off_goalie_eh_id (list | str | None):
                Evolving Hockey ID of the goalie off, e.g., None
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            hit (int):
                Dummy indicator whether event is a hit, e.g., 0
            give (int):
                Dummy indicator whether event is a give, e.g., 0
            take (int):
                Dummy indicator whether event is a take, e.g., 0
            fac (int):
                Dummy indicator whether event is a faceoff, e.g., 0
            penl (int):
                Dummy indicator whether event is a penalty, e.g., 0
            change (int):
                Dummy indicator whether event is a change, e.g., 0
            stop (int):
                Dummy indicator whether event is a stop, e.g., 0
            chl (int):
                Dummy indicator whether event is a challenge, e.g., 0
            ozf (int):
                Dummy indicator whether event is a offensive zone faceoff, e.g., 0
            nzf (int):
                Dummy indicator whether event is a neutral zone faceoff, e.g., 0
            dzf (int):
                Dummy indicator whether event is a defensive zone faceoff, e.g., 0
            ozc (int):
                Dummy indicator whether event is a offensive zone change, e.g., 0
            nzc (int):
                Dummy indicator whether event is a neutral zone change, e.g., 0
            dzc (int):
                Dummy indicator whether event is a defensive zone change, e.g., 0
            otf (int):
                Dummy indicator whether event is an on-the-fly change, e.g., 0
            pen0 (int):
                Dummy indicator whether event is a penalty, e.g., 0
            pen2 (int):
                Dummy indicator whether event is a minor penalty, e.g., 0
            pen4 (int):
                Dummy indicator whether event is a double minor penalty, e.g., 0
            pen5 (int):
                Dummy indicator whether event is a major penalty, e.g., 0
            pen10 (int):
                Dummy indicator whether event is a game misconduct penalty, e.g., 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.play_by_play

        """
        # TODO: Update documentation for extended version of play_by_play

        if self.game_ids != self._scraped_play_by_play:
            self._scrape("play_by_play")

        return pd.DataFrame(self._play_by_play_ext)

    @property
    def rosters(self) -> pd.DataFrame:
        """Pandas Dataframe of players scraped from API & HTML endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            api_id (int | None):
                Player's NHL API ID, e.g., 8476887
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE
            headshot_url (str | None):
                URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.rosters

        """
        if not self._rosters:
            self._scrape("rosters")

        return pd.DataFrame(self._rosters)

    @property
    def shifts(self) -> pd.DataFrame:
        """Pandas Dataframe of shifts scraped from HTML endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            jersey (int):
                Player's jersey number, e.g., 9
            shift_count (int):
                Shift number for that player, e.g., 1
            period (int):
                Period number for the shift, e.g., 1
            start_time (str):
                Time shift started, e.g., 0:00
            end_time (str):
                Time shift ended, e.g., 0:18
            duration (str):
                Length of shift, e.g, 00:18
            start_time_seconds (int):
                Time shift started in seconds, e.g., 0
            end_time_seconds (int):
                Time shift ended in seconds, e.g., 18
            duration_seconds (int):
                Length of shift in seconds, e.g., 18
            shift_start (str):
                Time the shift started as the original string, e.g., 0:00 / 20:00
            shift_end (str):
                Time the shift ended as the original string, e.g., 0:18 / 19:42
            goalie (int):
                Whether player is a goalie, e.g., 0
            is_home (int):
                Whether player is home e.g., 0
            is_away (int):
                Whether player is away, e.g., 1
            team_venue (str):
                Whether player is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.shifts

        """
        if not self._shifts:
            self._scrape("shifts")

        return pd.DataFrame(self._shifts)

    def _prep_ind(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of individual stats from play-by-play data.

        Nested within `prep_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            g (int):
                Goals scored, e.g, 0
            ihdg (int):
                High-danger goals scored, e.g, 0
            a1 (int):
                Primary assists, e.g, 0
            a2 (int):
                Secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            isf (int):
                Individual shots taken, e.g, 3
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            ihdf (int):
                High-danger fenwick for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            icf (int):
                Individual corsi for, e.g., 3
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Aggregates individual stats to game level
            >>> scraper._prep_ind(level="game")

            Aggregates individual stats to season level
            >>> scraper._prep_ind(level="season")

            Aggregates individual stats to game level, accounting for teammates on-ice
            >>> scraper._prep_ind(level="game", teammates=True)

        """
        df = self.play_by_play.copy()

        players = ["player_1", "player_2", "player_3"]

        if level == "session" or level == "season":
            merge_list = [
                "season",
                "session",
                "player",
                "eh_id",
                "api_id",
                "position",
                "team",
                "strength_state",
            ]

        if level == "game":
            merge_list = [
                "season",
                "session",
                "player",
                "eh_id",
                "api_id",
                "position",
                "team",
                "strength_state",
                "game_id",
                "game_date",
                "opp_team",
            ]

        if level == "period":
            merge_list = [
                "season",
                "session",
                "player",
                "eh_id",
                "api_id",
                "position",
                "team",
                "strength_state",
                "game_id",
                "game_date",
                "opp_team",
                "period",
            ]

        if score is True:
            merge_list.append("score_state")

        if teammates is True:
            merge_list = merge_list + [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

        if opposition is True:
            merge_list = merge_list + [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_forwards_api_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_defense_api_id",
                "opp_goalie",
                "opp_goalie_eh_id",
                "opp_goalie_api_id",
            ]

            if "opp_team" not in merge_list:
                merge_list.append("opp_team")

        ind_stats = pd.DataFrame(columns=merge_list)

        for player in players:
            player_eh_id = f"{player}_eh_id"
            player_api_id = f"{player}_api_id"
            position = f"{player}_position"

            if level == "session" or level == "season":
                group_base = [
                    "season",
                    "session",
                    "event_team",
                    player,
                    player_eh_id,
                    player_api_id,
                    position,
                ]

            if level == "game":
                group_base = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "event_team",
                    "opp_team",
                    player,
                    player_eh_id,
                    player_api_id,
                    position,
                ]

            if level == "period":
                group_base = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "event_team",
                    "opp_team",
                    "period",
                    player,
                    player_eh_id,
                    player_api_id,
                    position,
                ]

            if opposition is True and "opp_team" not in group_base:
                group_base.append("opp_team")

            mask = df[player] != "BENCH"

            if player == "player_1":
                strength_group = ["strength_state"]
                group_list = group_base + strength_group

                if teammates is True:
                    teammates_group = [
                        "forwards",
                        "forwards_eh_id",
                        "forwards_api_id",
                        "defense",
                        "defense_eh_id",
                        "defense_api_id",
                        "own_goalie",
                        "own_goalie_eh_id",
                        "own_goalie_api_id",
                    ]

                    group_list = group_list + teammates_group

                if score is True:
                    score_group = ["score_state"]
                    group_list = group_list + score_group

                if opposition is True:
                    opposition_group = [
                        "opp_forwards",
                        "opp_forwards_eh_id",
                        "opp_forwards_api_id",
                        "opp_defense",
                        "opp_defense_eh_id",
                        "opp_defense_api_id",
                        "opp_goalie",
                        "opp_goalie_eh_id",
                        "opp_goalie_api_id",
                    ]

                    group_list = group_list + opposition_group

                stats_list = [
                    "block",
                    "fac",
                    "give",
                    "goal",
                    "hd_fenwick",
                    "hd_goal",
                    "hd_miss",
                    "hd_shot",
                    "hit",
                    "miss",
                    "pen0",
                    "pen2",
                    "pen4",
                    "pen5",
                    "pen10",
                    "shot",
                    "take",
                    # "corsi",
                    "fenwick",
                    "pred_goal",
                    "ozf",
                    "nzf",
                    "dzf",
                ]

                stats_dict = {x: "sum" for x in stats_list if x in df.columns}

                new_cols = {
                    "block": "ibs",
                    "fac": "ifow",
                    "give": "igive",
                    "goal": "g",
                    "hd_fenwick": "ihdf",
                    "hd_goal": "ihdg",
                    "hd_miss": "ihdm",
                    "hd_shot": "ihdsf",
                    "hit": "ihf",
                    "miss": "imsf",
                    "pen0": "ipent0",
                    "pen2": "ipent2",
                    "pen4": "ipent4",
                    "pen5": "ipent5",
                    "pen10": "ipent10",
                    "shot": "isf",
                    "take": "itake",
                    "fenwick": "iff",
                    "pred_goal": "ixg",
                    "ozf": "iozfw",
                    "nzf": "inzfw",
                    "dzf": "idzfw",
                    "event_team": "team",
                    player: "player",
                    player_eh_id: "eh_id",
                    player_api_id: "api_id",
                    position: "position",
                }

                mask = np.logical_and.reduce(
                    [
                        df[player] != "BENCH",
                        ~df.description.astype(str).str.contains(
                            "BLOCKED BY TEAMMATE", na=False
                        ),
                    ]
                )

                player_df = (
                    df[mask]
                    .copy()
                    .groupby(group_list, as_index=False)
                    .agg(stats_dict)
                    .rename(columns=new_cols)
                )

                # drop_list = [x for x in stats if x not in new_cols.keys() and x in player_df.columns]

            if player == "player_2":
                # Getting on-ice stats against for player 2

                opp_strength = ["opp_strength_state"]
                event_strength = ["strength_state"]

                opp_group_list = group_base + opp_strength
                event_group_list = group_base + event_strength

                if opposition is False:
                    if level in ["season", "session"]:
                        opp_group_list.remove("event_team")
                        opp_group_list.append("opp_team")

                if teammates is True:
                    opp_teammates = [
                        "opp_forwards",
                        "opp_forwards_eh_id",
                        "opp_forwards_api_id",
                        "opp_defense",
                        "opp_defense_eh_id",
                        "opp_defense_api_id",
                        "opp_goalie",
                        "opp_goalie_eh_id",
                        "opp_goalie_api_id",
                    ]

                    event_teammates = [
                        "forwards",
                        "forwards_eh_id",
                        "forwards_api_id",
                        "defense",
                        "defense_eh_id",
                        "defense_api_id",
                        "own_goalie",
                        "own_goalie_eh_id",
                        "own_goalie_api_id",
                    ]

                    opp_group_list = opp_group_list + opp_teammates
                    event_group_list = event_group_list + event_teammates

                if score is True:
                    opp_score = ["opp_score_state"]
                    event_score = ["score_state"]

                    opp_group_list = opp_group_list + opp_score
                    event_group_list = event_group_list + event_score

                if opposition is True:
                    opp_opposition = [
                        "forwards",
                        "forwards_eh_id",
                        "forwards_api_id",
                        "defense",
                        "defense_eh_id",
                        "defense_api_id",
                        "own_goalie",
                        "own_goalie_eh_id",
                        "own_goalie_api_id",
                    ]

                    event_opposition = [
                        "opp_forwards",
                        "opp_forwards_eh_id",
                        "opp_forwards_api_id",
                        "opp_defense",
                        "opp_defense_eh_id",
                        "opp_defense_api_id",
                        "opp_goalie",
                        "opp_goalie_eh_id",
                        "opp_goalie_api_id",
                    ]

                    opp_group_list = opp_group_list + opp_opposition
                    event_group_list = event_group_list + event_opposition

                stats_1 = [
                    "block",
                    "fac",
                    "hit",
                    "pen0",
                    "pen2",
                    "pen4",
                    "pen5",
                    "pen10",
                    "ozf",
                    "nzf",
                    "dzf",
                ]

                stats_1 = {x: "sum" for x in stats_1 if x.lower() in df.columns}

                new_cols_1 = {
                    "opp_goalie": "own_goalie",
                    "opp_goalie_eh_id": "own_goalie_eh_id",
                    "opp_goalie_api_id": "own_goalie_api_id",
                    "own_goalie": "opp_goalie",
                    "own_goalie_eh_id": "opp_goalie_eh_id",
                    "own_goalie_api_id": "opp_goalie_api_id",
                    "opp_team": "team",
                    "event_team": "opp_team",
                    "opp_score_state": "score_state",
                    "opp_strength_state": "strength_state",
                    "pen0": "ipend0",
                    "pen2": "ipend2",
                    "pen4": "ipend4",
                    "pen5": "ipend5",
                    "pen10": "ipend10",
                    player: "player",
                    player_eh_id: "eh_id",
                    player_api_id: "api_id",
                    position: "position",
                    "fac": "ifol",
                    "hit": "iht",
                    "ozf": "iozfl",
                    "nzf": "inzfl",
                    "dzf": "idzfl",
                    "block": "isb",
                    "opp_forwards": "forwards",
                    "opp_forwards_eh_id": "forwards_eh_id",
                    "opp_forwards_api_id": "forwards_api_id",
                    "opp_defense": "defense",
                    "opp_defense_eh_id": "defense_eh_id",
                    "opp_defense_api_id": "defense_api_id",
                    "forwards": "opp_forwards",
                    "forwards_eh_id": "opp_forwards_eh_id",
                    "forwards_api_id": "opp_forwards_api_id",
                    "defense": "opp_defense",
                    "defense_eh_id": "opp_defense_eh_id",
                    "defense_api_id": "opp_defense_api_id",
                }

                event_types = ["BLOCK", "FAC", "HIT", "PENL"]

                mask_1 = np.logical_and.reduce(
                    [
                        df[player] != "BENCH",
                        df.event.isin(event_types),
                        ~df.description.astype(str).str.contains(
                            "BLOCKED BY TEAMMATE", na=False
                        ),
                    ]
                )

                opps = (
                    df[mask_1]
                    .copy()
                    .groupby(opp_group_list, as_index=False)
                    .agg(stats_1)
                    .rename(columns=new_cols_1)
                )

                # Getting primary assists and primary assists xG from player 2

                stats_2 = ["goal", "pred_goal", "teammate_block"]

                stats_2 = {x: "sum" for x in stats_2 if x in df.columns}

                new_cols_2 = {
                    "event_team": "team",
                    player: "player",
                    player_eh_id: "eh_id",
                    player_api_id: "api_id",
                    "goal": "a1",
                    "pred_goal": "a1_xg",
                    position: "position",
                    "teammate_block": "isb",
                }

                event_types = ["BLOCK", "GOAL"]

                mask_2 = np.logical_and.reduce(
                    [df[player] != "BENCH", df.event.isin(event_types)]
                )

                own = (
                    df[mask_2]
                    .copy()
                    .groupby(event_group_list, as_index=False)
                    .agg(stats_2)
                    .rename(columns=new_cols_2)
                )

                player_df = opps.merge(
                    own, left_on=merge_list, right_on=merge_list, how="outer"
                ).fillna(0)

                player_df["isb"] = player_df.isb_x + player_df.isb_y

            if player == "player_3":
                group_list = group_base + strength_group

                if teammates is True:
                    group_list = group_list + teammates_group

                if score is True:
                    group_list = group_list + score_group

                if opposition is True:
                    group_list = group_list + opposition_group

                    if "opp_team" not in group_list:
                        group_list.append("opp_team")

                stats_list = ["goal", "pred_goal"]

                stats_dict = {x: "sum" for x in stats_list if x in df.columns}

                player_df = df[mask].groupby(group_list, as_index=False).agg(stats_dict)

                new_cols = {
                    "goal": "a2",
                    "pred_goal": "a2_xg",
                    "event_team": "team",
                    player: "player",
                    player_eh_id: "eh_id",
                    player_api_id: "api_id",
                    position: "position",
                }

                player_df = player_df.rename(columns=new_cols)

            ind_stats = (
                ind_stats.merge(player_df, on=merge_list, how="outer")
                .infer_objects(copy=False)
                .fillna(0)
            )

        # Fixing some stats

        ind_stats["icf"] = ind_stats.iff + ind_stats.isb

        ind_stats["gax"] = ind_stats.g - ind_stats.ixg

        columns = [
            x for x in list(IndStatSchema.dtypes.keys()) if x in ind_stats.columns
        ]

        ind_stats = ind_stats[columns]

        stats = [
            "g",
            "a1",
            "a2",
            "isf",
            "iff",
            "icf",
            "ixg",
            "gax",
            "ihdg",
            "ihdf",
            "ihdsf",
            "ihdm",
            "imsf",
            "isb",
            "ibs",
            "igive",
            "itake",
            "ihf",
            "iht",
            "ifow",
            "ifol",
            "iozfw",
            "iozfl",
            "inzfw",
            "inzfl",
            "idzfw",
            "idzfl",
            "a1_xg",
            "a2_xg",
            "ipent0",
            "ipent2",
            "ipent4",
            "ipent5",
            "ipent10",
            "ipend0",
            "ipend2",
            "ipend4",
            "ipend5",
            "ipend10",
        ]

        stats = [x for x in stats if x in ind_stats.columns]

        ind_stats = ind_stats.loc[(ind_stats[stats] > 0).any(axis=1)]

        ind_stats = IndStatSchema.validate(ind_stats)

        self._ind_stats = ind_stats

    @property
    def ind_stats(self) -> pd.DataFrame:
        """Pandas Dataframe of individual stats aggregated from play-by-play data.

        Nested within `prep_stats` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            g (int):
                Goals scored, e.g, 0
            ihdg (int):
                High-danger goals scored, e.g, 0
            a1 (int):
                Primary assists, e.g, 0
            a2 (int):
                Secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            isf (int):
                Individual shots taken, e.g, 3
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            ihdf (int):
                High-danger fenwick for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            icf (int):
                Individual corsi for, e.g., 3
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.ind_stats

        """
        if self._ind_stats.empty:
            self._prep_ind()

        return self._ind_stats

    def _prep_oi(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of on-ice stats from play-by-play data.

        Nested within `prep_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares on-ice dataframe with default options
            >>> scraper._prep_oi()

            On-ice statistics, aggregated to season level
            >>> scraper._prep_oi(level="season")

            On-ice statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_oi(level="game", teammates=True)

        """
        merge_cols = ["id", "event_idx"]

        df = self.play_by_play.merge(self.play_by_play_ext, how="left", on=merge_cols)

        players = (
            [f"event_on_{x}" for x in range(1, 8)]
            + [f"opp_on_{x}" for x in range(1, 8)]
            + [f"change_on_{x}" for x in range(1, 8)]
        )

        event_list = []
        opp_list = []
        zones_list = []

        for player in players:
            position = f"{player}_pos"
            player_eh_id = f"{player}_eh_id"
            player_api_id = f"{player}_api_id"

            if level == "session" or level == "season":
                group_list = ["season", "session"]

            if level == "game":
                group_list = [
                    "season",
                    "session",
                    "game_id",
                    "game_date",
                    "event_team",
                    "opp_team",
                ]

            if level == "period":
                group_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "event_team",
                    "opp_team",
                    "period",
                ]

            # Accounting for desired player

            if "event_on" in player or "opp_on" in player:
                stats_list = [
                    "block",
                    "teammate_block",
                    "fac",
                    "goal",
                    "goal_adj",
                    "hd_fenwick",
                    "hd_goal",
                    "hd_miss",
                    "hd_shot",
                    "hit",
                    "miss",
                    "pen0",
                    "pen2",
                    "pen4",
                    "pen5",
                    "pen10",
                    "shot",
                    "shot_adj",
                    "fenwick",
                    "fenwick_adj",
                    "pred_goal",
                    "pred_goal_adj",
                    "ozf",
                    "nzf",
                    "dzf",
                    "event_length",
                ]

            if "change_on" in player:
                stats_list = ["ozc", "nzc", "dzc", "otf"]

            stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            if "event_on" in player or "change_on" in player:
                if level == "session" or level == "season":
                    group_list.append("event_team")

                strength_group = ["strength_state"]

                teammates_group = [
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                    "own_goalie_api_id",
                ]

                score_group = ["score_state"]

                opposition_group = [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_forwards_api_id",
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_defense_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]

                if "opp_team" not in group_list:
                    opposition_group.insert(0, "opp_team")

                col_names = {
                    "event_team": "team",
                    player: "player",
                    player_eh_id: "eh_id",
                    player_api_id: "api_id",
                    position: "position",
                    "goal": "gf",
                    "goal_adj": "gf_adj",
                    "hit": "hf",
                    "miss": "msf",
                    "block": "bsa",
                    "teammate_block": "bsf",
                    "pen0": "pent0",
                    "pen2": "pent2",
                    "pen4": "pent4",
                    "pen5": "pent5",
                    "pen10": "pent10",
                    "fenwick": "ff",
                    "fenwick_adj": "ff_adj",
                    "pred_goal": "xgf",
                    "pred_goal_adj": "xgf_adj",
                    "fac": "fow",
                    "ozf": "ozfw",
                    "dzf": "dzfw",
                    "nzf": "nzfw",
                    "ozc": "ozs",
                    "nzc": "nzs",
                    "dzc": "dzs",
                    "shot": "sf",
                    "shot_adj": "sf_adj",
                    "hd_goal": "hdgf",
                    "hd_shot": "hdsf",
                    "hd_fenwick": "hdff",
                    "hd_miss": "hdmsf",
                }

            if "opp_on" in player:
                if level == "session" or level == "season":
                    group_list.append("opp_team")

                strength_group = ["opp_strength_state"]

                teammates_group = [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_forwards_api_id",
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_defense_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]

                score_group = ["opp_score_state"]

                opposition_group = [
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                    "own_goalie_api_id",
                ]

                if "event_team" not in group_list:
                    opposition_group.insert(0, "event_team")

                col_names = {
                    "opp_team": "team",
                    "event_team": "opp_team",
                    "opp_goalie": "own_goalie",
                    "own_goalie": "opp_goalie",
                    "opp_score_state": "score_state",
                    "opp_strength_state": "strength_state",
                    player: "player",
                    player_eh_id: "eh_id",
                    player_api_id: "api_id",
                    position: "position",
                    "block": "bsf",
                    "goal": "ga",
                    "goal_adj": "ga_adj",
                    "hit": "ht",
                    "miss": "msa",
                    "pen0": "pend0",
                    "pen2": "pend2",
                    "pen4": "pend4",
                    "pen5": "pend5",
                    "pen10": "pend10",
                    "shot": "sa",
                    "shot_adj": "sa_adj",
                    "fenwick": "fa",
                    "fenwick_adj": "fa_adj",
                    "pred_goal": "xga",
                    "pred_goal_adj": "xga_adj",
                    "fac": "fol",
                    "ozf": "dzfl",
                    "dzf": "ozfl",
                    "nzf": "nzfl",
                    "hd_goal": "hdga",
                    "hd_shot": "hdsa",
                    "hd_fenwick": "hdfa",
                    "hd_miss": "hdmsa",
                    "forwards": "opp_forwards",
                    "forwards_eh_id": "opp_forwards_eh_id",
                    "forwards_api_id": "opp_forwards_api_id",
                    "defense": "opp_defense",
                    "defense_eh_id": "opp_defense_eh_id",
                    "defense_api_id": "opp_defense_api_id",
                    "own_goalie_eh_id": "opp_goalie_eh_id",
                    "own_goalie_api_id": "opp_goalie_api_id",
                    "opp_forwards": "forwards",
                    "opp_forwards_eh_id": "forwards_eh_id",
                    "opp_forwards_api_id": "forwards_api_id",
                    "opp_defense": "defense",
                    "opp_defense_eh_id": "defense_eh_id",
                    "opp_defense_api_id": "defense_api_id",
                    "opp_goalie_eh_id": "own_goalie_eh_id",
                    "opp_goalie_api_id": "own_goalie_api_id",
                }

            group_list = (
                group_list
                + [player, player_eh_id, player_api_id, position]
                + strength_group
            )

            if teammates is True:
                group_list = group_list + teammates_group

            if score is True:
                group_list = group_list + score_group

            if opposition is True:
                group_list = group_list + opposition_group

            player_df = df.groupby(group_list, dropna=False, as_index=False).agg(
                stats_dict
            )

            col_names = {
                key: value
                for key, value in col_names.items()
                if key in player_df.columns
            }

            player_df = player_df.rename(columns=col_names)

            if "event_on" in player:
                event_list.append(player_df)

            elif "opp_on" in player:
                opp_list.append(player_df)

            elif "change_on" in player:
                zones_list.append(player_df)

        # On-ice stats

        merge_cols = [
            "season",
            "session",
            "game_id",
            "game_date",
            "team",
            "opp_team",
            "player",
            "eh_id",
            "api_id",
            "position",
            "period",
            "strength_state",
            "score_state",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
        ]

        event_stats = pd.concat(event_list, ignore_index=True)

        stats_dict = {x: "sum" for x in event_stats.columns if x not in merge_cols}

        group_list = [x for x in merge_cols if x in event_stats.columns]

        event_stats = event_stats.groupby(group_list, as_index=False).agg(stats_dict)

        opp_stats = pd.concat(opp_list, ignore_index=True)

        stats_dict = {x: "sum" for x in opp_stats.columns if x not in merge_cols}

        group_list = [x for x in merge_cols if x in opp_stats.columns]

        opp_stats = opp_stats.groupby(group_list, as_index=False).agg(stats_dict)

        zones_stats = pd.concat(zones_list, ignore_index=True)

        stats_dict = {x: "sum" for x in zones_stats.columns if x not in merge_cols}

        group_list = [x for x in merge_cols if x in zones_stats.columns]

        zones_stats = zones_stats.groupby(group_list, as_index=False).agg(stats_dict)

        merge_cols = [
            x
            for x in merge_cols
            if x in event_stats.columns
            and x in opp_stats.columns
            and x in zones_stats.columns
        ]

        oi_stats = event_stats.merge(opp_stats, on=merge_cols, how="outer").fillna(0)

        oi_stats = oi_stats.merge(zones_stats, on=merge_cols, how="outer").fillna(0)

        oi_stats["toi"] = (oi_stats.event_length_x + oi_stats.event_length_y) / 60

        oi_stats["bsf"] = oi_stats.bsf_x + oi_stats.bsf_y

        oi_stats["cf"] = oi_stats.sf + oi_stats.msf + oi_stats.bsf
        oi_stats["ca"] = (
            oi_stats.sa + oi_stats.msa + oi_stats.bsa + oi_stats.teammate_block
        )

        fo_list = ["ozf", "dzf", "nzf"]

        for fo in fo_list:
            oi_stats[fo] = oi_stats[f"{fo}w"] + oi_stats[f"{fo}l"]

        oi_stats["fac"] = oi_stats.ozf + oi_stats.nzf + oi_stats.dzf

        columns = [x for x in list(OIStatSchema.dtypes.keys()) if x in oi_stats.columns]

        oi_stats = oi_stats[columns]

        stats = [
            "toi",
            "gf",
            "gf_adj",
            "hdgf",
            "sf",
            "sf_adj",
            "hdsf",
            "ff",
            "ff_adj",
            "hdff",
            "cf",
            "cf_adj",
            "xgf",
            "xgf_adj",
            "bsf",
            "msf",
            "hdmsf",
            "ga",
            "ga_adj",
            "hdga",
            "sa",
            "sa_adj",
            "hdsa",
            "fa",
            "fa_adj",
            "hdfa",
            "ca",
            "ca_adj",
            "xga",
            "xga_adj",
            "bsa",
            "msa",
            "hdmsa",
            "hf",
            "ht",
            "ozf",
            "nzf",
            "dzf",
            "fow",
            "fol",
            "ozfw",
            "ozfl",
            "nzfw",
            "nzfl",
            "dzfw",
            "dzfl",
            "pent0",
            "pent2",
            "pent4",
            "pent5",
            "pent10",
            "pend0",
            "pend2",
            "pend4",
            "pend5",
            "pend10",
        ]

        stats = [x.lower() for x in stats if x.lower() in oi_stats.columns]

        oi_stats = oi_stats.loc[(oi_stats[stats] != 0).any(axis=1)]

        oi_stats = OIStatSchema.validate(oi_stats)

        self._oi_stats = oi_stats

    @property
    def oi_stats(self) -> pd.DataFrame:
        """Pandas Dataframe of on-ice stats aggregated from play-by-play data.

        Nested within `prep_stats` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.ind_stats

        """
        if self._oi_stats.empty:
            self._prep_oi()

        return self._oi_stats

    def _prep_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of individual and on-ice stats from play-by-play data.

        Nested within `prep_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            g (int):
                Goals scored, e.g, 0
            ihdg (int):
                High-danger goals scored, e.g, 0
            a1 (int):
                Primary assists, e.g, 0
            a2 (int):
                Secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            isf (int):
                Individual shots taken, e.g, 3
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            ihdf (int):
                High-danger fenwick for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            icf (int):
                Individual corsi for, e.g., 3
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0
            g_p60 (float):
                Goals scored per 60 minutes
            ihdg_p60 (float):
                Individual high-danger goals scored per 60
            a1_p60 (float):
                Primary assists per 60 minutes
            a2_p60 (float):
                Secondary per 60 minutes
            ixg_p60 (float):
                Individual xG for per 60 minutes
            isf_p60 (float):
                Individual shots for per 60 minutes
            ihdsf_p60 (float):
                Individual high-danger shots for per 60 minutes
            imsf_p60 (float):
                Individual missed shorts for per 60 minutes
            ihdm_p60 (float):
                Individual high-danger missed shots for per 60 minutes
            iff_p60 (float):
                Individual fenwick for per 60 minutes
            ihdff_p60 (float):
                Individual high-danger fenwick for per 60 minutes
            isb_p60 (float):
                Individual shots blocked (for) per 60 minutes
            icf_p60 (float):
                Individual corsi for per 60 minutes
            ibs_p60 (float):
                Individual blocked shots (against) per 60 minutes
            igive_p60 (float):
                Individual giveaways per 60 minutes
            itake_p60 (float):
                Individual takeaways per 60 minutes
            ihf_p60 (float):
                Individual hits for per 60 minutes
            iht_p60 (float):
                Individual hits taken per 60 minutes
            a1_xg_p60 (float):
                Individual primary assists' xG per 60 minutes
            a2_xg_p60 (float):
                Individual secondary assists' xG per 60 minutes
            ipent0_p60 (float):
                Individual penalty shots taken per 60 minutes
            ipent2_p60 (float):
                Individual minor penalties taken per 60 minutes
            ipent4_p60 (float):
                Individual double minor penalties taken per 60 minutes
            ipent5_p60 (float):
                Individual major penalties taken per 60 minutes
            ipent10_p60 (float):
                Individual game misconduct pentalties taken per 60 minutes
            ipend0_p60 (float):
                Individual penalty shots drawn per 60 minutes
            ipend2_p60 (float):
                Individual minor penalties drawn per 60 minutes
            ipend4_p60 (float):
                Individual double minor penalties drawn per 60 minutes
            ipend5_p60 (float):
                Individual major penalties drawn per 60 minutes
            ipend10_p60 (float):
                Individual game misconduct penalties drawn per 60 minutes
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares individual and on-ice dataframe with default options
            >>> scraper._prep_stats()

            Individual and on-ice statistics, aggregated to season level
            >>> scraper._prep_stats(level="season")

            Individual and on-ice statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_stats(level="game", teammates=True)

        """
        if self._ind_stats.empty:
            self._prep_ind(
                level=level, score=score, teammates=teammates, opposition=opposition
            )

        if self._oi_stats.empty:
            self._prep_oi(
                level=level, score=score, teammates=teammates, opposition=opposition
            )

        merge_cols = [
            "season",
            "session",
            "game_id",
            "game_date",
            "player",
            "eh_id",
            "api_id",
            "position",
            "team",
            "opp_team",
            "strength_state",
            "score_state",
            "period",
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]

        merge_cols = [
            x
            for x in merge_cols
            if x in self._ind_stats.columns and x in self._oi_stats.columns
            # and x in self._zones.columns
        ]

        stats = self._oi_stats.merge(
            self._ind_stats, how="left", left_on=merge_cols, right_on=merge_cols
        ).fillna(0)

        stats = stats.loc[stats.toi > 0].reset_index(drop=True).copy()

        columns = [x for x in list(StatSchema.dtypes.keys()) if x in stats.columns]

        stats = stats[columns]

        stats = prep_p60(stats)

        stats = prep_oi_percent(stats)

        stats = StatSchema.validate(stats)

        self._stats = stats

    def prep_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
    ) -> None:
        """Prepares DataFrame of individual and on-ice stats from play-by-play data.

        Used to prepare, or reset prepared data for later analysis

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice
            disable_progress_bar (bool):
                Determines whether to display the progress bar

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            g (int):
                Goals scored, e.g, 0
            ihdg (int):
                High-danger goals scored, e.g, 0
            a1 (int):
                Primary assists, e.g, 0
            a2 (int):
                Secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            isf (int):
                Individual shots taken, e.g, 3
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            ihdf (int):
                High-danger fenwick for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            icf (int):
                Individual corsi for, e.g., 3
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0
            g_p60 (float):
                Goals scored per 60 minutes
            ihdg_p60 (float):
                Individual high-danger goals scored per 60
            a1_p60 (float):
                Primary assists per 60 minutes
            a2_p60 (float):
                Secondary per 60 minutes
            ixg_p60 (float):
                Individual xG for per 60 minutes
            isf_p60 (float):
                Individual shots for per 60 minutes
            ihdsf_p60 (float):
                Individual high-danger shots for per 60 minutes
            imsf_p60 (float):
                Individual missed shorts for per 60 minutes
            ihdm_p60 (float):
                Individual high-danger missed shots for per 60 minutes
            iff_p60 (float):
                Individual fenwick for per 60 minutes
            ihdff_p60 (float):
                Individual high-danger fenwick for per 60 minutes
            isb_p60 (float):
                Individual shots blocked (for) per 60 minutes
            icf_p60 (float):
                Individual corsi for per 60 minutes
            ibs_p60 (float):
                Individual blocked shots (against) per 60 minutes
            igive_p60 (float):
                Individual giveaways per 60 minutes
            itake_p60 (float):
                Individual takeaways per 60 minutes
            ihf_p60 (float):
                Individual hits for per 60 minutes
            iht_p60 (float):
                Individual hits taken per 60 minutes
            a1_xg_p60 (float):
                Individual primary assists' xG per 60 minutes
            a2_xg_p60 (float):
                Individual secondary assists' xG per 60 minutes
            ipent0_p60 (float):
                Individual penalty shots taken per 60 minutes
            ipent2_p60 (float):
                Individual minor penalties taken per 60 minutes
            ipent4_p60 (float):
                Individual double minor penalties taken per 60 minutes
            ipent5_p60 (float):
                Individual major penalties taken per 60 minutes
            ipent10_p60 (float):
                Individual game misconduct pentalties taken per 60 minutes
            ipend0_p60 (float):
                Individual penalty shots drawn per 60 minutes
            ipend2_p60 (float):
                Individual minor penalties drawn per 60 minutes
            ipend4_p60 (float):
                Individual double minor penalties drawn per 60 minutes
            ipend5_p60 (float):
                Individual major penalties drawn per 60 minutes
            ipend10_p60 (float):
                Individual game misconduct penalties drawn per 60 minutes
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares individual and on-ice dataframe with default options
            >>> scraper.prep_stats()

            Individual and on-ice statistics, aggregated to season level
            >>> scraper.prep_stats(level="season")

            Individual and on-ice statistics, aggregated to game level, accounting for teammates
            >>> scraper.prep_stats(level="game", teammates=True)

        """
        levels = self._stats_levels

        if (
            levels["level"] != level
            or levels["score"] != score
            or levels["teammates"] != teammates
            or levels["opposition"] != opposition
        ):
            self._clear_stats()

            new_values = {
                "level": level,
                "score": score,
                "teammates": teammates,
                "opposition": opposition,
            }

            self._stats_levels.update(new_values)

        if self._stats.empty:
            with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
                pbar_message = f"Prepping stats data..."
                progress_task = progress.add_task(
                    pbar_message, total=None, refresh=True
                )

                progress.start_task(progress_task)
                progress.update(
                    progress_task, total=1, description=pbar_message, refresh=True
                )

                self._prep_stats(
                    level=level, score=score, teammates=teammates, opposition=opposition
                )

                progress.update(
                    progress_task,
                    description="Finished prepping stats data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )

    @property
    def stats(self) -> pd.DataFrame:
        """Pandas Dataframe of individual & on-ice stats aggregated from play-by-play data.

        Determine level of aggregation using prep_stats method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            player (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            position (str):
                Player's position, e.g., L
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            g (int):
                Goals scored, e.g, 0
            ihdg (int):
                High-danger goals scored, e.g, 0
            a1 (int):
                Primary assists, e.g, 0
            a2 (int):
                Secondary assists, e.g, 0
            ixg (float):
                Individual xG for, e.g, 1.014336
            isf (int):
                Individual shots taken, e.g, 3
            ihdsf (int):
                High-danger shots taken, e.g, 3
            imsf (int):
                Individual missed shots, e.g, 0
            ihdm (int):
                High-danger missed shots, e.g, 0
            iff (int):
                Individual fenwick for, e.g., 3
            ihdf (int):
                High-danger fenwick for, e.g., 3
            isb (int):
                Shots taken that were blocked, e.g, 0
            icf (int):
                Individual corsi for, e.g., 3
            ibs (int):
                Individual shots blocked on defense, e.g, 0
            igive (int):
                Individual giveaways, e.g, 0
            itake (int):
                Individual takeaways, e.g, 0
            ihf (int):
                Individual hits for, e.g, 0
            iht (int):
                Individual hits taken, e.g, 0
            ifow (int):
                Individual faceoffs won, e.g, 0
            ifol (int):
                Individual faceoffs lost, e.g, 0
            iozfw (int):
                Individual faceoffs won in offensive zone, e.g, 0
            iozfl (int):
                Individual faceoffs lost in offensive zone, e.g, 0
            inzfw (int):
                Individual faceoffs won in neutral zone, e.g, 0
            inzfl (int):
                Individual faceoffs lost in neutral zone, e.g, 0
            idzfw (int):
                Individual faceoffs won in defensive zone, e.g, 0
            idzfl (int):
                Individual faceoffs lost in defensive zone, e.g, 0
            a1_xg (float):
                xG on primary assists, e.g, 0
            a2_xg (float):
                xG on secondary assists, e.g, 0
            ipent0 (int):
                Individual penalty shots against, e.g, 0
            ipent2 (int):
                Individual minor penalties taken, e.g, 0
            ipent4 (int):
                Individual double minor penalties taken, e.g, 0
            ipent5 (int):
                Individual major penalties taken, e.g, 0
            ipent10 (int):
                Individual game misconduct penalties taken, e.g, 0
            ipend0 (int):
                Individual penalty shots drawn, e.g, 0
            ipend2 (int):
                Individual minor penalties taken, e.g, 0
            ipend4 (int):
                Individual double minor penalties drawn, e.g, 0
            ipend5 (int):
                Individual major penalties drawn, e.g, 0
            ipend10 (int):
                Individual game misconduct penalties drawn, e.g, 0
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            ozs (int):
                Offensive zone starts, e.g, 0
            nzs (int):
                Neutral zone starts, e.g, 0
            dzs (int):
                Defenzive zone starts, e.g, 0
            otf (int):
                On-the-fly starts, e.g, 0
            g_p60 (float):
                Goals scored per 60 minutes
            ihdg_p60 (float):
                Individual high-danger goals scored per 60
            a1_p60 (float):
                Primary assists per 60 minutes
            a2_p60 (float):
                Secondary per 60 minutes
            ixg_p60 (float):
                Individual xG for per 60 minutes
            isf_p60 (float):
                Individual shots for per 60 minutes
            ihdsf_p60 (float):
                Individual high-danger shots for per 60 minutes
            imsf_p60 (float):
                Individual missed shorts for per 60 minutes
            ihdm_p60 (float):
                Individual high-danger missed shots for per 60 minutes
            iff_p60 (float):
                Individual fenwick for per 60 minutes
            ihdff_p60 (float):
                Individual high-danger fenwick for per 60 minutes
            isb_p60 (float):
                Individual shots blocked (for) per 60 minutes
            icf_p60 (float):
                Individual corsi for per 60 minutes
            ibs_p60 (float):
                Individual blocked shots (against) per 60 minutes
            igive_p60 (float):
                Individual giveaways per 60 minutes
            itake_p60 (float):
                Individual takeaways per 60 minutes
            ihf_p60 (float):
                Individual hits for per 60 minutes
            iht_p60 (float):
                Individual hits taken per 60 minutes
            a1_xg_p60 (float):
                Individual primary assists' xG per 60 minutes
            a2_xg_p60 (float):
                Individual secondary assists' xG per 60 minutes
            ipent0_p60 (float):
                Individual penalty shots taken per 60 minutes
            ipent2_p60 (float):
                Individual minor penalties taken per 60 minutes
            ipent4_p60 (float):
                Individual double minor penalties taken per 60 minutes
            ipent5_p60 (float):
                Individual major penalties taken per 60 minutes
            ipent10_p60 (float):
                Individual game misconduct pentalties taken per 60 minutes
            ipend0_p60 (float):
                Individual penalty shots drawn per 60 minutes
            ipend2_p60 (float):
                Individual minor penalties drawn per 60 minutes
            ipend4_p60 (float):
                Individual double minor penalties drawn per 60 minutes
            ipend5_p60 (float):
                Individual major penalties drawn per 60 minutes
            ipend10_p60 (float):
                Individual game misconduct penalties drawn per 60 minutes
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Returns individual and on-ice stats with default options
            >>> scraper.stats

            Resets individual and on-ice stats to period level, accounting for teammates on-ice
            >>> scraper.prep_stats(level="period", teammates=True)
            >>> scraper.stats

            Resets individual and on-ice stats to season level, accounting for teammates on-ice and score state
            >>> scraper.prep_stats(level="season", teammates=True, score=True)
            >>> scraper.stats

        """
        if self._stats.empty:
            self.prep_stats()

        return self._stats

    def _clear_stats(self):
        """Method to clear stats dataframes. Nested within `prep_stats` method."""
        self._stats = pd.DataFrame()
        self._oi_stats = pd.DataFrame()
        self._ind_stats = pd.DataFrame()

    def _prep_lines(
        self,
        position: Literal["F", "D"] = "F",
        level: Literal["period", "game", "session", "season"] = "game",
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
    ) -> None:
        """Prepares DataFrame of line-level stats from play-by-play data.

        Nested within `prep_lines` method.

        Parameters:
            position (str):
                Determines what positions to aggregate. One of F or D
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares on-ice, line-level dataframe with default options
            >>> scraper._prep_lines()

            Line-level statistics, aggregated to season level
            >>> scraper._prep_lines(level="season")

            Line-level statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_lines(level="game", teammates=True)

        """
        merge_cols = ["id", "event_idx"]

        data = self.play_by_play.merge(self.play_by_play_ext, how="left", on=merge_cols)

        # Creating the "for" dataframe

        # Accounting for desired level of aggregation

        if level == "session" or level == "season":
            group_base = ["season", "session", "event_team", "strength_state"]

        if level == "game":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "strength_state",
            ]

        if level == "period":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "period",
                "strength_state",
            ]

        # Accounting for score state

        if score:
            group_base = group_base + ["score_state"]

        # Accounting for desired position

        if position == "F":
            group_list = group_base + ["forwards", "forwards_eh_id", "forwards_api_id"]

        if position == "D":
            group_list = group_base + ["defense", "defense_eh_id", "defense_api_id"]

        # Accounting for teammates

        if teammates is True:
            if position == "F":
                group_list = group_list + [
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                    "own_goalie_api_id",
                ]

            if position == "D":
                group_list = group_list + [
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                    "own_goalie_api_id",
                ]

        # Accounting for opposition

        if opposition is True:
            group_list = group_list + [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_forwards_api_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_defense_api_id",
                "opp_goalie",
                "opp_goalie_eh_id",
                "opp_goalie_api_id",
            ]

            if "opp_team" not in group_list:
                group_list.append("opp_team")

        # Creating dictionary of statistics for the groupby function

        stats = [
            "pred_goal",
            "pred_goal_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "miss",
            "block",
            "teammate_block",
            "shot",
            "shot_adj",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "event_length",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "hit",
            "give",
            "take",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
        ]

        agg_stats = {x: "sum" for x in stats if x in data.columns}

        # Aggregating the "for" dataframe

        lines_f = data.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

        # Creating the dictionary to change column names

        columns = [
            "xgf",
            "xgf_adj",
            "ff",
            "ff_adj",
            "gf",
            "gf_adj",
            "msf",
            "bsf",
            "teammate_block",
            "sf",
            "sf_adj",
            "hdgf",
            "hdsf",
            "hdff",
            "hdmsf",
            "toi",
            "fow",
            "ozfw",
            "nzfw",
            "dzfw",
            "hf",
            "give",
            "take",
            "pent0",
            "pent2",
            "pent4",
            "pent5",
            "pent10",
        ]

        columns = dict(zip(stats, columns))

        # Accounting for positions

        columns.update({"event_team": "team"})

        # columns = {k: v for k, v in columns.items() if k in lines_f.columns}

        lines_f = lines_f.rename(columns=columns)

        cols = [
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]

        cols = [x for x in cols if x in lines_f]

        for col in cols:
            lines_f[col] = lines_f[col].fillna("EMPTY")

        # Creating the against dataframe

        # Accounting for desired level of aggregation

        if level == "session" or level == "season":
            group_base = ["season", "session", "opp_team", "opp_strength_state"]

        if level == "game":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "opp_strength_state",
            ]

        if level == "period":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "period",
                "opp_strength_state",
            ]

        # Accounting for score state

        if score is True:
            group_base = group_base + ["opp_score_state"]

        # Accounting for desired position

        if position == "F":
            group_list = group_base + [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_forwards_api_id",
            ]

        if position == "D":
            group_list = group_base + [
                "opp_defense",
                "opp_defense_eh_id",
                "opp_defense_api_id",
            ]

        # Accounting for teammates

        if teammates is True:
            if position == "F":
                group_list = group_list + [
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_defense_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]

            if position == "D":
                group_list = group_list + [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_forwards_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]

        # Accounting for opposition

        if opposition is True:
            group_list = group_list + [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

            if "event_team" not in group_list:
                group_list.append("event_team")

        # Creating dictionary of statistics for the groupby function

        stats = [
            "pred_goal",
            "pred_goal_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "miss",
            "block",
            "shot",
            "shot_adj",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "event_length",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "hit",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
        ]

        agg_stats = {x: "sum" for x in stats if x in data.columns}

        # Aggregating "against" dataframe

        lines_a = data.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

        # Creating the dictionary to change column names

        columns = [
            "xga",
            "xga_adj",
            "fa",
            "fa_adj",
            "ga",
            "ga_adj",
            "msa",
            "bsa",
            "sa",
            "sa_adj",
            "hdga",
            "hdsa",
            "hdfa",
            "hdmsa",
            "toi",
            "fol",
            "ozfl",
            "nzfl",
            "dzfl",
            "ht",
            "pend0",
            "pend2",
            "pend4",
            "pend5",
            "pend10",
        ]

        columns = dict(zip(stats, columns))

        # Accounting for positions

        columns.update(
            {
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_forwards_api_id": "forwards_api_id",
                "opp_strength_state": "strength_state",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_defense_api_id": "defense_api_id",
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "forwards_api_id": "opp_forwards_api_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "defense_api_id": "opp_defense_api_id",
                "opp_score_state": "score_state",
                "own_goalie": "opp_goalie",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
                "opp_goalie": "own_goalie",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
            }
        )

        # columns = {k: v for k, v in columns.items() if k in lines_a.columns}

        lines_a = lines_a.rename(columns=columns)

        cols = [
            "forwards",
            "forwards_eh_id",
            "forwards_api_id",
            "defense",
            "defense_eh_id",
            "defense_api_id",
            "own_goalie",
            "own_goalie_eh_id",
            "own_goalie_api_id",
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]

        cols = [x for x in cols if x in lines_a]

        for col in cols:
            lines_a[col] = lines_a[col].fillna("EMPTY")

        # Merging the "for" and "against" dataframes

        if level == "session" or level == "season":
            if position == "F":
                merge_list = [
                    "season",
                    "session",
                    "team",
                    "strength_state",
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                ]

            if position == "D":
                merge_list = [
                    "season",
                    "session",
                    "team",
                    "strength_state",
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                ]

        if level == "game":
            if position == "F":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                ]

            if position == "D":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                ]

        if level == "period":
            if position == "F":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                    "period",
                ]

            if position == "D":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                    "period",
                ]

        if score is True:
            merge_list.append("score_state")

        if teammates is True:
            if position == "F":
                merge_list = merge_list + [
                    "defense",
                    "defense_eh_id",
                    "defense_api_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                    "own_goalie_api_id",
                ]

            if position == "D":
                merge_list = merge_list + [
                    "forwards",
                    "forwards_eh_id",
                    "forwards_api_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                    "own_goalie_api_id",
                ]

        if opposition is True:
            merge_list = merge_list + [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_forwards_api_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_defense_api_id",
                "opp_goalie",
                "opp_goalie_eh_id",
                "opp_goalie_api_id",
            ]

            if "opp_team" not in merge_list:
                merge_list.insert(3, "opp_team")

        lines = lines_f.merge(
            lines_a, how="outer", on=merge_list, suffixes=("_x", "_y")
        ).fillna(0)

        lines["toi"] = (lines.toi_x + lines.toi_y) / 60

        lines["cf"] = lines.bsf + lines.teammate_block + lines.ff

        lines["ozf"] = lines.ozfw + lines.ozfl

        lines["nzf"] = lines.nzfw + lines.nzfl

        lines["dzf"] = lines.dzfw + lines.dzfl

        cols = [x for x in list(LineSchema.dtypes.keys()) if x in lines.columns]

        lines = lines[cols].loc[lines.toi > 0].reset_index(drop=True)

        lines = prep_p60(lines)

        lines = prep_oi_percent(lines)

        lines = LineSchema.validate(lines)

        self._lines = lines

    def prep_lines(
        self,
        position: Literal["F", "D"] = "F",
        level: Literal["period", "game", "session", "season"] = "game",
        score: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
    ) -> None:
        """Prepares DataFrame of line-level stats from play-by-play data.

        Used to prepare, or reset prepared data for later analysis

        Parameters:
            position (str):
                Determines what positions to aggregate. One of F or D
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account for score state
            teammates (bool):
                Determines if stats account for teammates on ice
            opposition (bool):
                Determines if stats account for opponents on ice
            disable_progress_bar (bool):
                Determines whether to display the progress bar

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Prepares on-ice, line-level dataframe with default options
            >>> scraper.prep_lines()

            Line-level statistics, aggregated to season level
            >>> scraper.prep_lines(level="season")

            Line-level statistics, aggregated to game level, accounting for teammates
            >>> scraper.prep_lines(level="game", teammates=True)

        """
        levels = self._lines_levels

        if (
            levels["position"] != position
            or levels["level"] != level
            or levels["score"] != score
            or levels["teammates"] != teammates
            or levels["opposition"] != opposition
        ):
            self._lines = pd.DataFrame()

            new_values = {
                "position": position,
                "level": level,
                "score": score,
                "teammates": teammates,
                "opposition": opposition,
            }

            self._lines_levels.update(new_values)

        if self._lines.empty:
            with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
                pbar_message = f"Prepping lines data..."
                progress_task = progress.add_task(
                    pbar_message, total=None, refresh=True
                )

                progress.start_task(progress_task)
                progress.update(
                    progress_task, total=1, description=pbar_message, refresh=True
                )

                self._prep_lines(
                    level=level,
                    position=position,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                )

                progress.update(
                    progress_task,
                    description="Finished prepping lines data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )

    @property
    def lines(self) -> pd.DataFrame:
        """Pandas Dataframe of line-level stats aggregated from play-by-play data.

        Determine level of aggregation using `prep_lines` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            game_date (int):
                Date game was played, e.g., 2023-10-10
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            forwards (str):
                Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
            forwards_eh_id (str):
                Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
            forwards_api_id (str):
                Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
            defense (str):
                Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
            defense_eh_id (str):
                Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
            defense_api_id (str):
                Defense teammates' NHL API IDs, e.g., 8474151, 8478851
            own_goalie (str):
                Own goalie, e.g., JUUSE SAROS
            own_goalie_eh_id (str):
                Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
            own_goalie_api_id (str):
                Own goalie's NHL API ID, e.g., 8477424
            opp_forwards (str):
                Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
            opp_forwards_eh_id (str):
                Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
            opp_forwards_api_id (str):
                Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
            opp_defense (str):
                Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
            opp_defense_eh_id (str):
                Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
            opp_defense_api_id (str):
                Opposing defense's NHL API IDs, e.g., 8480246, 8475167
            opp_goalie (str):
                Opposing goalie, e.g., JONAS JOHANSSON
            opp_goalie_eh_id (str):
                Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
            opp_goalie_api_id (str):
                Opposing goalie's NHL API ID, e.g., 8477992
            toi (float):
                Time on-ice, in minutes, e.g, 0.483333
            gf (int):
                Goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.258332
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 4
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 4
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 4
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 1
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 1
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 1
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 0
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 0
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 0
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Returns line stats with default options
            >>> scraper.lines

            Resets line stats to period level, accounting for teammates on-ice
            >>> scraper.prep_lines(level="period", teammates=True)
            >>> scraper.lines

            Resets line stats to season level, accounting for teammates on-ice and score state
            >>> scraper.prep_lines(level="season", teammates=True, score=True)
            >>> scraper.lines

        """
        if self._lines.empty:
            self.prep_lines()

        return self._lines

    def _prep_team_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strengths: bool = True,
        opposition: bool = False,
        score: bool = False,
    ) -> None:
        """Prepares DataFrame of team stats from play-by-play data.

        Nested within `prep_team_stats` method.

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account  for score state
            strengths (bool):
                Determines if stats account  for strength state
            opposition (bool):
                Determines if stats account  for opponents on ice

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            toi (float):
                Time on-ice, in minutes, e.g, 1.100000
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.271583
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 5
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 5
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 5
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 4
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 2
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 2
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 1
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 1
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 1
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Team dataframe with default options
            >>> scraper._prep_team_stats()

            Team statistics, aggregated to season level
            >>> scraper._prep_team_stats(level="season")

            Team statistics, aggregated to game level, accounting for teammates
            >>> scraper._prep_team_stats(level="game", teammates=True)

        """
        merge_cols = ["id", "event_idx"]

        data = self.play_by_play.merge(self.play_by_play_ext, how="left", on=merge_cols)

        # Getting the "for" stats

        group_list = ["season", "session", "event_team"]

        if strengths is True:
            group_list.append("strength_state")

        if level == "game" or level == "period" or opposition:
            group_list.insert(3, "opp_team")

            group_list[2:2] = ["game_id", "game_date"]

        if level == "period":
            group_list.append("period")

        if score is True:
            group_list.append("score_state")

        agg_stats = [
            "pred_goal",
            "pred_goal_adj",
            "shot",
            "shot_adj",
            "miss",
            "block",
            "teammate_block",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "give",
            "take",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "hit",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "event_length",
        ]

        agg_dict = {x: "sum" for x in agg_stats if x in data.columns}

        new_cols = [
            "xgf",
            "xgf_adj",
            "sf",
            "sf_adj",
            "msf",
            "bsa",
            "teammate_block",
            "ff",
            "ff_adj",
            "gf",
            "gf_adj",
            "give",
            "take",
            "hdgf",
            "hdsf",
            "hdff",
            "hdmsf",
            "hf",
            "pent0",
            "pent2",
            "pent4",
            "pent5",
            "pent10",
            "fow",
            "ozfw",
            "nzfw",
            "dzfw",
            "toi",
        ]

        new_cols = dict(zip(agg_stats, new_cols))

        new_cols.update({"event_team": "team"})

        stats_for = (
            data.groupby(group_list, as_index=False)
            .agg(agg_dict)
            .rename(columns=new_cols)
        )

        # Getting the "against" stats

        group_list = ["season", "session", "opp_team"]

        if strengths is True:
            group_list.append("opp_strength_state")

        if level == "game" or level == "period":
            group_list.insert(3, "event_team")

            group_list[2:2] = ["game_id", "game_date"]

        if level == "period":
            group_list.append("period")

        if score is True:
            group_list.append("opp_score_state")

        agg_stats = [
            "pred_goal",
            "pred_goal_adj",
            "shot",
            "shot_adj",
            "miss",
            "block",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "hit",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "event_length",
        ]

        agg_dict = {x: "sum" for x in agg_stats if x in data.columns}

        new_cols = [
            "xga",
            "xga_adj",
            "sa",
            "sa_adj",
            "msa",
            "bsf",
            "fa",
            "fa_adj",
            "ga",
            "ga_adj",
            "hdga",
            "hdsa",
            "hdfa",
            "hdmsa",
            "ht",
            "pend0",
            "pend2",
            "pend4",
            "pend5",
            "pend10",
            "fol",
            "ozfl",
            "nzfl",
            "dzfl",
            "toi",
        ]

        new_cols = dict(zip(agg_stats, new_cols))

        new_cols.update(
            {
                "opp_team": "team",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                "event_team": "opp_team",
            }
        )

        stats_against = (
            data.groupby(group_list, as_index=False)
            .agg(agg_dict)
            .rename(columns=new_cols)
        )

        merge_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "team",
            "opp_team",
            "strength_state",
            "score_state",
            "period",
        ]

        merge_list = [
            x
            for x in merge_list
            if x in stats_for.columns and x in stats_against.columns
        ]

        team_stats = stats_for.merge(stats_against, on=merge_list, how="outer")

        team_stats["toi"] = (team_stats.toi_x + team_stats.toi_y) / 60

        fos = ["ozf", "nzf", "dzf"]

        for fo in fos:
            team_stats[fo] = team_stats[f"{fo}w"] + team_stats[f"{fo}w"]

        team_stats = team_stats.dropna(subset="toi").reset_index(drop=True)

        cols = [x for x in list(TeamStatSchema.dtypes.keys()) if x in team_stats]

        team_stats = team_stats[cols]

        team_stats = prep_p60(team_stats)

        team_stats = prep_oi_percent(team_stats)

        team_stats = TeamStatSchema.validate(team_stats)

        self._team_stats = team_stats

    def prep_team_stats(
        self,
        level: Literal["period", "game", "session", "season"] = "game",
        strengths: bool = True,
        opposition: bool = False,
        score: bool = False,
        disable_progress_bar: bool = False,
    ) -> None:
        """Prepares DataFrame of team stats from play-by-play data.

        Used to prepare, or reset prepared data for later analysis

        Parameters:
            level (str):
                Determines the level of aggregation. One of season, session, game, period
            score (bool):
                Determines if stats account  for score state
            strengths (bool):
                Determines if stats account  for strength state
            opposition (bool):
                Determines if stats account  for opponents on ice
            disable_progress_bar (bool):
                Determines whether to display the progress bar

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            toi (float):
                Time on-ice, in minutes, e.g, 1.100000
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.271583
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 5
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 5
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 5
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 4
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 2
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 2
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 1
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 1
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 1
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Team dataframe with default options
            >>> scraper.prep_team_stats()

            Team statistics, aggregated to season level
            >>> scraper.prep_team_stats(level="season")

            Team statistics, aggregated to game level, accounting for teammates
            >>> scraper.prep_team_stats(level="game", teammates=True)

        """
        levels = self._team_stats_levels

        if (
            levels["level"] != level
            or levels["score"] != score
            or levels["strengths"] != strengths
            or levels["opposition"] != opposition
        ):
            self._team_stats = pd.DataFrame()

            new_values = {
                "level": level,
                "score": score,
                "strengths": strengths,
                "opposition": opposition,
            }

            self._team_stats_levels.update(new_values)

        if self._team_stats.empty:
            with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
                pbar_message = f"Prepping team stats data..."
                progress_task = progress.add_task(
                    pbar_message, total=None, refresh=True
                )

                progress.start_task(progress_task)
                progress.update(
                    progress_task, total=1, description=pbar_message, refresh=True
                )

                self._prep_team_stats(
                    level=level, score=score, strengths=strengths, opposition=opposition
                )

                progress.update(
                    progress_task,
                    description="Finished prepping team stats data",
                    completed=True,
                    advance=True,
                    refresh=True,
                )

    @property
    def team_stats(self):
        """Pandas Dataframe of teams stats aggregated from play-by-play data.

        Determine level of aggregation using `prep_team_stats` method.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 2023 for 2023-24 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020001
            team (str):
                Player's team, e.g., NSH
            opp_team (str):
                Opposing team, e.g., TBL
            strength_state (str):
                Strength state, e.g., 5v5
            period (int):
                Period, e.g., 3
            score_state (str):
                Score state, e.g., 2v1
            toi (float):
                Time on-ice, in minutes, e.g, 1.100000
            gf (int):
                Goals for (on-ice), e.g, 0
            hdgf (int):
                High-danger goals for (on-ice), e.g, 0
            ga (int):
                Goals against (on-ice), e.g, 0
            hdga (int):
                High-danger goals against (on-ice), e.g, 0
            xgf (float):
                xG for (on-ice), e.g., 1.271583
            xga (float):
                xG against (on-ice), e.g, 0.000000
            sf (int):
                Shots for (on-ice), e.g, 5
            sa (int):
                Shots against (on-ice), e.g, 0
            hdsf (int):
                High-danger shots for (on-ice), e.g, 3
            hdsa (int):
                High-danger shots against (on-ice), e.g, 0
            ff (int):
                Fenwick for (on-ice), e.g, 5
            fa (int):
                Fenwick against (on-ice), e.g, 0
            hdff (int):
                High-danger fenwick for (on-ice), e.g, 3
            hdfa (int):
                High-danger fenwick against (on-ice), e.g, 0
            cf (int):
                Corsi for (on-ice), e.g, 5
            ca (int):
                Corsi against (on-ice), e.g, 0
            bsf (int):
                Shots taken that were blocked (on-ice), e.g, 0
            bsa (int):
                Shots blocked (on-ice), e.g, 0
            msf (int):
                Missed shots taken (on-ice), e.g, 0
            msa (int):
                Missed shots against (on-ice), e.g, 0
            hdmsf (int):
                High-danger missed shots taken (on-ice), e.g, 0
            hdmsa (int):
                High-danger missed shots against (on-ice), e.g, 0
            teammate_block (int):
                Shots blocked by teammates (on-ice), e.g, 0
            hf (int):
                Hits for (on-ice), e.g, 0
            ht (int):
                Hits taken (on-ice), e.g, 0
            give (int):
                Giveaways (on-ice), e.g, 0
            take (int):
                Takeaways (on-ice), e.g, 0
            ozf (int):
                Offensive zone faceoffs (on-ice), e.g, 0
            nzf (int):
                Neutral zone faceoffs (on-ice), e.g, 4
            dzf (int):
                Defensive zone faceoffs (on-ice), e.g, 0
            fow (int):
                Faceoffs won (on-ice), e.g, 2
            fol (int):
                Faceoffs lost (on-ice), e.g, 0
            ozfw (int):
                Offensive zone faceoffs won (on-ice), e.g, 0
            ozfl (int):
                Offensive zone faceoffs lost (on-ice), e.g, 0
            nzfw (int):
                Neutral zone faceoffs won (on-ice), e.g, 2
            nzfl (int):
                Neutral zone faceoffs lost (on-ice), e.g, 1
            dzfw (int):
                Defensive zone faceoffs won (on-ice), e.g, 0
            dzfl (int):
                Defensive zone faceoffs lost (on-ice), e.g, 1
            pent0 (int):
                Penalty shots allowed (on-ice), e.g, 0
            pent2 (int):
                Minor penalties taken (on-ice), e.g, 1
            pent4 (int):
                Double minor penalties taken (on-ice), e.g, 0
            pent5 (int):
                Major penalties taken (on-ice), e.g, 0
            pent10 (int):
                Game misconduct penalties taken (on-ice), e.g, 0
            pend0 (int):
                Penalty shots drawn (on-ice), e.g, 0
            pend2 (int):
                Minor penalties drawn (on-ice), e.g, 0
            pend4 (int):
                Double minor penalties drawn (on-ice), e.g, 0
            pend5 (int):
                Major penalties drawn (on-ice), e.g, 0
            pend10 (int):
                Game misconduct penalties drawn (on-ice), e.g, 0
            gf_p60 (float):
                Goals for (on-ice) per 60 minutes
            ga_p60 (float):
                Goals against (on-ice) per 60 minutes
            hdgf_p60 (float):
                High-danger goals for (on-ice) per 60 minutes
            hdga_p60 (float):
                High-danger goals against (on-ice) per 60 minutes
            xgf_p60 (float):
                xG for (on-ice) per 60 minutes
            xga_p60 (float):
                xG against (on-ice) per 60 minutes
            sf_p60 (float):
                Shots for (on-ice) per 60 minutes
            sa_p60 (float):
                Shots against (on-ice) per 60 minutes
            hdsf_p60 (float):
                High-danger shots for (on-ice) per 60 minutes
            hdsa_p60 (float):
                High danger shots against (on-ice) per 60 minutes
            ff_p60 (float):
                Fenwick for (on-ice) per 60 minutes
            fa_p60 (float):
                Fenwick against (on-ice) per 60 minutes
            hdff_p60 (float):
                High-danger fenwick for (on-ice) per 60 minutes
            hdfa_p60 (float):
                High-danger fenwick against (on-ice) per 60 minutes
            cf_p60 (float):
                Corsi for (on-ice) per 60 minutes
            ca_p60 (float):
                Corsi against (on-ice) per 60 minutes
            bsf_p60 (float):
                Blocked shots for (on-ice) per 60 minutes
            bsa_p60 (float):
                Blocked shots against (on-ice) per 60 minutes
            msf_p60 (float):
                Missed shots for (on-ice) per 60 minutes
            msa_p60 (float):
                Missed shots against (on-ice) per 60 minutes
            hdmsf_p60 (float):
                High-danger missed shots for (on-ice) per 60 minutes
            hdmsa_p60 (float):
                High-danger missed shots against (on-ice) per 60 minutes
            teammate_block_p60 (float):
                Shots blocked by teammates (on-ice) per 60 minutes
            hf_p60 (float):
                Hits  for (on-ice) per 60 minutes
            ht_p60 (float):
                Hits taken (on-ice) per 60 minutes
            give_p60 (float):
                Giveaways (on-ice) per 60 minutes
            take_p60 (float):
                Takeaways (on-ice) per 60 minutes
            pent0_p60 (float):
                Penalty shots taken (on-ice) per 60 minutes
            pent2_p60 (float):
                Minor penalties taken (on-ice) per 60 minutes
            pent4_p60 (float):
                Double minor penalties taken (on-ice) per 60 minutes
            pent5_p60 (float):
                Major penalties taken (on-ice) per 60 minutes
            pent10_p60 (float):
                Game misconduct pentalties taken (on-ice) per 60 minutes
            pend0_p60 (float):
                Penalty shots drawn (on-ice) per 60 minutes
            pend2_p60 (float):
                Minor penalties drawn (on-ice) per 60 minutes
            pend4_p60 (float):
                Double minor penalties drawn (on-ice) per 60 minutes
            pend5_p60 (float):
                Major penalties drawn (on-ice) per 60 minutes
            pend10_p60 (float):
                Game misconduct penalties drawn (on-ice) per 60 minutes
            gf_percent (float):
                On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
            hdgf_percent (float):
                On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
            xgf_percent (float):
                On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
            sf_percent (float):
                On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
            hdsf_percent (float):
                On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
            ff_percent (float):
                On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
            hdff_percent (float):
                On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
            cf_percent (float):
                On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
            bsf_percent (float):
                On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
            msf_percent (float):
                On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
            hdmsf_percent (float):
                On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
            hf_percent (float):
                On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
            take_percent (float):
                On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2023020001
            >>> scraper = Scraper(game_id)

            Returns team stats with default options
            >>> scraper.team_stats

            Resets team stats to season level, accounting for opposing team
            >>> scraper.prep_team_stats(level="season", opposition=True)
            >>> scraper.team_stats

            Resets team stats to season level, accounting for opposing team and score state
            >>> scraper.prep_team_stats(level="season", opposition=True, score=True)
            >>> scraper.team_stats

        """
        if self._team_stats.empty:
            self.prep_team_stats()

        return self._team_stats


class Season:
    """Scrapes schedule and standings data.

    Helpful for pulling game IDs and scraping programmatically.

    Parameters:
        year (int or float or str):
            4-digit year identifier, the first year in the season, e.g., 2023

    Attributes:
        season (int):
            8-digit year identifier, the year entered, plus 1, e.g., 20232024

    Examples:
        First, instantiate the Season object
        >>> season = Season(2023)

        Scrape schedule information
        >>> nsh_schedule = season.schedule(
        ...     "NSH"
        ... )  # Returns the schedule for the Nashville Predators

        Scrape standings information
        >>> standings = season.standings  # Returns the latest standings for that season

    """

    def __init__(self, year: str | int | float):
        """Instantiates a Season object for a given year."""
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

        teams_2024 = [
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
            "PIT",
            "SEA",
            "SJS",
            "STL",
            "TBL",
            "TOR",
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
        }

        self.teams = self._teams_dict.get(first_year)

        if self._teams_dict.get(first_year) is None:
            raise Exception(f"{first_year} IS NOT SUPPORTED")

        self._schedule = []

        self._scraped_schedule_teams = []

        self._scraped_schedule = []

        self._standings = []

        self._requests_session = ChickenSession()

        self._season_str = str(self.season)[:4] + "-" + str(self.season)[6:8]

    def _scrape_schedule(
        self,
        team_schedule: str = "all",
        sessions: list[str] | str | None = None,
        disable_progress_bar=False,
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

        if team_schedule not in self._scraped_schedule_teams:
            with self._requests_session as s:
                with ChickenProgress(disable=disable_progress_bar) as progress:
                    if team_schedule == "all":
                        teams = self.teams

                        pbar_stub = f"{self._season_str} schedule information"

                        pbar_message = f"Downloading {pbar_stub} for all teams..."

                        sched_task = progress.add_task(pbar_message, total=len(teams))

                        for team in teams:
                            if (
                                team in self._scraped_schedule_teams
                            ):  # Not covered by tests
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
                                games = self._munge_schedule(games, sessions)
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
                                games = self._munge_schedule(games, sessions)
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

        self._schedule.extend(schedule_list)

    @staticmethod
    def _munge_schedule(
        games: list[dict], sessions: list[str] | str | None
    ) -> list[dict]:
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
                session_dict = {"PR": 1, "R": 2, "P": 3}

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
                "game_date_dt": game_date_dt,
                "tv_broadcasts": game["tvBroadcasts"],
                "home_logo": game["homeTeam"].get("logo"),
                "home_logo_dark": game["homeTeam"].get("darkLogo"),
                "away_logo": game["awayTeam"].get("logo"),
                "away_logo_dark": game["awayTeam"].get("darkLogo"),
            }

            returned_games.append(ScheduleGame.model_validate(game_info).model_dump())

        return returned_games

    @staticmethod
    def _finalize_schedule(games: list[dict]) -> pd.DataFrame:
        """Method to finalize the schedule from NHL API endpoint into a Pandas DataFrame.

        Nested within `schedule` method.

        For more information and usage, see
        https://chickenstats.com/latest/contribute/contribute/
        """
        df = pd.DataFrame(games)

        return df

    def schedule(
        self,
        team_schedule: str | None = "all",
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> pd.DataFrame:
        """Scrapes NHL schedule. Can return whole or season or subset of teams' schedules.

        Parameters:
            team_schedule (str | None):
                Three-letter team's schedule to scrape, e.g., NSH
            sessions: (list | None | str | int):
                Whether to scrape regular season (2), playoffs (3), or pre-season (1), if left blank,
                scrapes regular season and playoffs
            disable_progress_bar (bool):
                Whether to disable progress bar

        Returns:
            season (int):
                8-digit season identifier, e.g., 20232024
            session (int):
                Type of game played - pre-season (1), regular season (2), or playoffs (3), e.g., 2
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2023020015
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
            game_date_dt (dt.datetime):
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
        if team_schedule not in self._scraped_schedule_teams:
            self._scrape_schedule(
                team_schedule=team_schedule,
                sessions=sessions,
                disable_progress_bar=disable_progress_bar,
            )

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
        url = "https://api-web.nhle.com/v1/standings/now"

        with self._requests_session as s:
            r = s.get(url).json()

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
                "conference": team["conferenceName"],
                "date": team["date"],
                "division": team["divisionName"],
                "games_played": team["gamesPlayed"],
                "goal_differential": team["goalDifferential"],
                "goal_differential_pct": team["goalDifferentialPctg"],
                "goals_against": team["goalAgainst"],
                "goals_for": team["goalFor"],
                "goals_for_pct": team["goalsForPctg"],
                "home_games_played": team["homeGamesPlayed"],
                "home_goal_differential": team["homeGoalDifferential"],
                "home_goals_against": team["homeGoalsAgainst"],
                "home_goals_for": team["homeGoalsFor"],
                "home_losses": team["homeLosses"],
                "home_ot_losses": team["homeOtLosses"],
                "home_points": team["homePoints"],
                "home_wins": team["homeWins"],
                "home_regulation_wins": team["homeRegulationWins"],
                "home_ties": team["homeTies"],
                "l10_goal_differential": team["l10GoalDifferential"],
                "l10_goals_against": team["l10GoalsAgainst"],
                "l10_goals_for": team["l10GoalsFor"],
                "l10_losses": team["l10Losses"],
                "l10_ot_losses": team["l10OtLosses"],
                "l10_points": team["l10Points"],
                "l10_regulation_wins": team["l10RegulationWins"],
                "l10_ties": team["l10Ties"],
                "l10_wins": team["l10Wins"],
                "losses": team["losses"],
                "ot_losses": team["otLosses"],
                "points_pct": team["pointPctg"],
                "points": team["points"],
                "regulation_win_pct": team["regulationWinPctg"],
                "regulation_wins": team["regulationWins"],
                "road_games_played": team["roadGamesPlayed"],
                "road_goal_differential": team["roadGoalDifferential"],
                "road_goals_against": team["roadGoalsAgainst"],
                "road_goals_for": team["roadGoalsFor"],
                "road_losses": team["roadLosses"],
                "road_ot_losses": team["roadOtLosses"],
                "road_points": team["roadPoints"],
                "road_regulation_wins": team["roadRegulationWins"],
                "road_ties": team["roadTies"],
                "road_wins": team["roadWins"],
                "season": team["seasonId"],
                "shootoutLosses": team["shootoutLosses"],
                "shootout_wins": team["shootoutWins"],
                "streak_code": team["streakCode"],
                "streak_count": team["streakCount"],
                "team_name": team["teamName"]["default"],
                "team": team["teamAbbrev"]["default"],
                "team_logo": team["teamLogo"],
                "ties": team["ties"],
                "waivers_sequence": team["waiversSequence"],
                "wildcard_sequence": team["wildcardSequence"],
                "win_pct": team["winPctg"],
                "wins": team["wins"],
            }

            final_standings.append(StandingsTeam.model_validate(team_data).model_dump())

        self._standings = final_standings

    def _finalize_standings(self):
        df = pd.DataFrame(self._standings)

        return df

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

        return self._finalize_standings()
