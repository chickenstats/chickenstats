"""Rolling goals above expected: each shooter's and goalie's recent finishing against an xG model.

Shooters take goals minus expected goals (GxG) and goalies expected goals minus goals (GSAx),
both over the same rows: Fenwick events in the modeled strength states. Every value looks only
backward, so a shot's own result never feeds its features.

    prep_rolling_gax         the six features on every row of a play-by-play history
    prep_rolling_gax_games   one row per player-game: the values entering it and the state after
    latest_rolling_state     each player's last game, the state the live path starts from
    continue_rolling_gax     the same features for live shots, carried from that state

Attributes:
    EWMA_HALF_LIFE: Shots back at which a shot keeps half its weight in the EWMA.
    FORM_GAMES: Games in the trailing window of the 10-game features.
    MODELLED_STRENGTH_STATES: The strength states the features count, with the event types
        in ``contract.FENWICK_EVENTS``.
    SHOOTER_ID_COL: The column that names the shooter.
    GOALIE_ID_COL: The column that names the goalie facing the shot.
    ROLLING_GAX_COLUMNS: The six feature columns.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, overload

import numpy as np
import polars as pl

from chickenstats.chicken_nhl import contract
from chickenstats.chicken_nhl._aggregation import _output_backend
from chickenstats.chicken_nhl.contract import sort_chronological
from chickenstats.exceptions import InvalidInputError
from chickenstats.utilities.utilities import _to_backend, _to_polars

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    from chickenstats.utilities.types import (
        DataFrameT,
        InputFrameT,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )

__all__ = [
    "EWMA_HALF_LIFE",
    "FORM_GAMES",
    "GOALIE_ID_COL",
    "MODELLED_STRENGTH_STATES",
    "ROLLING_GAX_COLUMNS",
    "SHOOTER_ID_COL",
    "continue_rolling_gax",
    "latest_rolling_state",
    "prep_rolling_gax",
    "prep_rolling_gax_games",
]

EWMA_HALF_LIFE = 50
"""A shot this many shots back keeps half its weight in the ``_ewma`` features."""

FORM_GAMES = 10
"""Games in the trailing window of the ``_10g`` and ``_per_shot_10g`` features."""

_FENWICK_EVENTS: tuple[str, ...] = tuple(sorted(contract.FENWICK_EVENTS))

MODELLED_STRENGTH_STATES: frozenset[str] = frozenset(
    {
        *("5v5", "4v4", "3v3"),
        *("5v4", "4v3", "5v3"),
        *("4v5", "3v4", "3v5"),
        *("Ev5", "Ev4", "Ev3"),
        *("5vE", "4vE", "3vE"),
    }
)
"""Even strength, power play, shorthanded and either empty net. 6v5 and other illegal counts,
EvE, and penalty shots and shootout attempts (1v0, 0v1) are left out."""

SHOOTER_ID_COL = "player_1_api_id"
GOALIE_ID_COL = "opp_goalie_api_id"

ROLLING_GAX_COLUMNS: tuple[str, ...] = (
    "shooter_gax_ewma",
    "shooter_gax_10g",
    "shooter_gax_per_shot_10g",
    "goalie_gsax_ewma",
    "goalie_gsax_10g",
    "goalie_gsax_per_shot_10g",
)
"""The six columns ``prep_rolling_gax`` and ``continue_rolling_gax`` add."""

_REQUIRED = (
    "goal",
    SHOOTER_ID_COL,
    GOALIE_ID_COL,
    "season",
    "session",
    "game_date",
    "game_id",
    "event_idx",
    "event",
    "fenwick",
    "strength_state",
)
_STATE_COLUMNS = ("ewma_after", "shots_after", "10g_after", "shots_10g_after")
_LIVE_COLS = ("ewma", "10g", "per_shot_10g")
_EWMA_DECAY = 0.5 ** (1 / EWMA_HALF_LIFE)


def _talent(xg_col: str) -> tuple[tuple[str, pl.Expr, str], ...]:
    """Each player's id column, metric and column prefix."""
    return (
        (SHOOTER_ID_COL, pl.col("goal") - pl.col(xg_col), "shooter_gax"),
        (GOALIE_ID_COL, pl.col(xg_col) - pl.col("goal"), "goalie_gsax"),
    )


def _in_row_set() -> pl.Expr:
    """True for the rows the features count: Fenwick events in the modeled strength states."""
    return (
        pl.col("event").is_in(_FENWICK_EVENTS)
        & (pl.col("fenwick") == 1)
        & pl.col("strength_state").is_in(sorted(MODELLED_STRENGTH_STATES))
    )


def _check_columns(df: pl.DataFrame, func: str, required: list[str] | tuple[str, ...], what: str = "df") -> None:
    """Raises InvalidInputError naming every required column ``df`` lacks."""
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise InvalidInputError(f"{func} needs {what} to have the columns {missing}", obj=df)


def _prepare(frame: object, func: str, xg_col: str) -> pl.DataFrame:
    """The play-by-play as polars, checked for every column the features need and for null dates."""
    df = _to_polars(frame)
    _check_columns(df, func, [*_REQUIRED, xg_col])
    nulls = df["game_date"].null_count()
    if nulls:
        raise InvalidInputError(f"{func} cannot order {nulls:,} rows with a null game_date", obj=df)
    return df


@contextmanager
def _as_input_error(func: str) -> Generator[None]:
    """Re-raises a polars error from a column of the wrong type as InvalidInputError."""
    try:
        yield
    except pl.exceptions.PolarsError as exc:
        raise InvalidInputError(f"{func} could not compute the rolling features: {exc}") from exc


def _ewma_stats(df: pl.DataFrame, id_col: str, metric_expr: pl.Expr, stat_col: str) -> pl.DataFrame:
    """The EWMA of the metric over a player's earlier shots; shift(1) leaves out the shot itself."""
    return df.with_columns(
        metric_expr.ewm_mean(half_life=EWMA_HALF_LIFE, ignore_nulls=True)
        .shift(1)
        .over(id_col)
        .cast(pl.Float64)
        .alias(f"{stat_col}_ewma")
    )


def _form_columns(total: pl.Expr, shots: pl.Expr, stat_col: str) -> tuple[pl.Expr, pl.Expr]:
    """The FORM_GAMES total and per-shot columns from a window's metric total and shot count."""
    return (
        pl.when(shots > 0).then(total).otherwise(None).cast(pl.Float64).alias(f"{stat_col}_10g"),
        pl.when(shots > 0).then(total / shots).otherwise(None).cast(pl.Float64).alias(f"{stat_col}_per_shot_10g"),
    )


def _game_level_stats(df: pl.DataFrame, id_col: str, metric_expr: pl.Expr, stat_col: str) -> pl.DataFrame:
    """The metric over a player's FORM_GAMES previous games, in total and per shot.

    Games are ordered by date, then game_id, since a postponed game keeps its number.
    """
    game = (
        df.group_by([id_col, "season", "game_date", "game_id"])
        .agg(metric_expr.sum().alias("_g"), pl.len().alias("_s"))
        .sort([id_col, "season", "game_date", "game_id"])
    )

    g10 = pl.col("_g").rolling_sum(window_size=FORM_GAMES, min_samples=1).shift(1).over(id_col)
    s10 = pl.col("_s").rolling_sum(window_size=FORM_GAMES, min_samples=1).shift(1).over(id_col)

    return game.with_columns(*_form_columns(g10, s10, stat_col)).select(
        id_col, "game_id", f"{stat_col}_10g", f"{stat_col}_per_shot_10g"
    )


def _rolling_rows(df: pl.DataFrame, xg_col: str) -> pl.DataFrame:
    """``df`` in chronological order with the six features, null outside the row set."""
    df = sort_chronological(df).with_row_index("_row_idx")
    for id_col, metric, prefix in _talent(xg_col):
        rows = _ewma_stats(df.filter(_in_row_set(), pl.col(id_col).is_not_null()), id_col, metric, prefix)
        rows = rows.join(
            _game_level_stats(rows, id_col, metric, prefix), on=[id_col, "game_id"], how="left", maintain_order="left"
        )
        stats = rows.select("_row_idx", f"{prefix}_10g", f"{prefix}_per_shot_10g", f"{prefix}_ewma")
        df = df.join(stats, on="_row_idx", how="left", maintain_order="left")
    return df.drop("_row_idx")


def _games_with_state(rows: pl.DataFrame, id_col: str, metric_expr: pl.Expr, prefix: str) -> pl.DataFrame:
    """One row per player-game of sorted ``rows``: the features entering it and the state after."""
    keys = [id_col, "season", "game_date", "game_id"]
    rows = rows.filter(pl.col(id_col).is_not_null())
    counted = rows.filter(metric_expr.is_not_null()).with_columns(
        metric_expr.ewm_mean(half_life=EWMA_HALF_LIFE, ignore_nulls=True).over(id_col).alias("_after"),
        pl.int_range(1, pl.len() + 1).over(id_col).alias("_n"),
    )
    after = counted.group_by(keys, maintain_order=True).agg(
        pl.col("_after").last().alias(f"{prefix}_ewma_after"), pl.col("_n").last().alias(f"{prefix}_shots_after")
    )
    games = (
        rows.group_by(keys, maintain_order=True)
        .agg(
            pl.col(f"{prefix}_ewma").first(),
            pl.col(f"{prefix}_10g").first(),
            pl.col(f"{prefix}_per_shot_10g").first(),
            metric_expr.sum().alias("_g"),
            pl.len().alias("_s"),
        )
        .with_columns(
            pl.col("_g").rolling_sum(window_size=FORM_GAMES, min_samples=1).over(id_col).alias(f"{prefix}_10g_after"),
            pl.col("_s")
            .rolling_sum(window_size=FORM_GAMES, min_samples=1)
            .over(id_col)
            .alias(f"{prefix}_shots_10g_after"),
        )
        .drop("_g", "_s")
    )
    return games.join(after, on=keys, how="left", maintain_order="left")


def _continue(live: pl.DataFrame, state: pl.DataFrame, id_col: str, metric_expr: pl.Expr, prefix: str) -> pl.DataFrame:
    """``live`` with the prefix's three features, carried from ``state`` (one row per player).

    polars' ewm_mean (adjust=True) is a running weighted sum, so it carries exactly: after n
    shots the mean is S / W, with S = x + d * S_prev, W = 1 + d * W_prev and d = 1 - alpha.
    """
    names = [f"{prefix}_{c}" for c in _LIVE_COLS]
    rows = (
        live.with_row_index("_row")
        .filter(_in_row_set(), pl.col(id_col).is_not_null())
        .with_columns(metric_expr.alias("_x"))
    )
    rows = rows.join(
        state.select(id_col, *(f"{prefix}_{c}" for c in _STATE_COLUMNS)), on=id_col, how="left", maintain_order="left"
    )
    ewma = np.full(rows.height, np.nan)
    ids = rows[id_col].to_numpy()
    xs = rows["_x"].to_numpy(allow_copy=True).astype(float)
    mean0 = rows[f"{prefix}_ewma_after"].to_numpy(allow_copy=True).astype(float)
    n0 = rows[f"{prefix}_shots_after"].fill_null(0).to_numpy()
    # rows is in chronological order, so each player's shots are visited in the order taken.
    carried: dict = {}
    for i in range(rows.height):
        if ids[i] not in carried:
            w = (1 - _EWMA_DECAY ** n0[i]) / (1 - _EWMA_DECAY) if n0[i] else 0.0
            carried[ids[i]] = [mean0[i] * w if n0[i] else 0.0, w, n0[i] > 0]
        s, w, ok = carried[ids[i]]
        ewma[i] = s / w if ok else np.nan
        if np.isnan(xs[i]):
            carried[ids[i]][2] = False  # shift(1) of a null mean, as in prep_rolling_gax
            continue
        carried[ids[i]] = [xs[i] + _EWMA_DECAY * s, 1 + _EWMA_DECAY * w, True]
    g10, s10 = pl.col(f"{prefix}_10g_after"), pl.col(f"{prefix}_shots_10g_after")
    feats = rows.select("_row", pl.Series(names[0], ewma).fill_nan(None), *_form_columns(g10, s10, prefix))
    return live.with_row_index("_row").join(feats, on="_row", how="left", maintain_order="left").drop("_row")


@overload
def prep_rolling_gax(pbp: InputFrameT, *, xg_col: str = "context_xg", backend: None = None) -> InputFrameT: ...
@overload
def prep_rolling_gax(pbp: DataFrameT, *, xg_col: str = "context_xg", backend: PolarsBackend) -> pl.DataFrame: ...
@overload
def prep_rolling_gax(pbp: DataFrameT, *, xg_col: str = "context_xg", backend: PandasBackend) -> pd.DataFrame: ...
@overload
def prep_rolling_gax(pbp: DataFrameT, *, xg_col: str = "context_xg", backend: PyarrowBackend) -> pa.Table: ...
@overload
def prep_rolling_gax(pbp: DataFrameT, *, xg_col: str = "context_xg", backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def prep_rolling_gax(pbp: DataFrameT, *, xg_col: str = "context_xg", backend: str | None = None) -> Any: ...
def prep_rolling_gax(pbp: DataFrameT, *, xg_col: str = "context_xg", backend: str | None = None) -> Any:
    """Add each shooter's goals above expected and each goalie's goals saved above expected.

    Shooters take ``goal`` minus ``xg_col`` (GxG), goalies ``xg_col`` minus ``goal`` (GSAx).
    Both count only Fenwick events in ``MODELLED_STRENGTH_STATES``; every other row is kept
    with nulls. Rows run in the order played (``contract.sort_chronological``: season,
    game_date, game_id, event_idx), across seasons, and each value looks only backward:

    - ``{prefix}_ewma``: the exponentially weighted mean over the player's earlier shots, a
      shot ``EWMA_HALF_LIFE`` shots back keeping half its weight.
    - ``{prefix}_10g``: the total over the player's ``FORM_GAMES`` previous games.
    - ``{prefix}_per_shot_10g``: that total divided by the shots in those games.

    The prefix is ``shooter_gax`` or ``goalie_gsax``. A shot with a missing xG stays null and
    the EWMA skips it, though it still counts as a shot in ``_per_shot_10g``. A row with no
    shooter id gets null shooter features, and a shot on an empty net, with no goalie id,
    null goalie features, rather than a form pooled over every unknown player. A player's
    first shot and first game get nulls.

    Parameters:
        pbp (DataFrameT): Play-by-play in any backend, with goal, ``xg_col``,
            player_1_api_id, opp_goalie_api_id, season, session, game_date, game_id,
            event_idx, event, fenwick and strength_state. Pass every earlier game the
            features should see.
        xg_col (str): The expected-goals column. Default ``"context_xg"``.
        backend (str | None): Backend for the result. Default None returns the same type as
            ``pbp``.

    Returns:
        DataFrameT: ``pbp`` in chronological order with the six ``ROLLING_GAX_COLUMNS``.

    Raises:
        InvalidInputError: If a column is missing, a game_date is null, or a column has a
            type the features cannot use.

    Examples:
        >>> from chickenstats.chicken_nhl import prep_rolling_gax
        >>> pbp = pbp.join(xg_predictions, on=["game_id", "event_idx"])  # adds context_xg
        >>> rolling = prep_rolling_gax(pbp)
    """
    backend = _output_backend(pbp, backend)
    df = _prepare(pbp, "prep_rolling_gax", xg_col)
    with _as_input_error("prep_rolling_gax"):
        out = _rolling_rows(df, xg_col)
    return _to_backend(out, backend)


@overload
def prep_rolling_gax_games(
    pbp: InputFrameT, *, xg_col: str = "context_xg", backend: None = None
) -> tuple[InputFrameT, InputFrameT]: ...
@overload
def prep_rolling_gax_games(
    pbp: DataFrameT, *, xg_col: str = "context_xg", backend: PolarsBackend
) -> tuple[pl.DataFrame, pl.DataFrame]: ...
@overload
def prep_rolling_gax_games(
    pbp: DataFrameT, *, xg_col: str = "context_xg", backend: PandasBackend
) -> tuple[pd.DataFrame, pd.DataFrame]: ...
@overload
def prep_rolling_gax_games(
    pbp: DataFrameT, *, xg_col: str = "context_xg", backend: PyarrowBackend
) -> tuple[pa.Table, pa.Table]: ...
@overload
def prep_rolling_gax_games(
    pbp: DataFrameT, *, xg_col: str = "context_xg", backend: NarwhalsBackend
) -> tuple[NarwhalsFrame, NarwhalsFrame]: ...
@overload
def prep_rolling_gax_games(
    pbp: DataFrameT, *, xg_col: str = "context_xg", backend: str | None = None
) -> tuple[Any, Any]: ...
def prep_rolling_gax_games(
    pbp: DataFrameT, *, xg_col: str = "context_xg", backend: str | None = None
) -> tuple[Any, Any]:
    """Return one row per shooter-game and one per goalie-game, with the state after each game.

    Each row carries the features entering the game, as ``prep_rolling_gax`` gives the
    player's first shot of it, and the state ``continue_rolling_gax`` carries into the
    player's next game:

    - ``{prefix}_ewma_after`` and ``{prefix}_shots_after``: the EWMA through the game's last
      shot and the number of shots with an xG it covers.
    - ``{prefix}_10g_after`` and ``{prefix}_shots_10g_after``: the total and the shots over
      the ``FORM_GAMES`` games ending with this one.

    Parameters:
        pbp (DataFrameT): Play-by-play in any backend, with the columns ``prep_rolling_gax``
            needs.
        xg_col (str): The expected-goals column. Default ``"context_xg"``.
        backend (str | None): Backend for the results. Default None returns the same type as
            ``pbp``.

    Returns:
        tuple[DataFrameT, DataFrameT]: The shooter games, keyed by player_1_api_id, season,
            game_date and game_id with the ``shooter_gax`` prefix, and the goalie games, keyed
            by opp_goalie_api_id with the ``goalie_gsax`` prefix, in the order played.

    Raises:
        InvalidInputError: If a column is missing, a game_date is null, or a column has a
            type the features cannot use.

    Examples:
        >>> from chickenstats.chicken_nhl import prep_rolling_gax_games
        >>> shooter_games, goalie_games = prep_rolling_gax_games(pbp)
    """
    backend = _output_backend(pbp, backend)
    df = _prepare(pbp, "prep_rolling_gax_games", xg_col)
    with _as_input_error("prep_rolling_gax_games"):
        scored = sort_chronological(_rolling_rows(df, xg_col).filter(_in_row_set()))
        shooter, goalie = (_games_with_state(scored, *talent) for talent in _talent(xg_col))
    return _to_backend(shooter, backend), _to_backend(goalie, backend)


@overload
def latest_rolling_state(games: InputFrameT, id_col: str, *, backend: None = None) -> InputFrameT: ...
@overload
def latest_rolling_state(games: DataFrameT, id_col: str, *, backend: PolarsBackend) -> pl.DataFrame: ...
@overload
def latest_rolling_state(games: DataFrameT, id_col: str, *, backend: PandasBackend) -> pd.DataFrame: ...
@overload
def latest_rolling_state(games: DataFrameT, id_col: str, *, backend: PyarrowBackend) -> pa.Table: ...
@overload
def latest_rolling_state(games: DataFrameT, id_col: str, *, backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def latest_rolling_state(games: DataFrameT, id_col: str, *, backend: str | None = None) -> Any: ...
def latest_rolling_state(games: DataFrameT, id_col: str, *, backend: str | None = None) -> Any:
    """Return each player's last game in ``games``, across seasons, by game_date then game_id.

    Parameters:
        games (DataFrameT): Shooter or goalie games from ``prep_rolling_gax_games``, or the
            same rows read back from storage, in any backend.
        id_col (str): The player column: ``SHOOTER_ID_COL`` for shooter games,
            ``GOALIE_ID_COL`` for goalie games.
        backend (str | None): Backend for the result. Default None returns the same type as
            ``games``.

    Returns:
        DataFrameT: One row per player, the state ``continue_rolling_gax`` starts from.

    Raises:
        InvalidInputError: If ``games`` lacks ``id_col``, game_date or game_id.

    Examples:
        >>> from chickenstats.chicken_nhl import latest_rolling_state, prep_rolling_gax_games
        >>> shooter_games, goalie_games = prep_rolling_gax_games(history)
        >>> shooter_state = latest_rolling_state(shooter_games, "player_1_api_id")
    """
    backend = _output_backend(games, backend)
    df = _to_polars(games)
    _check_columns(df, "latest_rolling_state", [id_col, "game_date", "game_id"], what="games")
    with _as_input_error("latest_rolling_state"):
        out = df.sort(id_col, "game_date", "game_id").group_by(id_col, maintain_order=True).last()
    return _to_backend(out, backend)


@overload
def continue_rolling_gax(
    live: InputFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: None = None,
) -> InputFrameT: ...
@overload
def continue_rolling_gax(
    live: DataFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def continue_rolling_gax(
    live: DataFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def continue_rolling_gax(
    live: DataFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def continue_rolling_gax(
    live: DataFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def continue_rolling_gax(
    live: DataFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: str | None = None,
) -> Any: ...
def continue_rolling_gax(
    live: DataFrameT,
    shooter_state: DataFrameT,
    goalie_state: DataFrameT,
    *,
    xg_col: str = "context_xg",
    backend: str | None = None,
) -> Any:
    """Add ``prep_rolling_gax``'s six features to live shots, from each player's stored state.

    Gives every shot of a new game what ``prep_rolling_gax`` gives it with the game appended
    to the history, without recomputing that history. The EWMA carries forward shot by shot,
    so it moves within the game; the 10-game features are constant within the game, since
    they cover the games before it. A player with no state gets what a player's first shot
    gets: null, then form from the live game's own shots.

    Parameters:
        live (DataFrameT): Play-by-play of games not in the state, in any backend, with the
            columns ``prep_rolling_gax`` needs.
        shooter_state (DataFrameT): ``latest_rolling_state`` of the shooter games, one row per
            player_1_api_id with the ``shooter_gax`` state columns.
        goalie_state (DataFrameT): ``latest_rolling_state`` of the goalie games, one row per
            opp_goalie_api_id with the ``goalie_gsax`` state columns.
        xg_col (str): The expected-goals column. Default ``"context_xg"``.
        backend (str | None): Backend for the result. Default None returns the same type as
            ``live``.

    Returns:
        DataFrameT: ``live`` in chronological order with the six ``ROLLING_GAX_COLUMNS``,
            null outside Fenwick events in ``MODELLED_STRENGTH_STATES``.

    Raises:
        InvalidInputError: If a column is missing, a game_date is null, a state has more
            than one row for a player, or a column has a type the features cannot use.

    Examples:
        >>> from chickenstats.chicken_nhl import continue_rolling_gax, latest_rolling_state
        >>> shooter_state = latest_rolling_state(shooter_games, "player_1_api_id")
        >>> goalie_state = latest_rolling_state(goalie_games, "opp_goalie_api_id")
        >>> live = continue_rolling_gax(live_pbp, shooter_state, goalie_state)
    """
    func = "continue_rolling_gax"
    backend = _output_backend(live, backend)
    df = _prepare(live, func, xg_col)
    states = []
    for (id_col, _, prefix), frame, name in zip(
        _talent(xg_col), (shooter_state, goalie_state), ("shooter_state", "goalie_state"), strict=True
    ):
        state = _to_polars(frame)
        _check_columns(state, func, [id_col, *(f"{prefix}_{c}" for c in _STATE_COLUMNS)], what=name)
        repeats = state.height - state[id_col].n_unique()
        if repeats:
            raise InvalidInputError(
                f"{func} needs one {name} row per {id_col}, but {repeats:,} repeat; pass latest_rolling_state's output",
                obj=state,
            )
        states.append(state)

    with _as_input_error(func):
        df = sort_chronological(df)
        for talent, state in zip(_talent(xg_col), states, strict=True):
            df = _continue(df, state, *talent)
    return _to_backend(df, backend)
