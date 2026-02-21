import importlib.resources

import matplotlib.pyplot as plt
import requests
import urllib3
from matplotlib import rc_params_from_file
from requests.adapters import HTTPAdapter
from rich.progress import (
    BarColumn,
    GetTimeCallable,
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
import rich
from collections.abc import Sequence


class ChickenHTTPAdapter(HTTPAdapter):
    """Modified HTTPAdapter for managing requests timeouts."""

    def __init__(self, *args, **kwargs):
        """Initializes HTTPAdapter for managing requests timeouts."""
        self.timeout = 3

        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]

            del kwargs["timeout"]

        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """Modifies the HTTPAdapter's send method to manage requests timeouts."""
        timeout = kwargs.get("timeout")

        if timeout is None:
            kwargs["timeout"] = self.timeout

        return super().send(request, **kwargs)


class ChickenSession(requests.Session):
    """Modified Requests session for use with chickenstats library."""

    def __init__(self):
        """Initializes Requests Session object."""
        super().__init__()

        retry = urllib3.Retry(
            total=10,
            backoff_factor=2,
            respect_retry_after_header=False,
            status_forcelist=[54, 60, 401, 403, 404, 408, 429, 500, 502, 503, 504],
        )

        connect_timeout = 3
        read_timeout = 10

        adapter = ChickenHTTPAdapter(max_retries=retry, timeout=(connect_timeout, read_timeout))

        # noinspection HttpUrlsUsage
        self.mount("http://", adapter)
        self.mount("https://", adapter)

        # self.headers["User-Agent"] = fake_user_agent.random

    def update_headers(self):
        """Updates headers for a random user agent."""
        # self.headers["User-Agent"] = fake_user_agent.random


class ScrapeSpeedColumn(ProgressColumn):
    """Renders human-readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed")
        else:
            speed = round(speed, 2)

            if speed < 1:
                speed = round(1 / speed, 2)
                pbar_text = f"{speed:.2f} s/it"

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

    def __init__(
        self,
        columns: Sequence = progress_columns,
        console: rich.console.Console | None = None,
        auto_refresh: bool = True,
        refresh_per_second: float = 10,
        speed_estimate_period: float = 30.0,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        get_time: GetTimeCallable | None = None,
        disable: bool = False,
        expand: bool = False,
    ):
        """Progress bar to be used across modules."""
        super().__init__(
            *columns,
            console=console,
            auto_refresh=auto_refresh,
            refresh_per_second=refresh_per_second,
            speed_estimate_period=speed_estimate_period,
            transient=transient,
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
            get_time=get_time,
            disable=disable,
            expand=expand,
        )


class ChickenProgressIndeterminate(Progress):
    """Indeterminate progress bar to be used across modules."""

    def __init__(self, transient: bool = False, disable: bool = False):
        """Progress bar to be used across modules."""
        super().__init__(
            TextColumn("[progress.description]{task.description}"),
            SpinnerColumn(),
            BarColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            disable=disable,
            transient=transient,
        )


def add_cs_mplstyles():
    """Add chickenstats matplotlib style to style library for later usage."""
    styles = dict()

    style_files: list[str] = ["chickenstats.mplstyle", "chickenstats_dark.mplstyle"]

    for style_file in style_files:
        with importlib.resources.as_file(
            importlib.resources.files("chickenstats.utilities.styles").joinpath(style_file)
        ) as file:
            style_name = style_file.replace(".mplstyle", "")
            styles[style_name] = rc_params_from_file(file, use_default_template=False)

    # with importlib.resources.as_file(
    #     importlib.resources.files("chickenstats.utilities.styles").joinpath("chickenstats.mplstyle")
    # ) as file:
    #     styles["chickenstats"] = rc_params_from_file(file, use_default_template=False)
    #
    # with importlib.resources.as_file(
    #     importlib.resources.files("chickenstats.utilities.styles").joinpath("chickenstats_dark.mplstyle")
    # ) as file:
    #     styles["chickenstats_dark"] = rc_params_from_file(file, use_default_template=False)

    # Update dictionary of styles
    plt.style.core.update_nested_dict(plt.style.library, styles)
    plt.style.core.available[:] = sorted(plt.style.library.keys())
