import importlib
import sys
from unittest.mock import patch

import polars as pl
import pytest

pytest.importorskip("matplotlib", reason="requires the 'plotting' extra")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

pytest.importorskip("seaborn", reason="requires the 'plotting' extra")
pytest.importorskip("hockey_rink", reason="requires the 'plotting' extra")
pytest.importorskip("networkx", reason="requires the 'plotting' extra")

from chickenstats.chicken_nhl import Scraper
from chickenstats.chicken_nhl.viz._network import _create_network_graph
from chickenstats.chicken_nhl.viz._rink import _filter_shots
from chickenstats.chicken_nhl.viz import (
    plot_density_heatmap,
    plot_line_network,
    plot_rolling_stats,
    plot_shot_chart,
    plot_stat_comparison,
)
from chickenstats.exceptions import InvalidInputError


def plotted_points(ax) -> list[int]:
    """Return the number of points in each scatter drawn on the axes."""
    return [len(collection.get_offsets()) for collection in ax.collections if len(collection.get_offsets())]


def marker_sizes(ax) -> list[list[float]]:
    """Return the marker sizes of each scatter drawn on the axes; one value when they are all the same."""
    return [collection.get_sizes().tolist() for collection in ax.collections if len(collection.get_offsets())]


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
        assert sum(plotted_points(ax)) == 4
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
        assert sum(plotted_points(ax)) == 2
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_strengths_filter(self):
        ax = plot_shot_chart(_make_pbp(), team="NSH", strengths=["5v4"])
        assert sum(plotted_points(ax)) == 1
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

    def test_markers_are_sized_by_pred_goal(self):
        """Each marker's area is its shot's pred_goal times 500: MISS, then SHOT, then GOAL."""
        ax = plot_shot_chart(_make_pbp(with_pred_goal=True), team="NSH")
        assert marker_sizes(ax) == [[15.0], [25.0], [200.0, 175.0]]
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_markers_are_one_size_without_pred_goal(self):
        ax = plot_shot_chart(_make_pbp(), team="NSH")
        assert marker_sizes(ax) == [[40.0], [40.0], [40.0]]
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]


def kde_weights(pbp: pl.DataFrame, **kwargs) -> list:
    """The weights each kdeplot layer of plot_density_heatmap receives, None for an unweighted layer."""
    import seaborn

    with patch.object(seaborn, "kdeplot", wraps=seaborn.kdeplot) as spy:
        plt.close(plot_density_heatmap(pbp, team="NSH", **kwargs).get_figure())  # ty: ignore[invalid-argument-type]
    return [None if call.kwargs["weights"] is None else list(call.kwargs["weights"]) for call in spy.call_args_list]


class TestPlotDensityHeatmap:
    def test_weights_by_pred_goal_when_present(self):
        assert kde_weights(_make_pbp(with_pred_goal=True)) == [[0.05, 0.03, 0.4, 0.35]] * 2

    def test_weights_by_an_explicit_column(self):
        pbp = _make_pbp().with_columns(pl.Series("custom_weight", [1.0, 2.0, 3.0, 4.0, 5.0]))
        assert kde_weights(pbp, weight_col="custom_weight") == [[1.0, 2.0, 3.0, 5.0]] * 2

    def test_unweighted_without_pred_goal(self):
        assert kde_weights(_make_pbp()) == [None, None]

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
    def test_returns_axes(self):
        ax = plot_line_network(_make_line_stats(), team="NSH", toi_min=5.0)
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

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

    def test_existing_ax_reused(self):
        fig, ax = plt.subplots()
        result = plot_line_network(_make_line_stats(), team="NSH", toi_min=5.0, ax=ax)
        assert result is ax
        plt.close(fig)

    def test_real_scraped_data(self, real_teammate_stats):
        ax = plot_line_network(real_teammate_stats, team="NSH", toi_min=1.0)
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_toi_min_applies_to_a_players_total_ice_time(self):
        """Each line combination is under 15 minutes, but A and B play 18 in all and C only 10 (R40)."""
        stats = pd.DataFrame(
            {
                "player": ["A", "B", "C", "A", "B"],
                "team": "NSH",
                "strength_state": "5v5",
                "toi": [10.0, 10.0, 10.0, 8.0, 8.0],
                "position": "C",
                "forwards": ["A, B, C", "A, B, C", "A, B, C", "A, B", "A, B"],
                "defense": "",
            }
        )

        graph = _create_network_graph(stats, "NSH", ["5v5"], toi_min=15.0, positions=["C"])

        assert sorted(graph.nodes) == ["A", "B"]

    def test_edge_weights_are_shared_ice_time(self):
        """A, B and C play 10 minutes together, and A, B and D 4, so A and B share 14 minutes.

        Each edge is the pair's shared ice time, scaled so the most shared pair is 75.
        """
        lines = {"A, B, C": ["A", "B", "C"], "A, B, D": ["A", "B", "D"]}
        toi = {"A, B, C": 10.0, "A, B, D": 4.0}
        rows = [(player, line, toi[line]) for line, players in lines.items() for player in players]
        stats = pd.DataFrame(
            {
                "player": [player for player, _, _ in rows],
                "team": "NSH",
                "strength_state": "5v5",
                "toi": [minutes for _, _, minutes in rows],
                "position": "C",
                "forwards": [line for _, line, _ in rows],
                "defense": "",
            }
        )

        graph = _create_network_graph(stats, "NSH", ["5v5"], toi_min=1.0, positions=["C"])
        weights = {tuple(sorted(edge)): round(w, 3) for *edge, w in graph.edges(data="weight") if edge[0] != edge[1]}

        assert weights == {
            ("A", "B"): 75.0,
            ("A", "C"): round(10 / 14 * 75, 3),
            ("B", "C"): round(10 / 14 * 75, 3),
            ("A", "D"): round(4 / 14 * 75, 3),
            ("B", "D"): round(4 / 14 * 75, 3),
            ("C", "D"): 0.0,
        }


class TestPlotRollingStats:
    def test_returns_axes(self):
        ax = plot_rolling_stats(_make_rolling_stats(), stat="cf_p60")
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_team_filter(self):
        ax = plot_rolling_stats(_make_rolling_stats(), stat="cf_p60", team="NSH")
        assert [np.asarray(line.get_ydata()).tolist() for line in ax.lines] == [[50.0, 55.0, 60.0]]
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_one_line_per_player_in_game_order_across_a_trade(self):
        """A traded player stays one line, ordered by date even when the rows are not."""
        rolling = pl.DataFrame(
            {
                "player": ["A", "B", "A", "B", "A"],
                "team": ["NSH", "NSH", "TBL", "NSH", "NSH"],
                "game_date": ["2024-01-05", "2024-01-01", "2024-01-09", "2024-01-05", "2024-01-01"],
                "game_id": [2, 1, 3, 2, 1],
                "rolling_cf_p60": [52.0, 40.0, 54.0, 41.0, 50.0],
            }
        )
        ax = plot_rolling_stats(rolling, stat="cf_p60")
        assert sorted(np.asarray(line.get_ydata()).tolist() for line in ax.lines) == [[40.0, 41.0], [50.0, 52.0, 54.0]]
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
        assert plotted_points(ax) == [5]
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_highlight_team(self):
        ax = plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", highlight_team="NSH")
        assert plotted_points(ax) == [3, 2]
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_no_size_column(self):
        ax = plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", size=None)
        assert isinstance(ax, plt.Axes)
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]

    def test_save_path_writes_file(self, tmp_path):
        save_path = tmp_path / "comparison.png"
        plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", save_path=save_path)
        assert save_path.exists()


CHARTS = {
    "plot_shot_chart": lambda **kw: plot_shot_chart(_make_pbp(), team="NSH", **kw),
    "plot_density_heatmap": lambda **kw: plot_density_heatmap(_make_pbp(), team="NSH", **kw),
    "plot_line_network": lambda **kw: plot_line_network(_make_line_stats(), team="NSH", toi_min=5.0, **kw),
    "plot_rolling_stats": lambda **kw: plot_rolling_stats(_make_rolling_stats(), stat="cf_p60", **kw),
    "plot_stat_comparison": lambda **kw: plot_stat_comparison(_make_comparison_stats(), x="cf_p60", y="ff_p60", **kw),
}


@pytest.mark.parametrize("chart", CHARTS)
class TestFigures:
    """Charts open at matplotlib's dpi, save at 650 dpi, and close a figure they made once it is saved (N141)."""

    def test_a_saved_chart_leaves_no_figure_open(self, chart, tmp_path):
        from PIL import Image

        plt.close("all")
        CHARTS[chart](save_path=tmp_path / "chart.png")

        assert plt.get_fignums() == []
        with Image.open(tmp_path / "chart.png") as image:
            assert image.info["dpi"] == pytest.approx((650, 650), abs=1)

    def test_a_figure_passed_in_stays_open(self, chart, tmp_path):
        fig, ax = plt.subplots()
        CHARTS[chart](ax=ax, save_path=tmp_path / "chart.png")

        assert plt.fignum_exists(fig.number)
        plt.close(fig)

    def test_an_unsaved_chart_uses_the_default_dpi(self, chart):
        ax = CHARTS[chart]()

        assert ax.get_figure().dpi == matplotlib.rcParams["figure.dpi"]  # ty: ignore[unresolved-attribute]
        plt.close(ax.get_figure())  # ty: ignore[invalid-argument-type]


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


# -----------------------------------------------------------------------------
# Shootouts
# -----------------------------------------------------------------------------


def test_charts_leave_out_shootout_attempts(long_shootout_game):
    """In 2023020411 Montreal scored 2 goals; its 4 shootout attempts are not drawn as shots or goals."""
    play_by_play = long_shootout_game.play_by_play
    shots = _filter_shots(play_by_play, "MTL", None, None)

    assert shots["shootout_attempt"].sum() == 0
    assert shots.filter(pl.col("event") == "GOAL").height == 2
    plot_shot_chart(play_by_play, team="MTL")
    plot_density_heatmap(play_by_play, team="MTL")
    plt.close("all")


@pytest.mark.parametrize(
    "call",
    [
        lambda: plot_shot_chart(pl.DataFrame(), "NSH"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: plot_density_heatmap(pl.DataFrame(), "NSH"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: plot_line_network(pl.DataFrame(), "NSH"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: plot_rolling_stats(pl.DataFrame(), "cf_p60"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: plot_stat_comparison(pl.DataFrame(), "cf_p60", "ff_p60"),  # ty: ignore[missing-argument, too-many-positional-arguments]
    ],
    ids=["plot_shot_chart", "plot_density_heatmap", "plot_line_network", "plot_rolling_stats", "plot_stat_comparison"],
)
def test_plot_options_are_keyword_only(call):
    with pytest.raises(TypeError):
        call()
