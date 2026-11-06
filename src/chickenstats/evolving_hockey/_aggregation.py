"""Aggregation functions for evolving-hockey.com play-by-play data.

Polars-only internally. All public functions accept any narwhals-compatible
input via stats.py, which handles backend detection and output conversion.

All stat-level validation schemas are imported from chickenstats.evolving_hockey.validation.
All shared utilities (_prep_p60, _prep_oi_percent) are imported from chickenstats.chicken_nhl.
"""

from __future__ import annotations

from typing import Literal

from chickenstats.utilities.enums import AggLevel

import polars as pl

from chickenstats.chicken_nhl._aggregation import _drop_empty_rows, _prep_p60, _prep_oi_percent
from chickenstats.exceptions import DataMismatchError, InvalidInputError
from chickenstats.evolving_hockey._names import eh_id_expr, player_name_expr
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
    TEAM_REPLACE,
)
from chickenstats.chicken_nhl._validation_utils import validate_dataframe
from chickenstats.evolving_hockey.validation import (
    eh_ind_stats_pandera_polars as ind_stats_pandera_polars,
    eh_oi_stats_pandera_polars as oi_stats_pandera_polars,
    eh_stats_pandera_polars as stats_pandera_polars,
    eh_line_stats_pandera_polars as line_stats_pandera_polars,
    eh_team_stats_pandera_polars as team_stats_pandera_polars,
    eh_gar_pandera_polars as gar_pandera_polars,
    eh_xgar_pandera_polars as xgar_pandera_polars,
)
from chickenstats.utilities.utilities import COLLECT_ENGINE, ChickenProgress


def _collect(lf: pl.LazyFrame) -> pl.DataFrame:
    """Collect a LazyFrame to an eager DataFrame.

    LazyFrame.collect() is overloaded but ty resolves to the implementation signature
    which returns DataFrame | InProcessQuery. This helper asserts the runtime guarantee
    (no background=True → always DataFrame) in a single place.
    """
    result = lf.collect(engine=COLLECT_ENGINE)
    assert isinstance(result, pl.DataFrame)
    return result


# -----------------------------------------------------------------------------
# Column name maps — EH PBP raw stat names → shared schema stat names
# -----------------------------------------------------------------------------

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
    "block_adj": "ibs_adj",
    "fac": "ifol",
    "hit": "iht",
    "ozf": "idzfl",  # the loser's zone is the winner's flipped
    "nzf": "inzfl",
    "dzf": "iozfl",
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
    "miss_adj": "msf_adj",
    "hd_miss": "hdmsf",
    "fenwick": "ff",
    "fenwick_adj": "ff_adj",
    "hd_fenwick": "hdff",
    "corsi": "cf",
    "corsi_adj": "cf_adj",
    "block": "bsf",
    "block_adj": "bsf_adj",
    "teammate_block": "teammate_block",
    "teammate_block_adj": "teammate_block_adj",
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
    "miss_adj": "msa_adj",
    "hd_miss": "hdmsa",
    "fenwick": "fa",
    "fenwick_adj": "fa_adj",
    "hd_fenwick": "hdfa",
    "corsi": "ca",
    "corsi_adj": "ca_adj",
    "block": "bsa",
    "block_adj": "bsa_adj",
    "teammate_block": "opp_teammate_block",
    "teammate_block_adj": "opp_teammate_block_adj",
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

# prep_lines and prep_team_stats sum event_length straight into toi
_LINE_FOR_RENAMES: dict[str, str] = {**_OI_FOR_RENAMES, "event_length": "toi"}
_LINE_AGAINST_RENAMES: dict[str, str] = {**_OI_AGAINST_RENAMES, "event_length": "toi"}

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


def _read_pbp(pbp: pl.DataFrame | pl.LazyFrame, level: str) -> pl.DataFrame:
    """Collect the play-by-play. A season is one row, regular season and playoffs together."""
    df = _collect(pbp) if isinstance(pbp, pl.LazyFrame) else pbp

    return df.with_columns(session=pl.lit("ALL")) if level == "season" else df


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
        ensure_team=opposition,
    )


# -----------------------------------------------------------------------------
# Individual stats
# -----------------------------------------------------------------------------


def prep_ind(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepare individual player stats from evolving-hockey.com play-by-play data.

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.

    Returns:
        Polars DataFrame validated against ind_stats_pandera_polars.
    """
    df = _read_pbp(pbp, level)

    players = ["event_player_1", "event_player_2", "event_player_3"]

    merge_list = build_group_list(
        ["season", "session", "player", "eh_id", "position", "team"],
        level=level,
        strength_state=True,
        score=score,
        teammates=teammates,
        opposition=opposition,
        teammates_cols=TEAMMATES_COLS,
        opposition_cols=OPPOSITION_COLS,
        ensure_team=opposition,
    )

    frames: list[pl.DataFrame] = []

    for player in players:
        player_eh_id = f"{player}_eh_id"
        player_pos = f"{player}_pos"

        not_bench = ~pl.col(player).is_in(["BENCH", "REFEREE"])

        if player == "event_player_1":
            group_list = build_group_list(
                ["season", "session", "event_team", player, player_eh_id, player_pos],
                level=level,
                strength_state=True,
                score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=TEAMMATES_COLS,
                opposition_cols=OPPOSITION_COLS,
                ensure_team=opposition,
            )

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
            event_group = build_group_list(
                ["season", "session", "event_team", player, player_eh_id, player_pos],
                level=level,
                strength_state=True,
                score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=TEAMMATES_COLS,
                opposition_cols=OPPOSITION_COLS,
                ensure_team=opposition,
            )
            opp_group = build_group_list(
                ["season", "session", "opp_team", player, player_eh_id, player_pos],
                level=level,
                opp_strength_state=True,
                opp_score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=OPPOSITION_COLS,
                opposition_cols=TEAMMATES_COLS,
                opp_perspective=True,
                ensure_team=opposition,
            )

            def_cols = [
                c
                for c in [
                    "block",
                    "block_adj",
                    "fac",
                    "hit",
                    "pen0",
                    "pen2",
                    "pen4",
                    "pen5",
                    "pen10",
                    "ozf",
                    "nzf",
                    "dzf",
                ]
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
            player_df = opps.join(own, on=merge_keys, how="full", coalesce=True, nulls_equal=True).fill_null(0)

        else:  # event_player_3
            group_list = build_group_list(
                ["season", "session", "event_team", player, player_eh_id, player_pos],
                level=level,
                strength_state=True,
                score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=TEAMMATES_COLS,
                opposition_cols=OPPOSITION_COLS,
                ensure_team=opposition,
            )

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
        ind_stats = ind_stats.join(frame, on=merge_keys, how="full", coalesce=True, nulls_equal=True).fill_null(0)

    # A shootout attempt leaves its shooter a row with nothing in it
    counts = [c for c, dtype in ind_stats.schema.items() if c not in merge_list and dtype.is_numeric()]
    ind_stats = ind_stats.remove(pl.all_horizontal(pl.col(counts) == 0))

    if level == "season":
        ind_stats = ind_stats.drop("session")

    ind_stats = validate_dataframe(ind_stats, ind_stats_pandera_polars)
    return ind_stats


# -----------------------------------------------------------------------------
# On-ice stats
# -----------------------------------------------------------------------------


def prep_oi(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepare on-ice stats from evolving-hockey.com play-by-play data.

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.

    Returns:
        Polars DataFrame validated against oi_stats_pandera_polars.
    """
    df = _read_pbp(pbp, level)

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

        if player in event_players:
            group_list = build_group_list(
                ["season", "session", "event_team", player, player_eh_id, player_pos],
                level=level,
                strength_state=True,
                score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=TEAMMATES_COLS,
                opposition_cols=OPPOSITION_COLS,
                ensure_team=opposition,
            )

            rename = {
                **_OI_FOR_RENAMES,
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }

        else:
            group_list = build_group_list(
                ["season", "session", "opp_team", player, player_eh_id, player_pos],
                level=level,
                opp_strength_state=True,
                opp_score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=OPPOSITION_COLS,  # opp perspective: their teammates = our opposition
                opposition_cols=TEAMMATES_COLS,  # opp perspective: their opposition = our teammates
                opp_perspective=True,
                ensure_team=opposition,
            )

            rename = {
                **_OI_AGAINST_RENAMES,
                **_OI_COMPOSITE_FLIP,
                player: "player",
                player_eh_id: "eh_id",
                player_pos: "position",
            }

        group_list = [c for c in group_list if c in df.columns]
        agg_cols = [c for c in OI_STATS if c in df.columns]
        player_df = (
            df.filter(pl.col(player).is_not_null())
            .group_by(group_list)
            .agg([pl.sum(c) for c in agg_cols])
            .rename({k: v for k, v in rename.items() if k in group_list + agg_cols})
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
    oi_stats = event_stats.join(opp_stats, on=join_keys, how="full", coalesce=True, nulls_equal=True).fill_null(0)

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

    if level == "season":
        oi_stats = oi_stats.drop("session")

    oi_stats = validate_dataframe(oi_stats, oi_stats_pandera_polars)
    return oi_stats


# -----------------------------------------------------------------------------
# Zone starts (EH-specific — from CHANGE events)
# -----------------------------------------------------------------------------


def _prep_zones_polars(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepare zone-start stats from EH CHANGE events (internal, polars)."""
    df = _read_pbp(pbp, level)

    zone_cond = (pl.col("event_type") == "CHANGE") & (
        (pl.col("ozs") > 0) | (pl.col("nzs") > 0) | (pl.col("dzs") > 0) | (pl.col("otf") > 0)
    )
    df = df.filter(zone_cond)

    group_list = build_group_list(
        ["season", "session", "event_team"],
        level=level,
        strength_state=True,
        score=score,
        teammates=teammates,
        opposition=opposition,
        teammates_cols=TEAMMATES_COLS,
        opposition_cols=OPPOSITION_COLS,
        ensure_team=opposition,
    )

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
        .explode(["players_on", "players_on_eh_id", "players_on_pos"], empty_as_null=True)
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

    return zones.drop("session") if level == "season" else zones


# -----------------------------------------------------------------------------
# Combined player stats
# -----------------------------------------------------------------------------


def prep_stats(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepare combined individual + on-ice player stats.

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        disable_progress_bar: Whether to suppress the progress bar.

    Returns:
        Polars DataFrame validated against stats_pandera_polars.
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
        # A full join, because an event can be credited to a player with no on-ice row in that group, such as a
        # secondary assist or a penalty taken from the bench
        stats = oi.join(ind, on=oi_merge, how="full", coalesce=True, nulls_equal=True).fill_null(0)

        zone_merge = [c for c in merge_cols if c in stats.columns and c in zones.columns]
        stats = stats.join(zones, on=zone_merge, how="full", coalesce=True, nulls_equal=True).fill_null(0)
        stats = _drop_empty_rows(stats, merge_cols)

        stats = _prep_p60(stats, P60_STATS)
        stats = _prep_oi_percent(stats, OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST)

        stats = validate_dataframe(stats, stats_pandera_polars)

        progress.update(task, description="Finished prepping stats data", advance=1, refresh=True)

    return stats


# -----------------------------------------------------------------------------
# Lines
# -----------------------------------------------------------------------------


def prep_lines(
    pbp: pl.DataFrame | pl.LazyFrame,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepare line stats from evolving-hockey.com play-by-play data.

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        position: Position group — 'f' (forwards) or 'd' (defense).
        level: Aggregation level.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        disable_progress_bar: Whether to suppress the progress bar.

    Returns:
        Polars DataFrame validated against line_stats_pandera_polars.
    """
    if position not in ("f", "d"):
        raise InvalidInputError(f"position must be 'f' or 'd', got {position!r}", obj=position)

    with ChickenProgress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Prepping lines data...", total=1)

        df = _read_pbp(pbp, level)

        pos_col = "forwards" if position == "f" else "defense"
        pos_eh_col = f"{pos_col}_eh_id"
        opp_pos_col = f"opp_{pos_col}"
        opp_pos_eh_col = f"opp_{pos_col}_eh_id"

        # ---- "For" stats ----
        teammates_extra = (
            ["defense", "defense_eh_id", "own_goalie", "own_goalie_eh_id"]
            if position == "f"
            else ["forwards", "forwards_eh_id", "own_goalie", "own_goalie_eh_id"]
        )
        teammates_extra_opp = (
            ["opp_defense", "opp_defense_eh_id", "opp_goalie", "opp_goalie_eh_id"]
            if position == "f"
            else ["opp_forwards", "opp_forwards_eh_id", "opp_goalie", "opp_goalie_eh_id"]
        )

        group_f = build_group_list(
            ["season", "session", "event_team", pos_col, pos_eh_col],
            level=level,
            strength_state=True,
            score=score,
            teammates=teammates,
            opposition=opposition,
            teammates_cols=teammates_extra,
            opposition_cols=OPPOSITION_COLS,
            ensure_team=opposition,
        )

        for_rename = {**_LINE_FOR_RENAMES, "event_team": "team"}

        group_f_clean = [c for c in group_f if c in df.columns]
        for_agg_cols = [c for c in _LINE_FOR_RENAMES if c in df.columns]

        lines_f = (
            df.group_by(group_f_clean)
            .agg([pl.sum(c) for c in for_agg_cols])
            .rename({k: v for k, v in for_rename.items() if k in group_f_clean + for_agg_cols})
        )
        # ---- "Against" stats ----
        group_a = build_group_list(
            ["season", "session", "opp_team", opp_pos_col, opp_pos_eh_col],
            level=level,
            opp_strength_state=True,
            opp_score=score,
            teammates=teammates,
            opposition=opposition,
            teammates_cols=teammates_extra_opp,
            opposition_cols=TEAMMATES_COLS,
            opp_perspective=True,
            ensure_team=opposition,
        )

        against_rename = {**_LINE_AGAINST_RENAMES, **_OI_COMPOSITE_FLIP}

        group_a_clean = [c for c in group_a if c in df.columns]
        against_agg_cols = [c for c in _LINE_AGAINST_RENAMES if c in df.columns]

        lines_a = (
            df.group_by(group_a_clean)
            .agg([pl.sum(c) for c in against_agg_cols])
            .rename({k: v for k, v in against_rename.items() if k in group_a_clean + against_agg_cols})
        )

        # ---- Merge ----
        merge_list = build_group_list(
            ["season", "session", "team", pos_col, pos_eh_col],
            level=level,
            strength_state=True,
            score=score,
            teammates=teammates,
            opposition=opposition,
            teammates_cols=teammates_extra,
            opposition_cols=OPPOSITION_COLS,
            ensure_team=opposition,
        )

        merge_list = [c for c in merge_list if c in lines_f.columns and c in lines_a.columns]
        lines = lines_f.join(lines_a, on=merge_list, how="full", coalesce=True, nulls_equal=True).fill_null(0)

        # TOI
        if "toi" in lines.columns and "toi_right" in lines.columns:
            lines = lines.with_columns(((pl.col("toi") + pl.col("toi_right")) / 60).alias("toi")).drop("toi_right")

        for fo in ("ozf", "nzf", "dzf"):
            wins, losses = f"{fo}w", f"{fo}l"
            if wins in lines.columns and losses in lines.columns:
                lines = lines.with_columns((pl.col(wins) + pl.col(losses)).alias(fo))

        lines = _drop_empty_rows(lines, merge_list)

        lines = _prep_p60(lines, P60_STATS)
        lines = _prep_oi_percent(lines, OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST)

        if level == "season":
            lines = lines.drop("session")

        lines = validate_dataframe(lines, line_stats_pandera_polars)

        progress.update(task, description="Finished prepping lines data", advance=1, refresh=True)

    return lines


# -----------------------------------------------------------------------------
# Team stats
# -----------------------------------------------------------------------------


def prep_team_stats(
    pbp: pl.DataFrame | pl.LazyFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
) -> pl.DataFrame:
    """Prepare team stats from evolving-hockey.com play-by-play data.

    Parameters:
        pbp: DataFrame or LazyFrame from prep_pbp.
        level: Aggregation level.
        strengths: Whether to split by strength state.
        score: Whether to split by score state.
        disable_progress_bar: Whether to suppress the progress bar.

    Returns:
        Polars DataFrame validated against team_stats_pandera_polars.
    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        task = progress.add_task("Prepping team data...", total=1)

        df = _read_pbp(pbp, level)

        # ---- "For" stats ----
        group_list = build_group_list(
            ["season", "session", "event_team"], level=level, strength_state=strengths, score=score
        )

        for_rename = {**_LINE_FOR_RENAMES, "event_team": "team"}

        group_f_clean = [c for c in group_list if c in df.columns]
        for_agg_cols = [c for c in _LINE_FOR_RENAMES if c in df.columns]

        stats_for = (
            df.filter(pl.col("event_team").is_not_null())
            .group_by(group_f_clean)
            .agg([pl.sum(c) for c in for_agg_cols])
            .rename({k: v for k, v in for_rename.items() if k in group_f_clean + for_agg_cols})
        )

        # ---- "Against" stats ----
        group_list_a = build_group_list(
            ["season", "session", "opp_team"],
            level=level,
            opp_strength_state=strengths,
            opp_score=score,
            opp_perspective=True,
        )

        against_rename = {**_LINE_AGAINST_RENAMES, **_OI_COMPOSITE_FLIP}

        group_a_clean = [c for c in group_list_a if c in df.columns]
        against_agg_cols = [c for c in _LINE_AGAINST_RENAMES if c in df.columns]

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

        team_stats = stats_for.join(
            stats_against, on=merge_list, how="full", coalesce=True, nulls_equal=True
        ).fill_null(0)

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

        team_stats = _drop_empty_rows(team_stats, merge_list)

        team_stats = _prep_p60(team_stats, P60_STATS)
        team_stats = _prep_oi_percent(team_stats, OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST)

        if level == "season":
            team_stats = team_stats.drop("session")

        team_stats = validate_dataframe(team_stats, team_stats_pandera_polars)

        progress.update(task, description="Finished prepping team data", advance=1, refresh=True)

    return team_stats


# -----------------------------------------------------------------------------
# GAR / xGAR (EH website CSV exports)
# -----------------------------------------------------------------------------

_EH_SEASON_PATTERN = r"^\d{2}-\d{2}$"


def _check_eh_season_format(df: pl.DataFrame) -> None:
    """Raise if any ``season`` value is not EH's expected two-digit-dash-two-digit format.

    The season is built from the first two digits with no guard of its own, so a season
    string with a different shape (a 4-digit-dash-4-digit format, or no dash at all) would
    give a wrong season rather than a clear error pointing at the malformed input.
    """
    bad_values = df.filter(~pl.col("season").str.contains(_EH_SEASON_PATTERN))["season"].unique().to_list()
    if bad_values:
        raise DataMismatchError(f"Unexpected EH season format (expected 'YY-YY', e.g. '23-24'): {bad_values}")


def _eh_season_expr() -> pl.Expr:
    """The eight-digit season of the play-by-play from EH's 'YY-YY', such as 20232024 from '23-24'."""
    first_year = pl.col("season").str.slice(0, 2).cast(pl.Int64)
    start = pl.when(first_year >= 50).then(1900 + first_year).otherwise(2000 + first_year)

    return ((start * 10000) + start + 1).alias("season")


def prep_gar(skater_data: pl.DataFrame, goalie_data: pl.DataFrame) -> pl.DataFrame:
    """Prepare GAR stats from evolving-hockey.com csv data.

    Parameters:
        skater_data: Polars DataFrame loaded from EH skater GAR CSV.
        goalie_data: Polars DataFrame loaded from EH goalie GAR CSV.

    Returns:
        Normalized polars DataFrame with eh_id column.
    """
    gar = pl.concat([skater_data, goalie_data], how="diagonal_relaxed")
    gar = gar.rename({c: c.replace(" ", "_").lower() for c in gar.columns})

    _check_eh_season_format(gar)

    gar = gar.with_columns(
        [
            _eh_season_expr(),
            pl.col("birthday").str.to_date(strict=False),
            pl.col("team").replace(TEAM_REPLACE),
            pl.lit(None, dtype=pl.String).alias("team_jersey"),
        ]
    )
    gar = gar.with_columns(eh_id_expr(pl.col("eh_id")), player_name_expr(pl.col("eh_id")).alias("player")).drop(
        "team_jersey"
    )

    gar = validate_dataframe(gar, gar_pandera_polars)

    return gar


def prep_xgar(data: pl.DataFrame) -> pl.DataFrame:
    """Prepare xGAR stats from evolving-hockey.com csv data.

    Parameters:
        data: Polars DataFrame loaded from EH xGAR CSV.

    Returns:
        Normalized polars DataFrame with eh_id column.
    """
    xgar = data.rename({c: c.replace(" ", "_").lower() for c in data.columns})

    _check_eh_season_format(xgar)

    xgar = xgar.with_columns(
        [
            _eh_season_expr(),
            pl.col("birthday").str.to_date(strict=False),
            pl.col("team").replace(TEAM_REPLACE),
            pl.lit(None, dtype=pl.String).alias("team_jersey"),
        ]
    )
    xgar = xgar.with_columns(eh_id_expr(pl.col("eh_id")), player_name_expr(pl.col("eh_id")).alias("player")).drop(
        "team_jersey"
    )

    xgar = validate_dataframe(xgar, xgar_pandera_polars)

    return xgar
