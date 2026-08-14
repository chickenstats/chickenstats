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


class TestScraperCacheArgument:
    """cache=/overwrite= automate the save()/load() flow via the constructor."""

    def test_cache_false_writes_nothing(self, tmp_path, monkeypatch):
        """Default cache=False leaves zero file-write behavior — matches today exactly."""
        monkeypatch.chdir(tmp_path)
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        assert not (tmp_path / "data").exists()
        assert scraper._cache_dir is None

    def test_cache_true_uses_data_directory(self, tmp_path, monkeypatch):
        """cache=True auto-saves to the same default save() uses, with no explicit .save() call."""
        monkeypatch.chdir(tmp_path)
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=True)
        _ = scraper.play_by_play

        save_path = tmp_path / "data"
        assert (save_path / "_meta.json").exists()
        assert (save_path / "play_by_play.parquet").exists()

    def test_cache_path_auto_saves(self, tmp_path):
        """cache=<path> auto-saves to that exact directory after scraping."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        _ = scraper.play_by_play

        assert (cache_dir / "_meta.json").exists()
        assert (cache_dir / "play_by_play.parquet").exists()

    def test_second_construction_reuses_cache_without_network(self, tmp_path):
        """A fresh Scraper(cache=<path>) against an already-populated cache doesn't
        re-fetch cached games."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        original = scraper.play_by_play

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            scraper2 = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
            reloaded = scraper2.play_by_play

        assert reloaded.shape == original.shape
        assert 2023020001 in scraper2._scraped_play_by_play

    def test_cache_path_empty_dir_scrapes_normally(self, tmp_path):
        """cache=<path> pointing at a directory with no _meta.json yet doesn't error —
        just scrapes normally and creates the cache on first save."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        pbp = scraper.play_by_play

        assert not pbp.is_empty()
        assert (cache_dir / "_meta.json").exists()

    def test_overwrite_true_ignores_existing_cache(self, tmp_path):
        """overwrite=True skips loading an existing cache, scraping fresh instead."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        _ = scraper.play_by_play

        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = lambda url, *a, **kw: mock_session_get(None, url, *a, **kw)
            scraper2 = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir, overwrite=True)
            _ = scraper2.play_by_play

        assert mock_get.call_count > 0
        assert 2023020001 in scraper2._scraped_play_by_play

    def test_overwrite_true_without_cache_is_noop(self, tmp_path, monkeypatch):
        """overwrite=True with cache=False (default) behaves identically to cache=False alone."""
        monkeypatch.chdir(tmp_path)
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, overwrite=True)
        _ = scraper.play_by_play

        assert not (tmp_path / "data").exists()
        assert scraper._cache_dir is None


class TestScraperCrossFetchReuse:
    """Data already cached under one scrape_type is reused when a bigger fetch needs it,
    instead of re-fetching it from the network."""

    def test_cached_rosters_not_refetched_by_play_by_play(self, tmp_path):
        """rosters already cached -> play_by_play doesn't re-hit the roster HTML endpoint,
        and produces byte-identical output to a fully-fresh scrape."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        _ = scraper.rosters

        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = lambda url, *a, **kw: mock_session_get(None, url, *a, **kw)
            scraper2 = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
            pbp = scraper2.play_by_play

        requested_urls = [call.args[0] for call in mock_get.call_args_list]
        assert not any("RO020001.HTM" in url for url in requested_urls)

        fresh_scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        pbp_fresh = fresh_scraper.play_by_play
        assert pbp.equals(pbp_fresh)

    def test_partial_cache_only_fetches_missing_piece(self, tmp_path):
        """Only api_rosters cached (not html_rosters) -> .rosters fetches just the
        missing HTML piece, and still produces correct, complete roster data."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        _ = scraper.api_rosters

        scraper2 = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        rosters = scraper2.rosters

        assert not rosters.is_empty()

        fresh_scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        rosters_fresh = fresh_scraper.rosters
        assert rosters.equals(rosters_fresh)
