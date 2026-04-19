"""Utility helpers for building upload-ready records for the chickenstats API.

Includes:
    * _to_int_list      — coerce a scalar/list/None parameter to list[int] | None
    * _to_str_list      — coerce a scalar/list/None parameter to list[str] | None
    * _sort_api_id_list — Polars expression: sorts a comma-separated API ID field numerically
    * _player_stats_id  — Polars expression: unique row ID for player-level stats
    * _line_stats_id    — Polars expression: unique row ID for line-level stats
    * _team_stats_id    — Polars expression: unique row ID for team-level stats
    * _prep_with_id     — adds an ID column, moves it first, returns DataFrame or list[dict]

ID format
---------
Fields are separated by ``-``; player API ID lists within a field are sorted
numerically and joined with ``_``. Period is zero-padded to two digits.

Example (player-level)::

    2024020123-01-0v0-5v5-TOR-8471675-8474141_8478402_8471234-8480801_8476981-8476412-BOS-...
"""

from __future__ import annotations

from typing import Literal, overload

import polars as pl


def _to_int_list(v: list | int | str | None) -> list[int] | None:
    """Coerce a scalar, list, or None query parameter to ``list[int] | None``.

    Parameters:
        v: The raw parameter value — ``None``, a single ``int`` or ``str``, or an
           iterable of values that can each be passed to ``int()``.

    Returns:
        ``None`` when *v* is ``None``; otherwise a ``list[int]``.
    """
    if v is None:
        return None
    if isinstance(v, (int, str)):
        return [int(v)]
    return [int(x) for x in v]


def _to_str_list(v: list | str | None) -> list[str] | None:
    """Coerce a scalar, list, or None query parameter to ``list[str] | None``.

    Parameters:
        v: The raw parameter value — ``None``, a single ``str``, or an iterable of
           strings.

    Returns:
        ``None`` when *v* is ``None``; otherwise a ``list[str]``.
    """
    if v is None:
        return None
    if isinstance(v, str):
        return [v]
    return list(v)


def _sort_api_id_list(col_name: str) -> pl.Expr:
    """Return a Polars expression that sorts a comma-separated API ID field numerically.

    Splits the string on ``", "``, casts each element to Int64, sorts ascending, then
    rejoins with ``"_"``. Null inputs produce an empty string. Ensures the same set of
    players always produces the same ID segment regardless of their original ordering.

    Parameters:
        col_name (str): Name of the column containing comma-separated API IDs.
    """
    return (
        pl.col(col_name)
        .cast(pl.String)
        .str.split(", ")
        .list.eval(pl.element().filter(pl.element() != "").cast(pl.Int64))
        .list.sort()
        .cast(pl.List(pl.String))
        .list.join("_")
        .fill_null("")
    )


def _player_stats_id() -> pl.Expr:
    """Return a Polars expression that builds the unique row ID for player-level stats.

    Used by ``_prep_stats_polars``. Fields are separated by ``-``; player API ID
    lists within a field are sorted numerically via ``_sort_api_id_list``. Period is
    zero-padded to two digits.
    """
    return (
        pl.col("game_id").cast(pl.String)
        + "-"
        + pl.col("period").cast(pl.String).str.zfill(2)
        + "-"
        + pl.col("score_state")
        + "-"
        + pl.col("strength_state")
        + "-"
        + pl.col("team")
        + "-"
        + pl.col("api_id").cast(pl.String)
        + "-"
        + _sort_api_id_list("forwards_api_id")
        + "-"
        + _sort_api_id_list("defense_api_id")
        + "-"
        + pl.col("own_goalie_api_id").cast(pl.String).fill_null("")
        + "-"
        + pl.col("opp_team").fill_null("")
        + "-"
        + _sort_api_id_list("opp_forwards_api_id")
        + "-"
        + _sort_api_id_list("opp_defense_api_id")
        + "-"
        + pl.col("opp_goalie_api_id").cast(pl.String).fill_null("")
    )


def _line_stats_id() -> pl.Expr:
    """Return a Polars expression that builds the unique row ID for line-level stats.

    Same format as ``_player_stats_id`` but without a per-player ``api_id`` field,
    since lines are keyed by the group of players rather than an individual.
    """
    return (
        pl.col("game_id").cast(pl.String)
        + "-"
        + pl.col("period").cast(pl.String).str.zfill(2)
        + "-"
        + pl.col("score_state")
        + "-"
        + pl.col("strength_state")
        + "-"
        + pl.col("team")
        + "-"
        + _sort_api_id_list("forwards_api_id")
        + "-"
        + _sort_api_id_list("defense_api_id")
        + "-"
        + pl.col("own_goalie_api_id").cast(pl.String).fill_null("")
        + "-"
        + pl.col("opp_team").fill_null("")
        + "-"
        + _sort_api_id_list("opp_forwards_api_id")
        + "-"
        + _sort_api_id_list("opp_defense_api_id")
        + "-"
        + pl.col("opp_goalie_api_id").cast(pl.String).fill_null("")
    )


@overload
def _prep_with_id(df: pl.DataFrame, id_expr: pl.Expr, as_polars: Literal[True]) -> pl.DataFrame: ...
@overload
def _prep_with_id(df: pl.DataFrame, id_expr: pl.Expr, as_polars: Literal[False] = ...) -> list[dict]: ...
def _prep_with_id(df: pl.DataFrame, id_expr: pl.Expr, as_polars: bool = False) -> pl.DataFrame | list[dict]:
    """Add an ID column to *df*, reorder it first, and return the result.

    Parameters:
        df: Input Polars DataFrame.
        id_expr: Polars expression that produces the ID values (e.g. ``_player_stats_id()``).
        as_polars: When ``True`` return a ``pl.DataFrame``; otherwise return ``list[dict]``.
    """
    df = df.with_columns(id=id_expr)
    cols = ["id"] + [c for c in df.columns if c != "id"]
    df = df.select(cols)
    return df if as_polars else df.to_dicts()


def _team_stats_id() -> pl.Expr:
    """Return a Polars expression that builds the unique row ID for team-level stats.

    Keyed by game, period, score state, strength state, team, and opponent — no
    player-level fields needed.
    """
    return (
        pl.col("game_id").cast(pl.String)
        + "-"
        + pl.col("period").cast(pl.String).str.zfill(2)
        + "-"
        + pl.col("score_state")
        + "-"
        + pl.col("strength_state")
        + "-"
        + pl.col("team")
        + "-"
        + pl.col("opp_team").fill_null("")
    )
