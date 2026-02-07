# from pathlib import Path

import numpy as np
import pandas as pd

import polars as pl

from typing import Literal

# import mlflow
# from sklearn.model_selection import train_test_split
#
# import matplotlib.pyplot as plt
# import shap
# from yellowbrick.classifier import (
#     ClassificationReport,
#     ClassPredictionError,
#     ROCAUC,
#     PrecisionRecallCurve,
#     ConfusionMatrix,
# )
# from yellowbrick.model_selection import FeatureImportances
from chickenstats.chicken_nhl.validation import XGSchema


def prep_data_pandas(data: pd.DataFrame, strengths: str) -> pd.DataFrame:
    """Function for prepping play-by-play data for xG experiments.

    Data are play-by-play data from the chickenstats function.

    Strengths can be: even, powerplay, shorthanded, empty_for, empty_against
    """
    df = data.copy()

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

    conds = np.logical_and.reduce(
        [df.event.isin(events), df.strength_state != "1v0", pd.notnull(df.coords_x), pd.notnull(df.coords_y)]
    )

    df = df.loc[conds]

    conds = np.logical_and.reduce(
        [df.season == df.season.shift(1), df.game_id == df.game_id.shift(1), df.period == df.period.shift(1)]
    )
    df["seconds_since_last"] = np.where(conds, df.game_seconds - df.game_seconds.shift(1), np.nan)
    df["event_type_last"] = np.where(conds, df.event.shift(1), np.nan)
    df["event_team_last"] = np.where(conds, df.event_team.shift(1), np.nan)
    df["event_strength_last"] = np.where(conds, df.strength_state.shift(1), np.nan)
    df["coords_x_last"] = np.where(conds, df.coords_x.shift(1), np.nan)
    df["coords_y_last"] = np.where(conds, df.coords_y.shift(1), np.nan)
    df["zone_last"] = np.where(conds, df.zone.shift(1), np.nan)

    df["same_team_last"] = np.where(np.equal(df.event_team, df.event_team_last), 1, 0)

    df["distance_from_last"] = ((df.coords_x - df.coords_x_last) ** 2 + (df.coords_y - df.coords_y_last) ** 2) ** (
        1 / 2
    )

    last_is_shot = np.equal(df.event_type_last, "SHOT")
    last_is_miss = np.equal(df.event_type_last, "MISS")
    last_is_block = np.equal(df.event_type_last, "BLOCK")
    last_is_give = np.equal(df.event_type_last, "GIVE")
    last_is_take = np.equal(df.event_type_last, "TAKE")
    last_is_hit = np.equal(df.event_type_last, "HIT")
    last_is_fac = np.equal(df.event_type_last, "FAC")

    same_team_as_last = np.equal(df.same_team_last, 1)
    not_same_team_as_last = np.equal(df.same_team_last, 0)

    df["prior_shot_same"] = np.where((last_is_shot & same_team_as_last), 1, 0)
    df["prior_miss_same"] = np.where((last_is_miss & same_team_as_last), 1, 0)
    df["prior_block_same"] = np.where((last_is_block & same_team_as_last), 1, 0)
    df["prior_give_same"] = np.where((last_is_give & same_team_as_last), 1, 0)
    df["prior_take_same"] = np.where((last_is_take & same_team_as_last), 1, 0)
    df["prior_hit_same"] = np.where((last_is_hit & same_team_as_last), 1, 0)

    df["prior_shot_opp"] = np.where((last_is_shot & not_same_team_as_last), 1, 0)
    df["prior_miss_opp"] = np.where((last_is_miss & not_same_team_as_last), 1, 0)
    df["prior_block_opp"] = np.where((last_is_block & not_same_team_as_last), 1, 0)
    df["prior_give_opp"] = np.where((last_is_give & not_same_team_as_last), 1, 0)
    df["prior_take_opp"] = np.where((last_is_take & not_same_team_as_last), 1, 0)
    df["prior_hit_opp"] = np.where((last_is_hit & not_same_team_as_last), 1, 0)

    df["prior_face"] = np.where(last_is_fac, 1, 0)

    shot_types = pd.get_dummies(df.shot_type, dtype=int)

    shot_types = shot_types.rename(
        columns={x: x.lower().replace("-", "_").replace(" ", "_") for x in shot_types.columns}
    )

    df = df.copy().merge(shot_types, left_index=True, right_index=True, how="outer")

    conds = [df.score_diff > 4, df.score_diff < -4]

    values = [4, -4]

    df.score_diff = np.select(conds, values, df.score_diff)

    conds = [df.player_1_position.isin(["F", "L", "R", "C"]), df.player_1_position == "D", df.player_1_position == "G"]

    values = ["F", "D", "G"]

    df["position_group"] = np.select(conds, values, default="F")

    position_dummies = pd.get_dummies(df.position_group, dtype=int)

    new_cols = {x: f"position_{x.lower()}" for x in values}

    position_dummies = position_dummies.rename(columns=new_cols)

    df = df.merge(position_dummies, left_index=True, right_index=True)

    conds = [
        np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "BLOCK", "MISS"]),
                df.event_type_last.isin(["SHOT", "MISS"]),
                df.event_team_last == df.event_team,
                df.game_id == df.game_id.shift(1),
                df.period == df.period.shift(1),
                df.seconds_since_last <= 3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "BLOCK", "MISS"]),
                df.event_type_last == "BLOCK",
                df.event_team_last == df.opp_team,
                df.game_id == df.game_id.shift(1),
                df.period == df.period.shift(1),
                df.seconds_since_last <= 3,
            ]
        ),
    ]

    values = [1, 1]

    df["is_rebound"] = np.select(conds, values, 0)

    conds = np.logical_and.reduce(
        [
            df.event.isin(["GOAL", "SHOT", "BLOCK", "MISS"]),
            df.seconds_since_last <= 4,
            df.zone_last == "NEU",
            df.game_id == df.game_id.shift(1),
            df.period == df.period.shift(1),
            df.event != "FAC",
        ]
    )

    df["rush_attempt"] = np.where(conds, 1, 0)

    cat_cols = ["strength_state", "position_group", "event_type_last"]

    for col in cat_cols:
        dummies = pd.get_dummies(df[col], dtype=int)

        new_cols = {x: f"{col}_{x}" for x in dummies.columns}

        dummies = dummies.rename(columns=new_cols)

        df = df.copy().merge(dummies, left_index=True, right_index=True)

    if strengths.lower() == "even":
        strengths_list = ["5v5", "4v4", "3v3"]

    if strengths.lower() == "powerplay" or strengths.lower() == "pp":
        strengths_list = ["5v4", "4v3", "5v3"]

    if strengths.lower() == "shorthanded" or strengths.lower() == "ss":
        strengths_list = ["4v5", "3v4", "3v5"]

    if strengths.lower() == "empty_for":
        strengths_list = ["Ev5", "Ev4", "Ev3"]

    if strengths.lower() == "empty_against":
        strengths_list = ["5vE", "4vE", "3vE"]

    conds = np.logical_and.reduce([df.event.isin(["GOAL", "SHOT", "MISS"]), df.strength_state.isin(strengths_list)])

    df = df.loc[conds]

    drop_cols = [
        x for x in df.columns if "strength_state_" in x and x not in [f"strength_state_{x}" for x in strengths_list]
    ] + cat_cols

    df = df.drop(drop_cols, axis=1, errors="ignore")

    df = XGSchema.validate(df[[x for x in XGSchema.dtypes if x in df.columns]])

    return df


def prep_data_polars(
    df: pl.DataFrame, strengths: Literal["even", "powerplay", "shorthanded", "empty_for", "empty_against"]
) -> pl.DataFrame:
    """Docstring."""
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
        pl.col("coords_x").is_not_nan(),
        pl.col("coords_y").is_not_nan(),
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

    rebound_conditions = conditions + (
        pl.col("event").is_in(corsi_events),
        pl.col("event").shift(1).is_in(fenwick_events),
        pl.col("event_team") == pl.col("event_team").shift(1),
        (pl.col("game_seconds") - pl.col("game_seconds").shift(1)) <= 3,
    ) or conditions + (
        pl.col("event").is_in(corsi_events),
        pl.col("event").shift(1) == "BLOCK",
        pl.col("event_team") != pl.col("event_team").shift(1),
        (pl.col("game_seconds") - pl.col("game_seconds").shift(1)) <= 3,
    )

    rush_attempt_conditions = conditions + (
        pl.col("event").is_in(corsi_events),
        (pl.col("game_seconds") - pl.col("game_seconds").shift(1)) <= 4,
        pl.col("zone").shift(1) == "NEU",
        pl.col("event").shift(1) == "FAC",
    )

    position_map = {"F": "F", "L": "F", "R": "F", "C": "F"}

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
        strength_state2=pl.col("strength_state"),
        position=pl.col("player_1_position").replace_strict(position_map, default=pl.col("player_1_position")),
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

    dummy_columns = ["strength_state2", "position", "shot_type"]

    df = df.to_dummies(columns=dummy_columns, drop_nulls=True)

    rename_cols = {
        x: x.lower().replace("shot_type_", "").replace("strength_state2_", "strength_state_")
        for x in df.columns
        if "shot_type_" in x or "position_" in x or "strength_state2_" in x
    }

    df = df.rename(rename_cols)

    select_columns = [
        "season",
        "goal",
        "period",
        "period_seconds",
        "score_diff",
        "danger",
        "high_danger",
        "position_f",
        "position_d",
        "position_g",
        "event_distance",
        "event_angle",
        "is_rebound",
        "rush_attempt",
        "is_home",
        "seconds_since_last",
        "distance_from_last",
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
        "backhand",
        "bat",
        "between_legs",
        "cradle",
        "deflected",
        "poke",
        "slap",
        "snap",
        "tip_in",
        "wrap_around",
        "wrist",
        # "strength_state_3v3",
        # "strength_state_4v4",
        # "strength_state_5v5",
        # "strength_state_3v4",
        # "strength_state_3v5",
        # "strength_state_4v5",
        # "strength_state_4v3",
        # "strength_state_5v3",
        # "strength_state_5v4",
        # "strength_state_Ev3",
        # "strength_state_Ev4",
        # "strength_state_Ev5",
        # "strength_state_3vE",
        # "strength_state_4vE",
        # "strength_state_5vE",
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

    select_columns = select_columns + [
        f"strength_state_{x}" for x in strengths_list if f"strength_state_{x}" in df.columns
    ]

    filter_conditions = (pl.col("event").is_in(fenwick_events), pl.col("strength_state").is_in(strengths_list))

    df = df.filter(filter_conditions).select(select_columns)

    return df
