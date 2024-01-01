from pydantic import BaseModel, field_validator


class APIEvent(BaseModel):
    """Pydantic model for validating API event data"""

    season: int
    session: str
    game_id: int
    event_idx: int
    period: int
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
    player_1_api_id: int | None = None
    player_1_team_jersey: str | None = None
    player_2: str | None = None
    player_2_eh_id: str | None = None
    player_2_position: str | None = None
    player_2_type: str | None = None
    player_2_api_id: int | None = None
    player_2_team_jersey: str | None = None
    player_3: str | None = None
    player_3_eh_id: str | None = None
    player_3_position: str | None = None
    player_3_type: str | None = None
    player_3_api_id: int | None = None
    player_3_team_jersey: str | None = None
    strength: int | None = None
    shot_type: str | None = None
    miss_reason: str | None = None
    opp_goalie: str | None = None
    opp_goalie_eh_id: str | None = None
    opp_goalie_position: str | None = None
    opp_goalie_type: str | None = None
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
    """Pydantic model for validating API roster data"""

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
    """Pydantic model for validating Changes data"""

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
    change_on_id: list[str] | str = ""
    change_on_positions: list[str] | str = ""
    change_off: list[str] | str = ""
    change_off_jersey: list[str] | str = ""
    change_off_id: list[str] | str = ""
    change_off_positions: list[str] | str = ""
    change_on_forwards_count: int
    change_off_forwards_count: int
    change_on_forwards: list[str] | str = ""
    change_on_forwards_jersey: list[str] | str = ""
    change_on_forwards_id: list[str] | str = ""
    change_off_forwards: list[str] | str = ""
    change_off_forwards_jersey: list[str] | str = ""
    change_off_forwards_id: list[str] | str = ""
    change_on_defense_count: int
    change_off_defense_count: int
    change_on_defense: list[str] | str = ""
    change_on_defense_jersey: list[str] | str = ""
    change_on_defense_id: list[str] | str = ""
    change_off_defense: list[str] | str = ""
    change_off_defense_jersey: list[str] | str = ""
    change_off_defense_id: list[str] | str = ""
    change_on_goalie_count: int
    change_off_goalie_count: int
    change_on_goalie: list[str] | str = ""
    change_on_goalie_jersey: list[str] | str = ""
    change_on_goalie_id: list[str] | str = ""
    change_off_goalie: list[str] | str = ""
    change_off_goalie_jersey: list[str] | str = ""
    change_off_goalie_id: list[str] | str = ""
    is_home: int
    team_venue: str


class HTMLEvent(BaseModel):
    """Class for validating HTML event data"""

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
    pbp_distance: int | None
    penalty_length: int | None = None
    penalty: str | None = None
    strength: str | None = None
    away_skaters: str | None = None
    home_skaters: str | None = None
    version: int

    @field_validator("strength")
    def fix_strength(cls, v):
        if v == " ":
            strength = None

        else:
            strength = v

        return strength

    @field_validator("away_skaters")
    def fix_away_skaters(cls, v):
        if v == " ":
            skaters = None

        else:
            skaters = v

        return skaters

    @field_validator("home_skaters")
    def fix_home_skaters(cls, v):
        if v == " ":
            skaters = None

        else:
            skaters = v

        return skaters


class HTMLRosterPlayer(BaseModel):
    """Pydantic model for validating HTML roster data"""

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
    """Pydantic model for validating roster data"""

    season: int
    session: str
    game_id: int
    team: str
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
