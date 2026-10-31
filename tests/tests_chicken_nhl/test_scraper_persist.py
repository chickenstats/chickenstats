import json
import os
from unittest.mock import patch

import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl.scraper import Scraper


class TestScraperPersist:
    def test_save_creates_files(self, tmp_path):
        """save() writes a parquet per game in a folder per data type, plus _meta.json."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        save_path = scraper.save(tmp_path / "cache")

        assert (save_path / "_meta.json").exists()
        assert (save_path / "play_by_play" / "2023020001.parquet").exists()

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
        assert 2023020001 in loaded._play_by_play

    def test_load_round_trips_every_frame(self, tmp_path):
        """Every frame save() writes comes back from load() unchanged, with no network access."""
        names = [
            "api_events",
            "api_rosters",
            "changes",
            "html_events",
            "html_rosters",
            "rosters",
            "shifts",
            "play_by_play",
            "play_by_play_ext",
            "xg_fields",
        ]
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        originals = {name: getattr(scraper, name) for name in names}
        save_path = scraper.save(tmp_path / "cache")

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            loaded = Scraper.load(save_path, disable_progress_bar=True)
            reloaded = {name: getattr(loaded, name) for name in names}

        for name in names:
            assert reloaded[name].equals(originals[name]), name
        assert loaded.failed_games == scraper.failed_games

    def test_load_extends_with_new_game_ids(self, tmp_path):
        """load(..., game_ids=[...]) merges new IDs in without touching cached ones."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play
        save_path = scraper.save(tmp_path / "cache")

        loaded = Scraper.load(save_path, game_ids=[2023020002], disable_progress_bar=True)

        assert loaded.game_ids == [2023020001, 2023020002]
        assert 2023020001 in loaded._play_by_play
        assert 2023020002 not in loaded._play_by_play

    def test_load_preserves_failed_games(self, tmp_path):
        """Failed games are preserved across a save/load round trip."""
        scraper = Scraper(game_ids=[2023020001, 9999999999], disable_progress_bar=True)
        with pytest.warns(UserWarning, match="Failed to scrape"):
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
        assert (save_path / "play_by_play" / "2023020001.parquet").exists()

    def test_cache_path_auto_saves(self, tmp_path):
        """cache=<path> auto-saves to that exact directory after scraping."""
        cache_dir = tmp_path / "cache"
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
        _ = scraper.play_by_play

        assert (cache_dir / "_meta.json").exists()
        assert (cache_dir / "play_by_play" / "2023020001.parquet").exists()

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
        assert 2023020001 in scraper2._play_by_play

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

        served_get = requests.Session.get
        with patch.object(requests.Session, "get", autospec=True, side_effect=served_get) as mock_get:
            scraper2 = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir, overwrite=True)
            _ = scraper2.play_by_play

        assert mock_get.call_count > 0
        assert 2023020001 in scraper2._play_by_play

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

        served_get = requests.Session.get
        with patch.object(requests.Session, "get", autospec=True, side_effect=served_get) as mock_get:
            scraper2 = Scraper(game_ids=[2023020001], disable_progress_bar=True, cache=cache_dir)
            pbp = scraper2.play_by_play

        requested_urls = [str(call.args[1]) for call in mock_get.call_args_list]
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


class TestCacheFormat:
    """Each game is written as its scrape ends, files are swapped in whole, and other formats are refused."""

    def test_an_interrupted_run_resumes_without_duplicate_rows(self, tmp_path):
        """A run stopped after its first game keeps that game, and the next run fetches only the rest (N53)."""
        from chickenstats.chicken_nhl import _scraper_core

        cache_dir = tmp_path / "cache"
        scrape_one = _scraper_core._ScraperCore._scrape_single_game

        def interrupted(self, game_id, scrape_type):
            if game_id == 2023020015:
                raise KeyboardInterrupt
            return scrape_one(self, game_id, scrape_type)

        with patch.object(_scraper_core._ScraperCore, "_scrape_single_game", interrupted):
            with pytest.raises(KeyboardInterrupt):
                _ = Scraper([2023020001, 2023020015], disable_progress_bar=True, cache=cache_dir).play_by_play

        served_get = requests.Session.get
        with patch.object(requests.Session, "get", autospec=True, side_effect=served_get) as mock_get:
            resumed = Scraper([2023020001, 2023020015], disable_progress_bar=True, cache=cache_dir)
            play_by_play = resumed.play_by_play

        requested = [str(call.args[1]) for call in mock_get.call_args_list]
        assert requested and not any("2023020001" in url or "020001.HTM" in url for url in requested)
        assert play_by_play.group_by("game_id").len().sort("game_id")["len"].to_list() == [781, 792]
        assert play_by_play.select("game_id", "event_idx").is_duplicated().sum() == 0

    def test_overwrite_removes_only_the_cache_files(self, tmp_path):
        """overwrite=True removes every file chickenstats wrote, so none is stale, and nothing else (R38)."""
        cache_dir = tmp_path / "cache"
        _ = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir).play_by_play
        (cache_dir / "notes.txt").write_text("not ours")

        scraper = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir, overwrite=True)
        _ = scraper.html_events

        assert (cache_dir / "notes.txt").read_text() == "not ours"
        # html_events stores the rosters it is built from, and nothing from the play-by-play scrape is left
        assert sorted(path.name for path in cache_dir.iterdir()) == [
            ".meta.lock",
            "_meta.json",
            "api_rosters",
            "html_events",
            "html_rosters",
            "notes.txt",
            "rosters",
        ]

    def test_overwrite_keeps_a_users_own_parquet_file(self, tmp_path):
        """A play_by_play.parquet the cache did not write survives overwrite=True, with or without a cache (in-01)."""
        empty, cached = tmp_path / "empty", tmp_path / "cached"
        _ = Scraper([2023020001], disable_progress_bar=True, cache=cached).api_events
        for folder in (empty, cached):
            folder.mkdir(exist_ok=True)
            pl.DataFrame({"mine": [1]}).write_parquet(folder / "play_by_play.parquet")

            _ = Scraper([2023020001], disable_progress_bar=True, cache=folder, overwrite=True).api_events

            assert pl.read_parquet(folder / "play_by_play.parquet").columns == ["mine"]

    def test_an_added_game_is_read_from_the_cache(self, tmp_path):
        """add_games() reads the new games from the cache and keeps the frames already held (bA-07)."""
        cache_dir = tmp_path / "cache"
        _ = Scraper([2023020015], disable_progress_bar=True, cache=cache_dir).play_by_play
        scraper = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)
        held = scraper.play_by_play
        frame = scraper._play_by_play[2023020001]

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            scraper.add_games([2023020015])
            play_by_play = scraper.play_by_play

        assert scraper._play_by_play[2023020001] is frame
        assert play_by_play.height == held.height + scraper._play_by_play[2023020015].height

    def test_two_scrapers_on_one_directory_keep_both_games(self, tmp_path):
        """Each write re-reads _meta.json, so a Scraper writing again keeps the game another wrote meanwhile (bA-06)."""
        cache_dir = tmp_path / "cache"
        first = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)
        second = Scraper([2023020015], disable_progress_bar=True, cache=cache_dir)
        _ = first.api_events
        _ = second.api_events
        _ = first.shifts

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            both = Scraper([2023020001, 2023020015], disable_progress_bar=True, cache=cache_dir)
            api_events = both.api_events

        assert sorted(api_events["game_id"].unique().to_list()) == [2023020001, 2023020015]

    def test_save_keeps_the_types_another_scraper_saved(self, tmp_path):
        """save() adds a Scraper's types to the ones already listed for a game instead of replacing them (tu-08)."""
        save_dir = tmp_path / "saved"
        shifts = Scraper([2023020001], disable_progress_bar=True)
        _ = shifts.shifts
        shifts.save(save_dir)
        events = Scraper([2023020001], disable_progress_bar=True)
        _ = events.api_events
        events.save(save_dir)

        entry = json.loads((save_dir / "_meta.json").read_text())["games"]["2023020001"]
        assert {"shifts", "api_events"} <= set(entry["types"])
        assert entry["state"] == "OFF"
        assert Scraper.load(save_dir).shifts.equals(shifts.shifts)

    def test_a_second_writer_waits_for_the_meta_lock(self, tmp_path):
        """While one Scraper holds the lock on _meta.json, another waits for it instead of writing (in-07)."""
        import threading

        from chickenstats.chicken_nhl._scraper_persist import _meta_lock

        held, release, order = threading.Event(), threading.Event(), []

        def hold():
            with _meta_lock(tmp_path):
                order.append("first")
                held.set()
                release.wait()

        def wait():
            with _meta_lock(tmp_path):
                order.append("second")

        holder, waiter = threading.Thread(target=hold), threading.Thread(target=wait)
        holder.start()
        held.wait()
        waiter.start()
        waiter.join(timeout=0.2)
        assert order == ["first"]

        release.set()
        holder.join()
        waiter.join()
        assert order == ["first", "second"]

    def test_a_recovered_game_leaves_the_caches_failed_list(self, tmp_path):
        """A game that failed and then scraped is no longer failed in the cache, so it is not fetched again (ts-14)."""
        from test_failed_reports import failing

        cache_dir = tmp_path / "cache"
        with patch.object(requests.Session, "get", failing("PL", 404)), pytest.warns(UserWarning):
            _ = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir).play_by_play
        recovered = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)
        assert recovered.failed_games == [2023020001]
        recovered.refresh()

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            reread = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)
            play_by_play = reread.play_by_play

        assert reread.failed_games == []
        assert play_by_play.height == 781

    def test_a_cached_failure_is_listed_only_for_its_game(self, tmp_path):
        """A cache= Scraper lists only its own games' cached failures, and load() lists every one (ts-14)."""
        from test_failed_reports import failing

        cache_dir = tmp_path / "cache"
        with patch.object(requests.Session, "get", failing("PL", 404)), pytest.warns(UserWarning):
            _ = Scraper([2023020001, 2023020015], disable_progress_bar=True, cache=cache_dir).play_by_play

        assert Scraper([2023020015], disable_progress_bar=True, cache=cache_dir).failed_games == []
        assert Scraper.load(cache_dir, disable_progress_bar=True).failed_games == [2023020001]

    def test_a_cache_with_other_columns_is_refused(self, tmp_path):
        """A cache whose schema hash differs from this version's columns is refused, not cast (C1)."""
        from chickenstats.exceptions import CacheFormatError

        cache_dir = tmp_path / "cache"
        _ = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir).api_events
        meta = json.loads((cache_dir / "_meta.json").read_text())
        (cache_dir / "_meta.json").write_text(json.dumps({**meta, "schema": "0" * 16}))

        with pytest.raises(CacheFormatError, match="stores columns"):
            Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)

    def test_a_game_from_another_version_is_provisional(self, tmp_path):
        """A game written by another version loads its frames, warns, and is fetched again by the next scrape (C1)."""
        cache_dir = tmp_path / "cache"
        _ = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir).api_events
        meta = json.loads((cache_dir / "_meta.json").read_text())
        meta["games"]["2023020001"]["version"] = "1.8.9"
        (cache_dir / "_meta.json").write_text(json.dumps(meta))

        with pytest.warns(UserWarning, match=r"1 cached game\(s\) were written by chickenstats \['1.8.9'\]") as warned:
            scraper = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)

        assert 2023020001 in scraper._api_events
        assert scraper.game_states == {}
        assert scraper.provisional_games == [2023020001]
        assert [warning.filename for warning in warned] == [__file__]

    def test_a_cache_from_before_1_9_is_refused(self, tmp_path):
        """A cache in the old format is never loaded, because 1.9.0 changed its values (R29)."""
        from chickenstats.exceptions import CacheFormatError

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "_meta.json").write_text(json.dumps({"game_ids": [2023020001], "bad_games": [], "scraped": {}}))
        pl.DataFrame({"game_id": [2023020001]}).write_parquet(cache_dir / "play_by_play.parquet")

        with pytest.raises(CacheFormatError, match="overwrite=True"):
            Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)
        with pytest.raises(CacheFormatError):
            Scraper.load(cache_dir)

        scraper = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir, overwrite=True)
        assert scraper.play_by_play.height == 781
        assert not (cache_dir / "play_by_play.parquet").exists()

    def test_a_failed_write_keeps_the_earlier_file(self, tmp_path):
        """A file is written under a temporary name and swapped in, so a failed write leaves the old one (N54)."""
        from chickenstats.chicken_nhl._scraper_persist import _replace_file

        file = tmp_path / "frame.parquet"
        pl.DataFrame({"a": [1]}).write_parquet(file)

        def half_written(path):
            path.write_bytes(b"PAR1")
            raise OSError("disk full")

        with pytest.raises(OSError, match="disk full"):
            _replace_file(file, half_written)

        assert pl.read_parquet(file)["a"].to_list() == [1]
        assert [path.name for path in tmp_path.iterdir()] == ["frame.parquet"]

    def test_a_listed_file_that_is_missing_is_fetched_again(self, tmp_path):
        cache_dir = tmp_path / "cache"
        _ = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir).play_by_play
        (cache_dir / "shifts" / "2023020001.parquet").unlink()

        scraper = Scraper([2023020001], disable_progress_bar=True, cache=cache_dir)

        assert 2023020001 not in scraper._shifts
        assert scraper.shifts.height > 0

    def test_cache_returns_the_games_asked_for(self, tmp_path):
        """cache= with one game returns that game, and the other cached games stay in the cache (N84)."""
        cache_dir = tmp_path / "cache"
        _ = Scraper([2023020001, 2023020015], disable_progress_bar=True, cache=cache_dir).play_by_play

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            one = Scraper([2023020015], disable_progress_bar=True, cache=cache_dir)
            play_by_play = one.play_by_play

        assert one.game_ids == [2023020015]
        assert play_by_play["game_id"].unique().to_list() == [2023020015]
        assert Scraper.load(cache_dir, disable_progress_bar=True).game_ids == [2023020001, 2023020015]
