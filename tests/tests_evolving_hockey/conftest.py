"""Shared offline fixtures for the evolving_hockey tests."""

from types import SimpleNamespace

import pytest
from eh_converter import (
    csv_round_trip,
    to_eh_gar_goalies,
    to_eh_gar_skaters,
    to_eh_pbp,
    to_eh_shifts,
    to_eh_xgar_skaters,
)

from chickenstats.chicken_nhl import Scraper
from chickenstats.evolving_hockey import prep_pbp

# Every game saved for the chicken_nhl tests
FIXTURE_GAME_ID = 2023020001
SECOND_NASHVILLE_GAME_ID = 2023020015
SHOOTOUT_GAME_ID = 2023020125
LONG_SHOOTOUT_GAME_ID = 2023020411
PLAYOFF_OVERTIME_GAME_ID = 2023030223
OLD_REGULAR_SEASON_GAME_ID = 2010020012
OLD_PLAYOFF_GAME_ID = 2017030111

SAVED_GAME_IDS = [
    FIXTURE_GAME_ID,
    SECOND_NASHVILLE_GAME_ID,
    SHOOTOUT_GAME_ID,
    LONG_SHOOTOUT_GAME_ID,
    PLAYOFF_OVERTIME_GAME_ID,
    OLD_REGULAR_SEASON_GAME_ID,
    OLD_PLAYOFF_GAME_ID,
]


@pytest.fixture(scope="session")
def chicken():
    """The chicken_nhl frames for the saved games, read from the saved responses."""
    scraper = Scraper([*SAVED_GAME_IDS], disable_progress_bar=True)

    return SimpleNamespace(
        play_by_play=scraper.play_by_play,
        play_by_play_ext=scraper.play_by_play_ext,
        rosters=scraper.rosters,
        shifts=scraper.shifts,
    )


@pytest.fixture(scope="session")
def raw_pbp_polars(chicken):
    """The saved games as an Evolving-Hockey play-by-play export."""
    return csv_round_trip(to_eh_pbp(chicken.play_by_play, chicken.rosters))


@pytest.fixture(scope="session")
def raw_shifts_polars(chicken):
    """The saved games as an Evolving-Hockey shifts export."""
    return csv_round_trip(to_eh_shifts(chicken.shifts, chicken.play_by_play))


@pytest.fixture(scope="session")
def pbp_polars(raw_pbp_polars, raw_shifts_polars):
    return prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, disable_progress_bar=True)


@pytest.fixture(scope="session")
def pbp_lazy(pbp_polars):
    return pbp_polars.lazy()


@pytest.fixture(scope="session")
def pbp_pandas(pbp_polars):
    return pbp_polars.to_pandas()


@pytest.fixture(scope="session")
def pbp_pyarrow(raw_pbp_polars, raw_shifts_polars):
    return prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, backend="pyarrow", disable_progress_bar=True)


@pytest.fixture(scope="session")
def raw_gar_skater_polars(chicken):
    return csv_round_trip(to_eh_gar_skaters(chicken.shifts))


@pytest.fixture(scope="session")
def raw_gar_goalie_polars(chicken):
    return csv_round_trip(to_eh_gar_goalies(chicken.shifts))


@pytest.fixture(scope="session")
def raw_xgar_polars(chicken):
    return csv_round_trip(to_eh_xgar_skaters(chicken.shifts))


@pytest.fixture(scope="session")
def raw_gar_skater_pandas(raw_gar_skater_polars):
    return raw_gar_skater_polars.to_pandas()


@pytest.fixture(scope="session")
def raw_gar_goalie_pandas(raw_gar_goalie_polars):
    return raw_gar_goalie_polars.to_pandas()


@pytest.fixture(scope="session")
def raw_xgar_pandas(raw_xgar_polars):
    return raw_xgar_polars.to_pandas()


@pytest.fixture(scope="session")
def raw_gar_skater_pyarrow(raw_gar_skater_polars):
    return raw_gar_skater_polars.to_arrow()


@pytest.fixture(scope="session")
def raw_gar_goalie_pyarrow(raw_gar_goalie_polars):
    return raw_gar_goalie_polars.to_arrow()


@pytest.fixture(scope="session")
def raw_xgar_pyarrow(raw_xgar_polars):
    return raw_xgar_polars.to_arrow()
