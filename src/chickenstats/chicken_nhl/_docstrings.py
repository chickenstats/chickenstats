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
        "Evolving Hockey IDs of away team's skaters on-ice (incl. goalies), e.g.,\n"
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

# ---------------------------------------------------------------------------
# _build_params — analogous to _build_returns, produces a Parameters: block
# ---------------------------------------------------------------------------


def _build_params(fields: dict[str, tuple[str, str]]) -> str:
    """Render a Google-style ``Parameters:`` block from a parameter registry dict.

    Parameters:
        fields: Ordered mapping of ``param_name -> (type_str, description)``.

    Returns:
        str: A ``Parameters:`` block ready for embedding in a docstring constant.
    """
    lines = ["Parameters:"]
    for name, (type_str, desc) in fields.items():
        lines.append(f"    {name} ({type_str}):")
        for dline in desc.split("\n"):
            lines.append(f"        {dline}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parameter registries — shared across stats methods
# ---------------------------------------------------------------------------

_STATS_COMMON_PARAMS: dict[str, tuple[str, str]] = {
    "level": (
        "AggLevel | Literal['period', 'game', 'session', 'season']",
        "Aggregation level. One of ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``",
    ),
    "strength_state": ("bool", "Whether to split by strength state (5v5, 5v4, etc.). Default ``True``"),
    "score": ("bool", "Whether to split by score state (leading, tied, trailing). Default ``False``"),
    "teammates": ("bool", "Whether to split by teammate lineup. Default ``False``"),
    "opposition": ("bool", "Whether to split by opposing lineup. Default ``False``"),
}

_PREP_PROGRESS_PARAMS: dict[str, tuple[str, str]] = {
    "disable_progress_bar": (
        "bool | None",
        "Override the Scraper-level ``disable_progress_bar`` setting for this call. Default ``None``",
    ),
    "transient_progress_bar": (
        "bool | None",
        "Override the Scraper-level ``transient_progress_bar`` setting for this call. Default ``None``",
    ),
}

_LINES_POSITION_PARAM: dict[str, tuple[str, str]] = {
    "position": (
        "Literal['f', 'd']",
        "Whether to aggregate forward (``'f'``) or defense (``'d'``) lines. Default ``'f'``",
    )
}

# ---------------------------------------------------------------------------
# Context field registries — shared identity / lineup columns
# ---------------------------------------------------------------------------

_STATS_PLAYER_CONTEXT_FIELDS: dict[str, tuple[str, str]] = {
    "season": ("int", "Season as 8-digit number, e.g., 2023 for 2023-24 season"),
    "session": ("str", "Whether game is regular season, playoffs, or pre-season, e.g., R"),
    "game_id": ("int", "Unique game ID assigned by the NHL, e.g., 2023020001"),
    "game_date": ("str", "Date game was played, e.g., 2023-10-10"),
    "player": ("str", "Player's name, e.g., FILIP FORSBERG"),
    "eh_id": ("str", "Evolving Hockey ID for the player, e.g., FILIP.FORSBERG"),
    "api_id": ("str", "NHL API ID for the player, e.g., 8476887"),
    "position": ("str", "Player's position, e.g., L"),
    "team": ("str", "Player's team, e.g., NSH"),
    "opp_team": ("str", "Opposing team, e.g., TBL"),
    "strength_state": ("str", "Strength state, e.g., 5v5"),
    "period": ("int", "Period, e.g., 3"),
    "score_state": ("str", "Score state, e.g., 2v1"),
    "forwards": ("str", "Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY"),
    "forwards_eh_id": (
        "str",
        "Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY",
    ),
    "forwards_api_id": ("str", "Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158"),
    "defense": ("str", "Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER"),
    "defense_eh_id": ("str", "Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER"),
    "defense_api_id": ("str", "Defense teammates' NHL API IDs, e.g., 8474151, 8478851"),
    "own_goalie": ("str", "Own goalie, e.g., JUUSE SAROS"),
    "own_goalie_eh_id": ("str", "Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS"),
    "own_goalie_api_id": ("str", "Own goalie's NHL API ID, e.g., 8477424"),
    "opp_forwards": ("str", "Opposing forwards, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS"),
    "opp_forwards_eh_id": (
        "str",
        "Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS",
    ),
    "opp_forwards_api_id": ("str", "Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564"),
    "opp_defense": ("str", "Opposing defense, e.g., NICK PERBIX, VICTOR HEDMAN"),
    "opp_defense_eh_id": ("str", "Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN"),
    "opp_defense_api_id": ("str", "Opposing defense's NHL API IDs, e.g., 8480246, 8475167"),
    "opp_goalie": ("str", "Opposing goalie, e.g., JONAS JOHANSSON"),
    "opp_goalie_eh_id": ("str", "Opposing goalie's Evolving Hockey ID, e.g., JONAS.JOHANSSON"),
    "opp_goalie_api_id": ("str", "Opposing goalie's NHL API ID, e.g., 8477992"),
}

_LINES_CONTEXT_FIELDS: dict[str, tuple[str, str]] = {
    "season": ("int", "Season as 8-digit number, e.g., 2023 for 2023-24 season"),
    "session": ("str", "Whether game is regular season, playoffs, or pre-season, e.g., R"),
    "game_id": ("int", "Unique game ID assigned by the NHL, e.g., 2023020001"),
    "game_date": ("str", "Date game was played, e.g., 2023-10-10"),
    "team": ("str", "Team, e.g., NSH"),
    "opp_team": ("str", "Opposing team, e.g., TBL"),
    "strength_state": ("str", "Strength state, e.g., 5v5"),
    "period": ("int", "Period, e.g., 3"),
    "score_state": ("str", "Score state, e.g., 2v1"),
    "forwards": ("str", "Forward line members, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY"),
    "forwards_eh_id": (
        "str",
        "Forward line members' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY",
    ),
    "forwards_api_id": ("str", "Forward line members' NHL API IDs, e.g., 8476887, 8481704, 8475158"),
    "defense": ("str", "Defense pair members, e.g., RYAN MCDONAGH, ALEX CARRIER"),
    "defense_eh_id": ("str", "Defense pair members' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER"),
    "defense_api_id": ("str", "Defense pair members' NHL API IDs, e.g., 8474151, 8478851"),
    "own_goalie": ("str", "Own goalie, e.g., JUUSE SAROS"),
    "own_goalie_eh_id": ("str", "Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS"),
    "own_goalie_api_id": ("str", "Own goalie's NHL API ID, e.g., 8477424"),
    "opp_forwards": ("str", "Opposing forwards, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS"),
    "opp_forwards_eh_id": (
        "str",
        "Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS",
    ),
    "opp_forwards_api_id": ("str", "Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564"),
    "opp_defense": ("str", "Opposing defense, e.g., NICK PERBIX, VICTOR HEDMAN"),
    "opp_defense_eh_id": ("str", "Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN"),
    "opp_defense_api_id": ("str", "Opposing defense's NHL API IDs, e.g., 8480246, 8475167"),
    "opp_goalie": ("str", "Opposing goalie, e.g., JONAS JOHANSSON"),
    "opp_goalie_eh_id": ("str", "Opposing goalie's Evolving Hockey ID, e.g., JONAS.JOHANSSON"),
    "opp_goalie_api_id": ("str", "Opposing goalie's NHL API ID, e.g., 8477992"),
}

_TEAM_STATS_CONTEXT_FIELDS: dict[str, tuple[str, str]] = {
    "season": ("int", "Season as 8-digit number, e.g., 2023 for 2023-24 season"),
    "session": ("str", "Whether game is regular season, playoffs, or pre-season, e.g., R"),
    "game_id": ("int", "Unique game ID assigned by the NHL, e.g., 2023020001"),
    "team": ("str", "Team, e.g., NSH"),
    "opp_team": ("str", "Opposing team, e.g., TBL"),
    "strength_state": ("str", "Strength state, e.g., 5v5"),
    "period": ("int", "Period, e.g., 3"),
    "score_state": ("str", "Score state, e.g., 2v1"),
}

# ---------------------------------------------------------------------------
# Stat field registries — counting, per-60, and percentage columns
# ---------------------------------------------------------------------------

_IND_STATS_FIELDS: dict[str, tuple[str, str]] = {
    "g": ("int", "Individual goals scored, e.g., 0"),
    "g_adj": ("float", "Score- and venue-adjusted individual goals scored, e.g., 0.0"),
    "ihdg": ("int", "Individual high-danger goals scored, e.g., 0"),
    "a1": ("int", "Individual primary assists, e.g., 0"),
    "a2": ("int", "Individual secondary assists, e.g., 0"),
    "ixg": ("float", "Individual xG for, e.g., 1.014336"),
    "ixg_adj": ("float", "Score- and venue-adjusted individual xG for, e.g., 1.101715"),
    "isf": ("int", "Individual shots taken, e.g., 3"),
    "isf_adj": ("float", "Score- and venue-adjusted individual shots taken, e.g., 3.262966"),
    "ihdsf": ("int", "High-danger shots taken, e.g., 3"),
    "imsf": ("int", "Individual missed shots, e.g., 0"),
    "imsf_adj": ("float", "Score- and venue-adjusted individual missed shots, e.g., 0.0"),
    "ihdm": ("int", "High-danger missed shots, e.g., 0"),
    "iff": ("int", "Individual fenwick for, e.g., 3"),
    "iff_adj": ("float", "Score- and venue-adjusted individual fenwick events, e.g., 3.279018"),
    "ihdf": ("int", "High-danger fenwick events for, e.g., 3"),
    "isb": ("int", "Shots taken that were blocked, e.g., 0"),
    "isb_adj": ("float", "Score- and venue-adjusted individual shots blocked, e.g., 0.0"),
    "icf": ("int", "Individual corsi for, e.g., 3"),
    "icf_adj": ("float", "Score- and venue-adjusted individual corsi events, e.g., 3.279018"),
    "ibs": ("int", "Individual shots blocked on defense, e.g., 0"),
    "ibs_adj": ("float", "Score- and venue-adjusted shots blocked, e.g., 0.0"),
    "igive": ("int", "Individual giveaways, e.g., 0"),
    "itake": ("int", "Individual takeaways, e.g., 0"),
    "ihf": ("int", "Individual hits for, e.g., 0"),
    "iht": ("int", "Individual hits taken, e.g., 0"),
    "ifow": ("int", "Individual faceoffs won, e.g., 0"),
    "ifol": ("int", "Individual faceoffs lost, e.g., 0"),
    "iozfw": ("int", "Individual faceoffs won in offensive zone, e.g., 0"),
    "iozfl": ("int", "Individual faceoffs lost in offensive zone, e.g., 0"),
    "inzfw": ("int", "Individual faceoffs won in neutral zone, e.g., 0"),
    "inzfl": ("int", "Individual faceoffs lost in neutral zone, e.g., 0"),
    "idzfw": ("int", "Individual faceoffs won in defensive zone, e.g., 0"),
    "idzfl": ("int", "Individual faceoffs lost in defensive zone, e.g., 0"),
    "a1_xg": ("float", "xG on primary assists, e.g., 0"),
    "a2_xg": ("float", "xG on secondary assists, e.g., 0"),
    "ipent0": ("int", "Individual penalty shots against, e.g., 0"),
    "ipent2": ("int", "Individual minor penalties taken, e.g., 0"),
    "ipent4": ("int", "Individual double minor penalties taken, e.g., 0"),
    "ipent5": ("int", "Individual major penalties taken, e.g., 0"),
    "ipent10": ("int", "Individual game misconduct penalties taken, e.g., 0"),
    "ipend0": ("int", "Individual penalty shots drawn, e.g., 0"),
    "ipend2": ("int", "Individual minor penalties drawn, e.g., 0"),
    "ipend4": ("int", "Individual double minor penalties drawn, e.g., 0"),
    "ipend5": ("int", "Individual major penalties drawn, e.g., 0"),
    "ipend10": ("int", "Individual game misconduct penalties drawn, e.g., 0"),
}

_TOI_FIELD: dict[str, tuple[str, str]] = {"toi": ("float", "Time on-ice, in minutes, e.g., 0.483333")}

_OI_STATS_COUNTING_FIELDS: dict[str, tuple[str, str]] = {
    "gf": ("int", "Goals for (on-ice), e.g., 0"),
    "ga": ("int", "Goals against (on-ice), e.g., 0"),
    "gf_adj": ("float", "Score- and venue-adjusted goals for (on-ice), e.g., 0.0"),
    "ga_adj": ("float", "Score- and venue-adjusted goals against (on-ice), e.g., 0.0"),
    "hdgf": ("int", "High-danger goals for (on-ice), e.g., 0"),
    "hdga": ("int", "High-danger goals against (on-ice), e.g., 0"),
    "xgf": ("float", "xG for (on-ice), e.g., 1.258332"),
    "xga": ("float", "xG against (on-ice), e.g., 0.000000"),
    "xgf_adj": ("float", "Score- and venue-adjusted xG for (on-ice), e.g., 1.366730"),
    "xga_adj": ("float", "Score- and venue-adjusted xG against (on-ice), e.g., 0.0"),
    "sf": ("int", "Shots for (on-ice), e.g., 4"),
    "sa": ("int", "Shots against (on-ice), e.g., 0"),
    "sf_adj": ("float", "Score- and venue-adjusted shots for (on-ice), e.g., 4.350622"),
    "sa_adj": ("float", "Score- and venue-adjusted shots against (on-ice), e.g., 0.0"),
    "hdsf": ("int", "High-danger shots for (on-ice), e.g., 3"),
    "hdsa": ("int", "High-danger shots against (on-ice), e.g., 0"),
    "ff": ("int", "Fenwick for (on-ice), e.g., 4"),
    "fa": ("int", "Fenwick against (on-ice), e.g., 0"),
    "ff_adj": ("float", "Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024"),
    "fa_adj": ("float", "Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0"),
    "hdff": ("int", "High-danger fenwick for (on-ice), e.g., 3"),
    "hdfa": ("int", "High-danger fenwick against (on-ice), e.g., 0"),
    "cf": ("int", "Corsi for (on-ice), e.g., 4"),
    "ca": ("int", "Corsi against (on-ice), e.g., 0"),
    "cf_adj": ("float", "Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024"),
    "ca_adj": ("float", "Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0"),
    "bsf": ("int", "Shots taken that were blocked (on-ice), e.g., 0"),
    "bsa": ("int", "Shots blocked (on-ice), e.g., 0"),
    "bsf_adj": ("float", "Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0"),
    "bsa_adj": ("float", "Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0"),
    "msf": ("int", "Missed shots taken (on-ice), e.g., 0"),
    "msa": ("int", "Missed shots against (on-ice), e.g., 0"),
    "msf_adj": ("float", "Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0"),
    "msa_adj": ("float", "Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0"),
    "hdmsf": ("int", "High-danger missed shots taken (on-ice), e.g., 0"),
    "hdmsa": ("int", "High-danger missed shots against (on-ice), e.g., 0"),
    "teammate_block": ("int", "Shots blocked by teammates (on-ice), e.g., 0"),
    "teammate_block_adj": ("float", "Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0"),
    "hf": ("int", "Hits for (on-ice), e.g., 0"),
    "ht": ("int", "Hits taken (on-ice), e.g., 0"),
    "give": ("int", "Giveaways (on-ice), e.g., 0"),
    "take": ("int", "Takeaways (on-ice), e.g., 0"),
    "ozf": ("int", "Offensive zone faceoffs (on-ice), e.g., 0"),
    "nzf": ("int", "Neutral zone faceoffs (on-ice), e.g., 1"),
    "dzf": ("int", "Defensive zone faceoffs (on-ice), e.g., 0"),
    "fow": ("int", "Faceoffs won (on-ice), e.g., 1"),
    "fol": ("int", "Faceoffs lost (on-ice), e.g., 0"),
    "ozfw": ("int", "Offensive zone faceoffs won (on-ice), e.g., 0"),
    "ozfl": ("int", "Offensive zone faceoffs lost (on-ice), e.g., 0"),
    "nzfw": ("int", "Neutral zone faceoffs won (on-ice), e.g., 1"),
    "nzfl": ("int", "Neutral zone faceoffs lost (on-ice), e.g., 0"),
    "dzfw": ("int", "Defensive zone faceoffs won (on-ice), e.g., 0"),
    "dzfl": ("int", "Defensive zone faceoffs lost (on-ice), e.g., 0"),
    "pent0": ("int", "Penalty shots allowed (on-ice), e.g., 0"),
    "pent2": ("int", "Minor penalties taken (on-ice), e.g., 0"),
    "pent4": ("int", "Double minor penalties taken (on-ice), e.g., 0"),
    "pent5": ("int", "Major penalties taken (on-ice), e.g., 0"),
    "pent10": ("int", "Game misconduct penalties taken (on-ice), e.g., 0"),
    "pend0": ("int", "Penalty shots drawn (on-ice), e.g., 0"),
    "pend2": ("int", "Minor penalties drawn (on-ice), e.g., 0"),
    "pend4": ("int", "Double minor penalties drawn (on-ice), e.g., 0"),
    "pend5": ("int", "Major penalties drawn (on-ice), e.g., 0"),
    "pend10": ("int", "Game misconduct penalties drawn (on-ice), e.g., 0"),
}

_OI_ZONE_STARTS_FIELDS: dict[str, tuple[str, str]] = {
    "ozs": ("int", "Offensive zone starts, e.g., 0"),
    "nzs": ("int", "Neutral zone starts, e.g., 0"),
    "dzs": ("int", "Defensive zone starts, e.g., 0"),
    "otf": ("int", "On-the-fly starts, e.g., 0"),
}

_IND_P60_FIELDS: dict[str, tuple[str, str]] = {
    "g_p60": ("float", "Goals scored per 60 minutes"),
    "ihdg_p60": ("float", "Individual high-danger goals scored per 60 minutes"),
    "a1_p60": ("float", "Primary assists per 60 minutes"),
    "a2_p60": ("float", "Secondary assists per 60 minutes"),
    "ixg_p60": ("float", "Individual xG for per 60 minutes"),
    "isf_p60": ("float", "Individual shots for per 60 minutes"),
    "ihdsf_p60": ("float", "Individual high-danger shots for per 60 minutes"),
    "imsf_p60": ("float", "Individual missed shots for per 60 minutes"),
    "ihdm_p60": ("float", "Individual high-danger missed shots for per 60 minutes"),
    "iff_p60": ("float", "Individual fenwick for per 60 minutes"),
    "ihdff_p60": ("float", "Individual high-danger fenwick for per 60 minutes"),
    "isb_p60": ("float", "Individual shots blocked (for) per 60 minutes"),
    "icf_p60": ("float", "Individual corsi for per 60 minutes"),
    "ibs_p60": ("float", "Individual blocked shots (against) per 60 minutes"),
    "igive_p60": ("float", "Individual giveaways per 60 minutes"),
    "itake_p60": ("float", "Individual takeaways per 60 minutes"),
    "ihf_p60": ("float", "Individual hits for per 60 minutes"),
    "iht_p60": ("float", "Individual hits taken per 60 minutes"),
    "a1_xg_p60": ("float", "Individual primary assists' xG per 60 minutes"),
    "a2_xg_p60": ("float", "Individual secondary assists' xG per 60 minutes"),
    "ipent0_p60": ("float", "Individual penalty shots taken per 60 minutes"),
    "ipent2_p60": ("float", "Individual minor penalties taken per 60 minutes"),
    "ipent4_p60": ("float", "Individual double minor penalties taken per 60 minutes"),
    "ipent5_p60": ("float", "Individual major penalties taken per 60 minutes"),
    "ipent10_p60": ("float", "Individual game misconduct penalties taken per 60 minutes"),
    "ipend0_p60": ("float", "Individual penalty shots drawn per 60 minutes"),
    "ipend2_p60": ("float", "Individual minor penalties drawn per 60 minutes"),
    "ipend4_p60": ("float", "Individual double minor penalties drawn per 60 minutes"),
    "ipend5_p60": ("float", "Individual major penalties drawn per 60 minutes"),
    "ipend10_p60": ("float", "Individual game misconduct penalties drawn per 60 minutes"),
}

_OI_P60_FIELDS: dict[str, tuple[str, str]] = {
    "gf_p60": ("float", "Goals for (on-ice) per 60 minutes"),
    "ga_p60": ("float", "Goals against (on-ice) per 60 minutes"),
    "hdgf_p60": ("float", "High-danger goals for (on-ice) per 60 minutes"),
    "hdga_p60": ("float", "High-danger goals against (on-ice) per 60 minutes"),
    "xgf_p60": ("float", "xG for (on-ice) per 60 minutes"),
    "xga_p60": ("float", "xG against (on-ice) per 60 minutes"),
    "sf_p60": ("float", "Shots for (on-ice) per 60 minutes"),
    "sa_p60": ("float", "Shots against (on-ice) per 60 minutes"),
    "hdsf_p60": ("float", "High-danger shots for (on-ice) per 60 minutes"),
    "hdsa_p60": ("float", "High-danger shots against (on-ice) per 60 minutes"),
    "ff_p60": ("float", "Fenwick for (on-ice) per 60 minutes"),
    "fa_p60": ("float", "Fenwick against (on-ice) per 60 minutes"),
    "hdff_p60": ("float", "High-danger fenwick for (on-ice) per 60 minutes"),
    "hdfa_p60": ("float", "High-danger fenwick against (on-ice) per 60 minutes"),
    "cf_p60": ("float", "Corsi for (on-ice) per 60 minutes"),
    "ca_p60": ("float", "Corsi against (on-ice) per 60 minutes"),
    "bsf_p60": ("float", "Blocked shots for (on-ice) per 60 minutes"),
    "bsa_p60": ("float", "Blocked shots against (on-ice) per 60 minutes"),
    "msf_p60": ("float", "Missed shots for (on-ice) per 60 minutes"),
    "msa_p60": ("float", "Missed shots against (on-ice) per 60 minutes"),
    "hdmsf_p60": ("float", "High-danger missed shots for (on-ice) per 60 minutes"),
    "hdmsa_p60": ("float", "High-danger missed shots against (on-ice) per 60 minutes"),
    "teammate_block_p60": ("float", "Shots blocked by teammates (on-ice) per 60 minutes"),
    "hf_p60": ("float", "Hits for (on-ice) per 60 minutes"),
    "ht_p60": ("float", "Hits taken (on-ice) per 60 minutes"),
    "give_p60": ("float", "Giveaways (on-ice) per 60 minutes"),
    "take_p60": ("float", "Takeaways (on-ice) per 60 minutes"),
    "pent0_p60": ("float", "Penalty shots taken (on-ice) per 60 minutes"),
    "pent2_p60": ("float", "Minor penalties taken (on-ice) per 60 minutes"),
    "pent4_p60": ("float", "Double minor penalties taken (on-ice) per 60 minutes"),
    "pent5_p60": ("float", "Major penalties taken (on-ice) per 60 minutes"),
    "pent10_p60": ("float", "Game misconduct penalties taken (on-ice) per 60 minutes"),
    "pend0_p60": ("float", "Penalty shots drawn (on-ice) per 60 minutes"),
    "pend2_p60": ("float", "Minor penalties drawn (on-ice) per 60 minutes"),
    "pend4_p60": ("float", "Double minor penalties drawn (on-ice) per 60 minutes"),
    "pend5_p60": ("float", "Major penalties drawn (on-ice) per 60 minutes"),
    "pend10_p60": ("float", "Game misconduct penalties drawn (on-ice) per 60 minutes"),
}

_OI_PERCENT_FIELDS: dict[str, tuple[str, str]] = {
    "gf_percent": ("float", "On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)"),
    "hdgf_percent": (
        "float",
        "On-ice high-danger goals for as a percentage of total on-ice high-danger goals\ni.e., HDGF / (HDGF + HDGA)",
    ),
    "xgf_percent": ("float", "On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + xGA)"),
    "sf_percent": ("float", "On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)"),
    "hdsf_percent": (
        "float",
        "On-ice high-danger shots for as a percentage of total on-ice high-danger shots\ni.e., HDSF / (HDSF + HDSA)",
    ),
    "ff_percent": ("float", "On-ice fenwick for as a percentage of total on-ice fenwick i.e., FF / (FF + FA)"),
    "hdff_percent": (
        "float",
        "On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick\ni.e., HDFF / (HDFF + HDFA)",
    ),
    "cf_percent": ("float", "On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)"),
    "bsf_percent": (
        "float",
        "On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)",
    ),
    "msf_percent": (
        "float",
        "On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)",
    ),
    "hdmsf_percent": (
        "float",
        "On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots\ni.e., HDMSF / (HDMSF + HDMSA)",
    ),
    "hf_percent": ("float", "On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)"),
    "take_percent": (
        "float",
        "On-ice takeaways as a percentage of total on-ice giveaways and takeaways\ni.e., take / (take + give)",
    ),
}

# ---------------------------------------------------------------------------
# Docstring constants for stats properties and public methods
# ---------------------------------------------------------------------------

_IND_STATS_DOC = f"""\
DataFrame of individual stats aggregated from play-by-play data, with the below fields.

Note:
    You can determine the DataFrame backend with the ``backend`` argument at Scraper instantiation,
    e.g., ``Scraper(game_id, backend="pandas").ind_stats``

{_build_returns(_STATS_PLAYER_CONTEXT_FIELDS | _IND_STATS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(2023020001)

    Access individual stats (triggers play-by-play scrape if needed)
    >>> scraper.ind_stats

    Customise aggregation with prep_stats
    >>> scraper.prep_stats(level="season", teammates=True)
    >>> scraper.ind_stats

    You can also chain the prep method with the stats property you're calling
    >>> ind_stats = scraper.prep_stats(level="season").ind_stats
"""

_OI_STATS_DOC = f"""\
DataFrame of on-ice stats aggregated from play-by-play data, with the below fields.

Note:
    You can determine the DataFrame backend with the ``backend`` argument at Scraper instantiation,
    e.g., ``Scraper(game_id, backend="pandas").oi_stats``

{_build_returns(_STATS_PLAYER_CONTEXT_FIELDS | _TOI_FIELD | _OI_STATS_COUNTING_FIELDS | _OI_ZONE_STARTS_FIELDS)}

Examples:
    First, instantiate the Scraper with a game ID
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(2023020001)

    Access on-ice stats (triggers play-by-play scrape if needed)
    >>> scraper.oi_stats

    Customise aggregation with prep_stats
    >>> scraper.prep_stats(level="season", score=True)
    >>> scraper.oi_stats

    You can also chain the prep method with the stats property you're calling
    >>> oi_stats = scraper.prep_stats(level="season").oi_stats
"""

_PREP_STATS_DOC = f"""\
Prepare (or re-prepare) the combined individual + on-ice stats DataFrame.

Computes ``ind_stats`` and ``oi_stats`` concurrently via ``ThreadPoolExecutor``,
then merges them into ``stats``. Call this to change aggregation options; subsequent
accesses to ``stats``, ``ind_stats``, and ``oi_stats`` will reflect the new settings.

{_build_params(_STATS_COMMON_PARAMS | _PREP_PROGRESS_PARAMS)}

Returns:
    Self: The Scraper instance (for method chaining).

Examples:
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(list(range(2023020001, 2023020011)))

    Default game-level aggregation
    >>> scraper.prep_stats()
    >>> scraper.stats

    Season-level, split by score state
    >>> scraper.prep_stats(level="season", score=True)
    >>> scraper.stats

    Re-prepare to add teammate splits
    >>> scraper.prep_stats(level="game", teammates=True)

    You can also chain the prep method with the stats property you're calling
    >>> stats = scraper.prep_stats(level="season").stats
"""

_STATS_DOC = f"""\
DataFrame combining individual and on-ice stats, with the below fields.

Contains all columns from ``ind_stats`` and ``oi_stats`` plus per-60 and percentage columns.
Call ``prep_stats()`` to change the aggregation level or filters before accessing this property.

Note:
    You can determine the DataFrame backend with the ``backend`` argument at Scraper instantiation,
    e.g., ``Scraper(game_id, backend="pandas").stats``

{_build_returns(_STATS_PLAYER_CONTEXT_FIELDS | _TOI_FIELD | _IND_STATS_FIELDS | _OI_STATS_COUNTING_FIELDS | _OI_ZONE_STARTS_FIELDS | _IND_P60_FIELDS | _OI_P60_FIELDS | _OI_PERCENT_FIELDS)}

Examples:
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(list(range(2023020001, 2023020011)))

    Access combined stats at default game level
    >>> scraper.stats

    Prepare season-level stats first, then access
    >>> scraper.prep_stats(level="season")
    >>> scraper.stats

    You can also chain the prep method with the stats property you're calling
    >>> stats = scraper.prep_stats(level="season").stats
"""

_PREP_LINES_DOC = f"""\
Prepare (or re-prepare) the line-level stats DataFrame.

Aggregates on-ice stats by forward or defense line groupings. Call this to change
aggregation options; subsequent accesses to ``lines`` will reflect the new settings.

{_build_params(_LINES_POSITION_PARAM | _STATS_COMMON_PARAMS | _PREP_PROGRESS_PARAMS)}

Returns:
    Self: The Scraper instance (for method chaining).

Examples:
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(list(range(2023020001, 2023020011)))

    Default forward lines at game level
    >>> scraper.prep_lines()
    >>> scraper.lines

    Defense pairs, season level
    >>> scraper.prep_lines(position="d", level="season")
    >>> scraper.lines

    You can also chain the prep method with the stats property you're calling
    >>> lines = scraper.prep_lines(position="d", level="season").lines
"""

_LINES_DOC = f"""\
DataFrame of line-level on-ice stats, with the below fields.

Call ``prep_lines()`` to change the position, aggregation level, or filters
before accessing this property.

Note:
    You can determine the DataFrame backend with the ``backend`` argument at Scraper instantiation,
    e.g., ``Scraper(game_id, backend="pandas").lines``

{_build_returns(_LINES_CONTEXT_FIELDS | _TOI_FIELD | _OI_STATS_COUNTING_FIELDS | _OI_P60_FIELDS | _OI_PERCENT_FIELDS)}

Examples:
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(list(range(2023020001, 2023020011)))

    Access forward lines at default game level
    >>> scraper.lines

    Defense pairs, season level
    >>> scraper.prep_lines(position="d", level="season")
    >>> scraper.lines

    You can also chain the prep method with the stats property you're calling
    >>> lines = scraper.prep_lines(position="d", level="season").lines
"""

_PREP_TEAM_STATS_DOC = f"""\
Prepare (or re-prepare) the team-level stats DataFrame.

Aggregates on-ice stats by team. Call this to change aggregation options; subsequent
accesses to ``team_stats`` will reflect the new settings.

{_build_params({k: v for k, v in (_STATS_COMMON_PARAMS | _PREP_PROGRESS_PARAMS).items() if k != "teammates"})}

Returns:
    Self: The Scraper instance (for method chaining).

Examples:
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(list(range(2023020001, 2023020011)))

    Default game-level team stats
    >>> scraper.prep_team_stats()
    >>> scraper.team_stats

    Season-level, split by score state
    >>> scraper.prep_team_stats(level="season", score=True)
    >>> scraper.team_stats

    You can also chain the prep method with the stats property you're calling
    >>> team_stats = scraper.prep_team_stats(level="season").team_stats
"""

_TEAM_STATS_DOC = f"""\
DataFrame of team-level on-ice stats, with the below fields.

Call ``prep_team_stats()`` to change the aggregation level or filters
before accessing this property.

Note:
    You can determine the DataFrame backend with the ``backend`` argument at Scraper instantiation,
    e.g., ``Scraper(game_id, backend="pandas").team_stats``

{_build_returns(_TEAM_STATS_CONTEXT_FIELDS | _TOI_FIELD | _OI_STATS_COUNTING_FIELDS | _OI_P60_FIELDS | _OI_PERCENT_FIELDS)}

Examples:
    >>> from chickenstats.chicken_nhl import Scraper
    >>> scraper = Scraper(list(range(2023020001, 2023020011)))

    Access team stats at default game level
    >>> scraper.team_stats

    Season-level stats
    >>> scraper.prep_team_stats(level="season")
    >>> scraper.team_stats

    You can also chain the prep method with the stats property you're calling
    >>> team_stats = scraper.prep_team_stats(level="season").team_stats
"""
