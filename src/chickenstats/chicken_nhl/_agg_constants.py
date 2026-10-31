from chickenstats.exceptions import InvalidInputError

# Own on-ice lineup columns. Appended when teammates=True.
TEAMMATES_COLS = [
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

# Opposing on-ice lineup columns. Appended when opposition=True.
OPPOSITION_COLS = [
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

# Renames for building an opponent-perspective row: swaps team/opp_team, own/opposing
# lineup, and score/strength state. Used in prep_ind, prep_oi, prep_lines, prep_team_stats.
OPPONENT_SWAP_COLS: dict[str, str] = {
    "opp_team": "team",
    "event_team": "opp_team",
    "opp_score_state": "score_state",
    "opp_strength_state": "strength_state",
    "opp_goalie": "own_goalie",
    "opp_goalie_eh_id": "own_goalie_eh_id",
    "opp_goalie_api_id": "own_goalie_api_id",
    "own_goalie": "opp_goalie",
    "own_goalie_eh_id": "opp_goalie_eh_id",
    "own_goalie_api_id": "opp_goalie_api_id",
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

# Stats normalized per 60 minutes of TOI. Consumed by prep_p60().
P60_STATS = [
    "g",
    "g_adj",
    "ihdg",
    "a1",
    "a2",
    "ixg",
    "ixg_adj",
    "base_ixg",
    "base_ixg_adj",
    "context_ixg_adj",
    "context_ixg",
    "isf",
    "isf_adj",
    "ihdsf",
    "imsf",
    "imsf_adj",
    "ihdm",
    "iff",
    "iff_adj",
    "ihdf",
    "isb",
    "isb_adj",
    "icf",
    "icf_adj",
    "ibs",
    "ibs_adj",
    "igive",
    "itake",
    "ihf",
    "iht",
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
    "gf",
    "ga",
    "gf_adj",
    "ga_adj",
    "hdgf",
    "hdga",
    "xgf",
    "xga",
    "xgf_adj",
    "xga_adj",
    "base_xgf",
    "base_xgf_adj",
    "context_xgf_adj",
    "base_xga",
    "base_xga_adj",
    "context_xga_adj",
    "context_xgf",
    "context_xga",
    "sf",
    "sa",
    "sf_adj",
    "sa_adj",
    "hdsf",
    "hdsa",
    "ff",
    "fa",
    "ff_adj",
    "fa_adj",
    "hdff",
    "hdfa",
    "cf",
    "ca",
    "cf_adj",
    "ca_adj",
    "bsf",
    "bsa",
    "bsf_adj",
    "bsa_adj",
    "msf",
    "msa",
    "msf_adj",
    "msa_adj",
    "hdmsf",
    "hdmsa",
    "teammate_block",
    "opp_teammate_block",
    "hf",
    "ht",
    "give",
    "take",
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

# Numerator stats for on-ice percentages. Paired positionally with OI_PERCENT_STATS_AGAINST
# to produce stat_percent = for / (for + against). Consumed by prep_oi_percent().
OI_PERCENT_STATS_FOR = [
    "gf",
    "gf_adj",
    "hdgf",
    "xgf",
    "xgf_adj",
    "base_xgf",
    "base_xgf_adj",
    "context_xgf_adj",
    "context_xgf",
    "sf",
    "sf_adj",
    "hdsf",
    "ff",
    "ff_adj",
    "hdff",
    "cf",
    "cf_adj",
    "bsf",
    "bsf_adj",
    "msf",
    "msf_adj",
    "hdmsf",
    "hf",
    "take",
]

# Denominator stats, paired positionally with OI_PERCENT_STATS_FOR (same length/order).
OI_PERCENT_STATS_AGAINST = [
    "ga",
    "ga_adj",
    "hdga",
    "xga",
    "xga_adj",
    "base_xga",
    "base_xga_adj",
    "context_xga_adj",
    "context_xga",
    "sa",
    "sa_adj",
    "hdsa",
    "fa",
    "fa_adj",
    "hdfa",
    "ca",
    "ca_adj",
    "bsa",
    "bsa_adj",
    "msa",
    "msa_adj",
    "hdmsa",
    "ht",
    "give",
]


# Play-by-play columns prep_ind, prep_oi, prep_lines and prep_team_stats all read. The xG
# columns are left out because they're optional. Checked up front so one error names them all.
PBP_REQUIRED_COLS: list[str] = [
    "season",
    "session",
    "game_id",
    "game_date",
    "strength_state",
    "opp_strength_state",
    "event_team",
    "opp_team",
    "goal",
    "goal_adj",
    "hd_goal",
    "shot",
    "shot_adj",
    "hd_shot",
    "miss",
    "miss_adj",
    "hd_miss",
    "fenwick",
    "fenwick_adj",
    "hd_fenwick",
    "corsi_adj",
    "block",
    "block_adj",
    "teammate_block",
    "teammate_block_adj",
    "hit",
    "give",
    "take",
    "fac",
    "ozf",
    "nzf",
    "dzf",
    "pen0",
    "pen2",
    "pen4",
    "pen5",
    "pen10",
]

# prep_ind also reads each event's players
IND_REQUIRED_COLS: list[str] = [
    *PBP_REQUIRED_COLS,
    "event",
    "description",
    *[f"player_{i}{suffix}" for i in (1, 2, 3) for suffix in ("", "_eh_id", "_api_id", "_position")],
]

# prep_oi, prep_lines and prep_team_stats also join the on-ice slots and count ice time
ON_ICE_REQUIRED_COLS: list[str] = [*PBP_REQUIRED_COLS, "id", "event_idx", "event_length"]

# The lineup lists build_play_by_play_ext reads, required when no df_ext is passed
EXT_SOURCE_COLS: list[str] = [
    f"{lineup}{suffix}"
    for lineup in ("teammates", "opp_team_on", "change_on")
    for suffix in ("", "_eh_id", "_api_id", "_positions")
]

# Optional xG source column -> stat suffix. Used by prep_stints for whichever are present.
STINT_XG_COLS: dict[str, str] = {"pred_goal": "xgf", "base_xg": "base_xgf", "context_xg": "context_xgf"}

# On-ice lineup columns prep_stints normalizes to List[String] before aggregating.
STINT_LINEUP_COLS: list[str] = ["home_on_api_id", "away_on_api_id", "home_goalie_api_id", "away_goalie_api_id"]

# Play-by-play columns prep_stints requires. Checked up front so one error names them all.
STINT_REQUIRED_COLS: list[str] = [
    "season",
    "session",
    "game_id",
    "game_date",
    "event_idx",
    "period",
    "event_team",
    "event_length",
    "strength_state",
    "zone_start",
    "home_team",
    "away_team",
    "home_score_diff",
    "shot",
    "fenwick",
    "block",
    "teammate_block",
    "goal",
    *STINT_LINEUP_COLS,
]

# Output column order for prep_stints; anything else (the lineup source columns, the
# optional xG sums) is dropped by the final select.
STINT_COLUMN_ORDER: list[str] = [
    "season",
    "session",
    "game_id",
    "game_date",
    "period",
    "stint_id",
    "toi",
    "strength_state",
    "home_team",
    "away_team",
    "home_skaters",
    "away_skaters",
    "home_goalies",
    "away_goalies",
    "home_skater_count",
    "away_skater_count",
    "home_sf",
    "away_sf",
    "home_ff",
    "away_ff",
    "home_cf",
    "away_cf",
    "home_gf",
    "away_gf",
    "home_xgf",
    "away_xgf",
    "home_base_xgf",
    "away_base_xgf",
    "home_context_xgf",
    "away_context_xgf",
    "home_delta_xgf",
    "away_delta_xgf",
    "home_score_3",
    "home_score_7",
    "away_score_3",
    "away_score_7",
    "home_b2b",
    "away_b2b",
    "ozs",
    "nzs",
    "dzs",
    "home_ozs",
    "home_dzs",
    "away_ozs",
    "away_dzs",
]

# prep_stints counting stats, cast to Int64 before returning.
STINT_COUNT_COLS: list[str] = ["home_sf", "away_sf", "home_ff", "away_ff", "home_cf", "away_cf", "home_gf", "away_gf"]

# Canonical groupby column order, used by build_group_list(). Unlisted columns sort after.
_CANONICAL_ORDER: list[str] = [
    "season",
    "session",
    "game_id",
    "game_date",
    "event_team",
    "team",
    "opp_team",
    "period",
    "strength_state",
    "opp_strength_state",
    "score_state",
    "opp_score_state",
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


AGG_LEVELS = ("period", "game", "session", "season")


def build_group_list(
    base: list[str],
    *,
    level: str = "season",
    strength_state: bool = False,
    opp_strength_state: bool = False,
    score: bool = False,
    opp_score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    ensure_team: bool = False,
    teammates_cols: list[str] | None = None,
    opposition_cols: list[str] | None = None,
    opp_perspective: bool = False,
) -> list[str]:
    """Build a deduplicated, canonically-ordered group-by / merge list.

    Parameters:
        base: Starting column list (player columns, team columns, etc.).
        level: Aggregation level — adds game_id/game_date/opp_team (or event_team,
            see opp_perspective) for 'game', and additionally period for 'period'.
            No extra columns for 'season'/'session'.
        strength_state: Append 'strength_state'.
        opp_strength_state: Append 'opp_strength_state' instead of 'strength_state'.
        score: Append 'score_state'.
        opp_score: Append 'opp_score_state' instead of 'score_state'.
        teammates: Append teammate columns (defaults to module TEAMMATES_COLS).
        opposition: Append opposition columns (defaults to module OPPOSITION_COLS).
        ensure_team: Guarantee the level team column (opp_team, or event_team when
            opp_perspective=True) is present regardless of level — independent of
            opposition, for callers that want a per-opponent split without lineup
            detail columns (e.g. team-level stats).
        teammates_cols: Override the default TEAMMATES_COLS list.
        opposition_cols: Override the default OPPOSITION_COLS list.
        opp_perspective: Base already keys on 'opp_team' rather than 'event_team'
            (e.g. a "stats against" aggregation) — use 'event_team' wherever this
            function would otherwise add/ensure 'opp_team'.

    Returns:
        Deduplicated list in canonical order; unknown columns follow in insertion order.
    """
    _teammates = teammates_cols if teammates_cols is not None else TEAMMATES_COLS
    _opposition = opposition_cols if opposition_cols is not None else OPPOSITION_COLS
    level_team_col = "event_team" if opp_perspective else "opp_team"

    # Checked here because every prep_* function groups through this; an unknown level was read as season (R18)
    if level not in AGG_LEVELS:
        raise InvalidInputError(f"level must be one of {list(AGG_LEVELS)}, got {level!r}", obj=level)

    # A string such as "no" is truthy, so it split the frame instead of raising
    flags = {"strength_state": strength_state, "score": score, "teammates": teammates, "opposition": opposition}
    for name, value in flags.items():
        if not isinstance(value, bool):
            raise InvalidInputError(f"{name} must be True or False, got {value!r}", obj=value)

    cols = list(base)
    if level == "game":
        cols.extend(["game_id", "game_date", level_team_col])
    elif level == "period":
        cols.extend(["game_id", "game_date", level_team_col, "period"])
    if opp_strength_state:
        cols.append("opp_strength_state")
    elif strength_state:
        cols.append("strength_state")
    if opp_score:
        cols.append("opp_score_state")
    elif score:
        cols.append("score_state")
    if teammates:
        cols.extend(_teammates)
    if opposition:
        cols.extend(_opposition)
    if ensure_team and level_team_col not in cols:
        cols.append(level_team_col)

    deduped = list(dict.fromkeys(cols))
    canonical = [x for x in _CANONICAL_ORDER if x in deduped]
    extras = [x for x in deduped if x not in _CANONICAL_ORDER]
    return canonical + extras
