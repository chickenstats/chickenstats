from __future__ import annotations

from chickenstats.chicken_nhl._game_html_changes import _GameHTMLChangesMixin
from chickenstats.chicken_nhl._game_html_events import _GameHTMLEventsMixin
from chickenstats.chicken_nhl._game_html_rosters import _GameHTMLRostersMixin
from chickenstats.chicken_nhl._game_html_shifts import _GameHTMLShiftsMixin


class _GameHTMLMixin(_GameHTMLChangesMixin, _GameHTMLEventsMixin, _GameHTMLRostersMixin, _GameHTMLShiftsMixin):
    """Combines the events/rosters/shifts/changes HTML-report mixins for ``Game``."""
