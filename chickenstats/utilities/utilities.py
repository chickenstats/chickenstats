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

        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.4.1 Safari/605.1.15"
        )
        headers = {"User-Agent": user_agent}
        self.headers = headers

        retry = urllib3.Retry(
            total=7,
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
