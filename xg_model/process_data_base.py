from pathlib import Path
from typing import Literal, cast

from rich.progress import TaskID

import polars as pl

from chickenstats.chicken_nhl.validation_polars import pbp_polars_schema
from xg import prep_data
from chickenstats.utilities import ChickenProgress

HOLD_OUT_YEAR = 2024

_StrengthArg = Literal["even", "powerplay", "shorthanded", "empty_for", "empty_against"]

STRENGTH_FILE_ARGS: list[tuple[str, _StrengthArg]] = [
    ("even_strength", "even"),
    ("powerplay", "powerplay"),
    ("shorthanded", "shorthanded"),
    ("empty_for", "empty_for"),
    ("empty_against", "empty_against"),
]

# Columns needed by prep_data from the raw PBP
_PREP_DATA_COLS = [
    "event",
    "strength_state",
    "coords_x",
    "coords_y",
    "season",
    "game_id",
    "period",
    "period_seconds",
    "game_seconds",
    "event_team",
    "event_distance",
    "event_angle",
    "shot_type",
    "player_1_position",
    "is_home",
    "score_diff",
    "zone",
    "danger",
    "high_danger",
    "goal",
    "player_1_api_id",  # passthrough — needed by informed_xg for GxG/RAPM join
    "opp_goalie_api_id",  # passthrough — needed by informed_xg for GSAx/RAPM join
    "session",  # needed for hold-out split logic
    "home_on_api_id",  # passthrough — needed by process_data_inf.py for teammates RAPM
    "away_on_api_id",  # passthrough — needed by process_data_inf.py for teammates RAPM
]

READ_COLS = list(dict.fromkeys(_PREP_DATA_COLS))
READ_SCHEMA_OVERRIDES = {k: v for k, v in pbp_polars_schema.items() if k in READ_COLS}


def main():
    """Builds stateless base_xg training data from raw PBP CSVs.

    Features are entirely stateless — no player IDs or rolling metrics are used.
    Passthrough columns (game_id, player_1_api_id, opp_goalie_api_id) are kept in
    the output parquets for use by the informed_xg pipeline but are excluded from
    the training feature matrix in experiments.py.

    Output: data/base_xg/train/ and data/base_xg/hold_out/
    """
    years: list[int] = list(range(HOLD_OUT_YEAR, 2009, -1))

    raw_by_year: dict[int, pl.DataFrame] = {}

    with ChickenProgress(speed_estimate_period=300, transient=True) as progress:
        progress_task: TaskID = progress.add_task("Reading raw play-by-play data...", total=len(years))

        for year in years:
            progress.update(progress_task, description=f"Reading {year}...", refresh=True)
            filepath: Path = Path(__file__).parent / "data" / "raw" / f"pbp_{year}.csv"
            raw_by_year[year] = pl.read_csv(filepath, columns=READ_COLS, schema_overrides=READ_SCHEMA_OVERRIDES)
            progress.update(progress_task, advance=1, refresh=True)

        progress.update(progress_task, description="Finished reading raw data", refresh=True)

    combined = cast(
        pl.DataFrame,
        pl.concat(
            [pbp.with_columns(pl.lit(year).alias("_year")) for year, pbp in raw_by_year.items()], how="diagonal_relaxed"
        )
        .lazy()
        .sort(["season", "game_id", "game_seconds"])
        .collect(),
    )
    del raw_by_year

    hold_out_season: int = combined.filter(pl.col("_year") == HOLD_OUT_YEAR)["season"][0]

    accumulators: dict[str, list[pl.DataFrame]] = {name: [] for name, _ in STRENGTH_FILE_ARGS}

    with ChickenProgress(speed_estimate_period=300, transient=True) as progress:
        progress_task = progress.add_task("Prepping base_xg features...", total=len(years))

        for year in years:
            progress.update(progress_task, description=f"Prepping {year}...", refresh=True)

            for file_name, strength_arg in STRENGTH_FILE_ARGS:
                accumulators[file_name].append(
                    prep_data(combined.filter(pl.col("_year") == year).drop("_year"), strength_arg)
                )

            progress.update(progress_task, advance=1, refresh=True)

        progress.update(progress_task, description="Finished prepping base_xg data", refresh=True)

    del combined

    dfs: dict[str, pl.DataFrame] = {
        name: pl.concat(year_dfs, how="diagonal") for name, year_dfs in accumulators.items()
    }

    hold_out_dir: Path = Path(__file__).parent / "data" / "base_xg" / "hold_out"
    train_dir: Path = Path(__file__).parent / "data" / "base_xg" / "train"
    hold_out_dir.mkdir(parents=True, exist_ok=True)
    train_dir.mkdir(parents=True, exist_ok=True)

    for name, df in dfs.items():
        df = df.sort(["season", "game_id", "period", "period_seconds"])
        df.filter(pl.col("season") == hold_out_season).write_parquet(hold_out_dir / f"{name}.parquet")
        df.filter(pl.col("season") != hold_out_season).write_parquet(train_dir / f"{name}.parquet")


if __name__ == "__main__":
    main()
