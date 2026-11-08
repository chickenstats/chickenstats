from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, cast

import narwhals as nw

from chickenstats.utilities.enums import AggLevel
from chickenstats.utilities.utilities import COLLECT_ENGINE
import polars as pl

if TYPE_CHECKING:
    import pandas as pd
    import pandera.polars as pa_pl
from narwhals.typing import IntoFrameT
from polars import Int64, String

from chickenstats.chicken_nhl._agg_constants import (
    build_against_group_list,
    build_group_list,
    P60_STATS,
    OI_PERCENT_STATS_FOR,
    OI_PERCENT_STATS_AGAINST,
    ON_ICE_AGAINST,
    ON_ICE_FOR,
    TEAMMATES_COLS,
    OPPOSITION_COLS,
    OPPONENT_SWAP_COLS,
    STINT_XG_COLS,
    STINT_LINEUP_COLS,
    STINT_REQUIRED_COLS,
    IND_REQUIRED_COLS,
    ON_ICE_REQUIRED_COLS,
    STINT_READ_COLS,
    TEAMMATE_BLOCK_PATTERN,
    UNREAD_PBP_COLS,
    EXT_SOURCE_COLS,
    STINT_COLUMN_ORDER,
    STINT_COUNT_COLS,
    ZONE_START_COLS,
)
from chickenstats.chicken_nhl.validation_polars import (
    ind_stats_pandera_polars,
    oi_stats_pandera_polars,
    stats_pandera_polars,
    line_stats_pandera_polars,
    team_stats_pandera_polars,
)
from chickenstats.chicken_nhl._game_utils import OPPOSING_PLAYER_2_EVENTS, prepare_xg
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


def _add_unblocked_corsi_adj(df: pl.DataFrame) -> pl.DataFrame:
    """Adds each unblocked attempt at its Corsi weight, for the corsi_adj sums."""
    if "corsi_adj" not in df.columns:
        return df.with_columns(unblocked_corsi_adj=pl.col("fenwick_adj"))
    return df.with_columns(unblocked_corsi_adj=pl.col("corsi_adj") * pl.col("fenwick"))


@nw.narwhalify
def _prep_p60(df: IntoFrameT, stats: list) -> IntoFrameT:
    """Adds columns to normalize statistics on a 60-minute basis.

    Parameters:
        df (pd.DataFrame | pl.DataFrame):
            Statistics data from chickenstats.chicken_nhl.Scraper
    """
    existing = [s for s in stats if s in df.columns]

    # A rate with no ice time is null, not infinite
    has_toi = nw.col("toi") > 0

    return df.with_columns(  # ty: ignore[unresolved-attribute]
        [nw.when(has_toi).then((nw.col(stat) / nw.col("toi")) * 60).alias(f"{stat}_p60") for stat in existing]
    )


def _require_polars(df: object, func: str, *, lazy: bool = False) -> None:
    """Raises InvalidInputError for anything but a polars DataFrame (or LazyFrame, when lazy is True)."""
    accepted = (pl.DataFrame, pl.LazyFrame) if lazy else pl.DataFrame
    if not isinstance(df, accepted):
        raise InvalidInputError(
            f"{func} needs a polars DataFrame, not {type(df).__name__}. Convert a pandas frame with "
            "pl.from_pandas, or scrape with Scraper(backend='polars').",
            obj=df,
        )


def _raise_missing_columns(
    df: pl.DataFrame,
    func: str,
    required: list[str],
    *,
    level: str = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> None:
    """Raises InvalidInputError for anything but a polars frame holding every column the call needs."""
    _require_polars(df, func)

    required = list(required)

    if level == "period":
        required.append("period")

    if score:
        required += ["score_state", "opp_score_state"]

    if teammates:
        required += TEAMMATES_COLS

    if opposition:
        required += OPPOSITION_COLS

    missing = [x for x in required if x not in df.columns]
    if missing:
        raise InvalidInputError(
            f"{func} is missing required play-by-play columns: {missing}. Pass the "
            "unaggregated play-by-play DataFrame, e.g. Scraper.play_by_play, not the "
            "output of prep_stats/prep_team_stats.",
            obj=df,
        )

    # Play-by-play from 1.8 has no shootout_attempt, and mixing it with 1.9 rows leaves nulls
    if "shootout_attempt" not in df.columns or df["shootout_attempt"].null_count() > 0:
        raise InvalidInputError(
            f"{func} needs play-by-play from chickenstats 1.9 or later, and this frame has rows "
            "from an earlier version. Scrape those games again.",
            obj=df,
        )


def prep_p60(df: pd.DataFrame | pl.DataFrame) -> pd.DataFrame | pl.DataFrame:
    """Add per-60 normalized columns to a stats DataFrame.

    Divides each stat in ``P60_STATS`` by ``toi / 60``, appending a ``_p60`` suffix.
    A rate is null when ``toi`` is 0. Called by ``prep_stats``, ``prep_lines``, and ``prep_team_stats`` after the
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

    for stat_for, stat_against in zip(stats_for, stats_against, strict=True):
        # A pair with a missing side, such as xG without a model, gets no percentage column
        if stat_for not in df.columns or stat_against not in df.columns:
            continue

        # A percentage with nothing on either side is null, not 0
        total = nw.col(stat_for) + nw.col(stat_against)
        exprs.append(nw.when(total > 0).then(nw.col(stat_for) / total).alias(f"{stat_for}_percent"))

    return df.with_columns(exprs) if exprs else df  # ty: ignore[unresolved-attribute]


def prep_oi_percent(df: pd.DataFrame | pl.DataFrame) -> pd.DataFrame | pl.DataFrame:
    """Add on-ice percentage columns to a stats DataFrame.

    Pairs each stat in ``OI_PERCENT_STATS_FOR`` with its counterpart in
    ``OI_PERCENT_STATS_AGAINST`` and appends a ``_percent`` column
    (e.g., ``xgf_percent = xgf / (xgf + xga)``). A percentage is null when both
    sides are 0, and left out when either column is missing.

    Parameters:
        df (pd.DataFrame | pl.DataFrame): Stats DataFrame containing for/against columns.
    """
    stats_for = OI_PERCENT_STATS_FOR

    stats_against = OI_PERCENT_STATS_AGAINST

    df = _prep_oi_percent(df, stats_for=stats_for, stats_against=stats_against)

    return df


def _sort_rows(df: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Sort an aggregated frame by its grouping columns so the row order is the same on every call."""
    return df.sort([x for x in keys if x in df.columns], nulls_last=True)


def _uncovered_xg_seasons(df: pl.DataFrame) -> dict[str, list[int]]:
    """Return the seasons where each supplied xG column has no values, not counting a shootout's 0."""
    sources = [c for c in STINT_XG_COLS if c in df.columns]
    if not sources:
        return {}

    covered = df.group_by("season").agg(
        pl.col(c).filter(pl.col("shootout_attempt") == 0).is_not_null().any() for c in sources
    )
    return {c: covered.filter(~pl.col(c))["season"].to_list() for c in sources}


def _null_uncovered_xg(stats: pl.DataFrame, uncovered: dict[str, list[int]]) -> pl.DataFrame:
    """Set xG columns to null in the seasons their source does not cover, where a sum would read 0.0."""
    exprs = []
    for col in stats.columns:
        if "xg" not in col:
            continue
        source = "base_xg" if "base_" in col else "context_xg" if "context_" in col else "pred_goal"
        if uncovered.get(source):
            exprs.append(pl.when(pl.col("season").is_in(uncovered[source])).then(None).otherwise(col).alias(col))

    return stats.with_columns(exprs)


def _drop_empty_rows(df: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Drops rows with no ice time and no events."""
    counts = [c for c, dtype in df.schema.items() if c not in keys and not c.startswith("toi") and dtype.is_numeric()]
    has_event = pl.any_horizontal([pl.col(c).fill_null(0) != 0 for c in counts]) if counts else pl.lit(False)

    return df.filter((pl.col("toi").fill_null(0) > 0) | has_event)


def _prepare_pbp(df: pl.DataFrame, level: str) -> tuple[pl.DataFrame, dict[str, list[int]]]:
    """Ready play-by-play for summing. Returns it with the seasons each xG source does not cover."""
    # A season is one row, regular season and playoffs together
    if level == "season":
        df = df.with_columns(session=pl.lit("ALL"))

    df = prepare_xg(df)
    uncovered_xg = _uncovered_xg_seasons(df)

    # A faceoff with no winner is nobody's win or loss, but its ice time still counts for both sides,
    # so it is summed from the home side like the other events with no team
    if {"home_team", "away_team"} <= set(df.columns):
        no_winner = (pl.col("fac") == 1) & pl.col("event_team").is_null()
        df = df.with_columns(
            *[pl.when(no_winner).then(0).otherwise(pl.col(c)).alias(c) for c in ("fac", "ozf", "nzf", "dzf")],
            event_team=pl.when(no_winner).then(pl.col("home_team")).otherwise(pl.col("event_team")),
            opp_team=pl.when(no_winner).then(pl.col("away_team")).otherwise(pl.col("opp_team")),
        )

    return _add_unblocked_corsi_adj(df), uncovered_xg


def _finish(
    df: pl.DataFrame, level: str, schema: pa_pl.DataFrameSchema, keys: list[str], uncovered_xg: dict[str, list[int]]
) -> pl.DataFrame:
    """Validate a prep_* result, sort its rows and null the xG of the seasons with none."""
    if level == "season":
        df = df.drop("session")

    return _null_uncovered_xg(_sort_rows(validate_dataframe(df, schema), keys), uncovered_xg)


def _id_cols(name: str) -> list[str]:
    """Return a player or lineup column with its two id columns."""
    return [name, f"{name}_eh_id", f"{name}_api_id"]


def _player_cols(player: str, position: str) -> dict[str, str]:
    """Map a player's columns to their output names."""
    return {player: "player", f"{player}_eh_id": "eh_id", f"{player}_api_id": "api_id", position: "position"}


def _player_1_stats(df: pl.DataFrame, group_args: dict[str, Any]) -> pl.DataFrame:
    """Sum the events each player was first on: their shots, blocks, faceoff wins, hits and penalties taken."""
    player_cols = _player_cols("player_1", "player_1_position")

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
        "unblocked_corsi_adj": "iff_corsi_adj",
        "pred_goal": "ixg",
        "pred_goal_adj": "ixg_adj",
        "base_xg": "base_ixg",
        "base_xg_adj": "base_ixg_adj",
        "context_xg_adj": "context_ixg_adj",
        "context_xg": "context_ixg",
        "ozf": "iozfw",
        "nzf": "inzfw",
        "dzf": "idzfw",
    }

    # An event with no description is kept: it cannot be a teammate block
    return (
        df.lazy()
        .filter(
            ~pl.col("player_1").is_in(["BENCH", "REFEREE"]),
            ~pl.col("description").str.contains(TEAMMATE_BLOCK_PATTERN).fill_null(False),
        )
        .group_by(build_group_list(["season", "session", "event_team", *player_cols], **group_args))
        .agg(pl.sum(x) for x in new_cols if x in df.columns)
        .collect(engine=COLLECT_ENGINE)
        .rename(new_cols | player_cols | {"event_team": "team"}, strict=False)
    )


def _player_2_stats(df: pl.DataFrame, merge_list: list[str], group_args: dict[str, Any]) -> pl.DataFrame:
    """Sum the events each player was second on: as the opponent, as the primary assist, or as a teammate block."""
    player_cols = _player_cols("player_2", "player_2_position")

    base_df = df.lazy().filter(~pl.col("player_2").is_in(["BENCH", "REFEREE"]))

    opp_cols = {
        "pen0": "ipend0",
        "pen2": "ipend2",
        "pen4": "ipend4",
        "pen5": "ipend5",
        "pen10": "ipend10",
        "fac": "ifol",
        "hit": "iht",
        # The zone is the winner's, so the loser's offensive zone is the winner's defensive zone
        "ozf": "idzfl",
        "nzf": "inzfl",
        "dzf": "iozfl",
        "block": "isb",
        "block_adj": "isb_adj",
    }

    opps = (
        base_df.filter(
            ~pl.col("description").str.contains(TEAMMATE_BLOCK_PATTERN).fill_null(False),
            pl.col("event").is_in(OPPOSING_PLAYER_2_EVENTS),
        )
        .group_by(build_against_group_list(["season", "session", "opp_team", *player_cols], **group_args))
        .agg(pl.sum(x) for x in opp_cols if x in df.columns)
        .collect(engine=COLLECT_ENGINE)
        .rename(opp_cols | player_cols | OPPONENT_SWAP_COLS, strict=False)
    )

    own_cols = {"goal": "a1", "pred_goal": "a1_xg", "teammate_block": "isb", "teammate_block_adj": "isb_adj"}

    own = (
        base_df.filter(pl.col("event").is_in(["BLOCK", "GOAL"]))
        .group_by(build_group_list(["season", "session", "event_team", *player_cols], **group_args))
        .agg(pl.sum(x) for x in own_cols if x in df.columns)
        .collect(engine=COLLECT_ENGINE)
        .rename(own_cols | player_cols | {"event_team": "team"}, strict=False)
    )

    # Both sides have isb and isb_adj, and prep_ind adds the suffixed pair back in
    return opps.join(own, on=merge_list, how="full", coalesce=True, nulls_equal=True, suffix="_right")


def _player_3_stats(df: pl.DataFrame, group_args: dict[str, Any]) -> pl.DataFrame:
    """Sum the events each player was third on: the secondary assists."""
    player_cols = _player_cols("player_3", "player_3_position")

    new_cols = {"goal": "a2", "pred_goal": "a2_xg"}

    return (
        df.lazy()
        .filter(~pl.col("player_3").is_in(["BENCH", "REFEREE"]))
        .group_by(build_group_list(["season", "session", "event_team", *player_cols], **group_args))
        .agg(pl.sum(x) for x in new_cols if x in df.columns)
        .collect(engine=COLLECT_ENGINE)
        .rename(new_cols | player_cols | {"event_team": "team"}, strict=False)
    )


def prep_ind(
    df: pl.DataFrame,
    *,
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
    _raise_missing_columns(
        df, "prep_ind", IND_REQUIRED_COLS, level=level, score=score, teammates=teammates, opposition=opposition
    )

    df, uncovered_xg = _prepare_pbp(df, level)

    df = _cast_api_id_columns(df.drop(UNREAD_PBP_COLS, strict=False))

    group_args: dict[str, Any] = {
        "level": level,
        "strength_state": strength_state,
        "score": score,
        "teammates": teammates,
        "opposition": opposition,
        "ensure_team": opposition,
    }

    merge_list = build_group_list(["season", "session", "player", "eh_id", "api_id", "position", "team"], **group_args)

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

    for player_df in (
        _player_1_stats(df, group_args),
        _player_2_stats(df, merge_list, group_args),
        _player_3_stats(df, group_args),
    ):
        ind_stats = ind_stats.join(player_df, on=merge_list, how="full", coalesce=True, nulls_equal=True)

    # Fixing some stats

    null_columns = pl.exclude(merge_list).fill_null(0)

    ind_stats = ind_stats.with_columns(null_columns)

    ind_stats = ind_stats.with_columns(
        isb=pl.col("isb") + pl.col("isb_right"),
        isb_adj=pl.col("isb_adj") + pl.col("isb_adj_right"),
        icf=pl.col("iff") + pl.col("isb") + pl.col("isb_right"),
        icf_adj=pl.col("iff_corsi_adj") + pl.col("isb_adj") + pl.col("isb_adj_right"),
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

    return _finish(ind_stats, level, ind_stats_pandera_polars, merge_list, uncovered_xg)


def _attach_ext(df: pl.DataFrame, df_ext: pl.DataFrame) -> pl.DataFrame:
    """Add play_by_play_ext's columns to play-by-play, by id and event_idx.

    The two frames normally line up row for row, and then nothing needs copying. A join
    would copy every column of a season's play-by-play.
    """
    keys = ["id", "event_idx"]
    if df.height == df_ext.height and df.select(keys).equals(df_ext.select(keys), null_equal=True):
        added = [col for col in df_ext.columns if col not in df.columns]
        return df.hstack(df_ext.select(added))

    return df.join(df_ext, on=keys, how="left", nulls_equal=True)


def _with_slots(df: pl.DataFrame, df_ext: pl.DataFrame | None) -> pl.DataFrame:
    """Add the on-ice slots to play-by-play, building them from its lineups if ``df_ext`` is None."""
    if df_ext is None:
        df_ext = build_play_by_play_ext(df)

    return _attach_ext(df.drop(UNREAD_PBP_COLS, strict=False), df_ext)


def _side_totals(
    data: pl.DataFrame,
    group_list: list[str],
    stats: dict[str, str],
    group_names: dict[str, str],
    extra: list[pl.Expr] | None = None,
) -> pl.DataFrame:
    """Sum one side's stats and ice time, then give the stats and grouping columns their output names."""
    renames = stats | {"event_length": "toi"}
    totals = [pl.sum(x) for x in renames if x in data.columns] + (extra or [])

    return data.group_by(group_list).agg(totals).rename(renames | group_names, strict=False)


def _zone_start_totals(came_on: str) -> list[pl.Expr]:
    """Count the zone starts of the changes that brought on at least one player counted in ``came_on``.

    The play-by-play has one CHANGE row per team per second, so a team or line gets one zone start per change.
    A change that only takes players off, such as everyone leaving at the end of a period, is not a start.
    """
    return [pl.col(src).filter(pl.col(came_on) > 0).sum().alias(name) for src, name in ZONE_START_COLS.items()]


def _on_ice_exprs() -> dict[str, pl.Expr]:
    """Return the columns prep_oi, prep_lines and prep_team_stats derive from their summed sides."""
    return {
        # Teammate blocks are blocked attempts too, so cf = ff + bsf and ca = fa + bsa
        "bsf": pl.col("bsf") + pl.col("teammate_block"),
        "bsf_adj": pl.col("bsf_adj") + pl.col("teammate_block_adj"),
        "bsa": pl.col("bsa") + pl.col("opp_teammate_block"),
        "bsa_adj": pl.col("bsa_adj") + pl.col("opp_teammate_block_adj"),
        "cf": pl.col("ff") + pl.col("bsf") + pl.col("teammate_block"),
        "cf_adj": pl.col("ff_corsi_adj") + pl.col("bsf_adj") + pl.col("teammate_block_adj"),
        "ca": pl.col("fa") + pl.col("bsa") + pl.col("opp_teammate_block"),
        "ca_adj": pl.col("fa_corsi_adj") + pl.col("bsa_adj") + pl.col("opp_teammate_block_adj"),
        "ozf": pl.col("ozfw") + pl.col("ozfl"),
        "nzf": pl.col("nzfw") + pl.col("nzfl"),
        "dzf": pl.col("dzfw") + pl.col("dzfl"),
    }


def _normalize_lineup_cols(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Split comma-space String lineup columns, as the scraper writes them, into List[String].

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
    """Build the extended on-ice slot DataFrame from the PBP lineup columns.

    Expands the lineup columns (teammates_*, opp_team_on_*, change_on_*
    and their *_eh_id, *_api_id, *_positions variants) into per-slot columns
    event_on_1..7, opp_on_1..7, change_on_1..7 (each with _eh_id, _api_id, _pos).
    Returns a DataFrame keyed on id + event_idx for joining into prep_oi.

    Accepts the comma-space delimited String columns the scraper produces, or
    List[String] columns.

    Parameters:
        df (pl.DataFrame): Play-by-play DataFrame with on-ice lineup columns.
    """
    _require_polars(df, "build_play_by_play_ext")

    player_groups = [
        ("teammates", "teammates_eh_id", "teammates_api_id", "teammates_positions", "event_on"),
        ("opp_team_on", "opp_team_on_eh_id", "opp_team_on_api_id", "opp_team_on_positions", "opp_on"),
        ("change_on", "change_on_eh_id", "change_on_api_id", "change_on_positions", "change_on"),
    ]

    df = _normalize_lineup_cols(df, EXT_SOURCE_COLS)

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
    *,
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
            When ``None``, built automatically from the lineup columns in ``df``.
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    required = ON_ICE_REQUIRED_COLS + ["ozc", "nzc", "dzc", "otf"]
    if df_ext is None:
        required += EXT_SOURCE_COLS

    _raise_missing_columns(
        df, "prep_oi", required, level=level, score=score, teammates=teammates, opposition=opposition
    )

    df, uncovered_xg = _prepare_pbp(df, level)

    # Lazy, so each slot's select below reads only its own columns.
    joined = _cast_api_id_columns(_with_slots(df, df_ext)).lazy()
    joined_columns = joined.collect_schema().names()

    group_keys = [
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

    group_args: dict[str, Any] = {
        "level": level,
        "strength_state": strength_state,
        "score": score,
        "teammates": teammates,
        "opposition": opposition,
        "ensure_team": opposition,
    }

    def _slot_totals(
        slot: str, stats: list[str], renames: dict[str, str], team: str, build_groups: Callable[..., list[str]]
    ) -> pl.DataFrame:
        """Sum one slot by the keys it carries."""
        player_cols = _player_cols(slot, f"{slot}_pos")
        groups = build_groups(["season", "session", team, *player_cols], **group_args)
        select_cols = [x for x in [*groups, *stats] if x in joined_columns]

        rows = (
            joined.select(select_cols)
            .rename(renames | player_cols, strict=False)
            .drop_nulls(subset=["player", "eh_id", "api_id"])
        )

        names = rows.collect_schema().names()
        keys = [x for x in group_keys if x in names]
        return rows.group_by(keys).agg([pl.sum(x) for x in names if x not in group_keys]).collect(engine=COLLECT_ENGINE)

    def _combine(slots: list[pl.DataFrame], source: str) -> pl.DataFrame:
        """Sum one kind of slot across its slots, flagging where the rows came from."""
        combined = pl.concat(slots)
        keys = [x for x in group_keys if x in combined.columns]
        totals = [pl.sum(x) for x in combined.columns if x not in group_keys]
        return combined.group_by(keys).agg(totals).with_columns(pl.lit(1).alias(source))

    on_ice_stats = [*ON_ICE_FOR, "event_length"]
    own_renames = ON_ICE_FOR | ZONE_START_COLS | {"event_team": "team"}
    against_renames = ON_ICE_AGAINST | OPPONENT_SWAP_COLS

    slot_kinds = (
        ("event_on", "event_df", on_ice_stats, own_renames, "event_team", build_group_list),
        ("opp_on", "opp_df", on_ice_stats, against_renames, "opp_team", build_against_group_list),
        ("change_on", "zones_df", list(ZONE_START_COLS), own_renames, "event_team", build_group_list),
    )

    # One slot at a time, so the rows of 21 slots are never in memory together.
    event_stats, opp_stats, zones_stats = (
        _combine([_slot_totals(f"{prefix}_{i}", stats, renames, team, groups) for i in range(1, 8)], source)
        for prefix, source, stats, renames, team, groups in slot_kinds
    )

    merge_cols = [
        x for x in group_keys if x in event_stats.columns and x in opp_stats.columns and x in zones_stats.columns
    ]

    # suffix="_right" explicit — toi below references event_length_right.
    oi_stats = event_stats.join(opp_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True, suffix="_right")

    oi_stats = oi_stats.join(zones_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True)

    null_columns = pl.exclude(merge_cols).fill_null(0)

    oi_stats = oi_stats.with_columns(null_columns)

    oi_stats = oi_stats.with_columns(
        api_id=pl.col("api_id").cast(Int64),
        toi=(pl.col("event_length") + pl.col("event_length_right")) / 60,
        fac=(pl.col("ozfw") + pl.col("ozfl") + pl.col("nzfw") + pl.col("nzfl") + pl.col("dzfw") + pl.col("dzfl")),
        **_on_ice_exprs(),
    )

    columns = [x for x in list(oi_stats_pandera_polars.dtypes.keys()) if x in oi_stats.columns] + [
        "event_df",
        "opp_df",
        "zones_df",
    ]

    oi_stats = oi_stats.select(columns)

    # The source flags are always 1, so they don't count as events
    oi_stats = _drop_empty_rows(oi_stats, [*merge_cols, "event_df", "opp_df", "zones_df"])

    return _finish(oi_stats, level, oi_stats_pandera_polars, merge_cols, uncovered_xg)


def _merge_stats(ind_stats_df: pl.DataFrame, oi_stats_df: pl.DataFrame) -> pl.DataFrame:
    """Merge individual and on-ice stats into a combined per-player DataFrame.

    Called internally by ``_ScraperStatsMixin._prep_stats`` and ``prep_stats``.
    Joins ``ind_stats_df`` and ``oi_stats_df`` on shared groupby keys, then
    appends per-60 and percentage columns.

    Parameters:
        ind_stats_df (pl.DataFrame): Output of ``prep_ind()``.
        oi_stats_df (pl.DataFrame): Output of ``prep_oi()``.
    """
    key_candidates = [
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
        *TEAMMATES_COLS,
        *OPPOSITION_COLS,
    ]

    merge_cols = [x for x in key_candidates if x in ind_stats_df.columns and x in oi_stats_df.columns]

    # A full join, because an event can be credited to a player with no on-ice row in that group, such as a
    # secondary assist or a penalty taken from the bench
    stats = oi_stats_df.join(ind_stats_df, how="full", on=merge_cols, nulls_equal=True, coalesce=True)

    # A season with no xG in a column stays null there, so only a group with no attempts becomes 0
    null_columns = [
        pl.when(pl.col(c).is_not_null().any().over("season")).then(pl.col(c).fill_null(0)).alias(c)
        if "xg" in c
        else pl.col(c).fill_null(0)
        for c in stats.columns
        if c not in merge_cols
    ]

    stats = _drop_empty_rows(stats.with_columns(null_columns), merge_cols)

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

    # The remaining grouping columns break ties, so the row order is the same on every call
    tie_breakers = [x for x in merge_cols if x not in sort_list]
    sort_list += tie_breakers
    descending_list += [False] * len(tie_breakers)

    stats = stats.with_columns(integer_columns).sort(by=sort_list, descending=descending_list)

    stats = prep_p60(stats)
    stats = prep_oi_percent(stats)

    stats = validate_dataframe(cast(pl.DataFrame, stats), stats_pandera_polars)

    return stats


def prep_stats(
    df: pl.DataFrame,
    df_ext: pl.DataFrame | None = None,
    *,
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
            from the lineup columns in ``df`` when ``None``.
        level (str): Aggregation level. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    # prep_ind checks df too, but would name itself
    _require_polars(df, "prep_stats")
    if df_ext is not None:
        _require_polars(df_ext, "prep_stats")

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
    *,
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
            from the lineup columns in ``df`` when ``None``.
        position (str): ``'f'`` for forward lines, ``'d'`` for defense pairs. Default ``'f'``.
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        score (bool): Split by score state. Default ``False``.
        teammates (bool): Split by teammate lineup. Default ``False``.
        opposition (bool): Split by opposing lineup. Default ``False``.
    """
    if position not in ("f", "d"):
        raise InvalidInputError(f"position must be 'f' or 'd', got {position!r}", obj=position)

    line, other = ("forwards", "defense") if position == "f" else ("defense", "forwards")
    line_cols = _id_cols(line)
    came_on = f"change_on_{line}_count"

    required = ON_ICE_REQUIRED_COLS + line_cols + [*ZONE_START_COLS, came_on]
    if df_ext is None:
        required += EXT_SOURCE_COLS

    _raise_missing_columns(
        df, "prep_lines", required, level=level, score=score, teammates=teammates, opposition=opposition
    )

    df, uncovered_xg = _prepare_pbp(df, level)

    data = _with_slots(df, df_ext)

    group_args: dict[str, Any] = {
        "level": level,
        "strength_state": strength_state,
        "score": score,
        "teammates": teammates,
        "opposition": opposition,
        "ensure_team": opposition,
    }

    teammate_cols = [*_id_cols(other), *_id_cols("own_goalie")]

    lines_f = _side_totals(
        data,
        build_group_list(["season", "session", "event_team", *line_cols], teammates_cols=teammate_cols, **group_args),
        ON_ICE_FOR,
        {"event_team": "team"},
        # A line starts a shift when one of its players comes on
        _zone_start_totals(came_on),
    )

    lines_a = _side_totals(
        data,
        build_against_group_list(
            ["season", "session", "opp_team", *_id_cols(f"opp_{line}")],
            teammates_cols=[*_id_cols(f"opp_{other}"), *_id_cols("opp_goalie")],
            **group_args,
        ),
        ON_ICE_AGAINST,
        OPPONENT_SWAP_COLS,
    )

    # Merging the "for" and "against" dataframes. This order sets the row order, so it is
    # written out here rather than taken from build_group_list.

    if level in ("session", "season"):
        merge_list = ["season", "session", "team", *line_cols]
    else:
        merge_list = ["season", "game_id", "game_date", "session", "team", "opp_team", *line_cols]

    if level == "period":
        merge_list.append("period")

    if strength_state:
        merge_list.append("strength_state")

    if score:
        merge_list.append("score_state")

    if teammates:
        merge_list += teammate_cols

    if opposition:
        merge_list += OPPOSITION_COLS

        if "opp_team" not in merge_list:
            merge_list.insert(3, "opp_team")

    # suffix="_right" explicit — toi below references that column.
    lines = lines_f.join(lines_a, how="full", on=merge_list, coalesce=True, nulls_equal=True, suffix="_right")

    null_columns = pl.exclude(merge_list).fill_null(0)

    lines = lines.with_columns(null_columns)

    # Float addition is not associative, so the _adj sums keep their own term order
    lines = lines.with_columns(
        toi=(pl.col("toi") + pl.col("toi_right")) / 60,
        **_on_ice_exprs()
        | {
            "cf_adj": pl.col("bsf_adj") + pl.col("teammate_block_adj") + pl.col("ff_corsi_adj"),
            "ca_adj": pl.col("bsa_adj") + pl.col("fa_corsi_adj") + pl.col("opp_teammate_block_adj"),
        },
    )

    lines = _drop_empty_rows(lines, merge_list)

    lines = prep_p60(lines)

    lines = prep_oi_percent(lines)

    return _finish(cast(pl.DataFrame, lines), level, line_stats_pandera_polars, merge_list, uncovered_xg)


def prep_team_stats(
    df: pl.DataFrame,
    df_ext: pl.DataFrame | None = None,
    *,
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
            from the lineup columns in ``df`` when ``None``.
        level (str): Aggregation level — ``'period'``, ``'game'``, ``'session'``, or ``'season'``. Default ``'game'``.
        strength_state (bool): Split by strength state. Default ``True``.
        opposition (bool): Add ``opp_team``, for one row per opponent. Default ``False``.
        score (bool): Split by score state. Default ``False``.
    """
    required = [*ON_ICE_REQUIRED_COLS, "opp_team", *ZONE_START_COLS, "change_on_count"]
    if df_ext is None:
        required += EXT_SOURCE_COLS

    _raise_missing_columns(df, "prep_team_stats", required, level=level, score=score)

    df, uncovered_xg = _prepare_pbp(df, level)

    data = _with_slots(df, df_ext)

    group_args: dict[str, Any] = {
        "level": level,
        "strength_state": strength_state,
        "score": score,
        "ensure_team": opposition,
    }

    stats_for = _side_totals(
        data,
        build_group_list(["season", "session", "event_team"], **group_args),
        ON_ICE_FOR,
        {"event_team": "team"},
        _zone_start_totals("change_on_count"),
    )

    stats_against = _side_totals(
        data,
        build_against_group_list(["season", "session", "opp_team"], **group_args),
        ON_ICE_AGAINST,
        OPPONENT_SWAP_COLS,
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

    merge_list = [x for x in merge_list if x in stats_for.columns and x in stats_against.columns]

    # suffix="_right" explicit — toi below references that column.
    team_stats = stats_for.join(
        stats_against, on=merge_list, how="full", nulls_equal=True, coalesce=True, suffix="_right"
    )

    # A group where only one side has rows gets nulls on the other side, which are zeros
    team_stats = team_stats.with_columns(pl.exclude(merge_list).fill_null(0))

    team_stats = team_stats.with_columns(toi=(pl.col("toi") + pl.col("toi_right")) / 60, **_on_ice_exprs())

    team_stats = _drop_empty_rows(team_stats, merge_list)

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    return _finish(cast(pl.DataFrame, team_stats), level, team_stats_pandera_polars, merge_list, uncovered_xg)


def prep_rolling_stats(
    df: pl.DataFrame,
    window: int = 10,
    stats: list[str] | None = None,
    group_cols: list[str] | None = None,
    min_periods: int = 1,
) -> pl.DataFrame:
    """Add trailing rolling-window values for rate-stat columns.

    Operates on the output of ``prep_stats`` or ``prep_team_stats`` at ``level='game'``.
    Sorts by game order within each ``group_cols`` group, then computes each stat over the
    trailing ``window`` games, appending ``rolling_{stat}`` columns. Rates and percentages
    come from the rolling sums of their counts; any other column gets a rolling mean.

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
            output), or if ``group_cols`` plus ``game_id`` (``game_date`` when there is no
            ``game_id``) don't uniquely identify rows (multiple rows per game per group, e.g.
            unfiltered strength/score-state splits, or ``level='period'`` output).

    Examples:
        >>> from chickenstats.chicken_nhl import prep_rolling_stats
        >>> game_stats = scraper.prep_stats(level="game", strength_state=False).stats
        >>> rolling = prep_rolling_stats(game_stats, window=10)
    """
    _require_polars(df, "prep_rolling_stats")

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

    # A game is keyed by game_id when there is one, so a split-squad day with two games on one
    # date is two games; the games are ordered by date, then by game_id
    game_col = "game_id" if "game_id" in df.columns else "game_date"
    sort_cols = list(group_cols) + [x for x in ("game_date", "game_id") if x in df.columns]

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

    percent_pairs = dict(zip(OI_PERCENT_STATS_FOR, OI_PERCENT_STATS_AGAINST, strict=True))

    def rolling_sum(column: str) -> pl.Expr:
        return pl.col(column).rolling_sum(window_size=window, min_samples=min_periods).over(group_cols)

    # Rates and percentages are recomputed from rolling sums, so a short game counts for less
    rolling_exprs = []
    for stat in stats:
        if stat not in df.columns:
            continue

        count = stat.removesuffix("_p60")
        stat_for = stat.removesuffix("_percent")
        stat_against = percent_pairs.get(stat_for)

        if stat.endswith("_p60") and count in df.columns and "toi" in df.columns:
            toi = rolling_sum("toi")
            expr = pl.when(toi > 0).then(rolling_sum(count) / toi * 60)
        elif stat.endswith("_percent") and stat_for in df.columns and stat_against in df.columns:
            total = rolling_sum(stat_for) + rolling_sum(stat_against)
            expr = pl.when(total > 0).then(rolling_sum(stat_for) / total)
        else:
            expr = pl.col(stat).rolling_mean(window_size=window, min_samples=min_periods).over(group_cols)

        rolling_exprs.append(expr.alias(f"rolling_{stat}"))

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
        Penalty shots and shootout attempts have one skater on ice, so they're left
        out of stints. Stint totals fall short of ``prep_team_stats`` by the penalty-shot
        goals and shots; shootout attempts are not counted in either.

    Note:
        A stint whose events all fall in one second has ``toi_seconds`` of 0. It is kept
        when it holds a shot attempt or goal and dropped otherwise. ``build_rapm_matrix``
        leaves it out, since it has no rate.

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
    _raise_missing_columns(df, "prep_stints", STINT_REQUIRED_COLS)

    # The sort below would otherwise copy every column of the frame
    df = df.select([col for col in dict.fromkeys(STINT_READ_COLS) if col in df.columns])

    df = prepare_xg(df)
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
        pl.col(
            "game_date",
            "home_team",
            "away_team",
            "home_on_api_id",
            "away_on_api_id",
            "home_goalie_api_id",
            "away_goalie_api_id",
            "home_score_3",
            "home_score_7",
            "away_score_3",
            "away_score_7",
            "home_b2b",
            "away_b2b",
        ).first(),
        pl.col("event_length").sum().alias("toi_seconds"),
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
        (pl.col("zone_start") == "NEU").any().alias("nzs"),
        # Each team's own zone start: an away change into its defensive zone is a home OZS
        (((pl.col("zone_start") == "OFF") & (is_home == 1)) | ((pl.col("zone_start") == "DEF") & (is_away == 1)))
        .any()
        .alias("home_ozs"),
        (((pl.col("zone_start") == "DEF") & (is_home == 1)) | ((pl.col("zone_start") == "OFF") & (is_away == 1)))
        .any()
        .alias("home_dzs"),
    ]

    agg_stats += [
        (pl.col(source) * mask).sum().alias(f"{venue}_{suffix}")
        for source, suffix in STINT_XG_COLS.items()
        if source in df.columns
        for venue, mask in (("home", is_home), ("away", is_away))
    ]

    stints = df.group_by(["season", "session", "game_id", "period", "stint_id"]).agg(agg_stats)
    stints = _null_uncovered_xg(stints, _uncovered_xg_seasons(df))

    # Derived, not summed separately: sums are linear.
    if "home_context_xgf" in stints.columns and "home_base_xgf" in stints.columns:
        stints = stints.with_columns(
            home_delta_xgf=pl.col("home_context_xgf") - pl.col("home_base_xgf"),
            away_delta_xgf=pl.col("away_context_xgf") - pl.col("away_base_xgf"),
        )

    # A stint with no time is kept when it holds a shot attempt or goal, so stint totals match the play-by-play
    has_shot = pl.sum_horizontal("home_cf", "away_cf", "home_gf", "away_gf") > 0
    stints = stints.filter((pl.col("toi_seconds") > 0) | has_shot)
    # One team's offensive-zone start is the other's defensive-zone start.
    stints = stints.with_columns(away_ozs=pl.col("home_dzs"), away_dzs=pl.col("home_ozs"))

    # Null lineup columns become empty lists so set_difference and list.len() stay defined.
    stints = (
        stints.with_columns(
            home_goalie_ids=pl.col("home_goalie_api_id").fill_null([]),
            away_goalie_ids=pl.col("away_goalie_api_id").fill_null([]),
        )
        .with_columns(
            home_skater_ids=pl.col("home_on_api_id").list.set_difference(pl.col("home_goalie_ids")).fill_null([]),
            away_skater_ids=pl.col("away_on_api_id").list.set_difference(pl.col("away_goalie_ids")).fill_null([]),
        )
        .with_columns(
            home_skater_count=pl.col("home_skater_ids").list.len().cast(pl.Int64),
            away_skater_count=pl.col("away_skater_ids").list.len().cast(pl.Int64),
        )
    )

    # Home side first, whichever team had the stint's first event; E is an empty net.
    home_strength, away_strength = (
        pl.when(pl.col(f"{venue}_goalie_ids").list.len() == 0)
        .then(pl.lit("E"))
        .otherwise(pl.col(f"{venue}_skater_count").cast(pl.String))
        for venue in ("home", "away")
    )
    stints = stints.with_columns(strength_state=pl.concat_str([home_strength, away_strength], separator="v"))

    stints = stints.filter((pl.col("home_skater_count") >= min_skaters) & (pl.col("away_skater_count") >= min_skaters))

    stints = stints.with_columns(
        pl.col("toi_seconds").cast(pl.Int64),
        pl.col("stint_id").cast(pl.Int64),
        pl.col([col for col in STINT_COUNT_COLS if col in stints.columns]).cast(pl.Int64),
        pl.col(["home_b2b", "away_b2b", "nzs", "home_ozs", "home_dzs", "away_ozs", "away_dzs"]).cast(pl.Boolean),
    )

    stints = stints.select([col for col in STINT_COLUMN_ORDER if col in stints.columns])

    return stints.sort(["game_date", "game_id", "period", "stint_id"])
