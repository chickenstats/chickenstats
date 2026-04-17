"""Dataframe-agnostic public wrappers for EvolvingHockey stat functions.

Each function detects the input backend and dispatches to the polars implementation
in _aggregation.py, then converts output to the requested backend via narwhals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import polars as pl

from chickenstats.evolving_hockey._aggregation import (
    prep_gar as _prep_gar,
    prep_ind as _prep_ind,
    prep_lines as _prep_lines,
    prep_oi as _prep_oi,
    prep_stats as _prep_stats,
    prep_team_stats as _prep_team_stats,
    prep_xgar as _prep_xgar,
)
from chickenstats.utilities.utilities import _to_polars, _detect_backend, _to_backend
from chickenstats.utilities.enums import AggLevel
from chickenstats.utilities._types import DataFrameT

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa


def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: str | None = None,
):
    """Prepare individual player stats from EH PBP data.

    Parameters:
        pbp: DataFrame from prep_pbp (any narwhals-compatible backend).
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(pbp)
    return _to_backend(_prep_ind(_to_polars(pbp), level, score, teammates, opposition), backend)


def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: str | None = None,
):
    """Prepare on-ice stats from EH PBP data.

    Parameters:
        pbp: DataFrame from prep_pbp (any narwhals-compatible backend).
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(pbp)
    return _to_backend(_prep_oi(_to_polars(pbp), level, score, teammates, opposition), backend)


def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
):
    """Prepare combined individual + on-ice player stats from EH PBP data.

    Parameters:
        pbp: DataFrame from prep_pbp (any narwhals-compatible backend).
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        disable_progress_bar: Whether to suppress the progress bar.
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(pbp)
    return _to_backend(_prep_stats(_to_polars(pbp), level, score, teammates, opposition, disable_progress_bar), backend)


def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
):
    """Prepare line stats from EH PBP data.

    Parameters:
        pbp: DataFrame from prep_pbp (any narwhals-compatible backend).
        position: Position group — 'f' (forwards) or 'd' (defense).
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        score: Whether to split by score state.
        teammates: Whether to split by on-ice teammates.
        opposition: Whether to split by on-ice opponents.
        disable_progress_bar: Whether to suppress the progress bar.
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(pbp)
    return _to_backend(
        _prep_lines(_to_polars(pbp), position, level, score, teammates, opposition, disable_progress_bar), backend
    )


def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
):
    """Prepare team stats from EH PBP data.

    Parameters:
        pbp: DataFrame from prep_pbp (any narwhals-compatible backend).
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        strengths: Whether to split by strength state.
        score: Whether to split by score state.
        disable_progress_bar: Whether to suppress the progress bar.
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(pbp)
    return _to_backend(_prep_team_stats(_to_polars(pbp), level, strengths, score, disable_progress_bar), backend)


def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: str | None = None):
    """Prepare GAR data from EH CSV exports.

    Parameters:
        skater_data: Skater GAR DataFrame from EH (any narwhals-compatible backend).
        goalie_data: Goalie GAR DataFrame from EH (any narwhals-compatible backend).
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(skater_data)
    return _to_backend(_prep_gar(_to_polars(skater_data), _to_polars(goalie_data)), backend)


def prep_xgar(data: DataFrameT, backend: str | None = None):
    """Prepare xGAR data from EH CSV exports.

    Parameters:
        data: xGAR DataFrame from EH (any narwhals-compatible backend).
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    if backend is None:
        backend = _detect_backend(data)
    return _to_backend(_prep_xgar(_to_polars(data)), backend)
