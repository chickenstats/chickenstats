import pandas as pd
import pytest

from chickenstats.api.api import ChickenStats


@pytest.mark.skip(reason="Not working yet")
class TestChickenStats:
    def test_check_pbp_game_ids(self):
        api_instance = ChickenStats()

        game_ids = api_instance.check_pbp_game_ids(season=["20232024"], disable_progress_bar=True)

        assert isinstance(game_ids, list) is True

    def test_check_check_pbp_play_ids(self):
        api_instance = ChickenStats()

        play_ids = api_instance.check_pbp_play_ids(season=["20232024"], disable_progress_bar=True)

        assert isinstance(play_ids, list) is True

    def test_download_pbp(self):
        api_instance = ChickenStats()

        pbp_data = api_instance.download_pbp(game_id=[2023020001], strength_state=["5v5"], disable_progress_bar=True)

        assert isinstance(pbp_data, pd.DataFrame) is True

    def test_check_stats_game_ids(self):
        api_instance = ChickenStats()

        game_ids = api_instance.check_stats_game_ids(season=["20232024"], disable_progress_bar=True)

        assert isinstance(game_ids, list) is True

    def test_download_game_stats(self):
        api_instance = ChickenStats()

        game_stats = api_instance.download_game_stats(
            game_id=[2023020001], strength_state=["5v5"], disable_progress_bar=True
        )

        assert isinstance(game_stats, pd.DataFrame) is True

    def test_check_team_stats_game_ids(self):
        api_instance = ChickenStats()

        game_ids = api_instance.check_team_stats_game_ids(season=["20232024"], disable_progress_bar=True)

        assert isinstance(game_ids, list) is True

    def test_check_lines_game_ids(self):
        api_instance = ChickenStats()

        game_ids = api_instance.check_lines_game_ids(season=["20232024"], disable_progress_bar=True)

        assert isinstance(game_ids, list) is True
