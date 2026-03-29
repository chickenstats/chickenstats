from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cache, cached_property, lru_cache
import re
from datetime import datetime as dt
from datetime import timedelta
from typing import Literal

import narwhals as nw
import numpy as np
import pandas as pd
import polars as pl
import pytz
from bs4 import BeautifulSoup
from requests.exceptions import RetryError
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from unidecode import unidecode

from chickenstats.chicken_nhl._fixes import (
    api_events_fixes,
    api_rosters_fixes,
    html_events_fixes,
    html_rosters_fixes,
    rosters_fixes,
    shifts_fixes,
)
from chickenstats.chicken_nhl._game_utils import (
    calculate_score_adjustment,
    hs_strip_html,
    load_model,
    load_score_adjustments,
)

# These are dictionaries of names that are used throughout the module
from chickenstats.chicken_nhl._player_names import correct_player_name, correct_api_names_dict, correct_names_dict
from chickenstats.chicken_nhl.team import team_codes
from chickenstats.chicken_nhl.validation_pydantic import (
    APIEvent,
    APIRosterPlayer,
    ChangeEvent,
    HTMLEvent,
    HTMLRosterPlayer,
    PBPEvent,
    PBPEventExt,
    PlayerShift,
    RosterPlayer,
    XGFields,
)
from chickenstats.chicken_nhl.validation_polars import (
    api_events_polars_schema,
    api_rosters_polars_schema,
    changes_polars_schema,
    html_events_polars_schema,
    html_rosters_polars_schema,
    pbp_polars_schema,
    rosters_polars_schema,
    shifts_polars_schema,
)
from chickenstats.utilities.utilities import ChickenSession

model_version = "0.1.1"


@cache
@lru_cache(maxsize=5)
def _get_model(variant: str, version: str):
    return load_model(variant, version)


@lru_cache(maxsize=1)
def _get_score_adjustments():
    return load_score_adjustments()


# Pre-computed column name tuples for extended on-ice columns — avoids f-string formatting per play
_EXT_SOURCE_KEYS = (
    ("teammates", "teammates_eh_id", "teammates_api_id", "teammates_positions"),
    ("opp_team_on", "opp_team_on_eh_id", "opp_team_on_api_id", "opp_team_on_positions"),
)

_EXT_TARGET_KEYS = tuple(
    tuple((f"{prefix}_{i}", f"{prefix}_{i}_eh_id", f"{prefix}_{i}_api_id", f"{prefix}_{i}_pos") for i in range(1, 8))
    for prefix in ("event_on", "opp_on")
)


def handle_scoring_details(event_type: str, event_details: dict) -> dict:
    """Extracts common data for shots and goals."""
    mapping = {
        "event": "SHOT"
        if event_type == "shot-on-goal"
        else "MISS"
        if event_type in ["missed-shot", "failed-shot-attempt"]
        else "GOAL",
        "player_1_api_id": event_details.get("shootingPlayerId") or event_details.get("scoringPlayerId"),
        "player_1_type": "SHOOTER" if "shot" in event_type else "GOAL SCORER",
        "opp_goalie_api_id": event_details.get("goalieInNetId"),
        "shot_type": event_details.get("shotType", "WRIST").upper(),
    }

    if event_type == "goal":
        mapping.update(
            {
                "player_2_api_id": event_details.get("assist1PlayerId"),
                "player_2_type": "PRIMARY ASSIST" if event_details.get("assist1PlayerId") else None,
                "player_3_api_id": event_details.get("assist2PlayerId"),
                "player_3_type": "SECONDARY ASSIST" if event_details.get("assist2PlayerId") else None,
            }
        )
    elif event_type == "missed-shot":
        mapping["miss_reason"] = event_details.get("reason", "").replace("-", " ").upper()

    return mapping


def handle_penalty_details(event_details: dict) -> dict:
    """Logic for PENL event types, including bench penalties."""
    event_info = {
        "event": "PENL",
        "penalty_type": event_details.get("typeCode"),
        "penalty_reason": event_details.get("descKey", "").upper(),
        "penalty_duration": event_details.get("duration"),
    }

    # Bench penalty logic from original code
    is_bench = (
        event_info["penalty_type"] == "BEN"
        or "HEAD-COACH" in event_info["penalty_reason"]
        or "TEAM-STAFF" in event_info["penalty_reason"]
    )
    if is_bench and not event_details.get("committedByPlayerId"):
        event_info.update(
            {
                "player_1": "BENCH",
                "player_1_eh_id": "BENCH",
                "player_1_type": "COMMITTED BY",
                "player_2_api_id": event_details.get("servedByPlayerId"),
                "player_2_type": "SERVED BY",
            }
        )
    else:
        event_info.update(
            {
                "player_1_api_id": event_details.get("committedByPlayerId"),
                "player_1_type": "COMMITTED BY",
                "player_2_api_id": event_details.get("drawnByPlayerId") or event_details.get("servedByPlayerId"),
                "player_2_type": "DRAWN BY" if event_details.get("drawnByPlayerId") else "SERVED BY",
            }
        )
        if event_details.get("drawnByPlayerId") and event_details.get("servedByPlayerId"):
            event_info.update({"player_3_api_id": event_details.get("servedByPlayerId"), "player_3_type": "SERVED BY"})

    return event_info


def map_player_metadata(event_info: dict, rosters: dict) -> dict:
    """Injects Roster data (Names, Positions, EH_IDs) into an Event dict using API IDs."""
    for prefix in ["player_1", "player_2", "player_3", "opp_goalie"]:
        api_id = event_info.get(f"{prefix}_api_id")
        if api_id:
            player = rosters.get(api_id)
            if player:
                event_info.update(
                    {
                        prefix: player.get("player_name"),
                        f"{prefix}_eh_id": player.get("eh_id"),
                        f"{prefix}_team_jersey": player.get("team_jersey"),
                        f"{prefix}_position": player.get("position"),
                    }
                )

    # Specific logic for BLOCK team identification
    if event_info.get("event") == "BLOCK" and event_info.get("player_1_team_jersey"):
        event_info["event_team"] = event_info["player_1_team_jersey"][:3]

    elif event_info.get("event") == "BLOCK" and not event_info.get("player_1_team_jersey"):
        event_info["event_team"] = "OTHER"
        event_info["player_1"] = "REFEREE"
        event_info["player_1_eh_id"] = "REFEREE"
        event_info["player_1_api_id"] = None

    return event_info


def apply_event_versioning(event_list: list) -> list:
    """Ensures simultaneous events get unique version numbers and validates with Pydantic."""
    counts = {}
    final_events = []
    for ev in event_list:
        key = (ev["event"], ev["game_seconds"], ev["period"], ev.get("player_1_api_id"))
        counts[key] = counts.get(key, 0) + 1
        ev["version"] = counts[key]
        final_events.append(APIEvent.model_validate(ev).model_dump())
    return final_events


def parse_time(time_str: str) -> int:
    """Converts 'MM:SS' to total seconds."""
    if not time_str:
        return 0
    try:
        m, s = map(int, time_str.split(":"))
        return (m * 60) + s
    except ValueError:
        return 0


def aggregate_players(players: list) -> dict:
    """Loops through players exactly once and builds all arrays simultaneously. O(N) execution."""
    forwards_set = {"L", "C", "R"}

    agg = {
        "ALL": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
        "F": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
        "D": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
        "G": {"count": 0, "jerseys": [], "names": [], "eh_ids": [], "api_ids": [], "positions": []},
    }

    for p in players:
        team_jersey, name, eh_id = p.get("team_jersey"), p.get("player_name"), p.get("eh_id")
        api_id, pos = str(p.get("api_id")), p.get("position")

        # Determine specific bucket using O(1) lookups
        bucket = "F" if pos in forwards_set else pos if pos in {"D", "G"} else None

        # Always add to ALL, plus the specific positional bucket
        buckets_to_fill = ["ALL", bucket] if bucket else ["ALL"]

        for b in buckets_to_fill:
            agg[b]["count"] += 1
            agg[b]["jerseys"].append(team_jersey)
            agg[b]["names"].append(name)
            agg[b]["eh_ids"].append(eh_id)
            agg[b]["api_ids"].append(api_id)
            agg[b]["positions"].append(pos)

    return agg


def prefetch_concurrent(*fetch_tasks) -> None:
    """Run the given fetch tasks concurrently and cache their results.

    Each task is a bound method with its own cache guard, so calling this
    multiple times is safe — already-fetched tasks return immediately.
    """
    with ThreadPoolExecutor(max_workers=len(fetch_tasks)) as executor:
        futures = [executor.submit(task) for task in fetch_tasks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                pass


class Game:
    # noinspection GrazieInspection
    """Class instance for scraping play-by-play and other data for individual games. Utilized within Scraper.

    Parameters:
        game_id (int or float or str):
            10-digit game identifier, e.g., 2023020001
        requests_session (requests.Session, optional):
            If scraping multiple games, can provide single Session object to reduce stress on the API / HTML endpoints
        backend (None | str):
            Whether to use pandas or polars as backend for data manipulation. Defaults to pandas

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
        >>> rosters = game.rosters  # Returns a list of players from both API & HTML endpoints
        >>> changes = game.changes  # Returns a list of changes constructed from shifts & roster data

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
        requests_session: ChickenSession | None = None,
        backend: Literal["pandas", "polars", "pyarrow", "narwhals"] = "polars",
    ):
        """Instantiates a Game object for a given game ID.

        If nested, you can provide a requests.Session object to optimize speed.
        """
        if str(game_id).isdigit() is False or len(str(game_id)) != 10:
            raise ValueError(f"{game_id!r} is not a valid game ID")

        self._backend: Literal["pandas", "polars", "pyarrow", "narwhals"] = backend

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

        if self._backend != "polars":
            df = nw.from_native(df)

            if self._backend == "pandas":
                df = df.to_pandas()

            elif self._backend == "pyarrow":
                df = df.to_arrow()

        return df

    def _munge_single_api_event(self, event: dict, teams: dict, rosters: dict) -> dict:
        """Worker method to process one raw play using pattern matching."""
        period = int(event["periodDescriptor"]["number"])
        period_type = event["periodDescriptor"]["periodType"]
        period_seconds = parse_time(event["timeInPeriod"])

        # Standardize game clock logic
        if self.session == "R" and period == 5:
            game_seconds = 3900
        else:
            game_seconds = ((period - 1) * 1200) + period_seconds

        # Initialize the core event dictionary
        event_info = {
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

        event_details = event.get("details", {})
        if event_details:
            event_info.update(
                {
                    "event_team": teams.get(event_details.get("eventOwnerTeamId")),
                    "coords_x": event_details.get("xCoord"),
                    "coords_y": event_details.get("yCoord"),
                    "zone": event_details.get("zoneCode"),
                    "event_team_id": event_details.get("eventOwnerTeamId"),
                }
            )

            # Use Pattern Matching for event-specific details
            match event_info["event"]:
                case "faceoff":
                    event_info.update(
                        {
                            "event": "FAC",
                            "player_1_api_id": event_details["winningPlayerId"],
                            "player_1_type": "WINNER",
                            "player_2_api_id": event_details["losingPlayerId"],
                            "player_2_type": "LOSER",
                        }
                    )
                case "hit":
                    event_info.update(
                        {
                            "event": "HIT",
                            "player_1_api_id": event_details["hittingPlayerId"],
                            "player_1_type": "HITTER",
                            "player_2_api_id": event_details["hitteePlayerId"],
                            "player_2_type": "HITTEE",
                        }
                    )
                case "giveaway" | "takeaway":
                    event_info.update(
                        {
                            "event": "GIVE" if event_info["event"] == "giveaway" else "TAKE",
                            "player_1_api_id": event_details["playerId"],
                            "player_1_type": "GIVER" if event_info["event"] == "giveaway" else "TAKER",
                        }
                    )
                case "shot-on-goal" | "missed-shot" | "goal" | "failed-shot-attempt":
                    event_info.update(handle_scoring_details(event_info["event"], event_details))
                case "blocked-shot":
                    event_info.update(
                        {
                            "event": "BLOCK",
                            "player_1_api_id": event_details.get("blockingPlayerId"),
                            "player_1_type": "BLOCKER",
                            "player_2_api_id": event_details["shootingPlayerId"],
                            "player_2_type": "SHOOTER",
                        }
                    )
                case "penalty":
                    event_info.update(handle_penalty_details(event_details))
                case "stoppage":
                    event_info.update(
                        {
                            "event": "STOP",
                            "stoppage_reason": event_details["reason"].upper().replace("-", " "),
                            "stoppage_reason_secondary": event_details.get("secondaryReason", "")
                            .upper()
                            .replace("-", " "),
                        }
                    )
                case "period-start" | "period-end" | "game-end" | "shootout-complete" | "delayed-penalty":
                    codes = {
                        "period-start": "PSTR",
                        "period-end": "PEND",
                        "game-end": "GEND",
                        "shootout-complete": "SOC",
                        "delayed-penalty": "DELPEN",
                    }
                    event_info["event"] = codes[event_info["event"]]

        # Apply external fixes and map roster metadata (names, positions, eh_ids)
        event_info = api_events_fixes(self.game_id, event_info)
        return map_player_metadata(event_info, rosters)

    @cached_property
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
        self._fetch_api_data()

        # Dependency: Accessing self.api_rosters triggers its own cached logic
        roster_lookup = {x["api_id"]: x for x in self.api_rosters}

        teams_dict = {self.home_team["id"]: self.home_team["abbrev"], self.away_team["id"]: self.away_team["abbrev"]}

        # Step 1: Transform raw plays into structured event dictionaries
        event_list = [
            self._munge_single_api_event(event, teams_dict, roster_lookup)
            for event in self.api_response.get("plays", [])
        ]

        # Step 2: Handle simultaneous versioning and Pydantic validation
        return apply_event_versioning(event_list)

    @property
    def api_events_df(self) -> pd.DataFrame | pl.DataFrame:
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
        return self._finalize_dataframe(data=self.api_events, schema=api_events_polars_schema)

    def _munge_api_player(self, player: dict) -> dict:
        """Worker method to clean a single API player record."""
        # Use a mapping for teams to avoid 'if' blocks
        team_map = {
            self.home_team["id"]: {"venue": "HOME", "team": self.home_team["abbrev"]},
            self.away_team["id"]: {"venue": "AWAY", "team": self.away_team["abbrev"]},
        }
        team_info = team_map[player["teamId"]]

        # Clean strings and generate IDs
        first_name = unidecode(player["firstName"]["default"]).upper().strip()
        last_name = unidecode(player["lastName"]["default"]).upper().strip()
        player_name = f"{first_name} {last_name}"

        # Apply corrections from your helper dictionaries
        player_name = correct_names_dict.get(player_name, player_name)
        eh_id = f"{player_name.split(' ', 1)[0]}.{player_name.split(' ', 1)[1]}".replace("..", ".")
        eh_id = correct_api_names_dict.get(player["playerId"], eh_id)

        # Build and validate schema
        player_info = {
            "season": self.season,
            "session": self.session,
            "game_id": self.game_id,
            "team": team_info["team"],
            "team_venue": team_info["venue"],
            "player_name": player_name,
            "first_name": first_name,
            "last_name": last_name,
            "api_id": player["playerId"],
            "eh_id": correct_api_names_dict.get(player["playerId"], eh_id),
            "team_jersey": team_info["team"] + str(player["sweaterNumber"]),
            "jersey": player["sweaterNumber"],
            "position": player["positionCode"],
            "headshot_url": player.get("headshot", ""),
        }
        return APIRosterPlayer.model_validate(player_info).model_dump()

    @cached_property
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
        if not self.api_response:
            self._fetch_api_data()

            # Transformation Pipeline
        players = [self._munge_api_player(player) for player in self.api_response.get("rosterSpots", [])]

        # Apply external fixes
        new_player = api_rosters_fixes(season=self.season, session=self.session, game_id=self.game_id)
        if new_player:
            players.append(APIRosterPlayer.model_validate(new_player).model_dump())

        return sorted(players, key=lambda k: (k["team_venue"], k["player_name"]))

    @property
    def api_rosters_df(self) -> pd.DataFrame | pl.DataFrame:
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
        df = self._finalize_dataframe(data=self.api_rosters, schema=api_rosters_polars_schema)

        return df

    def _munge_changes(self, shifts: list) -> list:
        """Transforms shifts into changes using an optimized O(N) single-pass grouping strategy."""
        changes_map = {}

        # 1. Single Pass: Group all shifts by their start and end times instantly
        for shift in shifts:
            period = shift["period"]
            team_venue = shift["team_venue"]

            # Track Change ON
            on_sec = shift.get("start_time_seconds", 0)
            on_key = (period, team_venue, on_sec)

            if on_key not in changes_map:
                changes_map[on_key] = {
                    "on": [],
                    "off": [],
                    "period_time": shift["start_time"],
                    "is_home": shift["is_home"],
                    "is_away": shift["is_away"],
                    "team": shift["team"],
                }
            changes_map[on_key]["on"].append(shift)

            # Track Change OFF
            off_sec = shift.get("end_time_seconds", 0)
            off_key = (period, team_venue, off_sec)

            if off_key not in changes_map:
                changes_map[off_key] = {
                    "on": [],
                    "off": [],
                    "period_time": shift["end_time"],
                    "is_home": shift["is_home"],
                    "is_away": shift["is_away"],
                    "team": shift["team"],
                }
            changes_map[off_key]["off"].append(shift)

        final_changes = []

        # 2. Extract, Format, and Validate
        sorted_keys = sorted(changes_map.keys(), key=lambda k: (k[0], k[2], 0 if k[1] == "HOME" else 1))

        for key in sorted_keys:
            period, team_venue, time_seconds = key
            data = changes_map[key]

            # Sort players numerically by jersey, then aggregate instantly using the static helper
            on_players = sorted(data["on"], key=lambda k: k.get("jersey", 0))
            off_players = sorted(data["off"], key=lambda k: k.get("jersey", 0))

            on_data = aggregate_players(on_players)
            off_data = aggregate_players(off_players)

            # Build logical descriptions
            desc_parts = []
            if on_data["ALL"]["count"] > 0:
                desc_parts.append(f"PLAYERS ON: {', '.join(on_data['ALL']['names'])}")
            if off_data["ALL"]["count"] > 0:
                desc_parts.append(f"PLAYERS OFF: {', '.join(off_data['ALL']['names'])}")
            description = " / ".join(desc_parts) if desc_parts else "NO CHANGE"

            # Calculate absolute game seconds
            if period == 5 and self.session == "R":
                game_seconds = 3900 + time_seconds
            else:
                game_seconds = (period - 1) * 1200 + time_seconds

            # Build Standardized Dictionary utilizing the single-pass data
            change_dict = {
                "season": self.season,
                "session": self.session,
                "game_id": self.game_id,
                "event": "CHANGE",
                "event_type": f"{team_venue} CHANGE",
                "event_team": data["team"],
                "is_home": data["is_home"],
                "is_away": data["is_away"],
                "team_venue": team_venue,
                "period": period,
                "period_time": data["period_time"],
                "period_seconds": time_seconds,
                "game_seconds": game_seconds,
                "description": description,
                "change_on_count": on_data["ALL"]["count"],
                "change_off_count": off_data["ALL"]["count"],
                "change_on_jersey": on_data["ALL"]["jerseys"],
                "change_on": on_data["ALL"]["names"],
                "change_on_eh_id": on_data["ALL"]["eh_ids"],
                "change_on_api_id": on_data["ALL"]["api_ids"],
                "change_on_positions": on_data["ALL"]["positions"],
                "change_off_jersey": off_data["ALL"]["jerseys"],
                "change_off": off_data["ALL"]["names"],
                "change_off_eh_id": off_data["ALL"]["eh_ids"],
                "change_off_api_id": off_data["ALL"]["api_ids"],
                "change_off_positions": off_data["ALL"]["positions"],
                "change_on_forwards_count": on_data["F"]["count"],
                "change_off_forwards_count": off_data["F"]["count"],
                "change_on_forwards_jersey": on_data["F"]["jerseys"],
                "change_on_forwards": on_data["F"]["names"],
                "change_on_forwards_eh_id": on_data["F"]["eh_ids"],
                "change_on_forwards_api_id": on_data["F"]["api_ids"],
                "change_off_forwards_jersey": off_data["F"]["jerseys"],
                "change_off_forwards": off_data["F"]["names"],
                "change_off_forwards_eh_id": off_data["F"]["eh_ids"],
                "change_off_forwards_api_id": off_data["F"]["api_ids"],
                "change_on_defense_count": on_data["D"]["count"],
                "change_off_defense_count": off_data["D"]["count"],
                "change_on_defense_jersey": on_data["D"]["jerseys"],
                "change_on_defense": on_data["D"]["names"],
                "change_on_defense_eh_id": on_data["D"]["eh_ids"],
                "change_on_defense_api_id": on_data["D"]["api_ids"],
                "change_off_defense_jersey": off_data["D"]["jerseys"],
                "change_off_defense": off_data["D"]["names"],
                "change_off_defense_eh_id": off_data["D"]["eh_ids"],
                "change_off_defense_api_id": off_data["D"]["api_ids"],
                "change_on_goalie_count": on_data["G"]["count"],
                "change_off_goalie_count": off_data["G"]["count"],
                "change_on_goalie_jersey": on_data["G"]["jerseys"],
                "change_on_goalie": on_data["G"]["names"],
                "change_on_goalie_eh_id": on_data["G"]["eh_ids"],
                "change_on_goalie_api_id": on_data["G"]["api_ids"],
                "change_off_goalie_jersey": off_data["G"]["jerseys"],
                "change_off_goalie": off_data["G"]["names"],
                "change_off_goalie_eh_id": off_data["G"]["eh_ids"],
                "change_off_goalie_api_id": off_data["G"]["api_ids"],
            }

            # Validate instantly and append
            final_changes.append(ChangeEvent.model_validate(change_dict).model_dump())

        return final_changes

    @cached_property
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

        shifts = self.shifts
        if not shifts:
            return []

        # 2. Transformation Worker (Passes shifts to O(N) grouping method)
        final_changes = self._munge_changes(shifts)

        return final_changes

    @property
    def changes_df(self) -> pd.DataFrame | pl.DataFrame:
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

        return self._finalize_dataframe(data=self.changes, schema=changes_polars_schema)

    def _fetch_html_events(self) -> list:
        if self._raw_html_events is not None:
            return self._raw_html_events

        url = self.html_events_endpoint
        s = self._requests_session

        try:
            response = s.get(url)
        except RetryError:
            self._raw_html_events = []
            return self._raw_html_events

        soup = BeautifulSoup(response.content.decode("ISO-8859-1"), "lxml")
        events = []

        if soup.find("html") is None:
            self._raw_html_events = []
            return self._raw_html_events

        tds = soup.find_all("td", {"class": re.compile(".*bborder.*")})
        events_data = hs_strip_html(tds)
        events_data = [unidecode(x).replace("\n ", ", ").replace("\n", "") for x in events_data]

        length = int(len(events_data) / 8)
        events_data = np.array(events_data).reshape(length, 8)

        for _idx, event in enumerate(events_data):
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

            event_dict = dict(zip(column_names, event, strict=True))

            # Ensure period is handled as an integer immediately
            period_val = int(event_dict["period"]) if event_dict["period"].isdigit() else 1

            new_values = {
                "season": self.season,
                "session": self.session,
                "game_id": self.game_id,
                "event_idx": int(event_dict["event_idx"]),
                "description": unidecode(event_dict["description"]).upper(),
                "period": period_val,
            }

            event_dict.update(new_values)

            # Handle specific missing events
            if self.game_id == 2022020194 and event_dict["event_idx"] == 134:
                continue
            if self.game_id == 2022020673 and event_dict["event_idx"] == 208:
                continue

            events.append(event_dict)

        self._raw_html_events = events
        return self._raw_html_events

    def _munge_html_events(self, raw_events: list, actives: dict, scratches: dict) -> list:
        """Worker method to transform raw HTML events into structured event dicts.

        Called internally by the html_events cached property.

        Examples:
            >>> game = Game(2023020001)
            >>> game.html_events  # fetches and processes in one step
            >>> game.html_events_df
        """
        # 1. Compile regexes once
        event_team_re = re.compile(r"^([A-Z]{3}|[A-Z]\.[A-Z])")
        numbers_re = re.compile(r"#([0-9]{1,2})")
        event_players_re = re.compile(r"([A-Z]{3}\s+#[0-9]{1,2})")
        fo_team_re = re.compile(r"([A-Z]{3}) WON")
        block_team_re = re.compile(r"BLOCKED BY\s+([A-Z]{3})")
        zone_re = re.compile(r"([A-Za-z]{3}). ZONE")
        penalty_re = re.compile(r"([A-Za-z]*|[A-Za-z]*-[A-Za-z]*|[A-Za-z]*\s+\(.*\))\s*\(")
        penalty_length_re = re.compile(r"(\d+) MIN")
        shot_re = re.compile(r",\s+([A-Za-z]*|[A-Za-z]*-[A-Za-z]*)\s*,")
        distance_re = re.compile(r"(\d+) FT")
        served_re = re.compile(r"([A-Z]{3})\s.+SERVED BY: #([0-9]+)")
        drawn_re = re.compile(r"DRAWN BY: ([A-Z]{3}) #([0-9]+)")

        non_descripts = {
            "PGSTR": "PRE-GAME START",
            "PGEND": "PRE-GAME END",
            "ANTHEM": "NATIONAL ANTHEM",
            "EISTR": "EARLY INTERMISSION START",
            "EIEND": "EARLY INTERMISSION END",
            "SPC": "PUCK IN CROWD",
            "GOFF": "GAME OFFICIAL",
            "EGT": "EMERGENCY GOALTENDER",
        }

        new_team_names = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "PHX": "ARI"}
        non_team_events = ["STOP", "ANTHEM", "PGSTR", "PGEND", "PSTR", "PEND", "EISTR", "EIEND", "GEND", "SOC", "PBOX"]

        processed_events = []

        # 2. First Pass: Core Data Cleaning & Mapping
        for event in raw_events:
            if event["event"] in non_descripts:
                event["description"] = non_descripts[event["event"]]
                if event["event"] == "SPC":
                    event["event"] = "STOP"

            for old_name, new_name in new_team_names.items():
                event["description"] = event["description"].replace(old_name, new_name).upper()

            event = html_events_fixes(self.game_id, event)

            # Unified Time Parsing
            if event["event"] == "PEND" and event["time"] == "-16:0-120:00":
                goals = [x for x in raw_events if x["period"] == event["period"] and x["event"] == "GOAL"]
                if len(goals) == 0:
                    if event["period"] == 4 and self.session == "R":
                        event["time"] = event["time"].replace("-16:0-120:00", "5:000:00")
                    else:
                        event["time"] = event["time"].replace("-16:0-120:00", "20:000:00")
                else:
                    event["time"] = event["time"].replace("-16:0-120:00", goals[-1]["time"])

            event["period"] = int(event["period"])

            time_split = event["time"].split(":")
            event["period_time"] = time_split[0] + ":" + time_split[1][:2]
            event["period_seconds"] = (60 * int(event["period_time"].split(":")[0])) + int(
                event["period_time"].split(":")[1]
            )
            event["game_seconds"] = (int(event["period"]) - 1) * 1200 + event["period_seconds"]

            if event["period"] == 5 and self.session == "R":
                event["game_seconds"] = 3900 + event["period_seconds"]

            # Team Extractions
            if event["event"] not in non_team_events:
                try:
                    event["event_team"] = re.search(event_team_re, event["description"]).group(1)
                    if event["event_team"] == "LEA":
                        event["event_team"] = ""
                except AttributeError:
                    continue

            if event["event"] == "FAC":
                try:
                    event["event_team"] = re.search(fo_team_re, event["description"]).group(1)
                except AttributeError:
                    event["event_team"] = None

            if event["event"] == "BLOCK" and "BLOCKED BY" in event["description"]:
                event["event_team"] = re.search(block_team_re, event["description"]).group(1)

            # Player Identification
            if event["event"] in ["GOAL", "SHOT", "TAKE", "GIVE"]:
                event_players = [event["event_team"] + num for num in re.findall(numbers_re, event["description"])]
            else:
                event_players = re.findall(event_players_re, event["description"])

            if event["event"] == "FAC" and event_players and event["event_team"] not in event_players[0]:
                if len(event_players) > 1:
                    event_players[0], event_players[1] = event_players[1], event_players[0]

            if event["event"] == "BLOCK":
                if "TEAMMATE" in event["description"]:
                    event["event_team"] = event["description"][:3]
                    event_players.insert(0, "TEAMMATE")
                elif "BLOCKED BY OTHER" in event["description"]:
                    event["event_team"] = "OTHER"
                    event_players.insert(0, "REFEREE")
                elif event_players and event.get("event_team") not in event_players[0]:
                    if len(event_players) > 1:
                        event_players[0], event_players[1] = event_players[1], event_players[0]

            # O(1) Dictionary Lookup for Players
            for idx, event_player in enumerate(event_players):
                num = idx + 1
                event_player = event_player.replace(" #", "")

                if event_player == "TEAMMATE":
                    p_name, eh_id, pos = "TEAMMATE", "TEAMMATE", None
                elif event_player == "REFEREE":
                    p_name, eh_id, pos = "REFEREE", "REFEREE", None
                else:
                    p_info = actives.get(event_player) or scratches.get(event_player, {})
                    p_name = p_info.get("player_name", "")
                    eh_id = p_info.get("eh_id", "")
                    pos = p_info.get("position")

                event.update({f"player_{num}": p_name, f"player_{num}_eh_id": eh_id, f"player_{num}_position": pos})

            # Feature Parsing (Zone, Penalty, Shots)
            try:
                event["zone"] = re.search(zone_re, event["description"]).group(1).upper()
                if "BLOCK" in event["event"] and event["zone"] == "DEF":
                    event["zone"] = "OFF"
            except AttributeError:
                pass

            if event["event"] == "PENL":
                if ("TEAM" in event["description"] and "SERVED BY" in event["description"]) or (
                    "HEAD COACH" in event["description"]
                ):
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": None})
                    try:
                        served_by = re.search(served_re, event["description"])
                        name = served_by.group(1) + str(served_by.group(2))
                    except AttributeError:
                        try:
                            drawn_by = re.search(drawn_re, event["description"])
                            name = drawn_by.group(1) + str(drawn_by.group(2))
                        except AttributeError:
                            continue

                    p_info = actives.get(name) or scratches.get(name, {})
                    event.update(
                        {
                            "player_2": p_info.get("player_name"),
                            "player_2_eh_id": p_info.get("eh_id"),
                            "player_2_position": p_info.get("position"),
                        }
                    )

                # ... (Your existing DRAWN BY / SERVED BY nested logic remains identical here, just swapping dict lookups)
                if "SERVED BY" in event["description"] and "DRAWN BY" in event["description"]:
                    try:
                        drawn_by = re.search(drawn_re, event["description"])
                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))

                        p_info = actives.get(drawn_name) or scratches.get(drawn_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )

                        if event.get("player_1_eh_id") == event.get("player_2_eh_id"):
                            event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": None})

                        served_by = re.search(served_re, event["description"])
                        served_name = served_by.group(1) + str(served_by.group(2))

                        s_info = actives.get(served_name) or scratches.get(served_name, {})
                        event.update(
                            {
                                "player_3": s_info.get("player_name"),
                                "player_3_eh_id": s_info.get("eh_id"),
                                "player_3_position": s_info.get("position"),
                            }
                        )

                        if "TEAM" in event["description"] or "HEAD COACH" in event["description"]:
                            event["player_2"], event["player_3"] = event["player_3"], event["player_2"]
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
                        p_info = actives.get(served_name) or scratches.get(served_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )
                    except AttributeError:
                        pass
                elif "DRAWN BY" in event["description"]:
                    try:
                        drawn_by = re.search(drawn_re, event["description"])
                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))
                        p_info = actives.get(drawn_name) or scratches.get(drawn_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )
                    except AttributeError:
                        pass

                if "player_1" not in event:
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": ""})

                try:
                    event["penalty_length"] = int(re.search(penalty_length_re, event["description"]).group(1))
                except (TypeError, AttributeError):
                    pass

                try:
                    event["penalty"] = re.search(penalty_re, event["description"]).group(1).upper()
                except AttributeError:
                    pass

                # (Your specific penalty overwrites like "GOALKEEPER INTERFERENCE" go here identically)
                if event.get("penalty"):
                    desc = event["description"]
                    if "INTERFERENCE" in desc and "GOALKEEPER" in desc:
                        event["penalty"] = "GOALKEEPER INTERFERENCE"
                    elif "CROSS" in desc and "CHECKING" in desc:
                        event["penalty"] = "CROSS-CHECKING"
                    elif "DELAY" in desc and "GAME" in desc and "PUCK OVER" in desc:
                        event["penalty"] = "DELAY OF GAME - PUCK OVER GLASS"
                    elif "DELAY" in desc and "GAME" in desc and "UNSUCC" in desc:
                        event["penalty"] = "DELAY OF GAME - UNSUCCESSFUL CHALLENGE"
                    elif "GAME MISCONDUCT" in desc:
                        event["penalty"] = "GAME MISCONDUCT"
                    elif "MATCH PENALTY" in desc:
                        event["penalty"] = "MATCH PENALTY"
                    elif "GOALIE LEAVE CREASE" in desc:
                        event["penalty"] = "LEAVING THE CREASE"
                    elif "HOOKING" in desc and "BREAKAWAY" in desc:
                        event["penalty"] = "HOOKING - BREAKAWAY"
                    elif "HOLDING" in desc and "BREAKAWAY" in desc:
                        event["penalty"] = "HOLDING - BREAKAWAY"
                    elif "TEAM TOO MANY" in desc:
                        event["penalty"] = "TOO MANY MEN ON THE ICE"
                    elif "HOLDING" in desc and "STICK" in desc:
                        event["penalty"] = "HOLDING THE STICK"
                    elif "CLOSING" in desc and "HAND" in desc:
                        event["penalty"] = "CLOSING HAND ON PUCK"
                    elif "ABUSE" in desc and "OFFICIALS" in desc:
                        event["penalty"] = "ABUSE OF OFFICIALS"
                    elif "UNSPORTSMANLIKE CONDUCT" in desc:
                        event["penalty"] = "UNSPORTSMANLIKE CONDUCT"
                    elif "DELAY" in desc and "GAME" in desc:
                        event["penalty"] = "DELAY OF GAME"
                    elif event["penalty"] == "MISCONDUCT":
                        event["penalty"] = "GAME MISCONDUCT"

            if event["event"] in ["GOAL", "SHOT", "MISS", "BLOCK"]:
                try:
                    event["shot_type"] = re.search(shot_re, event["description"]).group(1).upper()
                except AttributeError:
                    event["shot_type"] = "WRIST"

                try:
                    event["pbp_distance"] = int(re.search(distance_re, event["description"]).group(1))
                except AttributeError:
                    if event["event"] in ["GOAL", "SHOT", "MISS"]:
                        event["pbp_distance"] = 0

            processed_events.append(event)

        # 3. Fast Versioning & Validation
        # We use an O(1) dictionary tracker instead of a massive list comprehension loop
        version_tracker = {}
        final_events = []

        for event in processed_events:
            eh_id = event.get("player_1_eh_id")
            if eh_id is not None:
                # Create a unique key for simultaneous identical events
                v_key = (event["event"], event["game_seconds"], event["period"], eh_id)
                version_tracker[v_key] = version_tracker.get(v_key, 0) + 1
                event["version"] = version_tracker[v_key]
            else:
                event["version"] = 1

            final_events.append(HTMLEvent.model_validate(event).model_dump())

        return final_events

    @cached_property
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
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_rosters, self._fetch_html_events)
        raw_events = self._fetch_html_events()
        if not raw_events:
            return []

        # 2. Dependency Injection: Build O(1) lookup dictionaries via team_jersey
        actives = {
            player["team_jersey"]: player
            for player in self.rosters
            if player.get("team_jersey") and player.get("status") == "ACTIVE"
        }

        scratches = {
            player["team_jersey"]: player
            for player in self.rosters
            if player.get("team_jersey") and player.get("status") == "SCRATCH"
        }

        # 3. Transformation Worker: Pass raw data and lookups to your munge method
        final_events = self._munge_html_events(raw_events, actives, scratches)

        # 4. Sort and return
        return sorted(final_events, key=lambda k: k["event_idx"])

    @property
    def html_events_df(self) -> pd.DataFrame | pl.DataFrame:
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
        return self._finalize_dataframe(data=self.html_events, schema=html_events_polars_schema)

    def _fetch_html_rosters(self) -> list:
        """Isolates requests and BeautifulSoup logic to extract raw player data."""
        if self._raw_html_rosters is not None:
            return self._raw_html_rosters

        try:
            page = self._requests_session.get(self.html_rosters_endpoint)
            if page.status_code == 404:
                self._raw_html_rosters = []
                return self._raw_html_rosters
            soup = BeautifulSoup(page.content.decode("ISO-8859-1"), "lxml", multi_valued_attributes=None)
        except RetryError:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        td_dict = {"align": "center", "class": ["teamHeading + border", "teamHeading + border "], "width": "50%"}
        teamsoup = soup.find_all("td", td_dict)
        if not teamsoup:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        table_dict = {
            "align": "center",
            "border": "0",
            "cellpadding": "0",
            "cellspacing": "0",
            "width": "100%",
            "xmlns:ext": False,
        }
        team_list = ["AWAY", "HOME"]
        team_names = {}
        raw_player_list = []

        # 1. Extract Team Names
        for idx, venue in enumerate(team_list):
            team_name = unidecode(teamsoup[idx].get_text().encode("latin-1").decode("utf-8")).upper()
            team_names[venue] = "ARIZONA COYOTES" if team_name == "PHOENIX COYOTES" else team_name

        all_tables = soup.find_all("table", table_dict)
        if len(all_tables) < 2:
            self._raw_html_rosters = []
            return self._raw_html_rosters

        # 2. Extract Active Players (First two tables)
        for idx, venue in enumerate(team_list):
            team_table = all_tables[idx]

            # Step A: Identify Starters
            # Use re.compile to catch "bold", "bold italic", " italic bold", etc.
            bold_tds = [
                td.get_text(separator=" ", strip=True)  # type: ignore[call-arg]
                for td in team_table.find_all("td", {"class": re.compile(r"bold", re.IGNORECASE)})
            ]

            # Safely extract every 3rd element (the player names) starting from index 2
            # This prevents numpy reshape crashes if the HTML is mangled
            starters = [bold_tds[i] for i in range(2, len(bold_tds), 3)]

            # Step B: Get ALL active players (both bold and normal text)
            all_tds = [td.get_text(separator=" ", strip=True) for td in team_table.find_all("td")]  # type: ignore[call-arg]
            if not all_tds:
                continue

            active_array = np.array(all_tds).reshape(-1, 3)

            # Skip the header row
            for row in active_array[1:]:
                headers = ["jersey", "position", "player_name"] if len(row) == 3 else ["jersey", "player_name"]
                p_dict = dict(zip(headers, row, strict=True))

                p_dict.update(
                    {
                        "team_name": team_names[venue],
                        "team_venue": venue,
                        "status": "ACTIVE",
                        "starter": 1 if p_dict.get("player_name") in starters else 0,
                    }
                )
                raw_player_list.append(p_dict)

        # 3. Extract Scratches (Tables 3 and 4, if they exist)
        if len(all_tables) > 2:
            for idx, venue in enumerate(team_list):
                if len(all_tables) > idx + 2:
                    scratch_tds = [td.get_text(separator=" ", strip=True) for td in all_tables[idx + 2].find_all("td")]  # type: ignore[call-arg]
                    if len(scratch_tds) > 1:
                        scratch_array = np.array(scratch_tds).reshape(-1, 3)[1:]
                        for row in scratch_array:
                            headers = (
                                ["jersey", "position", "player_name"] if len(row) == 3 else ["jersey", "player_name"]
                            )
                            p_dict = dict(zip(headers, row, strict=True))
                            p_dict.update(
                                {"team_name": team_names[venue], "team_venue": venue, "status": "SCRATCH", "starter": 0}
                            )
                            raw_player_list.append(p_dict)

        self._raw_html_rosters = raw_player_list
        return self._raw_html_rosters

    def _munge_single_html_player(self, raw_player: dict) -> dict:
        """Worker to clean, fix, and validate a single HTML roster record."""
        # Clean the raw player name extracted from HTML
        raw_name = raw_player.get("player_name", "").upper()

        # 1. Safely remove Captain (C) and Alternate (A) indicators
        clean_name = re.sub(r"\(\s?(.*)\)", "", raw_name)

        # 2. Clean up whitespace and encodings
        clean_name = clean_name.strip().encode("latin-1").decode("utf-8")
        raw_player["player_name"] = unidecode(clean_name)
        raw_player["position"] = raw_player.get("position")

        # Apply external edge-case fixes
        player = html_rosters_fixes(self.game_id, raw_player)

        # Build standard IDs and Team info
        player["jersey"] = int(player["jersey"])
        player["team"] = team_codes.get(player["team_name"])
        player["team_jersey"] = f"{player['team']}{player['jersey']}"

        # Get Evolving Hockey standardized name and ID
        player["player_name"], player["eh_id"] = correct_player_name(
            player_name=player["player_name"],
            season=self.season,
            player_position=player["position"],
            player_jersey=player["team_jersey"],
        )

        # Attach game context
        player.update({"season": int(self.season), "session": self.session, "game_id": self.game_id})

        return HTMLRosterPlayer.model_validate(player).model_dump()

    @cached_property
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
        raw_players = self._fetch_html_rosters()
        if not raw_players:
            return []

        # Step 2: Functional transformation and Pydantic validation
        cleaned_players = [self._munge_single_html_player(player) for player in raw_players]

        # Step 3: Sort and return
        return sorted(cleaned_players, key=lambda k: (k["team_venue"], k["status"], k["player_name"]))

    @property
    def html_rosters_df(self) -> pd.DataFrame | pl.DataFrame:
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
        return self._finalize_dataframe(data=self.html_rosters, schema=html_rosters_polars_schema)

    def _merge_pbp_events(self, html_events: list, api_events: list, changes: list) -> list:
        """O(N) Worker to merge HTML events, API events, and Line Changes with exact parity."""
        api_index = {}
        for api_ev in api_events:
            key = (api_ev["period"], api_ev["period_seconds"], api_ev["event"])
            if key not in api_index:
                api_index[key] = []
            api_index[key].append(api_ev)

        game_list = []
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

        for event in html_events:
            if event["event"] == "EGPID":
                continue

            event_data = dict(event)
            key = (event["period"], event["period_seconds"], event["event"])
            candidates = api_index.get(key, [])
            api_matches = []

            for x in candidates:
                if x["version"] != event.get("version", 1):
                    continue

                if event["event"] in non_team_events:
                    api_matches.append(x)
                elif event["event"] == "CHL" and event.get("event_team") is None:
                    api_matches.append(x)
                elif event["event"] == "CHL" and event.get("event_team") is not None:
                    if x.get("event_team") == event["event_team"]:
                        api_matches.append(x)
                elif event["event"] == "PENL":
                    if (
                        x.get("event_team") == event.get("event_team")
                        and x.get("player_1_eh_id") == event.get("player_1_eh_id")
                        and x.get("player_2_eh_id") == event.get("player_2_eh_id")
                        and x.get("player_3_eh_id") == event.get("player_3_eh_id")
                    ):
                        api_matches.append(x)
                elif event["event"] == "BLOCK" and event.get("player_1") == "TEAMMATE":
                    if x.get("event_team") == event.get("event_team"):
                        api_matches.append(x)
                else:
                    if x.get("event_team") == event.get("event_team") and x.get("player_1_eh_id") == event.get(
                        "player_1_eh_id"
                    ):
                        api_matches.append(x)

            if event["event"] == "FAC" and len(api_matches) == 0:
                api_matches = [x for x in candidates if x["version"] == event.get("version", 1)]

            if len(api_matches) == 1:
                api_match = api_matches[0]
                event_data.update(
                    {
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
                )
                if event["event"] == "BLOCK" and event.get("player_1") == "TEAMMATE":
                    event_data.update(
                        {
                            "player_1": api_match.get("player_1", event["player_1"]),
                            "player_1_eh_id": api_match.get("player_1_eh_id", event.get("player_1_eh_id")),
                            "player_1_position": api_match.get("player_1_position", event.get("player_1_position")),
                        }
                    )

            game_list.append(event_data)

        game_list.extend(changes)
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

        for event in game_list:
            event.update(
                {
                    "game_date": self.game_date,
                    "home_team": self.home_team["abbrev"],
                    "away_team": self.away_team["abbrev"],
                    "version": event.get("version", 1),
                }
            )
            event["sort_value"] = (
                event.get("event_idx")
                if (event["period"] == 5 and self.session == "R")
                else sort_dict.get(event["event"], 99)
            )

        return sorted(game_list, key=lambda k: (k["period"], k["period_seconds"], k.get("sort_value", 99)))

    def _track_pbp_state(self, merged_events: list, actives: dict) -> list:
        home_score, away_score = 0, 0
        home_on_ice, away_on_ice = {}, {}
        prev_event_type, prev_event_team = None, None
        last_fac_sec, last_fac_x, last_fac_y, last_fac_zone, last_fac_team = None, None, None, None, None

        hd1 = Polygon(np.array([[69, -9], [89, -9], [89, 9], [69, 9]]))
        hd2 = Polygon(np.array([[-69, -9], [-89, -9], [-89, 9], [-69, 9]]))
        d1 = Polygon(
            np.array(
                [[89, 9], [89, -9], [69, -22], [54, -22], [54, -9], [44, -9], [44, 9], [54, 9], [54, 22], [69, 22]]
            )
        )
        d2 = Polygon(
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

        # CACHE INITIALIZATION
        h_ice = aggregate_players([])
        a_ice = aggregate_players([])
        ice_changed = True

        for idx, event in enumerate(merged_events):
            if prev_event_type == "GOAL":
                if prev_event_team == event["home_team"]:
                    home_score += 1
                elif prev_event_team == event["away_team"]:
                    away_score += 1

            event.update(
                {
                    "home_score": home_score,
                    "away_score": away_score,
                    "home_score_diff": home_score - away_score,
                    "away_score_diff": away_score - home_score,
                    "score_state": f"{home_score}v{away_score}",
                    "score_diff": home_score - away_score,
                }
            )

            if event.get("event_team") == event["home_team"]:
                event.update({"opp_team": event["away_team"], "is_home": 1, "is_away": 0})
            elif event.get("event_team") == event["away_team"]:
                event.update({"opp_team": event["home_team"], "is_home": 0, "is_away": 1})
            else:
                event.update(
                    {"event_team": event["home_team"], "opp_team": event["away_team"], "is_home": 0, "is_away": 0}
                )

            # ICE CACHING LOGIC: Only re-aggregate if a change happens
            if event["event"] == "CHANGE":
                if event.get("change_on_jersey"):
                    for tj in str(event["change_on_jersey"]).split(", "):
                        if tj in actives:
                            if event["team_venue"] == "HOME":
                                home_on_ice[tj] = actives[tj]
                            else:
                                away_on_ice[tj] = actives[tj]
                if event.get("change_off_jersey"):
                    for tj in str(event["change_off_jersey"]).split(", "):
                        if event["team_venue"] == "HOME":
                            home_on_ice.pop(tj, None)
                        else:
                            away_on_ice.pop(tj, None)
                ice_changed = True

            if ice_changed:
                h_ice = aggregate_players(list(home_on_ice.values()))
                a_ice = aggregate_players(list(away_on_ice.values()))
                ice_changed = False

            event.update(
                {
                    "home_skaters": h_ice["ALL"]["count"] - h_ice["G"]["count"],
                    "away_skaters": a_ice["ALL"]["count"] - a_ice["G"]["count"],
                    "home_on_eh_id": h_ice["ALL"]["eh_ids"],
                    "home_on_api_id": h_ice["ALL"]["api_ids"],
                    "home_on": h_ice["ALL"]["names"],
                    "home_on_positions": h_ice["ALL"]["positions"],
                    "home_forwards_eh_id": h_ice["F"]["eh_ids"],
                    "home_forwards_api_id": h_ice["F"]["api_ids"],
                    "home_forwards": h_ice["F"]["names"],
                    "home_forwards_positions": h_ice["F"]["positions"],
                    "home_forwards_count": h_ice["F"]["count"],
                    "home_defense_eh_id": h_ice["D"]["eh_ids"],
                    "home_defense_api_id": h_ice["D"]["api_ids"],
                    "home_defense": h_ice["D"]["names"],
                    "home_defense_positions": h_ice["D"]["positions"],
                    "home_defense_count": h_ice["D"]["count"],
                    "home_goalie_eh_id": h_ice["G"]["eh_ids"],
                    "home_goalie_api_id": h_ice["G"]["api_ids"],
                    "home_goalie": h_ice["G"]["names"],
                    "away_on_eh_id": a_ice["ALL"]["eh_ids"],
                    "away_on_api_id": a_ice["ALL"]["api_ids"],
                    "away_on": a_ice["ALL"]["names"],
                    "away_on_positions": a_ice["ALL"]["positions"],
                    "away_forwards_eh_id": a_ice["F"]["eh_ids"],
                    "away_forwards_api_id": a_ice["F"]["api_ids"],
                    "away_forwards": a_ice["F"]["names"],
                    "away_forwards_positions": a_ice["F"]["positions"],
                    "away_forwards_count": a_ice["F"]["count"],
                    "away_defense_eh_id": a_ice["D"]["eh_ids"],
                    "away_defense_api_id": a_ice["D"]["api_ids"],
                    "away_defense": a_ice["D"]["names"],
                    "away_defense_positions": a_ice["D"]["positions"],
                    "away_defense_count": a_ice["D"]["count"],
                    "away_goalie_eh_id": a_ice["G"]["eh_ids"],
                    "away_goalie_api_id": a_ice["G"]["api_ids"],
                    "away_goalie": a_ice["G"]["names"],
                }
            )

            event["home_forwards_percent"] = event["home_forwards_count"] / max(1, event["home_skaters"])
            event["away_forwards_percent"] = event["away_forwards_count"] / max(1, event["away_skaters"])

            h_str = "E" if not event["home_goalie"] else event["home_skaters"]
            a_str = "E" if not event["away_goalie"] else event["away_skaters"]
            event["strength_state"] = f"{h_str}v{a_str}"

            if "PENALTY SHOT" in str(event.get("description", "")):
                event["strength_state"] = "1v0"
            if event["period"] == 5 and self.session == "R":
                event["strength_state"] = "1v0"
            if (event["home_skaters"] > 5 and event["home_goalie"]) or (
                event["away_skaters"] > 5 and event["away_goalie"]
            ):
                event["strength_state"] = "ILLEGAL"

            is_h_ev = event["event_team"] == event["home_team"]
            tm_pre, opp_pre = ("home", "away") if is_h_ev else ("away", "home")

            event.update(
                {
                    "event_team_skaters": event[f"{tm_pre}_skaters"],
                    "teammates_eh_id": event[f"{tm_pre}_on_eh_id"],
                    "teammates_api_id": event[f"{tm_pre}_on_api_id"],
                    "teammates": event[f"{tm_pre}_on"],
                    "teammates_positions": event[f"{tm_pre}_on_positions"],
                    "forwards_eh_id": event[f"{tm_pre}_forwards_eh_id"],
                    "forwards_api_id": event[f"{tm_pre}_forwards_api_id"],
                    "forwards": event[f"{tm_pre}_forwards"],
                    "forwards_count": event[f"{tm_pre}_forwards_count"],
                    "forwards_percent": event[f"{tm_pre}_forwards_percent"],
                    "defense_eh_id": event[f"{tm_pre}_defense_eh_id"],
                    "defense_api_id": event[f"{tm_pre}_defense_api_id"],
                    "defense": event[f"{tm_pre}_defense"],
                    "defense_count": event[f"{tm_pre}_defense_count"],
                    "own_goalie_eh_id": event[f"{tm_pre}_goalie_eh_id"],
                    "own_goalie_api_id": event[f"{tm_pre}_goalie_api_id"],
                    "own_goalie": event[f"{tm_pre}_goalie"],
                    "opp_strength_state": f"{a_str}v{h_str}" if is_h_ev else f"{h_str}v{a_str}",
                    "opp_score_state": f"{event['away_score']}v{event['home_score']}"
                    if is_h_ev
                    else f"{event['home_score']}v{event['away_score']}",
                    "opp_score_diff": event["away_score_diff"] if is_h_ev else event["home_score_diff"],
                    "opp_team_skaters": event[f"{opp_pre}_skaters"],
                    "opp_team_on_eh_id": event[f"{opp_pre}_on_eh_id"],
                    "opp_team_on_api_id": event[f"{opp_pre}_on_api_id"],
                    "opp_team_on": event[f"{opp_pre}_on"],
                    "opp_team_on_positions": event[f"{opp_pre}_on_positions"],
                    "opp_forwards_eh_id": event[f"{opp_pre}_forwards_eh_id"],
                    "opp_forwards_api_id": event[f"{opp_pre}_forwards_api_id"],
                    "opp_forwards": event[f"{opp_pre}_forwards"],
                    "opp_forwards_count": event[f"{opp_pre}_forwards_count"],
                    "opp_forwards_percent": event[f"{opp_pre}_forwards_percent"],
                    "opp_defense_eh_id": event[f"{opp_pre}_defense_eh_id"],
                    "opp_defense_api_id": event[f"{opp_pre}_defense_api_id"],
                    "opp_defense": event[f"{opp_pre}_defense"],
                    "opp_defense_count": event[f"{opp_pre}_defense_count"],
                    "opp_goalie_eh_id": event[f"{opp_pre}_goalie_eh_id"],
                    "opp_goalie_api_id": event[f"{opp_pre}_goalie_api_id"],
                    "opp_goalie": event[f"{opp_pre}_goalie"],
                }
            )
            if event.get("opp_strength_state") is None and event["strength_state"] == "ILLEGAL":
                event["opp_strength_state"] = "ILLEGAL"

            event["danger"], event["high_danger"] = 0, 0
            if event.get("coords_x") is not None and event.get("coords_y") is not None and event["coords_x"] != "":
                cx, cy = event["coords_x"], event["coords_y"]
                is_fen = event["event"] in ["GOAL", "SHOT", "MISS"]
                bad_s = event.get("shot_type", "WRIST") not in [
                    "TIP-IN",
                    "WRAP-AROUND",
                    "WRAP",
                    "DEFLECTED",
                    "BAT",
                    "BETWEEN LEGS",
                    "POKE",
                ]

                if is_fen and event.get("pbp_distance", 0) > 89 and bad_s and event.get("zone") != "OFF":
                    mx = abs(cx) + 89 if cx < 0 else cx + 89
                    event["event_distance"] = (mx**2 + cy**2) ** 0.5
                    event["event_angle"] = np.degrees(abs(np.arctan(cy / mx))) if mx != 0 else 90
                else:
                    event["event_distance"] = ((89 - abs(cx)) ** 2 + cy**2) ** 0.5
                    event["event_angle"] = (
                        np.degrees(abs(np.arctan(cy / (89 - abs(cx))))) if (89 - abs(cx)) != 0 else 90
                    )

                if is_fen and event.get("zone") == "DEF" and event.get("event_distance", 0) <= 64:
                    event["zone"] = "OFF"

                if is_fen and event.get("zone") == "OFF":
                    pt = Point(cx, cy)
                    if hd1.contains(pt) or hd2.contains(pt):
                        event["high_danger"] = 1
                    elif d1.contains(pt) or d2.contains(pt):
                        event["danger"] = 1

            if event["event"] == "FAC":
                last_fac_sec, last_fac_x, last_fac_y = (
                    event["game_seconds"],
                    event.get("coords_x"),
                    event.get("coords_y"),
                )
                last_fac_zone, last_fac_team = event.get("zone"), event.get("event_team")

            if event["event"] == "CHANGE":
                if last_fac_sec == event["game_seconds"]:
                    event["coords_x"], event["coords_y"] = last_fac_x, last_fac_y
                    event["zone_start"] = (
                        last_fac_zone
                        if event["event_team"] == last_fac_team
                        else {"OFF": "DEF", "DEF": "OFF", "NEU": "NEU"}.get(last_fac_zone)
                    )
                else:
                    event["zone_start"] = "OTF"

            for d in ["block", "change", "chl", "fac", "give", "goal", "hit", "miss", "penl", "shot", "stop", "take"]:
                event[d] = 1 if event["event"].lower() == d else 0

            event["shot"] = 1 if event["event"] in ["GOAL", "SHOT"] else 0
            event["fenwick"] = 1 if event["event"] in ["GOAL", "SHOT", "MISS"] else 0
            event["corsi"] = 1 if event["event"] in ["GOAL", "SHOT", "MISS", "BLOCK"] else 0

            event["hd_goal"] = 1 if event["goal"] and event["high_danger"] else 0
            event["hd_shot"] = 1 if event["shot"] and event["high_danger"] else 0
            event["hd_miss"] = 1 if event["miss"] and event["high_danger"] else 0
            event["hd_fenwick"] = 1 if event["fenwick"] and event["high_danger"] else 0

            event["ozf"] = 1 if event["event"] == "FAC" and event.get("zone") == "OFF" else 0
            event["dzf"] = 1 if event["event"] == "FAC" and event.get("zone") == "DEF" else 0
            event["nzf"] = 1 if event["event"] == "FAC" and event.get("zone") == "NEU" else 0

            z_start = event.get("zone_start")
            event["ozc"] = 1 if event["event"] == "CHANGE" and z_start == "OFF" else 0
            event["dzc"] = 1 if event["event"] == "CHANGE" and z_start == "DEF" else 0
            event["nzc"] = 1 if event["event"] == "CHANGE" and z_start == "NEU" else 0
            event["otf"] = 1 if event["event"] == "CHANGE" and z_start == "OTF" else 0

            for p_len in [0, 2, 4, 5, 10]:
                event[f"pen{p_len}"] = 1 if event["event"] == "PENL" and event.get("penalty_length") == p_len else 0

            if event["event"] == "BLOCK" and "BLOCKED BY TEAMMATE" in str(event.get("description", "")):
                event["teammate_block"], event["block"] = 1, 0
            else:
                event["teammate_block"] = 0

            event["event_idx"] = idx + 1
            nxt_idx = min(idx + 1, len(merged_events) - 1)
            event["event_length"] = merged_events[nxt_idx]["game_seconds"] - event["game_seconds"]
            event["id"] = int(f"{self.game_id}{event['event_idx']:04d}")

            prev_event_type, prev_event_team = event["event"], event["event_team"]

        return merged_events

    def _calculate_pbp_xg(self, events: list) -> tuple:
        """Finalized xG Worker: O(N) sequential calculation. Refactored for maximum readability and streamlined dictionary mapping."""
        # --- 1. Configuration & Constants ---
        model_groups = {
            "even": {"5v5", "4v4", "3v3"},
            "powerplay": {"5v4", "4v3", "5v3"},
            "shorthanded": {"4v5", "3v4", "3v5"},
            "empty_for": {"Ev5", "Ev4", "Ev3"},
            "empty_against": {"5vE", "4vE", "3vE"},
        }

        group_to_model = {
            "even": self._es_model,
            "powerplay": self._pp_model,
            "shorthanded": self._sh_model,
            "empty_for": self._ef_model,
            "empty_against": self._ea_model,
        }

        base_columns = [
            "season",
            "period",
            "period_seconds",
            "score_diff",
            "danger",
            "high_danger",
            "event_distance",
            "event_angle",
            "is_home",
            "position_f",
            "position_d",
            "position_g",
            "seconds_since_last",
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
            "is_rebound",
            "rush_attempt",
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

        valid_shots = {
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
        }
        valid_priors = {"SHOT", "MISS", "BLOCK", "GIVE", "TAKE", "HIT"}
        important_events = {"SHOT", "FAC", "HIT", "BLOCK", "MISS", "GIVE", "TAKE", "GOAL"}
        fenwick_events = {"GOAL", "SHOT", "MISS"}

        # --- Pass 1: Feature construction + collect pending predictions (sequential: last_xg_ev state) ---
        pending: dict[str, list] = {group: [] for group in group_to_model}
        last_xg_ev = None

        for play_idx, play in enumerate(events):
            play["pred_goal"] = 0.0

            # Sanitization & Eligibility
            raw_shot = play.get("shot_type") or ""
            s_type = raw_shot.lower().replace("-", "_").replace(" ", "_")
            if s_type not in valid_shots:
                s_type = "wrist"

            is_xg_eligible = (
                play["event"] in important_events
                and play.get("strength_state") not in {"1v0", "EvE", "ILLEGAL"}
                and play.get("coords_x") is not None
                and play["coords_x"] != ""
            )

            if is_xg_eligible:
                # Feature Construction
                xg = {col: 0 for col in base_columns}
                xg.update(
                    {
                        "season": self.season,
                        "period": play["period"],
                        "period_seconds": play["period_seconds"],
                        "score_diff": max(-4, min(4, play.get("score_diff", 0))),
                        "danger": play.get("danger", 0),
                        "high_danger": play.get("high_danger", 0),
                        "event_distance": play.get("event_distance", 0.0),
                        "event_angle": play.get("event_angle", 0.0),
                        "is_home": play.get("is_home", 0),
                    }
                )

                pos = play.get("player_1_position")
                if pos in {"L", "C", "R", "F"}:
                    xg["position_f"] = 1
                elif pos == "D":
                    xg["position_d"] = 1
                elif pos == "G":
                    xg["position_g"] = 1

                if s_type:
                    xg[s_type] = 1

                if last_xg_ev and last_xg_ev["period"] == play["period"]:
                    sec_since = play["game_seconds"] - last_xg_ev["game_seconds"]
                    s_tm = play["event_team"] == last_xg_ev["event_team"]
                    l_ev = last_xg_ev["event"]

                    xg.update(
                        {
                            "seconds_since_last": sec_since,
                            "distance_from_last": (
                                (play["coords_x"] - last_xg_ev["coords_x"]) ** 2
                                + (play["coords_y"] - last_xg_ev["coords_y"]) ** 2
                            )
                            ** 0.5,
                            "prior_face": 1 if l_ev == "FAC" else 0,
                            "is_rebound": 1
                            if (l_ev in {"SHOT", "MISS", "BLOCK"} and sec_since <= 3 and s_tm == (l_ev != "BLOCK"))
                            else 0,
                            "rush_attempt": 1 if (sec_since <= 4 and last_xg_ev.get("zone") == "NEU") else 0,
                        }
                    )

                    if l_ev in valid_priors:
                        xg[f"prior_{l_ev.lower()}_{'same' if s_tm else 'opp'}"] = 1

                ss = play.get("strength_state", "5v5")
                active_group = next((gn for gn, strs in model_groups.items() if ss in strs), None)

                if play["event"] in fenwick_events and active_group:
                    for s in model_groups[active_group]:
                        xg[f"strength_state_{s}"] = 1 if ss == s else 0

                    # Validates exact columns and strips unassigned optional strength dummies
                    val_xg = XGFields.model_validate(xg).model_dump(exclude_unset=True)
                    feature_row = np.array(list(val_xg.values()))
                    pending[active_group].append((play_idx, feature_row, s_type))

                last_xg_ev = play

        # --- Pass 2: Batched predictions per model group ---
        for group, rows in pending.items():
            if not rows:
                continue
            indices, feature_rows, s_types = zip(*rows, strict=True)
            probs = group_to_model[group].predict_proba(np.vstack(feature_rows))[:, 1]
            for _idx, prob, s_type in zip(indices, probs, s_types, strict=True):
                play_idx = int(_idx)  # zip(*rows) loses int type; re-cast explicitly
                events[play_idx]["pred_goal"] = float(prob)
                events[play_idx]["shot_type"] = s_type.upper().replace("_", "-") if s_type else "WRIST"
                calculate_score_adjustment(events[play_idx], self._score_adjustments)

        # --- Pass 3: Extended on-ice columns + schema validation ---
        final_pbp, final_ext = [], []
        for play in events:
            for (src_name, src_eh, src_api, src_pos), col_group in zip(_EXT_SOURCE_KEYS, _EXT_TARGET_KEYS, strict=True):
                players = play.get(src_name, [])
                eh_ids = play.get(src_eh, [])
                api_ids = play.get(src_api, [])
                positions = play.get(src_pos, [])
                n = len(players)
                for i, (col, col_eh, col_api, col_pos) in enumerate(col_group):
                    if i < n:
                        play[col] = players[i]
                        play[col_eh] = eh_ids[i] if i < len(eh_ids) else None
                        play[col_api] = api_ids[i] if i < len(api_ids) else None
                        play[col_pos] = positions[i] if i < len(positions) else None
                    else:
                        play[col] = play[col_eh] = play[col_api] = play[col_pos] = None

            final_pbp.append(PBPEvent.model_validate(play).model_dump())
            final_ext.append(PBPEventExt.model_validate(play).model_dump())

        return final_pbp, final_ext

    @cached_property
    def _pbp_pipeline(self) -> tuple[list, list]:
        """Hidden Master Pipeline: Orchestrates merging, state tracking, and xG calculation.

        Caches the result as a tuple to serve both PBP and Extended PBP properties instantly.
        """
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_events, self._fetch_html_rosters, self._fetch_shifts)
        api_events = self.api_events
        html_events = self.html_events
        changes = self.changes

        actives = {p["team_jersey"]: p for p in self.rosters if p.get("team_jersey") and p.get("status") == "ACTIVE"}

        if not html_events or not api_events:
            return [], []

        # 1. Pipeline Step 1: Merge
        merged_events = self._merge_pbp_events(html_events, api_events, changes)

        # 2. Pipeline Step 2: Track Game State
        stateful_events = self._track_pbp_state(merged_events, actives)

        # 3. Pipeline Step 3: Calculate xG and Validate
        final_pbp, final_ext = self._calculate_pbp_xg(stateful_events)

        return final_pbp, final_ext

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
            forwards_percent (float):
                Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions (e.g., F, C, L, R)
            opp_forwards_percent (float):
                Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed prior to next event, e.g., 5
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
            forwards_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            defense_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
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
            opp_forwards_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            opp_defense_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_forwards_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            home_forwards_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_defense_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_defense_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
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
            away_forwards_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            away_forwards_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_defense_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            away_defense_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
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
            pred_goal (float):
                xG value for a given shot attempt, e.g., 0.489021
            pred_goal_adj (float):
                Score- and venue-adjusted xG value for a given shot attempt,
                e.g., 0.489021
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            goal_adj (float):
                Score- and venue-adjusted value for a goal, e.g., 1.0
            hd_goal (int):
                Dummy indicator whether event is a high-danger goal, e.g., 0
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            shot_adj (float):
                Score- and venue-adjusted value for a shot, e.g., 1.0
            hd_shot (int):
                Dummy indicator whether event is a high-danger shot, e.g., 0
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            miss_adj (float):
                Score- and venue-adjusted value for a missed shot, e.g., 0.0
            hd_miss (int):
                Dummy indicator whether event is a high-danger missed shot, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            fenwick_adj (float):
                Score- and venue-adjusted value for a fenwick event, e.g., 1.0
            hd_fenwick (int):
                Dummy indicator whether event is a high-danger fenwick event, e.g., 0
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            corsi_adj (float):
                Score- and venue-adjusted value for a corsi event, e.g., 1.0
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            block_adj (float):
                Score- and venue-adjusted value for a blocked shot, e.g., 0.0
            teammate_block (int):
                Dummy indicator whether event is a shot blocked by a teammate, e.g., 0
            teammate_block_adj (float):
                Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0
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
        return self._pbp_pipeline[0]

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
        return self._pbp_pipeline[1]

    @property
    def play_by_play_df(self) -> pd.DataFrame | pl.DataFrame:
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
            forwards_percent (float):
                Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions (e.g., F, C, L, R)
            opp_forwards_percent (float):
                Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            event_length (int):
                Time elapsed prior to next event, e.g., 5
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
            forwards_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            defense (list | str | None):
                Name of event team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            defense_eh_id (list | str | None):
                Evolving Hockey IDs of event team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            defense_api_id (list | str | None):
                NHL API IDs of event team's skaters on-ice, e.g., 8475218, 8474600
            defense_count (int):
                Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
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
            opp_forwards_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            opp_defense (list | str | None):
                Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            opp_defense_eh_id (list | str | None):
                Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            opp_defense_api_id (list | str | None):
                NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979
            opp_defense_count (int):
                Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_forwards (list | str | None):
                Name of home team's forwards on-ice, e.g.,
                ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
            home_forwards_eh_id (list | str | None):
                Evolving Hockey IDs of home team's forwards on-ice, e.g.,
                ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
            home_forwards_api_id (list | str | None = None):
                NHL API IDs of home team's forwards on-ice, e.g.,
                8479337, 8473604, 8481523, 8474141
            home_forwards_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            home_forwards_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            home_defense (list | str | None):
                Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON
            home_defense_eh_id (list | str | None):
                Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
            home_defense_api_id (list | str | None):
                NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979
            home_defense_count (int):
                Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            home_defense_percent (float):
                Percentage of home skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
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
            away_forwards_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play forward positions
                (e.g., F, C, L, R)
            away_forwards_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions
                (e.g., F, C, L, R)
            away_defense (list | str | None):
                Name of away team's defense on-ice, e.g., MATTIAS EKHOLM, ROMAN JOSI
            away_defense_eh_id (list | str | None):
                Evolving Hockey IDs of away team's defense on-ice, e.g., MATTIAS.EKHOLM, ROMAN.JOSI
            away_defense_api_id (list | str | None):
                NHL API IDs of away team's skaters on-ice, e.g., 8475218, 8474600
            away_defense_count (int):
                Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (e.g., D)
            away_defense_percent (float):
                Percentage of away skaters (i.e., excluding goalies) on-ice that play defensive positions (e.g., D)
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
            pred_goal (float):
                xG value for a given shot attempt, e.g., 0.489021
            pred_goal_adj (float):
                Score- and venue-adjusted xG value for a given shot attempt,
                e.g., 0.489021
            goal (int):
                Dummy indicator whether event is a goal, e.g., 1
            goal_adj (float):
                Score- and venue-adjusted value for a goal, e.g., 1.0
            hd_goal (int):
                Dummy indicator whether event is a high-danger goal, e.g., 0
            shot (int):
                Dummy indicator whether event is a shot, e.g., 1
            shot_adj (float):
                Score- and venue-adjusted value for a shot, e.g., 1.0
            hd_shot (int):
                Dummy indicator whether event is a high-danger shot, e.g., 0
            miss (int):
                Dummy indicator whether event is a miss, e.g., 0
            miss_adj (float):
                Score- and venue-adjusted value for a missed shot, e.g., 0.0
            hd_miss (int):
                Dummy indicator whether event is a high-danger missed shot, e.g., 0
            fenwick (int):
                Dummy indicator whether event is a fenwick event, e.g., 1
            fenwick_adj (float):
                Score- and venue-adjusted value for a fenwick event, e.g., 1.0
            hd_fenwick (int):
                Dummy indicator whether event is a high-danger fenwick event, e.g., 0
            corsi (int):
                Dummy indicator whether event is a corsi event, e.g., 1
            corsi_adj (float):
                Score- and venue-adjusted value for a corsi event, e.g., 1.0
            block (int):
                Dummy indicator whether event is a block, e.g., 0
            block_adj (float):
                Score- and venue-adjusted value for a blocked shot, e.g., 0.0
            teammate_block (int):
                Dummy indicator whether event is a shot blocked by a teammate, e.g., 0
            teammate_block_adj (float):
                Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0
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
        return self._finalize_dataframe(data=self.play_by_play, schema=pbp_polars_schema)

    def _combine_rosters(self) -> list:
        """Combine API and HTML rosters into a unified list.

        Called internally by the rosters cached property.

        Examples:
            >>> game = Game(2023020001)
            >>> game.rosters  # fetches and combines in one step
        """
        api_rosters = self.api_rosters
        html_rosters = self.html_rosters

        html_lookup = {player["team_jersey"]: player for player in html_rosters if player.get("team_jersey")}

        combined_roster = []
        api_jerseys = set()

        # 3. Hydrate API data with HTML statuses
        for api_player in api_rosters:
            team_jersey = api_player["team_jersey"]
            api_jerseys.add(team_jersey)

            merged_player = api_player.copy()

            html_match = html_lookup.get(team_jersey)
            merged_player["team_name"] = html_match.get("team_name")
            merged_player["status"] = html_match.get("status", "UNKNOWN")
            merged_player["starter"] = html_match.get("starter", 0)

            combined_roster.append(rosters_fixes(self.game_id, merged_player))

        # 4. Catch players found ONLY in the HTML report (e.g., EBUGs)
        for html_player in html_rosters:
            if html_player["team_jersey"] not in api_jerseys:
                new_player = html_player.copy()
                new_player["api_id"] = None
                new_player["headshot_url"] = None
                combined_roster.append(new_player)

        return combined_roster

    @cached_property
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
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_rosters)
        combined_and_fixed = self._combine_rosters()

        # 2. Final Pydantic validation
        final = [RosterPlayer.model_validate(player).model_dump() for player in combined_and_fixed]

        # 3. Sort and return
        return sorted(final, key=lambda k: (k["team_venue"], k["status"], k["player_name"]))

    @property
    def rosters_df(self) -> pl.DataFrame:
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
        return self._finalize_dataframe(data=self.rosters, schema=rosters_polars_schema)

    def _parse_team_shifts(self, team_venue: str, response) -> list:
        """Parse shift data for a single team (HOME or AWAY) from an already-fetched response."""
        team_shifts = []

        soup = BeautifulSoup(response.content.decode("ISO-8859-1"), "lxml", multi_valued_attributes=None)

        team_name_td = soup.find("td", {"align": "center", "class": "teamHeading + border"})
        if not team_name_td:
            return team_shifts

        team_name = unidecode(team_name_td.get_text())
        if team_name == "PHOENIX COYOTES":
            team_name = "ARIZONA COYOTES"
        elif "CANADIENS" in team_name:
            team_name = "MONTREAL CANADIENS"

        players = soup.find_all("td", {"class": ["playerHeading + border", "lborder + bborder"]})
        players_dict = {}
        full_name = " "
        eh_id = None

        for player in players:
            data = player.get_text()
            if ", " in data:
                name = data.split(",", 1)
                last_name = name[0].split(" ", 1)[1].strip()
                first_name = re.sub(r"\(\s?(.+)\)", "", name[1]).strip()
                full_name = f"{first_name} {last_name}"

                if full_name == " ":
                    continue

                jersey = int(name[0].split(" ")[0].strip())
                full_name, eh_id = correct_player_name(player_name=full_name, season=self.season, player_jersey=jersey)
                players_dict[eh_id] = {"player_name": full_name, "eh_id": eh_id, "jersey": jersey, "shifts": []}
            else:
                if eh_id is not None and full_name != " ":
                    players_dict[eh_id]["shifts"].extend([data])

        for player, shifts in players_dict.items():
            length = int(len(np.array(shifts["shifts"])) / 5)
            player_name = shifts["player_name"]
            eh_id = shifts["eh_id"]
            team = team_codes.get(team_name, "")
            team_venue_name = team_venue.upper()
            team_jersey = f"{team}{shifts['jersey']}"
            jersey = int(shifts["jersey"])

            for _number, shift in enumerate(np.array(shifts["shifts"]).reshape(length, 5)):
                headers = ["shift_count", "period", "shift_start", "shift_end", "duration"]
                shift_dict = dict(zip(headers, shift.flatten(), strict=True))
                shift_dict = shifts_fixes(game_id=self.game_id, player_name=player_name, shift_dict=shift_dict)

                shift_dict.update(
                    {
                        "season": self.season,
                        "session": self.session,
                        "game_id": self.game_id,
                        "team_name": team_name,
                        "team": team,
                        "team_venue": team_venue_name,
                        "player_name": player_name,
                        "eh_id": eh_id,
                        "team_jersey": team_jersey,
                        "jersey": jersey,
                        "period": int(shift_dict["period"].replace("OT", "4").replace("SO", "5")),
                        "shift_count": int(shift_dict["shift_count"]),
                        "shift_start": unidecode(shift_dict["shift_start"]).strip(),
                        "start_time": unidecode(shift_dict["shift_start"]).strip().split("/", 1)[0].strip(),
                        "shift_end": unidecode(shift_dict["shift_end"]).strip(),
                        "end_time": unidecode(shift_dict["shift_end"]).strip().split("/", 1)[0].strip(),
                    }
                )

                if shift_dict["start_time"] != "31:23":
                    team_shifts.append(shift_dict)

        return team_shifts

    def _fetch_shifts(self) -> list:
        """Fetch shift data for HOME and AWAY teams.

        Fetches both team URLs concurrently (I/O only, GIL released during network wait),
        then parses the responses sequentially (CPU-bound BeautifulSoup, no threading).
        """
        if self._raw_shifts is not None:
            return self._raw_shifts

        endpoints = {"HOME": self.home_shifts_endpoint, "AWAY": self.away_shifts_endpoint}

        # Phase 1: concurrent HTTP fetch — I/O-bound, releases GIL during socket reads
        responses: dict = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(self._requests_session.get, url): venue for venue, url in endpoints.items()}
            for future in as_completed(futures):
                venue = futures[future]
                try:
                    responses[venue] = future.result()
                except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                    pass

        # Phase 2: sequential parse — CPU-bound, runs in this thread only
        game_list = []
        for venue, response in responses.items():
            try:
                game_list.extend(self._parse_team_shifts(venue, response))
            except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                continue

        self._raw_shifts = game_list
        return self._raw_shifts

    def _munge_shifts(self, raw_shifts: list, actives: dict, scratches: dict) -> list:
        """Transform raw shift data into structured shift dicts.

        Called internally by the shifts cached property.

        Examples:
            >>> game = Game(2023020001)
            >>> game.shifts  # fetches and processes in one step
        """
        # 1. Edge Case Pre-Injection: Add Game 2020020860 manual shifts before mapping begins
        if self.game_id == 2020020860:
            new_shifts_data = {
                "DAL29": 5,
                "CHI60": 4,
                "DAL14": 27,
                "DAL21": 22,
                "DAL3": 28,
                "CHI5": 27,
                "CHI88": 26,
                "CHI12": 26,
            }
            for new_player, shift_count in new_shifts_data.items():
                player_info = actives.get(new_player) or scratches.get(new_player)
                if not player_info:
                    continue
                start_time, end_time, duration, shift_start, shift_end = (
                    ("0:00", "4:30", "4:30", "0:00 / 5:00", "4:30 / 0:30")
                    if new_player in ["DAL29", "CHI60"]
                    else ("3:47", "4:30", "00:43", "3:47 / 1:13", "4:30 / 0:30")
                    if new_player in ["DAL14", "DAL21", "DAL3", "CHI5"]
                    else ("3:51", "4:30", "00:39", "3:51 / 1:09", "4:30 / 0:30")
                    if new_player == "CHI88"
                    else ("4:14", "4:30", "00:16", "4:14 / 0:46", "4:30 / 0:30")
                )

                raw_shifts.append(
                    {
                        "shift_count": shift_count,
                        "period": 4,
                        "shift_start": shift_start,
                        "shift_end": shift_end,
                        "duration": duration,
                        "season": self.season,
                        "session": self.session,
                        "game_id": self.game_id,
                        "team_name": player_info.get("team_name"),
                        "team": player_info.get("team"),
                        "team_venue": player_info.get("team_venue"),
                        "player_name": player_info.get("player_name"),
                        "team_jersey": player_info.get("team_jersey"),
                        "jersey": player_info.get("jersey"),
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                )
        period_shifts = {}
        period_max_seconds = {}
        team_goalies = {"HOME": {}, "AWAY": {}}

        # 2. Pass 1: Map Metadata, Clean Strings, Parse Times, and Track Period Data in O(N)
        for shift in raw_shifts:
            team_jersey = shift.get("team_jersey", "")
            player_info = actives.get(team_jersey) or scratches.get(team_jersey, {})

            # Hydrate Data
            shift["eh_id"] = player_info.get("eh_id", shift.get("eh_id"))
            shift["api_id"] = player_info.get("api_id")
            shift["position"] = player_info.get("position")
            shift["goalie"] = 1 if shift["position"] == "G" else 0
            shift["is_home"] = 1 if shift.get("team_venue") == "HOME" else 0
            shift["is_away"] = 1 if shift.get("team_venue") == "AWAY" else 0

            # Clean Names
            player_name = (
                shift.get("player_name", "")
                .replace("ALEXANDRE", "ALEX")
                .replace("ALEXANDER", "ALEX")
                .replace("CHRISTOPHER", "CHRIS")
            )
            shift["player_name"] = correct_names_dict.get(player_name, player_name)

            # Fast Time Parsing (Restored your original 'continue' logic to prevent bad data)
            for col in ["start_time", "end_time", "duration"]:
                t_str = shift.get(col, "")
                if ":" not in t_str:
                    continue
                ts = t_str.split(":", 1)
                try:
                    shift[f"{col}_seconds"] = 60 * int(ts[0]) + int(ts[1])
                except ValueError:
                    continue

            # Base Clock Fixes
            if not shift.get("end_time") or shift["end_time"].strip() == "":
                shift["end_time_seconds"] = shift.get("start_time_seconds", 0) + shift.get("duration_seconds", 0)
                shift["end_time"] = str(timedelta(seconds=shift.get("end_time_seconds"))).split(":", 1)[1]

            if shift["start_time_seconds"] > shift["end_time_seconds"] and shift["period"] < 4:
                shift.update(
                    {
                        "end_time": "20:00",
                        "end_time_seconds": 1200,
                        "shift_end": "20:00 / 0:00",
                        "duration_seconds": 1200 - shift["start_time_seconds"],
                    }
                )
                shift["duration"] = str(timedelta(seconds=shift["duration_seconds"])).split(":", 1)[1]

            p = shift.get("period", 1)
            if p not in period_shifts:
                period_shifts[p] = []
                period_max_seconds[p] = 0
                team_goalies["HOME"][p] = []
                team_goalies["AWAY"][p] = []

            period_shifts[p].append(shift)

            # Track max seconds dynamically
            end_sec = shift.get("end_time_seconds", 0)
            if end_sec > period_max_seconds[p]:
                period_max_seconds[p] = end_sec

            if shift["goalie"] == 1:
                team_goalies[shift["team_venue"]][p].append(shift)

        # 3. Preparation for Pass 2: Global Context
        if not period_shifts:
            return []

        final_shifts = []

        # 4. Pass 2: Apply period-dependent fixes using the grouped dictionaries
        for period, shifts in sorted(period_shifts.items()):
            max_seconds = period_max_seconds[period]
            expected_total_seconds = 1200 if (period < 4 or self.session == "P") else 300

            # A. Unified Fix for Broken Clocks & Missing Goalie Shift Ends
            for shift in shifts:
                start_seconds = shift.get("start_time_seconds", 0)
                end_seconds = shift.get("end_time_seconds", 0)

                needs_clock_fix = start_seconds > end_seconds
                needs_goalie_fix = shift["goalie"] == 1 and (
                    not shift.get("shift_end") or shift["shift_end"] == "0:00 / 0:00"
                )

                if needs_clock_fix or needs_goalie_fix:
                    if max_seconds < expected_total_seconds:
                        # Period ended early, cap shift at max_sec
                        end_time = f"{max_seconds // 60}:{max_seconds % 60:02d}"
                        remaining_seconds = expected_total_seconds - max_seconds
                        remaining_time = f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}"
                        shift.update(
                            {
                                "end_time_seconds": max_seconds,
                                "end_time": end_time,
                                "shift_end": f"{end_time} / {remaining_time}",
                            }
                        )
                    else:
                        # Period went the full length
                        end_time = "20:00" if expected_total_seconds == 1200 else "5:00"
                        shift.update(
                            {
                                "end_time_seconds": expected_total_seconds,
                                "end_time": end_time,
                                "shift_end": f"{end_time} / 0:00",
                            }
                        )

                    # Recalculate duration perfectly
                    shift["duration_seconds"] = shift["end_time_seconds"] - start_seconds
                    shift["duration"] = f"{shift['duration_seconds'] // 60}:{shift['duration_seconds'] % 60:02d}"

                final_shifts.append(PlayerShift.model_validate(shift).model_dump())

            # B. Inject Missing Goalies instantly using the dictionary
            for team in ["HOME", "AWAY"]:
                if len(team_goalies[team][period]) < 1:
                    base_goalie = None

                    if period == 1:
                        base_goalie = next(
                            (
                                x
                                for x in actives.values()
                                if x.get("position") == "G" and x.get("team_venue") == team and x.get("starter") == 1
                            ),
                            None,
                        )
                        if not base_goalie:
                            for p_idx in sorted(period_shifts.keys()):
                                if team_goalies[team].get(p_idx):
                                    base_goalie = team_goalies[team][p_idx][0]
                                    break
                    else:
                        prev_goalies = team_goalies[team].get(period - 1)
                        if prev_goalies:
                            base_goalie = prev_goalies[-1]

                    if base_goalie:
                        g_shift = dict(base_goalie)
                        g_shift.update(
                            {
                                "season": self.season,
                                "session": self.session,
                                "game_id": self.game_id,
                                "period": period,
                                "team_venue": team,
                                "goalie": 1,
                                "shift_count": 1,
                                "is_home": 1 if team == "HOME" else 0,
                                "is_away": 1 if team == "AWAY" else 0,
                                "number": 0,
                                "start_time": "0:00",
                                "start_time_seconds": 0,
                            }
                        )

                        g_shift["shift_start"] = "0:00 / 20:00" if expected_total_seconds == 1200 else "0:00 / 5:00"

                        if max_seconds < expected_total_seconds:
                            end_time = f"{max_seconds // 60}:{max_seconds % 60:02d}"
                            remaining_seconds = expected_total_seconds - max_seconds
                            remaining_time = f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}"

                            g_shift.update(
                                {
                                    "end_time_seconds": max_seconds,
                                    "end_time": end_time,
                                    "duration_seconds": max_seconds,
                                    "duration": end_time,
                                    "shift_end": f"{end_time} / {remaining_time}",
                                }
                            )
                        else:
                            end_time = "20:00" if expected_total_seconds == 1200 else "5:00"

                            g_shift.update(
                                {
                                    "end_time_seconds": expected_total_seconds,
                                    "end_time": end_time,
                                    "duration_seconds": expected_total_seconds,
                                    "duration": end_time,
                                    "shift_end": f"{end_time} / 0:00",
                                }
                            )

                        final_shifts.append(PlayerShift.model_validate(g_shift).model_dump())

        return final_shifts

    @cached_property
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
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_rosters, self._fetch_shifts)
        raw_shifts = self._fetch_shifts()
        if not raw_shifts:
            return []

        # 2. Trigger Dependencies
        # Corrected: Build the lookup dictionary using team_jersey (e.g., 'NSH59')
        actives = {
            player["team_jersey"]: player
            for player in self.rosters
            if player.get("team_jersey") and player.get("status") == "ACTIVE"
        }

        scratches = {
            player["team_jersey"]: player
            for player in self.rosters
            if player.get("team_jersey") and player.get("status") == "SCRATCH"
        }

        # 3. Functional Transformation
        # Because of the inter-shift dependencies (like finding max period time and injecting goalies),
        # we pass the entire list to a dedicated transformation worker rather than a single-shift loop.
        final_shifts = self._munge_shifts(raw_shifts, actives, scratches)

        # 4. Sort and return
        return sorted(final_shifts, key=lambda k: (k["period"], k["start_time_seconds"], k["team_venue"]))

    @property
    def shifts_df(self) -> pd.DataFrame | pl.DataFrame:
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

        return self._finalize_dataframe(data=self.shifts, schema=shifts_polars_schema)
