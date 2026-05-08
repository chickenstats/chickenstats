import polars as pl

from typing import Literal

from chickenstats.chicken_nhl._validation_schema import polars_dtype_map, polars_pandera_options
from chickenstats.chicken_nhl._validation_utils import build_pandera_schema
from chickenstats.utilities.enums import Zone

# ------------------------------
# Dictionaries for schema used to build the various pandera DataFrameSchema
# ------------------------------

# Columns and column options used in the xG DataFrameSchema
xg_fields = {
    "season": {"dtype": int, "nullable": False, "default": False, "required": True},
    "goal": {"dtype": int, "nullable": False, "default": False, "required": True},
    "period": {"dtype": int, "nullable": False, "default": False, "required": True},
    "period_seconds": {"dtype": int, "nullable": False, "default": False, "required": True},
    "score_diff": {"dtype": int, "nullable": False, "default": False, "required": True},
    "danger": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "high_danger": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "position": {"dtype": str, "nullable": False, "default": False, "required": True},
    "shot_type": {"dtype": str, "nullable": True, "default": False, "required": True},
    "strength_state": {"dtype": str, "nullable": False, "default": False, "required": True},
    "event_distance": {"dtype": float, "nullable": False, "default": False, "required": True},
    "event_angle": {"dtype": float, "nullable": True, "default": False, "required": True},
    "is_rebound": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "rush_attempt": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "is_home": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "seconds_since_last": {"dtype": float, "nullable": True, "default": False, "required": True},
    "distance_from_last": {"dtype": float, "nullable": True, "default": False, "required": True},
    "play_speed": {"dtype": float, "nullable": True, "default": False, "required": True},
    "rebound_angle_change": {"dtype": float, "nullable": True, "default": False, "required": True},
    "rebound_time_delta": {"dtype": float, "nullable": True, "default": False, "required": True},
    "seconds_since_stoppage": {"dtype": float, "nullable": True, "default": False, "required": True},
    "abs_y_distance": {"dtype": float, "nullable": False, "default": False, "required": True},
    "prior_shot_same": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_miss_same": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_block_same": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_give_same": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_take_same": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_hit_same": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_shot_opp": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_miss_opp": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_block_opp": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_give_opp": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_take_opp": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_hit_opp": {"dtype": int, "nullable": False, "default": 0, "required": True},
    "prior_face": {"dtype": int, "nullable": False, "default": 0, "required": True},
    # Passthrough — needed for informed_xg join operations; excluded from training feature matrix
    "game_id": {"dtype": int, "nullable": False, "default": False, "required": False},
    "player_1_api_id": {"dtype": int, "nullable": True, "default": False, "required": False},
    "opp_goalie_api_id": {"dtype": int, "nullable": True, "default": False, "required": False},
    "session": {"dtype": str, "nullable": False, "default": False, "required": False},
    "home_on_api_id": {"dtype": str, "nullable": True, "default": False, "required": False},
    "away_on_api_id": {"dtype": str, "nullable": True, "default": False, "required": False},
    # Model 1 output — direct feature in informed_xg; monotonic constraint: +1
    "env_xg": {"dtype": float, "nullable": True, "default": False, "required": False},
    # Shooter GxG rolling windows (4 windows × 2 values = 8 columns)
    "shooter_gax_career": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_per_shot_career": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_season": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_per_shot_season": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_10g": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_per_shot_10g": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_1g": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_gax_per_shot_1g": {"dtype": float, "nullable": True, "default": False, "required": False},
    # Goalie GSAx rolling windows (4 windows × 2 values = 8 columns)
    "goalie_gsax_career": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_per_shot_career": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_season": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_per_shot_season": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_10g": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_per_shot_10g": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_1g": {"dtype": float, "nullable": True, "default": False, "required": False},
    "goalie_gsax_per_shot_1g": {"dtype": float, "nullable": True, "default": False, "required": False},
    # RAPM features — lagged 1 season, situation-matched
    "shooter_rapm_off": {"dtype": float, "nullable": True, "default": False, "required": False},
    "shooter_rapm_def": {"dtype": float, "nullable": True, "default": False, "required": False},
    "opp_rapm_off": {"dtype": float, "nullable": True, "default": False, "required": False},
    "opp_rapm_def": {"dtype": float, "nullable": True, "default": False, "required": False},
    "teammates_rapm_off": {"dtype": float, "nullable": True, "default": False, "required": False},
    "teammates_rapm_def": {"dtype": float, "nullable": True, "default": False, "required": False},
}

xg_pandera_polars = build_pandera_schema(
    xg_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)


def prep_data(
    df: pl.DataFrame, strengths: Literal["even", "powerplay", "shorthanded", "empty_for", "empty_against"]
) -> pl.DataFrame:
    """Docstring."""
    if "pred_goal" in df.columns:
        df = df.drop(["pred_goal"])

    events = [
        "SHOT",
        "FAC",
        "HIT",
        "BLOCK",
        "MISS",
        "GIVE",
        "TAKE",
        # "PENL",
        "GOAL",
    ]

    df = df.filter(
        pl.col("event").is_in(events),
        pl.col("strength_state") != "1v0",
        pl.col("strength_state") != "EvE",
        pl.col("coords_x").is_not_null(),
        pl.col("coords_y").is_not_null(),
    )

    conditions = (
        pl.col("season") == pl.col("season").shift(1),
        pl.col("game_id") == pl.col("game_id").shift(1),
        pl.col("period") == pl.col("period").shift(1),
    )

    same_team_last_conditions = conditions + (pl.col("event_team") == pl.col("event_team").shift(1),)
    not_same_team_last_conditions = conditions + (pl.col("event_team") != pl.col("event_team").shift(1),)
    prior_faceoff_conditions = conditions + (pl.col("event").shift(1) == "FAC",)

    prior_shot_same_conditions = same_team_last_conditions + (pl.col("event").shift(1) == "SHOT",)
    prior_miss_same_conditions = same_team_last_conditions + (pl.col("event").shift(1) == "MISS",)
    prior_block_same_conditions = same_team_last_conditions + (pl.col("event").shift(1) == "BLOCK",)
    prior_give_same_conditions = same_team_last_conditions + (pl.col("event").shift(1) == "GIVE",)
    prior_take_same_conditions = same_team_last_conditions + (pl.col("event").shift(1) == "TAKE",)
    prior_hit_same_conditions = same_team_last_conditions + (pl.col("event").shift(1) == "HIT",)

    prior_shot_opp_conditions = not_same_team_last_conditions + (pl.col("event").shift(1) == "SHOT",)
    prior_miss_opp_conditions = not_same_team_last_conditions + (pl.col("event").shift(1) == "MISS",)
    prior_block_opp_conditions = not_same_team_last_conditions + (pl.col("event").shift(1) == "BLOCK",)
    prior_give_opp_conditions = not_same_team_last_conditions + (pl.col("event").shift(1) == "GIVE",)
    prior_take_opp_conditions = not_same_team_last_conditions + (pl.col("event").shift(1) == "TAKE",)
    prior_hit_opp_conditions = not_same_team_last_conditions + (pl.col("event").shift(1) == "HIT",)

    corsi_events = ["GOAL", "SHOT", "MISS", "BLOCK"]
    fenwick_events = ["SHOT", "MISS"]

    _sec_diff = pl.col("game_seconds") - pl.col("game_seconds").shift(1)
    _base_rebound = (
        (pl.col("season") == pl.col("season").shift(1))
        & (pl.col("game_id") == pl.col("game_id").shift(1))
        & (pl.col("period") == pl.col("period").shift(1))
        & pl.col("event").is_in(corsi_events)
        & (_sec_diff <= 3)
    )
    rebound_conditions = (
        _base_rebound
        & pl.col("event").shift(1).is_in(fenwick_events)
        & (pl.col("event_team") == pl.col("event_team").shift(1))
    ) | (
        _base_rebound & (pl.col("event").shift(1) == "BLOCK") & (pl.col("event_team") != pl.col("event_team").shift(1))
    )

    rush_attempt_conditions = conditions + (
        pl.col("event").is_in(corsi_events),
        _sec_diff <= 4,
        pl.col("zone").shift(1) == Zone.NEUTRAL,
    )

    position_map = {"F": "F", "L": "F", "R": "F", "C": "F", "D": "D", "G": "G"}

    df = df.with_columns(
        score_diff=pl.when(pl.col("score_diff") > 4)
        .then(pl.lit(4))
        .otherwise(pl.when(pl.col("score_diff") < -4).then(pl.lit(-4)).otherwise(pl.col("score_diff"))),
        seconds_since_last=pl.when(conditions)
        .then(pl.col("game_seconds") - pl.col("game_seconds").shift(1))
        .otherwise(float("nan")),
        distance_from_last=pl.when(conditions)
        .then(
            (
                ((pl.col("coords_x") - pl.col("coords_x").shift(1)) ** 2)
                + ((pl.col("coords_y") - pl.col("coords_y").shift(1)) ** 2)
            )
            ** (1 / 2)
        )
        .otherwise(float("nan")),
        position=pl.col("player_1_position").replace_strict(position_map, default=pl.lit("F")),
        is_rebound=pl.when(rebound_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        rush_attempt=pl.when(rush_attempt_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_face=pl.when(prior_faceoff_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_shot_same=pl.when(prior_shot_same_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_miss_same=pl.when(prior_miss_same_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_block_same=pl.when(prior_block_same_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_give_same=pl.when(prior_give_same_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_take_same=pl.when(prior_take_same_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_hit_same=pl.when(prior_hit_same_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_shot_opp=pl.when(prior_shot_opp_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_miss_opp=pl.when(prior_miss_opp_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_block_opp=pl.when(prior_block_opp_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_give_opp=pl.when(prior_give_opp_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_take_opp=pl.when(prior_take_opp_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
        prior_hit_opp=pl.when(prior_hit_opp_conditions).then(pl.lit(1)).otherwise(pl.lit(0)),
    )

    df = df.with_columns(
        _last_face_seconds=pl.when(pl.col("event") == "FAC")
        .then(pl.col("game_seconds"))
        .otherwise(None)
        .forward_fill()
        .over("game_id")
    )

    df = df.with_columns(
        play_speed=pl.when(pl.col("seconds_since_last").is_not_null() & (pl.col("seconds_since_last") > 0))
        .then(pl.col("distance_from_last") / pl.col("seconds_since_last"))
        .otherwise(None),
        rebound_angle_change=pl.when(pl.col("is_rebound") == 1)
        .then(pl.col("event_angle") - pl.col("event_angle").shift(1))
        .otherwise(float("nan")),
        rebound_time_delta=pl.when(pl.col("is_rebound") == 1)
        .then(pl.col("seconds_since_last"))
        .otherwise(float("nan")),
        seconds_since_stoppage=(pl.col("game_seconds") - pl.col("_last_face_seconds")).cast(pl.Float64),
        abs_y_distance=pl.col("coords_y").abs(),
    ).drop("_last_face_seconds")

    df = df.with_columns(
        shot_type=pl.col("shot_type").str.to_lowercase().str.replace_all("-", "_").str.replace_all(" ", "_")
    )

    select_columns = [
        "season",
        "goal",
        "period",
        "period_seconds",
        "score_diff",
        "danger",
        "high_danger",
        "position",
        "shot_type",
        "strength_state",
        "event_distance",
        "event_angle",
        "is_rebound",
        "rush_attempt",
        "is_home",
        "seconds_since_last",
        "distance_from_last",
        "play_speed",
        "rebound_angle_change",
        "rebound_time_delta",
        "seconds_since_stoppage",
        "abs_y_distance",
        "prior_shot_same",
        "prior_miss_same",
        "prior_block_same",
        "prior_give_same",
        "prior_take_same",
        "prior_hit_same",
        "prior_shot_opp",
        "prior_miss_opp",
        "prior_block_opp",
        "prior_give_opp",
        "prior_take_opp",
        "prior_hit_opp",
        "prior_face",
        # Passthrough — present in parquets for downstream joins; excluded from training matrix
        "game_id",
        "player_1_api_id",
        "opp_goalie_api_id",
        "session",
        "home_on_api_id",
        "away_on_api_id",
        # informed_xg talent features — absent in env_xg pipeline, picked up when present
        "env_xg",
        "shooter_gax_career",
        "shooter_gax_per_shot_career",
        "shooter_gax_season",
        "shooter_gax_per_shot_season",
        "shooter_gax_10g",
        "shooter_gax_per_shot_10g",
        "shooter_gax_1g",
        "shooter_gax_per_shot_1g",
        "goalie_gsax_career",
        "goalie_gsax_per_shot_career",
        "goalie_gsax_season",
        "goalie_gsax_per_shot_season",
        "goalie_gsax_10g",
        "goalie_gsax_per_shot_10g",
        "goalie_gsax_1g",
        "goalie_gsax_per_shot_1g",
        "shooter_rapm_off",
        "shooter_rapm_def",
        "opp_rapm_off",
        "opp_rapm_def",
        "teammates_rapm_off",
        "teammates_rapm_def",
    ]

    select_columns = [x for x in select_columns if x in df.columns]

    fenwick_events = ["GOAL", "SHOT", "MISS"]

    if strengths == "even":
        strengths_list = ["5v5", "4v4", "3v3"]

    if strengths == "powerplay" or strengths.lower() == "pp":
        strengths_list = ["5v4", "4v3", "5v3"]

    if strengths == "shorthanded" or strengths.lower() == "ss":
        strengths_list = ["4v5", "3v4", "3v5"]

    if strengths == "empty_for":
        strengths_list = ["Ev5", "Ev4", "Ev3"]

    if strengths == "empty_against":
        strengths_list = ["5vE", "4vE", "3vE"]

    filter_conditions = (pl.col("event").is_in(fenwick_events), pl.col("strength_state").is_in(strengths_list))

    df = df.filter(filter_conditions).select(select_columns)

    schema_cols = list(xg_pandera_polars.columns.keys())
    df = xg_pandera_polars.validate(df.select([c for c in schema_cols if c in df.columns]))

    return df
