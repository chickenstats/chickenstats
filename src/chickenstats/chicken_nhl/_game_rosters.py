from __future__ import annotations

from functools import cached_property

import polars as pl

from chickenstats.chicken_nhl._fixes import rosters_fixes
from chickenstats.chicken_nhl._game_utils import prefetch_concurrent
from chickenstats.chicken_nhl.validation_pydantic import RosterPlayer
from chickenstats.chicken_nhl.validation_polars import rosters_polars_schema
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

        # 3. Hydrate API data with HTML statuses
        for api_player in api_rosters:
            team_jersey = api_player["team_jersey"]
            api_jerseys.add(team_jersey)

            merged_player = api_player.copy()

            html_match = active_lookup.get(team_jersey) or scratch_lookup.get(team_jersey) or {}
            merged_player["team_name"] = html_match.get("team_name")
            merged_player["status"] = html_match.get("status", "UNKNOWN")
            merged_player["starter"] = html_match.get("starter", 0)

            combined_roster.append(rosters_fixes(self.game_id, merged_player))

        # 4. Catch players found ONLY in the HTML report (e.g., EBUGs and scratches).
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
    def rosters(self) -> list:
        """List of players scraped from API & HTML endpoints. Returns a dictionary of players with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).rosters_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            api_id (int | None):
                Player's NHL API ID, e.g., 8476887
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE
            headshot_url (str | None):
                URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.rosters

        """
        prefetch_concurrent(self._fetch_api_data, self._fetch_html_rosters)
        combined_and_fixed = self._combine_rosters()

        # 2. Final Pydantic validation
        final = [RosterPlayer.model_construct(**player).model_dump() for player in combined_and_fixed]

        # 3. Sort and return
        return sorted(final, key=lambda k: (k["team_venue"], k["status"], k["player_name"]))

    @property
    def rosters_df(self) -> pl.DataFrame:
        """Pandas Dataframe of players scraped from API & HTML endpoints.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_name (str):
                Full team name, e.g., NASHVILLE PREDATORS
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            api_id (int | None):
                Player's NHL API ID, e.g., 8476887
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            jersey (int):
                Player's jersey number, e.g., 9
            position (str):
                Player's position, e.g., L
            starter (int):
                Whether the player started the game, e.g., 0
            status (str):
                Whether player is active or scratched, e.g., ACTIVE
            headshot_url (str | None):
                URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.rosters_df

        """
        return self._finalize_dataframe(data=self.rosters, schema=rosters_polars_schema)
