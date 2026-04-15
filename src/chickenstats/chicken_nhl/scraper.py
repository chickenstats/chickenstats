from __future__ import annotations

from chickenstats.chicken_nhl._scraper_core import _ScraperCore
from chickenstats.chicken_nhl._scraper_raw import _ScraperRawMixin
from chickenstats.chicken_nhl._scraper_stats import _ScraperStatsMixin


class Scraper(_ScraperCore, _ScraperRawMixin, _ScraperStatsMixin):
    # noinspection GrazieInspection
    """Class instance for scraping play-by-play and other data for NHL games.

    Parameters:
        game_ids (list[str | float | int] | pd.Series | str | float | int):
            List of 10-digit game identifier, e.g., `[2023020001, 2023020002, 2023020003]`
        disable_progress_bar (bool):
            If true, disables the progress bar
        backend (None | str):
            Whether to use pandas or polars as backend for data manipulation. Defaults to pandas

    Attributes:
        game_ids (list):
            Game IDs that the Scraper will access, e.g., `[2023020001, 2023020002, 2023020003]`

    Examples:
        First, instantiate the Scraper object
        >>> game_ids = list(range(2023020001, 2023020011))
        >>> scraper = Scraper(game_ids)

        Scrape play-by-play information
        >>> pbp = scraper.play_by_play

        The object stores information from each component of the play-by-play data
        >>> shifts = scraper.shifts
        >>> rosters = scraper.rosters
        >>> changes = scraper.changes

        Access data from API or HTML endpoints, or both
        >>> api_events = scraper.api_events
        >>> api_rosters = scraper.api_rosters
        >>> html_events = scraper.html_events
        >>> html_rosters = scraper.html_rosters

    """
