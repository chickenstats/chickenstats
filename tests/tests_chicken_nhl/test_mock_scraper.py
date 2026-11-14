from unittest.mock import patch

import pytest
import polars as pl

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment] # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl.scraper import Scraper


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
        scraper = Scraper(game_ids=[2023029999], disable_progress_bar=True)
        with (
            patch("chickenstats.chicken_nhl._scraper_core.Game", side_effect=ValueError("no game")),
            pytest.warns(UserWarning, match="Failed to scrape"),
        ):
            pbp = scraper.play_by_play

        assert len(pbp) == 0
        assert 2023029999 in scraper.failed_games
