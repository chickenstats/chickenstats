"""Shared docstring constants and utilities.

Organized in three layers:

1. **``shared_doc`` decorator** — stamps a pre-built string onto any callable
   or ``property`` object so both IDEs and mkdocstrings pick it up.

2. **Field registries** — plain dicts mapping ``field_name -> (type_str, description)``.
   Each field is defined once here and referenced by every docstring that uses it.

3. **Docstring constants** — f-strings that compose a preamble, a
   ``_build_returns()`` call, and a per-caller Examples section.

To add a new field: add one entry to the relevant registry dict.
To update a description: change one entry — all consumers update automatically.
To add a new docstring: write an f-string that calls ``_build_returns()``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

_F = TypeVar("_F", bound=Callable)

# ---------------------------------------------------------------------------
# Decorator to inject common docstrings fields into classes, methods, and properties
# ---------------------------------------------------------------------------


def shared_doc(docstring: str) -> Callable[[_F], _F]:
    """Decorator that assigns *docstring* to the wrapped callable's ``__doc__``.

    Parameters:
        docstring: The docstring string to assign.

    Returns:
        A decorator that sets ``func.__doc__ = docstring`` and returns the
        callable unchanged.

    Examples:
        >>> @shared_doc("My shared docstring.")
        ... def my_func(): ...
        >>> my_func.__doc__
        'My shared docstring.'
    """

    def decorator(func: _F) -> _F:
        func.__doc__ = docstring
        return func

    return decorator


# ---------------------------------------------------------------------------
# Function to build docstrings, based on the field dictionaries
# ---------------------------------------------------------------------------


def _build_returns(fields: dict[str, tuple[str, str]]) -> str:
    """Render a Google-style ``Returns:`` block from a field registry dict.

    Parameters:
        fields: Ordered mapping of ``field_name -> (type_str, description)``.
            Descriptions may contain a newline character for continuation lines.

    Returns:
        str: A ``Returns:`` block ready for embedding in a docstring constant.
    """
    lines = ["Returns:"]
    for name, (type_str, desc) in fields.items():
        lines.append(f"    {name} ({type_str}):")
        for dline in desc.split("\n"):
            lines.append(f"        {dline}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dictionaries for common fields in docstrings
# ---------------------------------------------------------------------------

_GAME_ID_FIELDS: dict[str, tuple[str, str]] = {
    "season": ("int", "Season as 8-digit number, e.g., 20192020 for 2019-20 season"),
    "session": ("str", "Whether game is regular season, playoffs, or pre-season, e.g., R"),
    "game_id": ("int", "Unique game ID assigned by the NHL, e.g., 2019020684"),
}

_TIMING_FIELDS: dict[str, tuple[str, str]] = {
    "event_idx": ("int", "Index ID for event, e.g., 667"),
    "period": ("int", "Period number of the event, e.g., 3"),
    "period_seconds": ("int", "Time elapsed in the period, in seconds, e.g., 1178"),
    "game_seconds": ("int", "Time elapsed in the game, in seconds, e.g., 3578"),
}

_EVENT_CORE_FIELDS: dict[str, tuple[str, str]] = {
    "event_team": ("str", "Team that performed the action for the event, e.g., NSH"),
    "event": ("str", "Type of event that occurred, e.g., GOAL"),
    "description": ("str | None", "Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT."),
    "coords_x": ("int", "x-coordinates where the event occurred, e.g, -96"),
    "coords_y": ("int", "y-coordinates where the event occurred, e.g., 11"),
    "zone": ("str", "Zone where the event occurred, relative to the event team, e.g., DEF"),
}

_PLAYER_ROSTER_CORE_FIELDS: dict[str, tuple[str, str]] = {
    "team": ("str", "Team name, e.g., NSH"),
    "team_name": ("str", "Full team name, e.g., NASHVILLE PREDATORS"),
    "team_venue": ("str", "Whether team is home or away, e.g., AWAY"),
    "player_name": ("str", "Player's name, e.g., FILIP FORSBERG"),
    "eh_id": ("str", "Evolving Hockey ID for the player, e.g., FILIP.FORSBERG"),
    "team_jersey": ("str", "Team and jersey combination used for player identification, e.g., NSH9"),
    "jersey": ("int", "Player's jersey number, e.g., 9"),
    "position": ("str", "Player's position, e.g., L"),
}


def _player_slots(prefix: str, count: int = 7) -> dict[str, tuple[str, str]]:
    """Generate field entries for numbered player-slot groups (name / eh_id / api_id / pos).

    Parameters:
        prefix: Column name prefix, e.g., ``"event_on"`` or ``"change_off"``.
        count:  Number of slots to generate (default 7).
    """
    out: dict[str, tuple[str, str]] = {}
    for i in range(1, count + 1):
        out[f"{prefix}_{i}"] = ("str | None", "Player name")
        out[f"{prefix}_{i}_eh_id"] = ("str | None", "ID used for matching with Evolving Hockey data")
        out[f"{prefix}_{i}_api_id"] = ("int | None", "ID used for matching NHL API data")
        out[f"{prefix}_{i}_pos"] = ("str | None", "Player position")
    return out


# ---------------------------------------------------------------------------
# Dictionary of fields for play-by-play data
# ---------------------------------------------------------------------------

_PBP_FIELDS: dict[str, tuple[str, str]] = {
    "id": ("int", "The play ID for a given play, combining the game ID and the event_idx, e.g., 20190206840667"),
    "season": ("int", "Season as 8-digit number, e.g., 20192020 for 2019-20 season"),
    "session": ("str", "Whether game is regular season, playoffs, or pre-season, e.g., R"),
    "game_id": ("int", "Unique game ID assigned by the NHL, e.g., 2019020684"),
    "game_date": ("str", "Date game was played, e.g., 2020-01-09"),
    "event_idx": ("int", "Index ID for event, e.g., 667"),
    "period": ("int", "Period number of the event, e.g., 3"),
    "period_seconds": ("int", "Time elapsed in the period, in seconds, e.g., 1178"),
    "game_seconds": ("int", "Time elapsed in the game, in seconds, e.g., 3578"),
    "strength_state": ("str", "Strength state, e.g., 5vE"),
    "event_team": ("str", "Team that performed the action for the event, e.g., NSH"),
    "opp_team": ("str", "Opposing team, e.g., CHI"),
    "event": ("str", "Type of event that occurred, e.g., GOAL"),
    "description": ("str | None", "Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT."),
    "zone": ("str", "Zone where the event occurred, relative to the event team, e.g., DEF"),
    "coords_x": ("int", "x-coordinates where the event occurred, e.g, -96"),
    "coords_y": ("int", "y-coordinates where the event occurred, e.g., 11"),
    "danger": ("int", "Whether shot event occurred from danger area, e.g., 0"),
    "high_danger": ("int", "Whether shot event occurred from high-danger area, e.g., 0"),
    "player_1": ("str", "Player that performed the action, e.g., PEKKA RINNE"),
    "player_1_eh_id": ("str", "Evolving Hockey ID for player_1, e.g., PEKKA.RINNE"),
    "player_1_eh_id_api": (
        "str",
        "Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE",
    ),
    "player_1_api_id": ("int", "NHL API ID for player_1, e.g., 8471469"),
    "player_1_position": ("str", "Position player_1 plays, e.g., G"),
    "player_1_type": ("str", "Type of player, e.g., GOAL SCORER"),
    "player_2": ("str | None", "Player that performed the action, e.g., None"),
    "player_2_eh_id": ("str | None", "Evolving Hockey ID for player_2, e.g., None"),
    "player_2_eh_id_api": (
        "str | None",
        "Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None",
    ),
    "player_2_api_id": ("int | None", "NHL API ID for player_2, e.g., None"),
    "player_2_position": ("str | None", "Position player_2 plays, e.g., None"),
    "player_2_type": ("str | None", "Type of player, e.g., None"),
    "player_3": ("str | None", "Player that performed the action, e.g., None"),
    "player_3_eh_id": ("str | None", "Evolving Hockey ID for player_3, e.g., None"),
    "player_3_eh_id_api": (
        "str | None",
        "Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None",
    ),
    "player_3_api_id": ("int | None", "NHL API ID for player_3, e.g., None"),
    "player_3_position": ("str | None", "Position player_3 plays, e.g., None"),
    "player_3_type": ("str | None", "Type of player, e.g., None"),
    "score_state": ("str", "Score of the game from event team's perspective, e.g., 4v2"),
    "score_diff": ("int", "Score differential from event team's perspective, e.g., 2"),
    "forwards_percent": (
        "float",
        "Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions\n(i,e., F, C, L, R), e.g, 0.6",
    ),
    "opp_forwards_percent": (
        "float",
        "Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions\n(i.e., F, C, L, R), e.g., 0.667",
    ),
    "shot_type": ("str | None", "Type of shot taken, if event is a shot, e.g., WRIST"),
    "event_length": ("int", "Time elapsed between this event and the next event, e.g., 0"),
    "event_distance": ("float | None", "Calculated distance of event from goal, e.g, 185.32673849177834"),
    "pbp_distance": ("int", "Distance of event from goal from description, e.g., 185"),
    "event_angle": ("float | None", "Angle of event towards goal, e.g., 57.52880770915151"),
    "penalty": ("str | None", "Name of penalty, e.g., None"),
    "penalty_length": ("int | None", "Duration of penalty, e.g., None"),
    "home_score": ("int", "Home team's score, e.g., 2"),
    "home_score_diff": ("int", "Home team's score differential, e.g., -2"),
    "away_score": ("int", "Away team's score, e.g., 4"),
    "away_score_diff": ("int", "Away team's score differential, e.g., 2"),
    "is_home": ("int", "Whether event team is home, e.g., 0"),
    "is_away": ("int", "Whether event is away, e.g., 1"),
    "home_team": ("str", "Home team, e.g., CHI"),
    "away_team": ("str", "Away team, e.g., NSH"),
    "home_skaters": ("int", "Number of home team skaters on-ice (excl. goalies), e.g., 6"),
    "away_skaters": ("int", "Number of away team skaters on-ice (excl. goalies), e.g., 5"),
    "home_on": (
        "list | str | None",
        "Name of home team's skaters on-ice (incl. goalies), e.g.,\n"
        "DUNCAN KEITH, PATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, ERIK GUSTAFSSON, KIRBY DACH",
    ),
    "home_on_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of home team's skaters on-ice (incl. goalies), e.g.,\n"
        "DUNCAN.KEITH, PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, ERIK.GUSTAFSSON2, KIRBY.DACH",
    ),
    "home_on_api_id": (
        "list | str | None",
        "NHL API IDs of home team's skaters on-ice (incl. goalies), e.g.,\n"
        "8470281, 8474141, 8473604, 8479337, 8476979, 8481523",
    ),
    "home_on_positions": (
        "list | str | None",
        "Positions of home team's skaters on-ice (incl. goalies), e.g., D, R, C, R, D, C",
    ),
    "away_on": (
        "list | str | None",
        "Name of away team's skaters on-ice (incl. goalies), e.g.,\n"
        "PEKKA RINNE, NICK BONINO, ROMAN JOSI, MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND",
    ),
    "away_on_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of away team's skaters on-ice (excl. goalies), e.g.,\n"
        "PEKKA.RINNE, NICK.BONINO, ROMAN.JOSI, MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND",
    ),
    "away_on_api_id": (
        "list | str | None",
        "NHL API IDs of away team's skaters on-ice (incl. goalies), e.g.,\n8471469, 8474009, 8474600, 8475218, 8475714, 8475798",
    ),
    "away_on_positions": (
        "list | str | None",
        "Positions of away team's skaters on-ice (incl. goalies), e.g., G, C, D, D, C, C",
    ),
    "event_team_skaters": ("int | None", "Number of event team skaters on-ice (excl. goalies), e.g., 5"),
    "teammates": (
        "list | str | None",
        "Name of event team's players on-ice (incl. goalies), e.g.,\n"
        "PEKKA RINNE, NICK BONINO, ROMAN JOSI, MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND",
    ),
    "teammates_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of event team's players on-ice (incl. goalies), e.g.,\n"
        "PEKKA.RINNE, NICK.BONINO, ROMAN.JOSI, MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND",
    ),
    "teammates_api_id": (
        "list | str | None",
        "NHL API IDs of event team's players on-ice (incl. goalies), e.g.,\n"
        "8471469, 8474009, 8474600, 8475218, 8475714, 8475798",
    ),
    "teammates_positions": (
        "list | str | None",
        "Positions of event team's players on-ice (incl. goalies), e.g., G, C, D, D, C, C",
    ),
    "own_goalie": ("list | str | None", "Name of the event team's goalie, e.g., PEKKA RINNE"),
    "own_goalie_eh_id": ("list | str | None", "Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE"),
    "own_goalie_api_id": ("list | str | None", "NHL API ID of the event team's goalie, e.g., 8471469"),
    "forwards": (
        "list | str | None",
        "Name of event team's forwards on-ice, e.g.,\nNICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND",
    ),
    "forwards_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of event team's forwards on-ice, e.g.,\nNICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND",
    ),
    "forwards_api_id": (
        "list | str | None",
        "NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798",
    ),
    "forwards_count": (
        "int",
        "Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions\n(i.e., F, C, L, R), e.g., 3",
    ),
    "defense": ("list | str | None", "Name of event team's defense on-ice, e.g., ROMAN JOSI, MATTIAS EKHOLM"),
    "defense_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of event team's defense on-ice, e.g., ROMAN.JOSI, MATTIAS.EKHOLM",
    ),
    "defense_api_id": ("list | str | None", "NHL API IDs of event team's skaters on-ice, e.g., 8474600, 8475218"),
    "defense_count": (
        "int",
        "Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2",
    ),
    "opp_strength_state": ("str | None", "Strength state from opposing team's perspective, e.g., Ev5"),
    "opp_score_state": ("str | None", "Score state from opposing team's perspective, e.g., 2v4"),
    "opp_score_diff": ("int | None", "Score differential from opposing team's perspective, e.g., -2"),
    "opp_team_skaters": ("int | None", "Number of opposing team skaters on-ice (excl. goalies), e.g., 6"),
    "opp_team_on": (
        "list | str | None",
        "Name of opposing team's players on-ice (incl. goalies), e.g.,\n"
        "DUNCAN KEITH, PATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, ERIK GUSTAFSSON, KIRBY DACH",
    ),
    "opp_team_on_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of opposing team's players on-ice (incl. goalies), e.g.,\n"
        "DUNCAN.KEITH, PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, ERIK.GUSTAFSSON2, KIRBY.DACH",
    ),
    "opp_team_on_api_id": (
        "list | str | None",
        "NHL API IDs of opposing team's players on-ice (incl. goalies), e.g.,\n"
        "8470281, 8474141, 8473604, 8479337, 8476979, 8481523",
    ),
    "opp_team_on_positions": (
        "list | str | None",
        "Positions of opposing team's players on-ice (incl. goalies), e.g., D, R, C, R, D, C",
    ),
    "opp_goalie": ("list | str | None", "Name of the opposing team's goalie, e.g., None"),
    "opp_goalie_eh_id": ("list | str | None", "Evolving Hockey ID of the opposing team's goalie, e.g., None"),
    "opp_goalie_api_id": ("list | str | None", "NHL API ID of the opposing team's goalie, e.g., None"),
    "opp_forwards": (
        "list | str | None",
        "Name of opposing team's forwards on-ice, e.g.,\nPATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, KIRBY DACH",
    ),
    "opp_forwards_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of opposing team's forwards on-ice, e.g.,\n"
        "PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, KIRBY.DACH",
    ),
    "opp_forwards_api_id": (
        "list | str | None",
        "NHL API IDs of opposing team's forwards on-ice, e.g.,\n8474141, 8473604, 8479337, 8481523",
    ),
    "opp_forwards_count": (
        "int",
        "Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions\n(i.e., F, C, L, R), e.g., 4",
    ),
    "opp_defense": ("list | str | None", "Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON"),
    "opp_defense_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2",
    ),
    "opp_defense_api_id": (
        "list | str | None",
        "NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979",
    ),
    "opp_defense_count": (
        "int",
        "Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2",
    ),
    "home_forwards": (
        "list | str | None",
        "Name of home team's forwards on-ice, e.g.,\nPATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, KIRBY DACH",
    ),
    "home_forwards_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of home team's forwards on-ice, e.g.,\n"
        "PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, KIRBY.DACH",
    ),
    "home_forwards_api_id": (
        "list | str | None",
        "NHL API IDs of home team's forwards on-ice, e.g.,\n8474141, 8473604, 8479337, 8481523",
    ),
    "home_forwards_count": (
        "int",
        "Number of home skaters on-ice (i.e., excluding goalies) who play forward positions\n(i.e., F, C, L, R), e.g., 4",
    ),
    "home_forwards_percent": (
        "float",
        "Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions\n(i.e., F, C, L, R), e.g., 0.667",
    ),
    "home_defense": ("list | str | None", "Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON"),
    "home_defense_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2",
    ),
    "home_defense_api_id": ("list | str | None", "NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979"),
    "home_defense_count": (
        "int",
        "Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2",
    ),
    "home_goalie": ("list | str | None", "Name of the home team's goalie, e.g., None"),
    "home_goalie_eh_id": ("list | str | None", "Evolving Hockey ID of the home team's goalie, e.g., None"),
    "home_goalie_api_id": ("list | str | None", "NHL API ID of the home team's goalie, e.g., None"),
    "away_forwards": (
        "list | str | None",
        "Name of away team's forwards on-ice, e.g.,\nNICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND",
    ),
    "away_forwards_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of away team's forwards on-ice, e.g.,\nNICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND",
    ),
    "away_forwards_api_id": (
        "list | str | None",
        "NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798",
    ),
    "away_forwards_count": (
        "int",
        "Number of away skaters on-ice (i.e., excluding goalies) who play forward positions\n(i.e., F, C, L, R), e.g., 3",
    ),
    "away_forwards_percent": (
        "float",
        "Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions\n(i.e., F, C, L, R), e.g., 0.6",
    ),
    "away_defense": ("list | str | None", "Name of away team's defense on-ice, e.g., ROMAN JOSI, MATTIAS EKHOLM"),
    "away_defense_eh_id": (
        "list | str | None",
        "Evolving Hockey IDs of away team's defense on-ice, e.g., ROMAN.JOSI, MATTIAS.EKHOLM",
    ),
    "away_defense_api_id": ("list | str | None", "NHL API IDs of away team's skaters on-ice, e.g., 8474600, 8475218"),
    "away_defense_count": (
        "int",
        "Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2",
    ),
    "away_goalie": ("list | str | None", "Name of the away team's goalie, e.g., PEKKA RINNE"),
    "away_goalie_eh_id": ("list | str | None", "Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE"),
    "away_goalie_api_id": ("list | str | None", "NHL API ID of the away team's goalie, e.g., 8471469"),
    "change_on_count": ("int | None", "Number of players on, e.g., None"),
    "change_off_count": ("int | None", "Number of players off, e.g., None"),
    "zone_start": ("str | None", "The zone where the change occurred (OFF, DEF, NEU, or OTF), e.g., None"),
    "change_on": ("list | str | None", "Names of the players on, e.g., None"),
    "change_on_eh_id": ("list | str | None", "Evolving Hockey IDs of the players on, e.g., None"),
    "change_on_api_id": ("list | str | None", "NHL API IDs of the players on, e.g., None"),
    "change_on_positions": ("list | str | None", "Positions of the players on, e.g., None"),
    "change_off": ("list | str | None", "Names of the players off, e.g., None"),
    "change_off_eh_id": ("list | str | None", "Evolving Hockey IDs of the players off, e.g., None"),
    "change_off_api_id": ("list | str | None", "NHL API IDs of the players off, e.g., None"),
    "change_off_positions": ("list | str | None", "Positions of the players off, e.g., None"),
    "change_on_forwards_count": ("int | None", "Number of forwards changing on, e.g., None"),
    "change_off_forwards_count": ("int | None", "Number of forwards off, e.g., None"),
    "change_on_forwards": ("list | str | None", "Names of the forwards on, e.g., None"),
    "change_on_forwards_eh_id": ("list | str | None", "Evolving Hockey IDs of the forwards on, e.g., None"),
    "change_on_forwards_api_id": ("list | str | None", "NHL API IDs of the forwards on, e.g., None"),
    "change_off_forwards": ("list | str | None", "Names of the forwards off, e.g., None"),
    "change_off_forwards_eh_id": ("list | str | None", "Evolving Hockey IDs of the forwards off, e.g., None"),
    "change_off_forwards_api_id": ("list | str | None", "NHL API IDs of the forwards off, e.g., None"),
    "change_on_defense_count": ("int | None", "Number of defense on, e.g., None"),
    "change_off_defense_count": ("int | None", "Number of defense off, e.g., None"),
    "change_on_defense": ("list | str | None", "Names of the defense on, e.g., None"),
    "change_on_defense_eh_id": ("list | str | None", "Evolving Hockey IDs of the defense on, e.g., None"),
    "change_on_defense_api_id": ("list | str | None", "NHL API IDs of the defense on, e.g., None"),
    "change_off_defense": ("list | str | None", "Names of the defense off, e.g., None"),
    "change_off_defense_eh_id": ("list | str | None", "Evolving Hockey IDs of the defense off, e.g., None"),
    "change_off_defense_api_id": ("list | str | None", "NHL API IDs of the defense off, e.g., None"),
    "change_on_goalie_count": ("int | None", "Number of goalies on, e.g., None"),
    "change_off_goalie_count": ("int | None", "Number of goalies off, e.g., None"),
    "change_on_goalie": ("list | str | None", "Name of goalie on, e.g., None"),
    "change_on_goalie_eh_id": ("list | str | None", "Evolving Hockey ID of the goalie on, e.g., None"),
    "change_on_goalie_api_id": ("list | str | None", "NHL API ID of the goalie on, e.g., None"),
    "change_off_goalie": ("list | str | None", "Name of the goalie off, e.g., None"),
    "change_off_goalie_eh_id": ("list | str | None", "Evolving Hockey ID of the goalie off, e.g., None"),
    "change_off_goalie_api_id": ("list | str | None", "NHL API ID of the goalie off, e.g., None"),
    "pred_goal": ("float", "xG value for a given shot attempt, e.g., 0.5131293535232544"),
    "pred_goal_adj": ("float", "Score- and venue-adjusted xG value for a given shot attempt, e.g., 0.5131293535232544"),
    "goal": ("int", "Dummy indicator whether event is a goal, e.g., 1"),
    "goal_adj": ("float", "Score- and venue-adjusted value for a goal, e.g., 1.0"),
    "hd_goal": ("int", "Dummy indicator whether event is a high-danger goal, e.g., 0"),
    "shot": ("int", "Dummy indicator whether event is a shot, e.g., 1"),
    "shot_adj": ("float", "Score- and venue-adjusted value for a shot, e.g., 1.0"),
    "hd_shot": ("int", "Dummy indicator whether event is a high-danger shot, e.g., 0"),
    "miss": ("int", "Dummy indicator whether event is a miss, e.g., 0"),
    "miss_adj": ("float", "Score- and venue-adjusted value for a missed shot, e.g., 0.0"),
    "hd_miss": ("int", "Dummy indicator whether event is a high-danger missed shot, e.g., 0"),
    "fenwick": ("int", "Dummy indicator whether event is a fenwick event, e.g., 1"),
    "fenwick_adj": ("float", "Score- and venue-adjusted value for a fenwick event, e.g., 1.0"),
    "hd_fenwick": ("int", "Dummy indicator whether event is a high-danger fenwick event, e.g., 0"),
    "corsi": ("int", "Dummy indicator whether event is a corsi event, e.g., 1"),
    "corsi_adj": ("float", "Score- and venue-adjusted value for a corsi event, e.g., 1.0"),
    "block": ("int", "Dummy indicator whether event is a block, e.g., 0"),
    "block_adj": ("float", "Score- and venue-adjusted value for a blocked shot, e.g., 0.0"),
    "teammate_block": ("int", "Dummy indicator whether event is a shot blocked by a teammate, e.g., 0"),
    "teammate_block_adj": ("float", "Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0"),
    "hit": ("int", "Dummy indicator whether event is a hit, e.g., 0"),
    "give": ("int", "Dummy indicator whether event is a give, e.g., 0"),
    "take": ("int", "Dummy indicator whether event is a take, e.g., 0"),
    "fac": ("int", "Dummy indicator whether event is a faceoff, e.g., 0"),
    "penl": ("int", "Dummy indicator whether event is a penalty, e.g., 0"),
    "change": ("int", "Dummy indicator whether event is a change, e.g., 0"),
    "stop": ("int", "Dummy indicator whether event is a stop, e.g., 0"),
    "chl": ("int", "Dummy indicator whether event is a challenge, e.g., 0"),
    "ozf": ("int", "Dummy indicator whether event is a offensive zone faceoff, e.g., 0"),
    "nzf": ("int", "Dummy indicator whether event is a neutral zone faceoff, e.g., 0"),
    "dzf": ("int", "Dummy indicator whether event is a defensive zone faceoff, e.g., 0"),
    "ozc": ("int", "Dummy indicator whether event is a offensive zone change, e.g., 0"),
    "nzc": ("int", "Dummy indicator whether event is a neutral zone change, e.g., 0"),
    "dzc": ("int", "Dummy indicator whether event is a defensive zone change, e.g., 0"),
    "otf": ("int", "Dummy indicator whether event is an on-the-fly change, e.g., 0"),
    "pen0": ("int", "Dummy indicator whether event is a penalty, e.g., 0"),
    "pen2": ("int", "Dummy indicator whether event is a minor penalty, e.g., 0"),
    "pen4": ("int", "Dummy indicator whether event is a double minor penalty, e.g., 0"),
    "pen5": ("int", "Dummy indicator whether event is a major penalty, e.g., 0"),
    "pen10": ("int", "Dummy indicator whether event is a game misconduct penalty, e.g., 0"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for extended play-by-play data
# ---------------------------------------------------------------------------

_PBP_EXT_FIELDS: dict[str, tuple[str, str]] = {
    "id": ("int", "Unique play identifier — game_id and event_idx concatenated, e.g., 20190206840667"),
    "event_idx": ("int", "Index ID for event, e.g., 667"),
    **_player_slots("event_on"),
    **_player_slots("opp_on"),
    **_player_slots("change_on"),
    **_player_slots("change_off"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for API events data
# ---------------------------------------------------------------------------

_API_EVENTS_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    **_TIMING_FIELDS,
    "event_team": ("str", "Team that performed the action for the event, e.g., NSH"),
    "event": ("str", "Type of event that occurred, e.g., GOAL"),
    "event_code": ("str", "Code to indicate type of event that occurred, e.g., 505"),
    "description": ("str | None", "Description of the event, e.g., None"),
    "coords_x": ("int", "x-coordinates where the event occurred, e.g, -96"),
    "coords_y": ("int", "y-coordinates where the event occurred, e.g., 11"),
    "zone": ("str", "Zone where the event occurred, relative to the event team, e.g., D"),
    "player_1": ("str", "Player that performed the action, e.g., PEKKA RINNE"),
    "player_1_eh_id": ("str", "Evolving Hockey ID for player_1, e.g., PEKKA.RINNE"),
    "player_1_position": ("str", "Position player_1 plays, e.g., G"),
    "player_1_type": ("str", "Type of player, e.g., GOAL SCORER"),
    "player_1_api_id": ("int", "NHL API ID for player_1, e.g., 8471469"),
    "player_1_team_jersey": ("str", "Combination of team and jersey used for player identification, e.g., NSH35"),
    "player_2": ("str | None", "Player that performed the action, e.g., None"),
    "player_2_eh_id": ("str | None", "Evolving Hockey ID for player_2, e.g., None"),
    "player_2_position": ("str | None", "Position player_2 plays, e.g., None"),
    "player_2_type": ("str | None", "Type of player, e.g., None"),
    "player_2_api_id": ("str | None", "NHL API ID for player_2, e.g., None"),
    "player_2_team_jersey": ("str | None", "Combination of team and jersey used for player identification, e.g., None"),
    "player_3": ("str | None", "Player that performed the action, e.g., None"),
    "player_3_eh_id": ("str | None", "Evolving Hockey ID for player_3, e.g., None"),
    "player_3_position": ("str | None", "Position player_3 plays, e.g., None"),
    "player_3_type": ("str | None", "Type of player, e.g., None"),
    "player_3_api_id": ("str | None", "NHL API ID for player_3, e.g., None"),
    "player_3_team_jersey": ("str | None", "Combination of team and jersey used for player identification, e.g., None"),
    "strength": ("int", "Code to indicate strength state, e.g., 1560"),
    "shot_type": ("str | None", "Type of shot taken, if event is a shot, e.g., WRIST"),
    "miss_reason": ("str | None", "Reason shot missed, e.g., None"),
    "opp_goalie": ("str | None", "Opposing goalie, e.g., None"),
    "opp_goalie_eh_id": ("str | None", "Evolving Hockey ID for opposing goalie, e.g., None"),
    "opp_goalie_api_id": ("str | None", "NHL API ID for opposing goalie, e.g., None"),
    "opp_goalie_team_jersey": (
        "str | None",
        "Combination of team and jersey used for player identification, e.g., None",
    ),
    "event_team_id": ("int", "NHL ID for the event team, e.g., 18"),
    "stoppage_reason": ("str | None", "Reason the play was stopped, e.g., None"),
    "stoppage_reason_secondary": ("str | None", "Secondary reason play was stopped, e.g., None"),
    "penalty_type": ("str | None", "Type of penalty taken, e.g., None"),
    "penalty_reason": ("str | None", "Reason for the penalty, e.g., None"),
    "penalty_duration": ("int | None", "Duration of the penalty, e.g., None"),
    "home_team_defending_side": ("str", "Side of the ice the home team is defending, e.g., right"),
    "version": ("int", "Increases with simultaneous events, used for combining events in the scraper, e.g., 1"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for API rosters data
# ---------------------------------------------------------------------------

_API_ROSTERS_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    "team": ("str", "Team name, e.g., NSH"),
    "team_venue": ("str", "Whether team is home or away, e.g., AWAY"),
    "player_name": ("str", "Player's name, e.g., FILIP FORSBERG"),
    "eh_id": ("str", "Evolving Hockey ID for the player, e.g., FILIP.FORSBERG"),
    "api_id": ("str", "NHL API ID for the player, e.g., 8476887"),
    "team_jersey": ("str", "Team and jersey combination used for player identification, e.g., NSH9"),
    "position": ("str", "Player's position, e.g., L"),
    "first_name": ("str", "Player's first name, e.g., FILIP"),
    "last_name": ("str", "Player's last name, e.g., FORSBERG"),
    "headshot_url": ("str", "URL to retrieve player's headshot"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for HTML events data
# ---------------------------------------------------------------------------

_HTML_EVENTS_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    "event_idx": ("int", "Index ID for event, e.g., 331"),
    "period": ("int", "Period number of the event, e.g., 3"),
    "period_time": ("str", "Time elapsed in the period, e.g., 19:38"),
    "period_seconds": ("int", "Time elapsed in the period, in seconds, e.g., 1178"),
    "game_seconds": ("int", "Time elapsed in the game, in seconds, e.g., 3578"),
    "event_team": ("str", "Team that performed the action for the event, e.g., NSH"),
    "event": ("str", "Type of event that occurred, e.g., GOAL"),
    "description": ("str | None", "Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT."),
    "player_1": ("str", "Player that performed the action, e.g., PEKKA RINNE"),
    "player_1_eh_id": ("str", "Evolving Hockey ID for player_1, e.g., PEKKA.RINNE"),
    "player_1_position": ("str", "Position player_1 plays, e.g., G"),
    "player_2": ("str | None", "Player that performed the action, e.g., None"),
    "player_2_eh_id": ("str | None", "Evolving Hockey ID for player_2, e.g., None"),
    "player_2_position": ("str | None", "Position player_2 plays, e.g., None"),
    "player_3": ("str | None", "Player that performed the action, e.g., None"),
    "player_3_eh_id": ("str | None", "Evolving Hockey ID for player_3, e.g., None"),
    "player_3_position": ("str | None", "Position player_3 plays, e.g., None"),
    "zone": ("str", "Zone where the event occurred, relative to the event team, e.g., DEF"),
    "shot_type": ("str | None", "Type of shot taken, if event is a shot, e.g., WRIST"),
    "penalty_length": ("str | None", "Duration of the penalty, e.g., None"),
    "penalty": ("str | None", "Reason for the penalty, e.g., None"),
    "strength": ("str | None", "Code to indicate strength state, e.g., EV"),
    "away_skaters": ("str", "Away skaters on-ice, e.g., 13C, 19C, 64C, 14D, 59D, 35G"),
    "home_skaters": ("str", "Home skaters on-ice, e.g., 19C, 77C, 12R, 88R, 2D, 56D"),
    "version": ("int", "Increases with simultaneous events, used for combining events in the scraper, e.g., 1"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for HTML rosters data
# ---------------------------------------------------------------------------

_HTML_ROSTERS_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    "team": ("str", "Team name, e.g., NSH"),
    "team_name": ("str", "Full team name, e.g., NASHVILLE PREDATORS"),
    "team_venue": ("str", "Whether team is home or away, e.g., AWAY"),
    "player_name": ("str", "Player's name, e.g., FILIP FORSBERG"),
    "eh_id": ("str", "Evolving Hockey ID for the player, e.g., FILIP.FORSBERG"),
    "team_jersey": ("str", "Team and jersey combination used for player identification, e.g., NSH9"),
    "jersey": ("int", "Player's jersey number, e.g., 9"),
    "position": ("str", "Player's position, e.g., L"),
    "starter": ("int", "Whether the player started the game, e.g., 0"),
    "status": ("str", "Whether player is active or scratched, e.g., ACTIVE"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for combined rosters data
# ---------------------------------------------------------------------------

_ROSTERS_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    "team": ("str", "Team name, e.g., NSH"),
    "team_name": ("str", "Full team name, e.g., NASHVILLE PREDATORS"),
    "team_venue": ("str", "Whether team is home or away, e.g., AWAY"),
    "player_name": ("str", "Player's name, e.g., FILIP FORSBERG"),
    "api_id": ("int | None", "Player's NHL API ID, e.g., 8476887"),
    "eh_id": ("str", "Evolving Hockey ID for the player, e.g., FILIP.FORSBERG"),
    "team_jersey": ("str", "Team and jersey combination used for player identification, e.g., NSH9"),
    "jersey": ("int", "Player's jersey number, e.g., 9"),
    "position": ("str", "Player's position, e.g., L"),
    "starter": ("int", "Whether the player started the game, e.g., 0"),
    "status": ("str", "Whether player is active or scratched, e.g., ACTIVE"),
    "headshot_url": (
        "str | None",
        "URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png",
    ),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for HTML shifts data
# ---------------------------------------------------------------------------

_SHIFTS_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    "team": ("str", "Team name, e.g., NSH"),
    "team_name": ("str", "Full team name, e.g., NASHVILLE PREDATORS"),
    "player_name": ("str", "Player's name, e.g., FILIP FORSBERG"),
    "eh_id": ("str", "Evolving Hockey ID for the player, e.g., FILIP.FORSBERG"),
    "team_jersey": ("str", "Team and jersey combination used for player identification, e.g., NSH9"),
    "position": ("str", "Player's position, e.g., L"),
    "jersey": ("int", "Player's jersey number, e.g., 9"),
    "shift_count": ("int", "Shift number for that player, e.g., 1"),
    "period": ("int", "Period number for the shift, e.g., 1"),
    "start_time": ("str", "Time shift started, e.g., 0:00"),
    "end_time": ("str", "Time shift ended, e.g., 0:18"),
    "duration": ("str", "Length of shift, e.g., 00:18"),
    "start_time_seconds": ("int", "Time shift started in seconds, e.g., 0"),
    "end_time_seconds": ("int", "Time shift ended in seconds, e.g., 18"),
    "duration_seconds": ("int", "Length of shift in seconds, e.g., 18"),
    "shift_start": ("str", "Time the shift started as the original string, e.g., 0:00 / 20:00"),
    "shift_end": ("str", "Time the shift ended as the original string, e.g., 0:18 / 19:42"),
    "goalie": ("int", "Whether player is a goalie, e.g., 0"),
    "is_home": ("int", "Whether player is home, e.g., 0"),
    "is_away": ("int", "Whether player is away, e.g., 1"),
    "team_venue": ("str", "Whether player is home or away, e.g., AWAY"),
}

# ---------------------------------------------------------------------------
# Dictionary of fields for changes data
# ---------------------------------------------------------------------------

_CHANGES_FIELDS: dict[str, tuple[str, str]] = {
    **_GAME_ID_FIELDS,
    "event_team": ("str", "Team that performed the change, e.g., NSH"),
    "event": ("str", "Type of event, e.g., CHANGE"),
    "event_type": ("str", "Type of change, e.g., AWAY CHANGE"),
    "description": (
        "str | None",
        "Description of the change, e.g.,\n"
        "PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE\n"
        "/ PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN",
    ),
    "period": ("int", "Period number of the event, e.g., 3"),
    "period_seconds": ("int", "Time elapsed in the period, in seconds, e.g., 1178"),
    "game_seconds": ("int", "Time elapsed in the game, in seconds, e.g., 3578"),
    "change_on_count": ("int", "Number of players on, e.g., 4"),
    "change_off_count": ("int", "Number of players off, e.g., 4"),
    "change_on": ("str", "Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE"),
    "change_on_jersey": ("str", "Jerseys for the players on, e.g., NSH14, NSH19, NSH64, NSH95"),
    "change_on_eh_id": (
        "str",
        "Evolving Hockey IDs of the players on, e.g.,\nMATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE",
    ),
    "change_on_positions": ("str", "Positions of the players on, e.g., D, C, C, C"),
    "change_off": ("str", "Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN"),
    "change_off_jersey": ("str", "Jerseys for the players off, e.g., NSH7, NSH9, NSH33, NSH92"),
    "change_off_eh_id": (
        "str",
        "Evolving Hockey IDs of the players off, e.g.,\nYANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN",
    ),
    "change_off_positions": ("str", "Positions of the players off, e.g., D, L, L, C"),
    "change_on_forwards_count": ("int", "Number of forwards on, e.g., 3"),
    "change_off_forwards_count": ("int", "Number of forwards off, e.g., 3"),
    "change_on_forwards": ("str", "Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE"),
    "change_on_forwards_jersey": ("str", "Jerseys for the forwards on, e.g., NSH19, NSH64, NSH95"),
    "change_on_forwards_eh_id": (
        "str",
        "Evolving Hockey IDs of the forwards on, e.g.,\nCALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE",
    ),
    "change_off_forwards": ("str", "Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN"),
    "change_off_forwards_jersey": ("str", "Jerseys for the forwards off, e.g., NSH9, NSH33, NSH92"),
    "change_off_forwards_eh_id": (
        "str",
        "Evolving Hockey IDs of the forwards off, e.g.,\nFILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN",
    ),
    "change_on_defense_count": ("int", "Number of defense on, e.g., 1"),
    "change_off_defense_count": ("int", "Number of defense off, e.g., 1"),
    "change_on_defense": ("str", "Names of defense on, e.g., MATTIAS EKHOLM"),
    "change_on_defense_jersey": ("str", "Jerseys for the defense on, e.g., NSH14"),
    "change_on_defense_eh_id": ("str", "Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM"),
    "change_off_defense": ("str", "Names of defense off, e.g., YANNICK WEBER"),
    "change_off_defense_jersey": ("str", "Jerseys for the defense off, e.g., NSH7"),
    "change_off_defense_eh_id": ("str", "Evolving Hockey IDs of the defense off, e.g., YANNICK.WEBER"),
    "change_on_goalie_count": ("int", "Number of goalies on, e.g., 0"),
    "change_off_goalie_count": ("int", "Number of goalies off, e.g., 0"),
    "change_on_goalies": ("str", "Names of goalies on, e.g., None"),
    "change_on_goalies_jersey": ("str", "Jerseys for the goalies on, e.g., None"),
    "change_on_goalies_eh_id": ("str", "Evolving Hockey IDs of the goalies on, e.g., None"),
    "change_off_goalies": ("str", "Names of goalies off, e.g., None"),
    "change_off_goalies_jersey": ("str", "Jerseys for the goalies off, e.g., None"),
    "change_off_goalies_eh_id": ("str", "Evolving Hockey IDs of the goalies off, e.g., None"),
    "is_home": ("int", "Whether change team is home, e.g., 0"),
    "is_away": ("int", "Whether change team is away, e.g., 1"),
    "team_venue": ("str", "Whether team is home or away, e.g., AWAY"),
}


# ---------------------------------------------------------------------------
# Play-by-play docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_PLAY_BY_PLAY_DOC = f"""\
List of events in play-by-play. Each event is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).play_by_play_df``

{_build_returns(_PBP_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.play_by_play

    You can access the data as a dataframe by appending _df
    >>> game.play_by_play_df

"""

_GAME_PLAY_BY_PLAY_DF_DOC = f"""\
DataFrame of play-by-play data, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").play_by_play_df``.
    This has the same fields as ``game.play_by_play``

{_build_returns(_PBP_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.play_by_play_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.play_by_play_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.play_by_play_df    # narwhals DataFrame
"""

_GAME_PLAY_BY_PLAY_EXT_DOC = f"""\
List of on-ice player slots used internally for aggregating on-ice statistics. Each slot is a dictionary with the below keys.

{_build_returns(_PBP_EXT_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.play_by_play_ext
"""

_SCRAPER_PLAY_BY_PLAY_DOC = f"""\
DataFrame of play-by-play data, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").play_by_play``

{_build_returns(_PBP_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.play_by_play

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.play_by_play    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.play_by_play    # narwhals DataFrame
"""

_SCRAPER_PLAY_BY_PLAY_EXT_DOC = f"""\
DataFrame of on-ice player slots used internally for aggregating on-ice statistics.

{_build_returns(_PBP_EXT_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.play_by_play_ext

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.play_by_play_ext    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.play_by_play_ext    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# API events docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_API_EVENTS_DOC = f"""\
List of events scraped from the API endpoint. Each event is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).api_events_df``

{_build_returns(_API_EVENTS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.api_events

    You can access the data as a dataframe by appending _df
    >>> game.api_events_df
"""

_GAME_API_EVENTS_DF_DOC = f"""\
DataFrame of events scraped from the API endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation., i.e., ``Game(2019020684, backend="pandas").api_events_df``.
    This has the same fields as ``game.api_events``

{_build_returns(_API_EVENTS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.api_events_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.api_events_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.api_events_df    # narwhals DataFrame
"""

_SCRAPER_API_EVENTS_DOC = f"""\
DataFrame of events scraped from the API endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").api_events``

{_build_returns(_API_EVENTS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.api_events

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.api_events    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.api_events    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# API rosters docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_API_ROSTERS_DOC = f"""\
List of players scraped from the API endpoint. Each player is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).api_rosters_df``

{_build_returns(_API_ROSTERS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.api_rosters

    You can access the data as a dataframe by appending _df
    >>> game.api_rosters_df
"""

_GAME_API_ROSTERS_DF_DOC = f"""\
DataFrame of players scraped from the API endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").api_rosters_df``.
    This has the same fields as ``game.api_rosters``

{_build_returns(_API_ROSTERS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.api_rosters_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.api_rosters_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.api_rosters_df    # narwhals DataFrame
"""

_SCRAPER_API_ROSTERS_DOC = f"""\
DataFrame of players scraped from the API endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").api_rosters``

{_build_returns(_API_ROSTERS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.api_rosters

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.api_rosters    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.api_rosters    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# HTML events docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_HTML_EVENTS_DOC = f"""\
List of events scraped from the HTML endpoint. Each event is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).html_events_df``

{_build_returns(_HTML_EVENTS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.html_events

    You can access the data as a dataframe by appending _df
    >>> game.html_events_df
"""

_GAME_HTML_EVENTS_DF_DOC = f"""\
DataFrame of events scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").html_events_df``.
    This has the same fields as ``game.html_events``

{_build_returns(_HTML_EVENTS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.html_events_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.html_events_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.html_events_df    # narwhals DataFrame
"""

_SCRAPER_HTML_EVENTS_DOC = f"""\
DataFrame of events scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").html_events``

{_build_returns(_HTML_EVENTS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.html_events

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.html_events    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.html_events    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# HTML rosters docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_HTML_ROSTERS_DOC = f"""\
List of players scraped from the HTML endpoint. Each player is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).html_rosters_df``

{_build_returns(_HTML_ROSTERS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.html_rosters

    You can access the data as a dataframe by appending _df
    >>> game.html_rosters_df
"""

_GAME_HTML_ROSTERS_DF_DOC = f"""\
DataFrame of players scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").html_rosters_df``.
    This has the same fields as ``game.html_rosters``

{_build_returns(_HTML_ROSTERS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.html_rosters_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.html_rosters_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.html_rosters_df    # narwhals DataFrame
"""

_SCRAPER_HTML_ROSTERS_DOC = f"""\
DataFrame of players scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").html_rosters``

{_build_returns(_HTML_ROSTERS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.html_rosters

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.html_rosters    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.html_rosters    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# Rosters docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_ROSTERS_DOC = f"""\
List of players scraped from the API and HTML endpoints combined. Each player is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).rosters_df``

{_build_returns(_ROSTERS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.rosters

    You can access the data as a dataframe by appending _df
    >>> game.rosters_df
"""

_GAME_ROSTERS_DF_DOC = f"""\
DataFrame of players scraped from the API and HTML endpoints combined, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").rosters_df``.
    This has the same fields as ``game.rosters``

{_build_returns(_ROSTERS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.rosters_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.rosters_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.rosters_df    # narwhals DataFrame
"""

_SCRAPER_ROSTERS_DOC = f"""\
DataFrame of players scraped from the API and HTML endpoints combined, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").rosters``

{_build_returns(_ROSTERS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.rosters

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.rosters    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.rosters    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# Shifts docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_SHIFTS_DOC = f"""\
List of shifts scraped from the HTML endpoint. Each shift is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).shifts_df``

{_build_returns(_SHIFTS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.shifts

    You can access the data as a dataframe by appending _df
    >>> game.shifts_df
"""

_GAME_SHIFTS_DF_DOC = f"""\
DataFrame of shifts scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").shifts_df``.
    This has the same fields as ``game.shifts``

{_build_returns(_SHIFTS_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.shifts_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.shifts_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.shifts_df    # narwhals DataFrame
"""

_SCRAPER_SHIFTS_DOC = f"""\
DataFrame of shifts scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").shifts``

{_build_returns(_SHIFTS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.shifts

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.shifts    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.shifts    # narwhals DataFrame
"""

# ---------------------------------------------------------------------------
# Changes docstrings in Game and Scraper objects
# ---------------------------------------------------------------------------

_GAME_CHANGES_DOC = f"""\
List of line changes scraped from the HTML endpoint. Each change is a dictionary with the below keys.

Note:
    You can return any of the properties as a polars, pandas, pyarrow, or narwhals DataFrame by appending
    ``_df`` to the property, e.g., ``Game(2019020684).changes_df``

{_build_returns(_CHANGES_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the property, as a list of dictionaries
    >>> game.changes

    You can access the data as a dataframe by appending _df
    >>> game.changes_df
"""

_GAME_CHANGES_DF_DOC = f"""\
DataFrame of line changes scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Game class instantiation, i.e., ``Game(2019020684, backend="pandas").changes_df``.
    This has the same fields as ``game.changes``

{_build_returns(_CHANGES_FIELDS)}

Examples:
    First, instantiate the class with a game ID
    >>> from chickenstats.chicken_nhl import Game
    >>> game_id = 2019020684
    >>> game = Game(game_id)

    Then you can access the data as a dataframe
    >>> game.changes_df

    You can change the backend at the time of class instantiation
    >>> game = Game(game_id, backend="pandas")
    >>> game.changes_df    # pandas DataFrame

    As a narwhals dataframe
    >>> game = Game(game_id, backend="narwhals")
    >>> game.changes_df    # narwhals DataFrame
"""

_SCRAPER_CHANGES_DOC = f"""\
DataFrame of line changes scraped from the HTML endpoint, with the below fields.

Note:
    You can determine whether the dataframe is from polars, pandas, pyarrow, or narwhals library with the "backend" argument
    at the time of the Scraper class instantiation, i.e., ``Scraper(2019020684, backend="pandas").changes``

{_build_returns(_CHANGES_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> game_id = 2019020684
    >>> scraper = Scraper(game_id)

    Then you can access the data
    >>> scraper.changes

    You can also instantiate the Scraper object with a list of game IDs
    >>> game_ids = [2019020684, 2019020685]
    >>> scraper = Scraper(game_ids)

    You can change the backend at the time of class instantiation
    >>> scraper = Scraper(game_id, backend="pandas")
    >>> scraper.changes    # pandas DataFrame

    As a narwhals dataframe
    >>> scraper = Scraper(game_id, backend="narwhals")
    >>> scraper.changes    # narwhals DataFrame
"""
