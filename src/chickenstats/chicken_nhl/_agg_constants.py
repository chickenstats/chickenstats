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
    "base_xga",
    "base_xga_adj",
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
