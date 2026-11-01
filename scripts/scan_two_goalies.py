#!/usr/bin/env python3
"""Scan games for two goalies on the ice for one team at the same time.

Reads two things, since they can disagree: goalie shifts that overlap in the shift reports,
and plays whose on-ice goalie columns name two goalies. Give it a whole season, a team's
season, a list of games, or the save directories of earlier Scraper runs:

    uv run --frozen python scripts/scan_two_goalies.py --season 2024
    uv run --frozen python scripts/scan_two_goalies.py --season 2015 --team MTL
    uv run --frozen python scripts/scan_two_goalies.py --games 2023020001 2023020015
    uv run --frozen python scripts/scan_two_goalies.py --load /tmp/nsh /tmp/lak

The script exits 1 if it finds an overlap or a failed game, and 0 otherwise.
"""

import argparse
import sys
from pathlib import Path

import polars as pl

from chickenstats.chicken_nhl import Scraper, Season
from chickenstats.utilities import ChickenSession

PLAY_GOALIE_COLUMNS = ["home_goalie_api_id", "away_goalie_api_id"]


def shift_overlaps(shifts: pl.DataFrame) -> pl.DataFrame:
    """Return a row for each pair of goalies whose shifts on one team overlap, with the seconds they share."""
    goalies = shifts.filter(pl.col("position") == "G").select(
        "game_id", "team", "period", "api_id", start="start_time_seconds", end="end_time_seconds"
    )
    return (
        goalies.join(goalies, on=["game_id", "team", "period"], suffix="_other")
        .filter(pl.col("api_id") < pl.col("api_id_other"))
        .with_columns(seconds=pl.min_horizontal("end", "end_other") - pl.max_horizontal("start", "start_other"))
        .filter(pl.col("seconds") > 0)
        .select(
            "game_id", "team", "period", "api_id", "api_id_other", "start", "end", "start_other", "end_other", "seconds"
        )
        .sort("game_id", "period", "start")
    )


def two_goalie_plays(play_by_play: pl.DataFrame) -> pl.DataFrame:
    """Return the plays whose on-ice goalie columns name more than one goalie."""
    columns = [column for column in PLAY_GOALIE_COLUMNS if column in play_by_play.columns]
    named_twice = pl.any_horizontal(
        pl.col(column).cast(pl.String).str.contains(",", literal=True) for column in columns
    )
    return play_by_play.filter(named_twice).select(
        "game_id", "period", "period_seconds", "event", "event_team", *columns
    )


def game_ids_to_scan(args: argparse.Namespace, session: ChickenSession) -> list[int]:
    """Return the finished games the arguments name."""
    if args.games:
        return args.games
    season = Season(args.season, requests_session=session)
    schedule = season.schedule(args.team, sessions=["R", "P"], disable_progress_bar=True)
    return schedule.filter(pl.col("game_state").is_in(["OFF", "FINAL"]))["game_id"].sort().to_list()


def main() -> int:
    """Run the scan and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, nargs="+", help="game IDs to scrape")
    parser.add_argument("--season", help="season to scrape, as 2024 or 20242025")
    parser.add_argument("--team", help="only this team's games, with --season")
    parser.add_argument("--load", type=Path, nargs="+", help="directories saved by Scraper.save, in place of scraping")
    parser.add_argument("--rate", type=float, default=2.0, help="most NHL requests per second (default 2)")
    args = parser.parse_args()

    session = ChickenSession(max_requests_per_second=args.rate)
    if args.load:
        scrapers = [Scraper.load(path, disable_progress_bar=True, requests_session=session) for path in args.load]
    else:
        ids = game_ids_to_scan(args, session)
        scrapers = [Scraper(tuple(ids), disable_progress_bar=True, requests_session=session)]

    overlaps, plays, failed, games = [], [], [], 0
    for scraper in scrapers:
        shifts = scraper.shifts
        games += shifts["game_id"].n_unique()
        failed.extend(scraper.failed_games)
        overlaps.append(shift_overlaps(shifts))
        plays.append(two_goalie_plays(scraper.play_by_play))

    overlap = pl.concat(overlaps)
    play = pl.concat(plays)
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=160):
        print(f"{games} games scanned, {len(failed)} failed: {sorted(failed)}")
        print(f"{overlap.height} overlapping goalie shift pairs in {overlap['game_id'].n_unique()} games")
        if overlap.height:
            print(overlap)
        print(f"{play.height} plays naming two goalies in {play['game_id'].n_unique()} games")
        if play.height:
            print(play)

    return 1 if failed or overlap.height or play.height else 0


if __name__ == "__main__":
    sys.exit(main())
