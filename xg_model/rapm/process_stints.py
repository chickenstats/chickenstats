from pathlib import Path
from typing import cast

import polars as pl

from chickenstats.utilities import track


def process_pbp_metadata(lazy_pbp: pl.LazyFrame) -> pl.DataFrame:
    """Computes rest days."""
    games = cast(pl.DataFrame, lazy_pbp.select(["game_id", "game_date", "home_team", "away_team"]).unique().collect())
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
        is_b2b=pl.when((pl.col("game_date") - pl.col("game_date").shift(1)).over("team").dt.total_days() == 1)
        .then(True)
        .otherwise(False)
    )

    meta_lookup = (
        games.join(
            team_schedule.select(["game_id", "team", "is_b2b"]),
            left_on=["game_id", "home_team"],
            right_on=["game_id", "team"],
        )
        .rename({"is_b2b": "h_b2b"})
        .join(
            team_schedule.select(["game_id", "team", "is_b2b"]),
            left_on=["game_id", "away_team"],
            right_on=["game_id", "team"],
        )
        .rename({"is_b2b": "a_b2b"})
        .select(["game_id", "h_b2b", "a_b2b"])
    )

    return meta_lookup


def aggregate_stints_df(pbp_df: pl.DataFrame, meta_lookup: pl.DataFrame) -> pl.DataFrame:
    """Aggregate play-by-play data to a stints-level dataframe."""
    # Join the back-to-back play-by-play metadata to the dataframe
    df = pbp_df.join(meta_lookup, on="game_id", how="left")

    # Create 7-bucket and 3-bucket categories for score differential
    df = df.with_columns(
        h_s7=(
            pl.when(pl.col("home_score_diff") <= -3)
            .then(-3)
            .when(pl.col("home_score_diff") >= 3)
            .then(3)
            .otherwise(pl.col("home_score_diff"))
        ),
        h_s3=(pl.when(pl.col("home_score_diff") < 0).then(-1).when(pl.col("home_score_diff") > 0).then(1).otherwise(0)),
    ).with_columns(a_s7=-pl.col("h_s7"), a_s3=-pl.col("h_s3"))

    # Adding a stint_id column to the dataframe for aggregation purposes
    df = df.with_columns(
        stint_id=(
            (
                (pl.col("home_on_eh_id") != pl.col("home_on_eh_id").shift(1))
                | (pl.col("away_on_eh_id") != pl.col("away_on_eh_id").shift(1))
            )
            .fill_null(True)
            .cast(pl.Int32)
            .cum_sum()
            .over(["game_id", "period"])
        )
    )

    # Aggregating the stints dataframe
    stints = df.group_by(["season", "session", "game_id", "period", "stint_id"]).agg(
        toi=pl.col("event_length").sum(),
        h_xgf=(pl.col("pred_goal") * (pl.col("event_team") == pl.col("home_team"))).sum(),
        a_xgf=(pl.col("pred_goal") * (pl.col("event_team") == pl.col("away_team"))).sum(),
        h_cf=(
            pl.col("event").is_in(["SHOT", "MISS", "BLOCK", "GOAL"]) & (pl.col("event_team") == pl.col("home_team"))
        ).sum(),
        a_cf=(
            pl.col("event").is_in(["SHOT", "MISS", "BLOCK", "GOAL"]) & (pl.col("event_team") == pl.col("away_team"))
        ).sum(),
        h_gf=((pl.col("event") == "GOAL") & (pl.col("event_team") == pl.col("home_team"))).sum(),
        a_gf=((pl.col("event") == "GOAL") & (pl.col("event_team") == pl.col("away_team"))).sum(),
        h_ids=pl.col("home_on_eh_id").first().str.split(", "),
        a_ids=pl.col("away_on_eh_id").first().str.split(", "),
        h_goalie_ids=pl.col("home_goalie_eh_id").cast(pl.Utf8).fill_null("").first().str.split(","),
        a_goalie_ids=pl.col("away_goalie_eh_id").cast(pl.Utf8).fill_null("").first().str.split(","),
        h_team=pl.col("home_team").first(),
        a_team=pl.col("away_team").first(),
        h_s3=pl.col("h_s3").first(),
        h_s7=pl.col("h_s7").first(),
        a_s3=pl.col("a_s3").first(),
        a_s7=pl.col("a_s7").first(),
        h_b2b=pl.col("h_b2b").first(),
        a_b2b=pl.col("a_b2b").first(),
        strength=pl.col("strength_state").first(),
        ozs=pl.col("zone_start").is_in(["OFF"]).any(),
        nzs=pl.col("zone_start").is_in(["NEU"]).any(),
        dzs=pl.col("zone_start").is_in(["DEF"]).any(),
    )

    # Drop 0-second events and lists
    stints = stints.filter(pl.col("toi") > 0)

    # Remove goalies from home and away skaters, plus replace nulls with empty lists
    stints = stints.with_columns(
        h_skaters=pl.col("h_ids").list.set_difference(pl.col("h_goalie_ids")).fill_null([]),
        a_skaters=pl.col("a_ids").list.set_difference(pl.col("a_goalie_ids")).fill_null([]),
        h_goalies=pl.col("h_goalie_ids").fill_null([]),
        a_goalies=pl.col("a_goalie_ids").fill_null([]),
    )

    # Count home and away skaters after removing goalies
    stints = stints.with_columns(h_cnt=pl.col("h_skaters").list.len(), a_cnt=pl.col("a_skaters").list.len())

    # Filter out stings with fewer than three skaters
    stints = stints.filter((pl.col("h_skaters").list.len() >= 3) & (pl.col("a_skaters").list.len() >= 3))

    return stints


def main():
    """Function to fully process RAPM data."""
    pbp_path = Path(__file__).parent / "data/raw/pbp.parquet"

    # Reading play-by-play data as a lazyframe
    lazy_pbp = pl.scan_parquet(pbp_path)

    # Processing data into lookup file back-to-back games
    meta_lookup = process_pbp_metadata(lazy_pbp)

    # Getting the seasons to iterate through
    seasons = sorted(cast(pl.DataFrame, lazy_pbp.select(pl.col("season")).unique().collect())["season"].to_list())

    # Iterating through the seasons and saving data as a parquet file
    for season in track(seasons, description="Processing play-by-play data for RAPM regressions..."):
        # Iterating through the different sessions
        for session in ["R", "P"]:
            # Filter play-by-play data for the current season
            season_pbp = cast(
                pl.DataFrame, lazy_pbp.filter(pl.col("season") == season, pl.col("session") == session).collect()
            )

            # Aggregating to stints
            stints = aggregate_stints_df(pbp_df=season_pbp, meta_lookup=meta_lookup)

            # Saving data
            save_file = Path(__file__).parent / f"data/processed/stints_{str(season)[:4]}_{session.lower()}.parquet"
            stints.write_parquet(save_file, mkdir=True)


if __name__ == "__main__":
    main()
