"""What makes an aggregated row unique.

``prep_stats``, ``prep_lines`` and ``prep_team_stats`` group play-by-play into
rows. Whatever they group by *is* the identity of a row: two rows agreeing on
every one of those columns are not two rows, they are one. This module states
that explicitly, derived from the same :func:`build_group_list` those functions
use, so the definition cannot drift from the aggregation it describes.

It lives here rather than in a consumer because the consumers were each
re-deriving it, differently. Downstream code that stores these frames needs to
know which columns identify a row -- to enforce uniqueness, to deduplicate, to
build a stable key -- and every such consumer that works it out by hand is a
copy that can silently disagree with the aggregation. Deriving it from
``build_group_list`` means the answer changes when the grouping changes.

    >>> from chickenstats.chicken_nhl.identity import identity_columns
    >>> identity_columns("team_stats", level="period")
    ['season', 'session', 'game_id', 'team', 'opp_team', 'period', 'strength_state']

The flags, and their defaults, mirror the ``prep_*`` functions exactly, because the identity of a
row depends on how it was aggregated: a frame built with ``teammates=False``
has no on-ice detail to be identified by, and its rows are correspondingly
coarser.

``lineup_ids`` selects which flavour of the on-ice lineup columns to use.
``prep_*`` emits all three (``forwards``, ``forwards_eh_id``,
``forwards_api_id``) and they are redundant with one another -- they name the
same skaters -- so an identity should use exactly one. ``api_id`` is the
default because it is the stable identifier; names change spelling and eh_ids
are derived from names.
"""

from typing import Literal

from chickenstats.chicken_nhl._agg_constants import OPPOSITION_COLS, TEAMMATES_COLS, build_group_list
from chickenstats.exceptions import InvalidInputError

Frame = Literal["stats", "lines", "team_stats"]
LineupIds = Literal["name", "eh_id", "api_id"]

# Group-by base for each frame, in OUTPUT column names. prep_stats/prep_lines/
# prep_team_stats rename event_team -> team before returning, so an identity
# quoted in terms of event_team would not match the frame it describes.
_BASE: dict[str, list[str]] = {
    # A player: the row is that player's line in that game state. prep_stats also splits on
    # position, so a player listed at two positions has a row for each.
    "stats": ["season", "session", "team", "api_id", "position"],
    # A line: the lineup column for the chosen position is added in identity_columns.
    "lines": ["season", "session", "team"],
    # A team: no on-ice detail at all, so the matchup is the whole key.
    "team_stats": ["season", "session", "team"],
}

# Grouped on, but not identifying: game_date is a property of game_id, so
# including it could never separate two rows that game_id had not already
# separated. Left out so the identity is minimal rather than merely correct.
_FUNCTIONALLY_DEPENDENT = frozenset({"game_date"})


def _lineup_flavour(columns: list[str], lineup_ids: LineupIds) -> list[str]:
    if lineup_ids == "name":
        return [c for c in columns if not c.endswith(("_eh_id", "_api_id"))]
    return [c for c in columns if c.endswith(f"_{lineup_ids}")]


def identity_columns(
    frame: Frame,
    *,
    level: str = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    lineup_ids: LineupIds = "api_id",
    position: Literal["f", "d"] = "f",
) -> list[str]:
    """Columns that together identify one row of an aggregated frame.

    Parameters:
        frame: Which aggregation -- ``'stats'``, ``'lines'`` or
            ``'team_stats'`` -- matching prep_stats/prep_lines/prep_team_stats.
        level: Aggregation level, as passed to the ``prep_*`` function.
        strength_state: Whether the frame was split by strength state.
        score: Whether the frame was split by score state.
        teammates: Whether the frame was split by own on-ice lineup. Ignored
            for ``'team_stats'``, which has no lineup detail.
        opposition: Whether the frame was split by opposing on-ice lineup.
        lineup_ids: Which flavour of lineup column to identify players by.
        position: For ``'lines'``, the position the lines were built for, as
            passed to ``prep_lines``: ``'f'`` for forward lines, ``'d'`` for
            defense pairs. Ignored for the other frames.

    Returns:
        Column names in canonical order.

    Raises:
        ValueError: If ``frame`` is not one of the three aggregations.
    """
    if frame not in _BASE:
        raise InvalidInputError(f"frame must be one of {sorted(_BASE)}, got {frame!r}", obj=frame)
    if lineup_ids not in ("name", "eh_id", "api_id"):
        raise InvalidInputError(f"lineup_ids must be 'name', 'eh_id' or 'api_id', got {lineup_ids!r}", obj=lineup_ids)
    if position not in ("f", "d"):
        raise InvalidInputError(f"position must be 'f' or 'd', got {position!r}", obj=position)

    has_lineups = frame != "team_stats"

    base = list(_BASE[frame])
    if frame == "lines":
        # The line itself is always grouped on, whatever the teammates flag
        lineup = "forwards" if position == "f" else "defense"
        base += _lineup_flavour([lineup, f"{lineup}_eh_id", f"{lineup}_api_id"], lineup_ids)

    columns = build_group_list(
        base,
        level=level,
        strength_state=strength_state,
        score=score,
        teammates=teammates and has_lineups,
        opposition=opposition and has_lineups,
        teammates_cols=_lineup_flavour(TEAMMATES_COLS, lineup_ids),
        opposition_cols=_lineup_flavour(OPPOSITION_COLS, lineup_ids),
        # The prep_* functions only add the opponent beyond what level adds when splitting by opposition
        ensure_team=opposition,
    )

    return [c for c in dict.fromkeys(columns) if c not in _FUNCTIONALLY_DEPENDENT]
