"""Shared internals for chickenstats.chicken_nhl.viz plot functions."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
from hockey_rink import NHLRink

from chickenstats.utilities.utilities import charts_directory

# Fallback colors for teams missing a TEAM_COLORS entry.
DEFAULT_EVENT_COLORS = {"GOAL": "#000000", "SHOT": "#808080", "MISS": "#D3D3D3"}


def _setup_rink(rotation: int = 90) -> NHLRink:
    """Return a fresh NHLRink instance, rotated for horizontal display by default."""
    return NHLRink(rotation=rotation)


def _ensure_fig_ax(ax: plt.Axes | None) -> tuple[plt.Figure, plt.Axes]:
    """Return ``(fig, ax)``, creating a new figure/axes pair if ``ax`` is None."""
    if ax is None:
        return plt.subplots(dpi=650, figsize=(8, 5))
    return cast(plt.Figure, ax.get_figure()), ax


def _save_or_return(fig: plt.Figure, save_path: str | Path | None) -> None:
    """Save ``fig`` if ``save_path`` is given; a no-op otherwise.

    A bare filename (no parent directory) saves under ``charts_directory()``
    (``./charts``); any other path is used as-is.
    """
    if save_path is None:
        return

    path = Path(save_path)
    if path.parent == Path("."):
        path = charts_directory() / path

    fig.savefig(path, transparent=False, bbox_inches="tight")
