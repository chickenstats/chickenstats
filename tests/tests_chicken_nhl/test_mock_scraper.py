import os
import pytest
from unittest.mock import patch
import requests
import polars as pl

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment] # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl.scraper import Scraper

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "mock_data")


def mock_session_get(self, url, *args, **kwargs):
    """Custom mock for requests Session.get / ChickenSession.get."""
    response = requests.Response()
    response.url = url

    if "api-web.nhle.com/v1/gamecenter/2023020001/play-by-play" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "play_by_play.json"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/RO020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "rosters.html"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/TH020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "shifts_home.html"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/TV020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "shifts_away.html"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/PL020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "events.html"), "rb") as f:
            response._content = f.read()
        return response

    response.status_code = 404
    return response


@pytest.fixture(autouse=True)
def mock_requests():
    """Fixture to intercept all HTTP GET requests made via requests.Session."""
    with patch("requests.Session.get", mock_session_get):
        yield


class TestMockScraper:
    def test_mock_scraper_init(self):
        """Test Scraper initialization."""
        scraper = Scraper(game_ids=[2023020001])
        assert scraper.game_ids == [2023020001]

    def test_mock_scraper_play_by_play(self):
        """Test Scraper play_by_play retrieval."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        pbp = scraper.play_by_play

        # Verify result is a Polars DataFrame and has correct contents
        assert isinstance(pbp, pl.DataFrame)
        assert len(pbp) > 0
        assert "game_id" in pbp.columns
        assert pbp["game_id"][0] == 2023020001

    def test_mock_scraper_individual_and_team_stats(self):
        """Test Scraper stats preparation and extraction with mock data."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        scraper.prep_stats()
        stats = scraper.stats

        assert isinstance(stats, pl.DataFrame)
        assert len(stats) > 0
        assert "player" in stats.columns

        scraper.prep_team_stats()
        team_stats = scraper.team_stats
        assert isinstance(team_stats, pl.DataFrame)
        assert len(team_stats) > 0

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_mock_scraper_pandas_backend(self):
        """Test Scraper with pandas backend."""
        scraper = Scraper(game_ids=[2023020001], backend="pandas", disable_progress_bar=True)
        pbp = scraper.play_by_play
        assert isinstance(pbp, pd.DataFrame)
        assert not pbp.empty

    def test_mock_scraper_failed_game_handling(self):
        """Test Scraper handles non-existent or failing games gracefully."""
        # 9999999999 will fail with 404 in our mock
        scraper = Scraper(game_ids=[9999999999], disable_progress_bar=True)
        pbp = scraper.play_by_play

        assert len(pbp) == 0
        assert 9999999999 in scraper.failed_games
