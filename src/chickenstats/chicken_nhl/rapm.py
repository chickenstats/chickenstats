"""RAPM design matrices: build_rapm_matrix, build_position_map.

Turns the output of ``prep_stints`` into the sparse design matrix a regularized
adjusted plus-minus (RAPM) regression needs. Requires the ``rapm`` extra
(``pip install chickenstats[rapm]``) — scipy is not installed by default.

Stops at the matrix: fitting the ridge is left to the caller, so any estimator taking
``X``, ``y``, and ``sample_weight`` will do.

Public functions:
    build_rapm_matrix: Stack stints into a sparse design matrix, target, and weights.
    build_position_map: Map player api_id to position and name from play-by-play.
"""

from __future__ import annotations

try:
    from scipy import sparse
except ImportError as exc:
    raise ImportError(
        "chickenstats.chicken_nhl.rapm requires the 'rapm' extra. Install with: pip install chickenstats[rapm]"
    ) from exc

from typing import Literal, NamedTuple

import numpy as np
import polars as pl

from chickenstats.exceptions import InvalidInputError

# Metrics build_rapm_matrix can target, matching prep_stints' home_/away_ stat columns.
RAPM_METRICS: tuple[str, ...] = ("xgf", "base_xgf", "context_xgf", "delta_xgf", "sf", "ff", "cf", "gf")

# Shot-volume metrics get the 7-bucket score state; xG and goals get the 3-bucket version.
_SHOT_VOLUME_METRICS: frozenset[str] = frozenset({"sf", "ff", "cf"})

# Number of single-column binary features: OZS, NZS, DZS, home advantage, back-to-back.
_SCALAR_FEATURES = 5

_INDEX_MAP_SCHEMA = {"player_team": pl.String, "idx": pl.Int64}


class RapmMatrix(NamedTuple):
    """Sparse design matrix and targets for a RAPM regression; unpacks positionally."""

    x: sparse.csr_matrix
    """Sparse binary design matrix, one row per stint-perspective."""
    y: np.ndarray
    """Per-60 rate of the target metric for each row."""
    weights: np.ndarray
    """TOI in seconds for each row — pass as ``sample_weight``."""
    dates: np.ndarray | None
    """Game date per row, or ``None`` when stints carried no ``game_date``."""
    players: list[str]
    """Sorted ``"{api_id}_{team}"`` keys. Index ``i`` is that player's offensive column;
    index ``i + len(players)`` is their defensive column."""
    player_metrics: pl.DataFrame
    """Per-player TOI and metric for/against totals, filtered to the ``min_toi`` floor."""


def build_position_map(df: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame:
    """Map each on-ice player's api_id to their position and name.

    Built from play-by-play, since stints carry only api_ids. Use it to label
    regression coefficients.

    Parameters:
        df (pl.DataFrame | pl.LazyFrame): Play-by-play DataFrame with ``home_on_api_id`` /
            ``away_on_api_id`` and their ``_positions`` and name counterparts.

    Returns:
        pl.DataFrame: Columns ``api_id``, ``position``, ``player``, one row per player.
    """
    lazy = df.lazy() if isinstance(df, pl.DataFrame) else df
    schema = lazy.collect_schema()

    frames = []
    for venue in ("home", "away"):
        sources = {"api_id": f"{venue}_on_api_id", "position": f"{venue}_on_positions", "player": f"{venue}_on"}
        # A parquet round-trip collapses these to comma-space String.
        selected = {
            alias: pl.col(source).str.split(", ") if schema.get(source) == pl.String else pl.col(source)
            for alias, source in sources.items()
        }
        frames.append(lazy.select(**selected).explode(["api_id", "position", "player"], empty_as_null=True))

    return pl.concat(frames).drop_nulls("api_id").unique("api_id").sort("api_id").collect()


def build_rapm_matrix(
    stints: pl.DataFrame, metric: str = "xgf", situation: Literal["EV", "PP", "SH", "all"] = "EV", min_toi: int = 1
) -> RapmMatrix:
    """Build a sparse design matrix for a RAPM ridge regression.

    Each stint contributes two rows, one per team's perspective, so every player gets an
    offensive column when their team is the perspective and a defensive column when not.

    Columns, in order: offensive skaters, defensive skaters, opposing goalies (only when
    ``metric='gf'``), strength state, OZS, NZS, DZS, home advantage, back-to-back, score
    state.

    Parameters:
        stints (pl.DataFrame): Output of ``prep_stints``.
        metric (str): Target stat — one of ``RAPM_METRICS``. Default ``'xgf'``.
        situation (str): ``'EV'`` for even strength, ``'PP'`` for the team with the
            skater advantage, ``'SH'`` for the shorthanded team, ``'all'`` for no
            filter. Default ``'EV'``.
        min_toi (int): Minimum minutes a player must have in this situation to get a
            column. Default ``1``.

    Returns:
        RapmMatrix: Design matrix, target, TOI weights, dates, player keys, and
        per-player metric totals.

    Raises:
        InvalidInputError: If ``metric`` is unknown or its columns aren't in ``stints``.

    Examples:
        >>> from chickenstats.chicken_nhl import Scraper, prep_stints
        >>> from chickenstats.chicken_nhl.rapm import build_rapm_matrix
        >>> scraper = Scraper(list(range(2023020001, 2023020011)))
        >>> matrix = build_rapm_matrix(prep_stints(scraper.play_by_play), metric="xgf")
    """
    if metric not in RAPM_METRICS:
        raise InvalidInputError(f"Unknown metric: {metric!r}. Expected one of {list(RAPM_METRICS)}.", obj=stints)

    for_col, against_col = f"home_{metric}", f"away_{metric}"
    missing = [col for col in (for_col, against_col) if col not in stints.columns]
    if missing:
        raise InvalidInputError(
            f"metric={metric!r} needs columns {missing}, which aren't in the stints "
            "DataFrame. The xG metrics are only built when the matching xG column was "
            "present in the play-by-play passed to prep_stints.",
            obj=stints,
        )

    has_date = "game_date" in stints.columns
    if has_date and stints.schema["game_date"] == pl.String:
        stints = stints.with_columns(pl.col("game_date").str.to_date(strict=False))
    date_col = [pl.col("game_date")] if has_date else [pl.lit(None).cast(pl.Date).alias("game_date")]

    score_col = "score_7" if metric in _SHOT_VOLUME_METRICS else "score_3"

    def _perspective(venue: str, opponent: str, home_adv: int) -> pl.DataFrame:
        """Select one venue's perspective, renaming its side to offense."""
        return stints.select(
            [
                pl.col("toi"),
                (pl.col(f"{venue}_{metric}") / (pl.col("toi") / 3600)).alias("y"),
                pl.col(f"{venue}_{metric}").cast(pl.Float64).alias("metric_for"),
                pl.col(f"{opponent}_{metric}").cast(pl.Float64).alias("metric_against"),
                pl.col(f"{venue}_skaters").alias("offense"),
                pl.col(f"{opponent}_skaters").alias("defense"),
                pl.col(f"{opponent}_goalies").alias("goalie_def"),
                pl.col(f"{venue}_team").alias("off_team"),
                pl.col(f"{opponent}_team").alias("def_team"),
                pl.col("strength_state"),
                pl.col("ozs"),
                pl.col("nzs"),
                pl.col("dzs"),
                pl.col(f"{venue}_b2b").alias("b2b"),
                pl.col(f"{venue}_{score_col}").alias("score_state"),
                pl.lit(home_adv).alias("home_adv"),
                pl.col(f"{venue}_skater_count").alias("off_cnt"),
                pl.col(f"{opponent}_skater_count").alias("def_cnt"),
            ]
            + date_col
        )

    stacked = pl.concat([_perspective("home", "away", 1), _perspective("away", "home", 0)])

    # Filter AFTER stacking, on each perspective's own counts. Pre-stack, the home/away
    # counts only reveal that a stint was unequal-strength, not which side had the
    # advantage, so PP and SH would resolve to the same filter.
    if situation == "EV":
        stacked = stacked.filter(pl.col("off_cnt") == pl.col("def_cnt"))
    elif situation == "PP":
        stacked = stacked.filter(pl.col("off_cnt") > pl.col("def_cnt"))
    elif situation == "SH":
        stacked = stacked.filter(pl.col("off_cnt") < pl.col("def_cnt"))

    # Assigned after the filter so row_idx stays contiguous and matches the matrix shape.
    stacked = stacked.with_row_index("row_idx")

    # Built from the same filtered frame, so the TOI floor is scoped to the situation.
    player_metrics = (
        stacked.select(
            [
                pl.col("offense").alias("player"),
                pl.col("off_team").alias("team"),
                pl.col("toi"),
                pl.col("metric_for"),
                pl.col("metric_against"),
            ]
        )
        .explode("player", empty_as_null=True)
        .drop_nulls("player")
        .with_columns(player_team=pl.col("player") + "_" + pl.col("team"))
        .group_by("player_team")
        .agg([pl.col("toi").sum(), pl.col("metric_for").sum(), pl.col("metric_against").sum()])
        .filter(pl.col("toi") >= (min_toi * 60))
    )

    # One skater list drives both column ranges; the offset picks which range.
    skater_list = sorted(player_metrics["player_team"].to_list())
    num_skaters = len(skater_list)
    # Explicit schema so an empty list (every player under min_toi) still joins as String.
    offense_map = pl.DataFrame({"player_team": skater_list, "idx": list(range(num_skaters))}, schema=_INDEX_MAP_SCHEMA)
    defense_map = pl.DataFrame(
        {"player_team": skater_list, "idx": list(range(num_skaters, num_skaters * 2))}, schema=_INDEX_MAP_SCHEMA
    )

    if metric == "gf":
        goalies = (
            stacked.select(pl.col("goalie_def").alias("goalie"), pl.col("def_team").alias("team"))
            .explode("goalie", empty_as_null=True)
            .drop_nulls("goalie")
            .with_columns(goalie_team=pl.col("goalie") + "_" + pl.col("team"))
        )
        goalie_list = sorted(goalies["goalie_team"].unique().to_list())
    else:
        goalie_list = []

    goalie_map = pl.DataFrame(
        {"goalie_team": goalie_list, "idx": list(range(num_skaters * 2, (num_skaters * 2) + len(goalie_list)))},
        schema={"goalie_team": pl.String, "idx": pl.Int64},
    )

    # offset tracks the next free column index as each feature group is added.
    offset = (num_skaters * 2) + len(goalie_list)
    strengths = sorted(stacked["strength_state"].drop_nulls().unique().to_list())
    strength_idx = {value: offset + i for i, value in enumerate(strengths)}
    offset += len(strengths)

    idx_ozs, idx_nzs, idx_dzs, idx_home_adv, idx_b2b = (offset + i for i in range(_SCALAR_FEATURES))
    offset += _SCALAR_FEATURES

    score_levels = [-3, -2, -1, 1, 2, 3] if metric in _SHOT_VOLUME_METRICS else [-1, 1]
    score_idx = {level: offset + i for i, level in enumerate(score_levels)}

    # Build (row, col) coordinate lists — every value in the matrix is 1.
    all_rows: list[np.ndarray] = []
    all_cols: list[np.ndarray] = []

    lineups = [("offense", "off_team", offense_map, "player_team"), ("defense", "def_team", defense_map, "player_team")]
    if metric == "gf":
        lineups.append(("goalie_def", "def_team", goalie_map, "goalie_team"))

    for list_col, team_col, index_map, key in lineups:
        exploded = (
            stacked.select("row_idx", list_col, team_col)
            .explode(list_col, empty_as_null=True)
            .drop_nulls(list_col)
            .with_columns(**{key: pl.col(list_col) + "_" + pl.col(team_col)})
            .join(index_map, on=key, how="inner")
        )
        all_rows.append(exploded["row_idx"].to_numpy())
        all_cols.append(exploded["idx"].to_numpy())

    for column, mapping in (("strength_state", strength_idx), ("score_state", score_idx)):
        mapped = (
            stacked.select("row_idx", column)
            .with_columns(idx=pl.col(column).replace_strict(mapping, default=None))
            .drop_nulls("idx")
        )
        all_rows.append(mapped["row_idx"].to_numpy())
        all_cols.append(mapped["idx"].to_numpy())

    for flag, index in (
        (pl.col("ozs"), idx_ozs),
        (pl.col("nzs"), idx_nzs),
        (pl.col("dzs"), idx_dzs),
        (pl.col("home_adv") == 1, idx_home_adv),
        (pl.col("b2b"), idx_b2b),
    ):
        rows = stacked.filter(flag).select("row_idx")
        all_rows.append(rows["row_idx"].to_numpy())
        all_cols.append(np.full(len(rows), index, dtype=np.intp))

    y = stacked["y"].fill_nan(0.0).to_numpy()
    weights = stacked["toi"].to_numpy()
    dates = stacked["game_date"].to_numpy() if has_date else None

    rows_array = np.concatenate(all_rows)
    cols_array = np.concatenate(all_cols)
    data = np.ones(len(rows_array), dtype=np.float32)

    x = sparse.coo_matrix(
        (data, (rows_array, cols_array)), shape=(len(y), offset + len(score_levels)), dtype=np.float32
    ).tocsr()

    return RapmMatrix(x=x, y=y, weights=weights, dates=dates, players=skater_list, player_metrics=player_metrics)
