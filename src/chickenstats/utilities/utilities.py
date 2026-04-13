from __future__ import annotations

import importlib.resources
from typing import cast
from pathlib import Path

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
    SpinnerColumn,
    Task,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
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
    """Modified Requests session optimized for high-volume scraping."""

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
    """Renders human-readable transfer speed."""

    def render(self, task: Task) -> Text:
        """Show data transfer speed."""
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


class ChickenProgress(Progress):
    """Progress bar to be used across modules."""

    # If you want to change the default columns, this is where you would do so

    progress_columns = (
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
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
    """Indeterminate progress bar to be used across modules."""

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


@nw.narwhalify
def norm_coords(data: pd.DataFrame | pl.DataFrame, normalization_column: str, normalization_value: str) -> IntoFrameT:
    """Function to normalize x and y coordinates. Accepts Narwhals-compatible dataframe.

    All shots for are in an "offensive zone," while all shots against are in the "defensive zone."
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
    if backend == "pandas":
        return frame.to_pandas()
    if backend == "pyarrow":
        return frame.to_arrow()
    return frame.to_pandas()


def charts_directory(target_path: str | Path | None = None) -> None:
    """Creates charts directory in target directory. Defaults to current directory."""
    if not target_path:
        target_path = Path.cwd()

    charts_path = Path(target_path) / "charts"

    if not charts_path.exists():
        charts_path.mkdir()


def data_directory(target_path: str | Path | None = None) -> None:
    """Creates data directory in target directory. Defaults to current directory."""
    if not target_path:
        target_path = Path.cwd()

    data_path = Path(target_path) / "data"

    if not data_path.exists():
        data_path.mkdir()


_STYLES_REGISTERED = False


def add_cs_mplstyles():
    """Add chickenstats matplotlib style to style library for later usage."""
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
