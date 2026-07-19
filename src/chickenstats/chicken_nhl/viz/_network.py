"""Line-combination network graphs: plot_line_network."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import polars as pl
import seaborn as sns

from chickenstats.chicken_nhl.team import TEAM_COLORS
from chickenstats.chicken_nhl.viz._helpers import DEFAULT_EVENT_COLORS, _ensure_fig_ax, _save_or_return
from chickenstats.exceptions import InvalidInputError
from chickenstats.utilities.utilities import _to_polars

_DEFAULT_POSITIONS = ["C", "L", "R", "L/R", "L/C", "R/L", "R/C", "C/L", "C/R"]


def _create_network_graph(
    stats: pd.DataFrame, team: str, strengths: list[str], toi_min: float, positions: list[str]
) -> nx.Graph:
    """Build a teammate-combination graph weighted by shared TOI."""
    df = stats.loc[
        (stats.team == team)
        & (stats.strength_state.isin(strengths))
        & (stats.toi >= toi_min)
        & (stats.position.isin(positions))
    ].reset_index(drop=True)

    if df.empty:
        raise InvalidInputError(
            f"No players found for team={team!r}, strengths={strengths!r}, toi_min={toi_min!r}.", obj=stats
        )

    players = df.player.sort_values().unique().tolist()

    concat_list = [df.player.copy(deep=True)]

    for player in players:
        conds = [
            df.player == player,
            (df.player != player) & (df.forwards.str.contains(player) | df.defense.str.contains(player)),
        ]
        values = [np.nan, df.toi]
        player_series = pd.Series(np.select(conds, values, 0), name=player)
        concat_list.append(player_series)

    merged = pd.concat(concat_list, axis=1).groupby("player", as_index=False).sum()
    merged = merged.set_index("player", drop=True)
    merged = (merged - merged.min().min()) / (merged.max().max() - merged.min().min()) * 75
    merged = merged.reset_index()

    edges = merged.melt(
        id_vars=["player"],
        value_vars=[c for c in merged.columns if c != "player"],
        var_name="target",
        value_name="weight",
    ).rename(columns={"player": "source"})

    return nx.from_pandas_edgelist(edges, edge_attr=True)


def _draw_graph(g: nx.Graph, team: str, ax: plt.Axes) -> None:
    """Draw a teammate-combination graph with team-colored nodes/edges into ax."""
    colors = TEAM_COLORS.get(team, DEFAULT_EVENT_COLORS)

    node_options = {"node_color": colors["GOAL"], "node_size": 1000, "edgecolors": colors["SHOT"], "linewidths": 2}

    weights = nx.get_edge_attributes(g, "weight")
    edge_options = {"edge_color": colors["SHOT"], "alpha": 0.7, "width": [weights[edge] / 10 for edge in g.edges()]}

    pos = nx.spring_layout(g, iterations=10, seed=20000)

    nx.draw_networkx_nodes(g, pos, ax=ax, **node_options)
    nx.draw_networkx_labels(
        g, pos, ax=ax, font_size=8, font_color=colors["SHOT"], font_weight="bold", bbox={"alpha": 0.5, "color": "white"}
    )
    nx.draw_networkx_edges(g, pos, ax=ax, **edge_options)

    sns.despine(ax=ax, left=True, bottom=True)


def plot_line_network(
    stats: pl.DataFrame | pd.DataFrame,
    team: str,
    strengths: list[str] | None = None,
    toi_min: float = 15.0,
    positions: list[str] | None = None,
    ax: plt.Axes | None = None,
    save_path: str | Path | None = None,
) -> plt.Axes:
    """Network graph of teammate combinations, edge width proportional to shared TOI.

    Builds a graph from ``prep_stats(teammates=True)``-style output: each node is a
    player, each edge weight is TOI shared together (as teammates), min-max normalized.

    Parameters:
        stats (pl.DataFrame | pd.DataFrame): Individual stats with teammate columns, e.g.
            from ``scraper.prep_stats(teammates=True)`` then ``scraper.stats``.
        team (str): Three-letter team code to plot, e.g. ``"NSH"``.
        strengths (list[str] | None): Strength states to include. Defaults to ``["5v5"]``.
        toi_min (float): Minimum TOI (in the units present in ``stats``) for a player to
            be included. Default ``15.0``.
        positions (list[str] | None): Position codes to include. Defaults to forward
            positions (``C``, ``L``, ``R``, and their combinations).
        ax (plt.Axes | None): Existing axes to draw into. Creates a new figure if ``None``.
        save_path (str | Path | None): If given, saves the figure. A bare filename saves
            under ``charts_directory()``.

    Returns:
        plt.Axes: The axes the network graph was drawn on.

    Raises:
        InvalidInputError: If no players match the given filters.

    Examples:
        >>> from chickenstats.chicken_nhl import Scraper
        >>> from chickenstats.chicken_nhl.viz import plot_line_network
        >>> scraper = Scraper([2023020001])
        >>> scraper.prep_stats(teammates=True)
        >>> plot_line_network(scraper.stats, team="NSH")
    """
    if strengths is None:
        strengths = ["5v5"]

    if positions is None:
        positions = _DEFAULT_POSITIONS

    pdf = _to_polars(stats).to_pandas()

    graph = _create_network_graph(pdf, team, strengths, toi_min, positions)

    fig, ax = _ensure_fig_ax(ax)

    _draw_graph(graph, team, ax)

    _save_or_return(fig, save_path)

    return ax
