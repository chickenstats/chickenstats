import importlib
import os
import sys
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl import Scraper
from chickenstats.chicken_nhl.viz import (
    plot_density_heatmap,
    plot_line_network,
    plot_rolling_stats,
    plot_shot_chart,
    plot_stat_comparison,
)
from chickenstats.exceptions import InvalidInputError

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "mock_data")


def mock_session_get(self, url, *args, **kwargs):
    """Custom mock for requests Session.get / ChickenSession.get."""
    response = requests.Response()
    response.url = url

    if "api-web.nhle.com/v1/gamecenter/2023020001/play-by-play" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "play_by_play.json"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/RO020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "rosters.html"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/TH020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "shifts_home.html"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/TV020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "shifts_away.html"), "rb") as f:
            response._content = f.read()
        return response

    elif "scores/htmlreports/20232024/PL020001.HTM" in url:
        response.status_code = 200
        with open(os.path.join(MOCK_DATA_DIR, "events.html"), "rb") as f:
            response._content = f.read()
        return response

    response.status_code = 404
    return response


@pytest.fixture(autouse=True)
def mock_requests():
    """Fixture to intercept all HTTP GET requests made via requests.Session."""
    with patch("requests.Session.get", mock_session_get):
        yield


@pytest.fixture(scope="module")
def real_pbp():
    scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
    return scraper.play_by_play


@pytest.fixture(scope="module")
def real_teammate_stats():
    scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
    scraper.prep_stats(teammates=True, disable_progress_bar=True)
    return scraper.stats


def _make_pbp(with_pred_goal: bool = False) -> pl.DataFrame:
    data = {
        "event": ["SHOT", "MISS", "GOAL", "SHOT", "GOAL"],
        "event_team": ["NSH", "NSH", "NSH", "TBL", "NSH"],
        "player_1": ["A", "B", "C", "D", "A"],
        "strength_state": ["5v5", "5v5", "5v5", "5v5", "5v4"],
        "coords_x": [70.0, 60.0, 80.0, -70.0, 75.0],
        "coords_y": [10.0, -5.0, 0.0, 5.0, -10.0],
    }
    if with_pred_goal:
        data["pred_goal"] = [0.05, 0.03, 0.4, 0.02, 0.35]
    return pl.DataFrame(data)


def _make_line_stats() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "player": ["A", "B", "C"],
            "team": ["NSH", "NSH", "NSH"],
            "strength_state": ["5v5", "5v5", "5v5"],
            "toi": [20.0, 18.0, 15.0],
            "position": ["C", "L", "R"],
            "forwards": ["A, B, C", "A, B, C", "A, B, C"],
            "defense": ["", "", ""],
        }
    )


def _make_rolling_stats() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "team": ["NSH", "NSH", "NSH", "TBL", "TBL", "TBL"],
            "game_id": [1, 2, 3, 1, 2, 3],
            "rolling_cf_p60": [50.0, 55.0, 60.0, 40.0, 42.0, 44.0],
        }
    )


def _make_comparison_stats() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "team": ["NSH", "NSH", "TBL", "TBL", "BOS"],
            "cf_p60": [55.0, 60.0, 45.0, 48.0, 50.0],
            "ff_p60": [40.0, 44.0, 30.0, 33.0, 35.0],
            "toi": [20.0, 18.0, 15.0, 22.0, 19.0],
        }
    )


class TestPlotShotChart:
    def test_returns_axes(self):
        ax = plot_shot_chart(_make_pbp(), team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_works_without_pred_goal(self):
        ax = plot_shot_chart(_make_pbp(with_pred_goal=False), team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_works_with_pred_goal(self):
        ax = plot_shot_chart(_make_pbp(with_pred_goal=True), team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_player_filter(self):
        ax = plot_shot_chart(_make_pbp(), team="NSH", player="A")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_strengths_filter(self):
        ax = plot_shot_chart(_make_pbp(), team="NSH", strengths=["5v4"])
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_raises_on_empty_filter(self):
        with pytest.raises(InvalidInputError):
            plot_shot_chart(_make_pbp(), team="NSH", player="NOT A REAL PLAYER")

    def test_raises_on_team_with_no_shots(self):
        with pytest.raises(InvalidInputError):
            plot_shot_chart(_make_pbp(), team="BOS")

    def test_save_path_writes_file(self, tmp_path):
        save_path = tmp_path / "shot_chart.png"
        plot_shot_chart(_make_pbp(), team="NSH", save_path=save_path)
        assert save_path.exists()

    def test_existing_ax_reused(self):
        fig, ax = plt.subplots()
        result = plot_shot_chart(_make_pbp(), team="NSH", ax=ax)
        assert result is ax
        plt.close(fig)

    def test_real_scraped_data(self, real_pbp):
        ax = plot_shot_chart(real_pbp, team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]


class TestPlotDensityHeatmap:
    def test_returns_axes(self):
        ax = plot_density_heatmap(_make_pbp(), team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_auto_weights_by_pred_goal_when_present(self):
        ax = plot_density_heatmap(_make_pbp(with_pred_goal=True), team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_explicit_weight_col(self):
        pbp = _make_pbp().with_columns(pl.Series("custom_weight", [1.0, 2.0, 3.0, 4.0, 5.0]))
        ax = plot_density_heatmap(pbp, team="NSH", weight_col="custom_weight")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_raises_on_empty_filter(self):
        with pytest.raises(InvalidInputError):
            plot_density_heatmap(_make_pbp(), team="NSH", player="NOT A REAL PLAYER")

    def test_save_path_writes_file(self, tmp_path):
        save_path = tmp_path / "density.png"
        plot_density_heatmap(_make_pbp(), team="NSH", save_path=save_path)
        assert save_path.exists()

    def test_real_scraped_data(self, real_pbp):
        ax = plot_density_heatmap(real_pbp, team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]


class TestPlotLineNetwork:
    def test_returns_figure(self):
        fig = plot_line_network(_make_line_stats(), team="NSH", toi_min=5.0)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_raises_on_no_matching_players(self):
        with pytest.raises(InvalidInputError):
            plot_line_network(_make_line_stats(), team="NSH", toi_min=1000.0)

    def test_raises_on_unknown_team(self):
        with pytest.raises(InvalidInputError):
            plot_line_network(_make_line_stats(), team="BOS", toi_min=5.0)

    def test_save_path_writes_file(self, tmp_path):
        save_path = tmp_path / "network.png"
        plot_line_network(_make_line_stats(), team="NSH", toi_min=5.0, save_path=save_path)
        assert save_path.exists()

    def test_real_scraped_data(self, real_teammate_stats):
        fig = plot_line_network(real_teammate_stats, team="NSH", toi_min=1.0)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestPlotRollingStats:
    def test_returns_axes(self):
        ax = plot_rolling_stats(_make_rolling_stats(), stat="cf_p60")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_team_filter(self):
        ax = plot_rolling_stats(_make_rolling_stats(), stat="cf_p60", team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_raises_on_missing_rolling_column(self):
        with pytest.raises(InvalidInputError):
            plot_rolling_stats(_make_rolling_stats(), stat="xgf_p60")

    def test_raises_on_no_rows_after_filter(self):
        with pytest.raises(InvalidInputError):
            plot_rolling_stats(_make_rolling_stats(), stat="cf_p60", team="NOT A TEAM")

    def test_save_path_writes_file(self, tmp_path):
        save_path = tmp_path / "rolling.png"
        plot_rolling_stats(_make_rolling_stats(), stat="cf_p60", team="NSH", save_path=save_path)
        assert save_path.exists()


class TestPlotStatComparison:
    def test_returns_axes(self):
        ax = plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_highlight_team(self):
        ax = plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", highlight_team="NSH")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_no_size_column(self):
        ax = plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", size=None)
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_save_path_writes_file(self, tmp_path):
        save_path = tmp_path / "comparison.png"
        plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", save_path=save_path)
        assert save_path.exists()


class TestGuardedImport:
    def test_missing_plotting_extra_raises_clear_error(self, monkeypatch):
        """Simulates seaborn being unavailable — reloading viz/__init__.py should
        raise an ImportError naming the 'plotting' extra install fix, not a bare
        ModuleNotFoundError."""
        import chickenstats.chicken_nhl.viz as viz_module

        monkeypatch.setitem(sys.modules, "seaborn", None)
        with pytest.raises(ImportError, match="plotting"):
            importlib.reload(viz_module)

        monkeypatch.undo()
        importlib.reload(viz_module)
