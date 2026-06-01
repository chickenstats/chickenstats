from __future__ import annotations

from functools import cached_property

import polars as pl

from chickenstats.chicken_nhl._corrections import rosters_fixes
from chickenstats.chicken_nhl._game_utils import prefetch_concurrent
from chickenstats.chicken_nhl.validation_pydantic import RosterPlayer
from chickenstats.chicken_nhl.validation_polars import rosters_polars_schema
from chickenstats.chicken_nhl._docstrings import _GAME_ROSTERS_DF_DOC, _GAME_ROSTERS_DOC, shared_doc
from chickenstats.chicken_nhl._game_core import _GameBase

model_version = "0.1.1"


class _GameRostersMixin(_GameBase):
    def _combine_rosters(self) -> list:
        """Combine API and HTML rosters into a unified list.

        Called internally by the rosters cached property.

        Examples:
            >>> game = Game(2023020001)
            >>> game.rosters  # fetches and combines in one step
        """
        api_rosters = self.api_rosters
        html_rosters = self.html_rosters

        active_lookup: dict = {}
        scratch_lookup: dict = {}
        for player in html_rosters:
            key = player.get("team_jersey")
            if not key:
                continue
            if player.get("status") == "ACTIVE":
                active_lookup[key] = player
            else:
                scratch_lookup[key] = player

        combined_roster = []
        api_jerseys = set()

        # 1. Hydrate API data with HTML statuses (starter, status, team_name)
        for api_player in api_rosters:
            team_jersey = api_player["team_jersey"]
            api_jerseys.add(team_jersey)

            merged_player = api_player.copy()

            html_match = active_lookup.get(team_jersey) or scratch_lookup.get(team_jersey) or {}
            merged_player["team_name"] = html_match.get("team_name")
            merged_player["status"] = html_match.get("status", "UNKNOWN")
            merged_player["starter"] = html_match.get("starter", 0)

            combined_roster.append(rosters_fixes(self.game_id, merged_player))

        # 2. Catch players found ONLY in the HTML report (e.g., EBUGs and scratches).
        # API rosters never include scratches, so a scratch whose jersey collides with an
        # API player is always a distinct person and must be added unconditionally.
        for html_player in html_rosters:
            if html_player.get("status") == "SCRATCH" or html_player["team_jersey"] not in api_jerseys:
                new_player = html_player.copy()
                new_player["api_id"] = None
                new_player["headshot_url"] = None
                combined_roster.append(rosters_fixes(self.game_id, new_player))

        return combined_roster

    @cached_property
    @shared_doc(_GAME_ROSTERS_DOC)
    def rosters(self) -> list:
        """Rosters — docstring lives in _docstrings._GAME_ROSTERS_DOC."""
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_rosters)
        combined_and_fixed = self._combine_rosters()

        # Pydantic validation
        final = [RosterPlayer.model_construct(**player).model_dump() for player in combined_and_fixed]

        return sorted(final, key=lambda k: (k["team_venue"], k["status"], k["player_name"]))

    @property
    @shared_doc(_GAME_ROSTERS_DF_DOC)
    def rosters_df(self) -> pl.DataFrame:
        """rosters_df — docstring lives in _docstrings._GAME_ROSTERS_DF_DOC."""
        return self._finalize_dataframe(data=self.rosters, schema=rosters_polars_schema)
