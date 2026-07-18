"""Shared internals for chickenstats.chicken_nhl.viz plot functions."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from hockey_rink import NHLRink

from chickenstats.utilities.utilities import charts_directory


def _setup_rink(rotation: int = 90) -> NHLRink:
    """Return a fresh NHLRink instance, rotated for horizontal display by default."""
    return NHLRink(rotation=rotation)


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
