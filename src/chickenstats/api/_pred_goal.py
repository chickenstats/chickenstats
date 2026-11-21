from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

import polars as pl

from chickenstats.exceptions import InvalidInputError
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.types import DataFrameT
from chickenstats.utilities.utilities import _detect_backend, _to_backend, _to_polars, _validate_backend

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    from chickenstats.utilities.types import (
        AnyBackend,
        InputFrameT,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )

_KEYS = ["game_id", "event_idx"]
_CHECKS = ["event", "player_1_api_id"]
_XG_COLS = ["base_xg", "context_xg", "pred_goal"]
_SHOWN_MISMATCHES = 5


def _require(df: pl.DataFrame, columns: list[str], name: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise InvalidInputError(f"{name} is missing the column(s) {', '.join(missing)}")


@overload
def join_pred_goal(pbp: InputFrameT, pred: DataFrameT, *, backend: None = None) -> InputFrameT: ...
@overload
def join_pred_goal(pbp: DataFrameT, pred: DataFrameT, *, backend: PolarsBackend) -> pl.DataFrame: ...
@overload
def join_pred_goal(pbp: DataFrameT, pred: DataFrameT, *, backend: PandasBackend) -> pd.DataFrame: ...
@overload
def join_pred_goal(pbp: DataFrameT, pred: DataFrameT, *, backend: PyarrowBackend) -> pa.Table: ...
@overload
def join_pred_goal(pbp: DataFrameT, pred: DataFrameT, *, backend: NarwhalsBackend) -> NarwhalsFrame: ...
@overload
def join_pred_goal(pbp: DataFrameT, pred: DataFrameT, *, backend: AnyBackend | None = None) -> Any: ...
def join_pred_goal(
    pbp: DataFrameT,
    pred: DataFrameT,
    *,
    backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] | None = None,
) -> Any:
    """Add the chickenstats API's xG predictions to a play-by-play frame.

    Joins ``pred`` onto ``pbp`` on ``game_id`` and ``event_idx`` and adds its ``base_xg``,
    ``context_xg`` and ``pred_goal`` columns. Every play-by-play row is kept; a row with no
    prediction, such as a faceoff, has nulls in the three columns. Predictions that match no
    play-by-play row are ignored. Any xG columns ``pbp`` already has, and their ``_adj``
    versions, are replaced; ``prep_stats`` builds the adjusted ones again.

    Each matched prediction must agree with its play-by-play row on ``event`` and
    ``player_1_api_id`` (a null shooter on both sides counts as agreeing), so a prediction is
    never attached to the wrong shot.

    Parameters:
        pbp (DataFrameT):
            Play-by-play, e.g., from ``Scraper.play_by_play`` or ``ChickenStats.download_pbp()``.
        pred (DataFrameT):
            Predictions from ``ChickenStats.download_pred_goal()``.
        backend (Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] | None):
            Output backend. Defaults to the backend of ``pbp``.

    Returns:
        DataFrameT: ``pbp`` with ``base_xg``, ``context_xg`` and ``pred_goal`` added.

    Raises:
        InvalidInputError: If either frame lacks a needed column, ``pred`` has more than one row for an
            event, or any matched rows disagree.

    Examples:
        >>> from chickenstats import Scraper
        >>> from chickenstats.api import ChickenStats, join_pred_goal
        >>> pbp = Scraper(2023020001).play_by_play
        >>> pred = ChickenStats().download_pred_goal(game_id=2023020001)
        >>> pbp = join_pred_goal(pbp, pred)
    """
    output_backend = _validate_backend(backend or _detect_backend(pbp))
    pbp_df = _to_polars(pbp)
    pred_df = _to_polars(pred)

    _require(pbp_df, _KEYS + _CHECKS, "pbp")
    _require(pred_df, _KEYS + _CHECKS + _XG_COLS, "pred")

    # Old xG and its score-adjusted copies would shadow the new values
    pbp_df = pbp_df.drop(*_XG_COLS, *[f"{col}_adj" for col in _XG_COLS], strict=False)

    # An all-null column can arrive as a string, so match pbp's types before joining
    pred_df = pred_df.select(
        *[pl.col(col).cast(pbp_df.schema[col]) for col in _KEYS + _CHECKS],
        *[pl.col(col).cast(pl.Float64) for col in _XG_COLS],
    )

    if pred_df.select(pl.struct(_KEYS).is_duplicated().any()).item():
        raise InvalidInputError("pred has more than one row for the same game_id and event_idx")

    pred_df = pred_df.rename({col: f"_pred_{col}" for col in _CHECKS}).with_columns(_matched=pl.lit(True))
    joined = pbp_df.join(pred_df, on=_KEYS, how="left", maintain_order="left")

    mismatched = joined.filter(
        pl.col("_matched") & pl.any_horizontal(pl.col(col).ne_missing(pl.col(f"_pred_{col}")) for col in _CHECKS)
    )
    if mismatched.height:
        examples = "\n".join(
            f"  game {row['game_id']}, event {row['event_idx']}: "
            f"pbp {row['event']} by {row['player_1_api_id']}, "
            f"pred {row['_pred_event']} by {row['_pred_player_1_api_id']}"
            for row in mismatched.head(_SHOWN_MISMATCHES).iter_rows(named=True)
        )
        raise InvalidInputError(
            f"{mismatched.height} prediction(s) do not match their play-by-play event or shooter:\n{examples}"
        )

    result = joined.drop("_matched", *[f"_pred_{col}" for col in _CHECKS])

    return _to_backend(result, output_backend)
