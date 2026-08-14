from __future__ import annotations

from functools import cached_property

import polars as pl

from chickenstats.chicken_nhl._docstrings import (
    _SCRAPER_API_EVENTS_DOC,
    _SCRAPER_API_ROSTERS_DOC,
    _SCRAPER_CHANGES_DOC,
    _SCRAPER_HTML_EVENTS_DOC,
    _SCRAPER_HTML_ROSTERS_DOC,
    _SCRAPER_PLAY_BY_PLAY_DOC,
    _SCRAPER_PLAY_BY_PLAY_EXT_DOC,
    _SCRAPER_ROSTERS_DOC,
    _SCRAPER_SHIFTS_DOC,
    shared_doc,
)
from chickenstats.chicken_nhl._scraper_core import _ScraperBase
from chickenstats.utilities.types import DataFrameT
from chickenstats.utilities.utilities import _to_backend
from chickenstats.chicken_nhl.validation_polars import (
    api_events_polars_schema,
    api_rosters_polars_schema,
    changes_polars_schema,
    html_events_polars_schema,
    html_rosters_polars_schema,
    pbp_polars_schema,
    pbp_ext_polars_schema,
    rosters_polars_schema,
    shifts_polars_schema,
    xg_polars_schema,
)


class _ScraperRawMixin(_ScraperBase):
    @cached_property
    @shared_doc(_SCRAPER_API_EVENTS_DOC)
    def api_events(self) -> DataFrameT:
        """api_events — docstring lives in _docstrings._SCRAPER_API_EVENTS_DOC."""
        self._scrape("api_events")

        df = self._finalize_dataframe(data=self._api_events, schema=api_events_polars_schema)

        return df

    @cached_property
    @shared_doc(_SCRAPER_API_ROSTERS_DOC)
    def api_rosters(self) -> DataFrameT:
        """api_rosters — docstring lives in _docstrings._SCRAPER_API_ROSTERS_DOC."""
        self._scrape("api_rosters")

        df = self._finalize_dataframe(data=self._api_rosters, schema=api_rosters_polars_schema)

        return df

    @cached_property
    @shared_doc(_SCRAPER_CHANGES_DOC)
    def changes(self) -> DataFrameT:
        """Changes — docstring lives in _docstrings._SCRAPER_CHANGES_DOC.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., CHANGE
            event_type (str):
                Type of change that occurred, e.g., AWAY CHANGE
            description (str | None):
                Description of the event, e.g.,
                PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
                / PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            change_on_count (int):
                Number of players on, e.g., 4
            change_off_count (int):
                Number of players off, e.g., 4
            change_on (str):
                Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_jersey (str):
                Combination of jerseys and numbers for the players on, e.g., NSH14, NSH19, NSH64, NSH95
            change_on_eh_id (str):
                Evolving Hockey IDs of the players on, e.g.,
                MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_on_positions (str):
                Positions of the players on, e.g., D, C, C, C
            change_off (str):
                Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_jersey (str):
                Combination of jerseys and numbers for the players off, e.g., NSH7, NSH9, NSH33, NSH92
            change_off_eh_id (str):
                Evolving Hockey IDs of the players off, e.g.,
                YANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_off_positions (str):
                Positions of the players off, e.g., D, L, L, C
            change_on_forwards_count (int):
                Number of forwards on, e.g.,
            change_off_forwards_count (int):
                Number of forwards off, e.g., 3
            change_on_forwards (str):
                Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE
            change_on_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards on, e.g., NSH19, NSH64, NSH95
            change_on_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards on, e.g.,
                CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE
            change_off_forwards (str):
                Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN
            change_off_forwards_jersey (str):
                Combination of jerseys and numbers for the forwards off, e.g., NSH9, NSH33, NSH92
            change_off_forwards_eh_id (str):
                Evolving Hockey IDs of the forwards off, e.g.,
                FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN
            change_on_defense_count (int):
                Number of defense on, e.g., 1
            change_off_defense_count (int):
                Number of defense off, e.g., 1
            change_on_defense (str):
                Names of defense on, e.g., MATTIAS EKHOLM
            change_on_defense_jersey (str):
                Combination of jerseys and numbers for the defense on, e.g., NSH14
            change_on_defense_eh_id (str):
                Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM
            change_off_defense (str):
                Names of defense off, e.g., YANNICK WEBER
            change_off_defense_jersey (str):
                Combination of jerseys and numbers for the defense off, e.g., NSH7
            change_off_defense_eh_id (str):
                Evolving Hockey IDs of the defense off, e.g., YANNICK.WEBER
            change_on_goalie_count (int):
                Number of goalies on, e.g., 0
            change_off_goalie_count (int):
                Number of goalies off, e.g., 0
            change_on_goalies (str):
                Names of goalies on, e.g., None
            change_on_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies on, e.g., None
            change_on_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies on, e.g., None
            change_off_goalies (str):
                Names of goalies off, e.g., None
            change_off_goalies_jersey (str):
                Combination of jerseys and numbers for the goalies off, e.g., None
            change_off_goalies_eh_id (str):
                Evolving Hockey IDs of the goalies off, e.g., None
            is_home (int):
                Dummy indicator whether change team is home, e.g., 0
            is_away (int):
                Dummy indicator whether change team is away, e.g., 1
            team_venue (str):
                Whether team is home or away, e.g., AWAY

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> scraper = Scraper(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> scraper.changes
        """
        self._scrape("changes")

        df = self._finalize_dataframe(data=self._changes, schema=changes_polars_schema)

        return df

    @cached_property
    @shared_doc(_SCRAPER_HTML_EVENTS_DOC)
    def html_events(self) -> DataFrameT:
        """html_events — docstring lives in _docstrings._SCRAPER_HTML_EVENTS_DOC."""
        self._scrape("html_events")

        df = self._finalize_dataframe(data=self._html_events, schema=html_events_polars_schema)

        return df

    @cached_property
    @shared_doc(_SCRAPER_HTML_ROSTERS_DOC)
    def html_rosters(self) -> DataFrameT:
        """html_rosters — docstring lives in _docstrings._SCRAPER_HTML_ROSTERS_DOC."""
        self._scrape("html_rosters")

        df = self._finalize_dataframe(data=self._html_rosters, schema=html_rosters_polars_schema)

        return df

    @cached_property
    @shared_doc(_SCRAPER_PLAY_BY_PLAY_DOC)
    def play_by_play(self) -> DataFrameT:
        """play_by_play — docstring lives in _docstrings._SCRAPER_PLAY_BY_PLAY_DOC."""
        if set(self.game_ids) != self._scraped_play_by_play:
            self._scrape("play_by_play")

        raw = pl.concat(self._play_by_play) if self._play_by_play else pl.DataFrame(schema=pbp_polars_schema)

        return _to_backend(raw, self._backend)

    @cached_property
    @shared_doc(_SCRAPER_PLAY_BY_PLAY_EXT_DOC)
    def play_by_play_ext(self) -> DataFrameT:
        """play_by_play_ext — docstring lives in _docstrings._SCRAPER_PLAY_BY_PLAY_EXT_DOC."""
        if set(self.game_ids) != self._scraped_play_by_play:
            self._scrape("play_by_play")

        df = self._finalize_dataframe(data=self._play_by_play_ext, schema=pbp_ext_polars_schema)

        return df

    @cached_property
    def xg_fields(self) -> DataFrameT:
        """Polars DataFrame of xG input features for every fenwick event across all scraped games."""
        if set(self.game_ids) != self._scraped_play_by_play:
            self._scrape("play_by_play")

        return self._finalize_dataframe(data=self._xg_fields, schema=xg_polars_schema)

    @cached_property
    @shared_doc(_SCRAPER_ROSTERS_DOC)
    def rosters(self) -> DataFrameT:
        """Rosters — docstring lives in _docstrings._SCRAPER_ROSTERS_DOC."""
        self._scrape("rosters")

        df = self._finalize_dataframe(data=self._rosters, schema=rosters_polars_schema)

        return df

    @cached_property
    @shared_doc(_SCRAPER_SHIFTS_DOC)
    def shifts(self) -> DataFrameT:
        """Shifts — docstring lives in _docstrings._SCRAPER_SHIFTS_DOC."""
        self._scrape("shifts")

        df = self._finalize_dataframe(data=self._shifts, schema=shifts_polars_schema)

        return df
