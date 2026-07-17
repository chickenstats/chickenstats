import polars as pl
import pytest

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl._agg_constants import build_group_list
from chickenstats.chicken_nhl._aggregation import _prep_oi_percent, _prep_p60, prep_oi
from chickenstats.chicken_nhl import Scraper

_skip_no_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")


# -----------------------------------------------------------------------------
# prep_oi
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def game_pbp():
    scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
    return scraper.play_by_play, scraper.play_by_play_ext


class TestPrepOi:
    """prep_oi combines "for" (event_on), "against" (opp_on), and zone-start (change_on)
    perspectives across 21 lineup-slot columns into one row per player. These tests cover
    the deferred-aggregation rewrite (concat-then-single-group_by per category instead of
    a redundant per-slot group_by) added to reduce ~24 full-frame group_by calls to ~6.
    """

    @pytest.mark.parametrize(
        "level,strength_state,score,teammates,opposition",
        [
            ("game", True, False, False, False),
            ("period", True, True, False, False),
            ("session", False, False, True, False),
            ("season", True, False, False, True),
        ],
    )
    def test_runs_without_error_and_has_expected_columns(
        self, game_pbp, level, strength_state, score, teammates, opposition
    ):
        pbp, pbp_ext = game_pbp
        result = prep_oi(
            pbp,
            pbp_ext,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )
        assert len(result) > 0
        for col in ("player", "eh_id", "team", "toi", "gf", "ga", "sf", "sa", "cf", "ca", "give", "take"):
            assert col in result.columns

    def test_toi_and_counts_are_non_negative(self, game_pbp):
        pbp, pbp_ext = game_pbp
        result = prep_oi(pbp, pbp_ext, level="game")
        for col in ("toi", "gf", "ga", "sf", "sa", "cf", "ca", "give", "take"):
            assert (result[col] >= 0).all()


# -----------------------------------------------------------------------------
# _prep_p60
# -----------------------------------------------------------------------------


class TestPrepP60:
    def test_polars_adds_p60_column(self):
        df = pl.DataFrame({"toi": [60.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal"])
        assert "goal_p60" in result.columns

    def test_polars_p60_value(self):
        df = pl.DataFrame({"toi": [60.0], "goal": [2.0]})
        result = _prep_p60(df, stats=["goal"])
        assert result["goal_p60"][0] == pytest.approx(2.0)  # (2/60)*60 = 2

    @_skip_no_pandas
    def test_pandas_adds_p60_column(self):
        df = pd.DataFrame({"toi": [60.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal"])
        assert "goal_p60" in result.columns

    @_skip_no_pandas
    def test_pandas_p60_value(self):
        df = pd.DataFrame({"toi": [30.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal"])
        assert result["goal_p60"].iloc[0] == pytest.approx(2.0)  # (1/30)*60 = 2

    def test_missing_stat_column_skipped(self):
        """Stats not present in the DataFrame should be silently skipped."""
        df = pl.DataFrame({"toi": [60.0]})
        result = _prep_p60(df, stats=["goal"])
        assert "goal_p60" not in result.columns

    def test_multiple_stats(self):
        df = pl.DataFrame({"toi": [60.0], "goal": [1.0], "shot": [5.0]})
        result = _prep_p60(df, stats=["goal", "shot"])
        assert "goal_p60" in result.columns
        assert "shot_p60" in result.columns

    def test_partial_stats_present(self):
        """Only stats that exist in the DataFrame get a _p60 column."""
        df = pl.DataFrame({"toi": [60.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal", "shot"])
        assert "goal_p60" in result.columns
        assert "shot_p60" not in result.columns


# -----------------------------------------------------------------------------
# _prep_oi_percent
# -----------------------------------------------------------------------------


class TestPrepOiPercent:
    def test_polars_computes_percent(self):
        df = pl.DataFrame({"xgf": [2.0], "xga": [2.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"][0] == pytest.approx(0.5)

    @_skip_no_pandas
    def test_pandas_computes_percent(self):
        df = pd.DataFrame({"xgf": [3.0], "xga": [1.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"].iloc[0] == pytest.approx(0.75)

    def test_missing_stat_for_fills_zero(self):
        """When stat_for is absent from the DataFrame the percent column is 0.0."""
        df = pl.DataFrame({"xga": [2.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"][0] == pytest.approx(0.0)

    def test_missing_stat_against_fills_one(self):
        """When stat_against is absent the percent column is 1.0."""
        df = pl.DataFrame({"xgf": [2.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"][0] == pytest.approx(1.0)

    def test_multiple_stats(self):
        df = pl.DataFrame({"xgf": [1.0], "xga": [1.0], "cf": [3.0], "ca": [1.0]})
        result = _prep_oi_percent(df, stats_for=["xgf", "cf"], stats_against=["xga", "ca"])
        assert "xgf_percent" in result.columns
        assert "cf_percent" in result.columns
        assert result["cf_percent"][0] == pytest.approx(0.75)

    def test_zero_for_zero_fills_zero_not_nan(self):
        """When both stat_for and stat_against are present but zero, the percent is 0.0, not NaN.

        Regression test: 0/0 previously produced NaN, which is the common case for shifts
        with no goals/shots either way and silently passed schema validation since NaN != null.
        """
        df = pl.DataFrame({"xgf": [0.0], "xga": [0.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"][0] == pytest.approx(0.0)
        assert not result["xgf_percent"].is_nan()[0]

    @_skip_no_pandas
    def test_zero_for_zero_fills_zero_not_nan_pandas(self):
        df = pd.DataFrame({"xgf": [0.0], "xga": [0.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert result["xgf_percent"].iloc[0] == pytest.approx(0.0)
        assert not pd.isna(result["xgf_percent"].iloc[0])


# -----------------------------------------------------------------------------
# build_group_list
# -----------------------------------------------------------------------------


class TestBuildGroupList:
    def test_returns_list(self):
        result = build_group_list(["season", "game_id"])
        assert isinstance(result, list)

    def test_deduplicates(self):
        """Columns added more than once appear only once in the output."""
        result = build_group_list(["season", "season", "game_id"])
        assert result.count("season") == 1

    def test_canonical_order(self):
        """Columns present in _CANONICAL_ORDER are sorted into canonical order."""
        result = build_group_list(["game_id", "season"])
        assert result.index("season") < result.index("game_id")

    def test_level_game_adds_columns(self):
        result = build_group_list(["season"], level="game")
        assert "game_id" in result
        assert "opp_team" in result

    def test_level_period_adds_period(self):
        result = build_group_list(["season"], level="period")
        assert "period" in result

    def test_strength_state(self):
        result = build_group_list(["season"], strength_state=True)
        assert "strength_state" in result

    def test_opp_strength_state(self):
        result = build_group_list(["season"], opp_strength_state=True)
        assert "opp_strength_state" in result

    def test_filter_to_drops_absent_columns(self):
        df = pl.DataFrame({"season": [1], "game_id": [1]})
        result = [c for c in build_group_list(["season", "game_id", "opp_team"]) if c in df.columns]
        assert "season" in result
        assert "game_id" in result
        assert "opp_team" not in result

    def test_filter_to_only_returns_present_columns(self):
        df = pl.DataFrame({"season": [1]})
        result = [c for c in build_group_list(["season", "game_id"]) if c in df.columns]
        assert all(c in df.columns for c in result)
