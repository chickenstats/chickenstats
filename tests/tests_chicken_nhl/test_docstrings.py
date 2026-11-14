"""Tests for chickenstats.chicken_nhl._docstrings."""

import pytest

from chickenstats.chicken_nhl import Scraper
from chickenstats.chicken_nhl import _docstrings as docs
from chickenstats.chicken_nhl import _validation_schema as schema

STATS_DOC_SCHEMA_PAIRS = {
    "ind_stats": (docs._IND_STATS_RETURN_FIELDS, schema.ind_stats_fields),
    "oi_stats": (docs._OI_STATS_RETURN_FIELDS, schema.oi_stats_fields),
    "stats": (docs._STATS_RETURN_FIELDS, schema.stats_fields),
    "lines": (docs._LINES_RETURN_FIELDS, schema.line_stats_fields),
    "team_stats": (docs._TEAM_STATS_RETURN_FIELDS, schema.team_stats_fields),
}


@pytest.mark.parametrize("frame", STATS_DOC_SCHEMA_PAIRS)
def test_stats_docs_list_exactly_the_schema_columns(frame):
    """A column added to or removed from a stats schema must be documented to match."""
    documented, fields = STATS_DOC_SCHEMA_PAIRS[frame]

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
