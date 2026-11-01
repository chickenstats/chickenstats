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

# Play-by-play stat -> on-ice stat from the event team's side. Summed by prep_oi, prep_lines
# and prep_team_stats, each of which handles event_length itself.
ON_ICE_FOR: dict[str, str] = {
    "pred_goal": "xgf",
    "pred_goal_adj": "xgf_adj",
    "base_xg": "base_xgf",
    "base_xg_adj": "base_xgf_adj",
    "context_xg_adj": "context_xgf_adj",
    "context_xg": "context_xgf",
    "fenwick": "ff",
    "fenwick_adj": "ff_adj",
    "unblocked_corsi_adj": "ff_corsi_adj",
    "goal": "gf",
    "goal_adj": "gf_adj",
    "miss": "msf",
    "miss_adj": "msf_adj",
    # A side's own BLOCK events are shots it blocked, so bsa; bsf comes from the
    # "against" frame, where the opponent blocked one of this side's attempts.
    "block": "bsa",
    "block_adj": "bsa_adj",
    "teammate_block": "teammate_block",
    "teammate_block_adj": "teammate_block_adj",
    "shot": "sf",
    "shot_adj": "sf_adj",
    "hd_goal": "hdgf",
    "hd_shot": "hdsf",
    "hd_fenwick": "hdff",
    "hd_miss": "hdmsf",
    "fac": "fow",
    "ozf": "ozfw",
    "nzf": "nzfw",
    "dzf": "dzfw",
    "hit": "hf",
    "give": "give",
    "take": "take",
    "pen0": "pent0",
    "pen2": "pent2",
    "pen4": "pent4",
    "pen5": "pent5",
    "pen10": "pent10",
}

# The same stats from the opposing side, "a" suffix instead of "f" (xga vs xgf, etc.). The
# zones flip because a faceoff's zone is the winner's.
ON_ICE_AGAINST: dict[str, str] = {
    "pred_goal": "xga",
    "pred_goal_adj": "xga_adj",
    "base_xg": "base_xga",
    "base_xg_adj": "base_xga_adj",
    "context_xg_adj": "context_xga_adj",
    "context_xg": "context_xga",
    "fenwick": "fa",
    "fenwick_adj": "fa_adj",
    "unblocked_corsi_adj": "fa_corsi_adj",
    "goal": "ga",
    "goal_adj": "ga_adj",
    "miss": "msa",
    "miss_adj": "msa_adj",
    "block": "bsf",
    "block_adj": "bsf_adj",
    # The opponent's own-teammate blocks are Corsi against this side.
    "teammate_block": "opp_teammate_block",
    "teammate_block_adj": "opp_teammate_block_adj",
    "shot": "sa",
    "shot_adj": "sa_adj",
    "hd_goal": "hdga",
    "hd_shot": "hdsa",
    "hd_fenwick": "hdfa",
    "hd_miss": "hdmsa",
    "fac": "fol",
    "ozf": "dzfl",
    "nzf": "nzfl",
    "dzf": "ozfl",
    "hit": "ht",
    "pen0": "pend0",
    "pen2": "pend2",
    "pen4": "pend4",
    "pen5": "pend5",
    "pen10": "pend10",
}

# Line-change columns prep_oi renames, for the zone-start slots.
ZONE_START_COLS: dict[str, str] = {"ozc": "ozs", "nzc": "nzs", "dzc": "dzs", "otf": "otf"}

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
    "player_1",
    "player_1_eh_id",
    "player_1_api_id",
    "player_1_position",
    "player_2",
    "player_2_eh_id",
    "player_2_api_id",
    "player_2_position",
    "player_3",
    "player_3_eh_id",
    "player_3_api_id",
    "player_3_position",
]

# prep_oi, prep_lines and prep_team_stats also join the on-ice slots and count ice time
ON_ICE_REQUIRED_COLS: list[str] = [*PBP_REQUIRED_COLS, "id", "event_idx", "event_length"]

# The lineup lists build_play_by_play_ext reads, required when no df_ext is passed
EXT_SOURCE_COLS: list[str] = [
    "teammates",
    "teammates_eh_id",
    "teammates_api_id",
    "teammates_positions",
    "opp_team_on",
    "opp_team_on_eh_id",
    "opp_team_on_api_id",
    "opp_team_on_positions",
    "change_on",
    "change_on_eh_id",
    "change_on_api_id",
    "change_on_positions",
]

# Optional xG source column -> stat suffix. Used by prep_stints for whichever are present.
STINT_XG_COLS: dict[str, str] = {"pred_goal": "xgf", "base_xg": "base_xgf", "context_xg": "context_xgf"}

# On-ice lineup columns prep_stints normalizes to List[String] before aggregating.
STINT_LINEUP_COLS: list[str] = ["home_on_api_id", "away_on_api_id", "home_goalie_api_id", "away_goalie_api_id"]

# Large play-by-play text columns no prep_* reads, dropped so joins and sorts don't copy them.
UNREAD_PBP_COLS: list[str] = [
    f"{name}{suffix}"
    for name in ("teammates", "opp_team_on", "home_forwards", "home_defense", "away_forwards", "away_defense")
    for suffix in ("", "_eh_id", "_api_id", "_positions")
]

# How the report words a shot blocked by anyone but an opponent.
TEAMMATE_BLOCK_PATTERN = "BLOCKED BY (?:TEAMMATE|OTHER)|TEAMMATE-BLOCKED BY"

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

# Everything prep_stints reads: the required columns, then the ones it uses when present.
STINT_READ_COLS: list[str] = [
    *STINT_REQUIRED_COLS,
    *STINT_XG_COLS,
    "event",
    "base_xg_adj",
    "context_xg_adj",
    "pred_goal_adj",
    "strength_state",
    "shootout_attempt",
]

# Output column order for prep_stints; anything else, such as the lineup source columns,
# is dropped by the final select.
STINT_COLUMN_ORDER: list[str] = [
    "season",
    "session",
    "game_id",
    "game_date",
    "period",
    "stint_id",
    "toi_seconds",
    "strength_state",
    "home_team",
    "away_team",
    "home_skater_ids",
    "away_skater_ids",
    "home_goalie_ids",
    "away_goalie_ids",
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
    "nzs",
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


AGG_LEVELS: list[str] = ["period", "game", "session", "season"]


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

    # Every prep_* function groups through here
    if level not in AGG_LEVELS:
        raise InvalidInputError(f"level must be one of {AGG_LEVELS}, got {level!r}", obj=level)

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


def build_against_group_list(
    base: list[str],
    *,
    level: str = "season",
    strength_state: bool = False,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    ensure_team: bool = False,
    teammates_cols: list[str] | None = None,
) -> list[str]:
    """Build the group-by list for a "stats against" aggregation, seen from the opposing side.

    ``base`` keys on 'opp_team'. The flags mean what they mean in ``build_group_list``, with
    the opposing columns standing in for the event team's: its strength and score state, and
    its lineup as ``teammates``.

    Parameters:
        base: Starting column list (player columns, team columns, etc.).
        level: Aggregation level, as in ``build_group_list``.
        strength_state: Append 'opp_strength_state'.
        score: Append 'opp_score_state'.
        teammates: Append teammate columns (defaults to module OPPOSITION_COLS).
        opposition: Append the module TEAMMATES_COLS.
        ensure_team: Guarantee 'event_team' is present regardless of level.
        teammates_cols: Override the default OPPOSITION_COLS list.

    Returns:
        Deduplicated list in canonical order; unknown columns follow in insertion order.
    """
    return build_group_list(
        base,
        level=level,
        opp_strength_state=strength_state,
        opp_score=score,
        teammates=teammates,
        opposition=opposition,
        ensure_team=ensure_team,
        teammates_cols=OPPOSITION_COLS if teammates_cols is None else teammates_cols,
        opposition_cols=TEAMMATES_COLS,
        opp_perspective=True,
    )
