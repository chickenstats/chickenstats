from pydantic import BaseModel, field_validator
import datetime as dt

from pandera import Column, DataFrameSchema, Parser
import numpy as np


class APIEvent(BaseModel):
    """Pydantic model for validating API event data."""

    season: int
    session: str
    game_id: int
    event_idx: int
    period: int
    period_type: str
    period_seconds: int
    game_seconds: int
    event_team: str | None = None
    event: str
    event_code: int
    description: str | None = None
    coords_x: int | None = None
    coords_y: int | None = None
    zone: str | None = None
    player_1: str | None = None
    player_1_eh_id: str | None = None
    player_1_position: str | None = None
    player_1_type: str | None = None
    player_1_api_id: int | str | None = None
    player_1_team_jersey: str | None = None
    player_2: str | None = None
    player_2_eh_id: str | None = None
    player_2_position: str | None = None
    player_2_type: str | None = None
    player_2_api_id: int | str | None = None
    player_2_team_jersey: str | None = None
    player_3: str | None = None
    player_3_eh_id: str | None = None
    player_3_position: str | None = None
    player_3_type: str | None = None
    player_3_api_id: int | str | None = None
    player_3_team_jersey: str | None = None
    strength: int | None = None
    shot_type: str | None = None
    miss_reason: str | None = None
    opp_goalie: str | None = None
    opp_goalie_eh_id: str | None = None
    opp_goalie_api_id: int | str | None = None
    opp_goalie_team_jersey: str | None = None
    event_team_id: int | None = None
    stoppage_reason: str | None = None
    stoppage_reason_secondary: str | None = None
    penalty_type: str | None = None
    penalty_reason: str | None = None
    penalty_duration: int | None = None
    home_team_defending_side: str | None = None
    version: int


class APIRosterPlayer(BaseModel):
    """Pydantic model for validating API roster data."""

    season: int
    session: str
    game_id: int
    team: str
    team_venue: str
    player_name: str
    eh_id: str
    api_id: int
    team_jersey: str
    jersey: int
    position: str
    first_name: str
    last_name: str
    headshot_url: str


class ChangeEvent(BaseModel):
    """Pydantic model for validating changes data."""

    season: int
    session: str
    game_id: int
    event_team: str
    event: str
    event_type: str
    description: str
    period: int
    period_seconds: int
    game_seconds: int
    change_on_count: int
    change_off_count: int
    change_on: list[str] | str = ""
    change_on_jersey: list[str] | str = ""
    change_on_eh_id: list[str] | str = ""
    change_on_api_id: list[str] | str = ""
    change_on_positions: list[str] | str = ""
    change_off: list[str] | str = ""
    change_off_jersey: list[str] | str = ""
    change_off_eh_id: list[str] | str = ""
    change_off_api_id: list[str] | str = ""
    change_off_positions: list[str] | str = ""
    change_on_forwards_count: int
    change_off_forwards_count: int
    change_on_forwards: list[str] | str = ""
    change_on_forwards_jersey: list[str] | str = ""
    change_on_forwards_eh_id: list[str] | str = ""
    change_on_forwards_api_id: list[str] | str = ""
    change_off_forwards: list[str] | str = ""
    change_off_forwards_jersey: list[str] | str = ""
    change_off_forwards_eh_id: list[str] | str = ""
    change_off_forwards_api_id: list[str] | str = ""
    change_on_defense_count: int
    change_off_defense_count: int
    change_on_defense: list[str] | str = ""
    change_on_defense_jersey: list[str] | str = ""
    change_on_defense_eh_id: list[str] | str = ""
    change_on_defense_api_id: list[str] | str = ""
    change_off_defense: list[str] | str = ""
    change_off_defense_jersey: list[str] | str = ""
    change_off_defense_eh_id: list[str] | str = ""
    change_off_defense_api_id: list[str] | str = ""
    change_on_goalie_count: int
    change_off_goalie_count: int
    change_on_goalie: list[str] | str = ""
    change_on_goalie_jersey: list[str] | str = ""
    change_on_goalie_eh_id: list[str] | str = ""
    change_on_goalie_api_id: list[str] | str = ""
    change_off_goalie: list[str] | str = ""
    change_off_goalie_jersey: list[str] | str = ""
    change_off_goalie_eh_id: list[str] | str = ""
    change_off_goalie_api_id: list[str] | str = ""
    is_home: int
    is_away: int
    team_venue: str

    @field_validator(
        "change_on_jersey",
        "change_on",
        "change_on_eh_id",
        "change_on_api_id",
        "change_on_positions",
        "change_off_jersey",
        "change_off",
        "change_off_eh_id",
        "change_off_api_id",
        "change_off_positions",
        "change_on_forwards_jersey",
        "change_on_forwards",
        "change_on_forwards_eh_id",
        "change_on_forwards_api_id",
        "change_off_forwards_jersey",
        "change_off_forwards",
        "change_off_forwards_eh_id",
        "change_off_forwards_api_id",
        "change_on_defense_jersey",
        "change_on_defense",
        "change_on_defense_eh_id",
        "change_on_defense_api_id",
        "change_off_defense_jersey",
        "change_off_defense",
        "change_off_defense_eh_id",
        "change_off_defense_api_id",
        "change_on_goalie_jersey",
        "change_on_goalie",
        "change_on_goalie_eh_id",
        "change_on_goalie_api_id",
        "change_off_goalie_jersey",
        "change_off_goalie",
        "change_off_goalie_eh_id",
        "change_off_goalie_api_id",
        mode="after",
    )
    @classmethod
    def fix_list(cls, v):
        """Converts lists into strings."""
        if v and isinstance(v, list) is True:
            return ", ".join(v)

        elif not v:
            return None

        else:
            return v


class HTMLEvent(BaseModel):
    """Class for validating HTML event data."""

    season: int
    session: str
    game_id: int
    event_idx: int
    period: int
    period_time: str
    period_seconds: int
    game_seconds: int
    event_team: str | None = ""
    event: str
    description: str | None = None
    player_1: str | None = None
    player_1_eh_id: str | None = None
    player_1_position: str | None = None
    player_2: str | None = None
    player_2_eh_id: str | None = None
    player_2_position: str | None = None
    player_3: str | None = None
    player_3_eh_id: str | None = None
    player_3_position: str | None = None
    zone: str | None = None
    shot_type: str | None = None
    pbp_distance: int | None = None
    penalty_length: int | None = None
    penalty: str | None = None
    strength: str | None = None
    away_skaters: str | None = None
    home_skaters: str | None = None
    version: int

    @field_validator("strength", "away_skaters", "home_skaters")
    @classmethod
    def fix_strength(cls, v):
        """Changes blank strings into None objects."""
        if v == " ":
            new_v = None

        else:
            new_v = v

        return new_v


class HTMLRosterPlayer(BaseModel):
    """Pydantic model for validating HTML roster data."""

    season: int
    session: str
    game_id: int
    team: str
    team_name: str
    team_venue: str
    player_name: str
    eh_id: str
    team_jersey: str
    jersey: int
    position: str
    starter: int
    status: str


class RosterPlayer(BaseModel):
    """Pydantic model for validating roster data."""

    season: int
    session: str
    game_id: int
    team: str
    team_name: str
    team_venue: str
    player_name: str
    api_id: int | None
    eh_id: str
    team_jersey: str
    jersey: int
    position: str
    starter: int
    status: str
    headshot_url: str | None


class PlayerShift(BaseModel):
    """Pydantic model for validating shifts data."""

    season: int
    session: str
    game_id: int
    team: str
    team_name: str
    player_name: str
    eh_id: str
    api_id: int
    team_jersey: str
    position: str
    jersey: int
    shift_count: int
    period: int
    start_time: str
    end_time: str
    duration: str
    start_time_seconds: int
    end_time_seconds: int
    duration_seconds: int
    shift_start: str
    shift_end: str
    goalie: int
    is_home: int
    is_away: int
    team_venue: str


class PBPEvent(BaseModel):
    """Pydantic model for validating play-by-play data."""

    id: int
    season: int
    session: str
    game_id: int
    game_date: str
    event_idx: int
    period: int
    period_seconds: int
    game_seconds: int
    strength_state: str
    event_team: str | None = None
    opp_team: str | None = None
    event: str
    description: str
    zone: str | None = None
    coords_x: int | None = None
    coords_y: int | None = None
    danger: int | None = None
    high_danger: int | None = None
    player_1: str | None = None
    player_1_eh_id: str | None = None
    player_1_eh_id_api: str | None = None
    player_1_api_id: int | str | None = None
    player_1_position: str | None = None
    player_1_type: str | None = None
    player_2: str | None = None
    player_2_eh_id: str | None = None
    player_2_eh_id_api: str | None = None
    player_2_api_id: int | str | None = None
    player_2_position: str | None = None
    player_2_type: str | None = None
    player_3: str | None = None
    player_3_eh_id: str | None = None
    player_3_eh_id_api: str | None = None
    player_3_api_id: int | str | None = None
    player_3_position: str | None = None
    player_3_type: str | None = None
    score_state: str
    score_diff: int
    forwards_percent: float = 0
    opp_forwards_percent: float = 0
    shot_type: str | None = None
    event_length: int
    event_distance: float | None = None
    pbp_distance: int | None = None
    event_angle: float | None = None
    penalty: str | None = None
    penalty_length: int | None = None
    home_score: int
    home_score_diff: int
    away_score: int
    away_score_diff: int
    is_home: int
    is_away: int
    home_team: str
    away_team: str
    home_skaters: int
    away_skaters: int
    home_on: list | str | None = None
    home_on_eh_id: list | str | None = None
    home_on_api_id: list | str | None = None
    home_on_positions: list | str | None = None
    away_on: list | str | None = None
    away_on_eh_id: list | str | None = None
    away_on_api_id: list | str | None = None
    away_on_positions: list | str | None = None
    event_team_skaters: int | None = None
    teammates: list | str | None = None
    teammates_eh_id: list | str | None = None
    teammates_api_id: list | str | None = None
    teammates_positions: list | str | None = None
    own_goalie: list | str | None = None
    own_goalie_eh_id: list | str | None = None
    own_goalie_api_id: list | str | None = None
    forwards: list | str | None = None
    forwards_eh_id: list | str | None = None
    forwards_api_id: list | str | None = None
    forwards_count: int | None = None
    defense: list | str | None = None
    defense_eh_id: list | str | None = None
    defense_api_id: list | str | None = None
    defense_count: int | None = None
    opp_strength_state: str | None = None
    opp_score_state: str | None = None
    opp_score_diff: int | None = None
    opp_team_skaters: int | None = None
    opp_team_on: list | str | None = None
    opp_team_on_eh_id: list | str | None = None
    opp_team_on_api_id: list | str | None = None
    opp_team_on_positions: list | str | None = None
    opp_goalie: list | str | None = None
    opp_goalie_eh_id: list | str | None = None
    opp_goalie_api_id: list | str | None = None
    opp_forwards: list | str | None = None
    opp_forwards_eh_id: list | str | None = None
    opp_forwards_api_id: list | str | None = None
    opp_forwards_count: int | None = None
    opp_defense: list | str | None = None
    opp_defense_eh_id: list | str | None = None
    opp_defense_api_id: list | str | None = None
    opp_defense_count: int | None = None
    home_forwards: list | str | None = None
    home_forwards_eh_id: list | str | None = None
    home_forwards_api_id: list | str | None = None
    home_forwards_count: int | None = None
    home_forwards_percent: float = 0
    home_defense: list | str | None = None
    home_defense_eh_id: list | str | None = None
    home_defense_api_id: list | str | None = None
    home_defense_count: int | None = None
    home_goalie: list | str | None = None
    home_goalie_eh_id: list | str | None = None
    home_goalie_api_id: list | str | None = None
    away_forwards: list | str | None = None
    away_forwards_eh_id: list | str | None = None
    away_forwards_api_id: list | str | None = None
    away_forwards_count: int | None = None
    away_forwards_percent: float = 0
    away_defense: list | str | None = None
    away_defense_eh_id: list | str | None = None
    away_defense_api_id: list | str | None = None
    away_defense_count: int | None = None
    away_goalie: list | str | None = None
    away_goalie_eh_id: list | str | None = None
    away_goalie_api_id: list | str | None = None
    change_on_count: int | None = None
    change_off_count: int | None = None
    change_on: list | str | None = None
    change_on_eh_id: list | str | None = None
    change_on_api_id: list | str | None = None
    change_on_positions: list | str | None = None
    change_off: list | str | None = None
    change_off_eh_id: list | str | None = None
    change_off_api_id: list | str | None = None
    change_off_positions: list | str | None = None
    change_on_forwards_count: int | None = None
    change_off_forwards_count: int | None = None
    change_on_forwards: list | str | None = None
    change_on_forwards_eh_id: list | str | None = None
    change_on_forwards_api_id: list | str | None = None
    change_off_forwards: list | str | None = None
    change_off_forwards_eh_id: list | str | None = None
    change_off_forwards_api_id: list | str | None = None
    change_on_defense_count: int | None = None
    change_off_defense_count: int | None = None
    change_on_defense: list | str | None = None
    change_on_defense_eh_id: list | str | None = None
    change_on_defense_api_id: list | str | None = None
    change_off_defense: list | str | None = None
    change_off_defense_eh_id: list | str | None = None
    change_off_defense_api_id: list | str | None = None
    change_on_goalie_count: int | None = None
    change_off_goalie_count: int | None = None
    change_on_goalie: list | str | None = None
    change_on_goalie_eh_id: list | str | None = None
    change_on_goalie_api_id: list | str | None = None
    change_off_goalie: list | str | None = None
    change_off_goalie_eh_id: list | str | None = None
    change_off_goalie_api_id: list | str | None = None
    goal: int = 0
    hd_goal: int = 0
    shot: int = 0
    hd_shot: int = 0
    miss: int = 0
    hd_miss: int = 0
    fenwick: int = 0
    hd_fenwick: int = 0
    corsi: int = 0
    block: int = 0
    teammate_block: int = 0
    hit: int = 0
    give: int = 0
    take: int = 0
    fac: int = 0
    penl: int = 0
    change: int = 0
    stop: int = 0
    chl: int = 0
    ozf: int = 0
    nzf: int = 0
    dzf: int = 0
    ozc: int = 0
    nzc: int = 0
    dzc: int = 0
    otf: int = 0
    pen0: int = 0
    pen2: int = 0
    pen4: int = 0
    pen5: int = 0
    pen10: int = 0

    @field_validator("*", mode="before")
    @classmethod
    def invalid_strings(cls, v):
        """Changes blank strings into None."""
        if v == "" or v == " " or v == "nan":
            return None

        else:
            return v

    @field_validator(
        "home_on",
        "home_on_eh_id",
        "home_on_api_id",
        "home_on_positions",
        "home_forwards",
        "home_forwards_eh_id",
        "home_forwards_api_id",
        "home_defense",
        "home_defense_eh_id",
        "home_defense_api_id",
        "home_goalie",
        "home_goalie_eh_id",
        "home_goalie_api_id",
        "away_on",
        "away_on_eh_id",
        "away_on_api_id",
        "away_on_positions",
        "away_forwards",
        "away_forwards_eh_id",
        "away_forwards_api_id",
        "away_defense",
        "away_defense_eh_id",
        "away_defense_api_id",
        "away_goalie",
        "away_goalie_eh_id",
        "away_goalie_api_id",
        "teammates",
        "teammates_eh_id",
        "teammates_api_id",
        "teammates_positions",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "opp_team_on",
        "opp_team_on_eh_id",
        "opp_team_on_api_id",
        "opp_team_on_positions",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "change_on",
        "change_on_eh_id",
        "change_on_api_id",
        "change_on_positions",
        "change_off",
        "change_off_eh_id",
        "change_off_api_id",
        "change_off_positions",
        "change_on_forwards",
        "change_on_forwards_eh_id",
        "change_on_forwards_api_id",
        "change_off_forwards",
        "change_off_forwards_eh_id",
        "change_off_forwards_api_id",
        "change_on_defense",
        "change_on_defense_eh_id",
        "change_off_defense",
        "change_off_defense_eh_id",
        "change_off_defense_api_id",
        "change_on_goalie",
        "change_on_goalie_eh_id",
        "change_on_goalie_api_id",
        "change_off_goalie",
        "change_off_goalie_eh_id",
        "change_off_goalie_api_id",
        mode="before",
    )
    @classmethod
    def fix_list(cls, v):
        """Converts lists into strings."""
        if v and isinstance(v, list) is True:
            return ", ".join(v)

        elif not v:
            return None

        else:
            return v

    @field_validator(
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "home_goalie",
        "home_goalie_eh_id",
        "home_goalie_api_id",
        "away_goalie",
        "away_goalie_eh_id",
        "away_goalie_api_id",
        mode="before",
    )
    @classmethod
    def fix_goalies(cls, v):
        """If goalie is None, converts to EMPTY NET."""
        if v is None:
            return "EMPTY NET"

        else:
            return v


class PBPEventExt(BaseModel):
    """Pydantic model for validating play-by-play data."""

    id: int
    event_idx: int
    event_on_1: str | None = None
    event_on_1_eh_id: str | None = None
    event_on_1_api_id: str | None = None
    event_on_1_pos: str | None = None
    event_on_2: str | None = None
    event_on_2_eh_id: str | None = None
    event_on_2_api_id: str | None = None
    event_on_2_pos: str | None = None
    event_on_3: str | None = None
    event_on_3_eh_id: str | None = None
    event_on_3_api_id: str | None = None
    event_on_3_pos: str | None = None
    event_on_4: str | None = None
    event_on_4_eh_id: str | None = None
    event_on_4_api_id: str | None = None
    event_on_4_pos: str | None = None
    event_on_5: str | None = None
    event_on_5_eh_id: str | None = None
    event_on_5_api_id: str | None = None
    event_on_5_pos: str | None = None
    event_on_6: str | None = None
    event_on_6_eh_id: str | None = None
    event_on_6_api_id: str | None = None
    event_on_6_pos: str | None = None
    event_on_7: str | None = None
    event_on_7_eh_id: str | None = None
    event_on_7_api_id: str | None = None
    event_on_7_pos: str | None = None
    opp_on_1: str | None = None
    opp_on_1_eh_id: str | None = None
    opp_on_1_api_id: str | None = None
    opp_on_1_pos: str | None = None
    opp_on_2: str | None = None
    opp_on_2_eh_id: str | None = None
    opp_on_2_api_id: str | None = None
    opp_on_2_pos: str | None = None
    opp_on_3: str | None = None
    opp_on_3_eh_id: str | None = None
    opp_on_3_api_id: str | None = None
    opp_on_3_pos: str | None = None
    opp_on_4: str | None = None
    opp_on_4_eh_id: str | None = None
    opp_on_4_api_id: str | None = None
    opp_on_4_pos: str | None = None
    opp_on_5: str | None = None
    opp_on_5_eh_id: str | None = None
    opp_on_5_api_id: str | None = None
    opp_on_5_pos: str | None = None
    opp_on_6: str | None = None
    opp_on_6_eh_id: str | None = None
    opp_on_6_api_id: str | None = None
    opp_on_6_pos: str | None = None
    opp_on_7: str | None = None
    opp_on_7_eh_id: str | None = None
    opp_on_7_api_id: str | None = None
    opp_on_7_pos: str | None = None
    change_on_1: str | None = None
    change_on_1_eh_id: str | None = None
    change_on_1_api_id: str | None = None
    change_on_1_pos: str | None = None
    change_on_2: str | None = None
    change_on_2_eh_id: str | None = None
    change_on_2_api_id: str | None = None
    change_on_2_pos: str | None = None
    change_on_3: str | None = None
    change_on_3_eh_id: str | None = None
    change_on_3_api_id: str | None = None
    change_on_3_pos: str | None = None
    change_on_4: str | None = None
    change_on_4_eh_id: str | None = None
    change_on_4_api_id: str | None = None
    change_on_4_pos: str | None = None
    change_on_5: str | None = None
    change_on_5_eh_id: str | None = None
    change_on_5_api_id: str | None = None
    change_on_5_pos: str | None = None
    change_on_6: str | None = None
    change_on_6_eh_id: str | None = None
    change_on_6_api_id: str | None = None
    change_on_6_pos: str | None = None
    change_on_7: str | None = None
    change_on_7_eh_id: str | None = None
    change_on_7_api_id: str | None = None
    change_on_7_pos: str | None = None
    change_off_1: str | None = None
    change_off_1_eh_id: str | None = None
    change_off_1_api_id: str | None = None
    change_off_1_pos: str | None = None
    change_off_2: str | None = None
    change_off_2_eh_id: str | None = None
    change_off_2_api_id: str | None = None
    change_off_2_pos: str | None = None
    change_off_3: str | None = None
    change_off_3_eh_id: str | None = None
    change_off_3_api_id: str | None = None
    change_off_3_pos: str | None = None
    change_off_4: str | None = None
    change_off_4_eh_id: str | None = None
    change_off_4_api_id: str | None = None
    change_off_4_pos: str | None = None
    change_off_5: str | None = None
    change_off_5_eh_id: str | None = None
    change_off_5_api_id: str | None = None
    change_off_5_pos: str | None = None
    change_off_6: str | None = None
    change_off_6_eh_id: str | None = None
    change_off_6_api_id: str | None = None
    change_off_6_pos: str | None = None
    change_off_7: str | None = None
    change_off_7_eh_id: str | None = None
    change_off_7_api_id: str | None = None
    change_off_7_pos: str | None = None


class XGFields(BaseModel):
    """Pydantic model for validating xG data before making predictions."""

    period: int
    period_seconds: int
    score_diff: int
    danger: int
    high_danger: int
    position_f: int
    position_d: int
    position_g: int
    event_distance: float
    event_angle: float
    is_rebound: int
    rush_attempt: int
    is_home: int
    seconds_since_last: int
    distance_from_last: float
    # forwards_percent: float
    # forwards_count: int
    # opp_forwards_percent: float
    # opp_forwards_count: int
    prior_shot_same: int
    prior_miss_same: int
    prior_block_same: int
    prior_give_same: int
    prior_take_same: int
    prior_hit_same: int
    prior_shot_opp: int
    prior_miss_opp: int
    prior_block_opp: int
    prior_give_opp: int
    prior_take_opp: int
    prior_hit_opp: int
    prior_face: int
    backhand: int
    bat: int
    between_legs: int
    cradle: int
    deflected: int
    poke: int
    slap: int
    snap: int
    tip_in: int
    wrap_around: int
    wrist: int
    strength_state_3v3: int | None = None
    strength_state_4v4: int | None = None
    strength_state_5v5: int | None = None
    strength_state_3v4: int | None = None
    strength_state_3v5: int | None = None
    strength_state_4v5: int | None = None
    strength_state_4v3: int | None = None
    strength_state_5v3: int | None = None
    strength_state_5v4: int | None = None
    strength_state_Ev3: int | None = None
    strength_state_Ev4: int | None = None
    strength_state_Ev5: int | None = None
    strength_state_3vE: int | None = None
    strength_state_4vE: int | None = None
    strength_state_5vE: int | None = None


class ScheduleGame(BaseModel):
    """Pydantic model for validating schedule data."""

    season: int
    session: int
    game_id: int
    start_time: str
    game_state: str
    home_team: str
    home_team_id: int
    home_score: int
    away_team: str
    away_team_id: int
    away_score: int
    venue: str
    venue_timezone: str
    neutral_site: int
    game_date_dt: dt.datetime
    tv_broadcasts: list
    home_logo: str
    home_logo_dark: str
    away_logo: str
    away_logo_dark: str


class StandingsTeam(BaseModel):
    """Pydantic model for validating standings data."""

    season: int
    date: str
    team: str
    team_name: str
    conference: str
    division: str
    games_played: int
    points: int = None
    points_pct: float = None
    wins: int
    regulation_wins: int
    shootout_wins: int = None
    losses: int
    ot_losses: int = None
    shootout_losses: int = None
    ties: int = None
    win_pct: float
    regulation_win_pct: float
    streak_code: str
    streak_count: int
    goals_for: int
    goals_against: int
    goals_for_pct: float
    goal_differential: int
    goal_differential_pct: float
    home_games_played: int
    home_points: int
    home_goals_for: int
    home_goals_against: int
    home_goal_differential: int
    home_wins: int
    home_losses: int
    home_ot_losses: int
    home_ties: int
    home_regulation_wins: int
    road_games_played: int
    road_points: int
    road_goals_for: int
    road_goals_against: int
    road_goal_differential: int
    road_wins: int
    road_losses: int
    road_ot_losses: int
    road_ties: int
    road_regulation_wins: int
    l10_points: int
    l10_goals_for: int
    l10_goals_against: int
    l10_goal_differential: int
    l10_goals_for: int
    l10_wins: int
    l10_losses: int
    l10_ot_losses: int
    l10_ties: int
    l10_regulation_wins: int
    team_logo: str
    wildcard_sequence: int
    waivers_sequence: int


XGSchema = DataFrameSchema(
    columns={
        "season": Column(int),
        "goal": Column(int),
        "period": Column(int),
        "period_seconds": Column(int),
        "score_diff": Column(int),
        "danger": Column(int, default=0),
        "high_danger": Column(int, default=0),
        "position_f": Column(int, default=0),
        "position_d": Column(int, default=0),
        "position_g": Column(int, default=0),
        "event_distance": Column(float),
        "event_angle": Column(float, nullable=True),
        # "forwards_percent": Column(float, nullable=True),
        # "forwards_count": Column(int),
        # "opp_forwards_percent": Column(float, nullable=True),
        # "opp_forwards_count": Column(int),
        "is_rebound": Column(int, default=0),
        "rush_attempt": Column(int, default=0),
        "is_home": Column(int, default=0),
        "seconds_since_last": Column(float, nullable=True),
        "distance_from_last": Column(float, nullable=True),
        "prior_shot_same": Column(int, default=0),
        "prior_miss_same": Column(int, default=0),
        "prior_block_same": Column(int, default=0),
        "prior_give_same": Column(int, default=0),
        "prior_take_same": Column(int, default=0),
        "prior_hit_same": Column(int, default=0),
        "prior_shot_opp": Column(int, default=0),
        "prior_miss_opp": Column(int, default=0),
        "prior_block_opp": Column(int, default=0),
        "prior_give_opp": Column(int, default=0),
        "prior_take_opp": Column(int, default=0),
        "prior_hit_opp": Column(int, default=0),
        "prior_face": Column(int, default=0),
        "backhand": Column(int, default=0),
        "bat": Column(int, default=0),
        "between_legs": Column(int, default=0),
        "cradle": Column(int, default=0),
        "deflected": Column(int, default=0),
        "poke": Column(int, default=0),
        "slap": Column(int, default=0),
        "snap": Column(int, default=0),
        "tip_in": Column(int, default=0),
        "wrap_around": Column(int, default=0),
        "wrist": Column(int, default=0),
        "strength_state_3v3": Column(int, required=False),
        "strength_state_4v4": Column(int, required=False),
        "strength_state_5v5": Column(int, required=False),
        "strength_state_3v4": Column(int, required=False),
        "strength_state_3v5": Column(int, required=False),
        "strength_state_4v5": Column(int, required=False),
        "strength_state_4v3": Column(int, required=False),
        "strength_state_5v3": Column(int, required=False),
        "strength_state_5v4": Column(int, required=False),
        "strength_state_Ev3": Column(int, required=False),
        "strength_state_Ev4": Column(int, required=False),
        "strength_state_Ev5": Column(int, required=False),
        "strength_state_3vE": Column(int, required=False),
        "strength_state_4vE": Column(int, required=False),
        "strength_state_5vE": Column(int, required=False),
    },
    strict="filter",
    add_missing_columns=True,
    coerce=True,
    ordered=True,
)

IndStatSchema = DataFrameSchema(
    columns={
        "season": Column(str),
        "session": Column(str),
        "game_id": Column(str, required=False),
        "game_date": Column(str, required=False),
        "player": Column(str),
        "eh_id": Column(str),
        "api_id": Column(int),
        "position": Column(str),
        "team": Column(str),
        "opp_team": Column(str, required=False),
        "strength_state": Column(str),
        "period": Column(int, required=False),
        "score_state": Column(str, required=False),
        "forwards": Column(str, required=False),
        "forwards_eh_id": Column(str, required=False),
        "forwards_api_id": Column(str, required=False),
        "defense": Column(str, required=False),
        "defense_eh_id": Column(str, required=False),
        "defense_api_id": Column(str, required=False),
        "own_goalie": Column(str, required=False),
        "own_goalie_eh_id": Column(str, required=False),
        "own_goalie_api_id": Column(str, required=False),
        "opp_forwards": Column(str, required=False),
        "opp_forwards_eh_id": Column(str, required=False),
        "opp_forwards_api_id": Column(str, required=False),
        "opp_defense": Column(str, required=False),
        "opp_defense_eh_id": Column(str, required=False),
        "opp_defense_api_id": Column(str, required=False),
        "opp_goalie": Column(str, required=False),
        "opp_goalie_eh_id": Column(str, required=False),
        "opp_goalie_api_id": Column(str, required=False),
        "g": Column(int, default=0),
        "ihdg": Column(int, default=0),
        "a1": Column(int, default=0),
        "a2": Column(int, default=0),
        "ixg": Column(float, default=0),
        "isf": Column(int, default=0),
        "ihdsf": Column(int, default=0),
        "imsf": Column(int, default=0),
        "ihdm": Column(int, default=0),
        "iff": Column(int, default=0),
        "ihdf": Column(int, default=0),
        "isb": Column(int, default=0),
        "icf": Column(int, default=0),
        "ibs": Column(int, default=0),
        "igive": Column(int, default=0),
        "itake": Column(int, default=0),
        "ihf": Column(int, default=0),
        "iht": Column(int, default=0),
        "ifow": Column(int, default=0),
        "ifol": Column(int, default=0),
        "iozfw": Column(int, default=0),
        "iozfl": Column(int, default=0),
        "inzfw": Column(int, default=0),
        "inzfl": Column(int, default=0),
        "idzfw": Column(int, default=0),
        "idzfl": Column(int, default=0),
        "a1_xg": Column(float, default=0),
        "a2_xg": Column(float, default=0),
        "ipent0": Column(int, default=0),
        "ipent2": Column(int, default=0),
        "ipent4": Column(int, default=0),
        "ipent5": Column(int, default=0),
        "ipent10": Column(int, default=0),
        "ipend0": Column(int, default=0),
        "ipend2": Column(int, default=0),
        "ipend4": Column(int, default=0),
        "ipend5": Column(int, default=0),
        "ipend10": Column(int, default=0),
    },
    strict="filter",
    add_missing_columns=True,
    coerce=True,
    ordered=True,
)

OIStatSchema = DataFrameSchema(
    columns={
        "season": Column(str),
        "session": Column(str),
        "game_id": Column(str, required=False),
        "game_date": Column(str, required=False),
        "player": Column(str),
        "eh_id": Column(str),
        "api_id": Column(int),
        "position": Column(str),
        "team": Column(str),
        "opp_team": Column(str, required=False),
        "strength_state": Column(str),
        "period": Column(int, required=False),
        "score_state": Column(str, required=False),
        "forwards": Column(str, required=False),
        "forwards_eh_id": Column(str, required=False),
        "forwards_api_id": Column(str, required=False),
        "defense": Column(str, required=False),
        "defense_eh_id": Column(str, required=False),
        "defense_api_id": Column(str, required=False),
        "own_goalie": Column(str, required=False),
        "own_goalie_eh_id": Column(str, required=False),
        "own_goalie_api_id": Column(str, required=False),
        "opp_forwards": Column(str, required=False),
        "opp_forwards_eh_id": Column(str, required=False),
        "opp_forwards_api_id": Column(str, required=False),
        "opp_defense": Column(str, required=False),
        "opp_defense_eh_id": Column(str, required=False),
        "opp_defense_api_id": Column(str, required=False),
        "opp_goalie": Column(str, required=False),
        "opp_goalie_eh_id": Column(str, required=False),
        "opp_goalie_api_id": Column(str, required=False),
        "toi": Column(float, default=0),
        "gf": Column(int, default=0),
        "ga": Column(int, default=0),
        "hdgf": Column(int, default=0),
        "hdga": Column(int, default=0),
        "xgf": Column(float, default=0),
        "xga": Column(float, default=0),
        "sf": Column(int, default=0),
        "sa": Column(int, default=0),
        "hdsf": Column(int, default=0),
        "hdsa": Column(int, default=0),
        "ff": Column(int, default=0),
        "fa": Column(int, default=0),
        "hdff": Column(int, default=0),
        "hdfa": Column(int, default=0),
        "cf": Column(int, default=0),
        "ca": Column(int, default=0),
        "bsf": Column(int, default=0),
        "bsa": Column(int, default=0),
        "msf": Column(int, default=0),
        "msa": Column(int, default=0),
        "hdmsf": Column(int, default=0),
        "hdmsa": Column(int, default=0),
        "teammate_block": Column(int, default=0),
        "hf": Column(int, default=0),
        "ht": Column(int, default=0),
        "give": Column(int, default=0),
        "take": Column(int, default=0),
        "ozf": Column(int, default=0),
        "nzf": Column(int, default=0),
        "dzf": Column(int, default=0),
        "fow": Column(int, default=0),
        "fol": Column(int, default=0),
        "ozfw": Column(int, default=0),
        "ozfl": Column(int, default=0),
        "nzfw": Column(int, default=0),
        "nzfl": Column(int, default=0),
        "dzfw": Column(int, default=0),
        "dzfl": Column(int, default=0),
        "pent0": Column(int, default=0),
        "pent2": Column(int, default=0),
        "pent4": Column(int, default=0),
        "pent5": Column(int, default=0),
        "pent10": Column(int, default=0),
        "pend0": Column(int, default=0),
        "pend2": Column(int, default=0),
        "pend4": Column(int, default=0),
        "pend5": Column(int, default=0),
        "pend10": Column(int, default=0),
        "ozs": Column(int, default=0),
        "nzs": Column(int, default=0),
        "dzs": Column(int, default=0),
        "otf": Column(int, default=0),
    },
    strict="filter",
    add_missing_columns=True,
    coerce=True,
    ordered=True,
)

StatSchema = DataFrameSchema(
    columns={
        "season": Column(str),
        "session": Column(str),
        "game_id": Column(str, required=False),
        "game_date": Column(str, required=False),
        "player": Column(str),
        "eh_id": Column(str),
        "api_id": Column(int),
        "position": Column(str),
        "team": Column(str),
        "opp_team": Column(str, required=False),
        "strength_state": Column(str),
        "period": Column(int, required=False),
        "score_state": Column(str, required=False),
        "forwards": Column(str, required=False),
        "forwards_eh_id": Column(str, required=False),
        "forwards_api_id": Column(str, required=False),
        "defense": Column(str, required=False),
        "defense_eh_id": Column(str, required=False),
        "defense_api_id": Column(str, required=False),
        "own_goalie": Column(str, required=False),
        "own_goalie_eh_id": Column(str, required=False),
        "own_goalie_api_id": Column(str, required=False),
        "opp_forwards": Column(str, required=False),
        "opp_forwards_eh_id": Column(str, required=False),
        "opp_forwards_api_id": Column(str, required=False),
        "opp_defense": Column(str, required=False),
        "opp_defense_eh_id": Column(str, required=False),
        "opp_defense_api_id": Column(str, required=False),
        "opp_goalie": Column(str, required=False),
        "opp_goalie_eh_id": Column(str, required=False),
        "opp_goalie_api_id": Column(str, required=False),
        "toi": Column(float, default=0),
        "g": Column(int, default=0),
        "ihdg": Column(int, default=0),
        "a1": Column(int, default=0),
        "a2": Column(int, default=0),
        "ixg": Column(float, default=0),
        "isf": Column(int, default=0),
        "ihdsf": Column(int, default=0),
        "imsf": Column(int, default=0),
        "ihdm": Column(int, default=0),
        "iff": Column(int, default=0),
        "ihdf": Column(int, default=0),
        "isb": Column(int, default=0),
        "icf": Column(int, default=0),
        "ibs": Column(int, default=0),
        "igive": Column(int, default=0),
        "itake": Column(int, default=0),
        "ihf": Column(int, default=0),
        "iht": Column(int, default=0),
        "ifow": Column(int, default=0),
        "ifol": Column(int, default=0),
        "iozfw": Column(int, default=0),
        "iozfl": Column(int, default=0),
        "inzfw": Column(int, default=0),
        "inzfl": Column(int, default=0),
        "idzfw": Column(int, default=0),
        "idzfl": Column(int, default=0),
        "a1_xg": Column(float, default=0),
        "a2_xg": Column(float, default=0),
        "ipent0": Column(int, default=0),
        "ipent2": Column(int, default=0),
        "ipent4": Column(int, default=0),
        "ipent5": Column(int, default=0),
        "ipent10": Column(int, default=0),
        "ipend0": Column(int, default=0),
        "ipend2": Column(int, default=0),
        "ipend4": Column(int, default=0),
        "ipend5": Column(int, default=0),
        "ipend10": Column(int, default=0),
        "gf": Column(int, default=0),
        "ga": Column(int, default=0),
        "hdgf": Column(int, default=0),
        "hdga": Column(int, default=0),
        "xgf": Column(float, default=0),
        "xga": Column(float, default=0),
        "sf": Column(int, default=0),
        "sa": Column(int, default=0),
        "hdsf": Column(int, default=0),
        "hdsa": Column(int, default=0),
        "ff": Column(int, default=0),
        "fa": Column(int, default=0),
        "hdff": Column(int, default=0),
        "hdfa": Column(int, default=0),
        "cf": Column(int, default=0),
        "ca": Column(int, default=0),
        "bsf": Column(int, default=0),
        "bsa": Column(int, default=0),
        "msf": Column(int, default=0),
        "msa": Column(int, default=0),
        "hdmsf": Column(int, default=0),
        "hdmsa": Column(int, default=0),
        "teammate_block": Column(int, default=0),
        "hf": Column(int, default=0),
        "ht": Column(int, default=0),
        "give": Column(int, default=0),
        "take": Column(int, default=0),
        "ozf": Column(int, default=0),
        "nzf": Column(int, default=0),
        "dzf": Column(int, default=0),
        "fow": Column(int, default=0),
        "fol": Column(int, default=0),
        "ozfw": Column(int, default=0),
        "ozfl": Column(int, default=0),
        "nzfw": Column(int, default=0),
        "nzfl": Column(int, default=0),
        "dzfw": Column(int, default=0),
        "dzfl": Column(int, default=0),
        "pent0": Column(int, default=0),
        "pent2": Column(int, default=0),
        "pent4": Column(int, default=0),
        "pent5": Column(int, default=0),
        "pent10": Column(int, default=0),
        "pend0": Column(int, default=0),
        "pend2": Column(int, default=0),
        "pend4": Column(int, default=0),
        "pend5": Column(int, default=0),
        "pend10": Column(int, default=0),
        "ozs": Column(int, default=0),
        "nzs": Column(int, default=0),
        "dzs": Column(int, default=0),
        "otf": Column(int, default=0),
        "g_p60": Column(float, default=0),
        "ihdg_p60": Column(float, default=0),
        "a1_p60": Column(float, default=0),
        "a2_p60": Column(float, default=0),
        "ixg_p60": Column(float, default=0),
        "isf_p60": Column(float, default=0),
        "ihdsf_p60": Column(float, default=0),
        "imsf_p60": Column(float, default=0),
        "ihdm_p60": Column(float, default=0),
        "iff_p60": Column(float, default=0),
        "ihdf_p60": Column(float, default=0),
        "isb_p60": Column(float, default=0),
        "icf_p60": Column(float, default=0),
        "ibs_p60": Column(float, default=0),
        "igive_p60": Column(float, default=0),
        "itake_p60": Column(float, default=0),
        "ihf_p60": Column(float, default=0),
        "iht_p60": Column(float, default=0),
        "a1_xg_p60": Column(float, default=0),
        "a2_xg_p60": Column(float, default=0),
        "ipent0_p60": Column(float, default=0),
        "ipent2_p60": Column(float, default=0),
        "ipent4_p60": Column(float, default=0),
        "ipent5_p60": Column(float, default=0),
        "ipent10_p60": Column(float, default=0),
        "ipend0_p60": Column(float, default=0),
        "ipend2_p60": Column(float, default=0),
        "ipend4_p60": Column(float, default=0),
        "ipend5_p60": Column(float, default=0),
        "ipend10_p60": Column(float, default=0),
        "gf_p60": Column(float, default=0),
        "ga_p60": Column(float, default=0),
        "hdgf_p60": Column(float, default=0),
        "hdga_p60": Column(float, default=0),
        "xgf_p60": Column(float, default=0),
        "xga_p60": Column(float, default=0),
        "sf_p60": Column(float, default=0),
        "sa_p60": Column(float, default=0),
        "hdsf_p60": Column(float, default=0),
        "hdsa_p60": Column(float, default=0),
        "ff_p60": Column(float, default=0),
        "fa_p60": Column(float, default=0),
        "hdff_p60": Column(float, default=0),
        "hdfa_p60": Column(float, default=0),
        "cf_p60": Column(float, default=0),
        "ca_p60": Column(float, default=0),
        "bsf_p60": Column(float, default=0),
        "bsa_p60": Column(float, default=0),
        "msf_p60": Column(float, default=0),
        "msa_p60": Column(float, default=0),
        "hdmsf_p60": Column(float, default=0),
        "hdmsa_p60": Column(float, default=0),
        "teammate_block_p60": Column(float, default=0),
        "hf_p60": Column(float, default=0),
        "ht_p60": Column(float, default=0),
        "give_p60": Column(float, default=0),
        "take_p60": Column(float, default=0),
        "pent0_p60": Column(float, default=0),
        "pent2_p60": Column(float, default=0),
        "pent4_p60": Column(float, default=0),
        "pent5_p60": Column(float, default=0),
        "pent10_p60": Column(float, default=0),
        "pend0_p60": Column(float, default=0),
        "pend2_p60": Column(float, default=0),
        "pend4_p60": Column(float, default=0),
        "pend5_p60": Column(float, default=0),
        "pend10_p60": Column(float, default=0),
        "gf_percent": Column(float, default=0),
        "hdgf_percent": Column(float, default=0),
        "xgf_percent": Column(float, default=0),
        "sf_percent": Column(float, default=0),
        "hdsf_percent": Column(float, default=0),
        "ff_percent": Column(float, default=0),
        "hdff_percent": Column(float, default=0),
        "cf_percent": Column(float, default=0),
        "bsf_percent": Column(float, default=0),
        "msf_percent": Column(float, default=0),
        "hdmsf_percent": Column(float, default=0),
        "hf_percent": Column(float, default=0),
        "take_percent": Column(float, default=0),
    },
    strict="filter",
    add_missing_columns=True,
    coerce=True,
    ordered=True,
)

LineSchema = DataFrameSchema(
    columns={
        "season": Column(str),
        "session": Column(str),
        "game_id": Column(str, required=False),
        "game_date": Column(str, required=False),
        "team": Column(str),
        "opp_team": Column(str, required=False),
        "strength_state": Column(str),
        "period": Column(int, required=False),
        "score_state": Column(str, required=False),
        "forwards": Column(str, required=False),
        "forwards_eh_id": Column(str, required=False),
        "forwards_api_id": Column(str, required=False),
        "defense": Column(str, required=False),
        "defense_eh_id": Column(str, required=False),
        "defense_api_id": Column(str, required=False),
        "own_goalie": Column(str, required=False),
        "own_goalie_eh_id": Column(str, required=False),
        "own_goalie_api_id": Column(str, required=False),
        "opp_forwards": Column(str, required=False),
        "opp_forwards_eh_id": Column(str, required=False),
        "opp_forwards_api_id": Column(str, required=False),
        "opp_defense": Column(str, required=False),
        "opp_defense_eh_id": Column(str, required=False),
        "opp_defense_api_id": Column(str, required=False),
        "opp_goalie": Column(str, required=False),
        "opp_goalie_eh_id": Column(str, required=False),
        "opp_goalie_api_id": Column(str, required=False),
        "toi": Column(float, default=0),
        "gf": Column(int, default=0),
        "ga": Column(int, default=0),
        "hdgf": Column(int, default=0),
        "hdga": Column(int, default=0),
        "xgf": Column(float, default=0),
        "xga": Column(float, default=0),
        "sf": Column(int, default=0),
        "sa": Column(int, default=0),
        "hdsf": Column(int, default=0),
        "hdsa": Column(int, default=0),
        "ff": Column(int, default=0),
        "fa": Column(int, default=0),
        "hdff": Column(int, default=0),
        "hdfa": Column(int, default=0),
        "cf": Column(int, default=0),
        "ca": Column(int, default=0),
        "bsf": Column(int, default=0),
        "bsa": Column(int, default=0),
        "msf": Column(int, default=0),
        "msa": Column(int, default=0),
        "hdmsf": Column(int, default=0),
        "hdmsa": Column(int, default=0),
        "teammate_block": Column(int, default=0),
        "hf": Column(int, default=0),
        "ht": Column(int, default=0),
        "give": Column(int, default=0),
        "take": Column(int, default=0),
        "ozf": Column(int, default=0),
        "nzf": Column(int, default=0),
        "dzf": Column(int, default=0),
        "fow": Column(int, default=0),
        "fol": Column(int, default=0),
        "ozfw": Column(int, default=0),
        "ozfl": Column(int, default=0),
        "nzfw": Column(int, default=0),
        "nzfl": Column(int, default=0),
        "dzfw": Column(int, default=0),
        "dzfl": Column(int, default=0),
        "pent0": Column(int, default=0),
        "pent2": Column(int, default=0),
        "pent4": Column(int, default=0),
        "pent5": Column(int, default=0),
        "pent10": Column(int, default=0),
        "pend0": Column(int, default=0),
        "pend2": Column(int, default=0),
        "pend4": Column(int, default=0),
        "pend5": Column(int, default=0),
        "pend10": Column(int, default=0),
        "gf_p60": Column(float, default=0),
        "ga_p60": Column(float, default=0),
        "hdgf_p60": Column(float, default=0),
        "hdga_p60": Column(float, default=0),
        "xgf_p60": Column(float, default=0),
        "xga_p60": Column(float, default=0),
        "sf_p60": Column(float, default=0),
        "sa_p60": Column(float, default=0),
        "hdsf_p60": Column(float, default=0),
        "hdsa_p60": Column(float, default=0),
        "ff_p60": Column(float, default=0),
        "fa_p60": Column(float, default=0),
        "hdff_p60": Column(float, default=0),
        "hdfa_p60": Column(float, default=0),
        "cf_p60": Column(float, default=0),
        "ca_p60": Column(float, default=0),
        "bsf_p60": Column(float, default=0),
        "bsa_p60": Column(float, default=0),
        "msf_p60": Column(float, default=0),
        "msa_p60": Column(float, default=0),
        "hdmsf_p60": Column(float, default=0),
        "hdmsa_p60": Column(float, default=0),
        "teammate_block_p60": Column(float, default=0),
        "hf_p60": Column(float, default=0),
        "ht_p60": Column(float, default=0),
        "give_p60": Column(float, default=0),
        "take_p60": Column(float, default=0),
        "pent0_p60": Column(float, default=0),
        "pent2_p60": Column(float, default=0),
        "pent4_p60": Column(float, default=0),
        "pent5_p60": Column(float, default=0),
        "pent10_p60": Column(float, default=0),
        "pend0_p60": Column(float, default=0),
        "pend2_p60": Column(float, default=0),
        "pend4_p60": Column(float, default=0),
        "pend5_p60": Column(float, default=0),
        "pend10_p60": Column(float, default=0),
        "gf_percent": Column(float, default=0),
        "hdgf_percent": Column(float, default=0),
        "xgf_percent": Column(float, default=0),
        "sf_percent": Column(float, default=0),
        "hdsf_percent": Column(float, default=0),
        "ff_percent": Column(float, default=0),
        "hdff_percent": Column(float, default=0),
        "cf_percent": Column(float, default=0),
        "bsf_percent": Column(float, default=0),
        "msf_percent": Column(float, default=0),
        "hdmsf_percent": Column(float, default=0),
        "hf_percent": Column(float, default=0),
        "take_percent": Column(float, default=0),
    },
    strict="filter",
    add_missing_columns=True,
    coerce=True,
    ordered=True,
)

TeamStatSchema = DataFrameSchema(
    columns={
        "season": Column(str),
        "session": Column(str),
        "game_id": Column(str, required=False),
        "game_date": Column(str, required=False),
        "team": Column(str),
        "opp_team": Column(str, required=False),
        "strength_state": Column(str, required=False),
        "period": Column(int, required=False),
        "score_state": Column(str, required=False),
        "toi": Column(float, default=0),
        "gf": Column(int, default=0),
        "ga": Column(int, default=0),
        "hdgf": Column(int, default=0),
        "hdga": Column(int, default=0),
        "xgf": Column(float, default=0),
        "xga": Column(float, default=0),
        "sf": Column(int, default=0),
        "sa": Column(int, default=0),
        "hdsf": Column(int, default=0),
        "hdsa": Column(int, default=0),
        "ff": Column(int, default=0),
        "fa": Column(int, default=0),
        "hdff": Column(int, default=0),
        "hdfa": Column(int, default=0),
        "cf": Column(int, default=0),
        "ca": Column(int, default=0),
        "bsf": Column(int, default=0),
        "bsa": Column(int, default=0),
        "msf": Column(int, default=0),
        "msa": Column(int, default=0),
        "hdmsf": Column(int, default=0),
        "hdmsa": Column(int, default=0),
        "teammate_block": Column(int, default=0),
        "hf": Column(int, default=0),
        "ht": Column(int, default=0),
        "give": Column(int, default=0),
        "take": Column(int, default=0),
        "ozf": Column(int, default=0),
        "nzf": Column(int, default=0),
        "dzf": Column(int, default=0),
        "fow": Column(int, default=0),
        "fol": Column(int, default=0),
        "ozfw": Column(int, default=0),
        "ozfl": Column(int, default=0),
        "nzfw": Column(int, default=0),
        "nzfl": Column(int, default=0),
        "dzfw": Column(int, default=0),
        "dzfl": Column(int, default=0),
        "pent0": Column(int, default=0),
        "pent2": Column(int, default=0),
        "pent4": Column(int, default=0),
        "pent5": Column(int, default=0),
        "pent10": Column(int, default=0),
        "pend0": Column(int, default=0),
        "pend2": Column(int, default=0),
        "pend4": Column(int, default=0),
        "pend5": Column(int, default=0),
        "pend10": Column(int, default=0),
        "ozs": Column(int, default=0),
        "nzs": Column(int, default=0),
        "dzs": Column(int, default=0),
        "otf": Column(int, default=0),
        "gf_p60": Column(float, default=0),
        "ga_p60": Column(float, default=0),
        "hdgf_p60": Column(float, default=0),
        "hdga_p60": Column(float, default=0),
        "xgf_p60": Column(float, default=0),
        "xga_p60": Column(float, default=0),
        "sf_p60": Column(float, default=0),
        "sa_p60": Column(float, default=0),
        "hdsf_p60": Column(float, default=0),
        "hdsa_p60": Column(float, default=0),
        "ff_p60": Column(float, default=0),
        "fa_p60": Column(float, default=0),
        "hdff_p60": Column(float, default=0),
        "hdfa_p60": Column(float, default=0),
        "cf_p60": Column(float, default=0),
        "ca_p60": Column(float, default=0),
        "bsf_p60": Column(float, default=0),
        "bsa_p60": Column(float, default=0),
        "msf_p60": Column(float, default=0),
        "msa_p60": Column(float, default=0),
        "hdmsf_p60": Column(float, default=0),
        "hdmsa_p60": Column(float, default=0),
        "teammate_block_p60": Column(float, default=0),
        "hf_p60": Column(float, default=0),
        "ht_p60": Column(float, default=0),
        "give_p60": Column(float, default=0),
        "take_p60": Column(float, default=0),
        "pent0_p60": Column(float, default=0),
        "pent2_p60": Column(float, default=0),
        "pent4_p60": Column(float, default=0),
        "pent5_p60": Column(float, default=0),
        "pent10_p60": Column(float, default=0),
        "pend0_p60": Column(float, default=0),
        "pend2_p60": Column(float, default=0),
        "pend4_p60": Column(float, default=0),
        "pend5_p60": Column(float, default=0),
        "pend10_p60": Column(float, default=0),
        "gf_percent": Column(float, default=0),
        "hdgf_percent": Column(float, default=0),
        "xgf_percent": Column(float, default=0),
        "sf_percent": Column(float, default=0),
        "hdsf_percent": Column(float, default=0),
        "ff_percent": Column(float, default=0),
        "hdff_percent": Column(float, default=0),
        "cf_percent": Column(float, default=0),
        "bsf_percent": Column(float, default=0),
        "msf_percent": Column(float, default=0),
        "hdmsf_percent": Column(float, default=0),
        "hf_percent": Column(float, default=0),
        "take_percent": Column(float, default=0),
    },
    strict="filter",
    add_missing_columns=True,
    coerce=True,
    ordered=True,
)
