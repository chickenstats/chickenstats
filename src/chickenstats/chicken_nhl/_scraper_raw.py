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
        """Changes — docstring lives in _docstrings._SCRAPER_CHANGES_DOC."""
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

    def _play_by_play_snapshot(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Return play_by_play and play_by_play_ext from the same scrape, as polars."""
        self._scrape("play_by_play")

        return (
            self._concat_stored(self._play_by_play, pbp_polars_schema),
            self._concat_stored(self._play_by_play_ext, pbp_ext_polars_schema),
        )

    @cached_property
    @shared_doc(_SCRAPER_PLAY_BY_PLAY_DOC)
    def play_by_play(self) -> DataFrameT:
        """play_by_play — docstring lives in _docstrings._SCRAPER_PLAY_BY_PLAY_DOC."""
        self._scrape("play_by_play")

        return self._finalize_dataframe(data=self._play_by_play, schema=pbp_polars_schema)

    @cached_property
    @shared_doc(_SCRAPER_PLAY_BY_PLAY_EXT_DOC)
    def play_by_play_ext(self) -> DataFrameT:
        """play_by_play_ext — docstring lives in _docstrings._SCRAPER_PLAY_BY_PLAY_EXT_DOC."""
        self._scrape("play_by_play")

        df = self._finalize_dataframe(data=self._play_by_play_ext, schema=pbp_ext_polars_schema)

        return df

    @cached_property
    def xg_fields(self) -> DataFrameT:
        """Polars DataFrame of xG input features for every fenwick event across all scraped games."""
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
