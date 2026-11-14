"""Shot and event coordinates from ESPN, for games the NHL API has none for.

The NHL API has no coordinates before 2010-11, apart from most of 2009-10. ESPN kept them for 2007-08 onward,
and its plays line up with the NHL's HTML reports on period, elapsed clock, event type and team. The approach,
including the idea of matching tied events on the player, comes from the Evolving-Hockey scraper
(``sc.scrape_events_ESPN`` and ``sc.join_coordinates_ESPN``), which is GPL-3 like chickenstats.

These are undocumented ESPN endpoints that can change without notice, so every function here returns nothing
instead of raising: a game without coordinates is still a game.

Coordinates are passed on as ESPN gives them. Evolving-Hockey's 2007-09 rescale is left out because it moves
shots away from the distances in the NHL's own reports, by up to two feet depending on the end of the rink.
"""

import logging
import time
from collections import defaultdict
from typing import Any

from requests import RequestException
from unidecode import unidecode

from chickenstats.chicken_nhl._game_utils import parse_time
from chickenstats.utilities import ChickenSession

logger = logging.getLogger(__name__)

_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary"

# ESPN's abbreviations that differ from the codes a Game uses
_TEAM_CODES = {"LA": "LAK", "NJ": "NJD", "SJ": "SJS", "TB": "TBL", "PHX": "ARI"}

# ESPN's one turnover type covers both giveaways and takeaways
_TURNOVER = "TURN"
_PLAY_EVENTS = {
    "Face Off": "FAC",
    "Hit": "HIT",
    "Shot": "SHOT",
    "Missed": "MISS",
    "Blocked": "BLOCK",
    "Goal": "GOAL",
    "Penalty": "PENL",
    "Turnover": _TURNOVER,
}
_HTML_EVENTS = {event: event for event in _PLAY_EVENTS.values()} | {"GIVE": _TURNOVER, "TAKE": _TURNOVER}

# Where ESPN puts a 2007-09 penalty that has no location
_PENALTY_PLACEHOLDER = (-97, 40)

# Anything past the boards, by a margin, is not a location
_MAX_X, _MAX_Y = 100, 43

_FAILURES = (RequestException, ValueError, KeyError, TypeError, AttributeError)

# Pause between a game's two ESPN requests
_REQUEST_GAP = 0.5


def _get_json(session: ChickenSession, url: str, params: dict) -> dict | None:
    """Return an ESPN response as a dict, or ``None`` for any failure."""
    try:
        response = session.get(url, params=params)
        if response.status_code != 200:
            logger.debug("ESPN returned %s for %s %s", response.status_code, url, params)
            return None
        data = response.json()
    except (RequestException, ValueError) as exc:
        logger.debug("ESPN request failed for %s %s: %s", url, params, exc)
        return None

    return data if isinstance(data, dict) else None


def _team_code(abbreviation: str) -> str:
    """The code a Game uses for an ESPN team abbreviation."""
    return _TEAM_CODES.get(abbreviation, abbreviation)


def _competitors(competition: dict) -> list[dict]:
    """A competition's competitors, each with its team."""
    return [x for x in competition.get("competitors") or [] if x.get("team")]


def find_espn_id(game_date: str, home_team: str, away_team: str, session: ChickenSession) -> str | None:
    """Find ESPN's ID for a game, or ``None`` if ESPN does not list it.

    A date and two teams are enough: no team played twice on one date from 2007-08 through 2009-10.

    Parameters:
        game_date: The date of the game as ``YYYY-MM-DD``, in the NHL's listing.
        home_team: The home team's code, as a Game has it.
        away_team: The away team's code, as a Game has it.
        session: The session to send the request with.
    """
    scoreboard = _get_json(session, _SCOREBOARD_URL, {"dates": game_date.replace("-", "")})
    if scoreboard is None:
        return None

    teams = {"home": _team_code(home_team), "away": _team_code(away_team)}
    for event in scoreboard.get("events") or []:
        for competition in event.get("competitions") or []:
            sides = {x.get("homeAway"): _team_code(x["team"].get("abbreviation")) for x in _competitors(competition)}
            if sides == teams:
                return event.get("id")

    return None


def fetch_espn_summary(espn_id: str, session: ChickenSession) -> dict | None:
    """Fetch ESPN's summary of a game, plays included, or ``None`` if it cannot be read."""
    return _get_json(session, _SUMMARY_URL, {"event": espn_id})


def _usable_coordinates(event: str, coordinate: dict) -> tuple[Any, Any] | None:
    """A play's x and y, or ``None`` if it has no real location."""
    x, y = coordinate.get("x"), coordinate.get("y")
    # Coordinates in these seasons are whole numbers
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    if abs(x) > _MAX_X or abs(y) > _MAX_Y:
        return None
    if event == "PENL" and (x, y) == _PENALTY_PLACEHOLDER:
        return None
    return x, y


def _surnames(play: dict) -> set[str]:
    """The upper-case, ASCII surnames of a play's participants, to compare with an HTML description."""
    names = ((x.get("athlete") or {}).get("displayName") for x in play.get("participants") or [])
    return {unidecode(name).upper().split()[-1] for name in names if name and name.strip()}


def normalize_plays(summary: dict) -> list[dict]:
    """Reduce an ESPN summary to the plays that can be matched to an HTML event.

    Shootout attempts are left out because ESPN gives them no type. So is any play without a usable
    location, a clock or a team.

    Returns:
        One dict per play, with ``period``, ``period_seconds``, ``event``, ``event_team``, ``coords_x``,
        ``coords_y`` and ``players``. ``event`` is an HTML event code, or ``"TURN"`` for a turnover.
    """
    competitions = (summary.get("header") or {}).get("competitions") or [{}]
    teams = {x["team"].get("id"): _team_code(x["team"].get("abbreviation")) for x in _competitors(competitions[0])}

    plays = []
    for play in summary.get("plays") or []:
        event = _PLAY_EVENTS.get((play.get("type") or {}).get("text"))
        clock = (play.get("clock") or {}).get("displayValue")
        period = (play.get("period") or {}).get("number")
        team = teams.get((play.get("team") or {}).get("id"))
        if event is None or not clock or period is None or team is None:
            continue

        coordinates = _usable_coordinates(event, play.get("coordinate") or {})
        if coordinates is None:
            continue

        plays.append(
            {
                "period": period,
                # ESPN's clock for these seasons counts up, like the HTML report's elapsed time
                "period_seconds": parse_time(clock),
                "event": event,
                "event_team": team,
                "coords_x": coordinates[0],
                "coords_y": coordinates[1],
                "players": _surnames(play),
            }
        )

    return plays


def _candidates(event: dict, plays: list[dict]) -> list[dict]:
    """The plays at an event's second that are from its team."""
    same_team = [play for play in plays if play["event_team"] == event["event_team"]]
    # Some 2007-08 games credit a block to the shooter's team, the opposite of the HTML report
    if not same_team and event["event"] == "BLOCK":
        return plays
    return same_team


def match_coordinates(html_events: list[dict], plays: list[dict]) -> dict[int, dict]:
    """Match normalized ESPN plays onto HTML events.

    An event takes a play's coordinates when it is the only candidate at that second. When several events or
    plays share a second, the player's surname decides, and an event that is still not settled gets nothing
    rather than a guess. Penalties can share a play, since one player can take several at one spot.

    Parameters:
        html_events: Events from ``Game.html_events``, or dicts with ``event_idx``, ``period``,
            ``period_seconds``, ``event``, ``event_team`` and ``description``.
        plays: The output of ``normalize_plays``.

    Returns:
        ``coords_x`` and ``coords_y`` by HTML ``event_idx``, for the events that matched.
    """
    plays_at = defaultdict(list)
    for play in plays:
        plays_at[(play["period"], play["period_seconds"], play["event"])].append(play)

    events_at = defaultdict(list)
    for event in html_events:
        code = _HTML_EVENTS.get(event["event"])
        if code is not None:
            events_at[(event["period"], event["period_seconds"], code)].append(event)

    matches = {}
    for key, events in events_at.items():
        taken: list[dict] = []
        for event in events:
            candidates = _candidates(event, plays_at.get(key, []))

            if len(events) > 1 or len(candidates) > 1:
                candidates = [x for x in candidates if any(name in event["description"] for name in x["players"])]

            if event["event"] != "PENL":
                candidates = [x for x in candidates if not any(x is play for play in taken)]

            if len({(x["coords_x"], x["coords_y"]) for x in candidates}) == 1:
                taken.append(candidates[0])
                matches[event["event_idx"]] = {
                    "coords_x": candidates[0]["coords_x"],
                    "coords_y": candidates[0]["coords_y"],
                }

    return matches


def espn_coordinates(
    game_date: str, home_team: str, away_team: str, html_events: list[dict], session: ChickenSession
) -> dict[int, dict]:
    """Coordinates by HTML ``event_idx`` for one game, or an empty dict if ESPN has none or cannot be read.

    This makes two ESPN requests, and is what the rest of the package should call.

    Parameters:
        game_date: The date of the game as ``YYYY-MM-DD``.
        home_team: The home team's code, as a Game has it.
        away_team: The away team's code, as a Game has it.
        html_events: Events from ``Game.html_events``.
        session: The session to send the requests with.
    """
    try:
        espn_id = find_espn_id(game_date, home_team, away_team, session)
        if espn_id is None:
            return {}

        time.sleep(_REQUEST_GAP)
        summary = fetch_espn_summary(espn_id, session)
        if summary is None:
            return {}

        return match_coordinates(html_events, normalize_plays(summary))
    except _FAILURES as exc:
        # ESPN's format is undocumented
        logger.debug("ESPN coordinates failed for %s %s at %s: %s", game_date, away_team, home_team, exc)
        return {}
