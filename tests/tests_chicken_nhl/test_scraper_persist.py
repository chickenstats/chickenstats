import json
from unittest.mock import patch

import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl.scraper import Scraper


class TestScraperPersist:
    def test_save_creates_files(self, tmp_path):
        """save() writes one parquet file per data type, plus _meta.json."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        save_path = scraper.save(tmp_path / "saved")

        assert (save_path / "_meta.json").exists()
        assert (save_path / "play_by_play.parquet").exists()

    def test_load_round_trips_play_by_play(self, tmp_path):
        """load() reproduces the same play_by_play data without re-scraping."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        original = scraper.play_by_play
        save_path = scraper.save(tmp_path / "saved")

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
        save_path = scraper.save(tmp_path / "saved")

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            loaded = Scraper.load(save_path, disable_progress_bar=True)
            reloaded = {name: getattr(loaded, name) for name in names}

        for name in names:
            assert reloaded[name].equals(originals[name]), name
        assert loaded.failed_games == scraper.failed_games

    def test_load_extends_with_new_game_ids(self, tmp_path):
        """load(..., game_ids=[...]) merges new IDs in without touching the saved ones."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play
        save_path = scraper.save(tmp_path / "saved")

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

        save_path = scraper.save(tmp_path / "saved")
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

    def test_each_game_comes_back_as_its_own_frames(self, tmp_path):
        """A save of two games loads each game's own rows, play_by_play_ext included, with no request."""
        scraper = Scraper([2023020001, 2023020015], disable_progress_bar=True)
        _ = scraper.play_by_play_ext
        save_path = scraper.save(tmp_path / "saved")

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            loaded = Scraper.load(save_path, disable_progress_bar=True)

        for game_id in (2023020001, 2023020015):
            assert loaded._play_by_play[game_id].equals(scraper._play_by_play[game_id])
            assert loaded._play_by_play_ext[game_id].equals(scraper._play_by_play_ext[game_id])
        assert loaded.game_states == scraper.game_states

    def test_a_second_save_replaces_the_first(self, tmp_path):
        """Saving into a directory that holds an earlier save leaves only the new Scraper's games."""
        save_path = tmp_path / "saved"
        both = Scraper([2023020001, 2023020015], disable_progress_bar=True)
        _ = both.play_by_play
        both.save(save_path)
        one = Scraper([2023020015], disable_progress_bar=True)
        _ = one.api_events
        one.save(save_path)

        loaded = Scraper.load(save_path, disable_progress_bar=True)

        assert loaded.game_ids == [2023020015]
        assert loaded._play_by_play == {}
        assert list(loaded._api_events) == [2023020015]

    def test_a_recovered_game_is_saved_without_its_failure(self, tmp_path):
        """A game that failed, was saved, then scraped after load() is saved again with no failure (ts-14)."""
        from test_failed_reports import failing

        save_path = tmp_path / "saved"
        with patch.object(requests.Session, "get", failing("PL", 404)), pytest.warns(UserWarning):
            failed = Scraper([2023020001], disable_progress_bar=True)
            _ = failed.play_by_play
        failed.save(save_path)
        recovered = Scraper.load(save_path, disable_progress_bar=True)
        assert recovered.failed_games == [2023020001]
        recovered.refresh()
        recovered.save(save_path)

        with patch("requests.Session.get", side_effect=AssertionError("should not hit the network")):
            reread = Scraper.load(save_path, disable_progress_bar=True)
            play_by_play = reread.play_by_play

        assert reread.failed_games == []
        assert reread.failure_reasons == {}
        assert play_by_play.height == 781

    def test_a_save_from_another_version_warns(self, tmp_path):
        """A save written by another chickenstats version loads, and warns at the caller (C1)."""
        saved = Scraper([2023020001], disable_progress_bar=True)
        _ = saved.api_events
        save_path = saved.save(tmp_path / "saved")
        meta = json.loads((save_path / "_meta.json").read_text())
        (save_path / "_meta.json").write_text(json.dumps({**meta, "version": "1.9.0rc1"}))

        with pytest.warns(UserWarning, match=r"saved by chickenstats 1\.9\.0rc1, not .*refresh\(\)") as warned:
            scraper = Scraper.load(save_path, disable_progress_bar=True)

        assert 2023020001 in scraper._api_events
        assert [warning.filename for warning in warned] == [__file__]

    @pytest.mark.parametrize(
        "meta",
        [{"game_ids": [2023020001], "bad_games": [], "scraped": {}}, {"format": 3, "game_ids": [2023020001]}],
        ids=["1.8", "1.9 cache"],
    )
    def test_a_save_in_another_format_is_refused(self, tmp_path, meta):
        """A 1.8 save, or a cache from 1.9's development, is never loaded, because 1.9.0 changed its values (R29)."""
        from chickenstats.exceptions import SaveFormatError

        save_path = tmp_path / "saved"
        save_path.mkdir()
        (save_path / "_meta.json").write_text(json.dumps(meta))
        pl.DataFrame({"game_id": [2023020001]}).write_parquet(save_path / "play_by_play.parquet")

        with pytest.raises(SaveFormatError, match="Scrape those games again"):
            Scraper.load(save_path)

    def test_load_passes_its_session_to_the_scraper(self, tmp_path):
        from chickenstats.utilities import ChickenSession

        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_events
        session = ChickenSession()

        assert Scraper.load(scraper.save(tmp_path / "saved"), requests_session=session)._requests_session is session

    def test_a_directory_with_no_save_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No chickenstats save"):
            Scraper.load(tmp_path)

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
