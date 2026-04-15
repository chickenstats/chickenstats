from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cached_property
import logging
import re
from datetime import timedelta
from typing import cast

import numpy as np
import pandas as pd
import polars as pl
from bs4 import BeautifulSoup
from requests.exceptions import RetryError
from unidecode import unidecode

from chickenstats.chicken_nhl._fixes import (
    html_events_fixes,
    html_rosters_fixes,
    html_shifts_fixes,
    individual_shifts_fixes,
)
from chickenstats.chicken_nhl._game_utils import aggregate_players, hs_strip_html, prefetch_concurrent
from chickenstats.chicken_nhl._player_names import correct_player_name, correct_names_dict
from chickenstats.chicken_nhl.team import team_codes
from chickenstats.chicken_nhl.validation_pydantic import ChangeEvent, HTMLEvent, HTMLRosterPlayer, PlayerShift
from chickenstats.chicken_nhl.validation_polars import (
    changes_polars_schema,
    html_events_polars_schema,
    html_rosters_polars_schema,
    shifts_polars_schema,
)
from chickenstats.chicken_nhl._game_core import _GameBase

logger = logging.getLogger(__name__)

model_version = "0.1.1"


class _GameHTMLMixin(_GameBase):
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

            # Players in both ON and OFF are data errors — drop from each to preserve prior ice state
            duplicate_jerseys = {s["team_jersey"] for s in on_players} & {s["team_jersey"] for s in off_players}
            if duplicate_jerseys:
                on_players = [s for s in on_players if s["team_jersey"] not in duplicate_jerseys]
                off_players = [s for s in off_players if s["team_jersey"] not in duplicate_jerseys]

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
        del soup
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
                    _m = re.search(event_team_re, event["description"])
                    assert _m is not None
                    event["event_team"] = _m.group(1)
                    if event["event_team"] == "LEA":
                        event["event_team"] = ""
                except (AttributeError, AssertionError):
                    continue

            if event["event"] == "FAC":
                try:
                    _m = re.search(fo_team_re, event["description"])
                    assert _m is not None
                    event["event_team"] = _m.group(1)
                except (AttributeError, AssertionError):
                    event["event_team"] = None

            if event["event"] == "BLOCK" and "BLOCKED BY" in event["description"]:
                _m = re.search(block_team_re, event["description"])
                if _m is not None:
                    event["event_team"] = _m.group(1)

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
                _m = re.search(zone_re, event["description"])
                assert _m is not None
                event["zone"] = _m.group(1).upper()
                if "BLOCK" in event["event"] and event["zone"] == "DEF":
                    event["zone"] = "OFF"
            except (AttributeError, AssertionError):
                pass

            if event["event"] == "PENL" or event["event"] == "DELPEN":
                if ("TEAM" in event["description"] and "SERVED BY" in event["description"]) or (
                    "HEAD COACH" in event["description"]
                ):
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": None})
                    try:
                        served_by = re.search(served_re, event["description"])
                        assert served_by is not None
                        name = served_by.group(1) + str(served_by.group(2))
                    except (AttributeError, AssertionError):
                        try:
                            drawn_by = re.search(drawn_re, event["description"])
                            assert drawn_by is not None
                            name = drawn_by.group(1) + str(drawn_by.group(2))
                        except (AttributeError, AssertionError):
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
                        assert drawn_by is not None
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
                        assert served_by is not None
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
                    except (AttributeError, AssertionError):
                        pass
                elif "SERVED BY" in event["description"]:
                    try:
                        served_by = re.search(served_re, event["description"])
                        assert served_by is not None
                        served_name = served_by.group(1) + str(served_by.group(2))
                        p_info = actives.get(served_name) or scratches.get(served_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )
                    except (AttributeError, AssertionError):
                        pass
                elif "DRAWN BY" in event["description"]:
                    try:
                        drawn_by = re.search(drawn_re, event["description"])
                        assert drawn_by is not None
                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))
                        p_info = actives.get(drawn_name) or scratches.get(drawn_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )
                    except (AttributeError, AssertionError):
                        pass

                if "player_1" not in event and event["event"] == "PENL":
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": ""})

                try:
                    _m = re.search(penalty_length_re, event["description"])
                    assert _m is not None
                    event["penalty_length"] = int(_m.group(1))
                except (TypeError, AttributeError, AssertionError):
                    pass

                try:
                    _m = re.search(penalty_re, event["description"])
                    assert _m is not None
                    event["penalty"] = _m.group(1).upper()
                except (AttributeError, AssertionError):
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
                    _m = re.search(shot_re, event["description"])
                    assert _m is not None
                    event["shot_type"] = _m.group(1).upper()
                except (AttributeError, AssertionError):
                    event["shot_type"] = "WRIST"

                try:
                    _m = re.search(distance_re, event["description"])
                    assert _m is not None
                    event["pbp_distance"] = int(_m.group(1))
                except (AttributeError, AssertionError):
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

        td_dict: dict = {"align": "center", "class": ["teamHeading + border", "teamHeading + border "], "width": "50%"}
        teamsoup = soup.find_all("td", cast(dict, td_dict))
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

        all_tables = soup.find_all("table", cast(dict, table_dict))
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

        del soup
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
                shift_dict = individual_shifts_fixes(
                    game_id=self.game_id, player_name=player_name, shift_dict=shift_dict
                )

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
                    logger.debug("Failed to fetch shifts for %s venue", venue, exc_info=True)

        # Phase 2: sequential parse — CPU-bound, runs in this thread only
        game_list = []
        for venue, response in responses.items():
            try:
                game_list.extend(self._parse_team_shifts(venue, response))
            except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                logger.debug("Failed to parse shifts for %s venue", venue, exc_info=True)
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
        # 1. Edge Case Pre-Injection: Add missing OT shifts for known data gaps
        raw_shifts = html_shifts_fixes(self.game_id, self.season, self.session, raw_shifts, actives, scratches)

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

            # if shift["start_time_seconds"] > shift["end_time_seconds"] and shift["period"] < 4:
            #     shift.update(
            #         {
            #             "end_time": "20:00",
            #             "end_time_seconds": 1200,
            #             "shift_end": "20:00 / 0:00",
            #             "duration_seconds": 1200 - shift["start_time_seconds"],
            #         }
            #     )
            #     shift["duration"] = str(timedelta(seconds=shift["duration_seconds"])).split(":", 1)[1]

            if shift["shift_end"] == "0:00 / 0:00":
                if shift["period"] < 4 or self.session == "P":
                    fixed_end_time = "20:00"
                    fixed_end_time_seconds = 1200
                    fixed_shift_end = "20:00 / 0:00"
                    fixed_duration_seconds = fixed_end_time_seconds - shift["duration_seconds"]

                elif shift["period"] == 4 and self.session == "R":
                    fixed_end_time = "5:00"
                    fixed_end_time_seconds = 300
                    fixed_shift_end = "5:00 / 0:00"
                    fixed_duration_seconds = fixed_end_time_seconds - shift["duration_seconds"]

                shift.update(
                    {
                        "end_time": fixed_end_time,
                        "end_time_seconds": fixed_end_time_seconds,
                        "shift_end": fixed_shift_end,
                        "duration_seconds": fixed_duration_seconds,
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
