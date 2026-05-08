"""Compute multi-window rolling GxG/GSAx talent metrics for the informed_xg pipeline.

Input: combined scored parquets (all 5 strengths concatenated), sorted chronologically,
containing 'base_xg', 'goal', 'player_1_api_id', 'opp_goalie_api_id',
'season', 'session', 'game_id'.

All rows are already fenwick events (filtered by prep_data in process_data_base.py).
Returns the input DataFrame with 16 rolling stat columns added.
"""

import polars as pl

SHOOTER_ID_COL = "player_1_api_id"
GOALIE_ID_COL = "opp_goalie_api_id"
MIN_SHOTS = 20  # hard floor for raw cumulative stats
PRIOR_SHOTS = 100  # Bayesian prior: rookie with 5 shots gets pulled toward 0 by 100 phantom avg shots
EWMA_HALF_LIFE = 50  # shots until a past observation retains 50% weight


def _event_level_stats(
    df: pl.DataFrame, id_col: str, metric_expr: pl.Expr, stat_col: str, shots_col: str
) -> pl.DataFrame:
    """Career and season-YTD cumulative GxG or GSAx with shift(1) leakage guard."""
    df = df.with_columns(
        _g=metric_expr.cum_sum().shift(1).over(id_col),
        _s=pl.lit(1).cum_sum().shift(1).over(id_col),
        _sg=metric_expr.cum_sum().shift(1).over([id_col, "season", "session"]),
        _ss=pl.lit(1).cum_sum().shift(1).over([id_col, "season", "session"]),
    )
    return df.with_columns(
        pl.when(pl.col("_s") >= MIN_SHOTS)
        .then(pl.col("_g"))
        .otherwise(None)
        .cast(pl.Float64)
        .alias(f"{stat_col}_career"),
        # Bayesian shrinkage: divide by (shots + prior) so small samples regress toward zero
        (pl.col("_g") / (pl.col("_s") + PRIOR_SHOTS)).cast(pl.Float64).alias(f"{stat_col}_per_shot_career"),
        pl.col("_s").cast(pl.Int64).alias(f"{shots_col}_career"),
        pl.when(pl.col("_ss") >= MIN_SHOTS)
        .then(pl.col("_sg"))
        .otherwise(None)
        .cast(pl.Float64)
        .alias(f"{stat_col}_season"),
        (pl.col("_sg") / (pl.col("_ss") + PRIOR_SHOTS)).cast(pl.Float64).alias(f"{stat_col}_per_shot_season"),
        pl.col("_ss").cast(pl.Int64).alias(f"{shots_col}_season"),
    ).drop(["_g", "_s", "_sg", "_ss"])


def _ewma_stats(df: pl.DataFrame, id_col: str, metric_expr: pl.Expr, stat_col: str) -> pl.DataFrame:
    """Exponentially weighted moving average of per-shot metric, shift(1) leakage guard.

    A shot EWMA_HALF_LIFE shots ago retains 50% weight — captures hot/cold streaks
    without a hard window boundary.
    """
    return df.with_columns(
        metric_expr.ewm_mean(half_life=EWMA_HALF_LIFE, ignore_nulls=True)
        .shift(1)
        .over(id_col)
        .cast(pl.Float64)
        .alias(f"{stat_col}_ewma")
    )


def _game_level_stats(
    df: pl.DataFrame, id_col: str, metric_expr: pl.Expr, stat_col: str, shots_col: str
) -> pl.DataFrame:
    """Last-10g and last-1g GxG or GSAx via game-level aggregate and rolling window."""
    game = (
        df.group_by([id_col, "season", "game_id"])
        .agg(metric_expr.sum().alias("_g"), pl.len().alias("_s"))
        .sort([id_col, "season", "game_id"])
    )

    g10 = pl.col("_g").rolling_sum(window_size=10, min_samples=1).shift(1).over(id_col)
    s10 = pl.col("_s").rolling_sum(window_size=10, min_samples=1).shift(1).over(id_col)
    g1 = pl.col("_g").shift(1).over(id_col)
    s1 = pl.col("_s").shift(1).over(id_col)

    return game.with_columns(
        pl.when(s10 > 0).then(g10).otherwise(None).cast(pl.Float64).alias(f"{stat_col}_10g"),
        pl.when(s10 > 0).then(g10 / s10).otherwise(None).cast(pl.Float64).alias(f"{stat_col}_per_shot_10g"),
        s10.cast(pl.Int64).alias(f"{shots_col}_10g"),
        pl.when(s1 > 0).then(g1).otherwise(None).cast(pl.Float64).alias(f"{stat_col}_1g"),
        pl.when(s1 > 0).then(g1 / s1).otherwise(None).cast(pl.Float64).alias(f"{stat_col}_per_shot_1g"),
        s1.cast(pl.Int64).alias(f"{shots_col}_1g"),
    ).select(
        [
            id_col,
            "game_id",
            f"{stat_col}_10g",
            f"{stat_col}_per_shot_10g",
            f"{shots_col}_10g",
            f"{stat_col}_1g",
            f"{stat_col}_per_shot_1g",
            f"{shots_col}_1g",
        ]
    )


def compute_rolling_stats(scored: pl.DataFrame) -> pl.DataFrame:
    """Compute 4-window rolling GxG/GSAx on chronologically-sorted scored PBP.

    Input must be sorted by ['season', 'game_id', 'period', 'period_seconds'] and
    contain: base_xg, goal, player_1_api_id, opp_goalie_api_id, season, session, game_id.

    All rows are already fenwick events. Goalie stats exclude empty-net shots
    (rows where opp_goalie_api_id is null).

    Windows:
        career      — all prior shots across all seasons
        season      — all prior shots in current season + session
        10g         — shots in the 10 most recently completed games
        1g          — shots in the immediately preceding game

    Returns the input DataFrame with 16 GxG/GSAx columns added.
    """
    # Row index so we can join goalie stats back precisely (event-level stats differ per row)
    scored = scored.with_row_index("_row_idx")
    goalie_rows = scored.filter(pl.col(GOALIE_ID_COL).is_not_null())

    shooter_metric = pl.col("goal") - pl.col("base_xg")
    goalie_metric = pl.col("base_xg") - pl.col("goal")

    # Event-level career + season YTD (with Bayesian shrinkage on per-shot rates)
    scored = _event_level_stats(scored, SHOOTER_ID_COL, shooter_metric, "shooter_gax", "shooter_shots")
    goalie_rows = _event_level_stats(goalie_rows, GOALIE_ID_COL, goalie_metric, "goalie_gsax", "goalie_shots")

    # EWMA — exponentially weighted recent form
    scored = _ewma_stats(scored, SHOOTER_ID_COL, shooter_metric, "shooter_gax")
    goalie_rows = _ewma_stats(goalie_rows, GOALIE_ID_COL, goalie_metric, "goalie_gsax")

    # Game-level 10g + 1g
    shooter_game = _game_level_stats(scored, SHOOTER_ID_COL, shooter_metric, "shooter_gax", "shooter_shots")
    goalie_game = _game_level_stats(goalie_rows, GOALIE_ID_COL, goalie_metric, "goalie_gsax", "goalie_shots")

    scored = scored.join(shooter_game, on=[SHOOTER_ID_COL, "game_id"], how="left")
    goalie_rows = goalie_rows.join(goalie_game, on=[GOALIE_ID_COL, "game_id"], how="left")

    goalie_stat_cols = [
        "_row_idx",
        "goalie_gsax_career",
        "goalie_gsax_per_shot_career",
        "goalie_shots_career",
        "goalie_gsax_season",
        "goalie_gsax_per_shot_season",
        "goalie_shots_season",
        "goalie_gsax_10g",
        "goalie_gsax_per_shot_10g",
        "goalie_shots_10g",
        "goalie_gsax_1g",
        "goalie_gsax_per_shot_1g",
        "goalie_shots_1g",
        "goalie_gsax_ewma",
    ]

    # Join goalie stats back on row index; empty-net rows receive null via left join
    scored = scored.join(goalie_rows.select(goalie_stat_cols), on="_row_idx", how="left")

    return scored.drop("_row_idx")
