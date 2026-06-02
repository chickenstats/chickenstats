"""Aggregation functions for EvolvingHockey play-by-play data.

Polars-only internal computation. All public functions accept any narwhals-compatible
input via stats.py, which handles backend detection and output conversion.

All stat-level validation schemas are imported from chickenstats.evolving_hockey.validation.
All shared utilities (_prep_p60, _prep_oi_percent) are imported from chickenstats.chicken_nhl.
"""

from __future__ import annotations

from typing import Literal

from chickenstats.utilities.enums import AggLevel

import polars as pl

from chickenstats.chicken_nhl._aggregation import _prep_p60, _prep_oi_percent
from chickenstats.evolving_hockey._agg_constants import (
    build_group_list,
    IND_STATS,
    OI_PERCENT_STATS_AGAINST,
    OI_PERCENT_STATS_FOR,
    OI_STATS,
    P60_STATS,
    TEAMMATES_COLS,
    OPPOSITION_COLS,
    ZONE_STATS,
)
from chickenstats.chicken_nhl._validation_utils import validate_dataframe
from chickenstats.evolving_hockey.validation import (
    eh_ind_stats_pandera_polars as ind_stats_pandera_polars,
    eh_oi_stats_pandera_polars as oi_stats_pandera_polars,
    eh_stats_pandera_polars as stats_pandera_polars,
    eh_line_stats_pandera_polars as line_stats_pandera_polars,
    eh_team_stats_pandera_polars as team_stats_pandera_polars,
)
from chickenstats.utilities.utilities import ChickenProgress


def _collect(lf: pl.LazyFrame) -> pl.DataFrame:
    """Collect a LazyFrame to an eager DataFrame, narrowing the type for static analysis.

    LazyFrame.collect() is overloaded but ty resolves to the implementation signature
    which returns DataFrame | InProcessQuery. This helper asserts the runtime guarantee
    (no background=True → always DataFrame) in a single place.
    """
    result = lf.collect()
    assert isinstance(result, pl.DataFrame)
    return result


# ---------------------------------------------------------------------------
# Column name maps — EH PBP raw stat names → shared schema stat names
# ---------------------------------------------------------------------------

# player_1 (shooter / skater acting): stat renames for individual stats
_IND_PLAYER1_RENAMES: dict[str, str] = {
    "goal": "g",
    "goal_adj": "g_adj",
    "hd_goal": "ihdg",
    "pred_goal": "ixg",
    "pred_goal_adj": "ixg_adj",
    "shot": "isf",
    "shot_adj": "isf_adj",
    "hd_shot": "ihdsf",
    "miss": "imsf",
    "miss_adj": "imsf_adj",
    "hd_miss": "ihdm",
    "fenwick": "iff",
    "fenwick_adj": "iff_adj",
    "hd_fenwick": "ihdf",
    "corsi": "icf",
    "corsi_adj": "icf_adj",
    "block": "isb",
    "block_adj": "isb_adj",
    "hit": "ihf",
    "give": "igive",
    "take": "itake",
    "fac": "ifow",
    "ozf": "iozfw",
    "nzf": "inzfw",
    "dzf": "idzfw",
    "pen0": "ipent0",
    "pen2": "ipent2",
    "pen4": "ipent4",
    "pen5": "ipent5",
    "pen10": "ipent10",
}

# player_2 (defensive actions / penalties drawn / primary assist)
_IND_PLAYER2_DEF_RENAMES: dict[str, str] = {
    "block": "ibs",
    "fac": "ifol",
    "hit": "iht",
    "ozf": "iozfl",
    "nzf": "inzfl",
    "dzf": "idzfl",
    "pen0": "ipend0",
    "pen2": "ipend2",
    "pen4": "ipend4",
    "pen5": "ipend5",
    "pen10": "ipend10",
}

# player_2 primary assist renames
_IND_PLAYER2_ASSIST_RENAMES: dict[str, str] = {"goal": "a1", "pred_goal": "a1_xg"}

# player_3 secondary assist renames
_IND_PLAYER3_RENAMES: dict[str, str] = {"goal": "a2", "pred_goal": "a2_xg"}

# on-ice "for" renames (event_on_* perspective)
_OI_FOR_RENAMES: dict[str, str] = {
    "goal": "gf",
    "goal_adj": "gf_adj",
    "hd_goal": "hdgf",
    "pred_goal": "xgf",
    "pred_goal_adj": "xgf_adj",
    "shot": "sf",
    "shot_adj": "sf_adj",
    "hd_shot": "hdsf",
    "miss": "msf",
    "hd_miss": "hdmsf",
    "fenwick": "ff",
    "fenwick_adj": "ff_adj",
    "hd_fenwick": "hdff",
    "corsi": "cf",
    "corsi_adj": "cf_adj",
    "block": "bsf",
    "hit": "hf",
    "give": "give",
    "take": "take",
    "fac": "fow",
    "ozf": "ozfw",
    "nzf": "nzfw",
    "dzf": "dzfw",
    "pen0": "pent0",
    "pen2": "pent2",
    "pen4": "pent4",
    "pen5": "pent5",
    "pen10": "pent10",
    "event_length": "event_length",
}

# on-ice "against" renames (opp_on_* perspective — also flips team columns)
_OI_AGAINST_RENAMES: dict[str, str] = {
    "goal": "ga",
    "goal_adj": "ga_adj",
    "hd_goal": "hdga",
    "pred_goal": "xga",
    "pred_goal_adj": "xga_adj",
    "shot": "sa",
    "shot_adj": "sa_adj",
    "hd_shot": "hdsa",
    "miss": "msa",
    "hd_miss": "hdmsa",
    "fenwick": "fa",
    "fenwick_adj": "fa_adj",
    "hd_fenwick": "hdfa",
    "corsi": "ca",
    "corsi_adj": "ca_adj",
    "block": "bsa",
    "hit": "ht",
    "fac": "fol",
    "ozf": "dzfl",  # from opp perspective, their OZ = event team DZ
    "nzf": "nzfl",
    "dzf": "ozfl",  # from opp perspective, their DZ = event team OZ
    "pen0": "pend0",
    "pen2": "pend2",
    "pen4": "pend4",
    "pen5": "pend5",
    "pen10": "pend10",
    "event_length": "event_length",
}

# oi composite column flips for opp perspective
_OI_COMPOSITE_FLIP: dict[str, str] = {
    "opp_forwards": "forwards",
    "opp_forwards_eh_id": "forwards_eh_id",
    "opp_defense": "defense",
    "opp_defense_eh_id": "defense_eh_id",
    "opp_goalie": "own_goalie",
    "opp_goalie_eh_id": "own_goalie_eh_id",
    "forwards": "opp_forwards",
    "forwards_eh_id": "opp_forwards_eh_id",
    "defense": "opp_defense",
    "defense_eh_id": "opp_defense_eh_id",
    "own_goalie": "opp_goalie",
    "own_goalie_eh_id": "opp_goalie_eh_id",
    "opp_team": "team",
    "event_team": "opp_team",
    "opp_strength_state": "strength_state",
    "opp_score_state": "score_state",
}


def _build_merge_list(level: str, score: bool, teammates: bool, opposition: bool) -> list[str]:
    """Build the merge key list for prep_stats, using aligned column names."""
    base = ["season", "session", "player", "eh_id", "position", "team"]
    return build_group_list(
        base,
        level=level,
        strength_state=True,
        score=score,
        teammates=teammates,
        opposition=opposition,
        teammates_cols=TEAMMATES_COLS,
        opposition_cols=OPPOSITION_COLS,
    )


# ===========================================================================
# Individual stats
# ===========================================================================


def prep_ind(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepare individual player stats from EH PBP data (polars backend).

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.

    Returns:
        Polars DataFrame validated against ind_stats_polars_schema.
    """
    if isinstance(pbp, pl.LazyFrame):
        df = _collect(pbp)
    else:
        df = pbp

    players = ["event_player_1", "event_player_2", "event_player_3"]

    if level in ("session", "season"):
        merge_list = ["season", "session", "player", "eh_id", "position", "team", "strength_state"]
    elif level == "game":
        merge_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "player",
            "eh_id",
            "position",
            "team",
            "opp_team",
            "strength_state",
        ]
    else:
        merge_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "player",
            "eh_id",
            "position",
            "team",
            "opp_team",
            "strength_state",
            "period",
        ]

    if score:
        merge_list.append("score_state")
    if teammates:
        merge_list += ["forwards", "forwards_eh_id", "defense", "defense_eh_id", "own_goalie", "own_goalie_eh_id"]
    if opposition:
        merge_list += [
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_goalie",
            "opp_goalie_eh_id",
        ]
        if "opp_team" not in merge_list:
            merge_list.append("opp_team")

    frames: list[pl.DataFrame] = []

    for player in players:
        player_eh_id = f"{player}_eh_id"
        player_pos = f"{player}_pos"

        if level in ("session", "season"):
            group_base = ["season", "session", "event_team", player, player_eh_id, player_pos]
        elif level == "game":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                player,
                player_eh_id,
                player_pos,
            ]
        else:
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "period",
                player,
                player_eh_id,
                player_pos,
            ]

        if opposition and "opp_team" not in group_base:
            group_base.append("opp_team")

        not_bench = pl.col(player) != "BENCH"

        if player == "event_player_1":
            group_list = group_base + ["strength_state"]
            if teammates:
                group_list += [
                    "forwards",
                    "forwards_eh_id",
                    "defense",
                    "defense_eh_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                ]
            if score:
                group_list.append("score_state")
            if opposition:
                group_list += [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                ]

            group_list = [c for c in group_list if c in df.columns]
            agg_cols = [c for c in IND_STATS if c in df.columns]

            _p1_rename = {
                **_IND_PLAYER1_RENAMES,
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }
            player_df = (
                df.filter(not_bench)
                .group_by(group_list)
                .agg([pl.sum(c) for c in agg_cols])
                .rename({k: v for k, v in _p1_rename.items() if k in group_list + agg_cols})
            )

        elif player == "event_player_2":
            opp_group = group_base + ["opp_strength_state"]
            event_group = group_base + ["strength_state"]

            if not opposition and level in ("season", "session"):
                opp_group = [x for x in opp_group if x != "event_team"]
                opp_group.append("opp_team")

            if teammates:
                opp_group += [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                ]
                event_group += [
                    "forwards",
                    "forwards_eh_id",
                    "defense",
                    "defense_eh_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                ]
            if score:
                opp_group.append("opp_score_state")
                event_group.append("score_state")
            if opposition:
                opp_group += [
                    "forwards",
                    "forwards_eh_id",
                    "defense",
                    "defense_eh_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                ]
                event_group += [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                ]

            def_cols = [
                c
                for c in ["block", "fac", "hit", "pen0", "pen2", "pen4", "pen5", "pen10", "ozf", "nzf", "dzf"]
                if c in df.columns
            ]

            def_mask = not_bench & df["event_type"].is_in(["BLOCK", "FAC", "HIT", "PENL"])
            opp_group_clean = [c for c in opp_group if c in df.columns]

            _opps_rename = {
                **_IND_PLAYER2_DEF_RENAMES,
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_goalie": "own_goalie",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "own_goalie": "opp_goalie",
                "own_goalie_eh_id": "opp_goalie_eh_id",
            }
            opps = (
                df.filter(def_mask)
                .group_by(opp_group_clean)
                .agg([pl.sum(c) for c in def_cols])
                .rename({k: v for k, v in _opps_rename.items() if k in opp_group_clean + def_cols})
            )

            assist_cols = [c for c in ["goal", "pred_goal"] if c in df.columns]
            assist_mask = not_bench & (df["event_type"] == "GOAL")
            event_group_clean = [c for c in event_group if c in df.columns]

            _own_rename = {
                **_IND_PLAYER2_ASSIST_RENAMES,
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }
            own = (
                df.filter(assist_mask)
                .group_by(event_group_clean)
                .agg([pl.sum(c) for c in assist_cols])
                .rename({k: v for k, v in _own_rename.items() if k in event_group_clean + assist_cols})
            )

            merge_keys = [c for c in merge_list if c in opps.columns and c in own.columns]
            player_df = opps.join(own, on=merge_keys, how="full", coalesce=True).fill_null(0)

        else:  # event_player_3
            group_list = group_base + ["strength_state"]
            if teammates:
                group_list += [
                    "forwards",
                    "forwards_eh_id",
                    "defense",
                    "defense_eh_id",
                    "own_goalie",
                    "own_goalie_eh_id",
                ]
            if score:
                group_list.append("score_state")
            if opposition:
                group_list += [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                ]
                if "opp_team" not in group_list:
                    group_list.append("opp_team")

            group_list = [c for c in group_list if c in df.columns]
            agg_cols = [c for c in ["goal", "pred_goal"] if c in df.columns]

            _p3_rename = {
                **_IND_PLAYER3_RENAMES,
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }
            player_df = (
                df.filter(not_bench)
                .group_by(group_list)
                .agg([pl.sum(c) for c in agg_cols])
                .rename({k: v for k, v in _p3_rename.items() if k in group_list + agg_cols})
            )

        frames.append(player_df)

    # Merge all three player frames on merge_list
    ind_stats = frames[0]
    for frame in frames[1:]:
        merge_keys = [c for c in merge_list if c in ind_stats.columns and c in frame.columns]
        ind_stats = ind_stats.join(frame, on=merge_keys, how="full", coalesce=True).fill_null(0)

    ind_stats = validate_dataframe(ind_stats, ind_stats_pandera_polars)
    return ind_stats


# ===========================================================================
# On-ice stats
# ===========================================================================


def prep_oi(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepare on-ice stats from EH PBP data (polars backend).

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.

    Returns:
        Polars DataFrame validated against oi_stats_polars_schema.
    """
    if isinstance(pbp, pl.LazyFrame):
        df = _collect(pbp)
    else:
        df = pbp

    event_players = [f"event_on_{x}" for x in range(1, 8)]
    opp_players = [f"opp_on_{x}" for x in range(1, 8)]
    all_players = event_players + opp_players

    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "player",
        "eh_id",
        "position",
        "period",
        "strength_state",
        "score_state",
        "forwards",
        "forwards_eh_id",
        "defense",
        "defense_eh_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    event_list: list[pl.DataFrame] = []
    opp_list: list[pl.DataFrame] = []

    for player in all_players:
        player_eh_id = f"{player}_eh_id"
        player_pos = f"{player}_pos"

        if level in ("session", "season"):
            group_list = ["season", "session"]
        elif level == "game":
            group_list = ["season", "game_id", "game_date", "session", "event_team", "opp_team"]
        else:
            group_list = ["season", "game_id", "game_date", "session", "event_team", "opp_team", "period"]

        if player in event_players:
            if level in ("session", "season"):
                group_list.append("event_team")
            group_list += [player, player_eh_id, player_pos, "strength_state"]
            if teammates:
                group_list += TEAMMATES_COLS
            if score:
                group_list.append("score_state")
            if opposition:
                group_list += OPPOSITION_COLS

            rename = {
                **_OI_FOR_RENAMES,
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }

        else:
            if level in ("session", "season"):
                group_list.append("opp_team")
            group_list += [player, player_eh_id, player_pos, "opp_strength_state"]
            if teammates:
                group_list += OPPOSITION_COLS  # opp perspective: their teammates = our opposition
            if score:
                group_list.append("opp_score_state")
            if opposition:
                group_list += TEAMMATES_COLS  # opp perspective: their opposition = our teammates

            rename = {
                **_OI_AGAINST_RENAMES,
                **_OI_COMPOSITE_FLIP,
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }

        group_list = [c for c in group_list if c in df.columns]
        agg_cols = [c for c in OI_STATS if c in df.columns]
        rename_clean = {k: v for k, v in rename.items() if k in df.columns or k in rename}

        player_df = (
            df.filter(pl.col(player).is_not_null())
            .group_by(group_list)
            .agg([pl.sum(c) for c in agg_cols])
            .rename({k: v for k, v in rename_clean.items() if k in (group_list + [c for c in agg_cols])})
        )

        if player in event_players:
            event_list.append(player_df)
        else:
            opp_list.append(player_df)

    # Consolidate event and opp lists
    event_stats = pl.concat(event_list, how="diagonal_relaxed")
    active_merge_e = [c for c in merge_cols if c in event_stats.columns]
    stat_cols_e = [c for c in event_stats.columns if c not in merge_cols]
    event_stats = event_stats.group_by(active_merge_e).agg([pl.sum(c) for c in stat_cols_e])

    opp_stats = pl.concat(opp_list, how="diagonal_relaxed")
    active_merge_o = [c for c in merge_cols if c in opp_stats.columns]
    stat_cols_o = [c for c in opp_stats.columns if c not in merge_cols]
    opp_stats = opp_stats.group_by(active_merge_o).agg([pl.sum(c) for c in stat_cols_o])

    join_keys = [c for c in merge_cols if c in event_stats.columns and c in opp_stats.columns]
    oi_stats = event_stats.join(opp_stats, on=join_keys, how="full", coalesce=True).fill_null(0)

    # TOI
    if "event_length" in oi_stats.columns and "event_length_right" in oi_stats.columns:
        oi_stats = oi_stats.with_columns(
            ((pl.col("event_length") + pl.col("event_length_right")) / 60).alias("toi")
        ).drop(["event_length", "event_length_right"])
    elif "event_length" in oi_stats.columns:
        oi_stats = oi_stats.with_columns((pl.col("event_length") / 60).alias("toi")).drop("event_length")

    # Faceoff totals
    fo_exprs = []
    for fo in ("ozf", "nzf", "dzf"):
        w_col, l_col = f"{fo}w", f"{fo}l"
        if w_col in oi_stats.columns and l_col in oi_stats.columns:
            fo_exprs.append((pl.col(w_col) + pl.col(l_col)).alias(fo))
    if fo_exprs:
        oi_stats = oi_stats.with_columns(fo_exprs)

    if all(c in oi_stats.columns for c in ("ozf", "nzf", "dzf")):
        oi_stats = oi_stats.with_columns((pl.col("ozf") + pl.col("nzf") + pl.col("dzf")).alias("fac"))

    oi_stats = validate_dataframe(oi_stats, oi_stats_pandera_polars)
    return oi_stats


# ===========================================================================
# Zone starts (EH-specific — from CHANGE events)
# ===========================================================================


def _prep_zones_polars(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepare zone-start stats from EH CHANGE events (internal, polars)."""
    if isinstance(pbp, pl.LazyFrame):
        df = _collect(pbp)
    else:
        df = pbp

    zone_cond = (pl.col("event_type") == "CHANGE") & (
        (pl.col("ozs") > 0) | (pl.col("nzs") > 0) | (pl.col("dzs") > 0) | (pl.col("otf") > 0)
    )
    df = df.filter(zone_cond)

    if level in ("session", "season"):
        group_list = ["season", "session", "event_team", "strength_state"]
    elif level == "game":
        group_list = ["season", "session", "game_id", "game_date", "event_team", "strength_state", "opp_team"]
    else:
        group_list = ["season", "session", "game_id", "game_date", "period", "event_team", "strength_state", "opp_team"]

    if score:
        group_list.append("score_state")
    if teammates:
        group_list += TEAMMATES_COLS
    if opposition:
        group_list += OPPOSITION_COLS

    group_list = [c for c in group_list if c in df.columns]
    zone_stats_present = [c for c in ZONE_STATS if c in df.columns]

    # Explode players_on into separate rows
    df_exploded = (
        df.select(group_list + zone_stats_present + ["players_on", "players_on_eh_id", "players_on_pos"])
        .with_columns(
            [
                pl.col("players_on").str.split(", "),
                pl.col("players_on_eh_id").str.split(", "),
                pl.col("players_on_pos").str.split(", "),
            ]
        )
        .explode(["players_on", "players_on_eh_id", "players_on_pos"])
        .rename({"players_on": "player", "players_on_eh_id": "eh_id", "players_on_pos": "position"})
    )

    grp = [c for c in group_list + ["player", "eh_id", "position"] if c in df_exploded.columns]
    zones = (
        df_exploded.filter(
            pl.col("player").is_not_null()
            & (pl.col("player") != "")
            & pl.col("eh_id").is_not_null()
            & (pl.col("eh_id") != "")
        )
        .group_by(grp)
        .agg([pl.sum(c) for c in zone_stats_present])
        .rename({"event_team": "team"})
    )

    return zones


# ===========================================================================
# Combined player stats
# ===========================================================================


def prep_stats(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepare combined individual + on-ice player stats (polars backend).

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        disable_progress_bar: Whether to suppress the progress bar.

    Returns:
        Polars DataFrame validated against stats_polars_schema.
    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Prepping stats data...", total=1)

        if isinstance(pbp, pl.LazyFrame):
            pbp = _collect(pbp)

        ind = prep_ind(pbp, level, score, teammates, opposition)
        oi = prep_oi(pbp, level, score, teammates, opposition)
        zones = _prep_zones_polars(pbp, level, score, teammates, opposition)

        merge_cols = _build_merge_list(level, score, teammates, opposition)
        oi_merge = [c for c in merge_cols if c in oi.columns and c in ind.columns]
        stats = oi.join(ind, on=oi_merge, how="left", coalesce=True).fill_null(0)

        zone_merge = [c for c in merge_cols if c in stats.columns and c in zones.columns]
        stats = stats.join(zones, on=zone_merge, how="left", coalesce=True).fill_null(0)
        stats = stats.filter(pl.col("toi") > 0)

        stats = _prep_p60(stats, P60_STATS)
        stats = _prep_oi_percent(stats, OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST)

        stats = validate_dataframe(stats, stats_pandera_polars)

        progress.update(task, description="Finished prepping stats data", advance=1, refresh=True)

    return stats


# ===========================================================================
# Lines
# ===========================================================================


def prep_lines(
    pbp: pl.DataFrame | pl.LazyFrame,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepare line stats from EH PBP data (polars backend).

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        position: Position group — 'f' (forwards) or 'd' (defense).
        level: Aggregation level.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        disable_progress_bar: Whether to suppress the progress bar.

    Returns:
        Polars DataFrame validated against line_stats_polars_schema.
    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Prepping lines data...", total=1)

        if isinstance(pbp, pl.LazyFrame):
            df = _collect(pbp)
        else:
            df = pbp

        pos_col = "forwards" if position == "f" else "defense"
        pos_eh_col = f"{pos_col}_eh_id"
        opp_pos_col = f"opp_{pos_col}"
        opp_pos_eh_col = f"opp_{pos_col}_eh_id"

        # ---- "For" stats ----
        if level in ("session", "season"):
            group_base = ["season", "session", "event_team", "strength_state"]
        elif level == "game":
            group_base = ["season", "game_id", "game_date", "session", "event_team", "opp_team", "strength_state"]
        else:
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "period",
                "strength_state",
            ]

        if score:
            group_base = group_base + ["score_state"]

        group_f = group_base + [pos_col, pos_eh_col]
        if teammates:
            if position == "f":
                group_f += ["defense", "defense_eh_id", "own_goalie", "own_goalie_eh_id"]
            else:
                group_f += ["forwards", "forwards_eh_id", "own_goalie", "own_goalie_eh_id"]
        if opposition:
            group_f += [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_goalie",
                "opp_goalie_eh_id",
            ]
            if "opp_team" not in group_f:
                group_f.append("opp_team")

        for_stats = [
            "pred_goal",
            "pred_goal_adj",
            "corsi",
            "corsi_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "miss",
            "block",
            "shot",
            "shot_adj",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "event_length",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "hit",
            "give",
            "take",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
        ]
        for_out = [
            "xgf",
            "xgf_adj",
            "cf",
            "cf_adj",
            "ff",
            "ff_adj",
            "gf",
            "gf_adj",
            "msf",
            "bsf",
            "sf",
            "sf_adj",
            "hdgf",
            "hdsf",
            "hdff",
            "hdmsf",
            "toi",
            "fow",
            "ozfw",
            "nzfw",
            "dzfw",
            "hf",
            "give",
            "take",
            "pent0",
            "pent2",
            "pent4",
            "pent5",
            "pent10",
        ]
        for_rename = {**dict(zip(for_stats, for_out, strict=False)), "event_team": "team"}

        group_f_clean = [c for c in group_f if c in df.columns]
        for_agg_cols = [c for c in for_stats if c in df.columns]

        lines_f = (
            df.group_by(group_f_clean)
            .agg([pl.sum(c) for c in for_agg_cols])
            .rename({k: v for k, v in for_rename.items() if k in group_f_clean + for_agg_cols})
        )
        fill_cols = [
            c
            for c in [
                "forwards",
                "forwards_eh_id",
                "defense",
                "defense_eh_id",
                "own_goalie",
                "own_goalie_eh_id",
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_goalie",
                "opp_goalie_eh_id",
            ]
            if c in lines_f.columns
        ]
        if fill_cols:
            lines_f = lines_f.with_columns([pl.col(c).fill_null("EMPTY") for c in fill_cols])

        # ---- "Against" stats ----
        if level in ("session", "season"):
            group_base_a = ["season", "session", "opp_team", "opp_strength_state"]
        elif level == "game":
            group_base_a = ["season", "game_id", "game_date", "session", "event_team", "opp_team", "opp_strength_state"]
        else:
            group_base_a = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "period",
                "opp_strength_state",
            ]

        if score:
            group_base_a = group_base_a + ["opp_score_state"]

        group_a = group_base_a + [opp_pos_col, opp_pos_eh_col]
        if teammates:
            if position == "f":
                group_a += ["opp_defense", "opp_defense_eh_id", "opp_goalie", "opp_goalie_eh_id"]
            else:
                group_a += ["opp_forwards", "opp_forwards_eh_id", "opp_goalie", "opp_goalie_eh_id"]
        if opposition:
            group_a += ["forwards", "forwards_eh_id", "defense", "defense_eh_id", "own_goalie", "own_goalie_eh_id"]
            if "event_team" not in group_a:
                group_a.append("event_team")

        against_stats = [
            "pred_goal",
            "pred_goal_adj",
            "corsi",
            "corsi_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "miss",
            "block",
            "shot",
            "shot_adj",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "event_length",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "hit",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
        ]
        against_out = [
            "xga",
            "xga_adj",
            "ca",
            "ca_adj",
            "fa",
            "fa_adj",
            "ga",
            "ga_adj",
            "msa",
            "bsa",
            "sa",
            "sa_adj",
            "hdga",
            "hdsa",
            "hdfa",
            "hdmsa",
            "toi",
            "fol",
            "ozfl",
            "nzfl",
            "dzfl",
            "ht",
            "pend0",
            "pend2",
            "pend4",
            "pend5",
            "pend10",
        ]
        against_rename = {
            **dict(zip(against_stats, against_out, strict=False)),
            "opp_team": "team",
            "event_team": "opp_team",
            "opp_strength_state": "strength_state",
            "opp_score_state": "score_state",
            opp_pos_col: pos_col,
            opp_pos_eh_col: pos_eh_col,
            "opp_forwards": "forwards",
            "opp_forwards_eh_id": "forwards_eh_id",
            "opp_defense": "defense",
            "opp_defense_eh_id": "defense_eh_id",
            "opp_goalie": "own_goalie",
            "opp_goalie_eh_id": "own_goalie_eh_id",
            "forwards": "opp_forwards",
            "forwards_eh_id": "opp_forwards_eh_id",
            "defense": "opp_defense",
            "defense_eh_id": "opp_defense_eh_id",
            "own_goalie": "opp_goalie",
            "own_goalie_eh_id": "opp_goalie_eh_id",
        }

        group_a_clean = [c for c in group_a if c in df.columns]
        against_agg_cols = [c for c in against_stats if c in df.columns]

        lines_a = (
            df.group_by(group_a_clean)
            .agg([pl.sum(c) for c in against_agg_cols])
            .rename({k: v for k, v in against_rename.items() if k in group_a_clean + against_agg_cols})
        )
        for c in fill_cols:
            if c in lines_a.columns:
                lines_a = lines_a.with_columns(pl.col(c).fill_null("EMPTY"))

        # ---- Merge ----
        if level in ("session", "season"):
            merge_list = ["season", "session", "team", "strength_state", pos_col, pos_eh_col]
        elif level == "game":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "strength_state",
                pos_col,
                pos_eh_col,
            ]
        else:
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "strength_state",
                "period",
                pos_col,
                pos_eh_col,
            ]

        if score:
            merge_list.append("score_state")
        if teammates:
            if position == "f":
                merge_list += ["defense", "defense_eh_id", "own_goalie", "own_goalie_eh_id"]
            else:
                merge_list += ["forwards", "forwards_eh_id", "own_goalie", "own_goalie_eh_id"]
        if opposition:
            merge_list += [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_goalie",
                "opp_goalie_eh_id",
            ]
            if "opp_team" not in merge_list:
                merge_list.insert(3, "opp_team")

        merge_list = [c for c in merge_list if c in lines_f.columns and c in lines_a.columns]
        lines = lines_f.join(lines_a, on=merge_list, how="full", coalesce=True).fill_null(0)

        # TOI
        if "toi" in lines.columns and "toi_right" in lines.columns:
            lines = lines.with_columns(((pl.col("toi") + pl.col("toi_right")) / 60).alias("toi")).drop("toi_right")

        for fo in ("ozf", "nzf", "dzf"):
            wins, losses = f"{fo}w", f"{fo}l"
            if wins in lines.columns and losses in lines.columns:
                lines = lines.with_columns((pl.col(wins) + pl.col(losses)).alias(fo))

        lines = lines.filter(pl.col("toi") > 0)

        lines = _prep_p60(lines, P60_STATS)
        lines = _prep_oi_percent(lines, OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST)

        lines = validate_dataframe(lines, line_stats_pandera_polars)

        progress.update(task, description="Finished prepping lines data", advance=1, refresh=True)

    return lines


# ===========================================================================
# Team stats
# ===========================================================================


def prep_team_stats(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepare team stats from EH PBP data (polars backend).

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level.
        strengths: Whether to split by strength state.
        score: Whether to split by score state.
        disable_progress_bar: Whether to suppress the progress bar.

    Returns:
        Polars DataFrame validated against team_stats_polars_schema.
    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Prepping team data...", total=1)

        if isinstance(pbp, pl.LazyFrame):
            df = _collect(pbp)
        else:
            df = pbp

        # ---- "For" stats ----
        group_list = ["season", "session", "event_team"]
        if strengths:
            group_list.append("strength_state")
        if level in ("game", "period"):
            group_list[2:2] = ["game_id", "game_date"]
            group_list.insert(5, "opp_team")
        if level == "period":
            group_list.append("period")
        if score:
            group_list.append("score_state")

        for_stats = [
            "pred_goal",
            "pred_goal_adj",
            "shot",
            "shot_adj",
            "miss",
            "block",
            "corsi",
            "corsi_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "give",
            "take",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "hit",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "event_length",
        ]
        for_out = [
            "xgf",
            "xgf_adj",
            "sf",
            "sf_adj",
            "msf",
            "bsa",
            "cf",
            "cf_adj",
            "ff",
            "ff_adj",
            "gf",
            "gf_adj",
            "give",
            "take",
            "hdgf",
            "hdsf",
            "hdff",
            "hdmsf",
            "hf",
            "pent0",
            "pent2",
            "pent4",
            "pent5",
            "pent10",
            "fow",
            "ozfw",
            "nzfw",
            "dzfw",
            "toi",
        ]
        for_rename = {**dict(zip(for_stats, for_out, strict=False)), "event_team": "team"}

        group_f_clean = [c for c in group_list if c in df.columns]
        for_agg_cols = [c for c in for_stats if c in df.columns]

        stats_for = (
            df.filter(pl.col("event_team").is_not_null())
            .group_by(group_f_clean)
            .agg([pl.sum(c) for c in for_agg_cols])
            .rename({k: v for k, v in for_rename.items() if k in group_f_clean + for_agg_cols})
        )

        # ---- "Against" stats ----
        group_list_a = ["season", "session", "opp_team"]
        if strengths:
            group_list_a.append("opp_strength_state")
        if level in ("game", "period"):
            group_list_a[2:2] = ["game_id", "game_date"]
            group_list_a.insert(5, "event_team")
        if level == "period":
            group_list_a.append("period")
        if score:
            group_list_a.append("opp_score_state")

        against_stats = [
            "pred_goal",
            "pred_goal_adj",
            "shot",
            "shot_adj",
            "miss",
            "block",
            "corsi",
            "corsi_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "hd_goal",
            "hd_shot",
            "hd_fenwick",
            "hd_miss",
            "hit",
            "pen0",
            "pen2",
            "pen4",
            "pen5",
            "pen10",
            "fac",
            "ozf",
            "nzf",
            "dzf",
            "event_length",
        ]
        against_out = [
            "xga",
            "xga_adj",
            "sa",
            "sa_adj",
            "msa",
            "bsf",
            "ca",
            "ca_adj",
            "fa",
            "fa_adj",
            "ga",
            "ga_adj",
            "hdga",
            "hdsa",
            "hdfa",
            "hdmsa",
            "ht",
            "pend0",
            "pend2",
            "pend4",
            "pend5",
            "pend10",
            "fol",
            "ozfl",
            "nzfl",
            "dzfl",
            "toi",
        ]
        against_rename = {
            **dict(zip(against_stats, against_out, strict=False)),
            "opp_team": "team",
            "event_team": "opp_team",
            "opp_strength_state": "strength_state",
            "opp_score_state": "score_state",
        }

        group_a_clean = [c for c in group_list_a if c in df.columns]
        against_agg_cols = [c for c in against_stats if c in df.columns]

        stats_against = (
            df.filter(pl.col("opp_team").is_not_null())
            .group_by(group_a_clean)
            .agg([pl.sum(c) for c in against_agg_cols])
            .rename({k: v for k, v in against_rename.items() if k in group_a_clean + against_agg_cols})
        )

        merge_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "team",
            "opp_team",
            "strength_state",
            "score_state",
            "period",
        ]
        merge_list = [c for c in merge_list if c in stats_for.columns and c in stats_against.columns]

        team_stats = stats_for.join(stats_against, on=merge_list, how="full", coalesce=True).fill_null(0)

        if "toi" in team_stats.columns and "toi_right" in team_stats.columns:
            team_stats = team_stats.with_columns(((pl.col("toi") + pl.col("toi_right")) / 60).alias("toi")).drop(
                "toi_right"
            )

        fo_exprs = []
        for fo in ("ozf", "nzf", "dzf"):
            wins, losses = f"{fo}w", f"{fo}l"
            if wins in team_stats.columns and losses in team_stats.columns:
                fo_exprs.append((pl.col(wins) + pl.col(losses)).alias(fo))
        if fo_exprs:
            team_stats = team_stats.with_columns(fo_exprs)

        team_stats = team_stats.filter(pl.col("toi").is_not_null())

        team_stats = _prep_p60(team_stats, P60_STATS)
        team_stats = _prep_oi_percent(team_stats, OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST)

        team_stats = validate_dataframe(team_stats, team_stats_pandera_polars)

        progress.update(task, description="Finished prepping team data", advance=1, refresh=True)

    return team_stats


# ===========================================================================
# GAR / xGAR (EH website CSV exports)
# ===========================================================================

_TEAM_REPLACE = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}


def prep_gar(skater_data: pl.DataFrame, goalie_data: pl.DataFrame) -> pl.DataFrame:
    """Prepare GAR stats from EH CSV exports (polars backend).

    Parameters:
        skater_data: Polars DataFrame loaded from EH skater GAR CSV.
        goalie_data: Polars DataFrame loaded from EH goalie GAR CSV.

    Returns:
        Normalized polars DataFrame with eh_id column.
    """
    gar = pl.concat([skater_data, goalie_data], how="diagonal_relaxed")
    gar = gar.rename({c: c.replace(" ", "_").lower() for c in gar.columns})

    gar = gar.with_columns(
        [
            (
                pl.lit("20")
                + pl.col("season").str.split("-").list.get(0)
                + pl.lit("20")
                + pl.col("season").str.split("-").list.get(1)
            ).alias("season"),
            pl.col("birthday").str.to_date(strict=False),
            pl.col("player").str.to_uppercase(),
            pl.col("eh_id").str.replace("..", ".", literal=True),
            pl.col("team").replace(_TEAM_REPLACE),
        ]
    )

    return gar


def prep_xgar(data: pl.DataFrame) -> pl.DataFrame:
    """Prepare xGAR stats from EH CSV exports (polars backend).

    Parameters:
        data: Polars DataFrame loaded from EH xGAR CSV.

    Returns:
        Normalized polars DataFrame with eh_id column.
    """
    xgar = data.rename({c: c.replace(" ", "_").lower() for c in data.columns})

    xgar = xgar.with_columns(
        [
            (
                pl.lit("20")
                + pl.col("season").str.split("-").list.get(0)
                + pl.lit("20")
                + pl.col("season").str.split("-").list.get(1)
            ).alias("season"),
            pl.col("birthday").str.to_date(strict=False),
            pl.col("player").str.to_uppercase(),
            pl.col("eh_id").str.replace("..", ".", literal=True),
            pl.col("team").replace(_TEAM_REPLACE),
        ]
    )

    return xgar
