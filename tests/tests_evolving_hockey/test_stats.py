from pathlib import Path

import narwhals as nw
import polars as pl
import pytest

pd = pytest.importorskip("pandas", reason="pandas not installed")
pa = pytest.importorskip("pyarrow", reason="pyarrow not installed")

from chickenstats.evolving_hockey import (  # noqa: E402
    prep_gar,
    prep_ind,
    prep_lines,
    prep_oi,
    prep_pbp,
    prep_stats,
    prep_team_stats,
    prep_xgar,
)
from chickenstats.exceptions import DataMismatchError, UnsupportedBackendError  # noqa: E402

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="package")
def raw_pbp_polars():
    filepath = Path("./tests/tests_evolving_hockey/data/raw/raw_pbp.csv")
    return pl.read_csv(filepath, infer_schema_length=10000)


@pytest.fixture(scope="package")
def raw_shifts_polars():
    filepath = Path("./tests/tests_evolving_hockey/data/raw/raw_shifts.csv")
    return pl.read_csv(filepath, infer_schema_length=10000)


@pytest.fixture(scope="package")
def pbp_polars(raw_pbp_polars, raw_shifts_polars):
    return prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, disable_progress_bar=True)


@pytest.fixture(scope="package")
def pbp_lazy(pbp_polars):
    return pbp_polars.lazy()


@pytest.fixture(scope="package")
def pbp_pandas(pbp_polars):
    return pbp_polars.to_pandas()


@pytest.fixture(scope="package")
def raw_gar_skater_polars():
    filepath = Path("./tests/tests_evolving_hockey/data/raw/raw_gar_skater.csv")
    return pl.read_csv(filepath, infer_schema_length=10000)


@pytest.fixture(scope="package")
def raw_gar_goalie_polars():
    filepath = Path("./tests/tests_evolving_hockey/data/raw/raw_gar_goalie.csv")
    return pl.read_csv(filepath, infer_schema_length=10000)


@pytest.fixture(scope="package")
def raw_xgar_polars():
    filepath = Path("./tests/tests_evolving_hockey/data/raw/raw_xgar_skater.csv")
    return pl.read_csv(filepath, infer_schema_length=10000)


@pytest.fixture(scope="package")
def raw_gar_skater_pandas(raw_gar_skater_polars):
    return raw_gar_skater_polars.to_pandas()


@pytest.fixture(scope="package")
def raw_gar_goalie_pandas(raw_gar_goalie_polars):
    return raw_gar_goalie_polars.to_pandas()


@pytest.fixture(scope="package")
def raw_xgar_pandas(raw_xgar_polars):
    return raw_xgar_polars.to_pandas()


@pytest.fixture(scope="package")
def pbp_pyarrow(raw_pbp_polars, raw_shifts_polars):
    return prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, backend="pyarrow", disable_progress_bar=True)


@pytest.fixture(scope="package")
def raw_gar_skater_pyarrow(raw_gar_skater_polars):
    return raw_gar_skater_polars.to_arrow()


@pytest.fixture(scope="package")
def raw_gar_goalie_pyarrow(raw_gar_goalie_polars):
    return raw_gar_goalie_polars.to_arrow()


@pytest.fixture(scope="package")
def raw_xgar_pyarrow(raw_xgar_polars):
    return raw_xgar_polars.to_arrow()


# -----------------------------------------------------------------------------
# TestPrepPbp
# -----------------------------------------------------------------------------


class TestPrepPbp:
    def test_returns_polars(self, pbp_polars):
        assert isinstance(pbp_polars, pl.DataFrame)

    def test_non_empty(self, pbp_polars):
        assert len(pbp_polars) > 0

    def test_columns_full(self, pbp_polars):
        for col in ("game_id", "event_type", "strength_state", "pred_goal"):
            assert col in pbp_polars.columns

    def test_columns_light_fewer_than_full(self, raw_pbp_polars, raw_shifts_polars):
        full = prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, columns="full", disable_progress_bar=True)
        light = prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, columns="light", disable_progress_bar=True)
        assert len(light.columns) < len(full.columns)

    def test_columns_all_more_than_full(self, raw_pbp_polars, raw_shifts_polars):
        full = prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, columns="full", disable_progress_bar=True)
        all_ = prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, columns="all", disable_progress_bar=True)
        assert len(all_.columns) >= len(full.columns)

    def test_list_input(self, raw_pbp_polars, raw_shifts_polars):
        single_rows = len(prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, disable_progress_bar=True))
        result = prep_pbp(
            pbp=[raw_pbp_polars, raw_pbp_polars],
            shifts=[raw_shifts_polars, raw_shifts_polars],
            disable_progress_bar=True,
        )
        assert isinstance(result, pl.DataFrame)
        assert len(result) >= single_rows * 2

    def test_list_mismatch_raises(self, raw_pbp_polars, raw_shifts_polars):
        with pytest.raises(DataMismatchError):
            prep_pbp(pbp=[raw_pbp_polars, raw_pbp_polars], shifts=[raw_shifts_polars], disable_progress_bar=True)

    def test_backend_pandas(self, raw_pbp_polars, raw_shifts_polars):
        result = prep_pbp(pbp=raw_pbp_polars, shifts=raw_shifts_polars, backend="pandas", disable_progress_bar=True)
        assert isinstance(result, pd.DataFrame)

    def test_backend_pyarrow(self, pbp_pyarrow):
        assert isinstance(pbp_pyarrow, pa.Table)

    def test_pandas_input_returns_pandas(self, raw_pbp_polars, raw_shifts_polars):
        """Backend detection: pandas input -> pandas output."""
        pandas_pbp = raw_pbp_polars.to_pandas()
        pandas_shifts = raw_shifts_polars.to_pandas()
        result = prep_pbp(pbp=pandas_pbp, shifts=pandas_shifts, disable_progress_bar=True)
        assert isinstance(result, pd.DataFrame)

    def test_lazyframe_input(self, raw_pbp_polars, raw_shifts_polars):
        result = prep_pbp(pbp=raw_pbp_polars.lazy(), shifts=raw_shifts_polars.lazy(), disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)
        assert len(result) > 0


# -----------------------------------------------------------------------------
# TestPrepInd
# -----------------------------------------------------------------------------


class TestPrepInd:
    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_polars_returns_polars(self, pbp_polars, level):
        result = prep_ind(pbp_polars, level=level)
        assert isinstance(result, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_pandas_returns_pandas(self, pbp_pandas, level):
        result = prep_ind(pbp_pandas, level=level)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_non_empty(self, pbp_polars, level):
        result = prep_ind(pbp_polars, level=level)
        assert len(result) > 0

    def test_key_columns_present(self, pbp_polars):
        result = prep_ind(pbp_polars)
        for col in ("player", "eh_id", "team", "g", "isf"):
            assert col in result.columns

    def test_score_split(self, pbp_polars):
        result = prep_ind(pbp_polars, score=True)
        assert "score_state" in result.columns

    def test_teammates_split(self, pbp_polars):
        result = prep_ind(pbp_polars, teammates=True)
        assert "forwards" in result.columns

    def test_opposition_split(self, pbp_polars):
        result = prep_ind(pbp_polars, opposition=True)
        assert "opp_forwards" in result.columns

    def test_backend_pyarrow(self, pbp_polars):
        result = prep_ind(pbp_polars, backend="pyarrow")
        assert isinstance(result, pa.Table)

    def test_unknown_backend_raises(self, pbp_polars):
        """An unrecognized backend string must raise, not silently return polars."""
        with pytest.raises(UnsupportedBackendError):
            prep_ind(pbp_polars, backend="unknown")

    def test_explicit_backend_overrides_input(self, pbp_pandas):
        """Explicit backend param overrides input-type detection."""
        result = prep_ind(pbp_pandas, backend="polars")
        assert isinstance(result, pl.DataFrame)

    def test_season_level_no_game_id(self, pbp_polars):
        result = prep_ind(pbp_polars, level="season")
        assert "game_id" not in result.columns
        assert "game_date" not in result.columns

    def test_game_level_has_game_id(self, pbp_polars):
        result = prep_ind(pbp_polars, level="game")
        assert "game_id" in result.columns

    def test_lazyframe_input(self, pbp_lazy):
        result = prep_ind(pbp_lazy)
        assert isinstance(result, pl.DataFrame)
        assert len(result) > 0

    def test_all_splits_combined(self, pbp_polars):
        result = prep_ind(pbp_polars, score=True, teammates=True, opposition=True)
        for col in ("score_state", "forwards", "opp_forwards"):
            assert col in result.columns


# -----------------------------------------------------------------------------
# TestPrepOi
# -----------------------------------------------------------------------------


class TestPrepOi:
    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_polars_returns_polars(self, pbp_polars, level):
        result = prep_oi(pbp_polars, level=level)
        assert isinstance(result, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_pandas_returns_pandas(self, pbp_pandas, level):
        result = prep_oi(pbp_pandas, level=level)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_non_empty(self, pbp_polars, level):
        result = prep_oi(pbp_polars, level=level)
        assert len(result) > 0

    def test_key_columns_present(self, pbp_polars):
        result = prep_oi(pbp_polars)
        for col in ("player", "eh_id", "team", "toi", "gf", "ga", "xgf", "xga", "cf", "ca"):
            assert col in result.columns

    def test_score_split(self, pbp_polars):
        result = prep_oi(pbp_polars, score=True)
        assert "score_state" in result.columns

    def test_teammates_split(self, pbp_polars):
        result = prep_oi(pbp_polars, teammates=True)
        assert "forwards" in result.columns

    def test_opposition_split(self, pbp_polars):
        result = prep_oi(pbp_polars, opposition=True)
        assert "opp_forwards" in result.columns

    def test_backend_pyarrow(self, pbp_polars):
        result = prep_oi(pbp_polars, backend="pyarrow")
        assert isinstance(result, pa.Table)

    def test_explicit_backend_overrides_input(self, pbp_pandas):
        result = prep_oi(pbp_pandas, backend="polars")
        assert isinstance(result, pl.DataFrame)

    def test_season_level_no_game_id(self, pbp_polars):
        result = prep_oi(pbp_polars, level="season")
        assert "game_id" not in result.columns

    def test_game_level_has_game_id(self, pbp_polars):
        result = prep_oi(pbp_polars, level="game")
        assert "game_id" in result.columns

    def test_lazyframe_input(self, pbp_lazy):
        result = prep_oi(pbp_lazy)
        assert isinstance(result, pl.DataFrame)
        assert len(result) > 0

    def test_all_splits_combined(self, pbp_polars):
        result = prep_oi(pbp_polars, score=True, teammates=True, opposition=True)
        for col in ("score_state", "forwards", "opp_forwards"):
            assert col in result.columns


# -----------------------------------------------------------------------------
# TestPrepStats
# -----------------------------------------------------------------------------


class TestPrepStats:
    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_polars_returns_polars(self, pbp_polars, level):
        result = prep_stats(pbp_polars, level=level, disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_pandas_returns_pandas(self, pbp_pandas, level):
        result = prep_stats(pbp_pandas, level=level, disable_progress_bar=True)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_non_empty(self, pbp_polars, level):
        result = prep_stats(pbp_polars, level=level, disable_progress_bar=True)
        assert len(result) > 0

    def test_ind_and_oi_columns_present(self, pbp_polars):
        result = prep_stats(pbp_polars, disable_progress_bar=True)
        for col in ("player", "eh_id", "team", "toi", "g", "isf", "gf", "ga", "xgf", "xga", "cf", "ca", "g_p60"):
            assert col in result.columns

    def test_score_split(self, pbp_polars):
        result = prep_stats(pbp_polars, score=True, disable_progress_bar=True)
        assert "score_state" in result.columns

    def test_teammates_split(self, pbp_polars):
        result = prep_stats(pbp_polars, teammates=True, disable_progress_bar=True)
        assert "forwards" in result.columns

    def test_opposition_split(self, pbp_polars):
        result = prep_stats(pbp_polars, opposition=True, disable_progress_bar=True)
        assert "opp_forwards" in result.columns

    def test_backend_pyarrow(self, pbp_polars):
        result = prep_stats(pbp_polars, backend="pyarrow", disable_progress_bar=True)
        assert isinstance(result, pa.Table)

    def test_explicit_backend_overrides_input(self, pbp_pandas):
        result = prep_stats(pbp_pandas, backend="polars", disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)

    def test_season_level_no_game_id(self, pbp_polars):
        result = prep_stats(pbp_polars, level="season", disable_progress_bar=True)
        assert "game_id" not in result.columns

    def test_game_level_has_game_id(self, pbp_polars):
        result = prep_stats(pbp_polars, level="game", disable_progress_bar=True)
        assert "game_id" in result.columns

    def test_lazyframe_input(self, pbp_lazy):
        result = prep_stats(pbp_lazy, disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)
        assert len(result) > 0

    def test_all_splits_combined(self, pbp_polars):
        result = prep_stats(pbp_polars, score=True, teammates=True, opposition=True, disable_progress_bar=True)
        for col in ("score_state", "forwards", "opp_forwards"):
            assert col in result.columns

    def test_splits_at_season_level(self, pbp_polars):
        result = prep_stats(pbp_polars, level="season", score=True, disable_progress_bar=True)
        assert "score_state" in result.columns and len(result) > 0

    def test_splits_at_period_level(self, pbp_polars):
        result = prep_stats(pbp_polars, level="period", score=True, disable_progress_bar=True)
        assert "score_state" in result.columns and len(result) > 0


# -----------------------------------------------------------------------------
# TestPrepLines
# -----------------------------------------------------------------------------


class TestPrepLines:
    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    @pytest.mark.parametrize("position", ["f", "d"])
    def test_polars_returns_polars(self, pbp_polars, position, level):
        result = prep_lines(pbp_polars, position=position, level=level, disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    @pytest.mark.parametrize("position", ["f", "d"])
    def test_pandas_returns_pandas(self, pbp_pandas, position, level):
        result = prep_lines(pbp_pandas, position=position, level=level, disable_progress_bar=True)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    @pytest.mark.parametrize("position", ["f", "d"])
    def test_non_empty(self, pbp_polars, position, level):
        result = prep_lines(pbp_polars, position=position, level=level, disable_progress_bar=True)
        assert len(result) > 0

    def test_forwards_position_column(self, pbp_polars):
        result = prep_lines(pbp_polars, position="f", disable_progress_bar=True)
        assert "forwards" in result.columns

    def test_defense_position_column(self, pbp_polars):
        result = prep_lines(pbp_polars, position="d", disable_progress_bar=True)
        assert "defense" in result.columns

    def test_score_split(self, pbp_polars):
        result = prep_lines(pbp_polars, score=True, disable_progress_bar=True)
        assert "score_state" in result.columns

    def test_opposition_split(self, pbp_polars):
        result = prep_lines(pbp_polars, opposition=True, disable_progress_bar=True)
        assert "opp_forwards" in result.columns

    def test_backend_pyarrow(self, pbp_polars):
        result = prep_lines(pbp_polars, backend="pyarrow", disable_progress_bar=True)
        assert isinstance(result, pa.Table)

    def test_explicit_backend_overrides_input(self, pbp_pandas):
        result = prep_lines(pbp_pandas, backend="polars", disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)

    def test_season_level_no_game_id(self, pbp_polars):
        result = prep_lines(pbp_polars, level="season", disable_progress_bar=True)
        assert "game_id" not in result.columns

    def test_game_level_has_game_id(self, pbp_polars):
        result = prep_lines(pbp_polars, level="game", disable_progress_bar=True)
        assert "game_id" in result.columns

    def test_lazyframe_input(self, pbp_lazy):
        result = prep_lines(pbp_lazy, disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)
        assert len(result) > 0

    def test_all_splits_combined(self, pbp_polars):
        result = prep_lines(pbp_polars, score=True, opposition=True, disable_progress_bar=True)
        for col in ("score_state", "opp_forwards"):
            assert col in result.columns


# -----------------------------------------------------------------------------
# TestPrepTeamStats
# -----------------------------------------------------------------------------


class TestPrepTeamStats:
    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_polars_returns_polars(self, pbp_polars, level):
        result = prep_team_stats(pbp_polars, level=level, disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_pandas_returns_pandas(self, pbp_pandas, level):
        result = prep_team_stats(pbp_pandas, level=level, disable_progress_bar=True)
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.parametrize("level", ["game", "season", "session", "period"])
    def test_non_empty(self, pbp_polars, level):
        result = prep_team_stats(pbp_polars, level=level, disable_progress_bar=True)
        assert len(result) > 0

    def test_key_columns_present(self, pbp_polars):
        result = prep_team_stats(pbp_polars, disable_progress_bar=True)
        for col in ("team", "toi", "gf", "ga", "xgf", "xga", "cf", "ca"):
            assert col in result.columns

    @pytest.mark.parametrize("strengths", [True, False])
    def test_strengths_column(self, pbp_polars, strengths):
        result = prep_team_stats(pbp_polars, strengths=strengths, disable_progress_bar=True)
        if strengths:
            assert "strength_state" in result.columns
        else:
            assert "strength_state" not in result.columns

    def test_score_split(self, pbp_polars):
        result = prep_team_stats(pbp_polars, score=True, disable_progress_bar=True)
        assert "score_state" in result.columns

    def test_backend_pyarrow(self, pbp_polars):
        result = prep_team_stats(pbp_polars, backend="pyarrow", disable_progress_bar=True)
        assert isinstance(result, pa.Table)

    def test_explicit_backend_overrides_input(self, pbp_pandas):
        result = prep_team_stats(pbp_pandas, backend="polars", disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)

    def test_season_level_no_game_id(self, pbp_polars):
        result = prep_team_stats(pbp_polars, level="season", disable_progress_bar=True)
        assert "game_id" not in result.columns

    def test_game_level_has_game_id(self, pbp_polars):
        result = prep_team_stats(pbp_polars, level="game", disable_progress_bar=True)
        assert "game_id" in result.columns

    def test_lazyframe_input(self, pbp_lazy):
        result = prep_team_stats(pbp_lazy, disable_progress_bar=True)
        assert isinstance(result, pl.DataFrame)
        assert len(result) > 0


# -----------------------------------------------------------------------------
# TestPrepGar
# -----------------------------------------------------------------------------


class TestPrepGar:
    def test_polars_returns_polars(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        result = prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars)
        assert isinstance(result, pl.DataFrame)

    def test_pandas_returns_pandas(self, raw_gar_skater_pandas, raw_gar_goalie_pandas):
        result = prep_gar(raw_gar_skater_pandas, raw_gar_goalie_pandas)
        assert isinstance(result, pd.DataFrame)

    def test_non_empty(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        result = prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars)
        assert len(result) > 0

    def test_key_columns_present(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        result = prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars)
        for col in ("player", "eh_id", "team", "season"):
            assert col in result.columns

    def test_combines_skater_and_goalie_rows(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        result = prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars)
        assert len(result) >= len(raw_gar_skater_polars)

    def test_malformed_season_format_raises(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        """A season string that isn't EH's 'YY-YY' format must raise a clear error instead of
        silently producing a garbled or null season value.

        Regression test: "20" + season.split("-")[0] + "20" + season.split("-")[1] had no
        guard, so a 4-digit-dash-4-digit season (e.g. "2023-2024" instead of "23-24") would
        silently produce a garbled-but-non-null season like "2020232024" rather than erroring.
        """
        from chickenstats.exceptions import DataMismatchError

        bad_skater_data = raw_gar_skater_polars.with_columns(pl.lit("2023-2024").alias("Season"))
        with pytest.raises(DataMismatchError):
            prep_gar(bad_skater_data, raw_gar_goalie_polars)

    def test_gar_metric_columns_present(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        """Regression test: prep_gar previously had no schema validation at all, so this test
        would have passed either way — it now also confirms the newly-added schema doesn't
        accidentally drop the actual GAR metric columns that are the point of this output."""
        result = prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars)
        for col in ("gar", "war", "spar", "evo_gar", "evd_gar", "take_gar", "draw_gar"):
            assert col in result.columns

    def test_backend_pyarrow(self, raw_gar_skater_polars, raw_gar_goalie_polars):
        result = prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars, backend="pyarrow")
        assert isinstance(result, pa.Table)

    def test_explicit_backend_overrides_input(self, raw_gar_skater_pandas, raw_gar_goalie_pandas):
        result = prep_gar(raw_gar_skater_pandas, raw_gar_goalie_pandas, backend="polars")
        assert isinstance(result, pl.DataFrame)


# -----------------------------------------------------------------------------
# TestPrepXgar
# -----------------------------------------------------------------------------


class TestPrepXgar:
    def test_polars_returns_polars(self, raw_xgar_polars):
        result = prep_xgar(raw_xgar_polars)
        assert isinstance(result, pl.DataFrame)

    def test_pandas_returns_pandas(self, raw_xgar_pandas):
        result = prep_xgar(raw_xgar_pandas)
        assert isinstance(result, pd.DataFrame)

    def test_non_empty(self, raw_xgar_polars):
        result = prep_xgar(raw_xgar_polars)
        assert len(result) > 0

    def test_key_columns_present(self, raw_xgar_polars):
        result = prep_xgar(raw_xgar_polars)
        for col in ("player", "eh_id", "team", "season"):
            assert col in result.columns

    def test_malformed_season_format_raises(self, raw_xgar_polars):
        """A season string that isn't EH's 'YY-YY' format must raise a clear error instead of
        silently producing a garbled or null season value."""
        from chickenstats.exceptions import DataMismatchError

        bad_data = raw_xgar_polars.with_columns(pl.lit("2023-2024").alias("Season"))
        with pytest.raises(DataMismatchError):
            prep_xgar(bad_data)

    def test_xgar_metric_columns_present(self, raw_xgar_polars):
        """Regression test: prep_xgar previously had no schema validation at all. Confirms the
        newly-added schema doesn't accidentally drop the xGAR metric columns."""
        result = prep_xgar(raw_xgar_polars)
        for col in ("xgar", "xwar", "xspar", "xevo_gar", "xevd_gar", "take_gar", "draw_gar"):
            assert col in result.columns

    def test_backend_pyarrow(self, raw_xgar_polars):
        result = prep_xgar(raw_xgar_polars, backend="pyarrow")
        assert isinstance(result, pa.Table)

    def test_explicit_backend_overrides_input(self, raw_xgar_pandas):
        result = prep_xgar(raw_xgar_pandas, backend="polars")
        assert isinstance(result, pl.DataFrame)
