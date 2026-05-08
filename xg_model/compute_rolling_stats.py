"""Compute multi-window rolling talent metrics for xG model training.

Returns a join table of (_global_idx → 16 rolling stat columns) for fenwick events only.
Non-fenwick rows receive null via the left join performed in process_data.py.
"""

import polars as pl

FENWICK_EVENTS = ["GOAL", "SHOT", "MISS"]
SHOOTER_ID_COL = "player_1_api_id"
GOALIE_ID_COL = "opp_goalie_api_id"


def _event_level_stats(
    df: pl.DataFrame, id_col: str, rate_col: str, shots_col: str, invert: bool = False
) -> pl.DataFrame:
    """Career and season-YTD cumulative stats at event level with shift(1) leakage guard.

    invert=True computes 1 - rate (saves% from goals-against rather than shooting%).
    """
    df = df.with_columns(
        _g=pl.col("goal").cum_sum().shift(1).over(id_col),
        _s=pl.lit(1).cum_sum().shift(1).over(id_col),
        _sg=pl.col("goal").cum_sum().shift(1).over([id_col, "season", "session"]),
        _ss=pl.lit(1).cum_sum().shift(1).over([id_col, "season", "session"]),
    )
    career_rate = (1 - pl.col("_g") / pl.col("_s")) if invert else (pl.col("_g") / pl.col("_s"))
    season_rate = (1 - pl.col("_sg") / pl.col("_ss")) if invert else (pl.col("_sg") / pl.col("_ss"))
    return df.with_columns(
        pl.when(pl.col("_s") >= 20).then(career_rate).otherwise(None).cast(pl.Float64).alias(f"{rate_col}_career"),
        pl.col("_s").cast(pl.Int64).alias(f"{shots_col}_career"),
        pl.when(pl.col("_ss") >= 20).then(season_rate).otherwise(None).cast(pl.Float64).alias(f"{rate_col}_season"),
        pl.col("_ss").cast(pl.Int64).alias(f"{shots_col}_season"),
    ).drop(["_g", "_s", "_sg", "_ss"])


def _game_level_stats(
    df: pl.DataFrame, id_col: str, rate_col: str, shots_col: str, invert: bool = False
) -> pl.DataFrame:
    """Last-10g and last-1g stats via game-level aggregate and rolling window.

    rolling_sum(N, min_samples=1).shift(1) gives game G the sum of the N games before it.
    invert=True computes 1 - rate (saves% from goals-against rather than shooting%).
    """
    game = (
        df.group_by([id_col, "season", "game_id"])
        .agg(pl.col("goal").sum().alias("_g"), pl.len().alias("_s"))
        .sort([id_col, "season", "game_id"])
    )

    g10 = pl.col("_g").rolling_sum(window_size=10, min_samples=1).shift(1).over(id_col)
    s10 = pl.col("_s").rolling_sum(window_size=10, min_samples=1).shift(1).over(id_col)
    g1 = pl.col("_g").shift(1).over(id_col)
    s1 = pl.col("_s").shift(1).over(id_col)

    rate10 = (1 - g10 / s10) if invert else (g10 / s10)
    rate1 = (1 - g1 / s1) if invert else (g1 / s1)

    return game.with_columns(
        pl.when(s10 > 0).then(rate10).otherwise(None).cast(pl.Float64).alias(f"{rate_col}_10g"),
        s10.cast(pl.Int64).alias(f"{shots_col}_10g"),
        pl.when(s1 > 0).then(rate1).otherwise(None).cast(pl.Float64).alias(f"{rate_col}_1g"),
        s1.cast(pl.Int64).alias(f"{shots_col}_1g"),
    ).select([id_col, "game_id", f"{rate_col}_10g", f"{shots_col}_10g", f"{rate_col}_1g", f"{shots_col}_1g"])


def compute_rolling_stats(combined_raw: pl.DataFrame) -> pl.DataFrame:
    """Compute 4-window rolling talent metrics on chronologically-sorted raw PBP.

    Input must have '_global_idx' assigned before sorting, be sorted by
    ['season', 'game_id', 'game_seconds'], and contain SHOOTER_ID_COL and GOALIE_ID_COL.

    Windows:
        career   — all prior fenwick events across all seasons
        season   — all prior fenwick events in the current season + session
        10g      — fenwick events in the 10 most recent completed games
        1g       — fenwick events in the immediately preceding game

    Returns (_global_idx + 16 stat columns) for fenwick rows only.
    """
    fenwick = combined_raw.filter(pl.col("event").is_in(FENWICK_EVENTS))
    fenwick_g = fenwick.filter(pl.col(GOALIE_ID_COL).is_not_null())  # excludes empty-net shots

    # Event-level career + season YTD
    fenwick = _event_level_stats(fenwick, SHOOTER_ID_COL, "shooter_sp", "shooter_shots")
    fenwick_g = _event_level_stats(fenwick_g, GOALIE_ID_COL, "goalie_svpct", "goalie_shots", invert=True)

    # Game-level 10g + 1g
    shooter_game = _game_level_stats(fenwick, SHOOTER_ID_COL, "shooter_sp", "shooter_shots")
    goalie_game = _game_level_stats(fenwick_g, GOALIE_ID_COL, "goalie_svpct", "goalie_shots", invert=True)

    fenwick = fenwick.join(shooter_game, on=[SHOOTER_ID_COL, "game_id"], how="left")
    fenwick_g = fenwick_g.join(goalie_game, on=[GOALIE_ID_COL, "game_id"], how="left")

    # Merge goalie stats into fenwick; empty-net rows get null via left join on _global_idx
    goalie_stat_cols = [
        "_global_idx",
        "goalie_svpct_career",
        "goalie_shots_career",
        "goalie_svpct_season",
        "goalie_shots_season",
        "goalie_svpct_10g",
        "goalie_shots_10g",
        "goalie_svpct_1g",
        "goalie_shots_1g",
    ]
    fenwick = fenwick.join(fenwick_g.select(goalie_stat_cols), on="_global_idx", how="left")

    return fenwick.select(
        [
            "_global_idx",
            "shooter_sp_career",
            "shooter_shots_career",
            "shooter_sp_season",
            "shooter_shots_season",
            "shooter_sp_10g",
            "shooter_shots_10g",
            "shooter_sp_1g",
            "shooter_shots_1g",
            "goalie_svpct_career",
            "goalie_shots_career",
            "goalie_svpct_season",
            "goalie_shots_season",
            "goalie_svpct_10g",
            "goalie_shots_10g",
            "goalie_svpct_1g",
            "goalie_shots_1g",
        ]
    )
