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
from chickenstats.chicken_nhl._scraper_core import _SCRAPE_REGISTRY, ScrapeType, _ScraperBase
from chickenstats.utilities.types import DataFrameT
from chickenstats.chicken_nhl.validation_polars import pbp_polars_schema, pbp_ext_polars_schema


class _ScraperRawMixin(_ScraperBase):
    def _raw_frame(self, scrape_type: ScrapeType, key: str | None = None) -> DataFrameT:
        """Scrape one data type and return its frames, or key's when the scrape also builds key."""
        self._scrape(scrape_type)

        spec = _SCRAPE_REGISTRY[key or scrape_type]
        return self._finalize_dataframe(data=getattr(self, spec.list_attr), schema=spec.schema)

    @cached_property
    @shared_doc(_SCRAPER_API_EVENTS_DOC)
    def api_events(self) -> DataFrameT:
        """api_events — docstring lives in _docstrings._SCRAPER_API_EVENTS_DOC."""
        return self._raw_frame("api_events")

    @cached_property
    @shared_doc(_SCRAPER_API_ROSTERS_DOC)
    def api_rosters(self) -> DataFrameT:
        """api_rosters — docstring lives in _docstrings._SCRAPER_API_ROSTERS_DOC."""
        return self._raw_frame("api_rosters")

    @cached_property
    @shared_doc(_SCRAPER_CHANGES_DOC)
    def changes(self) -> DataFrameT:
        """Changes — docstring lives in _docstrings._SCRAPER_CHANGES_DOC."""
        return self._raw_frame("changes")

    @cached_property
    @shared_doc(_SCRAPER_HTML_EVENTS_DOC)
    def html_events(self) -> DataFrameT:
        """html_events — docstring lives in _docstrings._SCRAPER_HTML_EVENTS_DOC."""
        return self._raw_frame("html_events")

    @cached_property
    @shared_doc(_SCRAPER_HTML_ROSTERS_DOC)
    def html_rosters(self) -> DataFrameT:
        """html_rosters — docstring lives in _docstrings._SCRAPER_HTML_ROSTERS_DOC."""
        return self._raw_frame("html_rosters")

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
        return self._raw_frame("play_by_play")

    @cached_property
    @shared_doc(_SCRAPER_PLAY_BY_PLAY_EXT_DOC)
    def play_by_play_ext(self) -> DataFrameT:
        """play_by_play_ext — docstring lives in _docstrings._SCRAPER_PLAY_BY_PLAY_EXT_DOC."""
        return self._raw_frame("play_by_play", "play_by_play_ext")

    @cached_property
    def xg_fields(self) -> DataFrameT:
        """Polars DataFrame of xG input features for every fenwick event across all scraped games."""
        return self._raw_frame("play_by_play", "xg_fields")

    @cached_property
    @shared_doc(_SCRAPER_ROSTERS_DOC)
    def rosters(self) -> DataFrameT:
        """Rosters — docstring lives in _docstrings._SCRAPER_ROSTERS_DOC."""
        return self._raw_frame("rosters")

    @cached_property
    @shared_doc(_SCRAPER_SHIFTS_DOC)
    def shifts(self) -> DataFrameT:
        """Shifts — docstring lives in _docstrings._SCRAPER_SHIFTS_DOC."""
        return self._raw_frame("shifts")
