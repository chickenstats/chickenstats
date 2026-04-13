import pandas as pd
import polars as pl
import pyarrow as pa
import narwhals as nw
import pytest

from chickenstats.chicken_nhl.scraper import Scraper


class TestScraper:
    # -------------------------------------------------------------------------
    # api_events
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2023020001, 2023020002, 2023020003, 2023020004, 2023020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_api_events(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        api_events = scraper.api_events

        if backend == "pandas":
            assert isinstance(api_events, pd.DataFrame)
            assert not api_events.empty

        if backend == "polars":
            assert isinstance(api_events, pl.DataFrame)
            assert len(api_events) > 0

    # -------------------------------------------------------------------------
    # api_rosters
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2022020001, 2022020002, 2022020003, 2022020004, 2022020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_api_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        api_rosters = scraper.api_rosters

        if backend == "pandas":
            assert isinstance(api_rosters, pd.DataFrame)
            assert not api_rosters.empty

        if backend == "polars":
            assert isinstance(api_rosters, pl.DataFrame)
            assert len(api_rosters) > 0

    # -------------------------------------------------------------------------
    # changes
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2021020001, 2021020002, 2021020003, 2021020004, 2021020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_changes(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        changes = scraper.changes

        if backend == "pandas":
            assert isinstance(changes, pd.DataFrame)
            assert not changes.empty

        if backend == "polars":
            assert isinstance(changes, pl.DataFrame)
            assert len(changes) > 0

    # -------------------------------------------------------------------------
    # html_events
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2020020001, 2020020002, 2020020003, 2020020004, 2020020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_html_events(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        html_events = scraper.html_events

        if backend == "pandas":
            assert isinstance(html_events, pd.DataFrame)
            assert not html_events.empty

        if backend == "polars":
            assert isinstance(html_events, pl.DataFrame)
            assert len(html_events) > 0

    # -------------------------------------------------------------------------
    # html_rosters
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2019020001, 2019020002, 2019020003, 2019020004, 2019020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_html_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        html_rosters = scraper.html_rosters

        if backend == "pandas":
            assert isinstance(html_rosters, pd.DataFrame)
            assert not html_rosters.empty

        if backend == "polars":
            assert isinstance(html_rosters, pl.DataFrame)
            assert len(html_rosters) > 0

    # -------------------------------------------------------------------------
    # rosters
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2017020001, 2017020002, 2017020003, 2017020004, 2017020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        rosters = scraper.rosters

        if backend == "pandas":
            assert isinstance(rosters, pd.DataFrame)
            assert not rosters.empty

        if backend == "polars":
            assert isinstance(rosters, pl.DataFrame)
            assert len(rosters) > 0

    # -------------------------------------------------------------------------
    # shifts
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_ids", [[2016020001, 2016020002, 2016020003, 2016020004, 2016020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_shifts(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        shifts = scraper.shifts

        if backend == "pandas":
            assert isinstance(shifts, pd.DataFrame)
            assert not shifts.empty

        if backend == "polars":
            assert isinstance(shifts, pl.DataFrame)
            assert len(shifts) > 0

    # -------------------------------------------------------------------------
    # play_by_play + play_by_play_ext
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "game_ids",
        [
            [
                2018020001,
                2018020002,
                2018020003,
                2018020004,
                2018020005,
                2023020124,
                2023020570,
                2023020070,
                2023020021,
                2023020955,
                2023020288,
                2023020005,
                2023020066,
                2023020039,
                2023020004,
                2023020018,
            ]
        ],
    )
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_play_by_play(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        play_by_play = scraper.play_by_play

        if backend == "pandas":
            assert isinstance(play_by_play, pd.DataFrame)
            assert not play_by_play.empty

        if backend == "polars":
            assert isinstance(play_by_play, pl.DataFrame)
            assert len(play_by_play) > 0

    @pytest.mark.parametrize("game_ids", [[2023020001, 2023020002, 2023020003]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_play_by_play_ext(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        play_by_play_ext = scraper.play_by_play_ext

        if backend == "pandas":
            assert isinstance(play_by_play_ext, pd.DataFrame)
            assert not play_by_play_ext.empty

        if backend == "polars":
            assert isinstance(play_by_play_ext, pl.DataFrame)
            assert len(play_by_play_ext) > 0

    # -------------------------------------------------------------------------
    # Selective scraping: only the requested data type is fetched
    # -------------------------------------------------------------------------

    def test_selective_scraping_api_rosters_only(self):
        """Accessing api_rosters should not populate html_events, shifts, etc."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters

        assert len(scraper._scraped_api_rosters) == 1
        assert len(scraper._scraped_html_events) == 0
        assert len(scraper._scraped_html_rosters) == 0
        assert len(scraper._scraped_shifts) == 0
        assert len(scraper._scraped_changes) == 0
        assert len(scraper._scraped_play_by_play) == 0

    def test_selective_scraping_api_events_also_populates_api_rosters(self):
        """api_events and api_rosters share the same HTTP call — both should be tracked."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_events

        assert len(scraper._scraped_api_events) == 1
        assert len(scraper._scraped_api_rosters) == 1
        # Other types should remain unscraped
        assert len(scraper._scraped_html_events) == 0
        assert len(scraper._scraped_shifts) == 0

    def test_selective_scraping_html_events_only(self):
        """Accessing html_events should not populate api_events, shifts, etc."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.html_events

        assert len(scraper._scraped_html_events) == 1
        assert len(scraper._scraped_api_events) == 0
        assert len(scraper._scraped_api_rosters) == 0
        assert len(scraper._scraped_shifts) == 0

    def test_selective_scraping_play_by_play_populates_ext(self):
        """play_by_play and play_by_play_ext share the same scrape — both should be tracked once."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        assert len(scraper._scraped_play_by_play) == 1
        # play_by_play_ext should already be populated (same scrape pass)
        assert len(scraper._play_by_play_ext) > 0

    def test_selective_scraping_no_double_fetch(self):
        """Accessing the same property twice should not re-scrape."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters
        count_after_first = len(scraper._api_rosters)

        # Invalidate the cached_property so the property body runs again,
        # but _scrape should be a no-op because game is already in _scraped_api_rosters
        scraper.__dict__.pop("api_rosters", None)
        _ = scraper.api_rosters
        count_after_second = len(scraper._api_rosters)

        assert count_after_first == count_after_second

    # -------------------------------------------------------------------------
    # add_games() — cache invalidation
    # -------------------------------------------------------------------------

    def test_add_games_invalidates_cache(self):
        """add_games() should clear all cached_property values."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters
        assert "api_rosters" in scraper.__dict__

        scraper.add_games([2023020002])

        # Cache should be cleared
        assert "api_rosters" not in scraper.__dict__
        assert 2023020002 in scraper.game_ids

    def test_add_games_scrapes_new_game(self):
        """After add_games(), accessing a property fetches data for the new game too."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        first_rosters = scraper.api_rosters
        first_count = len(first_rosters)

        scraper.add_games([2023020002])
        second_rosters = scraper.api_rosters
        second_count = len(second_rosters)

        assert second_count > first_count

    # -------------------------------------------------------------------------
    # stats (prep_stats → stats)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("level", ["game", "period", "season", "session"])
    @pytest.mark.parametrize("strength_state", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("teammates", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_stats(self, level, strength_state, score, teammates, opposition, backend):
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_stats(
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
            disable_progress_bar=True,
        )
        stats = scraper.stats

        if backend == "pandas":
            assert isinstance(stats, pd.DataFrame)
            assert not stats.empty

        if backend == "polars":
            assert isinstance(stats, pl.DataFrame)
            assert len(stats) > 0

    # -------------------------------------------------------------------------
    # lines (prep_lines → lines)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("position", ["f", "d"])
    @pytest.mark.parametrize("level", ["game", "period", "season", "session"])
    @pytest.mark.parametrize("strength_state", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("teammates", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_lines(self, position, level, score, strength_state, teammates, opposition, backend):
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_lines(
            position=position,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
            disable_progress_bar=True,
        )
        lines = scraper.lines

        if backend == "pandas":
            assert isinstance(lines, pd.DataFrame)
            assert not lines.empty

        if backend == "polars":
            assert isinstance(lines, pl.DataFrame)
            assert len(lines) > 0

    # -------------------------------------------------------------------------
    # team_stats (prep_team_stats → team_stats)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("level", ["game", "period", "season", "session"])
    @pytest.mark.parametrize("strength_state", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_team_stats(self, level, score, strength_state, opposition, backend):
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_team_stats(
            level=level, score=score, strength_state=strength_state, opposition=opposition, disable_progress_bar=True
        )
        team_stats = scraper.team_stats

        if backend == "pandas":
            assert isinstance(team_stats, pd.DataFrame)
            assert not team_stats.empty

        if backend == "polars":
            assert isinstance(team_stats, pl.DataFrame)
            assert len(team_stats) > 0

    # -------------------------------------------------------------------------
    # __repr__ / __len__ / _is_empty
    # -------------------------------------------------------------------------

    def test_repr(self):
        scraper = Scraper(game_ids=[2023020001, 2023020002], disable_progress_bar=True)
        r = repr(scraper)
        assert "Scraper(game_ids=" in r
        assert "backend=" in r

    def test_len(self):
        scraper = Scraper(game_ids=[2023020001, 2023020002, 2023020003], disable_progress_bar=True)
        assert len(scraper) == 3

    def test_is_empty_polars(self):
        scraper = Scraper(game_ids=[2023020001], backend="polars", disable_progress_bar=True)
        assert scraper._is_empty(scraper._stats) is True

    def test_is_empty_pandas(self):
        # Internal cache is always polars regardless of backend
        scraper = Scraper(game_ids=[2023020001], backend="pandas", disable_progress_bar=True)
        assert isinstance(scraper._stats, pl.DataFrame)
        assert scraper._is_empty(scraper._stats) is True

    def test_is_empty_narwhals(self):
        scraper = Scraper(game_ids=[2023020001], backend="narwhals", disable_progress_bar=True)
        assert isinstance(scraper._stats, pl.DataFrame)
        assert scraper._is_empty(scraper._stats) is True

    # -------------------------------------------------------------------------
    # pyarrow backend
    # -------------------------------------------------------------------------

    def test_api_rosters_pyarrow(self):
        import pyarrow as pa

        scraper = Scraper(game_ids=[2023020001], backend="pyarrow", disable_progress_bar=True)
        api_rosters = scraper.api_rosters
        assert isinstance(api_rosters, pa.Table)
        assert len(api_rosters) > 0

    # -------------------------------------------------------------------------
    # _scrape_single_game exception path
    # -------------------------------------------------------------------------

    def test_scrape_single_game_bad_id_returns_none(self):
        """An invalid game_id that causes Game() to fail should return None, not raise."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        result = scraper._scrape_single_game(game_id=9999999999, scrape_type="api_rosters")
        assert result is None

    # -------------------------------------------------------------------------
    # ind_stats / oi_stats — direct property access (lazy prep path)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_ind_stats_direct_access(self, backend):
        """Accessing ind_stats without calling prep_stats first triggers _prep_ind."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        ind_stats = scraper.ind_stats

        if backend == "pandas":
            assert isinstance(ind_stats, pd.DataFrame)
            assert not ind_stats.empty

        if backend == "polars":
            assert isinstance(ind_stats, pl.DataFrame)
            assert len(ind_stats) > 0

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_oi_stats_direct_access(self, backend):
        """Accessing oi_stats without calling prep_stats first triggers _prep_oi."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        oi_stats = scraper.oi_stats

        if backend == "pandas":
            assert isinstance(oi_stats, pd.DataFrame)
            assert not oi_stats.empty

        if backend == "polars":
            assert isinstance(oi_stats, pl.DataFrame)
            assert len(oi_stats) > 0

    # -------------------------------------------------------------------------
    # stats / lines — lazy-call path (no prep_* called first)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_stats_without_prep(self, backend):
        """Accessing stats without calling prep_stats first auto-calls prep_stats."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        stats = scraper.stats

        if backend == "pandas":
            assert isinstance(stats, pd.DataFrame)
            assert not stats.empty

        if backend == "polars":
            assert isinstance(stats, pl.DataFrame)
            assert len(stats) > 0

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_lines_without_prep(self, backend):
        """Accessing lines without calling prep_lines first auto-calls prep_lines."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        lines = scraper.lines

        if backend == "pandas":
            assert isinstance(lines, pd.DataFrame)
            assert not lines.empty

        if backend == "polars":
            assert isinstance(lines, pl.DataFrame)
            assert len(lines) > 0

    # -------------------------------------------------------------------------
    # _prep_stats partial-empty branches (ind_empty XOR oi_empty)
    # -------------------------------------------------------------------------

    def test_prep_stats_only_ind_empty(self):
        """If _oi_stats is already populated, only _prep_ind should run."""
        scraper = Scraper(game_ids=2023020001, backend="polars", disable_progress_bar=True)
        # Pre-populate oi_stats
        scraper._prep_oi(level="game")
        oi_before = scraper._oi_stats.clone()

        # Now calling prep_stats should only run _prep_ind
        scraper.prep_stats(disable_progress_bar=True)
        stats = scraper.stats

        assert len(stats) > 0
        # oi_stats should be unchanged (same row count)
        assert len(scraper._oi_stats) == len(oi_before)

    def test_prep_stats_only_oi_empty(self):
        """If _ind_stats is already populated, only _prep_oi should run."""
        scraper = Scraper(game_ids=2023020001, backend="polars", disable_progress_bar=True)
        # Pre-populate ind_stats
        scraper._prep_ind(level="game")
        ind_before = scraper._ind_stats.clone()

        # Now calling prep_stats should only run _prep_oi
        scraper.prep_stats(disable_progress_bar=True)
        stats = scraper.stats

        assert len(stats) > 0
        # ind_stats should be unchanged (same row count)
        assert len(scraper._ind_stats) == len(ind_before)

    # -------------------------------------------------------------------------
    # team_stats — lazy-call path (no prep_team_stats called first)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_team_stats_without_prep(self, backend):
        """Accessing team_stats without calling prep_team_stats first auto-calls prep_team_stats."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        team_stats = scraper.team_stats

        if backend == "pandas":
            assert isinstance(team_stats, pd.DataFrame)
            assert not team_stats.empty

        if backend == "polars":
            assert isinstance(team_stats, pl.DataFrame)
            assert len(team_stats) > 0

    # -------------------------------------------------------------------------
    # narwhals / pyarrow backend output types
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(("backend", "expected_type"), [("pyarrow", pa.Table), ("narwhals", nw.DataFrame)])
    def test_stats_narwhals_backends(self, backend, expected_type):
        """stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        stats = scraper.stats
        assert isinstance(stats, expected_type)
        assert len(stats) > 0

    @pytest.mark.parametrize(("backend", "expected_type"), [("pyarrow", pa.Table), ("narwhals", nw.DataFrame)])
    def test_lines_narwhals_backends(self, backend, expected_type):
        """lines property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        lines = scraper.lines
        assert isinstance(lines, expected_type)
        assert len(lines) > 0

    @pytest.mark.parametrize(("backend", "expected_type"), [("pyarrow", pa.Table), ("narwhals", nw.DataFrame)])
    def test_team_stats_narwhals_backends(self, backend, expected_type):
        """team_stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        team_stats = scraper.team_stats
        assert isinstance(team_stats, expected_type)
        assert len(team_stats) > 0

    @pytest.mark.parametrize(("backend", "expected_type"), [("pyarrow", pa.Table), ("narwhals", nw.DataFrame)])
    def test_ind_stats_narwhals_backends(self, backend, expected_type):
        """ind_stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        ind_stats = scraper.ind_stats
        assert isinstance(ind_stats, expected_type)
        assert len(ind_stats) > 0

    @pytest.mark.parametrize(("backend", "expected_type"), [("pyarrow", pa.Table), ("narwhals", nw.DataFrame)])
    def test_oi_stats_narwhals_backends(self, backend, expected_type):
        """oi_stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        oi_stats = scraper.oi_stats
        assert isinstance(oi_stats, expected_type)
        assert len(oi_stats) > 0

    # -------------------------------------------------------------------------
    # Internal cache is always polars
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", ["pandas", "polars", "pyarrow", "narwhals"])
    def test_internal_cache_always_polars(self, backend):
        """Regardless of backend, _stats/_lines/_team_stats are stored as pl.DataFrame."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_stats(disable_progress_bar=True)
        assert isinstance(scraper._stats, pl.DataFrame)
        assert isinstance(scraper._ind_stats, pl.DataFrame)
        assert isinstance(scraper._oi_stats, pl.DataFrame)

    # -------------------------------------------------------------------------
    # Bad game tracking
    # -------------------------------------------------------------------------

    def test_bad_game_id_tracked(self):
        """An invalid game_id that causes scraping to fail should be recorded in _bad_games."""
        scraper = Scraper(game_ids=[9999999999], disable_progress_bar=True)
        _ = scraper.api_rosters
        assert 9999999999 in scraper._bad_games
