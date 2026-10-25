"""Shared offline fixtures for the chicken_nhl tests."""

import gzip
import json
import os
from types import SimpleNamespace

import pytest

from chickenstats.chicken_nhl import Scraper

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "mock_data")
FIXTURE_GAME_ID = 2023020001


SHOOTOUT_GAME_ID = 2023020125
PLAYOFF_OVERTIME_GAME_ID = 2023030223
LONG_SHOOTOUT_GAME_ID = 2023020411
SECOND_NASHVILLE_GAME_ID = 2023020015
OLD_REGULAR_SEASON_GAME_ID = 2010020012
OLD_PLAYOFF_GAME_ID = 2017030111


SAVED_GAME_IDS = [
    FIXTURE_GAME_ID,
    SHOOTOUT_GAME_ID,
    LONG_SHOOTOUT_GAME_ID,
    PLAYOFF_OVERTIME_GAME_ID,
    SECOND_NASHVILLE_GAME_ID,
    OLD_REGULAR_SEASON_GAME_ID,
    OLD_PLAYOFF_GAME_ID,
]


def scrape_saved_games(game_ids: list[int]) -> SimpleNamespace:
    """Scrape games from the saved responses in one Scraper and return every frame."""
    scraper = Scraper([*game_ids], disable_progress_bar=True)

    return SimpleNamespace(
        game_ids=game_ids,
        play_by_play=scraper.play_by_play,
        play_by_play_ext=scraper.play_by_play_ext,
        xg_fields=scraper.xg_fields,
        rosters=scraper.rosters,
        html_rosters=scraper.html_rosters,
        api_rosters=scraper.api_rosters,
        shifts=scraper.shifts,
        changes=scraper.changes,
        html_events=scraper.html_events,
        api_events=scraper.api_events,
        failed_games=scraper.failed_games,
    )


def scrape_saved_game(game_id: int) -> SimpleNamespace:
    """Scrape one game from the saved responses and return every frame."""
    game = scrape_saved_games([game_id])
    game.game_id = game_id

    return game


@pytest.fixture(scope="session")
def saved_api_response():
    """A function that returns the raw NHL API play-by-play response saved for a game."""

    def load(game_id: int) -> dict:
        path = os.path.join(MOCK_DATA_DIR, "saved", f"gamecenter_{game_id}_play-by-play.gz")
        with gzip.open(path, "rb") as f:
            return json.load(f)

    return load


@pytest.fixture(scope="session")
def fixture_game():
    """Every scraped frame for game 2023020001 (NSH at TBL, TBL won 5-3), built once from the saved responses."""
    return scrape_saved_game(FIXTURE_GAME_ID)


@pytest.fixture(scope="session")
def shootout_game():
    """Every scraped frame for game 2023020125 (VGK at LAK, VGK won 4-3 in a shootout)."""
    return scrape_saved_game(SHOOTOUT_GAME_ID)


@pytest.fixture(scope="session")
def long_shootout_game():
    """Every scraped frame for game 2023020411 (MTL at BUF, MTL won 3-2 in a shootout with five shootout goals)."""
    return scrape_saved_game(LONG_SHOOTOUT_GAME_ID)


@pytest.fixture(scope="session")
def playoff_overtime_game():
    """Every scraped frame for game 2023030223 (NYR at CAR, NYR won 3-2 in overtime)."""
    return scrape_saved_game(PLAYOFF_OVERTIME_GAME_ID)


@pytest.fixture(scope="session")
def second_nashville_game():
    """Every scraped frame for game 2023020015 (SEA at NSH, NSH won 3-0), Nashville's game after the fixture game."""
    return scrape_saved_game(SECOND_NASHVILLE_GAME_ID)


@pytest.fixture(scope="session")
def old_regular_season_game():
    """Every scraped frame for game 2010020012 (PHX at BOS, PHX won 5-2), from the oldest reports the tests read."""
    return scrape_saved_game(OLD_REGULAR_SEASON_GAME_ID)


@pytest.fixture(scope="session")
def old_playoff_game():
    """Every scraped frame for game 2017030111 (NJD at TBL, TBL won 5-2), a playoff game from before 2019."""
    return scrape_saved_game(OLD_PLAYOFF_GAME_ID)


@pytest.fixture(scope="session")
def all_saved_games():
    """Every scraped frame for the seven saved games in one Scraper, so season totals span several games."""
    return scrape_saved_games(SAVED_GAME_IDS)


@pytest.fixture(scope="session")
def saved_boxscore():
    """A function that returns the NHL API boxscore saved for a game."""

    def load(game_id: int) -> dict:
        path = os.path.join(MOCK_DATA_DIR, "saved", f"gamecenter_{game_id}_boxscore.gz")
        with gzip.open(path, "rb") as f:
            return json.loads(f.read())

    return load


@pytest.fixture(scope="session")
def fixture_api_response():
    """The raw NHL API play-by-play response for game 2023020001."""
    with open(os.path.join(MOCK_DATA_DIR, "play_by_play.json")) as f:
        return json.load(f)
