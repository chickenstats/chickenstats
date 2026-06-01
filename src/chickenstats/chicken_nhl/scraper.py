from __future__ import annotations

from chickenstats.chicken_nhl._scraper_core import _ScraperCore
from chickenstats.chicken_nhl._scraper_raw import _ScraperRawMixin
from chickenstats.chicken_nhl._scraper_stats import _ScraperStatsMixin


class Scraper(_ScraperCore, _ScraperRawMixin, _ScraperStatsMixin):
    # noinspection GrazieInspection
    """Class instance for scraping play-by-play and other data for NHL games.

    Parameters:
        game_ids (list[str | float | int] | pd.Series | str | float | int):
            One or more 10-digit game identifiers, e.g., ``[2023020001, 2023020002, 2023020003]``
        disable_progress_bar (bool):
            If ``True``, suppresses the Rich progress bar for all scraping and aggregation
            methods. Individual methods accept the same argument to override this per-call.
            Default ``False``.
        transient_progress_bar (bool):
            If ``True``, clears the progress bar from the terminal after it completes
            rather than leaving it visible. Can be overridden per-call. Default ``False``.
        backend (str):
            DataFrame backend for all returned data. One of ``"polars"`` (default),
            ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.

    Attributes:
        game_ids (list):
            Game IDs tracked by this Scraper, e.g., ``[2023020001, 2023020002, 2023020003]``
        failed_games (list):
            Game IDs that failed to scrape, e.g., ``[2023020005]``

    Examples:
        First, instantiate the Scraper object
        >>> from chickenstats.chicken_nhl import Scraper
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

        Add more game IDs after construction and scrape again
        >>> scraper.add_games(2023020011)
        >>> pbp = scraper.play_by_play  # now includes the new game

        Aggregate individual and on-ice player stats (game-level by default)
        >>> scraper.prep_stats()
        >>> player_stats = scraper.stats

        Aggregate forward or defense line stats
        >>> scraper.prep_lines(position="f")
        >>> fwd_lines = scraper.lines
        >>> scraper.prep_lines(position="d")
        >>> def_lines = scraper.lines

        Aggregate team-level stats
        >>> scraper.prep_team_stats()
        >>> team_stats = scraper.team_stats

        Method chaining — prepare and access in one expression
        >>> stats = scraper.prep_stats(level="season").stats
        >>> lines = scraper.prep_lines(position="d", level="season").lines
        >>> team_stats = scraper.prep_team_stats(level="season").team_stats

    """
