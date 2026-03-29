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

P60_STATS = [
    "g",
    "g_adj",
    "ihdg",
    "a1",
    "a2",
    "ixg",
    "ixg_adj",
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

OI_PERCENT_STATS_FOR = [
    "gf",
    "gf_adj",
    "hdgf",
    "xgf",
    "xgf_adj",
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

OI_PERCENT_STATS_AGAINST = [
    "ga",
    "ga_adj",
    "hdga",
    "xga",
    "xga_adj",
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


class GroupListBuilder:
    """Builds canonical group-by / merge lists for aggregation functions.

    Usage:
        group_list = (
            GroupListBuilder(["season", "session", "event_team", player, ...])
            .with_level(level)
            .with_strength_state(strength_state)
            .with_score(score)
            .with_teammates(teammates)
            .with_opposition(opposition)
            .build()
        )

    Call .build() from a notebook to reproduce exactly what any function will group by.
    """

    _CANONICAL_ORDER = [
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

    def __init__(self, base: list[str]):
        self._cols: list[str] = list(base)

    def with_level(self, level: str) -> "GroupListBuilder":
        if level == "game":
            self._cols.extend(["game_id", "game_date", "opp_team"])
        elif level == "period":
            self._cols.extend(["game_id", "game_date", "opp_team", "period"])
        return self

    def with_strength_state(self, enabled: bool = True, opp: bool = False) -> "GroupListBuilder":
        if enabled:
            self._cols.append("opp_strength_state" if opp else "strength_state")
        return self

    def with_score(self, enabled: bool = False, opp: bool = False) -> "GroupListBuilder":
        if enabled:
            self._cols.append("opp_score_state" if opp else "score_state")
        return self

    def with_teammates(self, enabled: bool = False, opp: bool = False) -> "GroupListBuilder":
        if enabled:
            self._cols.extend(OPPOSITION_COLS if opp else TEAMMATES_COLS)
        return self

    def with_opposition(
        self, enabled: bool = False, opp: bool = False, ensure_opp_team: bool = True
    ) -> "GroupListBuilder":
        if enabled:
            self._cols.extend(TEAMMATES_COLS if opp else OPPOSITION_COLS)
            if ensure_opp_team and "opp_team" not in self._cols:
                self._cols.append("opp_team")
        return self

    def build(self) -> list[str]:
        """Return deduplicated list in canonical order; unknown columns retain insertion order after known ones."""
        known = {col: i for i, col in enumerate(self._CANONICAL_ORDER)}
        seen: set[str] = set()
        deduped: list[str] = []
        for col in self._cols:
            if col not in seen:
                seen.add(col)
                deduped.append(col)
        insertion_order = {col: i for i, col in enumerate(deduped)}
        deduped.sort(key=lambda c: (known.get(c, len(known)), insertion_order[c]))
        return deduped

    def filter_to(self, df) -> list[str]:
        """build() then keep only columns present in df."""
        available = set(df.columns)
        return [c for c in self.build() if c in available]

    def __repr__(self) -> str:
        return f"GroupListBuilder({self._cols!r})"
