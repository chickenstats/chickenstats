from __future__ import annotations

from chickenstats.chicken_nhl._game_core import _GameCore
from chickenstats.chicken_nhl._game_api import _GameAPIMixin
from chickenstats.chicken_nhl._game_html import _GameHTMLMixin
from chickenstats.chicken_nhl._game_rosters import _GameRostersMixin
from chickenstats.chicken_nhl._game_pbp import _GamePBPMixin


class Game(_GameCore, _GameAPIMixin, _GameHTMLMixin, _GameRostersMixin, _GamePBPMixin):
    """Scrape play-by-play, rosters, shifts, and changes for a single NHL game.

    Parameters:
        game_id: 10-digit NHL game ID, e.g., ``2019020684``. Accepts int, str, or float.
        requests_session: Optional shared ``ChickenSession`` for connection pooling when
            scraping multiple games. A new session is created if not provided.
        backend: DataFrame library to use for ``_df`` properties. One of ``"polars"``
            (default), ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.

    Raises:
        InvalidGameIDError: If ``game_id`` is not a 10-digit integer string.

    Note:
        You can return any of the properties as a polars, pandas, pyarrow, or narwhals
        DataFrame by appending ``_df`` to the property name, e.g., ``game.play_by_play_df``.

    Examples:
        First, instantiate the class with a game ID
        >>> from chickenstats.chicken_nhl import Game
        >>> game = Game(2019020684)

        Scrape play-by-play data
        >>> pbp = game.play_by_play

        Access individual data sources
        >>> shifts = game.shifts
        >>> rosters = game.rosters
        >>> changes = game.changes
        >>> api_events = game.api_events
        >>> html_events = game.html_events

        Return any property as a DataFrame
        >>> pbp_df = game.play_by_play_df
        >>> shifts_df = game.shifts_df

        Use a different DataFrame backend
        >>> game = Game(2019020684, backend="pandas")
        >>> pbp_df = game.play_by_play_df  # pandas DataFrame
    """
