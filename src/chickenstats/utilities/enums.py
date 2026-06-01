from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Backend(str, Enum):
    """Output backend for DataFrame conversion.

    Since this is a `str` subclass, values compare equal to plain strings:
    ``Backend.POLARS == "polars"`` is ``True``.
    """

    POLARS = "polars"
    PANDAS = "pandas"
    PYARROW = "pyarrow"
    NARWHALS = "narwhals"


class AggLevel(str, Enum):
    """Aggregation level for statistics functions.

    Since this is a `str` subclass, values compare equal to plain strings:
    ``AggLevel.GAME == "game"`` is ``True``.
    """

    PERIOD = "period"
    GAME = "game"
    SESSION = "session"
    SEASON = "season"


class Position(str, Enum):
    """Player position codes.

    Since this is a `str` subclass, values compare equal to plain strings:
    ``Position.GOALIE == "G"`` is ``True``.
    """

    LEFT_WING = "L"
    CENTER = "C"
    RIGHT_WING = "R"
    DEFENSE = "D"
    GOALIE = "G"
    FORWARD = "F"  # aggregate label used in xG and aggregation logic


#: Frozenset of forward positions for O(1) membership tests.
FORWARDS: frozenset[str] = frozenset({Position.LEFT_WING, Position.CENTER, Position.RIGHT_WING})


class Zone(str, Enum):
    """Ice zone codes relative to the event team.

    Since this is a `str` subclass, values compare equal to plain strings:
    ``Zone.OFFENSIVE == "OFF"`` is ``True``.
    """

    OFFENSIVE = "OFF"
    DEFENSIVE = "DEF"
    NEUTRAL = "NEU"


@dataclass
class StatsLevels:
    """Tracks the aggregation parameters used for the cached ``stats`` DataFrame.

    Compared against the requested parameters on each ``Scraper.stats`` access
    to decide whether to recompute. Not intended for direct instantiation by
    external users.
    """

    level: str | None = None
    strength_state: bool | None = None
    score: bool | None = None
    teammates: bool | None = None
    opposition: bool | None = None


@dataclass
class LinesLevels:
    """Tracks the aggregation parameters used for the cached ``lines`` DataFrame.

    Compared against the requested parameters on each ``Scraper.lines`` access
    to decide whether to recompute. Not intended for direct instantiation by
    external users.
    """

    position: str | None = None
    level: str | None = None
    strength_state: bool | None = None
    score: bool | None = None
    teammates: bool | None = None
    opposition: bool | None = None


@dataclass
class TeamStatsLevels:
    """Tracks the aggregation parameters used for the cached ``team_stats`` DataFrame.

    Compared against the requested parameters on each ``Scraper.team_stats`` access
    to decide whether to recompute. Not intended for direct instantiation by
    external users.
    """

    level: str | None = None
    strength_state: bool | None = None
    score: bool | None = None
    opposition: bool | None = None
