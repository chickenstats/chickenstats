"""Core utilities: progress bars, HTTP session, coordinate helpers, and directory setup.

Classes:
    ChickenProgress: Rich progress bar with spinner, bar, %, elapsed/remaining time, M-of-N counts, and scrape speed.
    ChickenProgressIndeterminate: Simplified progress bar for operations where the total count is unknown.
    ChickenSession: Requests session pre-configured with retries, timeouts, and connection pooling.

Functions:
    norm_coords: Normalize shot coordinates so all shots for a reference team travel in the same direction.
    charts_directory: Create (or confirm) a ``charts/`` subdirectory and return its Path.
    data_directory: Create (or confirm) a ``data/`` subdirectory and return its Path.
    add_cs_mplstyles: Register the ``'chickenstats'`` and ``'chickenstats_dark'`` matplotlib styles.

Private helpers (used internally, not part of the public API):
    _to_polars, _detect_backend, _to_backend: Multi-backend DataFrame conversion utilities.
"""

from __future__ import annotations

import datetime
import importlib.resources
from collections.abc import Iterable
from typing import cast
from pathlib import Path

from rich.console import Console

import narwhals as nw
import pandas as pd
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

    def __init__(self, *args, **kwargs):
        """Initializes HTTPAdapter for managing requests timeouts."""
        self.timeout = kwargs.pop("timeout", 5)

        super().__init__(*args, **kwargs)

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        """Modifies the HTTPAdapter's send method to manage requests timeouts."""
        if timeout is None:
            timeout = self.timeout
        return super().send(request, stream=stream, timeout=timeout, verify=verify, cert=cert, proxies=proxies)


class ChickenSession(requests.Session):
    """Requests session pre-configured for reliable, high-volume NHL API scraping.

    Configuration applied on construction (not user-configurable without subclassing):

    Retries:
        Up to 5 automatic retries with 1 s exponential backoff. Retries on
        HTTP 408, 429, 500, 502, 503, and 504. Respects ``Retry-After`` response
        headers. Retry logic applies to GET, HEAD, and OPTIONS only.

    Timeouts:
        3.05 s connect timeout, 15 s read timeout. The fractional connect
        timeout avoids synchronising with a 3 s TCP timeout boundary.

    Connection pooling:
        10 pool connections, 150 pool maxsize — suitable for concurrent
        scraping across multiple threads.

    Headers:
        Chrome-compatible ``User-Agent``, ``Accept``, ``Accept-Encoding``,
        and ``Connection: keep-alive`` set by default.

    Examples:
        >>> from chickenstats.utilities import ChickenSession
        >>> with ChickenSession() as session:
        ...     data = session.get("https://api-web.nhle.com/v1/schedule/now").json()

        Update headers for a specific request context:

        >>> session = ChickenSession()
        >>> session.update_headers({"Accept-Language": "en-US"})
    """

    def __init__(self):
        """Initializes Requests Session object."""
        super().__init__()

        retry = urllib3.Retry(
            total=5,
            backoff_factor=1,
            respect_retry_after_header=True,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        connect_timeout = 3.05
        read_timeout = 15

        adapter = ChickenHTTPAdapter(
            max_retries=retry, timeout=(connect_timeout, read_timeout), pool_connections=10, pool_maxsize=150
        )

        self.mount("http://", adapter)
        self.mount("https://", adapter)

        self.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Encoding": "gzip, deflate",
                "Accept": "*/*",
                "Connection": "keep-alive",
            }
        )

    def update_headers(self, headers: dict) -> None:
        """Updates session headers dynamically."""
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
            to fully customise the display.
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
            to fully customise the display.
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

    A coordinate pair is flipped when:
        - The event belongs to the reference team (``normalization_column == normalization_value``)
          AND ``coords_x < 0`` (the puck is in the reference team's defensive half), OR
        - The event belongs to the opposing team AND ``coords_x > 0``.

    After normalization, all offensive-zone events for the reference team have
    ``norm_coords_x > 0`` and all defensive-zone events have ``norm_coords_x < 0``.

    Accepts any narwhals-compatible DataFrame (Polars, pandas, PyArrow) and returns
    the same type.

    Parameters:
        data: A narwhals-compatible DataFrame containing ``coords_x`` and ``coords_y`` columns.
        normalization_column (str): Name of the column that identifies the reference team or
            player perspective (e.g. ``"event_team"``).
        normalization_value (str): The value in ``normalization_column`` that defines the
            reference perspective (e.g. ``"TOR"``).

    Returns:
        DataFrame of the same type as ``data``, with ``norm_coords_x`` and ``norm_coords_y``
        columns appended.

    Examples:
        >>> from chickenstats.utilities import norm_coords
        >>> # Normalize so all TOR shots travel toward coords_x > 0
        >>> pbp_norm = norm_coords(pbp, normalization_column="event_team", normalization_value="TOR")
    """
    df = nw.from_native(data)

    normalization_conditions = (nw.col(f"{normalization_column}") == normalization_value) & (nw.col("coords_x") < 0)
    opposition_conditions = (nw.col(f"{normalization_column}") != normalization_value) & (nw.col("coords_x") > 0)

    test_conditions = normalization_conditions | opposition_conditions

    df = df.with_columns(
        norm_coords_x=nw.when(test_conditions).then(nw.col("coords_x") * -1).otherwise(nw.col("coords_x")),
        norm_coords_y=nw.when(test_conditions).then(nw.col("coords_y") * -1).otherwise(nw.col("coords_y")),
    )

    return df.to_native()  # ty: ignore[invalid-return-type]


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
        return frame.to_pandas()
    if backend == "pyarrow":
        return frame.to_arrow()
    return df


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
    if not target_path:
        target_path = Path.cwd()

    charts_path = Path(target_path) / "charts"

    if not charts_path.exists():
        charts_path.mkdir()

    return charts_path


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
    if not target_path:
        target_path = Path.cwd()

    data_path = Path(target_path) / "data"

    if not data_path.exists():
        data_path.mkdir()

    return data_path


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

    import matplotlib.pyplot as plt
    from matplotlib import rc_params_from_file

    styles = {}

    style_files: list[str] = ["chickenstats.mplstyle", "chickenstats_dark.mplstyle"]

    for style_file in style_files:
        with importlib.resources.as_file(
            importlib.resources.files("chickenstats.utilities.styles").joinpath(style_file)
        ) as file:
            style_name = Path(style_file).stem
            styles[style_name] = rc_params_from_file(file, use_default_template=False)

    plt.style.core.update_nested_dict(plt.style.library, styles)  # ty: ignore[unresolved-attribute]
    plt.style.core.available[:] = sorted(plt.style.library.keys())

    _STYLES_REGISTERED = True
