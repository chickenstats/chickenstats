"""chickenstats.chicken_nhl.viz: Chart functions for play-by-play and stats output.

Wraps the shot-chart, network-graph, and rate-stat comparison patterns from
chickenstats' example notebooks into reusable functions. Requires the ``plotting``
extra (``pip install chickenstats[plotting]``) — matplotlib, seaborn, hockey-rink,
and networkx are not installed by default.

Every function checks for a ``pred_goal`` column (xG) rather than requiring one:
``pred_goal`` is only present for chickenstats-api users, so scraper-only users get
a still-useful, count/rate-based fallback instead of an error.

Public functions:
    plot_shot_chart: Scatter shot chart on a rink, colored by event type.
    plot_density_heatmap: KDE shot-density map on a rink.
    plot_line_network: Network graph of teammate combinations, edge width = shared TOI.
    plot_rolling_stats: Line chart of a rolling_{stat} column over game number.
    plot_stat_comparison: Bubble scatter comparing two rate-stat columns.
"""

from __future__ import annotations

try:
    import matplotlib  # noqa: F401
    import seaborn  # noqa: F401
    import hockey_rink  # noqa: F401
    import networkx  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "chickenstats.chicken_nhl.viz requires the 'plotting' extra. Install with: pip install chickenstats[plotting]"
    ) from exc

from chickenstats.chicken_nhl.viz._rink import plot_shot_chart, plot_density_heatmap
from chickenstats.chicken_nhl.viz._network import plot_line_network
from chickenstats.chicken_nhl.viz._stats import plot_rolling_stats, plot_stat_comparison

__all__ = ["plot_shot_chart", "plot_density_heatmap", "plot_line_network", "plot_rolling_stats", "plot_stat_comparison"]
