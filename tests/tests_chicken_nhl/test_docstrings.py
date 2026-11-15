"""Tests for chickenstats.chicken_nhl._docstrings."""

import pytest

from chickenstats.chicken_nhl import Scraper
from chickenstats.chicken_nhl import _docstrings as docs
from chickenstats.chicken_nhl import _validation_schema as schema
from chickenstats.chicken_nhl import validation_polars as polars_schema

STATS_DOC_SCHEMA_PAIRS = {
    "ind_stats": (docs._IND_STATS_RETURN_FIELDS, schema.ind_stats_fields),
    "oi_stats": (docs._OI_STATS_RETURN_FIELDS, schema.oi_stats_fields),
    "stats": (docs._STATS_RETURN_FIELDS, schema.stats_fields),
    "lines": (docs._LINES_RETURN_FIELDS, schema.line_stats_fields),
    "team_stats": (docs._TEAM_STATS_RETURN_FIELDS, schema.team_stats_fields),
}

RAW_DOC_SCHEMA_PAIRS = {
    "api_events": (docs._API_EVENTS_FIELDS, polars_schema.api_events_polars_schema),
    "api_rosters": (docs._API_ROSTERS_FIELDS, polars_schema.api_rosters_polars_schema),
    "html_events": (docs._HTML_EVENTS_FIELDS, polars_schema.html_events_polars_schema),
    "html_rosters": (docs._HTML_ROSTERS_FIELDS, polars_schema.html_rosters_polars_schema),
    "rosters": (docs._ROSTERS_FIELDS, polars_schema.rosters_polars_schema),
    "shifts": (docs._SHIFTS_FIELDS, polars_schema.shifts_polars_schema),
    "changes": (docs._CHANGES_FIELDS, polars_schema.changes_polars_schema),
    "play_by_play": (docs._PBP_FIELDS, polars_schema.pbp_polars_schema),
    "play_by_play_ext": (docs._PBP_EXT_FIELDS, polars_schema.pbp_ext_polars_schema),
    "xg_fields": (docs._XG_FIELDS, polars_schema.xg_polars_schema),
    "schedule": (docs._SCHEDULE_FIELDS, polars_schema.schedule_polars_schema),
    "standings": (docs._STANDINGS_FIELDS, polars_schema.standings_polars_schema),
    "stints": (
        docs._STINTS_CONTEXT_FIELDS
        | docs._STINTS_PERSONNEL_FIELDS
        | docs._STINTS_STAT_FIELDS
        | docs._STINTS_MODEL_FIELDS,
        polars_schema.stints_polars_schema,
    ),
}


@pytest.mark.parametrize("frame", [*STATS_DOC_SCHEMA_PAIRS, *RAW_DOC_SCHEMA_PAIRS])
def test_docs_list_exactly_the_schema_columns(frame):
    """A column added to or removed from a schema must be documented to match."""
    documented, fields = (STATS_DOC_SCHEMA_PAIRS | RAW_DOC_SCHEMA_PAIRS)[frame]

    assert set(documented) - set(fields) == set(), "documented but not in the schema"
    assert set(fields) - set(documented) == set(), "in the schema but not documented"


def test_stats_output_columns_are_documented():
    """Every column the fixture game's stats frames return has a description."""
    scraper = Scraper(2023020001, disable_progress_bar=True)

    frames = {
        "stats": scraper.prep_stats(teammates=True, opposition=True, score=True).stats,
        "lines": scraper.prep_lines(teammates=True, opposition=True, score=True).lines,
        "team_stats": scraper.prep_team_stats(opposition=True, score=True).team_stats,
    }

    for frame, df in frames.items():
        documented = STATS_DOC_SCHEMA_PAIRS[frame][0]
        assert set(df.columns) - set(documented) == set(), frame


def test_raw_output_columns_are_documented():
    """Every column the fixture game's scraped frames return has a description."""
    scraper = Scraper(2023020001, disable_progress_bar=True)

    # schedule and standings come from Season and stints from prep_stints, not from a game scrape
    for frame in [name for name in RAW_DOC_SCHEMA_PAIRS if name not in ("schedule", "standings", "stints")]:
        documented = RAW_DOC_SCHEMA_PAIRS[frame][0]
        assert set(getattr(scraper, frame).columns) - set(documented) == set(), frame
