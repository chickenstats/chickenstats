import json
import warnings
from unittest.mock import patch

import polars as pl
import narwhals as nw
import pytest
import requests

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

try:
    import pyarrow as pa

    HAS_PYARROW = True
    _PA_TABLE = pa.Table
except ImportError:
    pa = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PYARROW = False
    _PA_TABLE = type(None)

from chickenstats.chicken_nhl.scraper import Scraper
from chickenstats.exceptions import InvalidGameIDError

_skip_no_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
_skip_no_pyarrow = pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")


class TestScraper:
    # -----------------------------------------------------------------------------
    # api_events
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2023020001, 2023020002, 2023020003, 2023020004, 2023020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_api_events(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        api_events = scraper.api_events

        if backend == "pandas":
            assert isinstance(api_events, pd.DataFrame)
            assert not api_events.empty

        if backend == "polars":
            assert isinstance(api_events, pl.DataFrame)
            assert len(api_events) > 0

    # -----------------------------------------------------------------------------
    # api_rosters
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2022020001, 2022020002, 2022020003, 2022020004, 2022020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_api_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        api_rosters = scraper.api_rosters

        if backend == "pandas":
            assert isinstance(api_rosters, pd.DataFrame)
            assert not api_rosters.empty

        if backend == "polars":
            assert isinstance(api_rosters, pl.DataFrame)
            assert len(api_rosters) > 0

    # -----------------------------------------------------------------------------
    # changes
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2021020001, 2021020002, 2021020003, 2021020004, 2021020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_changes(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        changes = scraper.changes

        if backend == "pandas":
            assert isinstance(changes, pd.DataFrame)
            assert not changes.empty

        if backend == "polars":
            assert isinstance(changes, pl.DataFrame)
            assert len(changes) > 0

    # -----------------------------------------------------------------------------
    # html_events
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2020020001, 2020020002, 2020020003, 2020020004, 2020020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_html_events(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        html_events = scraper.html_events

        if backend == "pandas":
            assert isinstance(html_events, pd.DataFrame)
            assert not html_events.empty

        if backend == "polars":
            assert isinstance(html_events, pl.DataFrame)
            assert len(html_events) > 0

    # -----------------------------------------------------------------------------
    # html_rosters
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2019020001, 2019020002, 2019020003, 2019020004, 2019020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_html_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        html_rosters = scraper.html_rosters

        if backend == "pandas":
            assert isinstance(html_rosters, pd.DataFrame)
            assert not html_rosters.empty

        if backend == "polars":
            assert isinstance(html_rosters, pl.DataFrame)
            assert len(html_rosters) > 0

    # -----------------------------------------------------------------------------
    # rosters
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2017020001, 2017020002, 2017020003, 2017020004, 2017020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        rosters = scraper.rosters

        if backend == "pandas":
            assert isinstance(rosters, pd.DataFrame)
            assert not rosters.empty

        if backend == "polars":
            assert isinstance(rosters, pl.DataFrame)
            assert len(rosters) > 0

    # -----------------------------------------------------------------------------
    # shifts
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2016020001, 2016020002, 2016020003, 2016020004, 2016020005]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_shifts(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        shifts = scraper.shifts

        if backend == "pandas":
            assert isinstance(shifts, pd.DataFrame)
            assert not shifts.empty

        if backend == "polars":
            assert isinstance(shifts, pl.DataFrame)
            assert len(shifts) > 0

    # -----------------------------------------------------------------------------
    # play_by_play + play_by_play_ext
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
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
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_play_by_play(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        play_by_play = scraper.play_by_play

        if backend == "pandas":
            assert isinstance(play_by_play, pd.DataFrame)
            assert not play_by_play.empty

        if backend == "polars":
            assert isinstance(play_by_play, pl.DataFrame)
            assert len(play_by_play) > 0

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_ids", [[2023020001, 2023020002, 2023020003]])
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_play_by_play_ext(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend, disable_progress_bar=True)
        play_by_play_ext = scraper.play_by_play_ext

        if backend == "pandas":
            assert isinstance(play_by_play_ext, pd.DataFrame)
            assert not play_by_play_ext.empty

        if backend == "polars":
            assert isinstance(play_by_play_ext, pl.DataFrame)
            assert len(play_by_play_ext) > 0

    # -----------------------------------------------------------------------------
    # Selective scraping: only the requested data type is fetched
    # -----------------------------------------------------------------------------

    def test_selective_scraping_api_rosters_only(self):
        """Accessing api_rosters should not populate html_events, shifts, etc."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters

        assert len(scraper._api_rosters) == 1
        assert len(scraper._html_events) == 0
        assert len(scraper._html_rosters) == 0
        assert len(scraper._shifts) == 0
        assert len(scraper._changes) == 0
        assert len(scraper._play_by_play) == 0

    def test_selective_scraping_api_events_also_populates_api_rosters(self):
        """api_events and api_rosters share the same HTTP call — both should be tracked."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_events

        assert len(scraper._api_events) == 1
        assert len(scraper._api_rosters) == 1
        # Other types should remain unscraped
        assert len(scraper._html_events) == 0
        assert len(scraper._shifts) == 0

    def test_selective_scraping_html_events_only(self):
        """Accessing html_events stores the rosters it is built from, but not api_events or shifts."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.html_events

        assert len(scraper._html_events) == 1
        assert len(scraper._rosters) == 1
        assert len(scraper._api_events) == 0
        assert len(scraper._shifts) == 0

    def test_selective_scraping_play_by_play_populates_ext(self):
        """play_by_play and play_by_play_ext share the same scrape — both should be tracked once."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play

        assert len(scraper._play_by_play) == 1
        # play_by_play_ext should already be populated (same scrape pass)
        assert len(scraper._play_by_play_ext) > 0

    def test_selective_scraping_no_double_fetch(self):
        """Accessing the same property twice should not re-scrape."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters
        count_after_first = len(scraper._api_rosters)

        # Invalidate the cached_property so the property body runs again,
        # but _scrape should be a no-op because the game is already stored in _api_rosters
        scraper.__dict__.pop("api_rosters", None)
        _ = scraper.api_rosters
        count_after_second = len(scraper._api_rosters)

        assert count_after_first == 1
        assert count_after_first == count_after_second

    # -----------------------------------------------------------------------------
    # add_games() — cache invalidation
    # -----------------------------------------------------------------------------

    def test_add_games_invalidates_cache(self):
        """add_games() should clear all cached_property values."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters
        assert "api_rosters" in scraper.__dict__

        scraper.add_games([2023020002])

        # Cache should be cleared
        assert "api_rosters" not in scraper.__dict__
        assert 2023020002 in scraper.game_ids

    @pytest.mark.nhl
    def test_add_games_scrapes_new_game(self):
        """After add_games(), accessing a property fetches data for the new game too."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        first_rosters = scraper.api_rosters
        first_count = len(first_rosters)

        scraper.add_games([2023020002])
        second_rosters = scraper.api_rosters
        second_count = len(second_rosters)

        assert second_count > first_count

    # -----------------------------------------------------------------------------
    # stats (prep_stats → stats)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "level,strength_state,score,teammates,opposition,backend",
        [
            ("game", False, False, False, False, "polars"),
            pytest.param("period", False, False, False, False, "pandas", marks=_skip_no_pandas),
            ("season", False, False, False, False, "polars"),
            pytest.param("session", False, False, False, False, "pandas", marks=_skip_no_pandas),
            ("game", True, False, False, False, "polars"),
            pytest.param("game", False, True, False, False, "pandas", marks=_skip_no_pandas),
            ("game", False, False, True, False, "polars"),
            pytest.param("game", False, False, False, True, "pandas", marks=_skip_no_pandas),
            ("game", True, True, True, True, "polars"),
        ],
    )
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

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(stats, pd.DataFrame)
            assert not stats.empty

        if backend == "polars":
            assert isinstance(stats, pl.DataFrame)
            assert len(stats) > 0

    # -----------------------------------------------------------------------------
    # lines (prep_lines → lines)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "position,level,strength_state,score,teammates,opposition,backend",
        [
            ("f", "game", False, False, False, False, "polars"),
            pytest.param("d", "game", False, False, False, False, "pandas", marks=_skip_no_pandas),
            pytest.param("f", "period", False, False, False, False, "pandas", marks=_skip_no_pandas),
            ("d", "season", False, False, False, False, "polars"),
            ("f", "session", False, False, False, False, "polars"),
            pytest.param("f", "game", True, False, False, False, "pandas", marks=_skip_no_pandas),
            ("d", "game", False, True, False, False, "polars"),
            pytest.param("f", "game", False, False, True, False, "pandas", marks=_skip_no_pandas),
            ("d", "game", False, False, False, True, "polars"),
            pytest.param("f", "game", True, True, True, True, "pandas", marks=_skip_no_pandas),
        ],
    )
    def test_lines(self, position, level, strength_state, score, teammates, opposition, backend):
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

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(lines, pd.DataFrame)
            assert not lines.empty

        if backend == "polars":
            assert isinstance(lines, pl.DataFrame)
            assert len(lines) > 0

    # -----------------------------------------------------------------------------
    # team_stats (prep_team_stats → team_stats)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "level,strength_state,score,opposition,backend",
        [
            ("game", False, False, False, "polars"),
            pytest.param("period", False, False, False, "pandas", marks=_skip_no_pandas),
            ("season", False, False, False, "polars"),
            pytest.param("session", False, False, False, "pandas", marks=_skip_no_pandas),
            ("game", True, False, False, "polars"),
            pytest.param("game", False, True, False, "pandas", marks=_skip_no_pandas),
            ("game", False, False, True, "polars"),
            pytest.param("game", True, True, True, "pandas", marks=_skip_no_pandas),
        ],
    )
    def test_team_stats(self, level, strength_state, score, opposition, backend):
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_team_stats(
            level=level, score=score, strength_state=strength_state, opposition=opposition, disable_progress_bar=True
        )
        team_stats = scraper.team_stats

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(team_stats, pd.DataFrame)
            assert not team_stats.empty

        if backend == "polars":
            assert isinstance(team_stats, pl.DataFrame)
            assert len(team_stats) > 0

    # -----------------------------------------------------------------------------
    # stints (prep_stints → stints)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "min_skaters,backend",
        [
            (3, "polars"),
            pytest.param(3, "pandas", marks=_skip_no_pandas),
            (2, "polars"),
            pytest.param(4, "pandas", marks=_skip_no_pandas),
        ],
    )
    def test_stints(self, min_skaters, backend):
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_stints(min_skaters=min_skaters, disable_progress_bar=True)
        stints = scraper.stints

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(stints, pd.DataFrame)
            assert not stints.empty
            assert (stints.home_skater_count >= min_skaters).all()

        if backend == "polars":
            assert isinstance(stints, pl.DataFrame)
            assert len(stints) > 0
            assert (stints["home_skater_count"] >= min_skaters).all()

    def test_prep_stints_invalidates_cache_on_new_min_skaters(self):
        scraper = Scraper(game_ids=2023020001, backend="polars", disable_progress_bar=True)
        loose = scraper.prep_stints(min_skaters=2, disable_progress_bar=True).stints
        strict = scraper.prep_stints(min_skaters=5, disable_progress_bar=True).stints

        assert len(strict) < len(loose)
        assert (strict["home_skater_count"] >= 5).all()

    # -----------------------------------------------------------------------------
    # __repr__ / __len__ / _is_empty
    # -----------------------------------------------------------------------------

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

    # -----------------------------------------------------------------------------
    # pyarrow backend
    # -----------------------------------------------------------------------------

    @pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
    def test_api_rosters_pyarrow(self):
        scraper = Scraper(game_ids=[2023020001], backend="pyarrow", disable_progress_bar=True)
        api_rosters = scraper.api_rosters
        assert isinstance(api_rosters, _PA_TABLE)
        assert len(api_rosters) > 0

    # -----------------------------------------------------------------------------
    # _scrape_single_game exception path
    # -----------------------------------------------------------------------------

    def test_scrape_single_game_bad_id_returns_the_error(self):
        """A game_id that causes the scrape to fail returns the exception instead of raising it."""
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        result = scraper._scrape_single_game(game_id=9999999999, scrape_types=("api_rosters",))
        assert isinstance(result, Exception)

    def test_a_game_is_not_kept_after_its_frames_are_stored(self):
        """A later scrape of another type reuses the stored frames instead of a kept Game (R14, N18)."""
        from chickenstats.chicken_nhl import _scraper_core

        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        _ = scraper.api_rosters
        assert not hasattr(scraper, "_games")

        seeded = []
        seed = _scraper_core._ScraperCore._seed_game_from_cache

        def recording_seed(self, game, game_id):
            seed(self, game, game_id)
            seeded.append(set(game.__dict__) & {"api_events", "api_rosters"})

        with patch.object(_scraper_core._ScraperCore, "_seed_game_from_cache", recording_seed):
            _ = scraper.rosters

        assert seeded == [{"api_rosters"}]

    def test_scrape_single_game_expected_error_logs_warning(self, caplog):
        """A known/expected failure class (ChickenstatsError, RequestException,
        pydantic ValidationError) should be logged at WARNING and returned."""
        from chickenstats.exceptions import DataMismatchError

        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        with patch(
            "chickenstats.chicken_nhl._scraper_core.Game", side_effect=DataMismatchError("simulated data issue")
        ):
            with caplog.at_level("WARNING"):
                result = scraper._scrape_single_game(game_id=2023020001, scrape_types=("api_rosters",))

        assert isinstance(result, DataMismatchError)
        assert any(
            record.levelname == "WARNING" and "Failed to scrape game" in record.message for record in caplog.records
        )

    def test_scrape_single_game_unexpected_error_logs_error(self, caplog):
        """An exception type that isn't one of the known/expected failure classes (e.g. a
        real bug like AttributeError/TypeError) should be logged at ERROR, not WARNING, so
        it's distinguishable from routine per-game data/network issues — while still
        returning the exception rather than crashing the batch scrape.
        """
        scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
        with patch("chickenstats.chicken_nhl._scraper_core.Game", side_effect=TypeError("simulated bug")):
            with caplog.at_level("WARNING"):
                result = scraper._scrape_single_game(game_id=2023020001, scrape_types=("api_rosters",))

        assert isinstance(result, TypeError)
        assert any(
            record.levelname == "ERROR" and "Unexpected error scraping game" in record.message
            for record in caplog.records
        )

    # -----------------------------------------------------------------------------
    # ind_stats / oi_stats — direct property access (lazy prep path)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
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

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
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

        # Regression test: give/take were computed but commented out of the schema, so they
        # were silently dropped from the final output despite being referenced in
        # _agg_constants.py's stat lists.
        assert "give" in oi_stats.columns
        assert "take" in oi_stats.columns

    # -----------------------------------------------------------------------------
    # stats / lines / stints — lazy-call path (no prep_* called first)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
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

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
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

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_stints_without_prep(self, backend):
        """Accessing stints without calling prep_stints first auto-calls prep_stints."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        stints = scraper.stints

        if backend == "pandas":
            assert isinstance(stints, pd.DataFrame)
            assert not stints.empty

        if backend == "polars":
            assert isinstance(stints, pl.DataFrame)
            assert len(stints) > 0

    # -----------------------------------------------------------------------------
    # _prep_stats partial-empty branches (ind_empty XOR oi_empty)
    # -----------------------------------------------------------------------------

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

    # -----------------------------------------------------------------------------
    # team_stats — lazy-call path (no prep_team_stats called first)
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
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

    # -----------------------------------------------------------------------------
    # narwhals / pyarrow backend output types
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("backend", "expected_type"),
        [pytest.param("pyarrow", _PA_TABLE, marks=_skip_no_pyarrow), pytest.param("narwhals", nw.DataFrame)],
    )
    def test_stats_narwhals_backends(self, backend, expected_type):
        """stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        stats = scraper.stats
        assert isinstance(stats, expected_type)
        assert len(stats) > 0

    @pytest.mark.parametrize(
        ("backend", "expected_type"),
        [pytest.param("pyarrow", _PA_TABLE, marks=_skip_no_pyarrow), pytest.param("narwhals", nw.DataFrame)],
    )
    def test_lines_narwhals_backends(self, backend, expected_type):
        """lines property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        lines = scraper.lines
        assert isinstance(lines, expected_type)
        assert len(lines) > 0

    @pytest.mark.parametrize(
        ("backend", "expected_type"),
        [pytest.param("pyarrow", _PA_TABLE, marks=_skip_no_pyarrow), pytest.param("narwhals", nw.DataFrame)],
    )
    def test_team_stats_narwhals_backends(self, backend, expected_type):
        """team_stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        team_stats = scraper.team_stats
        assert isinstance(team_stats, expected_type)
        assert len(team_stats) > 0

    @pytest.mark.parametrize(
        ("backend", "expected_type"),
        [pytest.param("pyarrow", _PA_TABLE, marks=_skip_no_pyarrow), pytest.param("narwhals", nw.DataFrame)],
    )
    def test_ind_stats_narwhals_backends(self, backend, expected_type):
        """ind_stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        ind_stats = scraper.ind_stats
        assert isinstance(ind_stats, expected_type)
        assert len(ind_stats) > 0

    @pytest.mark.parametrize(
        ("backend", "expected_type"),
        [pytest.param("pyarrow", _PA_TABLE, marks=_skip_no_pyarrow), pytest.param("narwhals", nw.DataFrame)],
    )
    def test_oi_stats_narwhals_backends(self, backend, expected_type):
        """oi_stats property returns the correct type for pyarrow and narwhals backends."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        oi_stats = scraper.oi_stats
        assert isinstance(oi_stats, expected_type)
        assert len(oi_stats) > 0

    # -----------------------------------------------------------------------------
    # Internal cache is always polars
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "backend",
        [
            pytest.param("pandas", marks=_skip_no_pandas),
            "polars",
            pytest.param("pyarrow", marks=_skip_no_pyarrow),
            "narwhals",
        ],
    )
    def test_internal_cache_always_polars(self, backend):
        """Regardless of backend, _stats/_lines/_team_stats are stored as pl.DataFrame."""
        scraper = Scraper(game_ids=2023020001, backend=backend, disable_progress_bar=True)
        scraper.prep_stats(disable_progress_bar=True)
        assert isinstance(scraper._stats, pl.DataFrame)
        assert isinstance(scraper._ind_stats, pl.DataFrame)
        assert isinstance(scraper._oi_stats, pl.DataFrame)
        assert (scraper._stats.height, scraper._ind_stats.height, scraper._oi_stats.height) == (122, 81, 122)

    # -----------------------------------------------------------------------------
    # Bad game tracking
    # -----------------------------------------------------------------------------

    def test_bad_game_id_tracked(self):
        """An invalid game_id that causes scraping to fail should be recorded in failed_games."""
        scraper = Scraper(game_ids=[9999999999], disable_progress_bar=True)
        with pytest.warns(UserWarning, match="Failed to scrape"):
            _ = scraper.api_rosters
        assert 9999999999 in scraper.failed_games

    # -----------------------------------------------------------------------------
    # Chaining (prep_* returns Self)
    # -----------------------------------------------------------------------------

    def test_prep_stats_returns_scraper(self):
        """prep_stats() returns the Scraper instance to enable chaining."""
        scraper = Scraper(game_ids=2023020001, disable_progress_bar=True)
        result = scraper.prep_stats(disable_progress_bar=True)
        assert result is scraper

    def test_prep_lines_returns_scraper(self):
        """prep_lines() returns the Scraper instance to enable chaining."""
        scraper = Scraper(game_ids=2023020001, disable_progress_bar=True)
        result = scraper.prep_lines(disable_progress_bar=True)
        assert result is scraper

    def test_prep_team_stats_returns_scraper(self):
        """prep_team_stats() returns the Scraper instance to enable chaining."""
        scraper = Scraper(game_ids=2023020001, disable_progress_bar=True)
        result = scraper.prep_team_stats(disable_progress_bar=True)
        assert result is scraper

    def test_chained_stats(self):
        """prep_stats().stats returns a non-empty DataFrame."""
        scraper = Scraper(game_ids=2023020001, disable_progress_bar=True)
        stats = scraper.prep_stats(level="game", disable_progress_bar=True).stats
        assert isinstance(stats, pl.DataFrame)
        assert len(stats) > 0

    def test_chained_lines(self):
        """prep_lines().lines returns a non-empty DataFrame."""
        scraper = Scraper(game_ids=2023020001, disable_progress_bar=True)
        lines = scraper.prep_lines(level="game", disable_progress_bar=True).lines
        assert isinstance(lines, pl.DataFrame)
        assert len(lines) > 0

    def test_chained_team_stats(self):
        """prep_team_stats().team_stats returns a non-empty DataFrame."""
        scraper = Scraper(game_ids=2023020001, disable_progress_bar=True)
        team_stats = scraper.prep_team_stats(level="game", disable_progress_bar=True).team_stats
        assert isinstance(team_stats, pl.DataFrame)
        assert len(team_stats) > 0


class TestGameIds:
    """Game IDs are ints, in order, each once, in a list the Scraper owns."""

    def test_floats_strings_and_repeats_become_one_int_each(self):
        scraper = Scraper(
            [2023020001, 2023020002.0, "2023020001", " 2023020003 ", 2023020002], disable_progress_bar=True
        )

        assert scraper.game_ids == [2023020001, 2023020002, 2023020003]

    @pytest.mark.parametrize("game_id", ["FAIL", 2023020001.5, None])
    def test_an_id_that_is_not_a_whole_number_raises(self, game_id):
        with pytest.raises(InvalidGameIDError):
            Scraper([2023020001, game_id], disable_progress_bar=True)

    def test_add_games_does_not_change_the_callers_list(self):
        game_ids: list[str | float | int] = [2023020001]
        scraper = Scraper(game_ids, disable_progress_bar=True)

        scraper.add_games(["2023020002", 2023020002.0, 2023020001])

        assert scraper.game_ids == [2023020001, 2023020002]
        assert game_ids == [2023020001]

    def test_load_normalizes_the_game_ids_it_adds(self, tmp_path):
        scraper = Scraper([2023020001], disable_progress_bar=True)
        _ = scraper.play_by_play
        path = scraper.save(tmp_path / "cache")

        loaded = Scraper.load(path, game_ids=["2023020002", 2023020001.0], disable_progress_bar=True)

        assert loaded.game_ids == [2023020001, 2023020002]


def test_a_frame_that_cannot_be_built_fails_its_game_without_storing_the_rest():
    """A game's frames are stored together: if one cannot be built, the game fails and no type records it."""
    from chickenstats.chicken_nhl import _scraper_core

    from_dicts = pl.from_dicts
    shifts_schema = _scraper_core._SCRAPE_REGISTRY["shifts"].schema

    def broken_shifts(data, *args, schema=None, **kwargs):
        if schema is shifts_schema:
            raise ValueError("a shifts frame that cannot be built")
        return from_dicts(data, *args, schema=schema, **kwargs)

    with (
        patch.object(_scraper_core.pl, "from_dicts", broken_shifts),
        pytest.warns(UserWarning, match="Failed to scrape"),
    ):
        scraper = Scraper([2023020001], disable_progress_bar=True)
        play_by_play = scraper.play_by_play

    assert scraper.failed_games == [2023020001]
    assert play_by_play.height == 0
    assert 2023020001 not in {*scraper._api_events, *scraper._rosters, *scraper._play_by_play}


def test_add_games_rebuilds_every_result_with_its_last_arguments():
    """After add_games, each result covers the new games too, built with the arguments it was last built with."""
    scraper = Scraper([2023020001], disable_progress_bar=True)
    scraper.prep_stats(level="season", strength_state=False, disable_progress_bar=True)
    scraper.prep_team_stats(level="season", strength_state=False, disable_progress_bar=True)
    scraper.prep_lines(level="season", strength_state=False, disable_progress_bar=True)
    first = {"stats": scraper.stats["toi"].sum(), "team_stats": scraper.team_stats["toi"].sum()}
    first["lines"], first["stints"] = scraper.lines["toi"].sum(), scraper.stints.height

    scraper.add_games([2023020015])

    both = Scraper([2023020001, 2023020015], disable_progress_bar=True)
    both.prep_stats(level="season", strength_state=False, disable_progress_bar=True)
    both.prep_team_stats(level="season", strength_state=False, disable_progress_bar=True)
    both.prep_lines(level="season", strength_state=False, disable_progress_bar=True)

    for name in ("stats", "team_stats", "lines"):
        assert getattr(scraper, name).equals(getattr(both, name)), name
        assert getattr(scraper, name)["toi"].sum() > first[name], name
    assert scraper.stints.height > first["stints"]
    assert "game_id" not in scraper.stats.columns


class TestFailedGames:
    """failed_games lists each game once, until every type that failed for it has been scraped."""

    @staticmethod
    def failing_play_by_play():
        from test_failed_reports import failing

        return patch.object(requests.Session, "get", failing("PL", 404))

    def test_a_game_is_listed_once_and_the_list_is_a_copy(self):
        with self.failing_play_by_play(), pytest.warns(UserWarning):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play
            _ = scraper.html_events

        listed = scraper.failed_games
        listed.append(1)
        assert scraper.failed_games == [2023020001]

    def test_a_repeat_failure_warns_again(self):
        with self.failing_play_by_play():
            scraper = Scraper([2023020001], disable_progress_bar=True)
            with pytest.warns(UserWarning, match="Failed to scrape 1 game"):
                _ = scraper.play_by_play
            with pytest.warns(UserWarning, match="Failed to scrape 1 game"):
                _ = scraper.html_events

    def test_another_type_that_succeeds_does_not_clear_the_failure(self):
        with self.failing_play_by_play(), pytest.warns(UserWarning):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play
        _ = scraper.rosters

        assert scraper.failed_games == [2023020001]

    def test_a_cached_failure_is_cleared_when_the_game_scrapes(self, tmp_path):
        with self.failing_play_by_play(), pytest.warns(UserWarning):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play
        path = scraper.save(tmp_path / "cache")

        loaded = Scraper.load(path, disable_progress_bar=True)
        assert loaded.failed_games == [2023020001]

        assert loaded.play_by_play.height == 781
        assert loaded.failed_games == []


def test_a_scraped_game_leaves_only_its_frames_behind():
    """Each game's Game object is dropped once its frames are stored (R14, N18).

    tracemalloc sees Python objects, not the frames' Arrow buffers, so this measures what a kept Game cost:
    about 15 MB of row dicts per game before, and almost nothing now.
    """
    import gc
    import tracemalloc

    saved: list[str | float | int] = [
        2023020001,
        2023020015,
        2023020125,
        2023020411,
        2023030223,
        2010020012,
        2017030111,
    ]

    warm = Scraper(saved[:1], disable_progress_bar=True)
    _ = warm.play_by_play
    del warm
    gc.collect()

    tracemalloc.start()
    try:
        before = tracemalloc.get_traced_memory()[0]
        scraper = Scraper(saved, disable_progress_bar=True)
        _ = scraper.play_by_play
        scraper.__dict__.pop("play_by_play")
        gc.collect()
        per_game = (tracemalloc.get_traced_memory()[0] - before) / len(saved)
    finally:
        tracemalloc.stop()

    assert per_game < 1_000_000


class TestGameState:
    """Only a game the API reports as OFF is final; a game in any other state is fetched again (N9)."""

    @staticmethod
    def served_as(state: str, requested: list[str]):
        """A Session.get that serves the saved responses with the fixture game's API state set to state."""
        served_get = requests.Session.get

        def get(self, url, *args, **kwargs):
            requested.append(str(url))
            response = served_get(self, url, *args, **kwargs)
            if "gamecenter/2023020001/play-by-play" in str(url):
                payload = response.json()
                payload["gameState"] = state
                response._content = json.dumps(payload).encode()
            return response

        return get

    @staticmethod
    def html_requests(requested: list[str]) -> int:
        return sum("020001.HTM" in url for url in requested)

    def test_a_final_game_is_fetched_again_and_its_rows_replaced(self):
        requested: list[str] = []
        with patch.object(requests.Session, "get", self.served_as("FINAL", requested)):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            first = scraper.play_by_play
            fetched = self.html_requests(requested)

            scraper.add_games([2023020015])
            second = scraper.play_by_play

        assert scraper._game_states[2023020001] == "FINAL"
        assert self.html_requests(requested) == 2 * fetched
        assert second.filter(pl.col("game_id") == 2023020001).equals(first)

    def test_an_off_game_is_not_fetched_again(self):
        requested: list[str] = []
        with patch.object(requests.Session, "get", self.served_as("OFF", requested)):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play
            fetched = len(requested)

            _ = scraper.shifts
            scraper.add_games([2023020001])
            _ = scraper.play_by_play

        assert scraper._game_states[2023020001] == "OFF"
        assert len(requested) == fetched

    def test_a_final_game_from_a_save_is_fetched_again(self, tmp_path):
        """A save taken before the game is OFF does not keep that data for good."""
        requested: list[str] = []
        with patch.object(requests.Session, "get", self.served_as("FINAL", requested)):
            saved = Scraper([2023020001], disable_progress_bar=True)
            _ = saved.play_by_play
            saved.save(tmp_path / "saved")
        with patch.object(requests.Session, "get", self.served_as("OFF", requested)):
            requested.clear()
            scraper = Scraper.load(tmp_path / "saved", disable_progress_bar=True)
            play_by_play = scraper.play_by_play

        assert self.html_requests(requested) > 0
        assert scraper._game_states[2023020001] == "OFF"
        assert play_by_play.height == 781

    def test_a_live_game_is_fetched_once_per_call(self):
        """prep_stats reads play_by_play and play_by_play_ext from one download; a later read fetches the game again."""
        requested: list[str] = []
        reports = ["gamecenter/2023020001/play-by-play", "PL020001", "RO020001", "TH020001", "TV020001"]
        with patch.object(requests.Session, "get", self.served_as("LIVE", requested)):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.prep_stats()
            once = {report: sum(report in url for url in requested) for report in reports}
            fetched = len(requested)

            _ = scraper.play_by_play

        assert once == dict.fromkeys(reports, 1)
        assert len(requested) > fetched

    def test_replacing_a_live_game_clears_the_frames_already_read(self):
        """A read that fetches a game in progress again rebuilds every frame from the new download."""
        with patch.object(requests.Session, "get", self.served_as("LIVE", [])):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play, scraper.prep_stats().stats
            _ = scraper.shifts

        assert "play_by_play" not in scraper.__dict__
        assert scraper._stats.is_empty()

    def test_one_type_fetched_at_off_leaves_the_game_provisional(self, tmp_path):
        """The play-by-play from before the game was OFF is fetched again, and the game is not saved as OFF."""
        requested: list[str] = []
        with patch.object(requests.Session, "get", self.served_as("LIVE", requested)):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play
        with patch.object(requests.Session, "get", self.served_as("OFF", requested)):
            _ = scraper.api_rosters
            provisional = not scraper._is_final(2023020001)
            scraper.save(tmp_path / "saved")
            saved = json.loads((tmp_path / "saved" / "_meta.json").read_text())["states"].get("2023020001")

            requested.clear()
            _ = scraper.play_by_play

        assert provisional
        assert saved is None
        assert self.html_requests(requested) > 0
        assert scraper._is_final(2023020001)

    def test_a_game_that_has_not_started_makes_one_request(self):
        """The API state is read before the HTML reports are requested, and a PRE game has none (pf-05)."""
        requested: list[str] = []
        with patch.object(requests.Session, "get", self.served_as("PRE", requested)), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.play_by_play

        assert len(requested) == 1
        assert scraper.not_started_games == [2023020001]

    def test_a_refresh_requests_each_report_once(self):
        """refresh() fetches every held type through one Game per game, not one per type (pf-04, mA-03)."""
        requested: list[str] = []
        reports = ["gamecenter/2023020001/play-by-play", "RO020001", "TH020001", "TV020001"]
        with patch.object(requests.Session, "get", self.served_as("LIVE", requested)):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.api_events, scraper.shifts
            requested.clear()
            scraper.refresh()

        assert {report: sum(report in url for url in requested) for report in reports} == dict.fromkeys(reports, 1)

    def test_a_scrape_stores_the_types_its_game_built(self):
        """An html_events scrape builds the rosters too, so reading them later makes no request (pf-07)."""
        requested: list[str] = []
        with patch.object(requests.Session, "get", self.served_as("OFF", requested)):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            _ = scraper.html_events
            fetched = len(requested)
            rosters = scraper.rosters

        assert 2023020001 in scraper._html_rosters
        assert rosters.height > 0
        assert len(requested) == fetched

    def test_the_states_and_provisional_games_are_public(self):
        """game_states and provisional_games report what the Scraper fetches again, as copies (tu-03)."""
        with patch.object(requests.Session, "get", self.served_as("LIVE", [])):
            scraper = Scraper([2023020001], disable_progress_bar=True)
            unscraped = scraper.provisional_games
            _ = scraper.html_events

        states = scraper.game_states
        states[2023020001] = "OFF"

        assert unscraped == []
        assert scraper.game_states == {2023020001: "LIVE"}
        assert scraper.provisional_games == [2023020001]

    def test_an_html_only_scrape_records_the_state(self):
        scraper = Scraper([2023020001], disable_progress_bar=True)
        _ = scraper.html_events

        assert scraper.game_states == {2023020001: "OFF"}
        assert scraper.provisional_games == []


def test_every_request_goes_through_the_session_passed_in():
    """A Scraper given a session sends each request through it, so its User-Agent and throttle apply (N110)."""
    from chickenstats.utilities import ChickenSession

    session = ChickenSession(user_agent="my-team/1.0")
    served_get = requests.Session.get
    sessions = []

    def recording_get(self, url, *args, **kwargs):
        sessions.append(self)
        return served_get(self, url, *args, **kwargs)

    with patch.object(requests.Session, "get", recording_get):
        _ = Scraper(2023020001, disable_progress_bar=True, requests_session=session).play_by_play

    assert sessions and all(used is session for used in sessions)


def test_a_pickled_scraper_scrapes_through_its_session():
    """A pickled Scraper's session keeps its throttle and adapter, so each request it sends works (in-06)."""
    import pickle

    from requests.adapters import HTTPAdapter

    from chickenstats.utilities import ChickenSession

    scraper = Scraper(
        2023020001, disable_progress_bar=True, requests_session=ChickenSession(max_requests_per_second=50)
    )
    unpickled = pickle.loads(pickle.dumps(scraper))
    served_get, plain = requests.Session.get, requests.Session()

    def serve(self, request, *args, **kwargs):
        return served_get(plain, request.url)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    # Requests go through ChickenSession.request and ChickenHTTPAdapter.send, and the saved responses are served last
    with patch.object(HTTPAdapter, "send", serve), patch.object(requests.Session, "get", get):
        play_by_play = unpickled.play_by_play

    assert unpickled.failed_games == []
    assert play_by_play.height == 781
