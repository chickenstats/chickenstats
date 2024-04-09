import requests
from requests.adapters import HTTPAdapter
import urllib3

import numpy as np
import pandas as pd

from rich.progress import (
    ProgressColumn,
    Task,
)

from rich.text import Text


# This function & the timeout class are used for scraping throughout
class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = 3

        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]

            del kwargs["timeout"]

        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")

        if timeout is None:
            kwargs["timeout"] = self.timeout

        return super().send(request, **kwargs)


def s_session() -> requests.Session:
    """Creates a requests Session object using the HTTPAdapter from above"""

    s = requests.Session()

    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
    headers = {"User-Agent": user_agent}
    s.headers.update(headers)

    retry = urllib3.Retry(
        total=7,
        backoff_factor=2,
        respect_retry_after_header=False,
        status_forcelist=[54, 60, 401, 403, 404, 408, 429, 500, 502, 503, 504],
    )

    connect_timeout = 3
    read_timeout = 10

    adapter = TimeoutHTTPAdapter(
        max_retries=retry, timeout=(connect_timeout, read_timeout)
    )

    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s


# General helper functions


def return_name_html(info: str) -> str:
    """
    Function from Harry Shomer's GitHub

    In the PBP html the name is in a format like: 'Center - MIKE RICHARDS'
    Some also have a hyphen in their last name so can't just split by '-'
    """
    s = info.index("-")  # Find first hyphen
    return info[s + 1 :].strip(" ")  # The name should be after the first hyphen


def hs_strip_html(td: list) -> list:
    """
    Function from Harry Shomer's GitHub, which I took from Patrick Bacon

    Parses html for html events function
    """
    for y in range(len(td)):
        # Get the 'br' tag for the time column...this gets us time remaining instead of elapsed and remaining combined
        if y == 3:
            td[y] = td[
                y
            ].get_text()  # This gets us elapsed and remaining combined-< 3:0017:00
            index = td[y].find(":")
            td[y] = td[y][: index + 3]
        elif (y == 6 or y == 7) and td[0] != "#":
            # 6 & 7-> These are the player 1 ice one's
            # The second statement controls for when it's just a header
            baz = td[y].find_all("td")
            bar = [
                baz[z] for z in range(len(baz)) if z % 4 != 0
            ]  # Because of previous step we get repeats...delete some

            # The setup in the list is now: Name/Number->Position->Blank...and repeat
            # Now strip all the html
            players = []
            for i in range(len(bar)):
                if i % 3 == 0:
                    try:
                        name = return_name_html(bar[i].find("font")["title"])
                        number = (
                            bar[i].get_text().strip("\n")
                        )  # Get number and strip leading/trailing newlines
                    except KeyError:
                        name = ""
                        number = ""
                elif i % 3 == 1:
                    if name != "":
                        position = bar[i].get_text()
                        players.append([name, number, position])

            td[y] = players
        else:
            td[y] = td[y].get_text()

    return td


def convert_to_list(
    obj: str | list | float | int | pd.Series | np.ndarray, object_type: str
) -> list:
    """If the object is not a list, converts the object to a list of length one"""

    if (
        isinstance(obj, str) is True
        or isinstance(obj, (int, np.integer)) is True
        or isinstance(obj, (float, np.float64)) is True
    ):
        obj = [int(obj)]

    elif isinstance(obj, pd.Series) is True or isinstance(obj, np.ndarray) is True:
        obj = obj.tolist()

    elif isinstance(obj, tuple) is True:
        obj = list(obj)

    elif isinstance(obj, list) is True:
        pass

    else:
        raise Exception(
            f"'{obj}' not a supported {object_type} or range of {object_type}s"
        )

    return obj


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
                pbar_text = f"{speed} s/it"

            else:
                pbar_text = f"{speed} it/s"

        return Text(pbar_text, style="progress.data.speed")
