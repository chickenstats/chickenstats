from pydantic import BaseModel, field_validator
import datetime as dt


class APIEvent(BaseModel):
    """Pydantic model for validating API event data"""

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
    """Pydantic model for validating changes data"""

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
    change_on_positions: list[str] | str = ""
    change_off: list[str] | str = ""
    change_off_jersey: list[str] | str = ""
    change_off_eh_id: list[str] | str = ""
    change_off_positions: list[str] | str = ""
    change_on_forwards_count: int
    change_off_forwards_count: int
    change_on_forwards: list[str] | str = ""
    change_on_forwards_jersey: list[str] | str = ""
    change_on_forwards_eh_id: list[str] | str = ""
    change_off_forwards: list[str] | str = ""
    change_off_forwards_jersey: list[str] | str = ""
    change_off_forwards_eh_id: list[str] | str = ""
    change_on_defense_count: int
    change_off_defense_count: int
    change_on_defense: list[str] | str = ""
    change_on_defense_jersey: list[str] | str = ""
    change_on_defense_eh_id: list[str] | str = ""
    change_off_defense: list[str] | str = ""
    change_off_defense_jersey: list[str] | str = ""
    change_off_defense_eh_id: list[str] | str = ""
    change_on_goalie_count: int
    change_off_goalie_count: int
    change_on_goalie: list[str] | str = ""
    change_on_goalie_jersey: list[str] | str = ""
    change_on_goalie_eh_id: list[str] | str = ""
    change_off_goalie: list[str] | str = ""
    change_off_goalie_jersey: list[str] | str = ""
    change_off_goalie_eh_id: list[str] | str = ""
    is_home: int
    is_away: int
    team_venue: str

    @field_validator(
        "change_on_jersey",
        "change_on",
        "change_on_eh_id",
        "change_on_positions",
        "change_off_jersey",
        "change_off",
        "change_off_eh_id",
        "change_off_positions",
        "change_on_forwards_jersey",
        "change_on_forwards",
        "change_on_forwards_eh_id",
        "change_off_forwards_jersey",
        "change_off_forwards",
        "change_off_forwards_eh_id",
        "change_on_defense_jersey",
        "change_on_defense",
        "change_on_defense_eh_id",
        "change_off_defense_jersey",
        "change_off_defense",
        "change_off_defense_eh_id",
        "change_on_goalie_jersey",
        "change_on_goalie",
        "change_on_goalie_eh_id",
        "change_off_goalie_jersey",
        "change_off_goalie",
        "change_off_goalie_eh_id",
        mode="after",
    )
    @classmethod
    def fix_list(cls, v):
        if v and isinstance(v, list) is True:
            return ", ".join(v)

        elif not v:
            return None

        else:
            return v


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
        if v == " ":
            new_v = None

        else:
            new_v = v

        return new_v


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
    """Pydantic model for validating shifts data"""

    season: int
    session: str
    game_id: int
    team: str
    team_name: str
    player_name: str
    eh_id: str
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
    """Pydantic model for validating play-by-play data"""

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
    defense: list | str | None = None
    defense_eh_id: list | str | None = None
    defense_api_id: list | str | None = None
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
    opp_defense: list | str | None = None
    opp_defense_eh_id: list | str | None = None
    opp_defense_api_id: list | str | None = None
    home_forwards: list | str | None = None
    home_forwards_eh_id: list | str | None = None
    home_forwards_api_id: list | str | None = None
    home_defense: list | str | None = None
    home_defense_eh_id: list | str | None = None
    home_defense_api_id: list | str | None = None
    home_goalie: list | str | None = None
    home_goalie_eh_id: list | str | None = None
    home_goalie_api_id: list | str | None = None
    away_forwards: list | str | None = None
    away_forwards_eh_id: list | str | None = None
    away_forwards_api_id: list | str | None = None
    away_defense: list | str | None = None
    away_defense_eh_id: list | str | None = None
    away_defense_api_id: list | str | None = None
    away_goalie: list | str | None = None
    away_goalie_eh_id: list | str | None = None
    away_goalie_api_id: list | str | None = None
    change_on_count: int | None = None
    change_off_count: int | None = None
    change_on: list | str | None = None
    change_on_eh_id: list | str | None = None
    change_on_positions: list | str | None = None
    change_off: list | str | None = None
    change_off_eh_id: list | str | None = None
    change_off_positions: list | str | None = None
    change_on_forwards_count: int | None = None
    change_off_forwards_count: int | None = None
    change_on_forwards: list | str | None = None
    change_on_forwards_eh_id: list | str | None = None
    change_off_forwards: list | str | None = None
    change_off_forwards_eh_id: list | str | None = None
    change_on_defense_count: int | None = None
    change_off_defense_count: int | None = None
    change_on_defense: list | str | None = None
    change_on_defense_eh_id: list | str | None = None
    change_off_defense: list | str | None = None
    change_off_defense_eh_id: list | str | None = None
    change_on_goalie_count: int | None = None
    change_off_goalie_count: int | None = None
    change_on_goalie: list | str | None = None
    change_on_goalie_eh_id: list | str | None = None
    change_off_goalie: list | str | None = None
    change_off_goalie_eh_id: list | str | None = None
    goal: int = 0
    shot: int = 0
    miss: int = 0
    fenwick: int = 0
    corsi: int = 0
    block: int = 0
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

    @field_validator("*")
    @classmethod
    def invalid_strings(cls, v):
        if v == "" or v == " ":
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
        "change_on_positions",
        "change_off",
        "change_off_eh_id",
        "change_off_positions",
        "change_on_forwards",
        "change_on_forwards_eh_id",
        "change_off_forwards",
        "change_off_forwards_eh_id",
        "change_on_defense",
        "change_on_defense_eh_id",
        "change_off_defense",
        "change_off_defense_eh_id",
        "change_on_goalie",
        "change_on_goalie_eh_id",
        "change_off_goalie",
        "change_off_goalie_eh_id",
        mode="before",
    )
    @classmethod
    def fix_list(cls, v):
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
        if v is None:
            return "EMPTY NET"

        else:
            return v


class ScheduleGame(BaseModel):
    """Pydantic model for validating schedule data"""

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
    """Pydantic model for validating standings data"""

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
