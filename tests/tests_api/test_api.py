from unittest.mock import MagicMock, patch

import polars as pl
import pytest

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.api.api import ChickenStats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_page(data, total, has_next):
    """Fake paginated response matching the chickenstats_api response shape."""
    page = MagicMock()
    page.data = data
    page.total = total
    page.count = len(data)
    page.has_next = has_next
    return page


@pytest.fixture(scope="module")
def cs():
    """ChickenStats instance with all SDK network calls patched out."""
    with (
        patch("chickenstats.api.api.chickenstats_api.Configuration"),
        patch("chickenstats.api.api.chickenstats_api.ApiClient"),
        patch("chickenstats.api.api.chickenstats_api.LoginApi") as MockLogin,
    ):
        token = MagicMock()
        token.access_token = "test-token"
        MockLogin.return_value.login_auth0_token.return_value = token
        yield ChickenStats()


# ---------------------------------------------------------------------------
# _finalize_dataframe
# ---------------------------------------------------------------------------


class TestFinalizeDataframe:
    def test_polars_returns_polars(self, cs):
        cs.backend = "polars"
        result = cs._finalize_dataframe([{"col": 1}, {"col": 2}])
        assert isinstance(result, pl.DataFrame)

    def test_polars_drops_all_null_columns(self, cs):
        cs.backend = "polars"
        result = cs._finalize_dataframe([{"col": 1, "empty": None}, {"col": 2, "empty": None}])
        assert "empty" not in result.columns

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_pandas_returns_pandas(self, cs):
        cs.backend = "pandas"
        result = cs._finalize_dataframe([{"col": 1}, {"col": 2}])
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_pandas_drops_all_null_columns(self, cs):
        cs.backend = "pandas"
        result = cs._finalize_dataframe([{"col": 1, "empty": None}, {"col": 2, "empty": None}])
        assert "empty" not in result.columns

    def test_invalid_backend_raises(self, cs):
        cs.backend = "invalid"
        with pytest.raises(ValueError, match="Unsupported backend"):
            cs._finalize_dataframe([{"col": 1}])
        cs.backend = "polars"  # restore


# ---------------------------------------------------------------------------
# _fetch_paginated
# ---------------------------------------------------------------------------


class TestFetchPaginated:
    def test_single_page_returns_all_rows(self, cs):
        rows = [{"a": 1}, {"a": 2}]
        api_method = MagicMock(return_value=_make_page(rows, total=2, has_next=False))
        result = cs._fetch_paginated(
            api_method, limit=100, progress=MagicMock(), progress_task=MagicMock(), pbar_message="test"
        )
        assert result == rows
        api_method.assert_called_once_with(limit=100, offset=0)

    def test_multi_page_concatenates_all_rows(self, cs):
        page1 = _make_page([{"a": 1}], total=2, has_next=True)
        page2 = _make_page([{"a": 2}], total=2, has_next=False)
        api_method = MagicMock(side_effect=[page1, page2])
        result = cs._fetch_paginated(
            api_method, limit=1, progress=MagicMock(), progress_task=MagicMock(), pbar_message="test"
        )
        assert len(result) == 2
        assert api_method.call_count == 2


# ---------------------------------------------------------------------------
# Live endpoint tests — require credentials and a running API
# Run with: pytest -m live
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestChickenStatsLive:
    def test_check_pbp_game_ids(self):
        api = ChickenStats()
        game_ids = api.check_pbp_game_ids(season=["20232024"], disable_progress_bar=True)
        assert isinstance(game_ids, list)

    def test_check_pbp_play_ids(self):
        api = ChickenStats()
        play_ids = api.check_pbp_play_ids(season=["20232024"], disable_progress_bar=True)
        assert isinstance(play_ids, list)

    def test_download_pbp(self):
        api = ChickenStats()
        df = api.download_pbp(game_id=[2023020001], strength_state=["5v5"], disable_progress_bar=True)
        expected_types = (pl.DataFrame, pd.DataFrame) if HAS_PANDAS else pl.DataFrame
        assert isinstance(df, expected_types)

    def test_check_stats_game_ids(self):
        api = ChickenStats()
        game_ids = api.check_stats_game_ids(season=["20232024"], disable_progress_bar=True)
        assert isinstance(game_ids, list)

    def test_download_game_stats(self):
        api = ChickenStats()
        df = api.download_game_stats(game_id=[2023020001], strength_state=["5v5"], disable_progress_bar=True)
        expected_types = (pl.DataFrame, pd.DataFrame) if HAS_PANDAS else pl.DataFrame
        assert isinstance(df, expected_types)

    def test_check_team_stats_game_ids(self):
        api = ChickenStats()
        game_ids = api.check_team_stats_game_ids(season=["20232024"], disable_progress_bar=True)
        assert isinstance(game_ids, list)

    def test_check_lines_game_ids(self):
        api = ChickenStats()
        game_ids = api.check_lines_game_ids(season=["20232024"], disable_progress_bar=True)
        assert isinstance(game_ids, list)

    def test_download_rapm(self):
        api = ChickenStats()
        df = api.download_rapm(season=[2024], disable_progress_bar=True)
        expected_types = (pl.DataFrame, pd.DataFrame) if HAS_PANDAS else pl.DataFrame
        assert isinstance(df, expected_types)

    def test_download_pred_goal(self):
        api = ChickenStats()
        df = api.download_pred_goal(season=[2024], disable_progress_bar=True)
        expected_types = (pl.DataFrame, pd.DataFrame) if HAS_PANDAS else pl.DataFrame
        assert isinstance(df, expected_types)

    def test_get_live_games(self):
        api = ChickenStats()
        df = api.get_live_games(disable_progress_bar=True)
        expected_types = (pl.DataFrame, pd.DataFrame) if HAS_PANDAS else pl.DataFrame
        assert isinstance(df, expected_types)

    def test_download_live_pbp(self):
        api = ChickenStats()
        df = api.download_live_pbp(disable_progress_bar=True)
        expected_types = (pl.DataFrame, pd.DataFrame) if HAS_PANDAS else pl.DataFrame
        assert isinstance(df, expected_types)
