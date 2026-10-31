import copy
import pickle
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
import requests
from requests.adapters import HTTPAdapter
from rich.progress import Progress

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

try:
    import pyarrow as pa

    HAS_PYARROW = True
except ImportError:
    pa = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PYARROW = False

try:
    import matplotlib  # noqa: F401

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from chickenstats.exceptions import UnsupportedBackendError
from chickenstats.utilities.utilities import (
    ChickenHTTPAdapter,
    ChickenProgress,
    ChickenSession,
    ScrapeSpeedColumn,
    _detect_backend,
    _to_backend,
    _to_polars,
    add_cs_mplstyles,
    norm_coords,
)


# -----------------------------------------------------------------------------
# ChickenProgress
# -----------------------------------------------------------------------------


def test_chicken_progress_is_progress():
    assert isinstance(ChickenProgress(), Progress)


# -----------------------------------------------------------------------------
# ChickenSession
# -----------------------------------------------------------------------------


def test_chicken_session_is_session():
    import requests

    assert isinstance(ChickenSession(), requests.Session)


def test_update_headers():
    session = ChickenSession()
    session.update_headers({"X-Custom": "test-value"})
    assert session.headers["X-Custom"] == "test-value"


def test_the_user_agent_names_chickenstats():
    """Requests say they come from chickenstats, not a browser (N110)."""
    from chickenstats import __version__

    assert ChickenSession().headers["User-Agent"] == f"chickenstats/{__version__}"
    assert ChickenSession(user_agent="my-team/1.0").headers["User-Agent"] == "my-team/1.0"


def test_the_throttle_spaces_out_requests():
    """With max_requests_per_second, requests start that far apart (N110).

    The throttle reads a fake clock, so the gaps are exact however busy the machine is.
    """
    from types import SimpleNamespace

    import requests

    clock = [100.0]
    starts: list[float] = []

    def sleep(seconds):
        clock[0] += seconds

    def record(self, method, url, *args, **kwargs):
        starts.append(clock[0])
        return MagicMock()

    fake_time = SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep)
    session = ChickenSession(max_requests_per_second=20)
    with patch("chickenstats.utilities.utilities.time", fake_time), patch.object(requests.Session, "request", record):
        for _ in range(4):
            session.request("GET", "https://api-web.nhle.com")

    assert starts == pytest.approx([100.0, 100.05, 100.1, 100.15])


def test_no_throttle_by_default():
    assert ChickenSession()._interval == 0


@pytest.mark.parametrize("rate", [0, -1])
def test_a_throttle_of_zero_or_less_raises(rate):
    from chickenstats.exceptions import InvalidInputError

    with pytest.raises(InvalidInputError, match="max_requests_per_second"):
        ChickenSession(max_requests_per_second=rate)


def test_retry_budget_is_small():
    """An outage costs a few retries per request, not minutes (N66)."""
    adapter = ChickenSession().get_adapter("https://api-web.nhle.com")
    assert isinstance(adapter, ChickenHTTPAdapter)
    retry = adapter.max_retries

    assert (retry.total, retry.connect, retry.read, retry.status) == (3, 2, 1, 3)


def test_retry_after_is_capped():
    """A Retry-After header asking for an hour waits a minute instead (N66)."""
    adapter = ChickenSession().get_adapter("https://api-web.nhle.com")
    assert isinstance(adapter, ChickenHTTPAdapter)
    retry = adapter.max_retries

    assert retry.parse_retry_after("3600") == 60
    assert retry.parse_retry_after("5") == 5
    assert type(retry.increment(method="GET", url="/")) is type(retry)


@pytest.mark.parametrize(
    "copy_session", [lambda session: pickle.loads(pickle.dumps(session)), copy.deepcopy], ids=["pickle", "deepcopy"]
)
def test_a_copied_session_keeps_its_throttle_timeout_and_retries(copy_session):
    """A pickled or copied session sends requests with the original's settings and a lock of its own (in-06)."""
    session = ChickenSession(user_agent="my-team/1.0", max_requests_per_second=4)
    copied = copy_session(session)
    adapter = copied.get_adapter("https://api-web.nhle.com")

    assert copied._interval == 0.25
    assert copied._throttle_lock is not session._throttle_lock
    assert copied.headers["User-Agent"] == "my-team/1.0"
    assert isinstance(adapter, ChickenHTTPAdapter)
    assert adapter.timeout == (3.05, 30)
    assert adapter.max_retries.total == 3

    response = requests.Response()
    response.status_code = 200
    with patch.object(HTTPAdapter, "send", return_value=response) as send:
        assert copied.request("GET", "https://api-web.nhle.com/v1/copied").status_code == 200
    assert send.call_args.kwargs["timeout"] == (3.05, 30)


# -----------------------------------------------------------------------------
# ChickenHTTPAdapter
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# ScrapeSpeedColumn
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# _to_polars
# -----------------------------------------------------------------------------


def test_to_polars_from_polars():
    df = pl.DataFrame({"a": [1, 2]})
    assert _to_polars(df) is df


def test_to_polars_from_lazy():
    lf = pl.LazyFrame({"a": [1, 2]})
    result = _to_polars(lf)
    assert isinstance(result, pl.DataFrame)


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
def test_to_polars_from_pandas():
    df = pd.DataFrame({"a": [1, 2]})
    result = _to_polars(df)
    assert isinstance(result, pl.DataFrame)


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
def test_to_polars_null_dtype_column():
    """Lines 344-345: all-None column is Null dtype → cast to String."""
    df = pd.DataFrame({"col": [1, 2], "empty": [None, None]})
    result = _to_polars(df)
    assert isinstance(result, pl.DataFrame)
    assert result["empty"].dtype == pl.String


# -----------------------------------------------------------------------------
# _to_backend
# -----------------------------------------------------------------------------


def test_to_backend_polars_passthrough():
    df = pl.DataFrame({"a": [1]})
    assert _to_backend(df, "polars") is df


def test_to_backend_narwhals():
    import narwhals as nw

    result = _to_backend(pl.DataFrame({"a": [1]}), "narwhals")
    assert isinstance(result, nw.DataFrame)


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
def test_to_backend_pandas():
    result = _to_backend(pl.DataFrame({"a": [1]}), "pandas")
    assert isinstance(result, pd.DataFrame)


@pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
def test_to_backend_pyarrow():
    result = _to_backend(pl.DataFrame({"a": [1]}), "pyarrow")
    assert isinstance(result, pa.Table)


def test_to_backend_invalid_raises():
    """An unrecognized backend must raise, not silently return polars."""
    with pytest.raises(UnsupportedBackendError):
        _to_backend(pl.DataFrame({"a": [1]}), "not_a_real_backend")


# -----------------------------------------------------------------------------
# _detect_backend
# -----------------------------------------------------------------------------


def test_detect_backend_polars():
    assert _detect_backend(pl.DataFrame()) == "polars"


def test_detect_backend_lazy():
    assert _detect_backend(pl.LazyFrame()) == "polars"


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
def test_detect_backend_pandas():
    """Lines 356-357: pandas DataFrame returns 'pandas'."""
    assert _detect_backend(pd.DataFrame()) == "pandas"


@pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
def test_detect_backend_pyarrow():
    """Lines 363-364: pyarrow Table returns 'pyarrow'."""
    assert _detect_backend(pa.table({"a": [1]})) == "pyarrow"


# -----------------------------------------------------------------------------
# add_cs_mplstyles
# -----------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
def test_add_cs_mplstyles_idempotent():
    """Line 469: second call returns early when already registered."""
    add_cs_mplstyles()
    add_cs_mplstyles()  # hits the `if _STYLES_REGISTERED: return` branch


# -----------------------------------------------------------------------------
# norm_coords
# -----------------------------------------------------------------------------


def two_period_game() -> pl.DataFrame:
    """NSH attacks +x in period 1 and -x in period 2; TBL attacks the other end."""
    return pl.DataFrame(
        {
            "game_id": [1, 1, 1, 1, 1, 1],
            "period": [1, 1, 1, 2, 2, 2],
            "event_team": ["NSH", "NSH", "TBL", "NSH", "NSH", "TBL"],
            "zone": ["OFF", "DEF", "OFF", "OFF", "DEF", "OFF"],
            "coords_x": [70.0, -80.0, -60.0, -70.0, 85.0, 65.0],
            "coords_y": [5.0, 1.0, 2.0, 3.0, -4.0, 0.0],
        }
    )


def test_norm_coords_flips_by_the_end_a_team_attacks():
    """A shot from a team's own half stays in its own half (R125), in every period."""
    result = norm_coords(two_period_game(), normalization_column="event_team", normalization_value="NSH")

    assert result["norm_coords_x"].to_list() == [70.0, -80.0, -60.0, 70.0, -85.0, -65.0]
    assert result["norm_coords_y"].to_list() == [5.0, 1.0, 2.0, -3.0, 4.0, 0.0]
    assert result.columns == [*two_period_game().columns, "norm_coords_x", "norm_coords_y"]


def test_norm_coords_without_game_period_or_zone_flips_by_sign():
    """Without the columns to find the attacking end, every reference-team event is put in the attacking half."""
    result = norm_coords(two_period_game().drop("zone"), normalization_column="event_team", normalization_value="NSH")

    assert result["norm_coords_x"].to_list() == [70.0, 80.0, -60.0, 70.0, 85.0, -65.0]


@pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
def test_norm_coords_keeps_a_pandas_frame():
    result = norm_coords(two_period_game().to_pandas(), normalization_column="event_team", normalization_value="NSH")

    assert result["norm_coords_x"].tolist() == [70.0, -80.0, -60.0, 70.0, -85.0, -65.0]
