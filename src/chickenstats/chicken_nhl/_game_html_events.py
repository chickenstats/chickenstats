from __future__ import annotations

from functools import cached_property
import re
from typing import TYPE_CHECKING

import numpy as np
import polars as pl

if TYPE_CHECKING:
    import pandas as pd
from bs4 import BeautifulSoup
from requests.exceptions import RetryError
from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import html_events_fixes
from chickenstats.chicken_nhl._game_utils import hs_strip_html, prefetch_concurrent
from chickenstats.chicken_nhl.validation_pydantic import HTMLEvent
from chickenstats.chicken_nhl.validation_polars import html_events_polars_schema
from chickenstats.chicken_nhl._docstrings import _GAME_HTML_EVENTS_DF_DOC, _GAME_HTML_EVENTS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import _GameBase


class _GameHTMLEventsMixin(_GameBase):
    def _fetch_html_events(self) -> list:
        """Fetch and cache raw HTML play-by-play events on ``self._raw_html_events``.

        Idempotent. Returns an empty list if the endpoint is unreachable or empty.
        """
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
        """Worker method to transform raw HTML events into structured event dicts."""
        # Compile regexes once
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

        # Core cleaning & mapping
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
                if (_m := re.search(event_team_re, event["description"])) is None:
                    continue
                event["event_team"] = _m.group(1)
                if event["event_team"] == "LEA":
                    event["event_team"] = ""

            if event["event"] == "FAC":
                _m = re.search(fo_team_re, event["description"])
                event["event_team"] = _m.group(1) if _m is not None else None

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
            if (_m := re.search(zone_re, event["description"])) is not None:
                event["zone"] = _m.group(1).upper()
                if "BLOCK" in event["event"] and event["zone"] == "DEF":
                    event["zone"] = "OFF"

            if event["event"] == "PENL" or event["event"] == "DELPEN":
                if ("TEAM" in event["description"] and "SERVED BY" in event["description"]) or (
                    "HEAD COACH" in event["description"]
                ):
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": None})
                    served_by = re.search(served_re, event["description"])
                    drawn_by = re.search(drawn_re, event["description"])
                    if served_by is not None:
                        name = served_by.group(1) + str(served_by.group(2))
                    elif drawn_by is not None:
                        name = drawn_by.group(1) + str(drawn_by.group(2))
                    else:
                        continue

                    p_info = actives.get(name) or scratches.get(name, {})
                    event.update(
                        {
                            "player_2": p_info.get("player_name"),
                            "player_2_eh_id": p_info.get("eh_id"),
                            "player_2_position": p_info.get("position"),
                        }
                    )

                if "SERVED BY" in event["description"] and "DRAWN BY" in event["description"]:
                    if (drawn_by := re.search(drawn_re, event["description"])) is not None:
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

                        if (served_by := re.search(served_re, event["description"])) is not None:
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
                elif "SERVED BY" in event["description"]:
                    if (served_by := re.search(served_re, event["description"])) is not None:
                        served_name = served_by.group(1) + str(served_by.group(2))
                        p_info = actives.get(served_name) or scratches.get(served_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )
                elif "DRAWN BY" in event["description"]:
                    if (drawn_by := re.search(drawn_re, event["description"])) is not None:
                        drawn_name = drawn_by.group(1) + str(drawn_by.group(2))
                        p_info = actives.get(drawn_name) or scratches.get(drawn_name, {})
                        event.update(
                            {
                                "player_2": p_info.get("player_name"),
                                "player_2_eh_id": p_info.get("eh_id"),
                                "player_2_position": p_info.get("position"),
                            }
                        )

                if "player_1" not in event and event["event"] == "PENL":
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": ""})

                if (_m := re.search(penalty_length_re, event["description"])) is not None:
                    try:
                        event["penalty_length"] = int(_m.group(1))
                    except TypeError:
                        pass

                if (_m := re.search(penalty_re, event["description"])) is not None:
                    event["penalty"] = _m.group(1).upper()

                # Hand-curated overwrites for penalty descriptions that need normalizing.
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
                if (_m := re.search(shot_re, event["description"])) is not None:
                    event["shot_type"] = _m.group(1).upper()
                else:
                    event["shot_type"] = "WRIST"

                if (_m := re.search(distance_re, event["description"])) is not None:
                    event["pbp_distance"] = int(_m.group(1))
                elif event["event"] in ["GOAL", "SHOT", "MISS"]:
                    event["pbp_distance"] = 0

            processed_events.append(event)

        # Versioning & validation
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
    @shared_doc(_GAME_HTML_EVENTS_DOC)
    def html_events(self) -> list:
        """html_events — docstring lives in _docstrings._GAME_HTML_EVENTS_DOC."""
        prefetch_concurrent(
            *self._prefetch_needed(
                (self._fetch_api_data, ()),
                (self._fetch_html_rosters, ("html_rosters", "rosters")),
                (self._fetch_html_events, ("html_events",)),
            )
        )
        raw_events = self._fetch_html_events()
        if not raw_events:
            return []

        # Build O(1) lookup dicts by team_jersey
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

        final_events = self._munge_html_events(raw_events, actives, scratches)

        return sorted(final_events, key=lambda k: k["event_idx"])

    @property
    @shared_doc(_GAME_HTML_EVENTS_DF_DOC)
    def html_events_df(self) -> pd.DataFrame | pl.DataFrame:
        """html_events_df — docstring lives in _docstrings._GAME_HTML_EVENTS_DF_DOC."""
        return self._finalize_dataframe(data=self.html_events, schema=html_events_polars_schema)
