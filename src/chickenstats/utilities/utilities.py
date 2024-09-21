import pandas as pd
import requests
from requests.adapters import HTTPAdapter
import urllib3

from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
    ProgressColumn,
    Task,
)

from rich.text import Text


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

        adapter = ChickenHTTPAdapter(
            max_retries=retry, timeout=(connect_timeout, read_timeout)
        )

        self.mount("http://", adapter)
        self.mount("https://", adapter)


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

    def __init__(self, disable: bool = False):
        """Progress bar to be used across modules."""
        super().__init__(
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
            disable=disable,
        )


def prep_p60(df: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    stats_list = [
        "g",
        "ihdg",
        "a1",
        "a2",
        "ixg",
        "isf",
        "ihdsf",
        "imsf",
        "ihdm",
        "iff",
        "ihdf",
        "isb",
        "icf",
        "ibs",
        "igive",
        "itake",
        "ihf",
        "iht",
        "a1_xg",
        "a2_xg",
        "ipent0",
        "ipent2",
        "ipent4",
        "ipent5",
        "ipent10",
        "ipend0",
        "ipend2",
        "ipend4",
        "ipend5",
        "ipend10",
        "gf",
        "ga",
        "hdgf",
        "hdga",
        "xgf",
        "xga",
        "sf",
        "sa",
        "hdsf",
        "hdsa",
        "ff",
        "fa",
        "hdff",
        "hdfa",
        "cf",
        "ca",
        "bsf",
        "bsa",
        "msf",
        "msa",
        "hdmsf",
        "hdmsa",
        "teammate_block",
        "hf",
        "ht",
        "give",
        "take",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
    ]

    stats_list = [x for x in stats_list if x in df.columns]

    for stat in stats_list:
        df[f"{stat}_p60"] = (df[f"{stat}"] / df.toi) * 60

    return df


def prep_oi_percent(df: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    stats_for = [
        "gf",
        "hdgf",
        "xgf",
        "sf",
        "hdsf",
        "ff",
        "hdff",
        "cf",
        "bsf",
        "msf",
        "hdmsf",
        "hf",
        "take",
    ]

    stats_against = [
        "ga",
        "hdga",
        "xga",
        "sa",
        "hdsa",
        "fa",
        "hdfa",
        "ca",
        "bsa",
        "msa",
        "hdmsa",
        "ht",
        "give",
    ]

    stats_tuples = list(zip(stats_for, stats_against))

    for stat_for, stat_against in stats_tuples:
        if stat_for not in df.columns:
            df[f"{stat_for}_percent"] = 0

        elif stat_against not in df.columns:
            df[f"{stat_for}_percent"] = 1

        else:
            df[f"{stat_for}_percent"] = df[f"{stat_for}"] / (
                df[f"{stat_for}"] + df[f"{stat_against}"]
            )

    return df
