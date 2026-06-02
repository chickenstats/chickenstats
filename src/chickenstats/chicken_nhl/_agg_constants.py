# Columns representing a player's own on-ice skating lineup (forwards, defense, goalie
# with eh_id and api_id variants). Appended to the groupby/merge list when
# teammates=True is passed to prep_ind, prep_oi, prep_lines, or prep_team_stats.
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

# Columns representing the opposing on-ice lineup (opp_forwards, opp_defense, opp_goalie
# with eh_id and api_id variants). Appended when opposition=True. Also forces
# opp_team into the groupby list (via ensure_opp_team in build_group_list).
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

# Stats to normalise per 60 minutes of ice time (stat / toi * 60).
# Consumed by prep_p60(), which appends a _p60 suffixed column for each name
# present in the DataFrame. Covers individual counting stats (g, a1, ixg, …)
# and on-ice counting stats (gf, ga, sf, sa, xgf, xga, …).
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

# Numerator stats for on-ice percentage calculations (e.g., gf, xgf, sf, cf).
# Each entry in OI_PERCENT_STATS_FOR is paired positionally with the corresponding
# entry in OI_PERCENT_STATS_AGAINST to produce stat_percent = for / (for + against).
# Consumed by prep_oi_percent().
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

# Denominator (against) stats paired positionally with OI_PERCENT_STATS_FOR.
# Must stay in sync with OI_PERCENT_STATS_FOR — same length, same index order.
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


# Authoritative column ordering used by build_group_list() to sort the deduped
# groupby list. Columns not in this list sort after it in insertion order.
# Kept private (_) because callers should go through build_group_list().
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
    ensure_opp_team: bool = True,
    teammates_cols: list[str] | None = None,
    opposition_cols: list[str] | None = None,
) -> list[str]:
    """Build a deduplicated, canonically-ordered group-by / merge list.

    Parameters:
        base: Starting column list (player columns, team columns, etc.).
        level: Aggregation level — adds game_id/game_date/opp_team for 'game',
            and additionally period for 'period'. No extra columns for 'season'/'session'.
        strength_state: Append 'strength_state'.
        opp_strength_state: Append 'opp_strength_state' instead of 'strength_state'.
        score: Append 'score_state'.
        opp_score: Append 'opp_score_state' instead of 'score_state'.
        teammates: Append teammate columns (defaults to module TEAMMATES_COLS).
        opposition: Append opposition columns (defaults to module OPPOSITION_COLS).
        ensure_opp_team: When opposition=True, guarantee 'opp_team' is present.
        teammates_cols: Override the default TEAMMATES_COLS list.
        opposition_cols: Override the default OPPOSITION_COLS list.

    Returns:
        Deduplicated list in canonical order; unknown columns follow in insertion order.
    """
    _teammates = teammates_cols if teammates_cols is not None else TEAMMATES_COLS
    _opposition = opposition_cols if opposition_cols is not None else OPPOSITION_COLS

    cols = list(base)
    if level == "game":
        cols += ["game_id", "game_date", "opp_team"]
    elif level == "period":
        cols += ["game_id", "game_date", "opp_team", "period"]
    if opp_strength_state:
        cols.append("opp_strength_state")
    elif strength_state:
        cols.append("strength_state")
    if opp_score:
        cols.append("opp_score_state")
    elif score:
        cols.append("score_state")
    if teammates:
        cols += _teammates
    if opposition:
        cols += _opposition
        if ensure_opp_team and "opp_team" not in cols:
            cols.append("opp_team")

    known = {col: i for i, col in enumerate(_CANONICAL_ORDER)}
    seen: set[str] = set()
    deduped: list[str] = []
    for col in cols:
        if col not in seen:
            seen.add(col)
            deduped.append(col)
    insertion_order = {col: i for i, col in enumerate(deduped)}
    deduped.sort(key=lambda c: (known.get(c, len(known)), insertion_order[c]))
    return deduped
