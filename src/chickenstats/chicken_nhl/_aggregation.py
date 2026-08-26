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
    OPPONENT_SWAP_COLS,
    STINT_XG_COLS,
    STINT_LINEUP_COLS,
    STINT_REQUIRED_COLS,
    STINT_COLUMN_ORDER,
    STINT_COUNT_COLS,
)
from chickenstats.chicken_nhl.validation_polars import (
    ind_stats_pandera_polars,
    oi_stats_pandera_polars,
    stats_pandera_polars,
    line_stats_pandera_polars,
    team_stats_pandera_polars,
)
from chickenstats.chicken_nhl._validation_utils import validate_dataframe
from chickenstats.exceptions import InvalidInputError


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
    initial aggregation step.

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
            Stats dataframe from chickenstats.chicken_nhl.Scraper
    """
    exprs = []

    for stat_for, stat_against in zip(stats_for, stats_against, strict=False):
        if stat_for not in df.columns:
            exprs.append(nw.lit(0.0).alias(f"{stat_for}_percent"))

        elif stat_against not in df.columns:
            exprs.append(nw.lit(1.0).alias(f"{stat_for}_percent"))

        else:
            exprs.append(
                (nw.col(stat_for) / (nw.col(stat_for) + nw.col(stat_against)))
                .fill_nan(0.0)
                .alias(f"{stat_for}_percent")
            )

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
        ensure_team=opposition,
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

        if player == "player_1":
            group_list = [
                c
                for c in build_group_list(
                    group_base,
                    level=level,
                    strength_state=strength_state,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                    ensure_team=opposition,
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

            event_group_list = build_group_list(
                group_base,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
                ensure_team=opposition,
            )

            opp_group_list = build_group_list(
                ["season", "session", "opp_team", player, player_eh_id, player_api_id, position],
                level=level,
                opp_strength_state=strength_state,
                opp_score=score,
                teammates=teammates,
                opposition=opposition,
                teammates_cols=OPPOSITION_COLS,
                opposition_cols=TEAMMATES_COLS,
                opp_perspective=True,
                ensure_team=opposition,
            )

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
                **OPPONENT_SWAP_COLS,
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
                    group_base,
                    level=level,
                    strength_state=strength_state,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                    ensure_team=opposition,
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

        # suffix="_right" explicit — isb/isb_adj below reference those columns.
        ind_stats = ind_stats.join(
            player_df, on=merge_list, how="full", coalesce=True, nulls_equal=True, suffix="_right"
        )

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


def _normalize_lineup_cols(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Normalize String lineup columns (parquet round-trip) back to List[String].

    Columns missing from ``df``, and columns already List-typed, are left alone.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame.
        cols (list[str]): Candidate lineup column names to normalize.
    """
    str_cols = [c for c in cols if c in df.columns and df.schema[c] == pl.String]
    if str_cols:
        df = df.with_columns([pl.col(c).str.split(", ") for c in str_cols])
    return df


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
    player_groups = [
        ("teammates", "teammates_eh_id", "teammates_api_id", "teammates_positions", "event_on"),
        ("opp_team_on", "opp_team_on_eh_id", "opp_team_on_api_id", "opp_team_on_positions", "opp_on"),
        ("change_on", "change_on_eh_id", "change_on_api_id", "change_on_positions", "change_on"),
    ]

    df = _normalize_lineup_cols(df, [c for group in player_groups for c in group[:4]])

    exprs: list[pl.Expr] = []
    for player, player_eh_id, player_api_id, player_pos, prefix in player_groups:
        if player not in df.columns:
            continue
        for i in range(1, 8):
            idx = i - 1
            exprs += [
                pl.col(player).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}"),
                pl.col(player_eh_id).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}_eh_id"),
                pl.col(player_api_id).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}_api_id"),
                pl.col(player_pos).list.get(idx, null_on_oob=True).alias(f"{prefix}_{i}_pos"),
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

        elif "change_on" in player:
            stats_list = ["ozc", "nzc", "dzc", "otf"]

        else:
            raise ValueError(f"Unrecognized player slot column: {player!r}")

        stats_cols = [x for x in stats_list if x in df.columns]

        if "event_on" in player or "change_on" in player:
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

        elif "opp_on" in player:
            col_names = {
                **OPPONENT_SWAP_COLS,
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
            }

        else:
            raise ValueError(f"Unrecognized player slot column: {player!r}")

        if "event_on" in player or "change_on" in player:
            group_list = [
                c
                for c in build_group_list(
                    ["season", "session", "event_team", player, player_eh_id, player_api_id, position],
                    level=level,
                    strength_state=strength_state,
                    score=score,
                    teammates=teammates,
                    opposition=opposition,
                    ensure_team=opposition,
                )
                if c in df.columns
            ]
        elif "opp_on" in player:
            group_list = [
                c
                for c in build_group_list(
                    ["season", "session", "opp_team", player, player_eh_id, player_api_id, position],
                    level=level,
                    opp_strength_state=strength_state,
                    opp_score=score,
                    teammates=teammates,
                    opposition=opposition,
                    teammates_cols=OPPOSITION_COLS,
                    opposition_cols=TEAMMATES_COLS,
                    opp_perspective=True,
                    ensure_team=opposition,
                )
                if c in df.columns
            ]
        else:
            raise ValueError(f"Unrecognized player slot column: {player!r}")

        # Aggregation is deferred to the single group_by below, after all slots are concatenated.
        select_cols = list(dict.fromkeys([*group_list, *stats_cols]))
        player_df = df.select(select_cols)

        col_names = {key: value for key, value in col_names.items() if key in player_df.columns}

        player_df = player_df.rename(col_names).drop_nulls(subset=["player", "eh_id", "api_id"])

        if "event_on" in player:
            event_list.append(player_df)

        elif "opp_on" in player:
            opp_list.append(player_df)

        elif "change_on" in player:
            zones_list.append(player_df)

        else:
            raise ValueError(f"Unrecognized player slot column: {player!r}")

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

    # suffix="_right" explicit — toi/bsf/bsf_adj/cf_adj below reference those columns.
    oi_stats = event_stats.join(
        opp_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True, suffix="_right"
    )  # .fill_null(0)

    oi_stats = oi_stats.join(zones_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

    null_columns = (pl.col(x).fill_null(0) for x in oi_stats.columns if x not in merge_cols)

    oi_stats = oi_stats.with_columns(null_columns)

    oi_stats = oi_stats.with_columns(
        api_id=pl.col("api_id").cast(Int64),
        toi=(pl.col("event_length") + pl.col("event_length_right")) / 60,
        bsf=pl.col("bsf") + pl.col("bsf_right"),
        bsf_adj=pl.col("bsf_adj") + pl.col("bsf_adj_right"),
        # bsf_right spelled out: with_columns reads the pre-sum bsf, not the line above.
        cf=pl.col("ff") + pl.col("bsf") + pl.col("bsf_right"),
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
        ["season", "session", "event_team"] + position_cols,
        level=level,
        strength_state=strength_state,
        score=score,
        teammates=teammates,
        opposition=opposition,
        teammates_cols=teammate_cols,
        ensure_team=opposition,
    )

    # stats/columns are positionally paired (index-for-index rename); must stay equal
    # length and order — strict=True below catches misalignment instead of truncating.
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
        # A line's own BLOCK events are shots it blocked, so bsa; bsf comes from the
        # "against" frame, where the opponent blocked one of this line's attempts.
        "bsa",
        "bsa_adj",
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

    columns = dict(zip(stats, columns, strict=True))

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

    group_list = build_group_list(
        ["season", "session", "opp_team"] + opp_position_cols,
        level=level,
        opp_strength_state=strength_state,
        opp_score=score,
        teammates=teammates,
        opposition=opposition,
        teammates_cols=opp_teammate_cols,
        opposition_cols=TEAMMATES_COLS,
        opp_perspective=True,
        ensure_team=opposition,
    )

    # Creating dictionary of statistics for the groupby function

    # Mirrors the "for" block above, "a" suffix instead of "f" (xga vs xgf, etc.)
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
        "bsf",
        "bsf_adj",
        # The opponent's own-teammate blocks are Corsi against this line.
        "opp_teammate_block",
        "opp_teammate_block_adj",
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

    columns = dict(zip(stats, columns, strict=True))

    # Accounting for positions

    columns.update(OPPONENT_SWAP_COLS)

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

    # suffix="_right" explicit — toi below references that column.
    lines = lines_f.join(lines_a, how="full", on=merge_list, coalesce=True, nulls_equal=True, suffix="_right")

    null_columns = (pl.col(x).fill_null(0) for x in lines.columns if x not in merge_list)

    lines = lines.with_columns(null_columns)

    lines = lines.with_columns(
        toi=(lines["toi"] + lines["toi_right"]) / 60,
        cf=lines["bsf"] + lines["teammate_block"] + lines["ff"],
        cf_adj=lines["bsf_adj"] + lines["teammate_block_adj"] + lines["ff_adj"],
        # opp_teammate_block keeps ca symmetric with the opponent's cf.
        ca=lines["bsa"] + lines["fa"] + lines["opp_teammate_block"],
        ca_adj=lines["bsa_adj"] + lines["fa_adj"] + lines["opp_teammate_block_adj"],
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

    # "for" stats — group_list built directly in final order
    group_list = ["season", "session"]

    group_list = build_group_list(
        ["season", "session", "event_team"],
        level=level,
        strength_state=strength_state,
        score=score,
        ensure_team=opposition,
    )

    # stats/new_cols positionally paired (index-for-index rename)
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

    new_cols = dict(zip(stats, new_cols, strict=True))

    new_cols.update({"event_team": "team"})

    new_cols = {k: v for k, v in new_cols.items() if k in stats_for.columns}
    stats_for = stats_for.rename(new_cols)

    # Getting the "against" stats

    group_list = build_group_list(
        ["season", "session", "opp_team"],
        level=level,
        opp_strength_state=strength_state,
        opp_score=score,
        opp_perspective=True,
        ensure_team=opposition,
    )

    # stats/new_cols positionally paired (index-for-index rename)
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
        # The opponent's own-teammate blocks are Corsi against this team.
        "opp_teammate_block",
        "opp_teammate_block_adj",
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

    new_cols = dict(zip(stats, new_cols, strict=True))

    new_cols.update(OPPONENT_SWAP_COLS)

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

    # suffix="_right" explicit — toi below references that column.
    team_stats = stats_for.join(
        stats_against, on=merge_list, how="full", nulls_equal=True, coalesce=True, suffix="_right"
    )

    team_stats = team_stats.with_columns(
        toi=(team_stats["toi"].fill_null(0) + team_stats["toi_right"].fill_null(0)) / 60,
        cf=team_stats["ff"] + team_stats["bsf"] + team_stats["teammate_block"],
        cf_adj=team_stats["ff_adj"] + team_stats["bsf_adj"] + team_stats["teammate_block_adj"],
        # opp_teammate_block keeps ca symmetric with the opponent's cf; filled so a team
        # with no "against" rows keeps the existing null behavior on the fa/bsa terms.
        ca=team_stats["fa"] + team_stats["bsa"] + team_stats["opp_teammate_block"].fill_null(0),
        ca_adj=team_stats["fa_adj"] + team_stats["bsa_adj"] + team_stats["opp_teammate_block_adj"].fill_null(0),
        ozf=team_stats["ozfw"] + team_stats["ozfl"],
        nzf=team_stats["nzfw"] + team_stats["nzfl"],
        dzf=team_stats["dzfw"] + team_stats["dzfl"],
    ).filter(pl.col("toi") > 0, pl.col("toi").is_not_null())

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    team_stats = validate_dataframe(cast(pl.DataFrame, team_stats), team_stats_pandera_polars)

    return team_stats


def prep_rolling_stats(
    df: pl.DataFrame,
    window: int = 10,
    stats: list[str] | None = None,
    group_cols: list[str] | None = None,
    min_periods: int = 1,
) -> pl.DataFrame:
    """Add trailing rolling-window averages for rate-stat columns.

    Operates on the output of ``prep_stats`` or ``prep_team_stats`` at ``level='game'``.
    Sorts by game order within each ``group_cols`` group, then computes a trailing
    ``window``-game rolling mean for each stat column, appending ``rolling_{stat}`` columns.

    Parameters:
        df (pl.DataFrame): Game-level stats DataFrame, e.g. from ``prep_stats`` or
            ``prep_team_stats`` with ``level='game'``.
        window (int): Number of trailing games to average over. Default ``10``.
        stats (list[str] | None): Stat columns to compute rolling averages for. Defaults
            to all ``*_p60``/``*_percent`` columns present in ``df``.
        group_cols (list[str] | None): Columns identifying the entity whose games should
            be tracked together, e.g. a player or a team. Defaults to
            ``['player', 'eh_id']`` if both are present, otherwise ``['team']``.
        min_periods (int): Minimum number of games required before a rolling value is
            computed. Default ``1``.

    Note:
        Requires exactly one row per game per group. ``prep_stats``/``prep_team_stats``
        default to splitting by ``strength_state`` (and optionally ``score_state``,
        ``teammates``, ``opposition``), which produce multiple rows per game per player —
        pass ``strength_state=False`` (and leave ``score``/``teammates``/``opposition``
        off) or filter/aggregate down to one row per game per group before calling this
        function. ``level='period'`` output and already-aggregated ``level='session'``/
        ``'season'`` output are rejected outright, since neither has one row per game.

    Returns:
        pl.DataFrame: ``df`` with added ``rolling_{stat}`` columns.

    Raises:
        InvalidInputError: If ``df`` lacks ``game_id``/``game_date`` (not game-level
            output), or if ``group_cols`` plus the game column don't uniquely identify
            rows (multiple rows per game per group, e.g. unfiltered strength/score-state
            splits, or ``level='period'`` output).

    Examples:
        >>> from chickenstats.chicken_nhl import prep_rolling_stats
        >>> game_stats = scraper.prep_stats(level="game", strength_state=False).stats
        >>> rolling = prep_rolling_stats(game_stats, window=10)
    """
    if "game_id" not in df.columns and "game_date" not in df.columns:
        raise InvalidInputError(
            "prep_rolling_stats requires game-level data (df must contain 'game_id' or "
            "'game_date'). Pass output from prep_stats/prep_team_stats with level='game', "
            "not 'session' or 'season' (which are already aggregated across all games).",
            obj=df,
        )

    if group_cols is None:
        group_cols = ["player", "eh_id"] if "player" in df.columns and "eh_id" in df.columns else ["team"]

    if stats is None:
        stats = [c for c in df.columns if c.endswith("_p60") or c.endswith("_percent")]

    game_col = "game_date" if "game_date" in df.columns else "game_id"
    sort_cols = [*group_cols, game_col]

    group_key_cols = [*group_cols, game_col]
    if df.select(group_key_cols).is_duplicated().any():
        raise InvalidInputError(
            "prep_rolling_stats requires exactly one row per game per group, but "
            f"duplicate {group_key_cols} combinations were found in df. This happens "
            "when df has multiple rows per game per group — e.g. unfiltered "
            "strength_state/score_state/teammates/opposition splits, or "
            "level='period' output. Filter down to a single split (e.g. "
            "strength_state='5v5') or aggregate across splits before calling this "
            "function.",
            obj=df,
        )

    df = df.sort(sort_cols)

    rolling_exprs = [
        pl.col(stat).rolling_mean(window_size=window, min_samples=min_periods).over(group_cols).alias(f"rolling_{stat}")
        for stat in stats
        if stat in df.columns
    ]

    if not rolling_exprs:
        return df

    return df.with_columns(rolling_exprs)


def _build_b2b_lookup(df: pl.DataFrame) -> pl.DataFrame:
    """Flag whether each game was a back-to-back for its home and away team.

    Ordered on ``game_date`` rather than ``game_id``: postponed and rescheduled games
    keep their originally-issued ID, so IDs are not reliably chronological.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).

    Returns:
        pl.DataFrame: One row per ``game_id`` with ``home_b2b`` and ``away_b2b``.
    """
    games = df.select(["game_id", "game_date", "home_team", "away_team"]).unique()

    # game_date is a String from the scraper but a Date once round-tripped through parquet.
    if games.schema["game_date"] == pl.String:
        games = games.with_columns(pl.col("game_date").str.to_date())

    team_schedule = (
        pl.concat(
            [
                games.select(["game_id", "game_date", pl.col("home_team").alias("team")]),
                games.select(["game_id", "game_date", pl.col("away_team").alias("team")]),
            ]
        )
        .unique()
        .sort(["team", "game_date"])
    )

    team_schedule = team_schedule.with_columns(
        is_b2b=((pl.col("game_date") - pl.col("game_date").shift(1)).over("team").dt.total_days() == 1).fill_null(False)
    )

    b2b_by_team = team_schedule.select(["game_id", "team", "is_b2b"])

    return (
        games.join(b2b_by_team, left_on=["game_id", "home_team"], right_on=["game_id", "team"], how="left")
        .rename({"is_b2b": "home_b2b"})
        .join(b2b_by_team, left_on=["game_id", "away_team"], right_on=["game_id", "team"], how="left")
        .rename({"is_b2b": "away_b2b"})
        .select(["game_id", "home_b2b", "away_b2b"])
    )


def prep_stints(df: pl.DataFrame, min_skaters: int = 3) -> pl.DataFrame:
    """Aggregate play-by-play data into RAPM stints.

    A stint is a contiguous run of events within one period during which neither team's
    on-ice personnel changed. Output columns are documented in ``Scraper.stints``, and
    feed ``chickenstats.chicken_nhl.rapm.build_rapm_matrix``.

    Stats are keyed on venue, not perspective: a stat's "against" side is the other
    team's "for" (``home_sa`` is ``away_sf``), so one row carries both sides. ``xgf``,
    ``base_xgf``, and ``context_xgf`` are summed for whichever of ``pred_goal``,
    ``base_xg``, and ``context_xg`` are in ``df``; ``delta_xgf`` needs both base and
    context.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame (polars).
        min_skaters (int): Minimum skaters per side for a stint to be kept. Default ``3``.

    Note:
        Back-to-back flags are derived only from the games present in ``df``, so a
        partial slate reports ``False`` for a team whose previous game isn't in the set.

    Note:
        Shootout attempts carry no on-ice lineup, so they're dropped rather than
        attributed to a stint. Totals will fall short of ``prep_team_stats`` by the
        shootout's shots and goals.

    Returns:
        pl.DataFrame: One row per ``season``, ``session``, ``game_id``, ``period``,
        ``stint_id``.

    Raises:
        InvalidInputError: If ``df`` is missing any required play-by-play column.

    Examples:
        >>> from chickenstats.chicken_nhl import Scraper, prep_stints
        >>> scraper = Scraper(list(range(2023020001, 2023020011)))
        >>> stints = prep_stints(scraper.play_by_play)
    """
    missing = [col for col in STINT_REQUIRED_COLS if col not in df.columns]
    if missing:
        raise InvalidInputError(
            f"prep_stints is missing required play-by-play columns: {missing}. Pass the "
            "unaggregated play-by-play DataFrame, e.g. Scraper.play_by_play, not the "
            "output of prep_stats/prep_team_stats.",
            obj=df,
        )

    df = _normalize_lineup_cols(df, STINT_LINEUP_COLS)

    df = df.join(_build_b2b_lookup(df), on="game_id", how="left")

    # 7 buckets for shot-volume metrics, which are sensitive to small leads; 3 for xG/goals.
    df = df.with_columns(
        home_score_7=pl.col("home_score_diff").clip(-3, 3), home_score_3=pl.col("home_score_diff").sign().cast(pl.Int64)
    ).with_columns(away_score_7=-pl.col("home_score_7"), away_score_3=-pl.col("home_score_3"))

    # Sort after the join: a left join isn't order-preserving and the shift(1) below needs
    # true sequence. game_date leads because postponed games keep a non-chronological ID.
    df = df.sort(["game_date", "game_id", "period", "event_idx"])

    # A new stint begins whenever either team's on-ice group changes. Joined string keys
    # rather than List columns keep the comparison dtype-stable.
    home_key = pl.col("home_on_api_id").list.join(",")
    away_key = pl.col("away_on_api_id").list.join(",")
    df = df.with_columns(
        stint_id=(
            ((home_key != home_key.shift(1)) | (away_key != away_key.shift(1)))
            .fill_null(True)
            .cast(pl.Int32)
            .cum_sum()
            .over(["game_id", "period"])
        )
    )

    is_home = (pl.col("event_team") == pl.col("home_team")).cast(pl.Int64)
    is_away = (pl.col("event_team") == pl.col("away_team")).cast(pl.Int64)

    # first() carries the source column name through, so only derived columns need an alias.
    agg_stats = [
        pl.col("game_date").first(),
        pl.col("strength_state").first(),
        pl.col("home_team").first(),
        pl.col("away_team").first(),
        pl.col("home_on_api_id").first(),
        pl.col("away_on_api_id").first(),
        pl.col("home_goalie_api_id").first(),
        pl.col("away_goalie_api_id").first(),
        pl.col("home_score_3").first(),
        pl.col("home_score_7").first(),
        pl.col("away_score_3").first(),
        pl.col("away_score_7").first(),
        pl.col("home_b2b").first(),
        pl.col("away_b2b").first(),
        pl.col("event_length").sum().alias("toi"),
        (pl.col("shot") * is_home).sum().alias("home_sf"),
        (pl.col("shot") * is_away).sum().alias("away_sf"),
        (pl.col("fenwick") * is_home).sum().alias("home_ff"),
        (pl.col("fenwick") * is_away).sum().alias("away_ff"),
        # A BLOCK's event_team is the blocker, so the opposing team's blocks are Corsi for.
        (pl.col("fenwick") * is_home + pl.col("block") * is_away + pl.col("teammate_block") * is_home)
        .sum()
        .alias("home_cf"),
        (pl.col("fenwick") * is_away + pl.col("block") * is_home + pl.col("teammate_block") * is_away)
        .sum()
        .alias("away_cf"),
        (pl.col("goal") * is_home).sum().alias("home_gf"),
        (pl.col("goal") * is_away).sum().alias("away_gf"),
        # zone_start is relative to the changing team, so these mean "either team".
        (pl.col("zone_start") == "OFF").any().alias("ozs"),
        (pl.col("zone_start") == "NEU").any().alias("nzs"),
        (pl.col("zone_start") == "DEF").any().alias("dzs"),
    ]

    agg_stats += [
        (pl.col(source) * mask).sum().alias(f"{venue}_{suffix}")
        for source, suffix in STINT_XG_COLS.items()
        if source in df.columns
        for venue, mask in (("home", is_home), ("away", is_away))
    ]

    stints = df.group_by(["season", "session", "game_id", "period", "stint_id"]).agg(agg_stats)

    # Derived, not summed separately: sums are linear.
    if "home_context_xgf" in stints.columns and "home_base_xgf" in stints.columns:
        stints = stints.with_columns(
            home_delta_xgf=pl.col("home_context_xgf") - pl.col("home_base_xgf"),
            away_delta_xgf=pl.col("away_context_xgf") - pl.col("away_base_xgf"),
        )

    stints = stints.filter(pl.col("toi") > 0)

    # Null lineup columns become empty lists so set_difference and list.len() stay defined.
    stints = (
        stints.with_columns(
            home_goalies=pl.col("home_goalie_api_id").fill_null([]),
            away_goalies=pl.col("away_goalie_api_id").fill_null([]),
        )
        .with_columns(
            home_skaters=pl.col("home_on_api_id").list.set_difference(pl.col("home_goalies")).fill_null([]),
            away_skaters=pl.col("away_on_api_id").list.set_difference(pl.col("away_goalies")).fill_null([]),
        )
        .with_columns(
            home_skater_count=pl.col("home_skaters").list.len().cast(pl.Int64),
            away_skater_count=pl.col("away_skaters").list.len().cast(pl.Int64),
        )
    )

    stints = stints.filter((pl.col("home_skater_count") >= min_skaters) & (pl.col("away_skater_count") >= min_skaters))

    stints = stints.with_columns(
        pl.col("toi").cast(pl.Int64),
        pl.col("stint_id").cast(pl.Int64),
        pl.col([col for col in STINT_COUNT_COLS if col in stints.columns]).cast(pl.Int64),
        pl.col(["home_b2b", "away_b2b", "ozs", "nzs", "dzs"]).cast(pl.Boolean),
    )

    stints = stints.select([col for col in STINT_COLUMN_ORDER if col in stints.columns])

    return stints.sort(["game_date", "game_id", "period", "stint_id"])
