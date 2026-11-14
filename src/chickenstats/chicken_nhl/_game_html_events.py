from __future__ import annotations

from functools import cached_property
import logging
import re

import numpy as np

from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import (
    DROPPED_HTML_EVENTS,
    GAMES_WITHOUT_GEND,
    HITS_WITHOUT_HITTER,
    html_events_fixes,
)
from chickenstats.chicken_nhl._game_utils import (
    CORSI_EVENTS,
    FENWICK_EVENTS,
    NON_TEAM_EVENTS,
    format_time,
    game_seconds,
    node_text,
    parse_report,
    period_length,
)
from chickenstats.chicken_nhl.validation_pydantic import HTMLEvent
from chickenstats.chicken_nhl.validation_polars import html_events_polars_schema
from chickenstats.utilities.types import FrameT
from chickenstats.chicken_nhl._docstrings import _GAME_HTML_EVENTS_DF_DOC, _GAME_HTML_EVENTS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import ENDED_STATES, FIRST_API_COORDS_SEASON, _GameBase

logger = logging.getLogger(__name__)

# Regexes for the HTML event descriptions
_EVENT_TEAM_RE = re.compile(r"^([A-Z]{3}|[A-Z]\.[A-Z])")
_NUMBERS_RE = re.compile(r"#([0-9]{1,2})")
_ONGOAL_NUMBER_RE = re.compile(r"ONGOAL - ([0-9]{1,2}) ")
_EVENT_PLAYERS_RE = re.compile(r"([A-Z]{3}\s+#[0-9]{1,2})")
_FO_TEAM_RE = re.compile(r"([A-Z]{3}) WON")
_BLOCK_TEAM_RE = re.compile(r"BLOCKED BY\s+([A-Z]{3})")
_ZONE_RE = re.compile(r"([A-Za-z]{3}). ZONE")
_PENALTY_RE = re.compile(r"^\S+\s+(?:#\s+)?(#\d+\s+)?([^(]*)\(")
_PENALTY_LENGTH_RE = re.compile(r"\((\d+) MIN")
_SHOT_RE = re.compile(r",\s+([A-Za-z]*|[A-Za-z]*-[A-Za-z]*)\s*,")
_DISTANCE_RE = re.compile(r"(\d+) FT")
_SERVED_RE = re.compile(r"([A-Z]{3})\s.+SERVED BY: #([0-9]+)")
_DRAWN_RE = re.compile(r"DRAWN BY: ([A-Z]{3}) #([0-9]+)")

# The first rule whose keywords all appear in the description names the penalty, so order matters
_PENALTY_RULES = (
    (("INTERFERENCE", "GOALKEEPER"), "GOALKEEPER INTERFERENCE"),
    (("CROSS", "CHECKING"), "CROSS-CHECKING"),
    (("DELAY", "GAME", "PUCK OVER"), "DELAY OF GAME - PUCK OVER GLASS"),
    (("DELAY", "GAME", "UNSUCC"), "DELAY OF GAME - UNSUCCESSFUL CHALLENGE"),
    (("GAME MISCONDUCT",), "GAME MISCONDUCT"),
    (("MATCH PENALTY",), "MATCH PENALTY"),
    (("GOALIE LEAVE CREASE",), "LEAVING THE CREASE"),
    (("HOOKING", "BREAKAWAY"), "HOOKING - BREAKAWAY"),
    (("HOLDING", "BREAKAWAY"), "HOLDING - BREAKAWAY"),
    (("TEAM TOO MANY",), "TOO MANY MEN ON THE ICE"),
    (("HOLDING", "STICK"), "HOLDING THE STICK"),
    (("CLOSING", "HAND"), "CLOSING HAND ON PUCK"),
    (("ABUSE", "OFFICIALS"), "ABUSE OF OFFICIALS"),
    (("UNSPORTSMANLIKE CONDUCT",), "UNSPORTSMANLIKE CONDUCT"),
    (("DELAY", "GAME"), "DELAY OF GAME"),
)

# Events whose report description is blank or unhelpful, given a fixed one instead
_NON_DESCRIPTS = {
    "PGSTR": "PRE-GAME START",
    "PGEND": "PRE-GAME END",
    "ANTHEM": "NATIONAL ANTHEM",
    "EISTR": "EARLY INTERMISSION START",
    "EIEND": "EARLY INTERMISSION END",
    "SPC": "PUCK IN CROWD",
    "GOFF": "GAME OFFICIAL",
    "EGT": "EMERGENCY GOALTENDER",
}

# Old or dotted team codes in the descriptions, mapped to the codes used everywhere else
_NEW_TEAM_NAMES = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL", "PHX": "ARI"}


def _put_team_first(event_players: list, event_team: str | None) -> None:
    """Swap the first two players in place when the first is not on the event team."""
    if len(event_players) > 1 and event_team is not None and event_team not in event_players[0]:
        event_players[0], event_players[1] = event_players[1], event_players[0]


def _penalty_name(description: str, player_name: str | None) -> str | None:
    """Return the penalty as the report names it, without the team or the player.

    The report puts only a space between the surname and the penalty, as in
    ``VGK #49 BARBASHEV HIGH-STICKING - DOUBLE MINOR(4 MIN)``. The first word after the
    jersey number is always the surname, and the roster name shows whether it runs on.

    Args:
        description (str):
            The event description from the report
        player_name (str | None):
            The roster name of the player who took the penalty

    Returns:
        str | None:
            The name of the penalty, or None when the report gives no name
    """
    if (match := _PENALTY_RE.search(description)) is None:
        return None

    jersey, text = match.groups()
    words = text.removeprefix("TEAM ").split()

    if jersey is not None:
        surname = (player_name or "").replace(".", "").split()[1:]
        words = words[1:]
        while words and words[0] in surname:
            words = words[1:]

    return " ".join(words) or None


def _slot_fields(slot: str, name: str | None, eh_id: str | None, position: str | None) -> dict:
    """Return the name, eh_id and position fields for one player slot, such as ``player_1``."""
    return {slot: name, f"{slot}_eh_id": eh_id, f"{slot}_position": position}


def _roster_fields(slot: str, team_jersey: str, actives: dict, scratches: dict) -> dict:
    """Return the slot fields for a team and jersey key, all None for a player on neither roster."""
    p_info = actives.get(team_jersey) or scratches.get(team_jersey, {})
    return _slot_fields(slot, p_info.get("player_name"), p_info.get("eh_id"), p_info.get("position"))


def _parse_event_team(event: dict) -> bool:
    """Set ``event_team`` from the description, and return True when a team event names no team."""
    no_team = False

    if event["event"] not in NON_TEAM_EVENTS:
        if (_m := _EVENT_TEAM_RE.search(event["description"])) is None:
            # Kept with no team, like the events that never have one
            no_team = True
            event["event_team"] = None
        else:
            event["event_team"] = _m.group(1)
            if event["event_team"] == "LEA":
                event["event_team"] = None

    if event["event"] == "FAC":
        # While a game is in progress the report can list a faceoff before its winner
        # is written. The row is kept, with no winning team, in the order the report
        # lists the two players
        _m = _FO_TEAM_RE.search(event["description"])
        event["event_team"] = _m.group(1) if _m is not None else None

    if event["event"] == "BLOCK" and "BLOCKED BY" in event["description"]:
        _m = _BLOCK_TEAM_RE.search(event["description"])
        if _m is not None:
            event["event_team"] = _m.group(1)

    return no_team


def _parse_zone(event: dict) -> None:
    """Set ``zone`` from the description, giving a blocked shot the shooter's zone."""
    if (_m := _ZONE_RE.search(event["description"])) is not None:
        event["zone"] = _m.group(1).upper()
        if "BLOCK" in event["event"] and event["zone"] == "DEF":
            event["zone"] = "OFF"


def _parse_penalty(event: dict, actives: dict, scratches: dict) -> bool:
    """Set the penalty fields, and return True for a bench penalty that names no player.

    player_2 drew the penalty and player_3 serves it.
    """
    desc = event["description"]

    if ("TEAM" in desc and "SERVED BY" in desc) or "HEAD COACH" in desc:
        event.update(_slot_fields("player_1", "BENCH", "BENCH", None))

    drawn_by = _DRAWN_RE.search(desc)
    served_by = _SERVED_RE.search(desc)
    for slot, match in (("player_2", drawn_by), ("player_3", served_by)):
        if match is not None:
            event.update(_roster_fields(slot, match.group(1) + match.group(2), actives, scratches))

    no_server = event.get("player_1") == "BENCH" and drawn_by is None and served_by is None

    # On a bench penalty the drawer is the only player with a team prefix, so it was read as player_1.
    # A player_1 on neither roster has no eh_id, which is not a match.
    player_1_eh_id = event.get("player_1_eh_id")
    same_player = player_1_eh_id == event.get("player_2_eh_id") and (
        player_1_eh_id is not None or "player_1" not in event
    )
    if drawn_by is not None and same_player:
        event.update(_slot_fields("player_1", "BENCH", "BENCH", None))

    if "player_1" not in event and event["event"] == "PENL":
        event.update(_slot_fields("player_1", "BENCH", "BENCH", None))

    if (_m := _PENALTY_LENGTH_RE.search(desc)) is not None:
        event["penalty_length"] = int(_m.group(1))

    if (penalty := _penalty_name(desc, event.get("player_1"))) is not None:
        event["penalty"] = penalty

    # Hand-curated overwrites for penalty descriptions that need normalizing
    if event.get("penalty"):
        for keywords, name in _PENALTY_RULES:
            if all(keyword in desc for keyword in keywords):
                event["penalty"] = name
                break

    return no_server


def _parse_shot(event: dict) -> None:
    """Set ``shot_type`` and ``pbp_distance`` on a shot attempt."""
    if (_m := _SHOT_RE.search(event["description"])) is not None:
        event["shot_type"] = _m.group(1).upper()
    else:
        event["shot_type"] = "WRIST"

    if (_m := _DISTANCE_RE.search(event["description"])) is not None:
        event["pbp_distance"] = int(_m.group(1))
    elif event["event"] in FENWICK_EVENTS:
        event["pbp_distance"] = 0


class _GameHTMLEventsMixin(_GameBase[FrameT]):
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

        root = parse_report(response.content)
        events = []

        if root is None:
            self._report_failures["PL"] = "empty report"
            self._raw_html_events = []
            return self._raw_html_events

        events_data = [node_text(td) for td in root.xpath("//td[contains(@class, 'bborder')]")]
        # The header's time cell runs on past the first time in it
        if len(events_data) > 3:
            events_data[3] = events_data[3][: events_data[3].find(":") + 3]
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

            if (self.game_id, event_dict["event_idx"]) in DROPPED_HTML_EVENTS:
                continue

            events.append(event_dict)

        self._raw_html_events = events
        return self._raw_html_events

    def _clean_event(self, event: dict, raw_events: list) -> dict:
        """Normalize the description and team codes, apply the corrections and set the time fields."""
        if event["event"] in _NON_DESCRIPTS:
            event["description"] = _NON_DESCRIPTS[event["event"]]
            if event["event"] == "SPC":
                event["event"] = "STOP"

        for old_name, new_name in _NEW_TEAM_NAMES.items():
            event["description"] = event["description"].replace(old_name, new_name).upper()

        event = html_events_fixes(self.game_id, event)

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

        return event

    def _parse_event_players(self, event: dict, actives: dict, scratches: dict) -> None:
        """Fill the player slots for the players the description names, the event team's player first."""
        if event["event"] in ["GOAL", "SHOT", "TAKE", "GIVE"]:
            numbers = _NUMBERS_RE.findall(event["description"])
            # 2007-08 reports leave the # off the shooter on a shot
            if not numbers and self.season < FIRST_API_COORDS_SEASON:
                numbers = _ONGOAL_NUMBER_RE.findall(event["description"])
            # With no team the numbers match no roster key, so the players are left empty
            event_players = [f"{event['event_team'] or ''}{num}" for num in numbers]
        else:
            event_players = _EVENT_PLAYERS_RE.findall(event["description"])

        # The faceoff winner, or the blocker, goes first
        if event["event"] == "FAC":
            _put_team_first(event_players, event["event_team"])

        if event["event"] == "BLOCK":
            if "TEAMMATE" in event["description"]:
                event["event_team"] = event["description"][:3]
                event_players.insert(0, "TEAMMATE")
            elif "BLOCKED BY OTHER" in event["description"]:
                # Nobody on the other team blocked it, so it stays with the shooter's team
                event["event_team"] = event["description"][:3]
                event_players.insert(0, "REFEREE")
            else:
                _put_team_first(event_players, event.get("event_team"))

        first_slot = 2 if (self.game_id, event["event_idx"]) in HITS_WITHOUT_HITTER else 1
        for num, event_player in enumerate(event_players, start=first_slot):
            event_player = event_player.replace(" #", "")

            if event_player in ("TEAMMATE", "REFEREE"):
                event.update(_slot_fields(f"player_{num}", event_player, event_player, None))
            else:
                event.update(_roster_fields(f"player_{num}", event_player, actives, scratches))

    def _munge_html_events(self, raw_events: list, actives: dict, scratches: dict) -> list:
        """Transform raw HTML events into structured event dicts."""
        processed_events = []
        # Counted for the warning at the end
        no_team, no_server = 0, 0

        for event in raw_events:
            event = self._clean_event(event, raw_events)
            no_team += _parse_event_team(event)
            self._parse_event_players(event, actives, scratches)
            _parse_zone(event)

            if event["event"] in ("PENL", "DELPEN"):
                no_server += _parse_penalty(event, actives, scratches)

            if event["event"] in CORSI_EVENTS:
                _parse_shot(event)

            processed_events.append(event)

        # Versioning & validation
        version_tracker = {}
        final_events = []

        for event in processed_events:
            # A named player_1 counts even when on neither roster, with no eh_id
            if "player_1_eh_id" in event:
                # Create a unique key for simultaneous identical events
                v_key = (event["event"], event["game_seconds"], event["period"], event["player_1_eh_id"])
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

    def _has_game_end(self, raw_events: list) -> bool:
        """Return whether a report runs to the end of the game."""
        if any(event["event"] == "GEND" for event in raw_events):
            return True

        # Reports from early 2007-08 can stop at the last period's end, with no GEND row
        last = raw_events[-1]
        return self.season < FIRST_API_COORDS_SEASON and last["event"] == "PEND" and last["period"] >= 3

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
            elif self.game_id not in GAMES_WITHOUT_GEND and not self._has_game_end(raw_events):
                self._report_failures.setdefault("PL", "no game end in the report")

        self._raise_for_reports("PL")
        if not raw_events:
            return []

        # Build O(1) lookup dicts by team_jersey
        actives = self._roster_by_jersey("ACTIVE")
        scratches = self._roster_by_jersey("SCRATCH")

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
    def html_events_df(self) -> FrameT:
        """html_events_df — docstring lives in _docstrings._GAME_HTML_EVENTS_DF_DOC."""
        return self._finalize_dataframe(data=self.html_events, schema=html_events_polars_schema)
