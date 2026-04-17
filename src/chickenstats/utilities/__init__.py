"""Public API for the chickenstats utilities module.

Importing this module automatically registers the ``'chickenstats'`` and
``'chickenstats_dark'`` matplotlib styles via ``add_cs_mplstyles()``.
After import, ``plt.style.use('chickenstats')`` works without any further calls.

Exports:
    Progress bars: ChickenProgress, ChickenProgressIndeterminate, ScrapeSpeedColumn
    HTTP session:  ChickenSession
    Enums:         AggLevel, Backend, Position, Zone, FORWARDS
    Cache helpers: StatsLevels, LinesLevels, TeamStatsLevels
    Type alias:    DataFrameT
    Directories:   charts_directory, data_directory
    Styles:        add_cs_mplstyles
"""

from chickenstats.utilities.utilities import (
    ChickenProgress,
    ChickenProgressIndeterminate,
    ChickenSession,
    ScrapeSpeedColumn,
    data_directory,
    charts_directory,
    add_cs_mplstyles,
)
from chickenstats.utilities.enums import (
    AggLevel,
    Backend,
    FORWARDS,
    LinesLevels,
    Position,
    StatsLevels,
    TeamStatsLevels,
    Zone,
)
from chickenstats.utilities._types import DataFrameT

add_cs_mplstyles()

__all__ = [
    "AggLevel",
    "Backend",
    "DataFrameT",
    "ChickenProgress",
    "ChickenProgressIndeterminate",
    "ChickenSession",
    "ScrapeSpeedColumn",
    "FORWARDS",
    "LinesLevels",
    "Position",
    "StatsLevels",
    "TeamStatsLevels",
    "Zone",
    "add_cs_mplstyles",
    "charts_directory",
    "data_directory",
]
