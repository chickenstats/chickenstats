"""Tests for chickenstats.chicken_nhl._docstrings."""

import pytest

from chickenstats import evolving_hockey
from chickenstats.chicken_nhl import Scraper, Season
from chickenstats.chicken_nhl import _docstrings as docs
from chickenstats.chicken_nhl import _validation_schema as schema
from chickenstats.chicken_nhl import player
from chickenstats.chicken_nhl import validation_polars as polars_schema
from chickenstats.evolving_hockey import _docstrings as eh_docs
from chickenstats.evolving_hockey import _validation_schema as eh_schema

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

PLAYER_DOC_SCHEMA_PAIRS = {
    "player_game_logs": (docs._PLAYER_GAME_LOGS_FIELDS, player._GAME_LOG_SCHEMA),
    "player_season_stats": (docs._PLAYER_SEASON_STATS_FIELDS, player._SEASON_STATS_SCHEMA),
    "player_career_totals": (docs._PLAYER_CAREER_TOTALS_FIELDS, player._CAREER_TOTALS_SCHEMA),
}

EH_DOC_SCHEMA_PAIRS = {
    "eh_pbp": (eh_docs._PBP_FIELDS, eh_schema.pbp_fields),
    "eh_gar": (eh_docs._GAR_FIELDS, eh_schema.gar_fields),
    "eh_xgar": (eh_docs._XGAR_FIELDS, eh_schema.xgar_fields),
}

ALL_DOC_SCHEMA_PAIRS = STATS_DOC_SCHEMA_PAIRS | RAW_DOC_SCHEMA_PAIRS | PLAYER_DOC_SCHEMA_PAIRS | EH_DOC_SCHEMA_PAIRS

# The public docstring that renders each registry, for frames whose docstring is a single function's
PUBLIC_DOCSTRINGS = {
    "schedule": (Season.schedule, docs._SCHEDULE_FIELDS),
    "standings": (Season.standings, docs._STANDINGS_FIELDS),
    "eh_pbp": (evolving_hockey.prep_pbp, eh_docs._PBP_FIELDS),
    "eh_gar": (evolving_hockey.prep_gar, eh_docs._GAR_FIELDS),
    "eh_xgar": (evolving_hockey.prep_xgar, eh_docs._XGAR_FIELDS),
}


@pytest.mark.parametrize("frame", list(ALL_DOC_SCHEMA_PAIRS))
def test_docs_list_exactly_the_schema_columns(frame):
    """A column added to or removed from a schema must be documented to match."""
    documented, fields = ALL_DOC_SCHEMA_PAIRS[frame]

    assert set(documented) - set(fields) == set(), "documented but not in the schema"
    assert set(fields) - set(documented) == set(), "in the schema but not documented"


@pytest.mark.parametrize("frame", list(PUBLIC_DOCSTRINGS))
def test_public_docstring_describes_every_column(frame):
    """The rendered docstring lists every column of its registry, each with a description."""
    obj, fields = PUBLIC_DOCSTRINGS[frame]
    doc = obj.__doc__
    assert doc is not None, frame

    for name, (type_str, description) in fields.items():
        assert description, name
        assert f"    {name} ({type_str}):" in doc, name


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
