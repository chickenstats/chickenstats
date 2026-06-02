from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

import narwhals as nw

from chickenstats.utilities.enums import AggLevel
import polars as pl

if TYPE_CHECKING:
    import pandas as pd
from narwhals.typing import IntoFrameT
from polars import Int64, String

from chickenstats.chicken_nhl._agg_constants import (
    build_group_list,
    P60_STATS,
    OI_PERCENT_STATS_FOR,
    OI_PERCENT_STATS_AGAINST,
    TEAMMATES_COLS,
    OPPOSITION_COLS,
)
from chickenstats.chicken_nhl.validation_polars import (
    ind_stats_pandera_polars,
    oi_stats_pandera_polars,
    stats_pandera_polars,
    line_stats_pandera_polars,
    team_stats_pandera_polars,
)
from chickenstats.chicken_nhl._validation_utils import validate_dataframe


def _cast_api_id_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Cast any Float64 ``*_api_id`` columns to Int64, filling NaN with null first.

    Pandas nullable integers become Float64 in Polars when data crosses the
    pandas→polars boundary (NaN represents missing values). ``cast(Int64)`` does
    not convert NaN to null by itself, so ``fill_nan(None)`` must run first.
    Called at the top of ``prep_ind`` and ``prep_oi`` before player rows are built.
    """
    float_cols = [c for c in df.columns if c.endswith("_api_id") and df.schema[c] == pl.Float64]
    if float_cols:
        df = df.with_columns([pl.col(c).fill_nan(None).cast(pl.Int64) for c in float_cols])
    return df


@nw.narwhalify
def _prep_p60(df: IntoFrameT, stats: list) -> IntoFrameT:
    """Adds columns to normalize statistics on a 60-minute basis.

    Parameters:
        df (pd.DataFrame | pl.DataFrame):
            Statistics data from chickenstats.chicken_nhl.Scraper
    """
    existing = [s for s in stats if s in df.columns]
    return df.with_columns([((nw.col(stat) / nw.col("toi")) * 60).alias(f"{stat}_p60") for stat in existing])  # ty: ignore[unresolved-attribute]


def prep_p60(df: pd.DataFrame | pl.DataFrame) -> pd.DataFrame | pl.DataFrame:
    """Add per-60 normalized columns to a stats DataFrame.

    Divides each stat in ``P60_STATS`` by ``toi / 60``, appending a ``_p60`` suffix.
    Called by ``prep_stats``, ``prep_lines``, and ``prep_team_stats`` after the
    base aggregation step.

    Parameters:
        df (pd.DataFrame | pl.DataFrame): Stats DataFrame containing a ``toi`` column.
    """
    stats = P60_STATS

    df = _prep_p60(df, stats=stats)

    return df


@nw.narwhalify
def _prep_oi_percent(df: IntoFrameT, stats_for: list, stats_against: list) -> IntoFrameT:
    """Adds columns for on-ice percentages (e.g., xGF%).

    Parameters:
        df (pd.DataFrame | pl.DataFrame):
            Statistics data from chickenstats.chicken_nhl.Scraper
    """
    exprs = []

    for stat_for, stat_against in zip(stats_for, stats_against, strict=False):
        if stat_for not in df.columns:
            exprs.append(nw.lit(0.0).alias(f"{stat_for}_percent"))

        elif stat_against not in df.columns:
            exprs.append(nw.lit(1.0).alias(f"{stat_for}_percent"))

        else:
            exprs.append((nw.col(stat_for) / (nw.col(stat_for) + nw.col(stat_against))).alias(f"{stat_for}_percent"))

    return df.with_columns(exprs)  # ty: ignore[unresolved-attribute]


def prep_oi_percent(df: pd.DataFrame | pl.DataFrame) -> pd.DataFrame | pl.DataFrame:
    """Add on-ice percentage columns to a stats DataFrame.

    Pairs each stat in ``OI_PERCENT_STATS_FOR`` with its counterpart in
    ``OI_PERCENT_STATS_AGAINST`` and appends a ``_percent`` column
    (e.g., ``xgf_percent = xgf / (xgf + xga)``). Missing numerator columns
    produce ``0.0``; missing denominator columns produce ``1.0``.

    Parameters:
        df (pd.DataFrame | pl.DataFrame): Stats DataFrame containing for/against columns.
    """
    stats_for = OI_PERCENT_STATS_FOR

    stats_against = OI_PERCENT_STATS_AGAINST

    df = _prep_oi_percent(df, stats_for=stats_for, stats_against=stats_against)

    return df


def prep_ind(
    df: pl.DataFrame,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Aggregate individual stats per player from play-by-play data.

    Called internally by ``_ScraperStatsMixin._prep_ind``. Output columns are
    documented in ``Scraper.ind_stats``.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    df = df.clone()

    df = _cast_api_id_columns(df)

    players = ["player_1", "player_2", "player_3"]

    merge_list = build_group_list(
        ["season", "session", "player", "eh_id", "api_id", "position", "team"],
        level=level,
        strength_state=strength_state,
        score=score,
        teammates=teammates,
        opposition=opposition,
    )

    polars_schema = {
        "season": Int64,
        "session": String,
        "team": String,
        "player": String,
        "eh_id": String,
        "api_id": Int64,
        "position": String,
        "game_id": Int64,
        "game_date": String,
        "opp_team": String,
        "period": Int64,
        "strength_state": String,
        "forwards": String,
        "forwards_eh_id": String,
        "forwards_api_id": String,
        "defense": String,
        "defense_eh_id": String,
        "defense_api_id": String,
        "own_goalie": String,
        "own_goalie_eh_id": String,
        "own_goalie_api_id": Int64,
        "score_state": String,
        "opp_forwards": String,
        "opp_forwards_eh_id": String,
        "opp_forwards_api_id": String,
        "opp_defense": String,
        "opp_defense_eh_id": String,
        "opp_defense_api_id": String,
        "opp_goalie": String,
        "opp_goalie_eh_id": String,
        "opp_goalie_api_id": Int64,
    }

    polars_schema = {column: polars_schema[column] for column in merge_list}

    ind_stats = pl.DataFrame(schema=polars_schema)

    for player in players:
        player_eh_id = f"{player}_eh_id"
        player_api_id = f"{player}_api_id"
        position = f"{player}_position"

        group_base = ["season", "session", "event_team", player, player_eh_id, player_api_id, position]

        if level == "session" or level == "season":
            group_base = group_base

        if level == "game":
            group_base.extend(["game_id", "game_date", "opp_team"])

        if level == "period":
            group_base.extend(["game_id", "game_date", "opp_team", "period"])

        if opposition and "opp_team" not in group_base:
            group_base.append("opp_team")

        if player == "player_1":
            group_list = [
                c
                for c in build_group_list(
                    group_base, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )
                if c in df.columns
            ]

            stats_list = [
                "block",
                "block_adj",
                "fac",
                "give",
                "goal",
                "goal_adj",
                "hd_fenwick",
                "hd_goal",
                "hd_miss",
                "hd_shot",
                "hit",
                "miss",
                "miss_adj",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "shot",
                "shot_adj",
                "take",
                # "corsi",
                "fenwick",
                "fenwick_adj",
                "pred_goal",
                "pred_goal_adj",
                "base_xg",
                "base_xg_adj",
                "context_xg",
                "ozf",
                "nzf",
                "dzf",
            ]

            # stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            agg_stats = [pl.sum(x) for x in stats_list if x in df.columns]

            new_cols = {
                "block": "ibs",
                "block_adj": "ibs_adj",
                "fac": "ifow",
                "give": "igive",
                "goal": "g",
                "goal_adj": "g_adj",
                "hd_fenwick": "ihdf",
                "hd_goal": "ihdg",
                "hd_miss": "ihdm",
                "hd_shot": "ihdsf",
                "hit": "ihf",
                "miss": "imsf",
                "miss_adj": "imsf_adj",
                "pen0": "ipent0",
                "pen2": "ipent2",
                "pen4": "ipent4",
                "pen5": "ipent5",
                "pen10": "ipent10",
                "shot": "isf",
                "shot_adj": "isf_adj",
                "take": "itake",
                "fenwick": "iff",
                "fenwick_adj": "iff_adj",
                "pred_goal": "ixg",
                "pred_goal_adj": "ixg_adj",
                "base_xg": "base_ixg",
                "base_xg_adj": "base_ixg_adj",
                "context_xg": "context_ixg",
                "ozf": "iozfw",
                "nzf": "inzfw",
                "dzf": "idzfw",
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
            }

            filter_df = df.filter(
                ~pl.col(player).is_in(["BENCH", "REFEREE"]), ~pl.col("description").str.contains("BLOCKED BY TEAMMATE")
            )

            player_df = filter_df.group_by(group_list).agg(agg_stats)

            rename_cols = {column: new_cols[column] for column in new_cols if column in player_df.columns}

            player_df = player_df.rename(rename_cols)

        if player == "player_2":
            # Getting on-ice stats against for player 2

            opp_group_list = group_base.copy()

            if strength_state:
                opp_group_list.append("opp_strength_state")

            event_group_list = group_base.copy()

            if strength_state:
                event_group_list.append("strength_state")

            if not opposition and level in ["season", "session"]:
                opp_group_list.remove("event_team")
                opp_group_list.append("opp_team")

            if teammates:
                opp_group_list.extend(OPPOSITION_COLS)
                event_group_list.extend(TEAMMATES_COLS)

            if score:
                opp_group_list.append("opp_score_state")
                event_group_list.append("score_state")

            if opposition:
                opp_group_list.extend(TEAMMATES_COLS)
                event_group_list.extend(OPPOSITION_COLS)

            stats_1 = ["block", "block_adj", "fac", "hit", "pen0", "pen2", "pen4", "pen5", "pen10", "ozf", "nzf", "dzf"]

            agg_stats_1 = [pl.sum(x) for x in stats_1 if x.lower() in df.columns]

            event_types = ["BLOCK", "FAC", "HIT", "PENL", "DELPEN"]

            base_df = df.filter(~pl.col(player).is_in(["BENCH", "REFEREE"]))

            opps = (
                base_df.filter(
                    ~pl.col("description").str.contains("BLOCKED BY TEAMMATE"), pl.col("event").is_in(event_types)
                )
                .group_by(opp_group_list)
                .agg(agg_stats_1)
            )

            new_cols_1 = {
                "opp_goalie": "own_goalie",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
                "own_goalie": "opp_goalie",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                "pen0": "ipend0",
                "pen2": "ipend2",
                "pen4": "ipend4",
                "pen5": "ipend5",
                "pen10": "ipend10",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "fac": "ifol",
                "hit": "iht",
                "ozf": "iozfl",
                "nzf": "inzfl",
                "dzf": "idzfl",
                "block": "isb",
                "block_adj": "isb_adj",
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

            rename_cols = {column: new_cols_1[column] for column in new_cols_1 if column in opps.columns}

            opps = opps.rename(rename_cols)

            # Getting primary assists and primary assists xG from player 2

            stats_2 = ["goal", "pred_goal", "teammate_block", "teammate_block_adj"]

            agg_stats_2 = [pl.sum(x) for x in stats_2 if x in df.columns]

            event_types = ["BLOCK", "GOAL"]

            own = base_df.filter(pl.col("event").is_in(event_types)).group_by(event_group_list).agg(agg_stats_2)

            new_cols_2 = {
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                "goal": "a1",
                "pred_goal": "a1_xg",
                position: "position",
                "teammate_block": "isb",
                "teammate_block_adj": "isb_adj",
            }

            rename_cols = {column: new_cols_2[column] for column in new_cols_2 if column in own.columns}

            own = own.rename(rename_cols)

            player_df = opps.join(own, on=merge_list, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

        if player == "player_3":
            group_list = [
                c
                for c in build_group_list(
                    group_base, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
                )
                if c in df.columns
            ]

            stats_list = ["goal", "pred_goal"]

            agg_stats = [pl.sum(x) for x in stats_list if x in df.columns]

            player_df = df.filter(~pl.col(player).is_in(["BENCH", "REFEREE"])).group_by(group_list).agg(agg_stats)

            new_cols = {
                "goal": "a2",
                "pred_goal": "a2_xg",
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
            }

            rename_cols = {column: new_cols[column] for column in new_cols if column in player_df.columns}

            player_df = player_df.rename(rename_cols)

        ind_stats = ind_stats.join(player_df, on=merge_list, how="full", coalesce=True, nulls_equal=True)

    # Fixing some stats

    null_columns = (pl.col(x).fill_null(0) for x in ind_stats.columns if x not in merge_list)

    ind_stats = ind_stats.with_columns(null_columns)

    ind_stats = ind_stats.with_columns(
        isb=pl.col("isb") + pl.col("isb_right"),
        isb_adj=pl.col("isb_adj") + pl.col("isb_adj_right"),
        icf=pl.col("iff") + pl.col("isb") + pl.col("isb_right"),
        icf_adj=pl.col("iff_adj") + pl.col("isb_adj") + pl.col("isb_adj_right"),
    )
    if "ixg" in ind_stats.columns:
        ind_stats = ind_stats.with_columns(gax=pl.col("g") - pl.col("ixg"))

    stats = [
        "g",
        "a1",
        "a2",
        "isf",
        "iff",
        "icf",
        "ixg",
        "gax",
        "ihdg",
        "ihdf",
        "ihdsf",
        "ihdm",
        "imsf",
        "isb",
        "ibs",
        "igive",
        "itake",
        "ihf",
        "iht",
        "ifow",
        "ifol",
        "iozfw",
        "iozfl",
        "inzfw",
        "inzfl",
        "idzfw",
        "idzfl",
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
    ]

    stats = [x for x in stats if x in ind_stats.columns]

    ind_stats = ind_stats.remove(pl.all_horizontal(pl.col(stats) == 0))

    ind_stats = validate_dataframe(ind_stats, ind_stats_pandera_polars)

    return ind_stats


def build_play_by_play_ext(df: pl.DataFrame) -> pl.DataFrame:
    """Build the extended on-ice slot DataFrame from PBP list columns.

    Expands list-typed lineup columns (teammates_*, opp_team_on_*, change_on_*
    and their *_eh_id, *_api_id, *_positions variants) into per-slot columns
    event_on_1..7, opp_on_1..7, change_on_1..7 (each with _eh_id, _api_id, _pos).
    Returns a DataFrame keyed on id + event_idx for joining into prep_oi.

    Accepts either List[String] columns (produced directly by the scraper) or
    String columns (comma-space delimited, produced when the PBP is round-tripped
    through parquet by an external scoring workflow).

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame with on-ice lineup columns.
    """
    source_groups = [
        ("teammates", "teammates_eh_id", "teammates_api_id", "teammates_positions", "event_on"),
        ("opp_team_on", "opp_team_on_eh_id", "opp_team_on_api_id", "opp_team_on_positions", "opp_on"),
        ("change_on", "change_on_eh_id", "change_on_api_id", "change_on_positions", "change_on"),
    ]

    # Normalize any String lineup columns (parquet round-trip) back to List[String].
    str_lineup_cols = [c for group in source_groups for c in group[:4] if c in df.columns and df.schema[c] == pl.String]
    if str_lineup_cols:
        df = df.with_columns([pl.col(c).str.split(", ") for c in str_lineup_cols])

    exprs: list[pl.Expr] = []
    for src, src_eh, src_api, src_pos, prefix in source_groups:
        if src not in df.columns:
            continue
        for i in range(1, 8):
            idx = i - 1
            exprs += [
                pl.col(src).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}"),
                pl.col(src_eh).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}_eh_id"),
                pl.col(src_api).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}_api_id"),
                pl.col(src_pos).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}_pos"),
            ]
    return df.select(["id", "event_idx", *exprs])


def prep_oi(
    df: pl.DataFrame,
    df_ext: pl.DataFrame | None = None,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Aggregate on-ice stats per player from play-by-play data.

    Called internally by ``_ScraperStatsMixin._prep_oi``. Joins ``df`` with
    ``df_ext`` (on-ice lineup data), then builds "for" and "against" perspectives
    separately across 21 player slots (event_on_1–7, opp_on_1–7, change_on_1–7)
    before merging into a single row per player. Output columns are documented
    in ``Scraper.oi_stats``.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).
        df_ext (pl.DataFrame | None): Extended play-by-play DataFrame with per-slot lineup columns.
            When ``None``, built automatically from list-typed lineup columns in ``df``.
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    if df_ext is None:
        df_ext = build_play_by_play_ext(df)

    merge_cols = ["id", "event_idx"]

    df = df.join(df_ext, on=merge_cols, how="left", nulls_equal=True)

    df = _cast_api_id_columns(df)

    players = (
        [f"event_on_{x}" for x in range(1, 8)]
        + [f"opp_on_{x}" for x in range(1, 8)]
        + [f"change_on_{x}" for x in range(1, 8)]
    )

    event_list = []
    opp_list = []
    zones_list = []

    for player in players:
        position = f"{player}_pos"
        player_eh_id = f"{player}_eh_id"
        player_api_id = f"{player}_api_id"

        group_list = ["season", "session"]

        if level == "game":
            group_list.extend(["game_id", "game_date", "event_team", "opp_team"])

        if level == "period":
            group_list.extend(["game_id", "game_date", "event_team", "opp_team", "period"])

        # Accounting for desired player

        if "event_on" in player or "opp_on" in player:
            stats_list = [
                "block",
                "block_adj",
                "teammate_block",
                "teammate_block_adj",
                "fac",
                "goal",
                "goal_adj",
                "hd_fenwick",
                "hd_goal",
                "hd_miss",
                "hd_shot",
                "hit",
                "miss",
                "miss_adj",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "shot",
                "shot_adj",
                "fenwick",
                "fenwick_adj",
                "pred_goal",
                "pred_goal_adj",
                "base_xg",
                "base_xg_adj",
                "context_xg",
                "give",
                "take",
                "ozf",
                "nzf",
                "dzf",
                "event_length",
            ]

        if "change_on" in player:
            stats_list = ["ozc", "nzc", "dzc", "otf"]

        agg_stats = [pl.sum(x) for x in stats_list if x in df.columns]

        if "event_on" in player or "change_on" in player:
            if level == "session" or level == "season":
                group_list.append("event_team")

            col_names = {
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "goal": "gf",
                "goal_adj": "gf_adj",
                "hit": "hf",
                "miss": "msf",
                "miss_adj": "msf_adj",
                "block": "bsa",
                "block_adj": "bsa_adj",
                "teammate_block": "bsf",
                "teammate_block_adj": "bsf_adj",
                "pen0": "pent0",
                "pen2": "pent2",
                "pen4": "pent4",
                "pen5": "pent5",
                "pen10": "pent10",
                "fenwick": "ff",
                "fenwick_adj": "ff_adj",
                "pred_goal": "xgf",
                "pred_goal_adj": "xgf_adj",
                "base_xg": "base_xgf",
                "base_xg_adj": "base_xgf_adj",
                "context_xg": "context_xgf",
                "fac": "fow",
                "ozf": "ozfw",
                "dzf": "dzfw",
                "nzf": "nzfw",
                "ozc": "ozs",
                "nzc": "nzs",
                "dzc": "dzs",
                "otf": "otf",
                "shot": "sf",
                "shot_adj": "sf_adj",
                "hd_goal": "hdgf",
                "hd_shot": "hdsf",
                "hd_fenwick": "hdff",
                "hd_miss": "hdmsf",
                "give": "give",
                "take": "take",
            }

        if "opp_on" in player:
            if level == "session" or level == "season":
                group_list.append("opp_team")

            col_names = {
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_goalie": "own_goalie",
                "own_goalie": "opp_goalie",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "block": "bsf",
                "block_adj": "bsf_adj",
                "goal": "ga",
                "goal_adj": "ga_adj",
                "hit": "ht",
                "miss": "msa",
                "miss_adj": "msa_adj",
                "pen0": "pend0",
                "pen2": "pend2",
                "pen4": "pend4",
                "pen5": "pend5",
                "pen10": "pend10",
                "shot": "sa",
                "shot_adj": "sa_adj",
                "fenwick": "fa",
                "fenwick_adj": "fa_adj",
                "pred_goal": "xga",
                "pred_goal_adj": "xga_adj",
                "base_xg": "base_xga",
                "base_xg_adj": "base_xga_adj",
                "context_xg": "context_xga",
                "fac": "fol",
                "ozf": "dzfl",
                "dzf": "ozfl",
                "nzf": "nzfl",
                "hd_goal": "hdga",
                "hd_shot": "hdsa",
                "hd_fenwick": "hdfa",
                "hd_miss": "hdmsa",
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "forwards_api_id": "opp_forwards_api_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "defense_api_id": "opp_defense_api_id",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_forwards_api_id": "forwards_api_id",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_defense_api_id": "defense_api_id",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
            }

        if "event_on" in player or "change_on" in player:
            group_list = [
                c
                for c in build_group_list(
                    group_list + [player, player_eh_id, player_api_id, position],
                    strength_state=strength_state,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                )
                if c in df.columns
            ]
        elif "opp_on" in player:
            group_list = [
                c
                for c in build_group_list(
                    group_list + [player, player_eh_id, player_api_id, position],
                    opp_strength_state=strength_state,
                    opp_score=score,
                    teammates=teammates,
                    opposition=opposition,
                    teammates_cols=OPPOSITION_COLS,
                    opposition_cols=TEAMMATES_COLS,
                )
                if c in df.columns
            ]

        player_df = df.group_by(group_list).agg(agg_stats)

        col_names = {key: value for key, value in col_names.items() if key in player_df.columns}

        player_df = player_df.rename(col_names).drop_nulls(subset=["player", "eh_id", "api_id"])

        if "event_on" in player:
            event_list.append(player_df)

        elif "opp_on" in player:
            opp_list.append(player_df)

        elif "change_on" in player:
            zones_list.append(player_df)

    # On-ice stats

    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "player",
        "eh_id",
        "api_id",
        "position",
        "period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
    ]

    event_stats = pl.concat(event_list)

    agg_stats = [pl.sum(x) for x in event_stats.columns if x not in merge_cols]

    group_list = [x for x in merge_cols if x in event_stats.columns]

    event_stats = event_stats.group_by(group_list).agg(agg_stats).with_columns(event_df=pl.lit(1))

    opp_stats = pl.concat(opp_list)

    agg_stats = [pl.sum(x) for x in opp_stats.columns if x not in merge_cols]

    group_list = [x for x in merge_cols if x in opp_stats.columns]

    opp_stats = opp_stats.group_by(group_list).agg(agg_stats).with_columns(opp_df=pl.lit(1))

    zones_stats = pl.concat(zones_list)

    agg_stats = [pl.sum(x) for x in zones_stats.columns if x not in merge_cols]

    group_list = [x for x in merge_cols if x in zones_stats.columns]

    zones_stats = zones_stats.group_by(group_list).agg(agg_stats).with_columns(zones_df=pl.lit(1))

    merge_cols = [
        x for x in merge_cols if x in event_stats.columns and x in opp_stats.columns and x in zones_stats.columns
    ]

    oi_stats = event_stats.join(opp_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

    oi_stats = oi_stats.join(zones_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

    null_columns = (pl.col(x).fill_null(0) for x in oi_stats.columns if x not in merge_cols)

    oi_stats = oi_stats.with_columns(null_columns)

    oi_stats = oi_stats.with_columns(
        api_id=pl.col("api_id").cast(Int64),
        toi=(pl.col("event_length") + pl.col("event_length_right")) / 60,
        bsf=pl.col("bsf") + pl.col("bsf_right"),
        bsf_adj=pl.col("bsf_adj") + pl.col("bsf_adj_right"),
        cf=pl.col("ff") + pl.col("bsf"),
        cf_adj=pl.col("ff_adj") + pl.col("bsf_adj") + pl.col("bsf_adj_right"),
        ca=pl.col("fa") + pl.col("bsa") + pl.col("teammate_block"),
        ca_adj=pl.col("fa_adj") + pl.col("bsa_adj") + pl.col("teammate_block_adj"),
        ozf=pl.col("ozfw") + pl.col("ozfl"),
        nzf=pl.col("nzfw") + pl.col("nzfl"),
        dzf=pl.col("dzfw") + pl.col("dzfl"),
        fac=(pl.col("ozfw") + pl.col("ozfl") + pl.col("nzfw") + pl.col("nzfl") + pl.col("dzfw") + pl.col("dzfl")),
    )

    columns = [x for x in list(oi_stats_pandera_polars.dtypes.keys()) if x in oi_stats.columns] + [
        "event_df",
        "opp_df",
        "zones_df",
    ]

    oi_stats = oi_stats.select(columns)

    stats = [
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "sf",
        "sf_adj",
        "hdsf",
        "ff",
        "ff_adj",
        "hdff",
        "cf",
        "cf_adj",
        "xgf",
        "xgf_adj",
        "bsf",
        "msf",
        "hdmsf",
        "ga",
        "ga_adj",
        "hdga",
        "sa",
        "sa_adj",
        "hdsa",
        "fa",
        "fa_adj",
        "hdfa",
        "ca",
        "ca_adj",
        "xga",
        "xga_adj",
        "bsa",
        "msa",
        "hdmsa",
        "hf",
        "ht",
        "ozf",
        "nzf",
        "dzf",
        "fow",
        "fol",
        "ozfw",
        "ozfl",
        "nzfw",
        "nzfl",
        "dzfw",
        "dzfl",
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
        "give",
        "take",
    ]

    stats = [x.lower() for x in stats if x.lower() in oi_stats.columns]

    oi_stats = oi_stats.remove(pl.all_horizontal(pl.col(stats) == 0))

    oi_stats = validate_dataframe(oi_stats, oi_stats_pandera_polars)

    return oi_stats


def _merge_stats(ind_stats_df: pl.DataFrame, oi_stats_df: pl.DataFrame) -> pl.DataFrame:
    """Merge individual and on-ice stats into a combined per-player DataFrame.

    Called internally by ``_ScraperStatsMixin._prep_stats`` and ``prep_stats``.
    Joins ``ind_stats_df`` and ``oi_stats_df`` on shared groupby keys, then
    appends per-60 and percentage columns.

    Parameters:
        ind_stats_df (pl.DataFrame): Output of ``prep_ind()``.
        oi_stats_df (pl.DataFrame): Output of ``prep_oi()``.
    """
    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "eh_id",
        "api_id",
        "position",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "period",
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

    merge_cols = [x for x in merge_cols if x in ind_stats_df.columns and x in oi_stats_df.columns]

    oi_stats_df = oi_stats_df.filter(pl.col("toi") > 0)

    stats = oi_stats_df.join(ind_stats_df, how="left", on=merge_cols, nulls_equal=True)

    null_columns = (pl.col(x).fill_null(0) for x in stats.columns if x not in merge_cols)

    stats = stats.with_columns(null_columns)

    integer_columns = ["api_id", "own_goalie_api_id", "opp_goalie_api_id"]
    integer_columns = (pl.col(x).cast(pl.Int64) for x in integer_columns if x in stats.columns)

    sort_stuff = {
        "season": False,
        "session": True,
        "game_id": False,
        "team": False,
        "player": False,
        "strength_state": True,
        "period": False,
        "score_state": False,
        "toi": True,
        "own_goalie": False,
        "forwards": False,
    }

    sort_list = [x for x in sort_stuff.keys() if x in stats.columns]
    descending_list = [v for k, v in sort_stuff.items() if k in stats.columns]

    stats = stats.with_columns(integer_columns).sort(by=sort_list, descending=descending_list)

    stats = prep_p60(stats)
    stats = prep_oi_percent(stats)

    stats = validate_dataframe(cast(pl.DataFrame, stats), stats_pandera_polars)

    return stats


def prep_stats(
    df: pl.DataFrame,
    df_ext: pl.DataFrame | None = None,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Aggregate individual and on-ice player stats from a play-by-play DataFrame.

    Public entry point that calls ``prep_ind`` + ``prep_oi`` then merges the results.
    When ``base_xg``, ``pred_goal``, and/or ``context_xg`` columns are present in ``df``,
    ``base_ixg``/``base_xgf``/``base_xga``, ``ixg``/``xgf``/``xga``, and
    ``context_ixg``/``context_xgf``/``context_xga`` are computed respectively.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).
        df_ext (pl.DataFrame | None): Extended on-ice slot DataFrame. Built automatically
            from list-typed lineup columns when ``None``.
        level (str): Aggregation level. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    ind = prep_ind(
        df, level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
    )
    oi = prep_oi(
        df,
        df_ext=df_ext,
        level=level,
        strength_state=strength_state,
        score=score,
        teammates=teammates,
        opposition=opposition,
    )
    return _merge_stats(ind_stats_df=ind, oi_stats_df=oi)


def prep_lines(
    df: pl.DataFrame,
    df_ext: pl.DataFrame | None = None,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Aggregate line-level on-ice stats from play-by-play data.

    Called internally by ``_ScraperStatsMixin._prep_lines``. Aggregates by forward
    or defense line groupings and appends per-60 and percentage columns.
    Output columns are documented in ``Scraper.lines``.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).
        df_ext (pl.DataFrame | None): Extended play-by-play DataFrame. Built automatically
            from list-typed lineup columns when ``None``.
        position (str): ``'f'`` for forward lines, ``'d'`` for defense pairs. Default ``'f'``.
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    if df_ext is None:
        df_ext = build_play_by_play_ext(df)

    merge_cols = ["id", "event_idx"]

    data = df.join(df_ext, how="left", on=merge_cols, nulls_equal=True)

    # Creating the "for" dataframe

    position_cols = (
        ["forwards", "forwards_eh_id", "forwards_api_id"]
        if position == "f"
        else ["defense", "defense_eh_id", "defense_api_id"]
    )
    teammate_cols = (
        ["defense", "defense_eh_id", "defense_api_id", "own_goalie", "own_goalie_eh_id", "own_goalie_api_id"]
        if position == "f"
        else ["forwards", "forwards_eh_id", "forwards_api_id", "own_goalie", "own_goalie_eh_id", "own_goalie_api_id"]
    )

    group_list = build_group_list(
        ["season", "session", "event_team"], level=level, strength_state=strength_state, score=score
    )
    group_list = group_list + position_cols
    if teammates:
        group_list = group_list + teammate_cols
    if opposition:
        group_list = group_list + [
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
        if "opp_team" not in group_list:
            group_list.append("opp_team")

    # Creating dictionary of statistics for the groupby function

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "base_xg",
        "base_xg_adj",
        "context_xg",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
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

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    # Aggregating the "for" dataframe

    lines_f = data.group_by(group_list).agg(agg_stats)

    # Creating the dictionary to change column names

    columns = [
        "xgf",
        "xgf_adj",
        "base_xgf",
        "base_xgf_adj",
        "context_xgf",
        "ff",
        "ff_adj",
        "gf",
        "gf_adj",
        "msf",
        "msf_adj",
        "bsf",
        "bsf_adj",
        "teammate_block",
        "teammate_block_adj",
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

    columns = dict(zip(stats, columns, strict=False))

    # Accounting for positions

    columns.update({"event_team": "team"})

    columns = {k: v for k, v in columns.items() if k in lines_f.columns}

    lines_f = lines_f.rename(columns)

    cols = [
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    cols = [pl.col(x).fill_null("") for x in cols if x in lines_f]

    lines_f = lines_f.with_columns(cols)

    # Creating the against dataframe

    opp_position_cols = (
        ["opp_forwards", "opp_forwards_eh_id", "opp_forwards_api_id"]
        if position == "f"
        else ["opp_defense", "opp_defense_eh_id", "opp_defense_api_id"]
    )
    opp_teammate_cols = (
        [
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]
        if position == "f"
        else [
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]
    )

    group_list = ["season", "session", "opp_team"]
    if level == "game":
        group_list.extend(["game_id", "game_date", "event_team"])
    elif level == "period":
        group_list.extend(["game_id", "game_date", "event_team", "period"])
    if strength_state:
        group_list.append("opp_strength_state")
    if score:
        group_list.append("opp_score_state")
    group_list = group_list + opp_position_cols
    if teammates:
        group_list = group_list + opp_teammate_cols
    if opposition:
        group_list = group_list + [
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
        if "event_team" not in group_list:
            group_list.append("event_team")

    # Creating dictionary of statistics for the groupby function

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "base_xg",
        "base_xg_adj",
        "context_xg",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
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

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    # Aggregating "against" dataframe

    lines_a = data.group_by(group_list).agg(agg_stats)

    # Creating the dictionary to change column names

    columns = [
        "xga",
        "xga_adj",
        "base_xga",
        "base_xga_adj",
        "context_xga",
        "fa",
        "fa_adj",
        "ga",
        "ga_adj",
        "msa",
        "msa_adj",
        "bsa",
        "bsa_adj",
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

    columns = dict(zip(stats, columns, strict=False))

    # Accounting for positions

    columns.update(
        {
            "opp_team": "team",
            "event_team": "opp_team",
            "opp_forwards": "forwards",
            "opp_forwards_eh_id": "forwards_eh_id",
            "opp_forwards_api_id": "forwards_api_id",
            "opp_strength_state": "strength_state",
            "opp_defense": "defense",
            "opp_defense_eh_id": "defense_eh_id",
            "opp_defense_api_id": "defense_api_id",
            "forwards": "opp_forwards",
            "forwards_eh_id": "opp_forwards_eh_id",
            "forwards_api_id": "opp_forwards_api_id",
            "defense": "opp_defense",
            "defense_eh_id": "opp_defense_eh_id",
            "defense_api_id": "opp_defense_api_id",
            "opp_score_state": "score_state",
            "own_goalie": "opp_goalie",
            "own_goalie_eh_id": "opp_goalie_eh_id",
            "own_goalie_api_id": "opp_goalie_api_id",
            "opp_goalie": "own_goalie",
            "opp_goalie_eh_id": "own_goalie_eh_id",
            "opp_goalie_api_id": "own_goalie_api_id",
        }
    )

    columns = {k: v for k, v in columns.items() if k in lines_a.columns}

    lines_a = lines_a.rename(columns)

    cols = [
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    cols = [pl.col(x).fill_null("") for x in cols if x in lines_a]

    lines_a = lines_a.with_columns(cols)

    # Merging the "for" and "against" dataframes

    if level == "session" or level == "season":
        if position == "f":
            merge_list = ["season", "session", "team", "forwards", "forwards_eh_id", "forwards_api_id"]

        if position == "d":
            merge_list = ["season", "session", "team", "defense", "defense_eh_id", "defense_api_id"]

    if level == "game":
        if position == "f":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
            ]

        if position == "d":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "defense",
                "defense_eh_id",
                "defense_api_id",
            ]

    if level == "period":
        if position == "f":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "period",
            ]

        if position == "d":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "period",
            ]

    if strength_state:
        merge_list.append("strength_state")

    if score:
        merge_list.append("score_state")

    if teammates:
        if position == "f":
            merge_list = merge_list + [
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

        if position == "d":
            merge_list = merge_list + [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

    if opposition:
        merge_list = merge_list + [
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

        if "opp_team" not in merge_list:
            merge_list.insert(3, "opp_team")

    lines = lines_f.join(lines_a, how="full", on=merge_list, coalesce=True, nulls_equal=True)

    null_columns = (pl.col(x).fill_null(0) for x in lines.columns if x not in merge_list)

    lines = lines.with_columns(null_columns)

    lines = lines.with_columns(
        toi=(lines["toi"] + lines["toi_right"]) / 60,
        cf=lines["bsf"] + lines["teammate_block"] + lines["ff"],
        cf_adj=lines["bsf_adj"] + lines["teammate_block_adj"] + lines["ff_adj"],
        ca=lines["bsa"] + lines["fa"],
        ca_adj=lines["bsa_adj"] + lines["fa_adj"],
        ozf=lines["ozfw"] + lines["ozfl"],
        nzf=lines["nzfw"] + lines["nzfl"],
        dzf=lines["dzfw"] + lines["dzfl"],
    )

    lines = lines.filter(pl.col("toi") > 0)

    lines = prep_p60(lines)

    lines = prep_oi_percent(lines)

    lines = validate_dataframe(cast(pl.DataFrame, lines), line_stats_pandera_polars)

    return lines


def prep_team_stats(
    df: pl.DataFrame,
    df_ext: pl.DataFrame | None = None,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    opposition: bool = False,
    score: bool = False,
) -> pl.DataFrame:
    """Aggregate team-level on-ice stats from play-by-play data.

    Called internally by ``_ScraperStatsMixin._prep_team_stats``. Builds "for"
    and "against" perspectives per team, then merges and appends per-60 and
    percentage columns. Output columns are documented in ``Scraper.team_stats``.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).
        df_ext (pl.DataFrame | None): Extended play-by-play DataFrame. Built automatically
            from list-typed lineup columns when ``None``.
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        opposition (bool): Split by opposing lineup. Default ``False``.
        score (bool): Split by score state. Default ``False``.
    """
    if df_ext is None:
        df_ext = build_play_by_play_ext(df)

    merge_cols = ["id", "event_idx"]

    data = df.join(df_ext, how="left", on=merge_cols, nulls_equal=True)

    # Getting the "for" stats

    group_list = ["season", "session", "event_team"]

    if strength_state:
        group_list.append("strength_state")

    if level == "game" or level == "period" or opposition:
        group_list.insert(3, "opp_team")

        group_list[2:2] = ["game_id", "game_date"]

    if level == "period":
        group_list.append("period")

    if score:
        group_list.append("score_state")

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "base_xg",
        "base_xg_adj",
        "context_xg",
        "shot",
        "shot_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
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

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    stats_for = data.group_by(group_list).agg(agg_stats)

    new_cols = [
        "xgf",
        "xgf_adj",
        "base_xgf",
        "base_xgf_adj",
        "context_xgf",
        "sf",
        "sf_adj",
        "msf",
        "msf_adj",
        "bsa",
        "bsa_adj",
        "teammate_block",
        "teammate_block_adj",
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

    new_cols = dict(zip(stats, new_cols, strict=False))

    new_cols.update({"event_team": "team"})

    new_cols = {k: v for k, v in new_cols.items() if k in stats_for.columns}
    stats_for = stats_for.rename(new_cols)

    # Getting the "against" stats

    group_list = ["season", "session", "opp_team"]

    if strength_state:
        group_list.append("opp_strength_state")

    if level == "game" or level == "period":
        group_list.insert(3, "event_team")

        group_list[2:2] = ["game_id", "game_date"]

    if level == "period":
        group_list.append("period")

    if score:
        group_list.append("opp_score_state")

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "base_xg",
        "base_xg_adj",
        "context_xg",
        "shot",
        "shot_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
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

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    stats_against = data.group_by(group_list).agg(agg_stats)

    new_cols = [
        "xga",
        "xga_adj",
        "base_xga",
        "base_xga_adj",
        "context_xga",
        "sa",
        "sa_adj",
        "msa",
        "msa_adj",
        "bsf",
        "bsf_adj",
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

    new_cols = dict(zip(stats, new_cols, strict=False))

    new_cols.update(
        {
            "opp_team": "team",
            "opp_score_state": "score_state",
            "opp_strength_state": "strength_state",
            "event_team": "opp_team",
        }
    )

    new_cols = {k: v for k, v in new_cols.items() if k in stats_against.columns}

    stats_against = stats_against.rename(new_cols)

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

    merge_list = [x for x in merge_list if x in stats_for.columns and x in stats_against.columns]

    team_stats = stats_for.join(stats_against, on=merge_list, how="full", nulls_equal=True, coalesce=True)

    team_stats = team_stats.with_columns(
        toi=(team_stats["toi"].fill_null(0) + team_stats["toi_right"].fill_null(0)) / 60,
        cf=team_stats["ff"] + team_stats["bsf"] + team_stats["teammate_block"],
        cf_adj=team_stats["ff_adj"] + team_stats["bsf_adj"] + team_stats["teammate_block_adj"],
        ca=team_stats["fa"] + team_stats["bsa"],
        ca_adj=team_stats["fa_adj"] + team_stats["bsa_adj"],
        ozf=team_stats["ozfw"] + team_stats["ozfl"],
        nzf=team_stats["nzfw"] + team_stats["nzfl"],
        dzf=team_stats["dzfw"] + team_stats["dzfl"],
    ).filter(pl.col("toi") > 0, pl.col("toi").is_not_null())

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    team_stats = validate_dataframe(cast(pl.DataFrame, team_stats), team_stats_pandera_polars)

    return team_stats
