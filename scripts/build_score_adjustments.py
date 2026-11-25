"""Rebuild the score-and-venue adjustment table from the hosted play-by-play.

The even-strength method is Micah McCurdy's (https://www.hockeyviz.com/txt/senstats): within each strength
state and score state, a team's weight is the average of both sides' events divided by its own, so the total
weight of events in that situation is unchanged. That works because both sides share the same ice time.

On the power play (5v4, 5v3 and 4v3) the two sides of a score state are different game states, such as the home
team on the power play while trailing and the away team on the power play while the home team trails, with
different amounts of ice time. So a bucket's weight there is the state's event rate over the bucket's rate, with
the rate in events per minute of the bucket's own ice time. A bucket holds the power-play team's attempts and the
short-handed team's attempts, keyed by the power-play team's side, exactly as ``calculate_score_adjustment`` and
``prepare_xg`` look them up.

Goals take the Fenwick weight of their bucket, because goals are too few to weigh by themselves. A bucket with less
than MIN_TOI_MINUTES of ice time is shrunk toward its side's weight over every score state (the venue-only weight),
in proportion to its share of the minimum, and that venue-only weight is shrunk toward 1.0 the same way.

Usage:
    uv run python scripts/build_score_adjustments.py --cache ~/score_adjustment_pbp

Each season's download is kept in the ``--cache`` directory, so a rerun only fetches what is missing.
"""

import argparse
import json
from pathlib import Path

import polars as pl

SEASONS = [20192020, 20202021, 20212022, 20222023, 20232024, 20242025, 20252026]
TABLE = Path(__file__).parents[1] / "src/chickenstats/chicken_nhl/score_adjustments/score_adjustments.json"

# About 1,000 attempts at power-play rates, so a bucket's rate has a standard error near 3%
MIN_TOI_MINUTES = 600

DISADVANTAGE_STATES = {"4v5": "5v4", "3v5": "5v3", "3v4": "4v3"}
POWER_PLAY_STATES = ["5v4", "5v3", "4v3"]
STATES = ["5v5", "4v4", "3v3", *POWER_PLAY_STATES]
SHOT_EVENTS = ["GOAL", "SHOT", "MISS", "BLOCK"]
COUNTS = ["goal", "pred_goal", "shot", "miss", "block", "fenwick", "corsi"]
# Missed and blocked shots take the Fenwick and Corsi weights, as in calculate_score_adjustment, and goals Fenwick's
WEIGHTS = ["pred_goal", "shot", "fenwick", "corsi"]
COLUMNS = [
    "season",
    "session",
    "game_id",
    "event",
    "event_team",
    "opp_team",
    "is_home",
    "is_away",
    "home_score_diff",
    "strength_state",
    "opp_strength_state",
    "teammate_block",
    "event_length",
    "pred_goal",
    *[c for c in COUNTS if c != "pred_goal"],
]


def download(cache: Path) -> pl.DataFrame:
    """Every regular-season event for SEASONS, kept per season under the cache directory."""
    from chickenstats.api import ChickenStats

    cache.mkdir(parents=True, exist_ok=True)
    # No limit, so the client pages at the largest size the API allows on this route
    client = ChickenStats()
    frames = []
    for season in SEASONS:
        path = cache / f"{season}.parquet"
        # A cache from the shots-only build has no ice time
        if not path.exists() or "event_length" not in pl.read_parquet_schema(path):
            # One retry, because a page can still be cut off in transit
            try:
                df = client.download_pbp(season=[season], sessions=["R"])
            except ValueError:
                df = client.download_pbp(season=[season], sessions=["R"])
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
    """Each shot's lookup key: the shooting team's state, mirrored on the penalty kill, and its side."""
    is_block = (pl.col("event") == "BLOCK") & (pl.col("teammate_block") == 0)
    # is_home is the event team's side, and a blocked shot's event team is the blocking team
    shooter_is_home = (pl.col("is_home") == 1) != is_block
    shooter_state = pl.when(is_block).then(pl.col("opp_strength_state")).otherwise(pl.col("strength_state"))
    disadvantage = shooter_state.is_in(list(DISADVANTAGE_STATES))

    return (
        pbp.filter(pl.col("event").is_in(SHOT_EVENTS))
        .with_columns(
            state=pl.when(disadvantage).then(shooter_state.replace(DISADVANTAGE_STATES)).otherwise(shooter_state),
            is_home=shooter_is_home != disadvantage,
            pred_goal=pl.when(pl.col("event").is_in(["GOAL", "SHOT", "MISS"])).then(pl.col("pred_goal")).otherwise(0.0),
        )
        .filter(pl.col("state").is_in(STATES))
    )


def ice_time(pbp: pl.DataFrame) -> pl.DataFrame:
    """Each event's minutes under the same key, with the power-play team's side; at even strength the home side."""
    # strength_state is the event team's, and an event with no team is seen from the home side
    home_state = pl.when(pl.col("is_away") == 1).then(pl.col("opp_strength_state")).otherwise(pl.col("strength_state"))
    disadvantage = home_state.is_in(list(DISADVANTAGE_STATES))

    return pbp.select(
        "home_score_diff",
        state=pl.when(disadvantage).then(home_state.replace(DISADVANTAGE_STATES)).otherwise(home_state),
        is_home=~disadvantage,
        minutes=pl.col("event_length").fill_null(0) / 60,
    ).filter(pl.col("state").is_in(STATES))


def bucket_sums(frame: pl.DataFrame, state: str, columns: list[str]) -> dict:
    """Each column's total per (score group, is_home) bucket of one state."""
    grouped = (
        frame.filter(pl.col("state") == state)
        .with_columns(group=score_group(state))
        .group_by("group", "is_home")
        .agg(pl.col(c).fill_null(0).sum() for c in columns)
    )
    return {(row["group"], row["is_home"]): row for row in grouped.to_dicts()}


def shrink(weight: float, toward: float, minutes: float) -> float:
    """Move a weight toward another in proportion to how far its sample falls short of MIN_TOI_MINUTES."""
    return toward + min(1.0, minutes / MIN_TOI_MINUTES) * (weight - toward)


def state_weights(events: dict, minutes: dict, rate_based: bool) -> dict:
    """One state's weight for each (score group, is_home) bucket, from its events and minutes, after shrinkage.

    With rate_based, a weight is the state's events per minute over the bucket's. Otherwise it is the mean of the
    two sides' events in the score group over the bucket's own, and both sides of a group share its minutes.
    """
    buckets = sorted(events.keys() | minutes.keys())
    groups = sorted({group for group, _ in buckets})
    side_events = {side: sum(events.get((g, side), 0) for g in groups) for side in (True, False)}
    side_minutes = {side: sum(minutes.get((g, side), 0) for g in groups) for side in (True, False)}

    def ratio(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator else 1.0

    if rate_based:
        state_rate = ratio(sum(events.values()), sum(minutes.values()))
        raw = {b: ratio(state_rate * minutes.get(b, 0), events.get(b, 0)) for b in buckets}
        venue = {s: ratio(state_rate * side_minutes[s], side_events[s]) for s in side_events}
    else:
        mean = {g: (events.get((g, True), 0) + events.get((g, False), 0)) / 2 for g in groups}
        raw = {(g, s): ratio(mean[g], events.get((g, s), 0)) for g, s in buckets}
        venue = {s: ratio(sum(side_events.values()) / 2, side_events[s]) for s in side_events}

    venue = {s: shrink(venue[s], 1.0, side_minutes[s]) for s in venue}
    return {(g, s): shrink(raw[(g, s)], venue[s], minutes.get((g, s), 0)) for g, s in buckets}


def build(pbp: pl.DataFrame) -> dict:
    """The table, in the shape load_score_adjustments returns: state -> home score difference -> fields."""
    events, time = keyed(pbp), ice_time(pbp)
    table: dict = {}
    for state in STATES:
        counts = bucket_sums(events, state, COUNTS)
        rate_based = state in POWER_PLAY_STATES
        # At even strength both sides of a score group share its ice time
        group_minutes = {key: row["minutes"] for key, row in bucket_sums(time, state, ["minutes"]).items()}
        minutes = {
            (g, s): group_minutes.get((g, s if rate_based else True), 0.0)
            for g in {g for g, _ in counts.keys() | group_minutes.keys()}
            for s in (True, False)
        }
        weights = {
            name: state_weights({b: row[name] for b, row in counts.items()}, minutes, rate_based) for name in WEIGHTS
        }

        table[state] = {}
        for diff in range(-3, 4):
            group = group_of(state, diff)
            label = "tied" if diff == 0 else ("leading" if diff > 0 else "trailing")
            fields: dict = {"score_diff_group": label}
            for side, is_home in (("home", True), ("away", False)):
                bucket = (group, is_home)
                fields[f"{side}_toi"] = minutes.get(bucket, 0.0)
                for count in COUNTS:
                    fields[f"{side}_{count}"] = counts.get(bucket, {}).get(count, 0)
                for name in WEIGHTS:
                    fields[f"{side}_{name}_weight"] = weights[name].get(bucket, 1.0)
                fields[f"{side}_goal_weight"] = fields[f"{side}_fenwick_weight"]
            table[state][diff] = fields

    return table


def write_table(table: dict, path: Path) -> None:
    """Write the table as JSON, which keeps integers, floats and their exact values."""
    path.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Download the play-by-play if needed, build the table and write it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, required=True, help="Directory that keeps each season's download")
    parser.add_argument("--out", type=Path, default=TABLE, help="Where to write the table")
    args = parser.parse_args()

    write_table(build(download(args.cache.expanduser())), args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
