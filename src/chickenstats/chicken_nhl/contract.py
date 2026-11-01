"""The public contract of play_by_play: its order, its strength states and its schema tools.

Code that sorts or validates play-by-play outside this package should read these names
rather than copy them, and they follow the package's version like any other public name.

Attributes:
    EVENT_SORT_ORDER: Where each event type falls among the events of one game second.
    PBP_ORDER_COLUMNS: The columns that put a play-by-play frame in its one true order.
    STRENGTH_STATES: The strength states a sound game produces.

Public functions:
    build_pandera_schema: Build a pandera DataFrameSchema from a schema dictionary.
"""

from types import MappingProxyType

from chickenstats.chicken_nhl._validation_schema import polars_dtype_map
from chickenstats.chicken_nhl._validation_utils import build_pandera_schema

__all__ = ["EVENT_SORT_ORDER", "PBP_ORDER_COLUMNS", "STRENGTH_STATES", "build_pandera_schema", "polars_dtype_map"]

EVENT_SORT_ORDER = MappingProxyType(
    {
        "PGSTR": 1,
        "PGEND": 2,
        "ANTHEM": 3,
        "EGT": 3,
        "CHL": 3,
        "DELPEN": 3,
        "BLOCK": 3,
        "GIVE": 3,
        "HIT": 3,
        "MISS": 3,
        "SHOT": 3,
        "TAKE": 3,
        "GOAL": 5,
        "STOP": 6,
        "PENL": 7,
        "PBOX": 7,
        "PSTR": 7,
        "CHANGE": 8,
        "EISTR": 9,
        "EIEND": 10,
        "FAC": 12,
        "PEND": 13,
        "SOC": 14,
        "GEND": 15,
        "GOFF": 16,
    }
)
"""Rank of each event type within one game second; lower comes first, and an unlisted type
comes last. An event the NHL's report places after a line change in its second is ranked
just after CHANGE instead, so sort on ``PBP_ORDER_COLUMNS`` to reproduce the final order."""

PBP_ORDER_COLUMNS: tuple[str, ...] = ("season", "game_id", "event_idx")
"""Sorting on these puts play-by-play in order. Shootouts are ordered the same way, and
``shootout_attempt`` flags their shots and goals."""

STRENGTH_STATES: tuple[str, ...] = (
    *(f"{home}v{away}" for home in ("5", "4", "3", "E") for away in ("5", "4", "3", "E")),
    "1v0",
    "0v1",
)
"""Strength states from the event team's side: skaters for each team, E for an empty net,
and 1v0 or 0v1 for a penalty shot or shootout attempt. Rows with other counts are errors in
the NHL's data, and ``ILLEGAL`` marks those the package can't resolve."""
