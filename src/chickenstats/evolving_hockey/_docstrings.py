"""Column descriptions for the frames only the evolving_hockey module returns.

Each registry maps ``field_name -> (type_str, description)``, as in ``chicken_nhl._docstrings``.
The stats frames share their columns with chicken_nhl and use its registries.
"""

from __future__ import annotations

from chickenstats.chicken_nhl._docstrings import _PBP_FIELDS as _NHL_PBP_FIELDS

_FULL = 'Only with columns="full" or "all"'
_ALL = 'Only with columns="all"'


def _on_ice_slots(prefix: str, team: str) -> dict[str, tuple[str, str]]:
    """Field entries for the seven numbered on-ice slots of one team."""
    out: dict[str, tuple[str, str]] = {}
    for i in range(1, 8):
        out[f"{prefix}_{i}"] = (
            "str | None",
            f"Player in on-ice slot {i} of the {team}, null when the slot is empty or the event has no team. "
            f"{_FULL}, e.g., NIKITA KUCHEROV",
        )
        out[f"{prefix}_{i}_eh_id"] = ("str | None", f"Evolving Hockey ID for {prefix}_{i}, e.g., NIKITA.KUCHEROV")
        out[f"{prefix}_{i}_pos"] = ("str | None", f"Position of {prefix}_{i}, e.g., R")
    return out


def _player_lists(prefix: str, who: str, example: str, example_id: str) -> dict[str, tuple[str, str]]:
    """Field entries for a comma-separated list of players and their Evolving Hockey IDs."""
    return {
        prefix: ("str | None", f"Names of {who}, sorted by name, null when there are none, e.g., {example}"),
        f"{prefix}_eh_id": ("str | None", f"Evolving Hockey IDs of {who}, in the same order, e.g., {example_id}"),
    }


# The dummy columns mean the same as in chicken_nhl play-by-play
_SHARED_DUMMIES = ["hit", "give", "take", "fac", "change", "stop", "ozf", "nzf", "dzf", "otf"]
_SHARED_DUMMIES += ["pen0", "pen2", "pen4", "pen5", "pen10"]

_PBP_FIELDS: dict[str, tuple[str, str]] = {
    "id": ("int", "Play ID, the game ID followed by event_index padded to four digits, e.g., 20230200010149"),
    "season": ("int", "Season as 8-digit number, e.g., 20232024"),
    "session": ("str", "Whether game is regular season or playoffs, e.g., R"),
    "game_id": ("int", "Unique game ID assigned by the NHL, e.g., 2023020001"),
    "game_date": ("str", "Date game was played, e.g., 2023-10-10"),
    "event_index": ("int", "Index of the event in the game, as the export gives it, e.g., 149"),
    "period": ("int", "Period number of the event, 0 when the export gives none, e.g., 1"),
    "period_seconds": ("int", "Time elapsed in the period, in seconds, 0 in a regular-season shootout, e.g., 588"),
    "game_seconds": ("int", "Time elapsed in the game, in seconds, 0 when the export gives none, e.g., 588"),
    "clock_time": ("str", "Time left in the period, as the export gives it, e.g., 10:12"),
    "strength_state": (
        "str | None",
        "Skaters on the ice for the event team, then the other team, with E for an empty net, "
        "null when the event has no team, e.g., 5v5",
    ),
    "event_team": ("str | None", "Team that performed the event, null when the event has no team, e.g., TBL"),
    "opp_team": ("str | None", "Team that did not perform the event, null when the event has no team, e.g., NSH"),
    "event_type": ("str", "Type of event, as the export gives it, e.g., GOAL"),
    "event_description": (
        "str | None",
        "Description of the event, as the export gives it, e.g., TBL #86 KUCHEROV(1), SLAP , OFF. ZONE, 42 FT.",
    ),
    "event_detail": (
        "str | None",
        "Shot type of a shot attempt or length of a penalty, as the export gives it, e.g., Slap",
    ),
    "event_zone": (
        "str | None",
        "Zone where the event occurred, relative to the event team, null when the export gives none, e.g., OFF",
    ),
    "coords_x": ("float | None", "x-coordinate where the event occurred, null when the export gives none, e.g., 50.0"),
    "coords_y": ("float | None", "y-coordinate where the event occurred, null when the export gives none, e.g., -16.0"),
    "high_danger": (
        "int",
        "Whether the event is an unblocked shot attempt from the high-danger area of the offensive zone, e.g., 0",
    ),
    "danger": (
        "int",
        "Whether the event is an unblocked shot attempt from the danger area of the offensive zone, "
        "outside the high-danger area, e.g., 1",
    ),
    "event_player_1": (
        "str | None",
        "First player in the event, such as the shooter, the faceoff winner, the hitter or the penalized player, "
        "e.g., NIKITA KUCHEROV",
    ),
    "event_player_1_eh_id": ("str | None", "Evolving Hockey ID for event_player_1, e.g., NIKITA.KUCHEROV"),
    "event_player_1_pos": ("str | None", "Position of event_player_1, from the shifts export, e.g., R"),
    "event_player_2": (
        "str | None",
        "Second player in the event, such as the primary assist, the faceoff loser, the player hit, "
        "the blocker or the player who drew the penalty, e.g., VICTOR HEDMAN",
    ),
    "event_player_2_eh_id": ("str | None", "Evolving Hockey ID for event_player_2, e.g., VICTOR.HEDMAN"),
    "event_player_2_pos": ("str | None", "Position of event_player_2, from the shifts export, e.g., D"),
    "event_player_3": ("str | None", "Third player in the event, the secondary assist, e.g., BRAYDEN POINT"),
    "event_player_3_eh_id": ("str | None", "Evolving Hockey ID for event_player_3, e.g., BRAYDEN.POINT"),
    "event_player_3_pos": ("str | None", "Position of event_player_3, from the shifts export, e.g., C"),
    "score_state": (
        "str | None",
        "Score from the event team's perspective, or the home team's when the event has no team, e.g., 0v0",
    ),
    "event_length": ("int", "Time between this event and the next, in seconds, as the export gives it, e.g., 0"),
    "event_distance": ("float | None", "Distance of the event from the goal, as the export gives it, e.g., 42.154478"),
    "pbp_distance": (
        "float | None",
        "Distance of the event from the goal, from the description, as the export gives it, e.g., 42.0",
    ),
    "event_angle": ("float | None", "Angle of the event towards the goal, as the export gives it, e.g., 22.306205"),
    "home_score": ("int | None", f"Home team's score. {_ALL}, e.g., 0"),
    "away_score": ("int | None", f"Away team's score. {_ALL}, e.g., 0"),
    "is_home": ("int", "Whether the event team is the home team, 0 when the event has no team, e.g., 1"),
    "home_team": ("str | None", f"Home team. {_ALL}, e.g., TBL"),
    "away_team": ("str | None", f"Away team. {_ALL}, e.g., NSH"),
    "home_skaters": ("int | None", f"Home team skaters on the ice, as the export gives it. {_ALL}, e.g., 5"),
    "away_skaters": ("int | None", f"Away team skaters on the ice, as the export gives it. {_ALL}, e.g., 5"),
    "home_zone": (
        "str | None",
        f"Zone where the event occurred, relative to the home team, as the export writes it. {_ALL}, e.g., Off",
    ),
    "home_goalie": (
        "str | None",
        f"Home team's goalie, as the export writes the name, null when the export gives none. {_ALL}, e.g., JONAS.JOHANSSON",
    ),
    "away_goalie": (
        "str | None",
        f"Away team's goalie, as the export writes the name, null when the export gives none. {_ALL}, e.g., JUUSE.SAROS",
    ),
    "home_zonestart": (
        "float | None",
        f"The export's home_zonestart column, passed through unchanged. {_ALL}, e.g., None",
    ),
    "face_index": ("int | None", f"The export's face_index column, passed through unchanged. {_ALL}, e.g., 4"),
    "pen_index": ("int | None", f"The export's pen_index column, passed through unchanged. {_ALL}, e.g., 0"),
    "shift_index": ("int | None", f"The export's shift_index column, passed through unchanged. {_ALL}, e.g., 104"),
    "game_score_state": ("str | None", f"Score from the home team's perspective. {_ALL}, e.g., 0v0"),
    "game_strength_state": (
        "str | None",
        f"Strength state from the home team's perspective, as the export gives it. {_ALL}, e.g., 5v5",
    ),
    **_player_lists(
        "forwards",
        "the event team's forwards on the ice",
        "BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS",
        "BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS",
    ),
    **_player_lists(
        "defense", "the event team's defense on the ice", "NICK PERBIX, VICTOR HEDMAN", "NICK.PERBIX, VICTOR.HEDMAN"
    ),
    "own_goalie": (
        "str | None",
        "Event team's goalie on the ice, null for an empty net or an event with no team, e.g., JONAS JOHANSSON",
    ),
    "own_goalie_eh_id": ("str | None", "Evolving Hockey ID of the event team's goalie, e.g., JONAS.JOHANSSON"),
    **_on_ice_slots("event_on", "event team"),
    "opp_strength_state": (
        "str | None",
        f"Strength state from the other team's perspective, null when the event has no team. {_FULL}, e.g., 5v5",
    ),
    "opp_score_state": (
        "str | None",
        f"Score from the other team's perspective, or the away team's when the event has no team. {_FULL}, e.g., 0v0",
    ),
    **_player_lists(
        "opp_forwards",
        "the other team's forwards on the ice",
        "FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY",
        "FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY",
    ),
    **_player_lists(
        "opp_defense", "the other team's defense on the ice", "LUKE SCHENN, ROMAN JOSI", "LUKE.SCHENN, ROMAN.JOSI"
    ),
    "opp_goalie": (
        "str | None",
        "Other team's goalie on the ice, null for an empty net or an event with no team, e.g., JUUSE SAROS",
    ),
    "opp_goalie_eh_id": ("str | None", "Evolving Hockey ID of the other team's goalie, e.g., JUUSE.SAROS"),
    **_on_ice_slots("opp_on", "other team"),
    "num_on": ("float | None", "Number of players coming on in a change, null for other events, e.g., 1.0"),
    "num_off": ("float | None", "Number of players going off in a change, null for other events, e.g., 1.0"),
    "players_on": (
        "str | None",
        "Names of the players coming on in a change, null for other events, e.g., YAKOV TRENIN",
    ),
    "players_on_eh_id": ("str | None", "Evolving Hockey IDs of the players coming on, e.g., YAKOV.TRENIN"),
    "players_on_pos": ("str | None", "Positions of the players coming on, e.g., C"),
    "players_off": (
        "str | None",
        "Names of the players going off in a change, null for other events, e.g., FILIP FORSBERG",
    ),
    "players_off_eh_id": ("str | None", "Evolving Hockey IDs of the players going off, e.g., FILIP.FORSBERG"),
    "players_off_pos": ("str | None", "Positions of the players going off, e.g., L"),
    "zone_start": (
        "str | None",
        "For a change, the zone of a faceoff in the same second, relative to the changing team (OFF, DEF or NEU), "
        "or OTF when there is none; null for other events, e.g., OTF",
    ),
    "goal": ("int", "Dummy indicator whether event is a goal, 0 for a shootout goal, e.g., 1"),
    "hd_goal": ("int", "Dummy indicator whether event is a high-danger goal, e.g., 0"),
    "goal_adj": ("float", "Score- and venue-adjusted value for a goal, e.g., 0.97653"),
    "pred_goal": (
        "float | None",
        "The export's xG for an unblocked shot attempt, null for other events and shootout attempts, e.g., 0.023173",
    ),
    "pred_goal_adj": ("float | None", "Score- and venue-adjusted pred_goal, e.g., 0.022491"),
    "shot": ("int", "Dummy indicator whether event is a shot on goal, goals included, 0 in a shootout, e.g., 1"),
    "hd_shot": ("int", "Dummy indicator whether event is a high-danger shot on goal, e.g., 0"),
    "shot_adj": ("float", "Score- and venue-adjusted value for a shot on goal, e.g., 0.977604"),
    "miss": ("int", "Dummy indicator whether event is a missed shot, 0 in a shootout, e.g., 0"),
    "miss_adj": ("float", "Score- and venue-adjusted value for a missed shot, e.g., 0.0"),
    "hd_miss": ("int", "Dummy indicator whether event is a high-danger missed shot, e.g., 0"),
    "fenwick": ("int", "Dummy indicator whether event is a fenwick event, shot plus miss, e.g., 1"),
    "hd_fenwick": ("int", "Dummy indicator whether event is a high-danger fenwick event, e.g., 0"),
    "fenwick_adj": ("float", "Score- and venue-adjusted value for a fenwick event, e.g., 0.974523"),
    "corsi": ("int", "Dummy indicator whether event is a corsi event, fenwick plus block, e.g., 1"),
    "corsi_adj": ("float", "Score- and venue-adjusted value for a corsi event, e.g., 0.976102"),
    "block": ("int", "Dummy indicator whether event is a blocked shot, teammate blocks included, e.g., 0"),
    "block_adj": ("float", "Score- and venue-adjusted value for a blocked shot, e.g., 0.0"),
    "teammate_block": ("int", "Dummy indicator whether event is a shot blocked by a teammate, e.g., 0"),
    "teammate_block_adj": ("float", "Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0"),
    "shootout_attempt": (
        "int",
        "Dummy indicator whether event is an unblocked shot attempt in a regular-season shootout, e.g., 0",
    ),
    "shootout_goal": ("int", "Dummy indicator whether event is a goal in a regular-season shootout, e.g., 0"),
    "ozs": ("int", "Dummy indicator whether event is a change with an offensive zone start, e.g., 0"),
    "nzs": ("int", "Dummy indicator whether event is a change with a neutral zone start, e.g., 0"),
    "dzs": ("int", "Dummy indicator whether event is a change with a defensive zone start, e.g., 0"),
    **{name: _NHL_PBP_FIELDS[name] for name in _SHARED_DUMMIES},
}

# -----------------------------------------------------------------------------
# GAR and xGAR, passed through from the exports with names, season and team normalized
# -----------------------------------------------------------------------------

_RATING_ID_FIELDS: dict[str, tuple[str, str]] = {
    "player": ("str", "Player name, written as chicken_nhl writes it, e.g., ROMAN JOSI"),
    "eh_id": ("str", "Evolving Hockey ID of the player, e.g., ROMAN.JOSI"),
    "api_id": ("int | None", "NHL API ID of the player, null when the export gives none, e.g., 8474600"),
    "season": ("int", "Season as 8-digit number, from the export's YY-YY season, e.g., 20232024"),
    "team": ("str", "Team the player played for, e.g., NSH"),
    "position": ("str", "Position of the player, as the export gives it, e.g., D"),
    "shoots": ("str | None", "Hand the skater shoots with, null for a goalie, e.g., L"),
    "catches": ("str | None", "Hand the goalie catches with, null for a skater, e.g., None"),
    "birthday": (
        "date | None",
        "Birthday of the player, null when the export gives none or not as a date, e.g., 2000-01-01",
    ),
    "age": ("int | None", "Age of the player, as the export gives it, e.g., 25"),
    "draft_yr": ("int | None", "Year the player was drafted, null when the export gives none, e.g., None"),
    "draft_rd": ("str | None", "Round the player was drafted in, as the export gives it, e.g., None"),
    "draft_ov": ("str | None", "Overall pick the player was drafted with, as the export gives it, e.g., None"),
    "gp": ("int | None", "Games played, e.g., 2"),
    "toi_all": ("float | None", "Time on ice in all situations, in minutes, null for a goalie, e.g., 48.9"),
}

_GAR_FIELDS: dict[str, tuple[str, str]] = {
    **_RATING_ID_FIELDS,
    "toi_ev": ("float | None", "Time on ice at even strength, in minutes, e.g., 48.9"),
    "toi_pp": ("float | None", "Time on ice on the power play, in minutes, null for a goalie, e.g., 0.0"),
    "toi_sh": ("float | None", "Time on ice shorthanded, in minutes, e.g., 0.0"),
    "fa_ev": ("int | None", "The goalie export's FA_EV column, null for a skater, e.g., None"),
    "fa_sh": ("int | None", "The goalie export's FA_SH column, null for a skater, e.g., None"),
    "evo_gar": ("float | None", "Even-strength offense goals above replacement, null for a goalie, e.g., 0.5"),
    "evd_gar": ("float | None", "Even-strength defense goals above replacement, e.g., 0.5"),
    "ppo_gar": ("float | None", "Power-play offense goals above replacement, null for a goalie, e.g., 0.5"),
    "shd_gar": ("float | None", "Shorthanded defense goals above replacement, e.g., 0.5"),
    "take_gar": ("float | None", "Goals above replacement from penalties taken, e.g., 0.5"),
    "draw_gar": ("float | None", "Goals above replacement from penalties drawn, e.g., 0.5"),
    "off_gar": ("float | None", "Offense goals above replacement, null for a goalie, e.g., 0.5"),
    "def_gar": ("float | None", "Defense goals above replacement, null for a goalie, e.g., 0.5"),
    "pens_gar": ("float | None", "Penalty goals above replacement, null for a goalie, e.g., 0.5"),
    "gar": ("float | None", "Total goals above replacement, e.g., 0.5"),
    "war": ("float | None", "Wins above replacement, e.g., 0.5"),
    "spar": ("float | None", "Standings points above replacement, e.g., 0.5"),
}

_XGAR_FIELDS: dict[str, tuple[str, str]] = {
    **_RATING_ID_FIELDS,
    "xevo_gar": ("float | None", "Expected even-strength offense goals above replacement, e.g., 0.5"),
    "xevd_gar": ("float | None", "Expected even-strength defense goals above replacement, e.g., 0.5"),
    "xppo_gar": ("float | None", "Expected power-play offense goals above replacement, e.g., 0.5"),
    "xshd_gar": ("float | None", "Expected shorthanded defense goals above replacement, e.g., 0.5"),
    "take_gar": _GAR_FIELDS["take_gar"],
    "draw_gar": _GAR_FIELDS["draw_gar"],
    "xoff_gar": ("float | None", "Expected offense goals above replacement, e.g., 0.5"),
    "xdef_gar": ("float | None", "Expected defense goals above replacement, e.g., 0.5"),
    "pens_gar": ("float | None", "Penalty goals above replacement, e.g., 0.5"),
    "xgar": ("float | None", "Total expected goals above replacement, e.g., 0.5"),
    "xwar": ("float | None", "Expected wins above replacement, e.g., 0.5"),
    "xspar": ("float | None", "Expected standings points above replacement, e.g., 0.5"),
}
