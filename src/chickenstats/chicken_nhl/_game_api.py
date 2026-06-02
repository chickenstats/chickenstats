from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import pandas as pd
from unidecode import unidecode

from chickenstats.chicken_nhl._corrections import api_events_fixes, api_rosters_fixes
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
from chickenstats.chicken_nhl._docstrings import (
    _GAME_API_EVENTS_DF_DOC,
    _GAME_API_EVENTS_DOC,
    _GAME_API_ROSTERS_DF_DOC,
    _GAME_API_ROSTERS_DOC,
    shared_doc,
)
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
    @shared_doc(_GAME_API_EVENTS_DOC)
    def api_events(self) -> list:
        """api_events — docstring lives in _docstrings._GAME_API_EVENTS_DOC."""
        self._fetch_api_data()

        # Build api_id → roster dict for player metadata hydration
        roster_lookup = {x["api_id"]: x for x in self.api_rosters}

        teams_dict = {self.home_team["id"]: self.home_team["abbrev"], self.away_team["id"]: self.away_team["abbrev"]}

        # Transform raw plays into structured event dicts, then apply versioning and Pydantic validation
        assert self.api_response is not None
        event_list = [
            self._munge_single_api_event(event, teams_dict, roster_lookup)
            for event in self.api_response.get("plays", [])
        ]

        return apply_event_versioning(event_list)

    @property
    @shared_doc(_GAME_API_EVENTS_DF_DOC)
    def api_events_df(self) -> pd.DataFrame | pl.DataFrame:
        """api_events_df — docstring lives in _docstrings._GAME_API_EVENTS_DF_DOC."""
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

        # Apply name corrections and resolve the Evolving Hockey ID
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
    @shared_doc(_GAME_API_ROSTERS_DOC)
    def api_rosters(self) -> list:
        """api_rosters — docstring lives in _docstrings._GAME_API_ROSTERS_DOC."""
        if not self.api_response:
            self._fetch_api_data()

        assert self.api_response is not None
        # Transform each rosterSpots entry into a normalized player dict
        players = [self._munge_api_player(player) for player in self.api_response.get("rosterSpots", [])]

        # Apply external fixes for known data gaps (e.g., missing players)
        new_player = api_rosters_fixes(season=self.season, session=self.session, game_id=self.game_id)
        if new_player:
            players.append(APIRosterPlayer.model_validate(new_player).model_dump())

        return sorted(players, key=lambda k: (k["team_venue"], k["player_name"]))

    @property
    @shared_doc(_GAME_API_ROSTERS_DF_DOC)
    def api_rosters_df(self) -> pd.DataFrame | pl.DataFrame:
        """api_rosters_df — docstring lives in _docstrings._GAME_API_ROSTERS_DF_DOC."""
        return self._finalize_dataframe(data=self.api_rosters, schema=api_rosters_polars_schema)
