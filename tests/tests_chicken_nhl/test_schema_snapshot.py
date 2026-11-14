"""Every frame the fixture game produces matches the schema snapshot: column order, dtypes and nulls.

The snapshot, tests/data/schema_snapshot.json, is written by scripts/schema_catalog.py from the
package's schemas, and test_schema_catalog.py keeps the two in step. This file checks the frames
themselves, so a column added, moved or retyped anywhere between the schema and the output fails.
"""

import datetime as dt

import pytest

from chickenstats.chicken_nhl import Scraper, Season, player_bios, player_profiles, search_players
from schema_snapshot import assert_matches_snapshot

SCRAPED = ["play_by_play", "play_by_play_ext", "xg_fields", "api_events", "api_rosters", "html_events"]
SCRAPED += ["html_rosters", "rosters", "shifts", "changes"]

# Each option set returns a different subset of the stats columns
OPTIONS = {
    "game_all_splits": {"level": "game", "teammates": True, "opposition": True, "score": True},
    "period": {"level": "period"},
    "season": {"level": "season", "strength_state": False},
}


@pytest.fixture(scope="module")
def scraper():
    return Scraper(2023020001, disable_progress_bar=True)


@pytest.mark.parametrize("frame", SCRAPED)
def test_scraped_frame_matches_the_snapshot(scraper, frame):
    assert_matches_snapshot(getattr(scraper, frame), f"chicken_nhl.{frame}", every_column=True)


@pytest.mark.parametrize("options", OPTIONS.values(), ids=OPTIONS.keys())
def test_stats_frames_match_the_snapshot(scraper, options):
    scraper.prep_stats(**options)
    assert_matches_snapshot(scraper.stats, "chicken_nhl.stats")
    assert_matches_snapshot(scraper.ind_stats, "chicken_nhl.ind_stats")
    assert_matches_snapshot(scraper.oi_stats, "chicken_nhl.oi_stats")


@pytest.mark.parametrize("options", OPTIONS.values(), ids=OPTIONS.keys())
def test_lines_match_the_snapshot(scraper, options):
    assert_matches_snapshot(scraper.prep_lines(**options).lines, "chicken_nhl.lines")


@pytest.mark.parametrize("options", OPTIONS.values(), ids=OPTIONS.keys())
def test_team_stats_match_the_snapshot(scraper, options):
    options = {key: value for key, value in options.items() if key != "teammates"}
    assert_matches_snapshot(scraper.prep_team_stats(**options).team_stats, "chicken_nhl.team_stats")


def test_stints_match_the_snapshot(scraper):
    assert_matches_snapshot(scraper.prep_stints().stints, "chicken_nhl.stints")


def test_schedule_matches_the_snapshot():
    schedule = Season(2023).schedule("NSH", disable_progress_bar=True)
    assert_matches_snapshot(schedule, "chicken_nhl.schedule", every_column=True)


def test_standings_match_the_snapshot():
    assert_matches_snapshot(Season(2023).standings, "chicken_nhl.standings", every_column=True)


def test_search_players_matches_the_snapshot():
    assert_matches_snapshot(search_players("forsberg"), "chicken_nhl.search_players", every_column=True)


def test_player_bios_match_the_snapshot():
    assert_matches_snapshot(player_bios([8476887]), "chicken_nhl.player_bios", every_column=True)


def test_player_profiles_match_the_snapshot():
    profiles = player_profiles(player_bios([8476887]), dt.date(2023, 10, 10))
    assert_matches_snapshot(profiles, "chicken_nhl.player_profiles", every_column=True)
