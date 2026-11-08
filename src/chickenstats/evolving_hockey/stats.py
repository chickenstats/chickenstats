"""Dataframe-agnostic public wrappers for stat functions.

Each function detects the input backend and dispatches to the polars implementation
in _aggregation.py, then converts output to the requested backend via narwhals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload


from chickenstats.evolving_hockey._aggregation import (
    prep_gar as _prep_gar,
    prep_ind as _prep_ind,
    prep_lines as _prep_lines,
    prep_oi as _prep_oi,
    prep_stats as _prep_stats,
    prep_team_stats as _prep_team_stats,
    prep_xgar as _prep_xgar,
)
from chickenstats.utilities.utilities import _to_polars, _detect_backend, _to_backend, _validate_backend
from chickenstats.utilities.enums import AggLevel

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl
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


@overload
def prep_ind(
    pbp: InputFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: None = None,
) -> InputFrameT: ...
@overload
def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: str | None = None,
) -> Any: ...
def prep_ind(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: str | None = None,
) -> Any:
    """Prepare individual player stats from evolving-hockey.com play-by-play data.

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
    backend = _validate_backend(backend or _detect_backend(pbp))
    return _to_backend(_prep_ind(_to_polars(pbp), level, score, teammates, opposition), backend)


@overload
def prep_oi(
    pbp: InputFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: None = None,
) -> InputFrameT: ...
@overload
def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    *,
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: str | None = None,
) -> Any: ...
def prep_oi(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    backend: str | None = None,
) -> Any:
    """Prepare on-ice stats from evolving-hockey.com play-by-play data.

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
    backend = _validate_backend(backend or _detect_backend(pbp))
    return _to_backend(_prep_oi(_to_polars(pbp), level, score, teammates, opposition), backend)


@overload
def prep_stats(
    pbp: InputFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: None = None,
) -> InputFrameT: ...
@overload
def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any: ...
def prep_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any:
    """Prepare combined individual + on-ice player stats from evolving-hockey.com play-by-play data.

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
    backend = _validate_backend(backend or _detect_backend(pbp))
    return _to_backend(_prep_stats(_to_polars(pbp), level, score, teammates, opposition, disable_progress_bar), backend)


@overload
def prep_lines(
    pbp: InputFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: None = None,
) -> InputFrameT: ...
@overload
def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any: ...
def prep_lines(
    pbp: DataFrameT,
    position: Literal["f", "d"] = "f",
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any:
    """Prepare line stats from evolving-hockey.com play-by-play data.

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

    Raises:
        InvalidInputError: If ``position`` is not 'f' or 'd', or ``pbp`` lacks ``players_on_pos`` or a zone start
            column.
    """
    backend = _validate_backend(backend or _detect_backend(pbp))
    return _to_backend(
        _prep_lines(_to_polars(pbp), position, level, score, teammates, opposition, disable_progress_bar), backend
    )


@overload
def prep_team_stats(
    pbp: InputFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    backend: None = None,
) -> InputFrameT: ...
@overload
def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PolarsBackend,
) -> pl.DataFrame: ...
@overload
def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PandasBackend,
) -> pd.DataFrame: ...
@overload
def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: PyarrowBackend,
) -> pa.Table: ...
@overload
def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    *,
    backend: NarwhalsBackend,
) -> NarwhalsFrame: ...
@overload
def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any: ...
def prep_team_stats(
    pbp: DataFrameT,
    level: AggLevel | Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
    backend: str | None = None,
) -> Any:
    """Prepare team stats from evolving-hockey.com play-by-play data.

    Parameters:
        pbp: DataFrame from prep_pbp (any narwhals-compatible backend).
        level: Aggregation level — 'season', 'session', 'game', or 'period'.
        strengths: Whether to split by strength state.
        score: Whether to split by score state.
        disable_progress_bar: Whether to suppress the progress bar.
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.

    Raises:
        InvalidInputError: If ``pbp`` lacks ``event_team``, ``opp_team``, ``players_on_pos`` or a zone start column.
    """
    backend = _validate_backend(backend or _detect_backend(pbp))
    return _to_backend(_prep_team_stats(_to_polars(pbp), level, strengths, score, disable_progress_bar), backend)


@overload
def prep_gar(skater_data: InputFrameT, goalie_data: DataFrameT, backend: None = None) -> InputFrameT: ...
@overload
def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: PolarsBackend) -> pl.DataFrame: ...
@overload
def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: PandasBackend) -> pd.DataFrame: ...
@overload
def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: PyarrowBackend) -> pa.Table: ...
@overload
def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: str | None = None) -> Any: ...
def prep_gar(skater_data: DataFrameT, goalie_data: DataFrameT, backend: str | None = None) -> Any:
    """Prepare GAR data from evolving-hockey.com CSV exports.

    Parameters:
        skater_data: Skater GAR DataFrame from EH (any narwhals-compatible backend).
        goalie_data: Goalie GAR DataFrame from EH (any narwhals-compatible backend).
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    backend = _validate_backend(backend or _detect_backend(skater_data))
    return _to_backend(_prep_gar(_to_polars(skater_data), _to_polars(goalie_data)), backend)


@overload
def prep_xgar(data: InputFrameT, backend: None = None) -> InputFrameT: ...
@overload
def prep_xgar(data: DataFrameT, backend: PolarsBackend) -> pl.DataFrame: ...
@overload
def prep_xgar(data: DataFrameT, backend: PandasBackend) -> pd.DataFrame: ...
@overload
def prep_xgar(data: DataFrameT, backend: PyarrowBackend) -> pa.Table: ...
@overload
def prep_xgar(data: DataFrameT, backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def prep_xgar(data: DataFrameT, backend: str | None = None) -> Any: ...
def prep_xgar(data: DataFrameT, backend: str | None = None) -> Any:
    """Prepare xGAR data from evolving-hockey.com CSV exports.

    Parameters:
        data: xGAR DataFrame from EH (any narwhals-compatible backend).
        backend: Output backend ('polars', 'pandas', 'pyarrow'). Defaults to input backend.

    Returns:
        DataFrame in the requested backend.
    """
    backend = _validate_backend(backend or _detect_backend(data))
    return _to_backend(_prep_xgar(_to_polars(data)), backend)
