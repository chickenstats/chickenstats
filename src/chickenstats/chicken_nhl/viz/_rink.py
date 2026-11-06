"""Rink-based shot charts: plot_shot_chart, plot_density_heatmap."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
import seaborn as sns

from chickenstats.chicken_nhl.team import TEAM_COLORS
from chickenstats.chicken_nhl.viz._helpers import DEFAULT_EVENT_COLORS, _ensure_fig_ax, _save_if_requested, _setup_rink
from chickenstats.exceptions import InvalidInputError
from chickenstats.utilities.utilities import _to_polars, norm_coords

_SHOT_EVENTS = ["MISS", "SHOT", "GOAL"]
_SIZE_MULTIPLIER = 500


def _filter_shots(pbp: pl.DataFrame, team: str, player: str | None, strengths: list[str] | None) -> pl.DataFrame:
    df = pbp.filter(pl.col("event").is_in(_SHOT_EVENTS), pl.col("event_team") == team)

    # Shootout attempts are not shots or goals, so they are not drawn
    if "shootout_attempt" in df.columns:
        df = df.filter(pl.col("shootout_attempt") != 1)

    if player is not None:
        df = df.filter(pl.col("player_1") == player)

    if strengths is not None:
        df = df.filter(pl.col("strength_state").is_in(strengths))

    if df.is_empty():
        raise InvalidInputError(
            f"No shot events found for team={team!r}, player={player!r}, strengths={strengths!r}.", obj=pbp
        )

    return norm_coords(df, normalization_column="event_team", normalization_value=team)


def _goal_edgecolor(colors: dict[str, str]) -> str:
    return colors["SHOT"] if colors["GOAL"] == "#FFFFFF" else "#FFFFFF"


def plot_shot_chart(
    pbp: pl.DataFrame | pd.DataFrame,
    team: str,
    player: str | None = None,
    zone: Literal["full", "ozone", "dzone"] = "ozone",
    strengths: list[str] | None = None,
    ax: plt.Axes | None = None,
    save_path: str | Path | None = None,
) -> plt.Axes:
    """Scatter shot chart on an NHL rink, colored by event type.

    Filters ``pbp`` to shot events (MISS/SHOT/GOAL), leaving out shootout attempts, and normalizes coordinates
    so shots point toward the same end. Markers are sized by ``pred_goal`` if present, else uniform.

    Parameters:
        pbp (pl.DataFrame | pd.DataFrame): Play-by-play data, e.g. from ``Scraper.play_by_play``.
        team (str): Three-letter team code to plot, e.g. ``"NSH"``.
        player (str | None): Restrict to a single shooter's shots. Default ``None`` (whole team).
        zone (Literal["full", "ozone", "dzone"]): Rink area to display. Default ``"ozone"``.
        strengths (list[str] | None): Restrict to specific strength states, e.g. ``["5v5"]``.
        ax (plt.Axes | None): Existing axes to draw into. Creates a new figure if ``None``.
        save_path (str | Path | None): If given, saves the figure at 650 dpi and, when this
            function created the figure, closes it. A bare filename saves under
            ``charts_directory()``.

    Returns:
        plt.Axes: The axes the shot chart was drawn on.

    Raises:
        InvalidInputError: If no shot events match the given filters.

    Examples:
        >>> from chickenstats.chicken_nhl import Scraper
        >>> from chickenstats.chicken_nhl.viz import plot_shot_chart
        >>> scraper = Scraper([2023020001])
        >>> plot_shot_chart(scraper.play_by_play, team="NSH")
    """
    df = _filter_shots(_to_polars(pbp), team, player, strengths)

    created = ax is None
    fig, ax = _ensure_fig_ax(ax)

    rink = _setup_rink()
    rink.draw(ax=ax, display_range=zone)

    colors = TEAM_COLORS.get(team, DEFAULT_EVENT_COLORS)
    sized_by_xg = "pred_goal" in df.columns

    for shot_event in _SHOT_EVENTS:
        event_df = df.filter(pl.col("event") == shot_event)
        if event_df.is_empty():
            continue

        facecolor = colors[shot_event]
        edgecolor = _goal_edgecolor(colors) if shot_event == "GOAL" else "#FFFFFF"

        plot_kwargs: dict = {}
        if sized_by_xg:
            plot_kwargs["s"] = event_df["pred_goal"].to_numpy() * _SIZE_MULTIPLIER
            plot_kwargs["size_norm"] = (0, _SIZE_MULTIPLIER)
        else:
            plot_kwargs["s"] = 40

        rink.plot_fn(
            sns.scatterplot,
            data=event_df.to_pandas(),
            x="norm_coords_x",
            y="norm_coords_y",
            color=facecolor,
            edgecolor=edgecolor,
            lw=0.75,
            zorder=100,
            alpha=0.75,
            ax=ax,
            legend=False,
            **plot_kwargs,
        )

    _save_if_requested(fig, save_path, close=created)

    return ax


def plot_density_heatmap(
    pbp: pl.DataFrame | pd.DataFrame,
    team: str,
    player: str | None = None,
    weight_col: str | None = None,
    strengths: list[str] | None = None,
    ax: plt.Axes | None = None,
    save_path: str | Path | None = None,
) -> plt.Axes:
    """KDE shot-density map on an NHL rink.

    Filters ``pbp`` to shot events, leaving out shootout attempts, and draws a filled kernel-density map with a
    contour outline.

    Parameters:
        pbp (pl.DataFrame | pd.DataFrame): Play-by-play data, e.g. from ``Scraper.play_by_play``.
        team (str): Three-letter team code to plot, e.g. ``"NSH"``.
        player (str | None): Restrict to a single shooter's shots. Default ``None`` (whole team).
        weight_col (str | None): Column to weight the density by. Defaults to unweighted, or
            ``"pred_goal"`` automatically if present in ``pbp``.
        strengths (list[str] | None): Restrict to specific strength states, e.g. ``["5v4"]``.
        ax (plt.Axes | None): Existing axes to draw into. Creates a new figure if ``None``.
        save_path (str | Path | None): If given, saves the figure at 650 dpi and, when this
            function created the figure, closes it. A bare filename saves under
            ``charts_directory()``.

    Returns:
        plt.Axes: The axes the density map was drawn on.

    Raises:
        InvalidInputError: If no shot events match the given filters.

    Examples:
        >>> from chickenstats.chicken_nhl import Scraper
        >>> from chickenstats.chicken_nhl.viz import plot_density_heatmap
        >>> scraper = Scraper([2023020001])
        >>> plot_density_heatmap(scraper.play_by_play, team="NSH")
    """
    df = _filter_shots(_to_polars(pbp), team, player, strengths)

    if weight_col is None and "pred_goal" in df.columns:
        weight_col = "pred_goal"

    created = ax is None
    fig, ax = _ensure_fig_ax(ax)

    rink = _setup_rink()
    rink.draw(ax=ax, display_range="ozone")

    pdf = df.to_pandas()
    weights = pdf[weight_col] if weight_col is not None else None

    # The filled density and its contour outline share the same data, levels and weights.
    kde_kwargs = {
        "data": pdf,
        "x": "norm_coords_x",
        "y": "norm_coords_y",
        "cmap": "rocket_r",
        "levels": 12,
        "weights": weights,
        "ax": ax,
    }

    rink.plot_fn(sns.kdeplot, **kde_kwargs, fill=True, zorder=100, alpha=0.75, legend=False)
    rink.plot_fn(sns.kdeplot, **kde_kwargs, fill=False, linewidths=2, zorder=110, alpha=1)

    _save_if_requested(fig, save_path, close=created)

    return ax
