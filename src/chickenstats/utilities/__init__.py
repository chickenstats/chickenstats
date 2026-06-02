"""Public API for the chickenstats utilities module.

Importing this module automatically registers the ``'chickenstats'`` and
``'chickenstats_dark'`` matplotlib styles via ``add_cs_mplstyles()``.
After import, ``plt.style.use('chickenstats')`` works without any further calls.

Exports:
    Progress bars: ChickenProgress, ChickenProgressIndeterminate, ScrapeSpeedColumn, track
    HTTP session:  ChickenSession
    Enums:         AggLevel, Backend, Position, Zone, FORWARDS
    Type alias:    DataFrameT
    Input helpers: convert_to_list
    Directories:   charts_directory, data_directory
    Styles:        add_cs_mplstyles
"""

from chickenstats.utilities.utilities import (
    ChickenProgress,
    ChickenProgressIndeterminate,
    ChickenSession,
    ScrapeSpeedColumn,
    convert_to_list,
    track,
    data_directory,
    charts_directory,
    add_cs_mplstyles,
)
from chickenstats.utilities.enums import (
    AggLevel,
    Backend,
    FORWARDS,
    Position,
    Zone,
)
from chickenstats.utilities.types import DataFrameT

add_cs_mplstyles()

__all__ = [
    "AggLevel",
    "Backend",
    "DataFrameT",
    "ChickenProgress",
    "ChickenProgressIndeterminate",
    "ChickenSession",
    "ScrapeSpeedColumn",
    "convert_to_list",
    "FORWARDS",
    "Position",
    "Zone",
    "add_cs_mplstyles",
    "charts_directory",
    "data_directory",
    "track",
]
