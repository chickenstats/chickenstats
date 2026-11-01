from __future__ import annotations

from chickenstats.chicken_nhl._game_html_changes import _GameHTMLChangesMixin
from chickenstats.chicken_nhl._game_html_events import _GameHTMLEventsMixin
from chickenstats.chicken_nhl._game_html_rosters import _GameHTMLRostersMixin
from chickenstats.chicken_nhl._game_html_shifts import _GameHTMLShiftsMixin
from chickenstats.utilities.types import FrameT


class _GameHTMLMixin(
    _GameHTMLChangesMixin[FrameT],
    _GameHTMLEventsMixin[FrameT],
    _GameHTMLRostersMixin[FrameT],
    _GameHTMLShiftsMixin[FrameT],
):
    """Combines the events/rosters/shifts/changes HTML-report mixins for ``Game``."""
