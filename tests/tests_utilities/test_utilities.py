from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pyarrow as pa
import pytest
from requests.adapters import HTTPAdapter
from rich.progress import Progress

from chickenstats.utilities.utilities import (
    ChickenHTTPAdapter,
    ChickenProgress,
    ChickenSession,
    ScrapeSpeedColumn,
    _detect_backend,
    _to_polars,
    add_cs_mplstyles,
)


# ---------------------------------------------------------------------------
# ChickenProgress
# ---------------------------------------------------------------------------


def test_chicken_progress_is_progress():
    assert isinstance(ChickenProgress(), Progress)


# ---------------------------------------------------------------------------
# ChickenSession
# ---------------------------------------------------------------------------


def test_chicken_session_is_session():
    import requests

    assert isinstance(ChickenSession(), requests.Session)


def test_update_headers():
    session = ChickenSession()
    session.update_headers({"X-Custom": "test-value"})
    assert session.headers["X-Custom"] == "test-value"


# ---------------------------------------------------------------------------
# ChickenHTTPAdapter
# ---------------------------------------------------------------------------


def test_adapter_is_http_adapter():
    assert isinstance(ChickenHTTPAdapter(), HTTPAdapter)


def test_adapter_default_timeout():
    adapter = ChickenHTTPAdapter()
    assert adapter.timeout == 5


def test_adapter_custom_timeout():
    adapter = ChickenHTTPAdapter(timeout=30)
    assert adapter.timeout == 30


def test_adapter_send_sets_default_timeout_when_none():
    """Lines 57-58: when timeout is None, adapter substitutes its own."""
    adapter = ChickenHTTPAdapter(timeout=10)
    with patch.object(HTTPAdapter, "send", return_value=MagicMock()) as mock_send:
        adapter.send(MagicMock(), timeout=None)
        assert mock_send.call_args.kwargs["timeout"] == 10


def test_adapter_send_passes_explicit_timeout():
    """Line 59 false branch: explicit timeout is forwarded unchanged."""
    adapter = ChickenHTTPAdapter(timeout=10)
    with patch.object(HTTPAdapter, "send", return_value=MagicMock()) as mock_send:
        adapter.send(MagicMock(), timeout=30)
        assert mock_send.call_args.kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# ScrapeSpeedColumn
# ---------------------------------------------------------------------------


def test_scrape_speed_fast():
    col = ScrapeSpeedColumn()
    task = MagicMock()
    task.finished_speed = 2.5
    task.speed = None
    task.elapsed = None
    result = col.render(task)
    assert "it/s" in result.plain


def test_scrape_speed_slow():
    """Lines 152-153: speed < 1 renders as s/it."""
    col = ScrapeSpeedColumn()
    task = MagicMock()
    task.finished_speed = 0.25
    task.speed = None
    task.elapsed = None
    result = col.render(task)
    assert "s/it" in result.plain


def test_scrape_speed_none_with_elapsed():
    """speed is None but elapsed > 0 → compute from completed/elapsed."""
    col = ScrapeSpeedColumn()
    task = MagicMock()
    task.finished_speed = None
    task.speed = None
    task.elapsed = 10.0
    task.completed = 5
    result = col.render(task)
    assert result.plain != "?"


def test_scrape_speed_unknown():
    """No speed, no elapsed → renders '?'."""
    col = ScrapeSpeedColumn()
    task = MagicMock()
    task.finished_speed = None
    task.speed = None
    task.elapsed = None
    result = col.render(task)
    assert result.plain == "?"


# ---------------------------------------------------------------------------
# _to_polars
# ---------------------------------------------------------------------------


def test_to_polars_from_polars():
    df = pl.DataFrame({"a": [1, 2]})
    assert _to_polars(df) is df


def test_to_polars_from_lazy():
    lf = pl.LazyFrame({"a": [1, 2]})
    result = _to_polars(lf)
    assert isinstance(result, pl.DataFrame)


def test_to_polars_from_pandas():
    df = pd.DataFrame({"a": [1, 2]})
    result = _to_polars(df)
    assert isinstance(result, pl.DataFrame)


def test_to_polars_null_dtype_column():
    """Lines 344-345: all-None column is Null dtype → cast to String."""
    df = pd.DataFrame({"col": [1, 2], "empty": [None, None]})
    result = _to_polars(df)
    assert isinstance(result, pl.DataFrame)
    assert result["empty"].dtype == pl.String


# ---------------------------------------------------------------------------
# _detect_backend
# ---------------------------------------------------------------------------


def test_detect_backend_polars():
    assert _detect_backend(pl.DataFrame()) == "polars"


def test_detect_backend_lazy():
    assert _detect_backend(pl.LazyFrame()) == "polars"


def test_detect_backend_pandas():
    """Lines 356-357: pandas DataFrame returns 'pandas'."""
    assert _detect_backend(pd.DataFrame()) == "pandas"


def test_detect_backend_pyarrow():
    """Lines 363-364: pyarrow Table returns 'pyarrow'."""
    assert _detect_backend(pa.table({"a": [1]})) == "pyarrow"


# ---------------------------------------------------------------------------
# add_cs_mplstyles
# ---------------------------------------------------------------------------


def test_add_cs_mplstyles_idempotent():
    """Line 469: second call returns early when already registered."""
    add_cs_mplstyles()
    add_cs_mplstyles()  # hits the `if _STYLES_REGISTERED: return` branch
