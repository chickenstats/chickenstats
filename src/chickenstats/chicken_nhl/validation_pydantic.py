"""Pydantic v2 models used to validate raw NHL data before it enters the pipeline.

Each model corresponds to one raw data type scraped or parsed by the Game class:
    * ChickenBaseModel  — shared base fields (season, session, game_id)
    * APIEvent          — NHL API event data
    * APIRosterPlayer   — NHL API roster entry
    * ChangeEvent       — line-change events derived from shifts
    * HTMLEvent         — HTML play-by-play event
    * HTMLRosterPlayer  — HTML roster entry
    * RosterPlayer      — merged API + HTML roster entry (the canonical player record)
    * PlayerShift       — individual player shift record
    * PBPEvent          — play-by-play row (the main event model used for stats)
    * PBPEventExt       — extended play-by-play (adds on-ice lineup columns)
    * XGFields          — feature row passed to the xG model for scoring chances
    * ScheduleGame      — schedule entry
    * StandingsTeam     — standings entry

Models use Pydantic v2's ``model_construct`` (skips re-validation) for performance in
hot loops. Field validators normalise raw strings, list fields, and sentinel None values
before data reaches downstream aggregation.
"""

import typing

from pydantic import BaseModel, field_validator, model_validator, Field
import datetime as dt


def _join_list(v) -> str | None:
    """Normalise a field value for storage as a plain string.

    - ``list`` with items → comma-separated string, e.g. ``[1, 2]`` → ``"1, 2"``
    - empty ``list``      → empty string ``""``
    - non-list truthy     → returned unchanged
    - non-list falsy      → ``None`` (covers ``None``, ``""``, ``0``, ``False``)
    """
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else ""
    return v or None


def _fix_lists(data, model_fields) -> dict:
    """Serialise any list-typed fields in ``data`` to comma-separated strings.

    Shared implementation called by the ``fix_lists`` model validators on
    ``ChangeEvent`` and ``PBPEvent``. Iterates the model's field map, checks each
    field's annotation with ``_annotation_has_list``, and applies ``_join_list``
    to any field present in ``data`` whose annotation includes ``list``.

    Parameters:
        data:
            The raw input dict passed to the model validator. Non-dict values are
            returned unchanged (Pydantic may pass other types in some edge cases).
        model_fields (dict):
            The ``cls.model_fields`` mapping from the calling model class.

    Returns:
        dict: The same ``data`` dict with list fields converted in-place.
    """
    if not isinstance(data, dict):
        return data
    for field_name, field_info in model_fields.items():
        if field_name in data and _annotation_has_list(field_info.annotation):
            data[field_name] = _join_list(data[field_name])
    return data


def _annotation_has_list(annotation) -> bool:
    """Return ``True`` if ``annotation`` is or contains ``list`` at any nesting level.

    Used by the ``fix_lists`` model validators on ``ChangeEvent`` and ``PBPEvent`` to
    detect which fields hold list values that need to be serialised to comma-separated
    strings before storage. Handles bare ``list``, ``list[T]``, ``Optional[list[T]]``,
    and other nested generic forms.
    """
    if annotation is list:
        return True
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is list:
        return True
    return bool(args) and any(_annotation_has_list(a) for a in args)


# Pydantic models
class ChickenBaseModel(BaseModel):
    """Pydantic model to be used as base for other Pydantic models."""

    season: int
    session: str = Field(pattern=r"PR|R|P|FO")
    game_id: int


class APIEvent(ChickenBaseModel):
    """Pydantic model for validating API event data."""

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
    opp_goalie_api_id: int | None = None
    opp_goalie_team_jersey: str | None = None
    event_team_id: int | None = None
    stoppage_reason: str | None = None
    stoppage_reason_secondary: str | None = None
    penalty_type: str | None = None
    penalty_reason: str | None = None
    penalty_duration: int | None = None
    home_team_defending_side: str | None = None
    version: int


class APIRosterPlayer(ChickenBaseModel):
    """Pydantic model for validating API roster data."""

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


class ChangeEvent(ChickenBaseModel):
    """Pydantic model for validating changes data."""

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

    @model_validator(mode="before")
    @classmethod
    def fix_lists(cls, data):
        """Convert list fields to comma-separated strings before validation."""
        return _fix_lists(data, cls.model_fields)


class HTMLEvent(ChickenBaseModel):
    """Class for validating HTML event data."""

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
        new_v = None if v == " " else v

        return new_v


class HTMLRosterPlayer(ChickenBaseModel):
    """Pydantic model for validating HTML roster data."""

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


class RosterPlayer(ChickenBaseModel):
    """Pydantic model for validating roster data."""

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


class PlayerShift(ChickenBaseModel):
    """Pydantic model for validating shifts data."""

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
    description: str | None = None
    zone: str | None = None
    coords_x: int | None = None
    coords_y: int | None = None
    danger: int | None = None
    high_danger: int | None = None
    player_1: str | None = None
    player_1_eh_id: str | None = None
    player_1_eh_id_api: str | None = None
    player_1_api_id: int | None = None
    player_1_position: str | None = None
    player_1_type: str | None = None
    player_2: str | None = None
    player_2_eh_id: str | None = None
    player_2_eh_id_api: str | None = None
    player_2_api_id: int | None = None
    player_2_position: str | None = None
    player_2_type: str | None = None
    player_3: str | None = None
    player_3_eh_id: str | None = None
    player_3_eh_id_api: str | None = None
    player_3_api_id: int | None = None
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
    own_goalie_api_id: list | int | None = None
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
    opp_goalie_api_id: list | int | None = None
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
    zone_start: str | None = None
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
    goal_adj: float = 0
    hd_goal: int = 0
    shot: int = 0
    shot_adj: float = 0
    hd_shot: int = 0
    miss: int = 0
    miss_adj: float = 0
    hd_miss: int = 0
    fenwick: int = 0
    fenwick_adj: float = 0
    hd_fenwick: int = 0
    corsi: int = 0
    corsi_adj: float = 0
    block: int = 0
    block_adj: float = 0
    teammate_block: int = 0
    teammate_block_adj: float = 0
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

    @model_validator(mode="before")
    @classmethod
    def fix_lists(cls, data):
        """Convert list fields to comma-separated strings before validation."""
        return _fix_lists(data, cls.model_fields)

    @field_validator(
        "goal",
        "goal_adj",
        "hd_goal",
        "shot",
        "shot_adj",
        "hd_shot",
        "miss",
        "miss_adj",
        "hd_miss",
        "fenwick",
        "fenwick_adj",
        "hd_fenwick",
        "corsi",
        "corsi_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
        "hit",
        "give",
        "take",
        "fac",
        "penl",
        "change",
        "stop",
        "chl",
        "ozf",
        "nzf",
        "dzf",
        "ozc",
        "nzc",
        "dzc",
        "otf",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def fix_stats(cls, v):
        """If statistic is None or empty, returns 0."""
        if not v:
            return 0

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
    """Documentation schema for the base_xg feature fields computed by the scraper.

    These fields are populated on every fenwick event in the PBP output and
    serve as inputs to the inference API's base_xg model. Kept as a reference
    for expected feature names, types, and nullability.
    """

    period: int
    period_seconds: int
    score_diff: int
    danger: int
    high_danger: int
    position: str  # "F", "D", or "G"
    shot_type: str  # lowercase e.g. "wrist"
    strength_state: str  # e.g. "5v5"
    event_distance: float
    event_angle: float | None
    coords_x: float
    coords_y: float
    is_rebound: int
    rush_attempt: int
    is_scramble: int
    is_home: int
    seconds_since_last: float | None = None
    distance_from_last: float | None = None
    play_speed: float | None = None
    prior_event_angle: float | None = None
    prior_event_distance: float | None = None
    seconds_since_stoppage: float | None = None
    abs_y_distance: float
    prior_event_same: str | None = None  # "SHOT" | "MISS" | "BLOCK" | "GIVE" | "TAKE" | "HIT"
    prior_event_opp: str | None = None
    prior_face: int


class ScheduleGame(ChickenBaseModel):
    """Pydantic model for validating schedule data."""

    session: int
    game_date: str
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
    game_date_dt_local: dt.datetime
    game_date_dt_utc: dt.datetime
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
    conference: str | None
    division: str | None
    games_played: int
    points: int | None = None
    points_pct: float | None = None
    wins: int
    regulation_wins: int
    shootout_wins: int | None = None
    losses: int
    ot_losses: int | None = None
    shootout_losses: int | None = None
    ties: int | None = None
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
