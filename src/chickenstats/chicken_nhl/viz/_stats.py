"""Rate-stat line and comparison charts: plot_rolling_stats, plot_stat_comparison."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
import seaborn as sns

from chickenstats.chicken_nhl.team import TEAM_COLORS
from chickenstats.chicken_nhl.viz._helpers import _save_or_return
from chickenstats.exceptions import InvalidInputError
from chickenstats.utilities.utilities import _to_polars


def plot_rolling_stats(
    rolling_df: pl.DataFrame | pd.DataFrame,
    stat: str,
    team: str | None = None,
    player: str | None = None,
    window: int | None = None,
    ax: plt.Axes | None = None,
    save_path: str | Path | None = None,
) -> plt.Axes:
    """Line chart of a rolling-window stat over game number.

    Plots the ``rolling_{stat}`` column produced by ``prep_rolling_stats()`` against game
    order. ``stat`` is required and explicit (not defaulted to an xG stat), so this works
    identically for a scraper-available stat like ``"cf_p60"`` as it would for an
    xG stat like ``"xgf_p60"`` (chickenstats-api only).

    Parameters:
        rolling_df (pl.DataFrame | pd.DataFrame): Output of ``prep_rolling_stats()``.
        stat (str): Base stat name (without the ``rolling_`` prefix), e.g. ``"cf_p60"``.
        team (str | None): Filter to a single team. Default ``None`` (no filter).
        player (str | None): Filter to a single player. Default ``None`` (no filter).
        window (int | None): Window size used when the rolling column was computed —
            used only to label the axis (e.g. "10-game rolling average"); the windowing
            itself already happened in ``prep_rolling_stats()``.
        ax (plt.Axes | None): Existing axes to draw into. Creates a new figure if ``None``.
        save_path (str | Path | None): If given, saves the figure. A bare filename saves
            under ``charts_directory()``.

    Returns:
        plt.Axes: The axes the line chart was drawn on.

    Raises:
        InvalidInputError: If ``rolling_{stat}`` is not a column in ``rolling_df``, or if
            no rows remain after filtering.

    Examples:
        >>> from chickenstats.chicken_nhl import prep_rolling_stats
        >>> from chickenstats.chicken_nhl.viz import plot_rolling_stats
        >>> rolling = prep_rolling_stats(game_stats, window=10)
        >>> plot_rolling_stats(rolling, stat="cf_p60", team="NSH")
    """
    rolling_col = f"rolling_{stat}"

    df = _to_polars(rolling_df)

    if rolling_col not in df.columns:
        raise InvalidInputError(
            f"{rolling_col!r} is not a column in rolling_df — call prep_rolling_stats() "
            f"with stat {stat!r} (or a matching stats=[...] list) first.",
            obj=rolling_df,
        )

    if team is not None and "team" in df.columns:
        df = df.filter(pl.col("team") == team)

    if player is not None and "player" in df.columns:
        df = df.filter(pl.col("player") == player)

    if df.is_empty():
        raise InvalidInputError(f"No rows remain for team={team!r}, player={player!r}.", obj=rolling_df)

    if ax is None:
        fig, ax = plt.subplots(dpi=650, figsize=(8, 5))
    else:
        fig = cast(plt.Figure, ax.get_figure())

    color = TEAM_COLORS.get(team, {}).get("GOAL") if team is not None else None

    y = df[rolling_col].to_list()
    x = list(range(1, len(y) + 1))

    sns.lineplot(x=x, y=y, color=color, ax=ax)

    ax.set_xlabel("Game number")
    label = f"{window}-game rolling {stat}" if window is not None else f"Rolling {stat}"
    ax.set_ylabel(label)

    _save_or_return(fig, save_path)

    return ax


def plot_stat_comparison(
    stats: pl.DataFrame | pd.DataFrame,
    x: str,
    y: str,
    highlight_team: str | None = None,
    size: str | None = "toi",
    ax: plt.Axes | None = None,
    save_path: str | Path | None = None,
) -> plt.Axes:
    """Bubble scatter comparing two rate-stat columns, with an optional highlighted team.

    Generic over column names — works identically for scraper-only users (e.g.
    ``x="cf_p60", y="ff_p60"``) as for chickenstats-api users passing xG columns.
    Draws mean reference lines for both axes. When ``highlight_team`` is given,
    non-matching rows are plotted first in gray and the highlighted team's rows are
    plotted on top in its own colors, so it's never visually buried.

    Note:
        Rate stats (``*_p60``) on rows with very low TOI can be extreme (e.g. one shot
        in six seconds of ice time is a huge per-60 rate) and will visually dominate the
        chart. Filter ``stats`` to a reasonable ``toi`` minimum first
        (e.g. ``stats.filter(pl.col("toi") >= 15)``).

    Parameters:
        stats (pl.DataFrame | pd.DataFrame): Stats DataFrame with a ``team`` column and
            the requested ``x``/``y``/``size`` columns, e.g. from ``scraper.lines`` or
            ``scraper.team_stats``.
        x (str): Column name for the x-axis.
        y (str): Column name for the y-axis.
        highlight_team (str | None): Three-letter team code to highlight. Default ``None``
            (single-pass scatter, default matplotlib coloring).
        size (str | None): Column name to size bubbles by. Default ``"toi"``; pass
            ``None`` for uniform bubble size.
        ax (plt.Axes | None): Existing axes to draw into. Creates a new figure if ``None``.
        save_path (str | Path | None): If given, saves the figure. A bare filename saves
            under ``charts_directory()``.

    Returns:
        plt.Axes: The axes the comparison chart was drawn on.

    Examples:
        >>> from chickenstats.chicken_nhl.viz import plot_stat_comparison
        >>> plot_stat_comparison(lines, x="cf_p60", y="ff_p60", highlight_team="NSH")
    """
    df = _to_polars(stats)

    if ax is None:
        fig, ax = plt.subplots(dpi=650, figsize=(8, 5))
    else:
        fig = cast(plt.Figure, ax.get_figure())

    x_mean = cast(float, df[x].mean())
    y_mean = cast(float, df[y].mean())
    ax.axvline(x=x_mean, zorder=-1, alpha=0.5)
    ax.axhline(y=y_mean, zorder=-1, alpha=0.5)

    size_norm = (df[size].min(), df[size].max()) if size is not None else None
    scatter_kwargs: dict = {"size": size, "sizes": (20, 150), "size_norm": size_norm} if size is not None else {}

    if highlight_team is None:
        sns.scatterplot(data=df.to_pandas(), x=x, y=y, ax=ax, legend=False, **scatter_kwargs)
    else:
        colors = TEAM_COLORS.get(highlight_team, {"GOAL": "#000000", "SHOT": "#808080", "MISS": "#D3D3D3"})

        other = df.filter(pl.col("team") != highlight_team).to_pandas()
        sns.scatterplot(
            data=other,
            x=x,
            y=y,
            ax=ax,
            facecolor=colors["MISS"],
            edgecolor=colors["MISS"],
            alpha=0.5,
            legend=False,
            **scatter_kwargs,
        )

        highlighted = df.filter(pl.col("team") == highlight_team).to_pandas()
        sns.scatterplot(
            data=highlighted,
            x=x,
            y=y,
            ax=ax,
            facecolor=colors["GOAL"],
            edgecolor=colors["SHOT"],
            alpha=0.8,
            legend=False,
            **scatter_kwargs,
        )

    ax.set_xlabel(x)
    ax.set_ylabel(y)

    _save_or_return(fig, save_path)

    return ax
