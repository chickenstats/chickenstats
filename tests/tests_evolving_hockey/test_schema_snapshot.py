"""Every evolving_hockey frame built from the saved games matches the schema snapshot.

See tests/tests_chicken_nhl/test_schema_snapshot.py; this is the same check for the frames
evolving_hockey returns.
"""

import pytest

from chickenstats.evolving_hockey import prep_gar, prep_ind, prep_lines, prep_oi, prep_stats, prep_team_stats, prep_xgar
from schema_snapshot import assert_matches_snapshot

# Each option set returns a different subset of the stats columns
OPTIONS = {
    "game_all_splits": {"level": "game", "teammates": True, "opposition": True, "score": True},
    "period": {"level": "period"},
    "season": {"level": "season"},
}
STATS = {"stats": prep_stats, "ind_stats": prep_ind, "oi_stats": prep_oi, "lines": prep_lines}


def test_pbp_matches_the_snapshot(pbp_polars):
    assert_matches_snapshot(pbp_polars, "evolving_hockey.pbp")


@pytest.mark.parametrize("frame", STATS)
@pytest.mark.parametrize("options", OPTIONS.values(), ids=OPTIONS.keys())
def test_stats_frames_match_the_snapshot(pbp_polars, frame, options):
    assert_matches_snapshot(STATS[frame](pbp_polars, **options), f"evolving_hockey.{frame}")


@pytest.mark.parametrize("options", OPTIONS.values(), ids=OPTIONS.keys())
def test_team_stats_match_the_snapshot(pbp_polars, options):
    # evolving_hockey's prep_team_stats splits by score only
    options = {key: value for key, value in options.items() if key in ("level", "score")}
    assert_matches_snapshot(prep_team_stats(pbp_polars, **options), "evolving_hockey.team_stats")


def test_gar_matches_the_snapshot(raw_gar_skater_polars, raw_gar_goalie_polars):
    assert_matches_snapshot(prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars), "evolving_hockey.gar")


def test_xgar_matches_the_snapshot(raw_xgar_polars):
    assert_matches_snapshot(prep_xgar(raw_xgar_polars), "evolving_hockey.xgar")
