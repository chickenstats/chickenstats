from xgboost import XGBClassifier
from pathlib import Path
import numpy as np
import pandas as pd


def load_model(model_name, model_version):
    file_name = Path(
        f"./chickenstats/chicken_nhl/xg_models/{model_name}-{model_version}.json"
    )

    model = XGBClassifier()
    model = model.load_model(file_name)

    return model


def prep_data(data, strengths):
    """
    Function for prepping play-by-play data for xG experiments

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
        [
            df.event.isin(events),
            df.strength_state != "1v0",
            pd.notnull(df.coords_x),
            pd.notnull(df.coords_y),
        ]
    )

    df = df.loc[conds]

    conds = np.logical_and.reduce(
        [
            df.season == df.season.shift(1),
            df.game_id == df.game_id.shift(1),
            df.period == df.period.shift(1),
        ]
    )
    df["seconds_since_last"] = np.where(
        conds, df.game_seconds - df.game_seconds.shift(1), np.nan
    )
    df["event_type_last"] = np.where(conds, df.event.shift(1), np.nan)
    df["event_team_last"] = np.where(conds, df.event_team.shift(1), np.nan)
    df["event_strength_last"] = np.where(conds, df.strength_state.shift(1), np.nan)
    df["coords_x_last"] = np.where(conds, df.coords_x.shift(1), np.nan)
    df["coords_y_last"] = np.where(conds, df.coords_y.shift(1), np.nan)
    df["zone_last"] = np.where(conds, df.zone.shift(1), np.nan)

    df["same_team_last"] = np.where(np.equal(df.event_team, df.event_team_last), 1, 0)

    df["distance_from_last"] = (
        (df.coords_x - df.coords_x_last) ** 2 + (df.coords_y - df.coords_y_last) ** 2
    ) ** (1 / 2)

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
        columns={
            x: x.lower().replace("-", "_").replace(" ", "_") for x in shot_types.columns
        }
    )

    df = df.copy().merge(shot_types, left_index=True, right_index=True, how="outer")

    conds = [df.score_diff > 4, df.score_diff < -4]

    values = [4, -4]

    df.score_diff = np.select(conds, values, df.score_diff)

    conds = [
        df.player_1_position.isin(["F", "L", "R", "C"]),
        df.player_1_position == "D",
        df.player_1_position == "G",
    ]

    values = ["F", "D", "G"]

    df["position_group"] = np.select(conds, values)

    conds = [
        np.logical_and.reduce(
            [
                df.event.isin(
                    [
                        "GOAL",
                        "SHOT",
                        "BLOCK",
                        "MISS",
                    ]
                ),
                df.event_type_last.isin(["SHOT", "MISS"]),
                df.event_team_last == df.event_team,
                df.game_id == df.game_id.shift(1),
                df.period == df.period.shift(1),
                df.seconds_since_last <= 3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.event.isin(
                    [
                        "GOAL",
                        "SHOT",
                        "BLOCK",
                        "MISS",
                    ]
                ),
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
            df.event.isin(
                [
                    "GOAL",
                    "SHOT",
                    "BLOCK",
                    "MISS",
                ]
            ),
            df.seconds_since_last <= 4,
            df.zone_last == "NEU",
            df.game_id == df.game_id.shift(1),
            df.period == df.period.shift(1),
            df.event != "FAC",
        ]
    )

    df["rush_attempt"] = np.where(conds, 1, 0)

    cat_cols = [
        "strength_state",
        "position_group",
        "event_type_last",
    ]

    for col in cat_cols:
        dummies = pd.get_dummies(df[col], dtype=int)

        new_cols = {x: f"{col}_{x}" for x in dummies.columns}

        dummies = dummies.rename(columns=new_cols)

        df = df.copy().merge(dummies, left_index=True, right_index=True)

        # df = df.drop(col, axis=1)

    if strengths.lower() == "even":
        strengths_list = ["5v5", "4v4", "3v3"]

        conds = np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "MISS"]),
                df.strength_state.isin(strengths_list),
            ]
        )

        df = df.loc[conds]

        drop_cols = [
            x for x in df.columns if "strength_state_" in x and x not in strengths_list
        ]

        df = df.drop(drop_cols, axis=1, errors="ignore")

    if strengths.lower() == "powerplay" or strengths.lower() == "pp":
        strengths_list = ["5v4", "4v3", "5v3"]
        conds = np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "MISS"]),
                df.strength_state.isin(strengths_list),
            ]
        )

        df = df.loc[conds]

        drop_cols = [
            x
            for x in df.columns
            if "strength_state_" in x
            and x not in [f"strength_state_{x}" for x in strengths_list]
        ]

        df = df.drop(drop_cols, axis=1, errors="ignore")

    if strengths.lower() == "shorthanded" or strengths.lower() == "ss":
        strengths_list = ["4v5", "3v4", "3v5"]
        conds = np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "MISS"]),
                df.strength_state.isin(strengths_list),
            ]
        )

        df = df.loc[conds]

        drop_cols = [
            x
            for x in df.columns
            if "strength_state_" in x
            and x not in [f"strength_state_{x}" for x in strengths_list]
        ]

        df = df.drop(drop_cols, axis=1, errors="ignore")

    if strengths.lower() == "empty_for":
        strengths_list = ["Ev5", "Ev4", "Ev3"]
        conds = np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "MISS"]),
                df.strength_state.isin(strengths_list),
            ]
        )

        df = df.loc[conds]

        drop_cols = [
            x
            for x in df.columns
            if "strength_state_" in x
            and x not in [f"strength_state_{x}" for x in strengths_list]
        ]

        df = df.drop(drop_cols, axis=1, errors="ignore")

    if strengths.lower() == "empty_against":
        strengths_list = ["5vE", "4vE", "3vE"]
        conds = np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "MISS"]),
                df.strength_state.isin(strengths_list),
            ]
        )

        df = df.loc[conds]

        drop_cols = [
            x
            for x in df.columns
            if "strength_state_" in x
            and x not in [f"strength_state_{x}" for x in strengths_list]
        ]

        df = df.drop(drop_cols, axis=1, errors="ignore")

    df = df.drop(cat_cols, axis=1, errors="ignore")

    cols = [
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
    ]

    for col in cols:
        if col not in df.columns:
            df[col] = 0

    cols = [
        "season",
        "goal",
        "period",
        "period_seconds",
        # "score_state",
        "score_diff",
        "danger",
        "high_danger",
        # "coords_x",
        # "coords_y",
        "player_1_age",
        "player_1_height",
        "player_1_weight",
        "position_group",
        # "shooter_good_hand",
        "shot_distance_from_mean",
        "event_distance",
        "event_angle",
        "is_rebound",
        "rush_attempt",
        "is_home",
        "own_goalie_age",
        "own_goalie_height",
        "own_goalie_weight",
        "forwards_ages_mean",
        "forwards_height_mean",
        "forwards_weight_mean",
        "defense_ages_mean",
        "defense_height_mean",
        "defense_weight_mean",
        "opp_goalie_age",
        "opp_goalie_height",
        "opp_goalie_weight",
        "opp_forwards_ages_mean",
        "opp_forwards_height_mean",
        "opp_forwards_weight_mean",
        "opp_defense_ages_mean",
        "opp_defense_height_mean",
        "opp_defense_weight_mean",
        "seconds_since_last",
        "event_type_last",
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
        "strength_state_3v3",
        "strength_state_4v4",
        "strength_state_5v5",
        "strength_state_3v4",
        "strength_state_3v5",
        "strength_state_4v5",
        "strength_state_4v3",
        "strength_state_5v3",
        "strength_state_5v4",
        "strength_state_Ev3",
        "strength_state_Ev4",
        "strength_state_Ev5",
        "strength_state_3vE",
        "strength_state_4vE",
        "strength_state_5vE",
        "player_1_hand_L",
        "player_1_hand_R",
        # "player_1_position_C",
        # "player_1_position_D",
        # "player_1_position_G",
        # "player_1_position_L",
        # "player_1_position_R",
        "opp_goalie_catches_L",
        "opp_goalie_catches_R",
    ]

    cols = [x for x in cols if x in df.columns]

    df = df[cols].copy()

    if strengths.lower() == "empty_for":
        drop_cols = [x for x in df.columns if "own_goalie" in x]

        df = df.drop(drop_cols, axis=1)

    if strengths.lower() == "empty_against":
        drop_cols = [x for x in df.columns if "opp_goalie" in x]

        df = df.drop(drop_cols, axis=1)

    for col in df.columns:
        df[col] = pd.to_numeric(df[col])

    conds = [df.goal == True, df.goal == False]

    values = [1, 0]

    df.goal = np.select(conds, values, df.goal)

    df = df.fillna(0)

    return df


model_version = "0.1.0"

es_model = load_model("even-strength", model_version)
pp_model = load_model("powerplay", model_version)
sh_model = load_model("shorthanded", model_version)
ea_model = load_model("empty-against", model_version)
ef_model = load_model("empty-for", model_version)
