"""Rebuild the score-and-venue adjustment table from the hosted play-by-play.

The method is Micah McCurdy's (https://www.hockeyviz.com/txt/senstats): within each strength state and score
state, a team's weight is the average of both sides' events divided by its own, so the total weight of events
in that situation is unchanged. Events are keyed exactly as ``calculate_score_adjustment`` and ``prepare_xg``
look them up: from the shooting team's side, with a disadvantage state counted under its mirror.

Usage:
    uv run python scripts/build_score_adjustments.py --cache ~/score_adjustment_pbp

Each season's download is kept in the ``--cache`` directory, so a rerun only fetches what is missing.
"""

import argparse
import gzip
import pickle
from pathlib import Path

import polars as pl

PAGE_SIZE = 50_000
SEASONS = [20192020, 20202021, 20212022, 20222023, 20232024, 20242025, 20252026]
TABLE = Path(__file__).parents[1] / "src/chickenstats/chicken_nhl/score_adjustments/score_adjustments.pkl.gz"

DISADVANTAGE_STATES = {"4v5": "5v4", "3v5": "5v3", "3v4": "4v3"}
STATES = ["5v5", "4v4", "3v3", "5v4", "5v3", "4v3"]
COUNTS = ["goal", "pred_goal", "shot", "miss", "block", "fenwick", "corsi"]
# Missed and blocked shots take the Fenwick and Corsi weights, as in calculate_score_adjustment
WEIGHTS = {"goal": "goal", "pred_goal": "pred_goal", "shot": "shot", "fenwick": "fenwick", "corsi": "corsi"}
COLUMNS = [
    "season",
    "session",
    "game_id",
    "event",
    "event_team",
    "opp_team",
    "is_home",
    "home_score_diff",
    "strength_state",
    "opp_strength_state",
    "teammate_block",
    "pred_goal",
    *[c for c in COUNTS if c != "pred_goal"],
]


def download(cache: Path) -> pl.DataFrame:
    """Regular-season goals, shots, misses and blocks for SEASONS, kept per season under the cache directory."""
    from chickenstats.api import ChickenStats

    cache.mkdir(parents=True, exist_ok=True)
    # Smaller pages, because one response for a full season can be cut off in transit
    client = ChickenStats(limit=PAGE_SIZE)
    frames = []
    for season in SEASONS:
        path = cache / f"{season}.parquet"
        if not path.exists():
            events = ["GOAL", "SHOT", "MISS", "BLOCK"]
            # One retry, because a page can still be cut off in transit
            try:
                df = client.download_pbp(season=[season], sessions=["R"], event=events)
            except ValueError:
                df = client.download_pbp(season=[season], sessions=["R"], event=events)
            frame = df if isinstance(df, pl.DataFrame) else pl.from_pandas(df)
            frame.select([c for c in COLUMNS if c in frame.columns]).write_parquet(path)
        frames.append(pl.read_parquet(path))

    return pl.concat(frames, how="diagonal_relaxed")


def score_group(strength_state: str) -> pl.Expr:
    """Score buckets from the home side: McCurdy's seven at 5v5, three at 4v4 and on the power play, one at 3v3.

    5v5 splits tied, 1, 2 and 3 or more each way. The other states have too few events for that, so 4v4 and the
    power play split only trailing, tied and leading, and 3v3, where the score barely changes play, is one bucket.
    """
    diff = pl.col("home_score_diff").clip(-3, 3)
    if strength_state == "5v5":
        return diff
    if strength_state == "3v3":
        return pl.lit(0, dtype=pl.Int64)
    return diff.sign()


def group_of(strength_state: str, diff: int) -> int:
    """The bucket score_group puts a home score difference in, for the table's per-difference keys."""
    if strength_state == "5v5":
        return diff
    if strength_state == "3v3":
        return 0
    return (diff > 0) - (diff < 0)


def keyed(pbp: pl.DataFrame) -> pl.DataFrame:
    """Each event's lookup key: the shooting team's state, mirrored on the penalty kill, and its side."""
    is_block = (pl.col("event") == "BLOCK") & (pl.col("teammate_block") == 0)
    # is_home is the event team's side, and a blocked shot's event team is the blocking team
    shooter_is_home = (pl.col("is_home") == 1) != is_block
    shooter_state = pl.when(is_block).then(pl.col("opp_strength_state")).otherwise(pl.col("strength_state"))
    disadvantage = shooter_state.is_in(list(DISADVANTAGE_STATES))

    return pbp.with_columns(
        state=pl.when(disadvantage).then(shooter_state.replace(DISADVANTAGE_STATES)).otherwise(shooter_state),
        is_home=shooter_is_home != disadvantage,
        pred_goal=pl.when(pl.col("event").is_in(["GOAL", "SHOT", "MISS"])).then(pl.col("pred_goal")).otherwise(0.0),
    ).filter(pl.col("state").is_in(STATES))


def build(pbp: pl.DataFrame) -> dict:
    """The table, in the shape load_score_adjustments returns: state -> home score difference -> fields."""
    events = keyed(pbp)
    table: dict = {}
    for state in STATES:
        grouped = (
            events.filter(pl.col("state") == state)
            .with_columns(group=score_group(state))
            .group_by("group", "is_home")
            .agg(pl.col(c).fill_null(0).sum() for c in COUNTS)
        )
        sums = {(row["group"], row["is_home"]): row for row in grouped.to_dicts()}

        table[state] = {}
        for diff in range(-3, 4):
            group = group_of(state, diff)
            home, away = sums[(group, True)], sums[(group, False)]
            label = "tied" if diff == 0 else ("leading" if diff > 0 else "trailing")
            fields: dict = {"score_diff_group": label}
            for count in COUNTS:
                fields[f"home_{count}"], fields[f"away_{count}"] = home[count], away[count]
            for name, count in WEIGHTS.items():
                mean = (home[count] + away[count]) / 2
                fields[f"home_{name}_weight"] = mean / home[count]
                fields[f"away_{name}_weight"] = mean / away[count]
            table[state][diff] = fields

    return table


def main() -> None:
    """Download the play-by-play if needed, build the table and write it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, required=True, help="Directory that keeps each season's download")
    parser.add_argument("--out", type=Path, default=TABLE, help="Where to write the table")
    args = parser.parse_args()

    table = build(download(args.cache.expanduser()))
    with gzip.open(args.out, "wb") as file:
        pickle.dump(table, file)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
