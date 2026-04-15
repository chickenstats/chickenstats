from __future__ import annotations

from functools import cached_property

import pandas as pd
import polars as pl
from unidecode import unidecode

from chickenstats.chicken_nhl._fixes import api_events_fixes, api_rosters_fixes
from chickenstats.chicken_nhl._game_utils import (
    apply_event_versioning,
    handle_penalty_details,
    handle_scoring_details,
    map_player_metadata,
    parse_time,
)
from chickenstats.chicken_nhl._player_names import correct_api_names_dict, correct_names_dict
from chickenstats.chicken_nhl.validation_pydantic import APIRosterPlayer
from chickenstats.chicken_nhl.validation_polars import api_events_polars_schema, api_rosters_polars_schema
from chickenstats.chicken_nhl._game_core import _GameBase

model_version = "0.1.1"


class _GameAPIMixin(_GameBase):
    def _munge_single_api_event(self, event: dict, teams: dict, rosters: dict) -> dict:
        """Worker method to process one raw play using pattern matching."""
        period = int(event["periodDescriptor"]["number"])
        period_type = event["periodDescriptor"]["periodType"]
        period_seconds = parse_time(event["timeInPeriod"])

        # Standardize game clock logic
        if self.session == "R" and period == 5:
            game_seconds = 3900
        else:
            game_seconds = ((period - 1) * 1200) + period_seconds

        # Initialize the core event dictionary
        event_info = {
            "season": self.season,
            "session": self.session,
            "game_id": self.game_id,
            "event_idx": event["sortOrder"],
            "period": period,
            "period_type": period_type,
            "period_seconds": period_seconds,
            "game_seconds": game_seconds,
            "event": event["typeDescKey"],
            "event_code": event["typeCode"],
            "strength": event.get("situationCode"),
            "home_team_defending_side": event.get("homeTeamDefendingSide"),
        }

        event_details = event.get("details", {})
        if event_details:
            event_info.update(
                {
                    "event_team": teams.get(event_details.get("eventOwnerTeamId")),
                    "coords_x": event_details.get("xCoord"),
                    "coords_y": event_details.get("yCoord"),
                    "zone": event_details.get("zoneCode"),
                    "event_team_id": event_details.get("eventOwnerTeamId"),
                }
            )

            # Use Pattern Matching for event-specific details
            match event_info["event"]:
                case "faceoff":
                    event_info.update(
                        {
                            "event": "FAC",
                            "player_1_api_id": event_details["winningPlayerId"],
                            "player_1_type": "WINNER",
                            "player_2_api_id": event_details["losingPlayerId"],
                            "player_2_type": "LOSER",
                        }
                    )
                case "hit":
                    event_info.update(
                        {
                            "event": "HIT",
                            "player_1_api_id": event_details["hittingPlayerId"],
                            "player_1_type": "HITTER",
                            "player_2_api_id": event_details["hitteePlayerId"],
                            "player_2_type": "HITTEE",
                        }
                    )
                case "giveaway" | "takeaway":
                    event_info.update(
                        {
                            "event": "GIVE" if event_info["event"] == "giveaway" else "TAKE",
                            "player_1_api_id": event_details["playerId"],
                            "player_1_type": "GIVER" if event_info["event"] == "giveaway" else "TAKER",
                        }
                    )
                case "shot-on-goal" | "missed-shot" | "goal" | "failed-shot-attempt":
                    event_info.update(handle_scoring_details(event_info["event"], event_details))
                case "blocked-shot":
                    event_info.update(
                        {
                            "event": "BLOCK",
                            "player_1_api_id": event_details.get("blockingPlayerId"),
                            "player_1_type": "BLOCKER",
                            "player_2_api_id": event_details["shootingPlayerId"],
                            "player_2_type": "SHOOTER",
                        }
                    )
                case "penalty":
                    event_info.update(handle_penalty_details(event_details))
                case "stoppage":
                    event_info.update(
                        {
                            "event": "STOP",
                            "stoppage_reason": event_details["reason"].upper().replace("-", " "),
                            "stoppage_reason_secondary": event_details.get("secondaryReason", "")
                            .upper()
                            .replace("-", " "),
                        }
                    )
                case "period-start" | "period-end" | "game-end" | "shootout-complete" | "delayed-penalty":
                    codes = {
                        "period-start": "PSTR",
                        "period-end": "PEND",
                        "game-end": "GEND",
                        "shootout-complete": "SOC",
                        "delayed-penalty": "DELPEN",
                    }
                    event_info["event"] = codes[event_info["event"]]

        # Apply external fixes and map roster metadata (names, positions, eh_ids)
        event_info = api_events_fixes(self.game_id, event_info)
        return map_player_metadata(event_info, rosters)

    @cached_property
    def api_events(self) -> list:
        """List of events scraped from API endpoint. Each event is a dictionary with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).api_events_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 689
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            event_code (str):
                Code to indicate type of event that occured, e.g., 505
            description (str | None):
                Description of the event, e.g., None
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., D
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_team_jersey (str):
                Combination of team and jersey used for player identification purposes, e.g, NSH35
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_2_api_id (str | None):
                NHL API ID for player_2, e.g., None
            player_2_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            player_3_api_id (str | None):
                NHL API ID for player_3, e.g., None
            player_3_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            strength (int):
                Code to indication strength state, e.g., 1560
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            miss_reason (str | None):
                Reason shot missed, e.g., None
            opp_goalie (str | None):
                Opposing goalie, e.g., None
            opp_goalie_eh_id (str | None):
                Evolving Hockey ID for opposing goalie, e.g., None
            opp_goalie_api_id (str | None):
                NHL API ID for opposing goalie, e.g., None
            opp_goalie_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            event_team_id (int):
                NHL ID for the event team, e.g., 18
            stoppage_reason (str | None):
                Reason the play was stopped, e.g., None
            stoppage_reason_secondary (str | None):
                Secondary reason play was stopped, e.g., None
            penalty_type (str | None):
                Type of penalty taken, e.g., None
            penalty_reason (str | None):
                Reason for the penalty, e.g., None
            penalty_duration (int | None):
                Duration of the penalty, e.g., None
            home_team_defending_side (str):
                Side of the ice the home team is defending, e.g., right
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.api_events

        """
        self._fetch_api_data()

        # Dependency: Accessing self.api_rosters triggers its own cached logic
        roster_lookup = {x["api_id"]: x for x in self.api_rosters}

        teams_dict = {self.home_team["id"]: self.home_team["abbrev"], self.away_team["id"]: self.away_team["abbrev"]}

        # Step 1: Transform raw plays into structured event dictionaries
        assert self.api_response is not None
        event_list = [
            self._munge_single_api_event(event, teams_dict, roster_lookup)
            for event in self.api_response.get("plays", [])
        ]

        # Step 2: Handle simultaneous versioning and Pydantic validation
        return apply_event_versioning(event_list)

    @property
    def api_events_df(self) -> pd.DataFrame | pl.DataFrame:
        """Pandas Dataframe of events scraped from API endpoint.

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            event_idx (int):
                Index ID for event, e.g., 689
            period (int):
                Period number of the event, e.g., 3
            period_seconds (int):
                Time elapsed in the period, in seconds, e.g., 1178
            game_seconds (int):
                Time elapsed in the game, in seconds, e.g., 3578
            event_team (str):
                Team that performed the action for the event, e.g., NSH
            event (str):
                Type of event that occurred, e.g., GOAL
            event_code (str):
                Code to indicate type of event that occured, e.g., 505
            description (str | None):
                Description of the event, e.g., None
            coords_x (int):
                x-coordinates where the event occurred, e.g, -96
            coords_y (int):
                y-coordinates where the event occurred, e.g., 11
            zone (str):
                Zone where the event occurred, relative to the event team, e.g., D
            player_1 (str):
                Player that performed the action, e.g., PEKKA RINNE
            player_1_eh_id (str):
                Evolving Hockey ID for player_1, e.g., PEKKA.RINNE
            player_1_position (str):
                Position player_1 plays, e.g., G
            player_1_type (str):
                Type of player, e.g., GOAL SCORER
            player_1_api_id (int):
                NHL API ID for player_1, e.g., 8471469
            player_1_team_jersey (str):
                Combination of team and jersey used for player identification purposes, e.g, NSH35
            player_2 (str | None):
                Player that performed the action, e.g., None
            player_2_eh_id (str | None):
                Evolving Hockey ID for player_2, e.g., None
            player_2_position (str | None):
                Position player_2 plays, e.g., None
            player_2_type (str | None):
                Type of player, e.g., None
            player_2_api_id (str | None):
                NHL API ID for player_2, e.g., None
            player_2_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            player_3 (str | None):
                Player that performed the action, e.g., None
            player_3_eh_id (str | None):
                Evolving Hockey ID for player_3, e.g., None
            player_3_position (str | None):
                Position player_3 plays, e.g., None
            player_3_type (str | None):
                Type of player, e.g., None
            player_3_api_id (str | None):
                NHL API ID for player_3, e.g., None
            player_3_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            strength (int):
                Code to indication strength state, e.g., 1560
            shot_type (str | None):
                Type of shot taken, if event is a shot, e.g., WRIST
            miss_reason (str | None):
                Reason shot missed, e.g., None
            opp_goalie (str | None):
                Opposing goalie, e.g., None
            opp_goalie_eh_id (str | None):
                Evolving Hockey ID for opposing goalie, e.g., None
            opp_goalie_api_id (str | None):
                NHL API ID for opposing goalie, e.g., None
            opp_goalie_team_jersey (str | None):
                Combination of team and jersey used for player identification purposes, e.g, None
            event_team_id (int):
                NHL ID for the event team, e.g., 18
            stoppage_reason (str | None):
                Reason the play was stopped, e.g., None
            stoppage_reason_secondary (str | None):
                Secondary reason play was stopped, e.g., None
            penalty_type (str | None):
                Type of penalty taken, e.g., None
            penalty_reason (str | None):
                Reason for the penalty, e.g., None
            penalty_duration (int | None):
                Duration of the penalty, e.g., None
            home_team_defending_side (str):
                Side of the ice the home team is defending, e.g., right
            version (int):
                Increases with simultaneous events, used for combining events in the scraper, e.g., 1

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.api_events_df
        """
        return self._finalize_dataframe(data=self.api_events, schema=api_events_polars_schema)

    def _munge_api_player(self, player: dict) -> dict:
        """Worker method to clean a single API player record."""
        # Use a mapping for teams to avoid 'if' blocks
        team_map = {
            self.home_team["id"]: {"venue": "HOME", "team": self.home_team["abbrev"]},
            self.away_team["id"]: {"venue": "AWAY", "team": self.away_team["abbrev"]},
        }
        team_info = team_map[player["teamId"]]

        # Clean strings and generate IDs
        first_name = unidecode(player["firstName"]["default"]).upper().strip()
        last_name = unidecode(player["lastName"]["default"]).upper().strip()
        player_name = f"{first_name} {last_name}"

        # Apply corrections from your helper dictionaries
        player_name = correct_names_dict.get(player_name, player_name)
        eh_id = f"{player_name.split(' ', 1)[0]}.{player_name.split(' ', 1)[1]}".replace("..", ".")
        eh_id = correct_api_names_dict.get(player["playerId"], eh_id)

        # Build and validate schema
        player_info = {
            "season": self.season,
            "session": self.session,
            "game_id": self.game_id,
            "team": team_info["team"],
            "team_venue": team_info["venue"],
            "player_name": player_name,
            "first_name": first_name,
            "last_name": last_name,
            "api_id": player["playerId"],
            "eh_id": correct_api_names_dict.get(player["playerId"], eh_id),
            "team_jersey": team_info["team"] + str(player["sweaterNumber"]),
            "jersey": player["sweaterNumber"],
            "position": player["positionCode"],
            "headshot_url": player.get("headshot", ""),
        }
        return APIRosterPlayer.model_validate(player_info).model_dump()

    @cached_property
    def api_rosters(self) -> list:
        """List of players scraped from API endpoint. Returns a dictionary of players with the below keys.

        Note:
            You can return any of the properties as a Pandas DataFrame by appending '_df' to the property, e.g.,
            `Game(2019020684).api_rosters_df`

        Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            first_name (str):
                Player's first name, e.g., FILIP
            last_name (str):
                Player's last name, e.g., FORSBERG
            headshot_url (str):
                URL to retreive player's headshot

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property
            >>> game.api_rosters
        """
        if not self.api_response:
            self._fetch_api_data()

        assert self.api_response is not None
        # Transformation Pipeline
        players = [self._munge_api_player(player) for player in self.api_response.get("rosterSpots", [])]

        # Apply external fixes
        new_player = api_rosters_fixes(season=self.season, session=self.session, game_id=self.game_id)
        if new_player:
            players.append(APIRosterPlayer.model_validate(new_player).model_dump())

        return sorted(players, key=lambda k: (k["team_venue"], k["player_name"]))

    @property
    def api_rosters_df(self) -> pd.DataFrame | pl.DataFrame:
        """Pandas Dataframe of players scraped from API endpoint.

        Returns:
            Returns:
            season (int):
                Season as 8-digit number, e.g., 20192020 for 2019-20 season
            session (str):
                Whether game is regular season, playoffs, or pre-season, e.g., R
            game_id (int):
                Unique game ID assigned by the NHL, e.g., 2019020684
            team (str):
                Team name of the player, e.g., NSH
            team_venue (str):
                Whether team is home or away, e.g., AWAY
            player_name (str):
                Player's name, e.g., FILIP FORSBERG
            eh_id (str):
                Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
            api_id (str):
                NHL API ID for the player, e.g., 8476887
            team_jersey (str):
                Team and jersey combination used for player identification, e.g., NSH9
            position (str):
                Player's position, e.g., L
            first_name (str):
                Player's first name, e.g., FILIP
            last_name (str):
                Player's last name, e.g., FORSBERG
            headshot_url (str):
                URL to retreive player's headshot

        Examples:
            First, instantiate the class with a game ID
            >>> game_id = 2019020684
            >>> game = Game(game_id)

            Then you can access the property as a Pandas DataFrame
            >>> game.api_rosters_df
        """
        df = self._finalize_dataframe(data=self.api_rosters, schema=api_rosters_polars_schema)

        return df
