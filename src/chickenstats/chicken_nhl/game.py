from __future__ import annotations

from chickenstats.chicken_nhl._game_core import _GameCore
from chickenstats.chicken_nhl._game_api import _GameAPIMixin
from chickenstats.chicken_nhl._game_html import _GameHTMLMixin
from chickenstats.chicken_nhl._game_rosters import _GameRostersMixin
from chickenstats.chicken_nhl._game_pbp import _GamePBPMixin


class Game(_GameCore, _GameAPIMixin, _GameHTMLMixin, _GameRostersMixin, _GamePBPMixin):
    # noinspection GrazieInspection
    """Class instance for scraping play-by-play and other data for individual games. Utilized within Scraper.

    Parameters:
        game_id (int or float or str):
            10-digit game identifier, e.g., 2023020001
        requests_session (requests.Session, optional):
            If scraping multiple games, can provide single Session object to reduce stress on the API / HTML endpoints
        backend (None | str):
            Whether to use pandas or polars as backend for data manipulation. Defaults to pandas

    Attributes:
        game_id (int):
            10-digit game identifier, e.g., 2019020684
        game_state (str):
            Whether game is scheduled, started, finished, or official, e.g., OFF
        game_schedule_state (str):
            Whether the game has been scheduled, e.g., OK
        current_period (int):
            Current period, or if game has finished, then latest period, e.g., 3
        current_period_type (str):
            Whether period is regular or overtime, e.g., REG
        time_remaining (str):
            Amount of time remaining in the game, e.g., '00:00'
        seconds_remaining (int):
            Amounting of time remaining in the game in seconds, e.g., 0
        running (bool):
            Whether the game is currently running, e.g., False
        in_intermission (bool):
            Whether the game is currently in intermission, e.g., False
        season (int):
            Season in which the game was played, e.g., 20192020
        session (str):
            Whether the game is regular season, playoffs, or pre-season, e.g., R
        html_id (str):
            Game ID used for scraping HTML endpoints, e.g., 020684
        game_date (str):
            Date game was played, e.g., 2020-01-09
        start_time_et (str):
            Start time in Eastern timezone, regardless of venue, e.g., 20:30
        venue (str):
            Venue name, e.g., UNITED CENTER
        tv_broadcasts (dict):
            TV broadcasts information, e.g., {141: {'market': 'A', 'countryCode': 'US', 'network': 'FS-TN'}, ...}
        home_team (dict):
            Home team information, e.g., {'id': 16, 'name': 'BLACKHAWKS', 'abbrev': 'CHI', ...}
        away_team (dict):
            Away team information, e.g., {'id': 18, 'name': 'PREDATORS', 'abbrev': 'NSH', ...}
        api_endpoint (str):
            URL for accessing play-by-play and API rosters, e.g.,
            'https://api-web.nhle.com/v1/gamecenter/2019020684/play-by-play'
        api_endpoint_other (str):
            URL for accessing other game information, e.g.,
            'https://api-web.nhle.com/v1/gamecenter/2019020684/landing'
        html_rosters_endpoint (str):
            URL for accessing rosters from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/RO020684.HTM'
        home_shifts_endpoint (str):
            URL for accessing home shifts from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/TH020684.HTM'
        away_shifts_endpoint (str):
            URL for accessing away shifts from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/TV020684.HTM'
        html_events_endpoint (str):
            URL for accessing events from HTML endpoint, e.g.,
            'https://www.nhl.com/scores/htmlreports/20192020/PL020684.HTM'

    Note:
        You can return any of the properties as a Pandas DataFrame by appending '_df' to the property

    Examples:
        First, instantiate the Game object
        >>> game = Game(2023020001)

        Scrape play-by-play information
        >>> pbp = game.play_by_play  # Returns the data as a list

        Get play-by-play as a Pandas DataFrame
        >>> pbp_df = game.play_by_play_df  # Returns the data as a Pandas DataFrame

        The object stores information from each component of the play-by-play data
        >>> shifts = game.shifts  # Returns a list of shifts
        >>> rosters = game.rosters  # Returns a list of players from both API & HTML endpoints
        >>> changes = game.changes  # Returns a list of changes constructed from shifts & roster data

        Data can also be returned as a Pandas DataFrame, rather than a list
        >>> shifts_df = game.shifts_df  # Same as above, but as Pandas DataFrame

        Access data from API or HTML endpoints, or both
        >>> api_events = game.api_events
        >>> api_rosters = game.api_rosters
        >>> html_events = game.html_events
        >>> html_rosters = game.html_rosters

        The Game object is fairly rich with information
        >>> game_date = game.game_date
        >>> home_team = game.home_team
        >>> game_state = game.game_state
        >>> seconds_remaining = game.seconds_remaining

    """

    # TODO: Add play_by_play_ext information to documentation
    # TODO: Check that documentation reflects roster changes
