from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import pandas as pd

from chickenstats.chicken_nhl._game_utils import aggregate_players
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
        """Worker method to transform shifts into changes."""
        changes_map = {}

        # Group all shifts by their start and end times in a single pass
        for shift in shifts:
            period = shift["period"]
            team_venue = shift["team_venue"]

            # Track Change ON
            on_sec = shift.get("start_time_seconds", 0)
            on_key = (period, team_venue, on_sec)

            if on_key not in changes_map:
                changes_map[on_key] = {
                    "on": [],
                    "off": [],
                    "period_time": shift["start_time"],
                    "is_home": shift["is_home"],
                    "is_away": shift["is_away"],
                    "team": shift["team"],
                }
            changes_map[on_key]["on"].append(shift)

            # Track Change OFF
            off_sec = shift.get("end_time_seconds", 0)
            off_key = (period, team_venue, off_sec)

            if off_key not in changes_map:
                changes_map[off_key] = {
                    "on": [],
                    "off": [],
                    "period_time": shift["end_time"],
                    "is_home": shift["is_home"],
                    "is_away": shift["is_away"],
                    "team": shift["team"],
                }
            changes_map[off_key]["off"].append(shift)

        final_changes = []

        sorted_keys = sorted(changes_map.keys(), key=lambda k: (k[0], k[2], 0 if k[1] == "HOME" else 1))

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

            if period == 5 and self.session == "R":
                game_seconds = 3900 + time_seconds
            else:
                game_seconds = (period - 1) * 1200 + time_seconds

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
                "game_seconds": game_seconds,
                "description": description,
                "change_on_count": on_data["ALL"]["count"],
                "change_off_count": off_data["ALL"]["count"],
                "change_on_jersey": on_data["ALL"]["jerseys"],
                "change_on": on_data["ALL"]["names"],
                "change_on_eh_id": on_data["ALL"]["eh_ids"],
                "change_on_api_id": on_data["ALL"]["api_ids"],
                "change_on_positions": on_data["ALL"]["positions"],
                "change_off_jersey": off_data["ALL"]["jerseys"],
                "change_off": off_data["ALL"]["names"],
                "change_off_eh_id": off_data["ALL"]["eh_ids"],
                "change_off_api_id": off_data["ALL"]["api_ids"],
                "change_off_positions": off_data["ALL"]["positions"],
                "change_on_forwards_count": on_data["F"]["count"],
                "change_off_forwards_count": off_data["F"]["count"],
                "change_on_forwards_jersey": on_data["F"]["jerseys"],
                "change_on_forwards": on_data["F"]["names"],
                "change_on_forwards_eh_id": on_data["F"]["eh_ids"],
                "change_on_forwards_api_id": on_data["F"]["api_ids"],
                "change_off_forwards_jersey": off_data["F"]["jerseys"],
                "change_off_forwards": off_data["F"]["names"],
                "change_off_forwards_eh_id": off_data["F"]["eh_ids"],
                "change_off_forwards_api_id": off_data["F"]["api_ids"],
                "change_on_defense_count": on_data["D"]["count"],
                "change_off_defense_count": off_data["D"]["count"],
                "change_on_defense_jersey": on_data["D"]["jerseys"],
                "change_on_defense": on_data["D"]["names"],
                "change_on_defense_eh_id": on_data["D"]["eh_ids"],
                "change_on_defense_api_id": on_data["D"]["api_ids"],
                "change_off_defense_jersey": off_data["D"]["jerseys"],
                "change_off_defense": off_data["D"]["names"],
                "change_off_defense_eh_id": off_data["D"]["eh_ids"],
                "change_off_defense_api_id": off_data["D"]["api_ids"],
                "change_on_goalie_count": on_data["G"]["count"],
                "change_off_goalie_count": off_data["G"]["count"],
                "change_on_goalie_jersey": on_data["G"]["jerseys"],
                "change_on_goalie": on_data["G"]["names"],
                "change_on_goalie_eh_id": on_data["G"]["eh_ids"],
                "change_on_goalie_api_id": on_data["G"]["api_ids"],
                "change_off_goalie_jersey": off_data["G"]["jerseys"],
                "change_off_goalie": off_data["G"]["names"],
                "change_off_goalie_eh_id": off_data["G"]["eh_ids"],
                "change_off_goalie_api_id": off_data["G"]["api_ids"],
            }

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
