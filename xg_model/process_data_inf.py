"""Assemble informed_xg training data from scored env_xg parquets.

Pipeline:
  1. Load all 5 scored env_xg parquets (from data/env_xg/scored/), tagged with RAPM situation
  2. Sort chronologically and call compute_rolling_stats → adds 16 GxG/GSAx columns
  3. Load RAPM table (from data/informed_xg/rapm/rapm_by_season.parquet)
  4. Join shooter RAPM (lagged 1 season, situation-matched)
  5. Join opp goalie RAPM (lagged 1 season, situation-matched)
  6. Compute teammates RAPM (explode on-ice IDs, exclude shooter, mean of lagged RAPM)
  7. Split by hold-out season and save to data/informed_xg/train/ + hold_out/

Usage:
    python process_data_inf.py
"""

from pathlib import Path
from typing import cast

import polars as pl
from rich.progress import track

from chickenstats.utilities import ChickenProgressIndeterminate

from compute_rolling_stats import compute_rolling_stats

HOLD_OUT_SEASON = 20242025

# Map each scored parquet → RAPM situation used for joins
STRENGTH_RAPM_SITUATION: dict[str, str] = {
    "even_strength": "EV",
    "powerplay": "PP",
    "shorthanded": "SH",
    "empty_for": "EV",
    "empty_against": "EV",
}

# Minimum teammates with prior-season RAPM required to compute a teammates mean
MIN_TEAMMATES_WITH_RAPM = 2


def _load_scored_parquets(scored_dir: Path) -> pl.DataFrame:
    """Load all 5 strength scored parquets and tag with RAPM situation."""
    frames = []
    for strength, situation in STRENGTH_RAPM_SITUATION.items():
        df = pl.read_parquet(scored_dir / f"{strength}.parquet").with_columns(
            pl.lit(situation).alias("_rapm_situation")
        )
        frames.append(df)
    return (
        pl.concat(frames, how="diagonal_relaxed").sort(["season", "game_id", "period", "period_seconds"]).collect()
        if False  # concat returns DataFrame, not LazyFrame
        else pl.concat(frames, how="diagonal_relaxed").sort(["season", "game_id", "period", "period_seconds"])
    )


def _load_rapm(rapm_path: Path) -> pl.DataFrame:
    """Load and deduplicate RAPM table to one row per (player, season, situation).

    Takes the entry with the highest TOI when a player appears for multiple teams.
    Uses regular-season (session='R') coefficients only for lagged joins.
    """
    rapm = pl.read_parquet(rapm_path)

    # Keep only regular season, select minimal columns
    rapm = rapm.filter(pl.col("session") == "R").select(
        ["player", "season", "situation", "toi_minutes", "off_coeff_env_xg", "def_coeff_env_xg"]
    )

    # When a player appears for multiple teams, take the one with most TOI
    rapm = (
        rapm.sort("toi_minutes", descending=True)
        .unique(subset=["player", "season", "situation"], keep="first")
        .drop("toi_minutes")
    )

    # Cast player to Int64 to match player_1_api_id / opp_goalie_api_id types
    return rapm.with_columns(pl.col("player").cast(pl.Int64))


def _join_shooter_rapm(df: pl.DataFrame, rapm: pl.DataFrame) -> pl.DataFrame:
    """Join shooter's prior-season, situation-matched RAPM."""
    rapm_shooter = rapm.rename(
        {"player": "player_1_api_id", "off_coeff_env_xg": "shooter_rapm_off", "def_coeff_env_xg": "shooter_rapm_def"}
    )
    # Lagged: join season S data to season S-1 RAPM
    df = df.with_columns((pl.col("season") - 10000).alias("_prev_season"))
    df = df.join(
        rapm_shooter,
        left_on=["player_1_api_id", "_prev_season", "_rapm_situation"],
        right_on=["player_1_api_id", "season", "situation"],
        how="left",
    )
    return df.drop("_prev_season")


def _join_opp_rapm(df: pl.DataFrame, rapm: pl.DataFrame) -> pl.DataFrame:
    """Join opposing goalie's prior-season, situation-matched RAPM."""
    rapm_opp = rapm.rename(
        {"player": "opp_goalie_api_id", "off_coeff_env_xg": "opp_rapm_off", "def_coeff_env_xg": "opp_rapm_def"}
    )
    df = df.with_columns((pl.col("season") - 10000).alias("_prev_season"))
    df = df.join(
        rapm_opp,
        left_on=["opp_goalie_api_id", "_prev_season", "_rapm_situation"],
        right_on=["opp_goalie_api_id", "season", "situation"],
        how="left",
    )
    return df.drop("_prev_season")


def _compute_teammates_rapm(df: pl.DataFrame, rapm: pl.DataFrame) -> pl.DataFrame:
    """Compute mean RAPM of on-ice teammates, excluding the shooter.

    Uses home_on_api_id when is_home == 1, away_on_api_id otherwise.
    Goalies naturally receive null (not in env_xg RAPM) and are excluded from the mean.
    Events with fewer than MIN_TEAMMATES_WITH_RAPM valid entries receive null.
    """
    # Add row index for joining back
    df = df.with_row_index("_row_idx")

    # Select the relevant on-ice column based on is_home
    # Result: one row per event, one column "_on_ice_ids" with the comma-separated string
    on_ice = df.select(
        [
            "_row_idx",
            "player_1_api_id",
            "season",
            "_rapm_situation",
            pl.when(pl.col("is_home") == 1)
            .then(pl.col("home_on_api_id"))
            .otherwise(pl.col("away_on_api_id"))
            .alias("_on_ice_ids"),
        ]
    )

    # Explode into one row per on-ice player
    on_ice = (
        on_ice.with_columns(pl.col("_on_ice_ids").str.split(", ").alias("_ids_list"))
        .explode("_ids_list")
        .filter(pl.col("_ids_list").is_not_null() & (pl.col("_ids_list") != ""))
        .with_columns(pl.col("_ids_list").cast(pl.Int64).alias("_teammate_id"))
        .drop(["_on_ice_ids", "_ids_list"])
    )

    # Exclude the shooter
    on_ice = on_ice.filter(pl.col("_teammate_id") != pl.col("player_1_api_id"))

    # Lagged RAPM join for each teammate
    rapm_teammates = rapm.rename(
        {"player": "_teammate_id", "off_coeff_env_xg": "_tm_rapm_off", "def_coeff_env_xg": "_tm_rapm_def"}
    )
    on_ice = on_ice.with_columns((pl.col("season") - 10000).alias("_prev_season"))
    on_ice = on_ice.join(
        rapm_teammates,
        left_on=["_teammate_id", "_prev_season", "_rapm_situation"],
        right_on=["_teammate_id", "season", "situation"],
        how="left",
    ).drop("_prev_season")

    # Mean RAPM per event, null if fewer than MIN_TEAMMATES_WITH_RAPM have data
    teammates_mean = (
        on_ice.group_by("_row_idx")
        .agg(
            pl.col("_tm_rapm_off").drop_nulls().mean().alias("_tm_off_mean"),
            pl.col("_tm_rapm_off").drop_nulls().len().alias("_tm_count"),
            pl.col("_tm_rapm_def").drop_nulls().mean().alias("_tm_def_mean"),
        )
        .with_columns(
            pl.when(pl.col("_tm_count") >= MIN_TEAMMATES_WITH_RAPM)
            .then(pl.col("_tm_off_mean"))
            .otherwise(None)
            .alias("teammates_rapm_off"),
            pl.when(pl.col("_tm_count") >= MIN_TEAMMATES_WITH_RAPM)
            .then(pl.col("_tm_def_mean"))
            .otherwise(None)
            .alias("teammates_rapm_def"),
        )
        .select(["_row_idx", "teammates_rapm_off", "teammates_rapm_def"])
    )

    df = df.join(teammates_mean, on="_row_idx", how="left")
    return df.drop("_row_idx")


def main() -> None:
    """Assemble informed_xg training and hold-out data."""
    data_dir = Path(__file__).parent / "data"
    scored_dir = data_dir / "env_xg" / "scored"
    rapm_path = data_dir / "informed_xg" / "rapm" / "rapm_by_season.parquet"

    # 1. Load and combine scored parquets
    frames = []
    for strength, situation in track(STRENGTH_RAPM_SITUATION.items(), description="Loading scored parquets..."):
        df = pl.read_parquet(scored_dir / f"{strength}.parquet").with_columns(
            pl.lit(situation).alias("_rapm_situation")
        )
        frames.append(df)

    combined = cast(
        pl.DataFrame, pl.concat(frames, how="diagonal_relaxed").sort(["season", "game_id", "period", "period_seconds"])
    )
    del frames

    # 2. Rolling GxG / GSAx
    with ChickenProgressIndeterminate(transient=True) as progress:
        task = progress.add_task("Computing rolling GxG / GSAx...", total=None)
        progress.start_task(task)
        combined = compute_rolling_stats(combined)
        progress.update(task, total=1, advance=1, description="Finished computing rolling stats", refresh=True)

    # 3. RAPM joins
    rapm = _load_rapm(rapm_path)
    combined = _join_shooter_rapm(combined, rapm)
    combined = _join_opp_rapm(combined, rapm)
    combined = _compute_teammates_rapm(combined, rapm)

    # Drop internal columns before saving
    combined = combined.drop(["_rapm_situation"])

    # 4. Split and save
    train_dir = data_dir / "informed_xg" / "train"
    hold_out_dir = data_dir / "informed_xg" / "hold_out"
    train_dir.mkdir(parents=True, exist_ok=True)
    hold_out_dir.mkdir(parents=True, exist_ok=True)

    strengths = list(STRENGTH_RAPM_SITUATION.keys())
    strength_state_map = {
        "even_strength": ["5v5", "4v4", "3v3"],
        "powerplay": ["5v4", "4v3", "5v3"],
        "shorthanded": ["4v5", "3v4", "3v5"],
        "empty_for": ["Ev5", "Ev4", "Ev3"],
        "empty_against": ["5vE", "4vE", "3vE"],
    }

    for strength in track(strengths, description="Saving informed_xg parquets..."):
        states = strength_state_map[strength]
        subset = combined.filter(pl.col("strength_state").is_in(states))
        subset.filter(pl.col("season") == HOLD_OUT_SEASON).write_parquet(hold_out_dir / f"{strength}.parquet")
        subset.filter(pl.col("season") != HOLD_OUT_SEASON).write_parquet(train_dir / f"{strength}.parquet")


if __name__ == "__main__":
    main()
