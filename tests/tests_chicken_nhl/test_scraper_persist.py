import os
from unittest.mock import patch

import polars as pl
import pytest
import requests

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


class TestScraperPersist:
    def test_save_creates_files(self, tmp_path):
        """save() writes a parquet per populated data type plus _meta.json."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        save_path = scraper.save(tmp_path / "cache")

        assert (save_path / "_meta.json").exists()
        assert (save_path / "play_by_play.parquet").exists()

    def test_load_round_trips_play_by_play(self, tmp_path):
        """load() reproduces the same play_by_play data without re-scraping."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        original = scraper.play_by_play
        save_path = scraper.save(tmp_path / "cache")

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            loaded = Scraper.load(save_path, disable_progress_bar=True)
            reloaded = loaded.play_by_play

        assert isinstance(reloaded, pl.DataFrame)
        assert reloaded.shape == original.shape
        assert 2023020001 in loaded._scraped_play_by_play

    def test_load_extends_with_new_game_ids(self, tmp_path):
        """load(..., game_ids=[...]) merges new IDs in without touching cached ones."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play
        save_path = scraper.save(tmp_path / "cache")

        loaded = Scraper.load(save_path, game_ids=[2023020002], disable_progress_bar=True)

        assert loaded.game_ids == [2023020001, 2023020002]
        assert 2023020001 in loaded._scraped_play_by_play
        assert 2023020002 not in loaded._scraped_play_by_play

    def test_load_preserves_failed_games(self, tmp_path):
        """Failed games are preserved across a save/load round trip."""
        scraper = Scraper(game_ids=[2023020001, 9999999999], disable_progress_bar=True)
        _ = scraper.play_by_play
        assert 9999999999 in scraper.failed_games

        save_path = scraper.save(tmp_path / "cache")
        loaded = Scraper.load(save_path, disable_progress_bar=True)

        assert 9999999999 in loaded.failed_games

    def test_save_default_path_uses_data_directory(self, tmp_path, monkeypatch):
        """save() with no path defaults to data_directory() under the cwd."""
        monkeypatch.chdir(tmp_path)
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        save_path = scraper.save()

        assert save_path == tmp_path / "data"
        assert (save_path / "_meta.json").exists()
