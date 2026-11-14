from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from chickenstats.chicken_nhl._game_core import _GameCore
from chickenstats.chicken_nhl._game_api import _GameAPIMixin
from chickenstats.chicken_nhl._game_html import _GameHTMLMixin
from chickenstats.chicken_nhl._game_rosters import _GameRostersMixin
from chickenstats.chicken_nhl._game_pbp import _GamePBPMixin
from chickenstats.utilities.types import FrameT

if TYPE_CHECKING:
    import pandas as pd
    import polars as pl
    import pyarrow as pa

    from chickenstats.utilities.types import (
        AnyBackend,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )
    from chickenstats.utilities.utilities import ChickenSession


class Game(
    _GameCore[FrameT], _GameAPIMixin[FrameT], _GameHTMLMixin[FrameT], _GameRostersMixin[FrameT], _GamePBPMixin[FrameT]
):
    """Scrape play-by-play, rosters, shifts, and changes for a single NHL game.

    Parameters:
        game_id: 10-digit NHL game ID, e.g., ``2019020684``. Accepts int or str.
        requests_session: Optional shared ``ChickenSession`` for connection pooling when
            scraping multiple games. A new session is created if not provided.
        backend: DataFrame library to use for ``_df`` properties. One of ``"polars"``
            (default), ``"pandas"``, ``"pyarrow"``, or ``"narwhals"``.

    Raises:
        InvalidGameIDError: If ``game_id`` is not a 10-digit integer string.

    Note:
        These properties have a ``_df`` version that returns a polars, pandas, pyarrow, or
        narwhals DataFrame: ``play_by_play``, ``api_events``, ``api_rosters``, ``html_events``,
        ``html_rosters``, ``rosters``, ``shifts``, ``changes`` and ``xg_fields``, e.g.,
        ``game.play_by_play_df``. ``play_by_play_ext`` has no ``_df`` version.

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

        Return a property as a DataFrame
        >>> pbp_df = game.play_by_play_df
        >>> shifts_df = game.shifts_df

        Use a different DataFrame backend
        >>> game = Game(2019020684, backend="pandas")
        >>> pbp_df = game.play_by_play_df  # pandas DataFrame
    """

    # Overloads must live on the public class for type checkers
    if TYPE_CHECKING:

        @overload
        def __init__(
            self: Game[pl.DataFrame],
            game_id: str | int | float,
            *,
            requests_session: ChickenSession | None = None,
            backend: PolarsBackend = "polars",
            _warn_season: bool = True,
        ) -> None: ...
        @overload
        def __init__(
            self: Game[pd.DataFrame],
            game_id: str | int | float,
            *,
            requests_session: ChickenSession | None = None,
            backend: PandasBackend,
            _warn_season: bool = True,
        ) -> None: ...
        @overload
        def __init__(
            self: Game[pa.Table],
            game_id: str | int | float,
            *,
            requests_session: ChickenSession | None = None,
            backend: PyarrowBackend,
            _warn_season: bool = True,
        ) -> None: ...
        @overload
        def __init__(
            self: Game[NarwhalsFrame],
            game_id: str | int | float,
            *,
            requests_session: ChickenSession | None = None,
            backend: NarwhalsBackend,
            _warn_season: bool = True,
        ) -> None: ...
        @overload
        def __init__(
            self: Game[Any],
            game_id: str | int | float,
            *,
            requests_session: ChickenSession | None = None,
            backend: AnyBackend = "polars",
            _warn_season: bool = True,
        ) -> None: ...
        def __init__(  # noqa: D107
            self,
            game_id: str | int | float,
            *,
            requests_session: ChickenSession | None = None,
            backend: AnyBackend = "polars",
            _warn_season: bool = True,
        ) -> None: ...
