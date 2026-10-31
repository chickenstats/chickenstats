"""Core utilities: progress bars, HTTP session, coordinate normalization, and directory setup."""

from __future__ import annotations

import contextlib
import datetime
import importlib.metadata
import importlib.resources
import threading
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import pandas as pd
from pathlib import Path

from rich.console import Console

from chickenstats.exceptions import InvalidInputError, UnsupportedBackendError

import narwhals as nw
import numpy as np
import polars as pl
import requests
import urllib3
from narwhals.typing import IntoFrameT
from requests.adapters import HTTPAdapter
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    ProgressType,
    SpinnerColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text


class ChickenHTTPAdapter(HTTPAdapter):
    """Modified HTTPAdapter for managing requests timeouts and connection pooling."""

    # Keep the timeout when pickled
    __attrs__ = [*HTTPAdapter.__attrs__, "timeout"]

    def __init__(self, *args, **kwargs):
        """Initializes HTTPAdapter for managing requests timeouts."""
        self.timeout = kwargs.pop("timeout", 5)

        super().__init__(*args, **kwargs)

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Apply the configured timeout when the caller doesn't pass one."""
        if timeout is None:
            timeout = self.timeout
        return super().send(request, stream=stream, timeout=timeout, verify=verify, cert=cert, proxies=proxies)


# The longest a Retry-After header can make a request wait
MAX_RETRY_AFTER = 60


class _CappedRetry(urllib3.Retry):
    """A Retry that waits at most MAX_RETRY_AFTER seconds for a Retry-After header."""

    def parse_retry_after(self, retry_after: str) -> float:
        """Return the header's wait in seconds, capped at MAX_RETRY_AFTER."""
        return min(super().parse_retry_after(retry_after), MAX_RETRY_AFTER)


def _default_user_agent() -> str:
    """The User-Agent chickenstats sends unless told otherwise: the package and its version."""
    try:
        version = importlib.metadata.version("chickenstats")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return f"chickenstats/{version}"


class ChickenSession(requests.Session):
    """Requests session pre-configured for reliable, high-volume scraping.

    Parameters:
        user_agent (str | None):
            The ``User-Agent`` header sent with every request. Defaults to
            ``chickenstats/<version>``, so the sites being read can tell where the
            traffic comes from.
        max_requests_per_second (float | None):
            The most requests the session starts in one second, across every
            thread that shares it. Defaults to ``None``, no limit.

    Raises:
        InvalidInputError: If ``max_requests_per_second`` is zero or negative.

    Retries:
        Up to 3 automatic retries with 1s exponential backoff: at most 2 for a
        failed connection, 1 for a failed read and 3 for HTTP 408, 429, 500, 502,
        503 and 504. Respects ``Retry-After`` response headers, for up to 60
        seconds. Retry logic applies to GET, HEAD, and OPTIONS only.

    Timeouts:
        3.05s connect timeout, 30s read timeout. The fractional connect
        timeout avoids synchronizing with a 3s TCP timeout boundary.

    Connection pooling:
        10 pool connections, 150 pool maxsize — suitable for concurrent
        scraping across multiple threads. The underlying urllib3 connection
        pool is thread-safe for concurrent ``get()``/``post()`` calls; this is
        what lets ``Scraper``/``Game`` share one ``ChickenSession`` instance
        across ``ThreadPoolExecutor`` prefetch tasks. That safety only holds
        if the session's own mutable state (headers, cookies, auth) isn't
        changed while requests are in flight — see ``update_headers()``.

    Headers:
        The ``User-Agent`` above, plus ``Accept``, ``Accept-Encoding`` and
        ``Connection: keep-alive``.

    Examples:
        >>> from chickenstats.utilities import ChickenSession
        >>> with ChickenSession() as session:
        ...     data = session.get("https://api-web.nhle.com/v1/schedule/now").json()

        Send at most two requests a second, and pass the session to a Scraper:

        >>> from chickenstats.chicken_nhl import Scraper
        >>> session = ChickenSession(max_requests_per_second=2)
        >>> scraper = Scraper([2023020001], requests_session=session)

        Update headers for a specific request context:

        >>> session = ChickenSession()
        >>> session.update_headers({"Accept-Language": "en-US"})
    """

    # Keep the throttle when pickled
    __attrs__ = [*requests.Session.__attrs__, "_interval"]

    def __init__(self, user_agent: str | None = None, max_requests_per_second: float | None = None):
        """Initializes Requests Session object."""
        super().__init__()

        if max_requests_per_second is not None and max_requests_per_second <= 0:
            raise InvalidInputError(
                f"max_requests_per_second must be greater than 0, not {max_requests_per_second!r}. "
                "Pass None for no limit."
            )

        # Seconds between the starts of two requests; 0 is no limit
        self._interval: float = 1 / max_requests_per_second if max_requests_per_second else 0.0
        self._next_request: float = 0.0
        self._throttle_lock = threading.Lock()

        # Small budgets, so an NHL outage costs seconds, not minutes
        retry = _CappedRetry(
            total=3,
            connect=2,
            read=1,
            status=3,
            backoff_factor=1,
            respect_retry_after_header=True,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        connect_timeout = 3.05
        read_timeout = 30

        adapter = ChickenHTTPAdapter(
            max_retries=retry, timeout=(connect_timeout, read_timeout), pool_connections=10, pool_maxsize=150
        )

        self.mount("http://", adapter)
        self.mount("https://", adapter)

        self.headers.update(
            {
                "User-Agent": user_agent or _default_user_agent(),
                "Accept-Encoding": "gzip, deflate",
                "Accept": "*/*",
                "Connection": "keep-alive",
            }
        )

    def __setstate__(self, state: dict) -> None:
        """Restore a pickled or copied session, with a new lock, since a lock cannot be copied."""
        super().__setstate__(state)
        self._next_request = 0.0
        self._throttle_lock = threading.Lock()

    def request(self, method, url, *args, **kwargs):
        """Send a request, first waiting out the throttle when ``max_requests_per_second`` is set."""
        if self._interval:
            # Each request claims the next start time under the lock, then sleeps outside it
            with self._throttle_lock:
                now = time.monotonic()
                start = max(now, self._next_request)
                self._next_request = start + self._interval
            if start > now:
                time.sleep(start - now)
        return super().request(method, url, *args, **kwargs)

    def update_headers(self, headers: dict) -> None:
        """Updates session headers dynamically.

        Not safe to call while this session has requests in flight on other
        threads (e.g. during a ``Scraper``/``Game`` prefetch) — ``headers`` is
        shared, mutable state, unlike the underlying connection pool. Call
        this before starting concurrent work, not during it.
        """
        self.headers.update(headers)


class ScrapeSpeedColumn(ProgressColumn):
    """Rich progress column that renders scrape throughput.

    Displays ``X.XX it/s`` when the task is completing more than one item per
    second, or ``X.XX s/it`` when each item takes longer than a second. Falls
    back to ``"?"`` before the first item completes.

    Used automatically as the last column in ``ChickenProgress``.
    """

    def render(self, task: Task) -> Text:
        """Render current scrape speed as a Rich Text object."""
        speed = task.finished_speed or task.speed

        if speed is None and task.elapsed is not None and task.elapsed > 0:
            speed = task.completed / task.elapsed

        if not speed:
            return Text("?", style="progress.data.speed")

        if speed < 1:
            inverted_speed = 1 / speed
            pbar_text = f"{inverted_speed:.2f} s/it"
        else:
            pbar_text = f"{speed:.2f} it/s"

        return Text(pbar_text, style="progress.data.speed")


class ChickenTimeRemainingColumn(ProgressColumn):
    """Rich progress column that estimates time remaining with an early fallback.

    Falls back to ``elapsed * (total - completed) / completed`` the moment the
    first item completes, rather than waiting for Rich's sliding-window speed
    estimate. Useful for outer progress bars that advance infrequently (e.g.
    once per season).
    """

    def render(self, task: Task) -> Text:
        """Render estimated time remaining as a Rich Text object."""
        remaining = task.time_remaining

        if remaining is None and task.completed > 0 and task.elapsed is not None and task.total is not None:
            remaining = task.elapsed * (task.total - task.completed) / task.completed

        if remaining is None:
            return Text("-:--:--", style="progress.remaining")

        return Text(str(datetime.timedelta(seconds=int(remaining))), style="progress.remaining")


class ChickenProgress(Progress):
    """Rich progress bar for scraping tasks with a known total.

    Default column layout (left → right):
        description · spinner · bar · % complete · elapsed · remaining · M/N count · speed

    Parameters:
        *columns: Override the default column layout entirely. When omitted, the built-in
            layout above is used. Pass Rich ``ProgressColumn`` instances or markup strings
            to fully customize the display.
        console (rich.Console | None): Custom Rich Console to write to. Use this to redirect
            output to a file, change terminal width, or share a console across multiple
            progress contexts. Default ``None`` (creates a new Console).
        disable (bool): Suppress all output when ``True``. Default ``False``.
        transient (bool): Erase the bar from the terminal on completion. Default ``False``.
        expand (bool): Stretch the bar to the full terminal width. Default ``False``.
        auto_refresh (bool): Automatically redraw at ``refresh_per_second`` Hz. Set to
            ``False`` for manual control (e.g. Jupyter notebooks). Default ``True``.
        speed_estimate_period (float): Seconds of history used to compute the speed
            estimate shown in the last column. Default ``30.0``.

    Examples:
        >>> from chickenstats.utilities import ChickenProgress
        >>> games = [20001, 20002, 20003]
        >>> with ChickenProgress() as progress:
        ...     task = progress.add_task("Scraping games...", total=len(games))
        ...     for game_id in games:
        ...         # ... fetch game data
        ...         progress.update(task, advance=1)

        Redirect output to stderr with a custom Console:

        >>> from rich.console import Console
        >>> with ChickenProgress(console=Console(stderr=True)) as progress:
        ...     task = progress.add_task("Scraping...", total=len(games))
        ...     for game_id in games:
        ...         progress.update(task, advance=1)

        Build a custom column layout reusing the built-in speed column:

        >>> from chickenstats.utilities import ChickenProgress, ScrapeSpeedColumn
        >>> from rich.progress import SpinnerColumn, TextColumn
        >>> with ChickenProgress(TextColumn("{task.description}"), SpinnerColumn(), ScrapeSpeedColumn()) as progress:
        ...     task = progress.add_task("Custom layout", total=len(games))
        ...     for game_id in games:
        ...         progress.update(task, advance=1)

        Silence the bar entirely (e.g. in CI or batch jobs):

        >>> with ChickenProgress(disable=True) as progress:
        ...     task = progress.add_task("Scraping...", total=len(games))
        ...     for game_id in games:
        ...         progress.update(task, advance=1)
    """

    # To change the column layout, update progress_columns below

    progress_columns = (
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        ChickenTimeRemainingColumn(),
        TextColumn("•"),
        MofNCompleteColumn(),
        TextColumn("•"),
        ScrapeSpeedColumn(),
    )

    @classmethod
    def get_default_columns(cls):
        """Return the default column layout for this progress bar."""
        return cls.progress_columns


class ChickenProgressIndeterminate(Progress):
    """Rich progress bar for operations where the total count is unknown.

    Default column layout (left → right):
        description · spinner · bar · elapsed time

    Use this when the number of items to process isn't known upfront (e.g.
    paginated API responses, streaming data). For tasks with a known total,
    prefer ``ChickenProgress``.

    Parameters:
        *columns: Override the default column layout entirely. When omitted, the built-in
            layout above is used. Pass Rich ``ProgressColumn`` instances or markup strings
            to fully customize the display.
        console (rich.Console | None): Custom Rich Console to write to. Default ``None``
            (creates a new Console).
        disable (bool): Suppress all output when ``True``. Default ``False``.
        transient (bool): Erase the bar from the terminal on completion. Default ``False``.
        expand (bool): Stretch the bar to the full terminal width. Default ``False``.
        auto_refresh (bool): Automatically redraw at ``refresh_per_second`` Hz. Default ``True``.

    Examples:
        >>> from chickenstats.utilities import ChickenProgressIndeterminate
        >>> with ChickenProgressIndeterminate() as progress:
        ...     task = progress.add_task("Fetching schedule...", total=None)
        ...     for page in paginated_api():
        ...         # ... process page
        ...         progress.update(task, advance=1)
    """

    progress_columns = (
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    )

    @classmethod
    def get_default_columns(cls):
        """Return the default column layout for this progress bar."""
        return cls.progress_columns


def track(
    sequence: Iterable[ProgressType],
    description: str = "Working...",
    total: float | None = None,
    completed: int = 0,
    update_period: float = 0.1,
    console: Console | None = None,
    transient: bool = False,
    disable: bool = False,
    speed_estimate_period: float = 30.0,
) -> Iterable[ProgressType]:
    """Wrap an iterable with a ChickenProgress bar, yielding each item.

    One-liner alternative to the full context-manager pattern. Mirrors
    ``rich.progress.track`` but uses ChickenProgress's custom columns
    (spinner, bar, %, elapsed, remaining, M/N count, speed).

    Parameters:
        sequence: Any iterable to track. If it has ``__len__``, ``total`` is inferred
            automatically; pass ``total`` explicitly for generators.
        description: Label shown to the left of the bar. Default ``"Working..."``.
        total: Override the item count. Inferred from ``len(sequence)`` when omitted.
        completed: Number of items already done at start. Default ``0``.
        update_period: Minimum seconds between display refreshes. Default ``0.1``.
        console: Custom Rich Console (e.g. to redirect to stderr). Default ``None``.
        transient: Erase the bar on completion. Default ``False``.
        disable: Suppress all output. Default ``False``.
        speed_estimate_period: Seconds of history used for the speed estimate. Default ``30.0``.

    Examples:
        >>> from chickenstats.utilities import track
        >>> games = [20001, 20002, 20003]
        >>> for game_id in track(games, "Scraping games..."):
        ...     pass  # fetch game data

        Silence output in CI or batch jobs:

        >>> for game_id in track(games, disable=True):
        ...     pass
    """
    with ChickenProgress(
        console=console, transient=transient, disable=disable, speed_estimate_period=speed_estimate_period
    ) as progress:
        yield from progress.track(
            sequence, total=total, completed=completed, description=description, update_period=update_period
        )


@nw.narwhalify
def norm_coords(data: pd.DataFrame | pl.DataFrame, normalization_column: str, normalization_value: str) -> IntoFrameT:
    """Normalize shot coordinates so all shots for a reference team travel in the same direction.

    Adds two new columns — ``norm_coords_x`` and ``norm_coords_y`` — that flip the
    sign of ``coords_x`` and ``coords_y`` when needed, leaving the originals intact.
    After normalization the reference team attacks toward ``norm_coords_x > 0`` and its
    opponents toward ``norm_coords_x < 0``, so a shot from the team's own half stays in
    its own half.

    Teams switch ends every period, so the end the reference team attacks is worked out for
    each game and period, from where the offensive-zone events (``zone == "OFF"``) of both
    teams were. That needs ``game_id``, ``period`` and ``zone`` columns. Without them, or in a
    period with no offensive-zone events, an event is flipped by the sign of its ``coords_x``
    alone, which puts every reference-team event in the attacking half.

    Accepts any narwhals-compatible DataFrame (Polars, pandas, PyArrow) and returns
    the same type.

    Parameters:
        data: A narwhals-compatible DataFrame containing ``coords_x`` and ``coords_y`` columns.
        normalization_column (str): Name of the column that identifies the reference team or
            player perspective (e.g. ``"event_team"``).
        normalization_value (str): The value in ``normalization_column`` that defines the
            reference perspective (e.g. ``"NSH"``).

    Returns:
        DataFrame of the same type as ``data``, with ``norm_coords_x`` and ``norm_coords_y``
        columns appended.

    Examples:
        >>> from chickenstats.chicken_nhl import Season, Scraper,
        >>> from chickenstats.utilities import norm_coords
        >>> season = Season(2025)
        >>> schedule = season.schedule("NSH")
        >>> game_ids = schedule["game_id"].to_list()[:10]
        >>> scraper = Scraper(game_ids)
        >>> pbp = scraper.play_by_play
        >>> # Normalize so all NSH shots travel toward coords_x > 0
        >>> pbp_norm = norm_coords(pbp, normalization_column="event_team", normalization_value="NSH")
    """
    df = nw.from_native(data)

    reference = nw.col(normalization_column) == normalization_value
    flip = (reference & (nw.col("coords_x") < 0)) | (~reference & (nw.col("coords_x") > 0))

    keys = ["game_id", "period"]
    if {"game_id", "period", "zone"} <= set(df.columns):
        # Median attacking x per game and period, with the opponents' events mirrored
        attack = (
            df.filter(nw.col("zone") == "OFF", ~nw.col("coords_x").is_null())
            .with_columns(_attack_x=nw.when(reference).then(nw.col("coords_x")).otherwise(nw.col("coords_x") * -1))
            .group_by(keys)
            .agg(nw.col("_attack_x").median())
        )
        df = df.join(attack, on=keys, how="left")
        # Mirror the whole period where the reference team attacks -x
        flip = nw.when(nw.col("_attack_x").is_null()).then(flip).otherwise(nw.col("_attack_x") < 0)

    df = df.with_columns(
        norm_coords_x=nw.when(flip).then(nw.col("coords_x") * -1).otherwise(nw.col("coords_x")),
        norm_coords_y=nw.when(flip).then(nw.col("coords_y") * -1).otherwise(nw.col("coords_y")),
    )

    return df.drop("_attack_x", strict=False).to_native()  # ty: ignore[invalid-return-type]


def _to_polars(frame) -> pl.DataFrame:
    """Convert any narwhals-compatible frame to a Polars DataFrame.

    Handles Polars DataFrame (no-op), Polars LazyFrame (collect), and any
    narwhals-compatible frame (pandas, pyarrow) via Arrow round-trip.
    All-null object columns that become pl.Null dtype via Arrow are cast to String.
    """
    if isinstance(frame, pl.DataFrame):
        return frame
    if isinstance(frame, pl.LazyFrame):
        return frame.collect()
    df = cast(pl.DataFrame, pl.from_arrow(nw.from_native(frame, eager_only=True).to_arrow()))
    null_dtype_cols = [c for c, t in df.schema.items() if t == pl.Null]
    if null_dtype_cols:
        df = df.with_columns([pl.lit(None, dtype=pl.String).alias(c) for c in null_dtype_cols])
    return df


def _detect_backend(frame) -> str:
    """Detect the backend of the input frame ('polars', 'pandas', or 'pyarrow')."""
    if isinstance(frame, (pl.DataFrame, pl.LazyFrame)):
        return "polars"
    try:
        import pandas as _pd  # noqa: PLC0415

        if isinstance(frame, _pd.DataFrame):
            return "pandas"
    except ImportError:
        pass
    try:
        import pyarrow as _pa  # noqa: PLC0415

        if isinstance(frame, _pa.Table):
            return "pyarrow"
    except ImportError:
        pass
    return "polars"


def _to_backend(df: pl.DataFrame, backend: str):
    """Convert a Polars DataFrame to the requested output backend."""
    if backend == "polars":
        return df
    frame = nw.from_native(df, eager_only=True)
    if backend == "narwhals":
        return frame
    if backend == "pandas":
        try:
            return frame.to_pandas()
        except ImportError as exc:
            raise ImportError(
                "pandas is required for backend='pandas'. Install with: pip install chickenstats[pandas]"
            ) from exc
    if backend == "pyarrow":
        try:
            return frame.to_arrow()
        except ImportError as exc:
            raise ImportError(
                "pyarrow is required for backend='pyarrow'. Install with: pip install chickenstats[pyarrow]"
            ) from exc
    raise UnsupportedBackendError(
        f"Unsupported backend: {backend!r}. Expected one of 'polars', 'pandas', 'pyarrow', 'narwhals'."
    )


def _subdirectory(name: str, target_path: str | Path | None) -> Path:
    """Create a name/ directory under target_path, or the working directory, and return its path."""
    path = Path(target_path or Path.cwd()) / name

    if not path.exists():
        path.mkdir()

    return path


def charts_directory(target_path: str | Path | None = None) -> Path:
    """Create a ``charts/`` subdirectory and return its path.

    Creates the directory if it does not already exist. Safe to call
    repeatedly — no error is raised if the directory is already present.

    Parameters:
        target_path (str | Path | None): Parent directory. Defaults to the
            current working directory when ``None``.

    Returns:
        Path: Path to the ``charts/`` directory.

    Examples:
        >>> from chickenstats.utilities import charts_directory
        >>> charts_dir = charts_directory()  # cwd/charts/
        >>> out = charts_directory() / "shot_chart.png"
    """
    return _subdirectory("charts", target_path)


def data_directory(target_path: str | Path | None = None) -> Path:
    """Create a ``data/`` subdirectory and return its path.

    Creates the directory if it does not already exist. Safe to call
    repeatedly — no error is raised if the directory is already present.

    Parameters:
        target_path (str | Path | None): Parent directory. Defaults to the
            current working directory when ``None``.

    Returns:
        Path: Path to the ``data/`` directory.

    Examples:
        >>> from chickenstats.utilities import data_directory
        >>> data_dir = data_directory()  # cwd/data/
        >>> out = data_directory() / "pbp.parquet"
    """
    return _subdirectory("data", target_path)


_STYLES_REGISTERED = False


def add_cs_mplstyles() -> None:
    """Register chickenstats matplotlib styles with the active matplotlib installation.

    Registers two styles:
        ``'chickenstats'``:      Light theme — white background, dimgray text, no top/right spines.
        ``'chickenstats_dark'``: Dark theme — black background, white text, custom color palette.

    This function is called automatically when ``chickenstats.utilities`` is imported,
    so ``plt.style.use('chickenstats')`` works immediately after any utilities import.
    Calling it again is safe — registration is skipped if already done.

    Examples:
        >>> import matplotlib.pyplot as plt
        >>> import chickenstats.utilities  # triggers registration automatically
        >>> plt.style.use("chickenstats")

        Or call explicitly if needed:

        >>> from chickenstats.utilities import add_cs_mplstyles
        >>> add_cs_mplstyles()
        >>> plt.style.use("chickenstats_dark")
    """
    global _STYLES_REGISTERED
    if _STYLES_REGISTERED:
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib import rc_params_from_file
    except ImportError:
        return

    styles = {}

    style_files: list[str] = ["chickenstats.mplstyle", "chickenstats_dark.mplstyle"]

    for style_file in style_files:
        with importlib.resources.as_file(
            importlib.resources.files("chickenstats.utilities.styles").joinpath(style_file)
        ) as file:
            style_name = Path(style_file).stem
            styles[style_name] = rc_params_from_file(file, use_default_template=False)

    if hasattr(plt.style, "core"):
        plt.style.core.update_nested_dict(plt.style.library, styles)
        plt.style.core.available[:] = sorted(plt.style.library)
    else:
        plt.style.library.update(styles)
        if hasattr(plt.style, "available"):
            with contextlib.suppress(Exception):
                plt.style.available[:] = sorted(plt.style.library)

    _STYLES_REGISTERED = True


def _is_pandas_series(obj) -> bool:
    """Return True if obj is a pandas Series, without hard-requiring pandas."""
    try:
        import pandas as _pd  # noqa: PLC0415
    except ImportError:
        return False
    return isinstance(obj, _pd.Series)


def convert_to_list(obj: str | list | float | int | pd.Series | np.ndarray, object_type: str) -> list:
    """Normalize ``obj`` to a plain Python list.

    Scalar inputs (str, int, float) are cast to int when they can be, then wrapped in a list.
    ``pd.Series`` and ``np.ndarray`` are converted via ``.tolist()``.
    Tuples are cast with ``list()``. Existing lists are returned unchanged.

    Parameters:
        obj: The value to normalize.
        object_type: Human-readable name for the input type, used in the error message.

    Raises:
        InvalidInputError: If ``obj`` is not a recognized type.
    """
    if isinstance(obj, str | int | float | np.integer):
        try:
            obj = [int(obj)]

        except ValueError:
            obj = [obj]

    elif isinstance(obj, np.ndarray) or _is_pandas_series(obj):
        obj = obj.tolist()  # ty: ignore[unresolved-attribute]

    elif isinstance(obj, tuple):
        obj = list(obj)

    elif not isinstance(obj, list):
        raise InvalidInputError(
            f"'{obj}' not a supported {object_type} or range of {object_type}s — expected a str, "
            "int, float, list, tuple, pd.Series, or np.ndarray",
            obj=obj,
            object_type=object_type,
        )

    return obj
