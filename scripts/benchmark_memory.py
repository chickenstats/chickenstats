#!/usr/bin/env python3
"""Measure the peak memory of a full-season prep_stats.

Repeats a scraped week of games under new game IDs until it is a full season, then runs
one default prep_stats in this process and reports its peak RSS. Save the two frames first:

    scraper.play_by_play.write_parquet("pbp.parquet")
    scraper.play_by_play_ext.write_parquet("ext.parquet")
    benchmark_memory.py pbp.parquet ext.parquet --games 1312

Run it in a fresh process for each measurement, since peak RSS never falls.
"""

import argparse
import resource
import sys
import time

import polars as pl

from chickenstats.chicken_nhl import prep_stats

GIGABYTE = 1024**3
# ru_maxrss is in bytes on macOS and in kilobytes on Linux
RSS_UNIT = 1 if sys.platform == "darwin" else 1024
GAME_ID_STEP = 100_000
ID_DIGITS = 10_000


def peak_rss() -> float:
    """Return this process's peak resident memory, in gigabytes."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * RSS_UNIT / GIGABYTE


def repeat_games(df: pl.DataFrame, copies: int) -> pl.DataFrame:
    """Repeat the frame under new IDs. A row's id is its game_id followed by four digits."""
    frames = []
    for copy in range(copies):
        shifted = df.with_columns(pl.col("id") + copy * GAME_ID_STEP * ID_DIGITS)
        if "game_id" in df.columns:
            shifted = shifted.with_columns(pl.col("game_id") + copy * GAME_ID_STEP)
        frames.append(shifted)
    # Rechunked so the copies hold their own memory, as a real season's frames would
    return pl.concat(frames, rechunk=True)


def main() -> None:
    """Build the season and report what one default prep_stats takes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pbp", help="parquet file of play_by_play")
    parser.add_argument("ext", help="parquet file of play_by_play_ext")
    parser.add_argument("--games", type=int, default=1312, help="games in the season (default 1312)")
    args = parser.parse_args()

    pbp, ext = pl.read_parquet(args.pbp), pl.read_parquet(args.ext)
    copies = -(-args.games // pbp["game_id"].n_unique())
    pbp, ext = repeat_games(pbp, copies), repeat_games(ext, copies)
    print(f"{pbp['game_id'].n_unique()} games, {pbp.height} rows, loaded at {peak_rss():.2f} GB", flush=True)

    start = time.perf_counter()
    stats = prep_stats(pbp, ext)
    print(f"prep_stats: {stats.height} rows in {time.perf_counter() - start:.1f} s, peak {peak_rss():.2f} GB")


if __name__ == "__main__":
    main()
