from __future__ import annotations

import polars as pl

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
)
from chickenstats.utilities.utilities import _to_polars, _to_backend, _detect_backend

# Re-export for consumers that import from _scraper_utils
_ensure_polars = _to_polars

__all__ = ["_SCRAPE_SCHEMAS", "_ensure_polars", "_to_backend", "_detect_backend"]

# Map result keys to their polars schemas for incremental DataFrame conversion
_SCRAPE_SCHEMAS: dict[str, dict] = {
    "api_events": api_events_polars_schema,
    "api_rosters": api_rosters_polars_schema,
    "changes": changes_polars_schema,
    "html_events": html_events_polars_schema,
    "html_rosters": html_rosters_polars_schema,
    "rosters": rosters_polars_schema,
    "shifts": shifts_polars_schema,
    "play_by_play": pbp_polars_schema,
    "play_by_play_ext": pbp_ext_polars_schema,
}
