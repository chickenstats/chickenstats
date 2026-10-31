from __future__ import annotations

from functools import cached_property
import logging
import re
from typing import TYPE_CHECKING

import numpy as np
import polars as pl

if TYPE_CHECKING:
    import pandas as pd
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import html_events_fixes
from chickenstats.chicken_nhl._game_utils import (
    format_time,
    decode_report,
    game_seconds,
    hs_strip_html,
    is_cut_off,
    period_length,
)
from chickenstats.chicken_nhl.validation_pydantic import HTMLEvent
from chickenstats.chicken_nhl.validation_polars import html_events_polars_schema
from chickenstats.chicken_nhl._docstrings import _GAME_HTML_EVENTS_DF_DOC, _GAME_HTML_EVENTS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import ENDED_STATES, _GameBase

logger = logging.getLogger(__name__)

# Regexes for the HTML event descriptions
_EVENT_TEAM_RE = re.compile(r"^([A-Z]{3}|[A-Z]\.[A-Z])")
_NUMBERS_RE = re.compile(r"#([0-9]{1,2})")
_EVENT_PLAYERS_RE = re.compile(r"([A-Z]{3}\s+#[0-9]{1,2})")
_FO_TEAM_RE = re.compile(r"([A-Z]{3}) WON")
_BLOCK_TEAM_RE = re.compile(r"BLOCKED BY\s+([A-Z]{3})")
_ZONE_RE = re.compile(r"([A-Za-z]{3}). ZONE")
_PENALTY_RE = re.compile(r"([A-Za-z]*|[A-Za-z]*-[A-Za-z]*|[A-Za-z]*\s+\(.*\))\s*\(")
_PENALTY_LENGTH_RE = re.compile(r"(\d+) MIN")
_SHOT_RE = re.compile(r",\s+([A-Za-z]*|[A-Za-z]*-[A-Za-z]*)\s*,")
_DISTANCE_RE = re.compile(r"(\d+) FT")
_SERVED_RE = re.compile(r"([A-Z]{3})\s.+SERVED BY: #([0-9]+)")
_DRAWN_RE = re.compile(r"DRAWN BY: ([A-Z]{3}) #([0-9]+)")


class _GameHTMLEventsMixin(_GameBase):
    def _fetch_html_events(self) -> list:
        """Fetch and cache raw HTML play-by-play events on ``self._raw_html_events``.

        Idempotent. Returns an empty list if the endpoint is unreachable or empty.
        """
        if self._raw_html_events is not None:
            return self._raw_html_events

        response = self._get_report(self.html_events_endpoint, "PL")
        if response is None:
            self._raw_html_events = []
            return self._raw_html_events

        soup = BeautifulSoup(decode_report(response.content), "lxml")
        events = []

        if soup.find("html") is None:
            self._report_failures["PL"] = "empty report"
            self._raw_html_events = []
            return self._raw_html_events

        tds = soup.find_all("td", {"class": re.compile(".*bborder.*")})
        events_data = hs_strip_html(tds)
        del soup
        events_data = [unidecode(x).replace("\n ", ", ").replace("\n", "") for x in events_data]

        # While a game is in progress the report can end with a half-written row for the
        # current event, so keep only the complete rows of 8 cells
        length = len(events_data) // 8
        events_data = np.array(events_data[: length * 8]).reshape(length, 8)

        for event in events_data:
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
        """Transform raw HTML events into structured event dicts."""
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
        # Counted for the warning at the end
        no_team, no_server = 0, 0

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
                    # The report's elapsed and remaining clocks run together, e.g. 5:000:00
                    period_end = format_time(period_length(int(event["period"]), self._overtime))
                    event["time"] = event["time"].replace("-16:0-120:00", f"{period_end}0:00")
                else:
                    event["time"] = event["time"].replace("-16:0-120:00", goals[-1]["time"])

            event["period"] = int(event["period"])

            time_split = event["time"].split(":")
            event["period_time"] = time_split[0] + ":" + time_split[1][:2]
            event["period_seconds"] = (60 * int(event["period_time"].split(":")[0])) + int(
                event["period_time"].split(":")[1]
            )
            event["game_seconds"] = game_seconds(event["period"], event["period_seconds"], self._overtime)

            # Team Extractions
            if event["event"] not in non_team_events:
                if (_m := _EVENT_TEAM_RE.search(event["description"])) is None:
                    # Kept with no team, like the events that never have one
                    no_team += 1
                    event["event_team"] = ""
                else:
                    event["event_team"] = _m.group(1)
                    if event["event_team"] == "LEA":
                        event["event_team"] = ""

            if event["event"] == "FAC":
                # While a game is in progress the report can list a faceoff before its winner
                # is written. The row is kept, with no winning team, in the order the report
                # lists the two players
                _m = _FO_TEAM_RE.search(event["description"])
                event["event_team"] = _m.group(1) if _m is not None else ""

            if event["event"] == "BLOCK" and "BLOCKED BY" in event["description"]:
                _m = _BLOCK_TEAM_RE.search(event["description"])
                if _m is not None:
                    event["event_team"] = _m.group(1)

            # Player Identification
            if event["event"] in ["GOAL", "SHOT", "TAKE", "GIVE"]:
                event_players = [event["event_team"] + num for num in _NUMBERS_RE.findall(event["description"])]
            else:
                event_players = _EVENT_PLAYERS_RE.findall(event["description"])

            # The faceoff winner, or the blocker, goes first
            if event["event"] == "FAC" and len(event_players) > 1 and event["event_team"] not in event_players[0]:
                event_players[0], event_players[1] = event_players[1], event_players[0]

            if event["event"] == "BLOCK":
                if "TEAMMATE" in event["description"]:
                    event["event_team"] = event["description"][:3]
                    event_players.insert(0, "TEAMMATE")
                elif "BLOCKED BY OTHER" in event["description"]:
                    event["event_team"] = "OTHER"
                    event_players.insert(0, "REFEREE")
                elif len(event_players) > 1 and event.get("event_team") not in event_players[0]:
                    event_players[0], event_players[1] = event_players[1], event_players[0]

            for num, event_player in enumerate(event_players, start=1):
                event_player = event_player.replace(" #", "")

                if event_player in ("TEAMMATE", "REFEREE"):
                    p_name, eh_id, pos = event_player, event_player, None
                else:
                    p_info = actives.get(event_player) or scratches.get(event_player, {})
                    p_name = p_info.get("player_name", "")
                    eh_id = p_info.get("eh_id", "")
                    pos = p_info.get("position")

                event.update({f"player_{num}": p_name, f"player_{num}_eh_id": eh_id, f"player_{num}_position": pos})

            # Feature Parsing (Zone, Penalty, Shots)
            if (_m := _ZONE_RE.search(event["description"])) is not None:
                event["zone"] = _m.group(1).upper()
                if "BLOCK" in event["event"] and event["zone"] == "DEF":
                    event["zone"] = "OFF"

            if event["event"] == "PENL" or event["event"] == "DELPEN":
                if ("TEAM" in event["description"] and "SERVED BY" in event["description"]) or (
                    "HEAD COACH" in event["description"]
                ):
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": None})

                # player_2 drew the penalty and player_3 serves it
                drawn_by = _DRAWN_RE.search(event["description"])
                served_by = _SERVED_RE.search(event["description"])
                for slot, match in (("player_2", drawn_by), ("player_3", served_by)):
                    if match is not None:
                        team_jersey = match.group(1) + match.group(2)
                        p_info = actives.get(team_jersey) or scratches.get(team_jersey, {})
                        event.update(
                            {
                                slot: p_info.get("player_name"),
                                f"{slot}_eh_id": p_info.get("eh_id"),
                                f"{slot}_position": p_info.get("position"),
                            }
                        )

                if event.get("player_1") == "BENCH" and drawn_by is None and served_by is None:
                    no_server += 1

                # On a bench penalty the drawer is the only player with a team prefix, so it was read as player_1
                if drawn_by is not None and event.get("player_1_eh_id") == event.get("player_2_eh_id"):
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": None})

                if "player_1" not in event and event["event"] == "PENL":
                    event.update({"player_1": "BENCH", "player_1_eh_id": "BENCH", "player_1_position": ""})

                if (_m := _PENALTY_LENGTH_RE.search(event["description"])) is not None:
                    event["penalty_length"] = int(_m.group(1))

                if (_m := _PENALTY_RE.search(event["description"])) is not None:
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
                if (_m := _SHOT_RE.search(event["description"])) is not None:
                    event["shot_type"] = _m.group(1).upper()
                else:
                    event["shot_type"] = "WRIST"

                if (_m := _DISTANCE_RE.search(event["description"])) is not None:
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

        if (no_team or no_server) and self.game_state in ENDED_STATES:
            logger.warning(
                "Game %s is final but its HTML events report has %s event(s) with no team and %s bench "
                "penalty(ies) with no player serving them",
                self.game_id,
                no_team,
                no_server,
            )

        return final_events

    @cached_property
    @shared_doc(_GAME_HTML_EVENTS_DOC)
    def html_events(self) -> list:
        """html_events — docstring lives in _docstrings._GAME_HTML_EVENTS_DOC."""
        self._prefetch_reports(
            (self._fetch_html_rosters, ("html_rosters", "rosters")), (self._fetch_html_events, ("html_events",))
        )
        raw_events = self._fetch_html_events()

        # A finished game's report has events and ends with GEND
        if self.game_state in ENDED_STATES:
            if not raw_events:
                self._report_failures.setdefault("PL", "no events in the report")
            elif not any(e["event"] == "GEND" for e in raw_events):
                self._report_failures.setdefault("PL", "no game end in the report")

        self._raise_for_reports("PL")
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

        # While a game is played the report can list a faceoff before its winner; once it is final it should not
        if self.game_state in ENDED_STATES:
            no_winner = sum(1 for event in final_events if event["event"] == "FAC" and not event.get("event_team"))
            if no_winner:
                logger.warning(
                    "Game %s is final but its HTML events report has %s faceoff(s) with no winner",
                    self.game_id,
                    no_winner,
                )

        return sorted(final_events, key=lambda k: k["event_idx"])

    @property
    @shared_doc(_GAME_HTML_EVENTS_DF_DOC)
    def html_events_df(self) -> pd.DataFrame | pl.DataFrame:
        """html_events_df — docstring lives in _docstrings._GAME_HTML_EVENTS_DF_DOC."""
        return self._finalize_dataframe(data=self.html_events, schema=html_events_polars_schema)
