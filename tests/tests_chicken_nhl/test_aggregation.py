import polars as pl
import pytest

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl._agg_constants import build_group_list
from chickenstats.chicken_nhl._aggregation import _prep_oi_percent, _prep_p60, prep_oi, prep_rolling_stats
from chickenstats.chicken_nhl import Scraper
from chickenstats.exceptions import InvalidInputError

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
# prep_rolling_stats
# -----------------------------------------------------------------------------


class TestPrepRollingStats:
    def test_defaults_to_p60_and_percent_columns(self):
        df = pl.DataFrame(
            {
                "player": ["A", "A", "A"],
                "eh_id": ["A.A", "A.A", "A.A"],
                "game_id": [1, 2, 3],
                "cf_p60": [10.0, 20.0, 30.0],
                "cf_percent": [0.4, 0.5, 0.6],
                "toi": [15.0, 16.0, 17.0],
            }
        )
        result = prep_rolling_stats(df, window=2)
        assert "rolling_cf_p60" in result.columns
        assert "rolling_cf_percent" in result.columns
        assert "rolling_toi" not in result.columns

    def test_explicit_stats_list(self):
        df = pl.DataFrame({"team": ["NSH", "NSH", "NSH"], "game_id": [1, 2, 3], "toi": [60.0, 61.0, 59.0]})
        result = prep_rolling_stats(df, window=2, stats=["toi"], group_cols=["team"])
        assert "rolling_toi" in result.columns

    def test_rolling_mean_value(self):
        """A trailing 2-game window's mean matches a manual computation, sorted by game_id."""
        df = pl.DataFrame({"team": ["NSH", "NSH", "NSH"], "game_id": [3, 1, 2], "cf_p60": [30.0, 10.0, 20.0]})
        result = prep_rolling_stats(df, window=2, stats=["cf_p60"], group_cols=["team"], min_periods=1)
        result = result.sort("game_id")
        assert result["rolling_cf_p60"].to_list() == pytest.approx([10.0, 15.0, 25.0])

    def test_groups_are_independent(self):
        """Rolling windows don't leak across different group_cols entities."""
        df = pl.DataFrame(
            {"team": ["NSH", "NSH", "TBL", "TBL"], "game_id": [1, 2, 1, 2], "cf_p60": [10.0, 20.0, 100.0, 200.0]}
        )
        result = prep_rolling_stats(df, window=2, stats=["cf_p60"], group_cols=["team"])
        result = result.sort(["team", "game_id"])
        assert result.filter(pl.col("team") == "NSH")["rolling_cf_p60"].to_list() == pytest.approx([10.0, 15.0])
        assert result.filter(pl.col("team") == "TBL")["rolling_cf_p60"].to_list() == pytest.approx([100.0, 150.0])

    def test_min_periods_respected(self):
        """With min_periods above the available history, early rows are null."""
        df = pl.DataFrame({"team": ["NSH", "NSH", "NSH"], "game_id": [1, 2, 3], "cf_p60": [10.0, 20.0, 30.0]})
        result = prep_rolling_stats(df, window=3, stats=["cf_p60"], group_cols=["team"], min_periods=3)
        result = result.sort("game_id")
        assert result["rolling_cf_p60"][0] is None
        assert result["rolling_cf_p60"][1] is None
        assert result["rolling_cf_p60"][2] == pytest.approx(20.0)

    def test_missing_stat_column_skipped(self):
        df = pl.DataFrame({"team": ["NSH"], "game_id": [1], "cf_p60": [10.0]})
        result = prep_rolling_stats(df, stats=["cf_p60", "xgf_p60"], group_cols=["team"])
        assert "rolling_cf_p60" in result.columns
        assert "rolling_xgf_p60" not in result.columns

    def test_no_matching_stats_returns_unchanged(self):
        df = pl.DataFrame({"team": ["NSH"], "game_id": [1], "toi": [60.0]})
        result = prep_rolling_stats(df, stats=["xgf_p60"], group_cols=["team"])
        assert result.columns == df.columns

    def test_defaults_to_player_eh_id_grouping_when_present(self):
        df = pl.DataFrame({"player": ["A", "B"], "eh_id": ["A.A", "B.B"], "game_id": [1, 1], "cf_p60": [10.0, 20.0]})
        result = prep_rolling_stats(df, stats=["cf_p60"])
        assert result["rolling_cf_p60"].to_list() == pytest.approx([10.0, 20.0])

    def test_raises_without_game_id_or_game_date(self):
        """level='session'/'season' output has no per-game granularity to roll over."""
        df = pl.DataFrame({"team": ["NSH"], "cf_p60": [10.0]})
        with pytest.raises(InvalidInputError):
            prep_rolling_stats(df, group_cols=["team"])

    def test_raises_with_duplicate_period_rows(self):
        """level='period' output has multiple rows per game, not meaningful to roll."""
        df = pl.DataFrame({"team": ["NSH", "NSH"], "game_id": [1, 1], "period": [1, 2], "cf_p60": [10.0, 5.0]})
        with pytest.raises(InvalidInputError):
            prep_rolling_stats(df, group_cols=["team"])

    def test_raises_with_unfiltered_strength_state_splits(self):
        """Default prep_stats(level='game') output splits by strength_state, producing
        multiple rows per game per player — must raise rather than silently mix them."""
        df = pl.DataFrame(
            {
                "player": ["A", "A"],
                "eh_id": ["A.A", "A.A"],
                "game_id": [1, 1],
                "strength_state": ["5v5", "5v4"],
                "cf_p60": [10.0, 20.0],
            }
        )
        with pytest.raises(InvalidInputError):
            prep_rolling_stats(df)


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
