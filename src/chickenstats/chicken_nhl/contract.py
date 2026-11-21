"""The public contract of play_by_play: its order, its strength states and its schema tools.

Code that sorts or validates play-by-play outside this package should read these names
rather than copy them, and they follow the package's version like any other public name.

Within one game second, events follow ``EVENT_SORT_ORDER``, except that an event the NHL's
report shows with a same-second line change already made comes just after that change, and a
shootout keeps the report's order. The order is the same whichever Scraper frame is read first.

Attributes:
    EVENT_SORT_ORDER: Where each event type falls among the events of one game second.
    PBP_ORDER_COLUMNS: The columns that put a play-by-play frame in its one true order.
    CHRONOLOGICAL_COLUMNS: The columns that put rows from many games in the order played.
    FENWICK_EVENTS: The event types that count as unblocked shot attempts.
    STRENGTH_STATES: The strength states a sound game produces.

Public functions:
    assert_chronological: Raise unless rows run forward in time, game by game.
    assert_unique_events: Raise if an event appears more than once.
    assert_xg_fields_match: Raise unless xg_fields has one row for each Fenwick attempt.
    build_pandera_schema: Build a pandera DataFrameSchema from a schema dictionary.
    sort_chronological: Sort rows from many games into the order they were played.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, overload

import polars as pl

from chickenstats.chicken_nhl import _game_utils
from chickenstats.chicken_nhl._validation_schema import polars_dtype_map, polars_pandera_options
from chickenstats.chicken_nhl._validation_utils import build_pandera_schema
from chickenstats.exceptions import InvalidInputError

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "CHRONOLOGICAL_COLUMNS",
    "EVENT_SORT_ORDER",
    "FENWICK_EVENTS",
    "PBP_ORDER_COLUMNS",
    "STRENGTH_STATES",
    "assert_chronological",
    "assert_unique_events",
    "assert_xg_fields_match",
    "build_pandera_schema",
    "polars_dtype_map",
    "polars_pandera_options",
    "sort_chronological",
]

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

CHRONOLOGICAL_COLUMNS: tuple[str, ...] = ("season", "game_date", "game_id", "event_idx")
"""Sorting on these puts rows from many games in the order they were played. game_id alone
does not: it follows the schedule's release, not the date, and game_id only breaks ties
among one day's games."""

FENWICK_EVENTS: frozenset[str] = _game_utils.FENWICK_EVENTS
"""Goals, shots on goal and missed shots. A play_by_play row has ``fenwick`` 1 only for these, and
not for an own goal or a shootout attempt, which ``shootout_attempt`` flags instead."""

STRENGTH_STATES: tuple[str, ...] = (
    *(f"{home}v{away}" for home in ("5", "4", "3", "E") for away in ("5", "4", "3", "E")),
    "1v0",
    "0v1",
)
"""Strength states from the event team's side: skaters for each team, E for an empty net,
and 1v0 or 0v1 for a penalty shot or shootout attempt. Rows with other counts are errors in
the NHL's data, and ``ILLEGAL`` marks those the package can't resolve."""


@overload
def sort_chronological(df: pd.DataFrame) -> pd.DataFrame: ...
@overload
def sort_chronological(df: pl.DataFrame) -> pl.DataFrame: ...
def sort_chronological(df: pd.DataFrame | pl.DataFrame) -> pd.DataFrame | pl.DataFrame:
    """Sort rows from many games into the order they were played, keeping ties in place.

    Parameters:
        df (pd.DataFrame | pl.DataFrame): Rows carrying ``CHRONOLOGICAL_COLUMNS``.

    Returns:
        pd.DataFrame | pl.DataFrame: The rows in order, in the same backend.

    Raises:
        InvalidInputError: If one of the columns is missing.
    """
    columns = list(CHRONOLOGICAL_COLUMNS)
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise InvalidInputError(f"Cannot order rows chronologically without {missing}")

    if isinstance(df, pl.DataFrame):
        return df.sort(columns, maintain_order=True)

    return df.sort_values(columns, kind="stable").reset_index(drop=True)


def assert_chronological(df: pd.DataFrame | pl.DataFrame, *, what: str) -> None:
    """Raise unless season and game_date never step back and each game's rows are together.

    Parameters:
        df (pd.DataFrame | pl.DataFrame): Rows carrying season, game_date and game_id.
        what (str): What the rows are, for the error message.

    Raises:
        InvalidInputError: If the rows step back in time or a game is split.
    """
    frame = df if isinstance(df, pl.DataFrame) else pl.from_pandas(df[["season", "game_date", "game_id"]])
    when = frame.select("season", pl.col("game_date").cast(pl.String), "game_id")

    season, date = pl.col("season"), pl.col("game_date")
    step_back = (season < season.shift(1)) | ((season == season.shift(1)) & (date < date.shift(1)))
    steps = when.select(step_back.fill_null(False).sum()).item()
    if steps:
        raise InvalidInputError(f"{what}: rows are not in chronological order ({steps:,} steps back in time)")

    starts = when.select((pl.col("game_id") != pl.col("game_id").shift(1)).fill_null(True).sum()).item()
    games = when["game_id"].n_unique()
    if starts != games:
        raise InvalidInputError(f"{what}: {starts - games:,} games are split across non-adjacent rows")


def assert_unique_events(df: pd.DataFrame | pl.DataFrame, *, what: str) -> None:
    """Raise if a (game_id, event_idx) pair appears more than once.

    Parameters:
        df (pd.DataFrame | pl.DataFrame): Rows carrying game_id and event_idx.
        what (str): What the rows are, for the error message.

    Raises:
        InvalidInputError: If a pair repeats.
    """
    keys = ["game_id", "event_idx"]
    frame = df if isinstance(df, pl.DataFrame) else pl.from_pandas(df[keys])
    repeats = frame.height - frame.n_unique(subset=keys)
    if repeats:
        raise InvalidInputError(f"{what}: {repeats:,} (game_id, event_idx) keys appear more than once")


def assert_xg_fields_match(
    play_by_play: pd.DataFrame | pl.DataFrame, xg_fields: pd.DataFrame | pl.DataFrame, *, what: str
) -> None:
    """Raise unless xg_fields has exactly one row for each play_by_play row with ``fenwick`` 1.

    Rows match on game_id and event_idx, so own goals and shootout attempts, which have
    ``fenwick`` 0, must not appear in xg_fields.

    Parameters:
        play_by_play (pd.DataFrame | pl.DataFrame): Play-by-play rows, with game_id, event_idx and fenwick.
        xg_fields (pd.DataFrame | pl.DataFrame): The xg_fields rows for the same games.
        what (str): What the rows are, for the error message.

    Raises:
        InvalidInputError: If a Fenwick attempt has no xg_fields row, or a row has no Fenwick attempt.
    """
    keys = ["game_id", "event_idx"]
    pbp = play_by_play if isinstance(play_by_play, pl.DataFrame) else pl.from_pandas(play_by_play[[*keys, "fenwick"]])
    xg = xg_fields if isinstance(xg_fields, pl.DataFrame) else pl.from_pandas(xg_fields[keys])
    assert_unique_events(xg, what=f"{what} xg_fields")

    attempts = pbp.filter(pl.col("fenwick") == 1).select(keys)
    missing = attempts.join(xg.select(keys), on=keys, how="anti")
    extra = xg.select(keys).join(attempts, on=keys, how="anti")
    problems = [
        f"{len(rows):,} {label}, e.g. {rows.head(3).rows()}"
        for rows, label in (
            (missing, "Fenwick attempts without an xg_fields row"),
            (extra, "xg_fields rows without a Fenwick attempt"),
        )
        if len(rows)
    ]
    if problems:
        raise InvalidInputError(f"{what}: " + "; ".join(problems))
