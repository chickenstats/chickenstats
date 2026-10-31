from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import pandas as pd

from chickenstats.chicken_nhl._game_utils import aggregate_players, game_seconds
from chickenstats.chicken_nhl.validation_pydantic import ChangeEvent
from chickenstats.chicken_nhl.validation_polars import changes_polars_schema
from chickenstats.chicken_nhl._docstrings import _GAME_CHANGES_DF_DOC, _GAME_CHANGES_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import _GameBase


def _dedupe_by_team_jersey(players: list[dict]) -> list[dict]:
    """Drop later entries with a team_jersey already seen, preserving order."""
    seen: set = set()
    deduped = []
    for player in players:
        team_jersey = player["team_jersey"]
        if team_jersey in seen:
            continue
        seen.add(team_jersey)
        deduped.append(player)
    return deduped


class _GameHTMLChangesMixin(_GameBase):
    def _munge_changes(self, shifts: list) -> list:
        """Transform shifts into changes."""
        changes_map = {}

        # Group all shifts by their start and end times in a single pass
        for shift in shifts:
            # A shift's start is a change on and its end a change off
            for side, seconds, time in (
                ("on", "start_time_seconds", "start_time"),
                ("off", "end_time_seconds", "end_time"),
            ):
                key = (shift["period"], shift["team_venue"], shift.get(seconds, 0))

                if key not in changes_map:
                    changes_map[key] = {
                        "on": [],
                        "off": [],
                        "period_time": shift[time],
                        "is_home": shift["is_home"],
                        "is_away": shift["is_away"],
                        "team": shift["team"],
                    }
                changes_map[key][side].append(shift)

        final_changes = []

        sorted_keys = sorted(changes_map, key=lambda k: (k[0], k[2], 0 if k[1] == "HOME" else 1))

        for key in sorted_keys:
            period, team_venue, time_seconds = key
            data = changes_map[key]

            on_players = sorted(data["on"], key=lambda k: k.get("jersey", 0))
            off_players = sorted(data["off"], key=lambda k: k.get("jersey", 0))

            # A player can have two shifts starting/ending at the same second (NHL data
            # inconsistency), which would otherwise duplicate them in the output.
            on_players = _dedupe_by_team_jersey(on_players)
            off_players = _dedupe_by_team_jersey(off_players)

            # Players in both ON and OFF are data errors — drop from each to preserve prior ice state
            duplicate_jerseys = {s["team_jersey"] for s in on_players} & {s["team_jersey"] for s in off_players}
            if duplicate_jerseys:
                on_players = [s for s in on_players if s["team_jersey"] not in duplicate_jerseys]
                off_players = [s for s in off_players if s["team_jersey"] not in duplicate_jerseys]

            on_data = aggregate_players(on_players)
            off_data = aggregate_players(off_players)

            desc_parts = []
            if on_data["ALL"]["count"] > 0:
                desc_parts.append(f"PLAYERS ON: {', '.join(on_data['ALL']['names'])}")
            if off_data["ALL"]["count"] > 0:
                desc_parts.append(f"PLAYERS OFF: {', '.join(off_data['ALL']['names'])}")
            description = " / ".join(desc_parts) if desc_parts else "NO CHANGE"

            change_dict = {
                "season": self.season,
                "session": self.session,
                "game_id": self.game_id,
                "event": "CHANGE",
                "event_type": f"{team_venue} CHANGE",
                "event_team": data["team"],
                "is_home": data["is_home"],
                "is_away": data["is_away"],
                "team_venue": team_venue,
                "period": period,
                "period_time": data["period_time"],
                "period_seconds": time_seconds,
                "game_seconds": game_seconds(period, time_seconds, self._overtime),
                "description": description,
            }

            # Every player changing, then the forwards, defense and goalies among them, on and off
            for side, side_data in (("on", on_data), ("off", off_data)):
                for group, label in (("ALL", ""), ("F", "_forwards"), ("D", "_defense"), ("G", "_goalie")):
                    prefix = f"change_{side}{label}"
                    players = side_data[group]

                    change_dict[f"{prefix}_count"] = players["count"]
                    change_dict[f"{prefix}_jersey"] = players["jerseys"]
                    change_dict[prefix] = players["names"]
                    change_dict[f"{prefix}_eh_id"] = players["eh_ids"]
                    change_dict[f"{prefix}_api_id"] = players["api_ids"]
                    if group == "ALL":
                        change_dict[f"{prefix}_positions"] = players["positions"]

            final_changes.append(ChangeEvent.model_validate(change_dict).model_dump())

        return final_changes

    @cached_property
    @shared_doc(_GAME_CHANGES_DOC)
    def changes(self) -> list:
        """Changes — docstring lives in _docstrings._GAME_CHANGES_DOC."""
        shifts = self.shifts
        if not shifts:
            return []

        return self._munge_changes(shifts)

    @property
    @shared_doc(_GAME_CHANGES_DF_DOC)
    def changes_df(self) -> pd.DataFrame | pl.DataFrame:
        """changes_df — docstring lives in _docstrings._GAME_CHANGES_DF_DOC."""
        return self._finalize_dataframe(data=self.changes, schema=changes_polars_schema)
