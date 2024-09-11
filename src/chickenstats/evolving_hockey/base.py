import pandas as pd
import numpy as np

import geopandas as gpd

from shapely.geometry.polygon import Polygon

from typing import Literal


def munge_pbp(pbp: pd.DataFrame) -> pd.DataFrame:
    """Prepares csv file of play-by-play data for use in the `prep_pbp` function.

    Parameters:
        pbp (pd.DataFrame):
            Pandas Dataframe of play-by-play data available from the queries section
            of evolving-hockey.com. Subscription required.

    """
    df = pbp.copy()

    # Common column names for ease of typing later

    EVENT_TEAM = df.event_team
    HOME_TEAM = df.home_team
    AWAY_TEAM = df.away_team
    EVENT_TYPE = df.event_type

    # Adding opp_team

    conditions = [EVENT_TEAM == HOME_TEAM, EVENT_TEAM == AWAY_TEAM]
    values = [AWAY_TEAM, HOME_TEAM]

    df["opp_team"] = np.select(conditions, values, np.nan)

    # Adding opp_goalie and own goalie

    values = [df.away_goalie, df.home_goalie]
    df["opp_goalie"] = np.select(
        conditions, values, np.nan
    )  # Uses same conditions as opp_team
    df.opp_goalie = df.opp_goalie.fillna("EMPTY NET")

    values.reverse()
    df["own_goalie"] = np.select(
        conditions, values, np.nan
    )  # Uses same conditions as opp_team
    df.own_goalie = df.own_goalie.fillna("EMPTY NET")

    # Adding event_on and opp_on

    for num in range(1, 8):
        home = df[f"home_on_{num}"]
        away = df[f"away_on_{num}"]

        conditions = [EVENT_TEAM == HOME_TEAM, EVENT_TEAM == AWAY_TEAM]
        values = [home, away]

        df[f"event_on_{num}"] = np.select(conditions, values, np.nan)

        values.reverse()

        df[f"opp_on_{num}"] = np.select(conditions, values, np.nan)

    # Adding zone_start

    conds_1 = np.logical_and(
        np.logical_and(EVENT_TYPE == "CHANGE", EVENT_TYPE.shift(-1) == "FAC"),
        np.logical_and(
            df.game_seconds == df.game_seconds.shift(-1),
            df.game_period == df.game_period.shift(-1),
        ),
    )

    conds_2 = np.logical_and(
        np.logical_and(EVENT_TYPE == "CHANGE", EVENT_TYPE.shift(-2) == "FAC"),
        np.logical_and(
            df.game_seconds == df.game_seconds.shift(-2),
            df.game_period == df.game_period.shift(-2),
        ),
    )

    conds_3 = np.logical_and(
        np.logical_and(EVENT_TYPE == "CHANGE", EVENT_TYPE.shift(-3) == "FAC"),
        np.logical_and(
            df.game_seconds == df.game_seconds.shift(-3),
            df.game_period == df.game_period.shift(-3),
        ),
    )

    conds_4 = np.logical_and(
        np.logical_and(EVENT_TYPE == "CHANGE", EVENT_TYPE.shift(-4) == "FAC"),
        np.logical_and(
            df.game_seconds == df.game_seconds.shift(-4),
            df.game_period == df.game_period.shift(-4),
        ),
    )

    conds_5 = np.logical_and(
        np.logical_and(EVENT_TYPE == "CHANGE", EVENT_TYPE.shift(-5) == "FAC"),
        np.logical_and(
            df.game_seconds == df.game_seconds.shift(-5),
            df.game_period == df.game_period.shift(-5),
        ),
    )

    conds_6 = np.logical_and(
        np.logical_and(EVENT_TYPE == "CHANGE", EVENT_TYPE.shift(-6) == "FAC"),
        np.logical_and(
            df.game_seconds == df.game_seconds.shift(-6),
            df.game_period == df.game_period.shift(-6),
        ),
    )

    conditions = [conds_1, conds_2, conds_3, conds_4, conds_5, conds_6]

    values = [
        df.home_zone.shift(-1),
        df.home_zone.shift(-2),
        df.home_zone.shift(-3),
        df.home_zone.shift(-4),
        df.home_zone.shift(-5),
        df.home_zone.shift(-6),
    ]

    df["zone_start"] = np.select(conditions, values, np.nan)

    is_away = EVENT_TEAM == AWAY_TEAM

    conditions = [
        np.logical_and(is_away, df.zone_start == "Off"),
        np.logical_and(is_away, df.zone_start == "Def"),
    ]

    values = ["Def", "Off"]

    df.zone_start = np.select(conditions, values, df.zone_start)

    df.zone_start = np.where(
        np.logical_and(EVENT_TYPE == "CHANGE", pd.isna(df.zone_start)),
        "otf",
        df.zone_start,
    )

    # df.zone_start = np.where(
    #    np.logical_or(df.clock_time == "0:00", df.clock_time == "20:00"),
    #    np.nan,
    #    df.zone_start,
    # )

    df.zone_start = df.zone_start.str.upper()

    df.event_zone = df.event_zone.str.upper()

    # Fixing strength states for changes preceding different strength states

    conditions = [conds_1, conds_2, conds_3, conds_4]

    values = [
        df.game_strength_state.shift(-1),
        df.game_strength_state.shift(-2),
        df.game_strength_state.shift(-3),
        df.game_strength_state.shift(-4),
    ]

    df.game_strength_state = np.select(conditions, values, df.game_strength_state)

    # Adding strength state & score state

    conditions = [EVENT_TEAM == HOME_TEAM, EVENT_TEAM == AWAY_TEAM]

    strength_split = df.game_strength_state.str.split("v", expand=True)

    values = [df.game_strength_state, strength_split[1] + "v" + strength_split[0]]
    df["strength_state"] = np.select(conditions, values, np.nan)

    values.reverse()
    df["opp_strength_state"] = np.select(conditions, values, np.nan)

    df.strength_state = np.where(
        df.game_strength_state == "illegal", "illegal", df.strength_state
    )

    df.opp_strength_state = np.where(
        df.game_strength_state == "illegal", "illegal", df.opp_strength_state
    )

    score_split = df.game_score_state.str.split("v", expand=True)

    values = [df.game_score_state, score_split[1] + "v" + score_split[0]]
    df["score_state"] = np.select(conditions, values, np.nan)

    values.reverse()
    df["opp_score_state"] = np.select(conditions, values, np.nan)

    # Swapping faceoff event_players

    conditions = np.logical_and(df.event_type == "FAC", EVENT_TEAM == HOME_TEAM)

    df.event_player_1, df.event_player_2 = np.where(
        conditions,
        [df.event_player_2, df.event_player_1],
        [df.event_player_1, df.event_player_2],
    )

    # Adding is_home dummy variable

    conditions = [df.event_team == df.home_team, df.event_team == df.away_team]
    values = [1, 0]

    df["is_home"] = np.select(conditions, values, np.nan)

    # Adding dummy variables

    dummies = pd.get_dummies(df.event_type, dtype=int)

    new_cols = {x: x.lower() for x in dummies.columns}

    df = pd.concat([df.copy(), dummies], axis=1).rename(columns=new_cols)

    conds = df.event_type == "FAC"

    columns = {"DEF": "dzf", "NEU": "nzf", "OFF": "ozf"}

    df = df.merge(
        pd.get_dummies(df[conds].event_zone, dtype=int).rename(columns=columns),
        how="left",
        left_index=True,
        right_index=True,
    )

    conds = df.event_type == "CHANGE"

    columns = {"DEF": "dzs", "NEU": "nzs", "OFF": "ozs", "OTF": "otf"}

    df = df.merge(
        pd.get_dummies(df[conds].zone_start, dtype=int).rename(columns=columns),
        how="left",
        left_index=True,
        right_index=True,
    )

    dummy_cols = ["dzf", "nzf", "ozf", "dzs", "nzs", "ozs", "otf"]

    df[dummy_cols] = df[dummy_cols].fillna(0).astype(int)

    # Calculating shots, corsi, & fenwick

    df["corsi"] = df.goal + df.shot + df.miss + df.block

    df["fenwick"] = df.goal + df.shot + df.miss

    df.shot = df.goal + df.shot

    # Adding penalty columns

    is_penalty = df.event_type == "PENL"

    penalty_list = ["0min", "2min", "4min", "5min", "10min"]

    conditions = [
        np.logical_and(is_penalty, df.event_detail == penalty)
        for penalty in penalty_list
    ]

    values = ["pen0", "pen2", "pen4", "pen5", "pen10"]

    df["penalty_type"] = np.select(conditions, values, "")

    df = pd.concat([df.copy(), pd.get_dummies(df.penalty_type, dtype=int)], axis=1)

    pen_cols = ["pen0", "pen2", "pen4", "pen5", "pen10"]

    for pen_col in pen_cols:
        if pen_col not in df.columns:
            df[pen_col] = 0

    # Fixing opening change

    conditions = (
        (df.event_type == "CHANGE")
        & (df.clock_time == "20:00")
        & (df.strength_state.str.contains("E"))
    )

    df.strength_state = np.where(
        conditions, df.strength_state.shift(-1), df.strength_state
    )

    df.opp_strength_state = np.where(
        conditions, df.opp_strength_state.shift(-1), df.opp_strength_state
    )

    df.opp_goalie = np.where(conditions, df.opp_goalie.shift(-1), df.opp_goalie)

    df.own_goalie = np.where(conditions, df.own_goalie.shift(-1), df.own_goalie)

    # Converting names to plain text

    player_cols = [
        col
        for col in pbp.columns
        if ("event_player" in col or "on_" in col or "_goalie" in col)
        and ("s_on" not in col)
    ]

    for col in player_cols:
        pbp[col] = (
            pbp[col]
            .astype(str)
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("utf-8")
        )

    # Replacing team names with codes that match NHL API

    replace_teams = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}

    for old, new in replace_teams.items():
        replace_cols = [col for col in df.columns if "_team" in col] + [
            "players_on",
            "players_off",
            "event_description",
        ]

        for col in replace_cols:
            df[col] = df[col].str.replace(old, new, regex=False)

    df["period_seconds"] = df.game_seconds - ((df.game_period - 1) * 1200)

    df.period_seconds = np.where(
        np.logical_and(df.game_period == 5, df.session == "R"), 0, df.period_seconds
    )

    # Adding danger and high danger dummy columns

    coords = gpd.GeoSeries(
        data=gpd.points_from_xy(df.coords_x, df.coords_y), index=df.index
    )

    high_danger1 = Polygon(np.array([[69, -9], [89, -9], [89, 9], [69, 9]]))
    high_danger2 = Polygon(np.array([[-69, -9], [-89, -9], [-89, 9], [-69, 9]]))

    danger1 = Polygon(
        np.array(
            [
                [89, 9],
                [89, -9],
                [69, -22],
                [54, -22],
                [54, -9],
                [44, -9],
                [44, 9],
                [54, 9],
                [54, 22],
                [69, 22],
            ]
        )
    )

    danger2 = Polygon(
        np.array(
            [
                [-89, 9],
                [-89, -9],
                [-69, -22],
                [-54, -22],
                [-54, -9],
                [-44, -9],
                [-44, 9],
                [-54, 9],
                [-54, 22],
                [-69, 22],
            ]
        )
    )

    high_danger1 = gpd.GeoSeries(data=high_danger1, index=df.index)
    high_danger2 = gpd.GeoSeries(data=high_danger2, index=df.index)

    danger1 = gpd.GeoSeries(data=danger1, index=df.index)
    danger2 = gpd.GeoSeries(data=danger2, index=df.index)

    shot_list = ["GOAL", "SHOT", "MISS"]

    conds = np.logical_or(
        np.logical_and.reduce(
            [
                coords.within(high_danger1),
                df.event_zone == "OFF",
                df.event_type.isin(shot_list),
            ]
        ),
        np.logical_and.reduce(
            [
                coords.within(high_danger2),
                df.event_zone == "OFF",
                df.event_type.isin(shot_list),
            ]
        ),
    )

    df["high_danger"] = np.where(conds, 1, 0)

    conds = np.logical_and(
        np.logical_and(~coords.within(high_danger1), ~coords.within(high_danger2)),
        np.logical_or(
            np.logical_and.reduce(
                [
                    coords.within(danger1),
                    df.event_zone == "OFF",
                    df.event_type.isin(shot_list),
                ]
            ),
            np.logical_and.reduce(
                [
                    coords.within(danger2),
                    df.event_zone == "OFF",
                    df.event_type.isin(shot_list),
                ]
            ),
        ),
    )

    df["danger"] = np.where(conds, 1, 0)

    df["hd_goal"] = df.high_danger * df.goal

    df["hd_shot"] = df.high_danger * df.shot

    df["hd_fenwick"] = df.high_danger * df.fenwick

    df["hd_miss"] = df.high_danger * df.miss

    # Adding adjusted G, xG, shot, corsi, and fenwick figures

    conds = [
        # 5v5
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score <= -3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score == -2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score == -1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score == 1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score == 2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 1,
                df.home_score - df.away_score >= 3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score <= -3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score == -2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score == -1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score == 1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score == 2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v5",
                df.is_home == 0,
                df.home_score - df.away_score >= 3,
            ]
        ),
        # 4v4
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score <= -3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score == -2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score == -1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score == 1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score == 2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 1,
                df.home_score - df.away_score >= 3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score <= -3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score == -2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score == -1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score == 1,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score == 2,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v4",
                df.is_home == 0,
                df.home_score - df.away_score >= 3,
            ]
        ),
        # 3v3
        np.logical_and(df.strength_state == "3v3", df.is_home == 1),
        np.logical_and(df.strength_state == "3v3", df.is_home == 0),
        # 5v4
        np.logical_and.reduce(
            [
                df.strength_state == "5v4",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v4",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v4",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v4",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v4",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v4",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v5",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        # 4v5
        np.logical_and.reduce(
            [
                df.strength_state == "4v5",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v5",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v5",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v5",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v5",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
        # 5v3
        np.logical_and.reduce(
            [
                df.strength_state == "5v3",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v3",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v3",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v3",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v3",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "5v3",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
        # 3v5
        np.logical_and.reduce(
            [
                df.strength_state == "3v5",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v5",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v5",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v5",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v5",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v5",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
        # 4v3
        np.logical_and.reduce(
            [
                df.strength_state == "4v3",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v3",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v3",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v3",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v3",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "4v3",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
        # 3v4
        np.logical_and.reduce(
            [
                df.strength_state == "3v4",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v4",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v4",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v4",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v4",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "3v4",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
        # 1v0
        np.logical_and.reduce(
            [
                df.strength_state == "1v0",
                df.is_home == 1,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "1v0",
                df.is_home == 1,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "1v0",
                df.is_home == 1,
                df.home_score - df.away_score > 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "1v0",
                df.is_home == 0,
                df.home_score - df.away_score < 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "1v0",
                df.is_home == 0,
                df.home_score - df.away_score == 0,
            ]
        ),
        np.logical_and.reduce(
            [
                df.strength_state == "1v0",
                df.is_home == 0,
                df.home_score - df.away_score > 0,
            ]
        ),
    ]

    weights = (
        # Home goal, while home team trailing, at 5v5
        ([0.938] * 3)
        +
        # Home goal, score tied at 5v5
        [0.945]
        +
        # Home goal, while home team leading, at 5v5
        ([0.988] * 3)
        +
        # Away goal, while home team trailing, at 5v5
        ([1.071] * 3)
        +
        # Away goal, score tied at 5v5
        [1.061]
        +
        # Away goal, while home team leading, at 5v5
        ([1.012] * 3)
        +
        # Home goal, at 4v4
        ([0.929] * 7)
        +
        # Away goal at 4v4
        ([1.082] * 7)
        +
        # Home goal at 3v3
        [1.033]
        +
        # Away goal at 3v3
        [0.969]
        +
        # Home goal, while home team trailing, at 5v4
        [0.860]
        +
        # Home goal, while score tied, at 5v4
        [0.933]
        +
        # Home goal, while home team leading, at 5v4
        [0.980]
        +
        # Away goal, while home team trailing, at 5v4
        [1.183]
        +
        # Away goal, while score tied, at 5v4
        [1.077]
        +
        # Away goal, while home team leading, at 5v4
        [1.006]
        +
        # Home goal, while home team trailing, at 4v5
        [1.183]
        +
        # Home goal, while score tied, at 4v5
        [1.077]
        +
        # Home goal, while home team leading, at 4v5
        [1.006]
        +
        # Away goal, while home team trailing, at 4v5
        [0.860]
        +
        # Away goal, while score tied, at 4v5
        [0.933]
        +
        # Away goal, while home team leading, at 4v5
        [0.980]
        +
        # Home goal, while home team trailing, at 5v3
        [0.840]
        +
        # Home goal, while score tied, at 5v3
        [0.927]
        +
        # Home goal, while home team leading, at 5v3
        [0.935]
        +
        # Away goal, while home team trailing, at 5v3
        [1.234]
        +
        # Away goal, while score tied, at 5v3
        [1.085]
        +
        # Away goal, while home team leading, at 5v3
        [1.075]
        +
        # Home goal, while home team trailing, at 3v5
        [1.234]
        +
        # Home goal, while score tied, at 3v5
        [1.085]
        +
        # Home goal, while home team leading, at 3v5
        [1.075]
        +
        # Away goal, while home team trailing, at 3v5
        [0.840]
        +
        # Away goal, while score tied, at 3v5
        [0.927]
        +
        # Away goal, while home team leading, at 3v5
        [0.935]
        +
        # Home goal, while home team trailing, at 4v3
        [0.769]
        +
        # Home goal, while score tied, at 4v3
        [0.923]
        +
        # Home goal, while home team leading, at 4v3
        [0.883]
        +
        # Away goal, while home team trailing, at 4v3
        [1.429]
        +
        # Away goal, while score tied, at 4v3
        [1.091]
        +
        # Away goal, while home team leading, at 4v3
        [1.153]
        +
        # Home goal, while home team trailing, at 3v4
        [1.429]
        +
        # Home goal, while score tied, at 3v4
        [1.091]
        +
        # Home goal, while home team leading, at 3v4
        [1.153]
        +
        # Away goal, while home team trailing, at 3v4
        [0.769]
        +
        # Away goal, while score tied, at 3v4
        [0.923]
        +
        # Away goal, while home team leading, at 3v4
        [0.883]
        +
        # Home goal, while home team trailing, at 1v0
        [1.172]
        +
        # Home goal, score tied at 1v0
        [1.053]
        +
        # Home goal, while home team leading, at 1v0
        [0.958]
        +
        # Away goal, while home team trailing, at 1v0
        [0.872]
        +
        # Away goal, score tied at 1v0
        [0.952]
        +
        # Away goal, while home team leading, at 1v0
        [1.045]
    )

    values = [df.goal * weight for weight in weights]

    df["goal_adj"] = np.select(conds, values)

    conds = conds[:-6]  # Don't need the 1v0 conditions for the other adjustments

    # xG weights

    weights = (
        # Home xG, while home team trailing, at 5v5
        ([0.923] * 3)
        +
        # Home xG, score tied at 5v5
        [0.954]
        +
        # Home xG, while home team leading, at 5v5
        ([0.991] * 3)
        +
        # Away xG, while home team trailing, at 5v5
        ([1.091] * 3)
        +
        # Away xG, score tied at 5v5
        [1.051]
        +
        # Away xG, while home team leading, at 5v5
        ([1.010] * 3)
        +
        # Home xG, at 4v4
        ([0.951] * 7)
        +
        # Away xG at 4v4
        ([1.055] * 7)
        +
        # Home xG at 3v3
        [1.006]
        +
        # Away xG at 3v3
        [0.994]
        +
        # Home xG, while home team trailing, at 5v4
        [0.844]
        +
        # Home xG, while score tied, at 5v4
        [0.912]
        +
        # Home xG, while home team leading, at 5v4
        [1.006]
        +
        # Away xG, while home team trailing, at 5v4
        [1.226]
        +
        # Away xG, while score tied, at 5v4
        [1.107]
        +
        # Away xG, while home team leading, at 5v4
        [0.994]
        +
        # Home xG, while home team trailing, at 4v5
        [1.226]
        +
        # Home xG, while score tied, at 4v5
        [1.107]
        +
        # Home xG, while home team leading, at 4v5
        [0.994]
        +
        # Away xG, while home team trailing, at 4v5
        [0.844]
        +
        # Away xG, while score tied, at 4v5
        [0.912]
        +
        # Away xG, while home team leading, at 4v5
        [1.006]
        +
        # Home xG, while home team trailing, at 5v3
        [0.801]
        +
        # Home xG, while score tied, at 5v3
        [0.896]
        +
        # Home xG, while home team leading, at 5v3
        [0.913]
        +
        # Away xG, while home team trailing, at 5v3
        [1.330]
        +
        # Away xG, while score tied, at 5v3
        [1.131]
        +
        # Away xG, while home team leading, at 5v3
        [1.105]
        +
        # Home xG, while home team trailing, at 3v5
        [1.330]
        +
        # Home xG, while score tied, at 3v5
        [1.131]
        +
        # Home xG, while home team leading, at 3v5
        [1.105]
        +
        # Away xG, while home team trailing, at 3v5
        [0.801]
        +
        # Away xG, while score tied, at 3v5
        [0.896]
        +
        # Away xG, while home team leading, at 3v5
        [0.913]
        +
        # Home xG, while home team trailing, at 4v3
        [0.820]
        +
        # Home xG, while score tied, at 4v3
        [0.912]
        +
        # Home xG, while home team leading, at 4v3
        [0.898]
        +
        # Away xG, while home team trailing, at 4v3
        [1.282]
        +
        # Away xG, while score tied, at 4v3
        [1.106]
        +
        # Away xG, while home team leading, at 4v3
        [1.129]
        +
        # Home xG, while home team trailing, at 3v4
        [1.282]
        +
        # Home xG, while score tied, at 3v4
        [1.106]
        +
        # Home xG, while home team leading, at 3v4
        [1.129]
        +
        # Away xG, while home team trailing, at 3v4
        [0.820]
        +
        # Away xG, while score tied, at 3v4
        [0.912]
        +
        # Away xG, while home team leading, at 3v4
        [0.898]
    )

    values = [df.pred_goal * weight for weight in weights]

    df["pred_goal_adj"] = np.select(conds, values)

    # shot weights

    weights = (
        # Home shot, while home team trailing by more than 3, at 5v5
        [0.862]
        +
        # Home shot, while home team trailing by 2, at 5v5
        [0.890]
        +
        # Home shot, while home team trailing by 1, at 5v5
        [0.915]
        +
        # Home shot, score tied at 5v5
        [0.972]
        +
        # Home shot, while home team leading by 1, at 5v5
        [1.037]
        +
        # Home shot, while home team leading by 2, at 5v5
        [1.077]
        +
        # Home shot, while home team leading by more than 3, at 5v5
        [1.104]
        +
        # Away shot, while home team trailing by more than 3, at 5v5
        [1.191]
        +
        # Away shot, while home team trailing by 2, at 5v5
        [1.141]
        +
        # Away shot, while home team trailing by 1, at 5v5
        [1.102]
        +
        # Away shot, score tied at 5v5
        [1.029]
        +
        # Away shot, while home team leading by 1, at 5v5
        [0.966]
        +
        # Away shot, while home team leading by 2, at 5v5
        [0.933]
        +
        # Away shot, while home team leading by more than 3, at 5v5
        [0.914]
        +
        # Home shot, while home team trailing, at 4v4
        ([0.939] * 3)
        +
        # Home shot, score tied at 4v4
        [0.969]
        +
        # Home shot, while home team leading, at 4v4
        ([1.029] * 3)
        +
        # Away shot, while home team trailing, at 4v4
        ([1.070] * 3)
        +
        # Away shot, score tied at 4v4
        [1.033]
        +
        # Away shot, while home team leading, at 4v4
        ([0.973] * 3)
        +
        # Home shot at 3v3
        [0.991]
        +
        # Away shot at 3v3
        [1.009]
        +
        # Home shot, while home team trailing, at 5v4
        [0.844]
        +
        # Home shot, while score tied, at 5v4
        [0.930]
        +
        # Home shot, while home team leading, at 5v4
        [1.046]
        +
        # Away shot, while home team trailing, at 5v4
        [1.226]
        +
        # Away shot, while score tied, at 5v4
        [1.081]
        +
        # Away shot, while home team leading, at 5v4
        [0.958]
        +
        # Home shot, while home team trailing, at 4v5
        [1.226]
        +
        # Home shot, while score tied, at 4v5
        [1.081]
        +
        # Home shot, while home team leading, at 4v5
        [0.958]
        +
        # Away shot, while home team trailing, at 4v5
        [0.844]
        +
        # Away shot, while score tied, at 4v5
        [0.930]
        +
        # Away shot, while home team leading, at 4v5
        [1.046]
        +
        # Home shot, while home team trailing, at 5v3
        [0.799]
        +
        # Home shot, while score tied, at 5v3
        [0.915]
        +
        # Home shot, while home team leading, at 5v3
        [0.949]
        +
        # Away shot, while home team trailing, at 5v3
        [1.336]
        +
        # Away shot, while score tied, at 5v3
        [1.102]
        +
        # Away shot, while home team leading, at 5v3
        [1.057]
        +
        # Home shot, while home team trailing, at 3v5
        [1.336]
        +
        # Home shot, while score tied, at 3v5
        [1.102]
        +
        # Home shot, while home team leading, at 3v5
        [1.057]
        +
        # Away shot, while home team trailing, at 3v5
        [0.799]
        +
        # Away shot, while score tied, at 3v5
        [0.915]
        +
        # Away shot, while home team leading, at 3v5
        [0.949]
        +
        # Home shot, while home team trailing, at 4v3
        [0.839]
        +
        # Home shot, while score tied, at 4v3
        [0.913]
        +
        # Home shot, while home team leading, at 4v3
        [0.975]
        +
        # Away shot, while home team trailing, at 4v3
        [1.238]
        +
        # Away shot, while score tied, at 4v3
        [1.105]
        +
        # Away shot, while home team leading, at 4v3
        [1.026]
        +
        # Home shot, while home team trailing, at 3v4
        [1.238]
        +
        # Home shot, while score tied, at 3v4
        [1.105]
        +
        # Home shot, while home team leading, at 3v4
        [1.026]
        +
        # Away shot, while home team trailing, at 3v4
        [0.839]
        +
        # Away shot, while score tied, at 3v4
        [0.913]
        +
        # Away shot, while home team leading, at 3v4
        [0.975]
    )

    values = [df.shot * weight for weight in weights]

    df["shot_adj"] = np.select(conds, values)

    # fenwwick weights

    weights = (
        # Home fenwick, while home team trailing by more than 3, at 5v5
        [0.859]
        +
        # Home fenwick, while home team trailing by 2, at 5v5
        [0.881]
        +
        # Home fenwick, while home team trailing by 1, at 5v5
        [0.909]
        +
        # Home fenwick, score tied at 5v5
        [0.968]
        +
        # Home fenwick, while home team leading by 1, at 5v5
        [1.037]
        +
        # Home fenwick, while home team leading by 2, at 5v5
        [1.078]
        +
        # Home fenwick, while home team leading by more than 3, at 5v5
        [1.109]
        +
        # Away fenwick, while home team trailing by more than 3, at 5v5
        [1.197]
        +
        # Away fenwick, while home team trailing by 2, at 5v5
        [1.155]
        +
        # Away fenwick, while home team trailing by 1, at 5v5
        [1.111]
        +
        # Away fenwick, score tied at 5v5
        [1.034]
        +
        # Away fenwick, while home team leading by 1, at 5v5
        [0.966]
        +
        # Away fenwick, while home team leading by 2, at 5v5
        [0.933]
        +
        # Away fenwick, while home team leading by more than 3, at 5v5
        [0.911]
        +
        # Home fenwick, while home team trailing by more than 3, at 4v4
        [0.933]
        +
        # Home fenwick, while home team trailing by 2, at 4v4
        [0.931]
        +
        # Home fenwick, while home team trailing by 1, at 4v4
        [0.938]
        +
        # Home fenwick, score tied at 4v4
        [0.973]
        +
        # Home fenwick, while home team leading by 1, at 4v4
        [1.027]
        +
        # Home fenwick, while home team leading by 2, at 4v4
        [1.040]
        +
        # Home fenwick, while home team leading by more than 3, at 4v4
        [1.060]
        +
        # Away fenwick, while home team trailing by more than 3, at 4v4
        [1.077]
        +
        # Away fenwick, while home team trailing by 2, at 4v4
        [1.079]
        +
        # Away fenwick, while home team trailing by 1, at 4v4
        [1.071]
        +
        # Away fenwick, score tied at 4v4
        [1.029]
        +
        # Away fenwick, while home team leading by 1, at 4v4
        [0.975]
        +
        # Away fenwick, while home team leading by 2, at 4v4
        [0.963]
        +
        # Away fenwick, while home team leading by more than 3, at 4v4
        [0.947]
        +
        # Home fenwick at 3v3
        [1.001]
        +
        # Away fenwick at 3v3
        [0.999]
        +
        # Home fenwick, while home team trailing, at 5v4
        [0.843]
        +
        # Home fenwick, while score tied, at 5v4
        [0.926]
        +
        # Home fenwick, while home team leading, at 5v4
        [1.039]
        +
        # Away fenwick, while home team trailing, at 5v4
        [1.229]
        +
        # Away fenwick, while score tied, at 5v4
        [1.087]
        +
        # Away fenwick, while home team leading, at 5v4
        [0.964]
        +
        # Home fenwick, while home team trailing, at 4v5
        [1.229]
        +
        # Home fenwick, while score tied, at 4v5
        [1.087]
        +
        # Home fenwick, while home team leading, at 4v5
        [0.964]
        +
        # Away fenwick, while home team trailing, at 4v5
        [0.843]
        +
        # Away fenwick, while score tied, at 4v5
        [0.926]
        +
        # Away fenwick, while home team leading, at 4v5
        [1.039]
        +
        # Home fenwick, while home team trailing, at 5v3
        [0.798]
        +
        # Home fenwick, while score tied, at 5v3
        [0.906]
        +
        # Home fenwick, while home team leading, at 5v3
        [0.932]
        +
        # Away fenwick, while home team trailing, at 5v3
        [1.340]
        +
        # Away fenwick, while score tied, at 5v3
        [1.115]
        +
        # Away fenwick, while home team leading, at 5v3
        [1.078]
        +
        # Home fenwick, while home team trailing, at 3v5
        [1.340]
        +
        # Home fenwick, while score tied, at 3v5
        [1.115]
        +
        # Home fenwick, while home team leading, at 3v5
        [1.078]
        +
        # Away fenwick, while home team trailing, at 3v5
        [0.798]
        +
        # Away fenwick, while score tied, at 3v5
        [0.906]
        +
        # Away fenwick, while home team leading, at 3v5
        [0.932]
        +
        # Home fenwick, while home team trailing, at 4v3
        [0.814]
        +
        # Home fenwick, while score tied, at 4v3
        [0.921]
        +
        # Home fenwick, while home team leading, at 4v3
        [0.941]
        +
        # Away fenwick, while home team trailing, at 4v3
        [1.297]
        +
        # Away fenwick, while score tied, at 4v3
        [1.093]
        +
        # Away fenwick, while home team leading, at 4v3
        [1.066]
        +
        # Home fenwick, while home team trailing, at 3v4
        [1.297]
        +
        # Home fenwick, while score tied, at 3v4
        [1.093]
        +
        # Home fenwick, while home team leading, at 3v4
        [1.066]
        +
        # Away fenwick, while home team trailing, at 3v4
        [0.814]
        +
        # Away fenwick, while score tied, at 3v4
        [0.921]
        +
        # Away fenwick, while home team leading, at 3v4
        [0.941]
    )

    values = [df.fenwick * weight for weight in weights]

    df["fenwick_adj"] = np.select(conds, values)

    # corsi weights

    weights = (
        # Home corsi, while home team trailing by more than 3, at 5v5
        [0.843]
        +
        # Home corsi, while home team trailing by 2, at 5v5
        [0.866]
        +
        # Home corsi, while home team trailing by 1, at 5v5
        [0.899]
        +
        # Home corsi, score tied at 5v5
        [0.970]
        +
        # Home corsi, while home team leading by 1, at 5v5
        [1.053]
        +
        # Home corsi, while home team leading by 2, at 5v5
        [1.105]
        +
        # Home corsi, while home team leading by more than 3, at 5v5
        [1.140]
        +
        # Away corsi, while home team trailing by more than 3, at 5v5
        [1.230]
        +
        # Away corsi, while home team trailing by 2, at 5v5
        [1.182]
        +
        # Away corsi, while home team trailing by 1, at 5v5
        [1.127]
        +
        # Away corsi, score tied at 5v5
        [1.032]
        +
        # Away corsi, while home team leading by 1, at 5v5
        [0.952]
        +
        # Away corsi, while home team leading by 2, at 5v5
        [0.913]
        +
        # Away corsi, while home team leading by more than 3, at 5v5
        [0.891]
        +
        # Home corsi, while home team trailing by more than 3, at 4v4
        [0.890]
        +
        # Home corsi, while home team trailing by 2, at 4v4
        [0.914]
        +
        # Home corsi, while home team trailing by 1, at 4v4
        [0.923]
        +
        # Home corsi, score tied at 4v4
        [0.977]
        +
        # Home corsi, while home team leading by 1, at 4v4
        [1.043]
        +
        # Home corsi, while home team leading by 2, at 4v4
        [1.050]
        +
        # Home corsi, while home team leading by more than 3, at 4v4
        [1.089]
        +
        # Away corsi, while home team trailing by more than 3, at 4v4
        [1.141]
        +
        # Away corsi, while home team trailing by 2, at 4v4
        [1.103]
        +
        # Away corsi, while home team trailing by 1, at 4v4
        [1.091]
        +
        # Away corsi, score tied at 4v4
        [1.024]
        +
        # Away corsi, while home team leading by 1, at 4v4
        [0.960]
        +
        # Away corsi, while home team leading by 2, at 4v4
        [0.954]
        +
        # Away corsi, while home team leading by more than 3, at 4v4
        [0.925]
        +
        # Home corsi at 3v3
        [0.99]
        +
        # Away corsi at 3v3
        [1.01]
        +
        # Home corsi, while home team trailing, at 5v4
        [0.841]
        +
        # Home corsi, while score tied, at 5v4
        [0.930]
        +
        # Home corsi, while home team leading, at 5v4
        [1.052]
        +
        # Away corsi, while home team trailing, at 5v4
        [1.233]
        +
        # Away corsi, while score tied, at 5v4
        [1.082]
        +
        # Away corsi, while home team leading, at 5v4
        [0.953]
        +
        # Home corsi, while home team trailing, at 4v5
        [1.233]
        +
        # Home corsi, while score tied, at 4v5
        [1.082]
        +
        # Home corsi, while home team leading, at 4v5
        [0.953]
        +
        # Away corsi, while home team trailing, at 4v5
        [0.841]
        +
        # Away corsi, while score tied, at 4v5
        [0.930]
        +
        # Away corsi, while home team leading, at 4v5
        [1.052]
        +
        # Home corsi, while home team trailing, at 5v3
        [0.798]
        +
        # Home corsi, while score tied, at 5v3
        [0.903]
        +
        # Home corsi, while home team leading, at 5v3
        [0.954]
        +
        # Away corsi, while home team trailing, at 5v3
        [1.338]
        +
        # Away corsi, while score tied, at 5v3
        [1.121]
        +
        # Away corsi, while home team leading, at 5v3
        [1.051]
        +
        # Home corsi, while home team trailing, at 3v5
        [1.338]
        +
        # Home corsi, while score tied, at 3v5
        [1.121]
        +
        # Home corsi, while home team leading, at 3v5
        [1.051]
        +
        # Away corsi, while home team trailing, at 3v5
        [0.798]
        +
        # Away corsi, while score tied, at 3v5
        [0.903]
        +
        # Away corsi, while home team leading, at 3v5
        [0.954]
        +
        # Home corsi, while home team trailing, at 4v3
        [0.841]
        +
        # Home corsi, while score tied, at 4v3
        [0.925]
        +
        # Home corsi, while home team leading, at 4v3
        [0.953]
        +
        # Away corsi, while home team trailing, at 4v3
        [1.234]
        +
        # Away corsi, while score tied, at 4v3
        [1.088]
        +
        # Away corsi, while home team leading, at 4v3
        [1.052]
        +
        # Home corsi, while home team trailing, at 3v4
        [1.234]
        +
        # Home corsi, while score tied, at 3v4
        [1.088]
        +
        # Home corsi, while home team leading, at 3v4
        [1.052]
        +
        # Away corsi, while home team trailing, at 3v4
        [0.841]
        +
        # Away corsi, while score tied, at 3v4
        [0.925]
        +
        # Away corsi, while home team leading, at 3v4
        [0.953]
    )

    values = [df.corsi * weight for weight in weights]

    df["corsi_adj"] = np.select(conds, values)

    df.game_period = np.where(pd.isna(df.game_period), 0, df.game_period)
    df.game_seconds = np.where(pd.isna(df.game_seconds), 0, df.game_seconds)
    df.period_seconds = np.where(pd.isna(df.period_seconds), 0, df.period_seconds)

    game_id_str = df.game_id.astype(str)
    event_index_str = df.event_index.astype(str)

    conds = [
        event_index_str.str.len() == 1,
        event_index_str.str.len() == 2,
        event_index_str.str.len() == 3,
        event_index_str.str.len() == 4,
    ]
    values = [
        game_id_str + "000" + event_index_str,
        game_id_str + "00" + event_index_str,
        game_id_str + "0" + event_index_str,
        game_id_str + event_index_str,
    ]

    df["id"] = np.select(conds, values).astype(np.int64)

    return df


def munge_rosters(shifts: pd.DataFrame) -> pd.DataFrame:
    """Prepares rosters from csv file of shifts data for use in the `prep_pbp` function.

    Parameters:
        shifts (pd.DataFrame):
            Pandas Dataframe of shifts data available from the queries section
            of evolving-hockey.com. Subscription required.

    """
    keep = ["player", "team_num", "position", "game_id", "season", "session", "team"]

    df = shifts[keep].copy().drop_duplicates()

    DUOS = {
        "SEBASTIAN.AHO": df.position == "D",
        "COLIN.WHITE": df.season >= 20162017,
        "SEAN.COLLINS": df.season >= 20162017,
        "ALEX.PICARD": df.position != "D",
        "ERIK.GUSTAFSSON": df.season >= 20152016,
        "MIKKO.LEHTONEN": df.season >= 20202021,
        "NATHAN.SMITH": df.season >= 20212022,
        "DANIIL.TARASOV": df.position == "G",
    }

    DUOS = [
        np.logical_and(df.player == player, condition)
        for player, condition in DUOS.items()
    ]

    df.player = (
        df.player.str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )

    df["eh_id"] = np.where(np.logical_or.reduce(DUOS), df.player + "2", df.player)

    replace_teams = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}

    df.team = df.team.replace(replace_teams)

    for old_team, new_team in replace_teams.items():
        df.team_num = df.team_num.str.replace(old_team, new_team, regex=False)

    return df


def add_positions(pbp: pd.DataFrame, rosters: pd.DataFrame) -> pd.DataFrame:
    """Adds position data to the play-by-play data from evolving-hockey.com.

    Nested within `prep_pbp` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `munge_pbp` function
        rosters (pd.DataFrame):
            Data returned from `munge_rosters` function

    """
    pbp = pbp.copy()

    rosters = rosters.copy()

    player_cols = [
        col
        for col in pbp.columns
        if ("event_player" in col or "on_" in col) and ("s_on" not in col)
    ]

    for col in player_cols:
        pbp[col] = (
            pbp[col]
            .astype(str)
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("utf-8")
        )  # .replace(EH_REPLACE[year])

        keep_list = ["game_id", "player", "eh_id", "position"]

        left_on = ["game_id", col]

        right_on = ["game_id", "player"]

        pbp = pbp.merge(
            rosters[keep_list], how="left", left_on=left_on, right_on=right_on
        )

        pbp = pbp.rename(columns={"position": col + "_pos", "eh_id": col + "_id"}).drop(
            "player", axis=1
        )

    # Adding names and positions for players changing

    change_players = pbp.players_on.str.split(", ", expand=True)

    pbp = pbp.drop("players_on", axis=1)

    columns = change_players.columns

    change_players["game_id"] = pbp.game_id

    for player_num, change_player in enumerate(columns, start=1):
        keep_list = ["game_id", "team_num", "player", "eh_id", "position"]

        left_on = ["game_id", change_player]

        right_on = ["game_id", "team_num"]

        change_players = change_players.merge(
            rosters[keep_list], how="left", left_on=left_on, right_on=right_on
        )

        new_cols = {
            "eh_id": f"id_{player_num}",
            "position": f"position_{player_num}",
            "player": f"player_{player_num}",
        }

        change_players = change_players.rename(columns=new_cols).drop(
            "team_num", axis=1
        )

    cols = [f"player_{x}" for x in range(1, len(columns))]

    change_players["players_on"] = change_players[cols].apply(
        lambda x: x.str.cat(sep=", "), axis=1
    )

    cols = [f"id_{x}" for x in range(1, len(columns))]

    change_players["players_on_id"] = change_players[cols].apply(
        lambda x: x.str.cat(sep=", "), axis=1
    )

    cols = [f"position_{x}" for x in range(1, len(columns))]

    change_players["players_on_pos"] = change_players[cols].apply(
        lambda x: x.str.cat(sep=", "), axis=1
    )

    keep_cols = ["players_on", "players_on_id", "players_on_pos"]

    change_players = change_players[keep_cols].copy()

    pbp = pbp.merge(change_players, left_index=True, right_index=True, how="left")

    change_players = pbp.players_off.str.split(", ", expand=True)

    pbp = pbp.drop("players_off", axis=1)

    columns = change_players.columns

    change_players["game_id"] = pbp.game_id

    for player_num, change_player in enumerate(columns, start=1):
        keep_list = ["game_id", "team_num", "player", "eh_id", "position"]

        left_on = ["game_id", change_player]

        right_on = ["game_id", "team_num"]

        change_players = change_players.merge(
            rosters[keep_list], how="left", left_on=left_on, right_on=right_on
        )

        new_cols = {
            "eh_id": f"id_{player_num}",
            "position": f"position_{player_num}",
            "player": f"player_{player_num}",
        }

        change_players = change_players.rename(columns=new_cols).drop(
            "team_num", axis=1
        )

    cols = [f"player_{x}" for x in range(1, len(columns))]

    change_players["players_off"] = change_players[cols].apply(
        lambda x: x.str.cat(sep=", "), axis=1
    )

    cols = [f"id_{x}" for x in range(1, len(columns))]

    change_players["players_off_id"] = change_players[cols].apply(
        lambda x: x.str.cat(sep=", "), axis=1
    )

    cols = [f"position_{x}" for x in range(1, len(columns))]

    change_players["players_off_pos"] = change_players[cols].apply(
        lambda x: x.str.cat(sep=", "), axis=1
    )

    keep_cols = ["players_off", "players_off_id", "players_off_pos"]

    change_players = change_players[keep_cols].copy()

    pbp = pbp.merge(change_players, left_index=True, right_index=True, how="left")

    player_groups = ["event", "opp"]

    for player_group in player_groups:
        player_types = {"f": ["L", "C", "R"], "d": ["D"], "g": ["G"]}

        for position_group, positions in player_types.items():
            col = f"{player_group}_on_{position_group}"

            pbp[col] = ""

            id_col = f"{player_group}_on_{position_group}_id"

            pbp[id_col] = ""

            player_cols = [f"{player_group}_on_{x}" for x in range(1, 7)]

            for player_col in player_cols:
                cond = pbp[f"{player_col}_pos"].isin(positions)

                pbp[col] = np.where(cond, pbp[col] + pbp[player_col] + "_", pbp[col])

                pbp[id_col] = np.where(
                    cond, pbp[id_col] + pbp[f"{player_col}_id"] + "_", pbp[id_col]
                )

            pbp[col] = pbp[col].str.split("_").map(lambda x: ", ".join(sorted(x)))

            pbp[col] = pbp[col].str.replace(r"(^, )", "", regex=True)

            pbp[id_col] = pbp[id_col].str.split("_").map(lambda x: ", ".join(sorted(x)))

            pbp[id_col] = pbp[id_col].str.replace(r"(^, )", "", regex=True)

    return pbp


def prep_ind(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of individual stats from play-by-play data.

    Nested within `prep_stats` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `prep_pbp` function
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        score (bool):
            Determines if stats are cut by score state
        teammates (bool):
            Determines if stats are cut by teammates on ice
        opposition (bool):
            Determines if stats are cut by opponents on ice

    """
    df = pbp.copy()

    players = ["event_player_1", "event_player_2", "event_player_3"]

    if level == "session" or level == "season":
        merge_list = [
            "season",
            "session",
            "player",
            "player_id",
            "position",
            "team",
            "strength_state",
        ]

    if level == "game":
        merge_list = [
            "season",
            "session",
            "player",
            "player_id",
            "position",
            "team",
            "strength_state",
            "game_id",
            "game_date",
            "opp_team",
        ]

    if level == "period":
        merge_list = [
            "season",
            "session",
            "player",
            "player_id",
            "position",
            "team",
            "strength_state",
            "game_id",
            "game_date",
            "opp_team",
            "game_period",
        ]

    if score is True:
        merge_list.append("score_state")

    if teammates is True:
        merge_list = merge_list + [
            "forwards",
            "forwards_id",
            "defense",
            "defense_id",
            "own_goalie",
            "own_goalie_id",
        ]

    if opposition is True:
        merge_list = merge_list + [
            "opp_forwards",
            "opp_forwards_id",
            "opp_defense",
            "opp_defense_id",
            "opp_goalie",
            "opp_goalie_id",
        ]

        if "opp_team" not in merge_list:
            merge_list.append("opp_team")

    ind_stats = pd.DataFrame(columns=merge_list)

    for player in players:
        player_id = f"{player}_id"

        position = f"{player}_pos"

        if level == "session" or level == "season":
            group_base = [
                "season",
                "session",
                "event_team",
                player,
                player_id,
                position,
            ]

        if level == "game":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                player,
                player_id,
                position,
            ]

        if level == "period":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "game_period",
                player,
                player_id,
                position,
            ]

        if opposition is True and "opp_team" not in group_base:
            group_base.append("opp_team")

        mask = df[player] != "BENCH"

        if player == "event_player_1":
            strength_group = ["strength_state"]
            group_list = group_base + strength_group

            if teammates is True:
                teammates_group = [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

                group_list = group_list + teammates_group

            if score is True:
                score_group = ["score_state"]
                group_list = group_list + score_group

            if opposition is True:
                opposition_group = [
                    "opp_on_f",
                    "opp_on_f_id",
                    "opp_on_d",
                    "opp_on_d_id",
                    "opp_on_g",
                    "opp_on_g_id",
                ]

                group_list = group_list + opposition_group

            stats_list = [
                "block",
                "fac",
                "give",
                "goal",
                "hd_fenwick",
                "hd_goal",
                "hd_miss",
                "hd_shot",
                "hit",
                "miss",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "shot",
                "take",
                "corsi",
                "fenwick",
                "pred_goal",
                "ozf",
                "nzf",
                "dzf",
            ]

            stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            new_cols = {
                "block": "isb",
                "fac": "ifow",
                "give": "igive",
                "goal": "g",
                "hd_fenwick": "ihdf",
                "hd_goal": "ihdg",
                "hd_miss": "ihdm",
                "hd_shot": "ihdsf",
                "hit": "ihf",
                "miss": "imsf",
                "pen0": "ipent0",
                "pen2": "ipent2",
                "pen4": "ipent4",
                "pen5": "ipent5",
                "pen10": "ipent10",
                "shot": "isf",
                "take": "itake",
                "corsi": "icf",
                "fenwick": "iff",
                "pred_goal": "ixg",
                "ozf": "iozfw",
                "nzf": "inzfw",
                "dzf": "idzfw",
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                position: "position",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

            player_df = (
                df[mask]
                .copy()
                .groupby(group_list, as_index=False)
                .agg(stats_dict)
                .rename(columns=new_cols)
            )

            # drop_list = [x for x in stats if x not in new_cols.keys() and x in player_df.columns]

        if player == "event_player_2":
            # Getting on-ice stats against for player 2

            opp_strength = ["opp_strength_state"]
            event_strength = ["strength_state"]

            opp_group_list = group_base + opp_strength
            event_group_list = group_base + event_strength

            if not opposition:
                if level in ["season", "session"]:
                    opp_group_list.remove("event_team")
                    opp_group_list.append("opp_team")

            if teammates is True:
                opp_teammates = [
                    "opp_on_f",
                    "opp_on_f_id",
                    "opp_on_d",
                    "opp_on_d_id",
                    "opp_on_g",
                    "opp_on_g_id",
                ]

                event_teammates = [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

                opp_group_list = opp_group_list + opp_teammates
                event_group_list = event_group_list + event_teammates

            if score is True:
                opp_score = ["opp_score_state"]
                event_score = ["score_state"]

                opp_group_list = opp_group_list + opp_score
                event_group_list = event_group_list + event_score

            if opposition is True:
                opp_opposition = [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

                event_opposition = [
                    "opp_on_f",
                    "opp_on_f_id",
                    "opp_on_d",
                    "opp_on_d_id",
                    "opp_on_g",
                    "opp_on_g_id",
                ]

                opp_group_list = opp_group_list + opp_opposition
                event_group_list = event_group_list + event_opposition

            stats_1 = [
                "block",
                "fac",
                "hit",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "ozf",
                "nzf",
                "dzf",
            ]

            stats_1 = {x: "sum" for x in stats_1 if x.lower() in df.columns}

            new_cols_1 = {
                "opp_on_g": "own_goalie",
                "opp_on_g_id": "own_goalie_id",
                "event_on_g": "opp_goalie",
                "event_on_g_id": "opp_goalie_id",
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                "pen0": "ipend0",
                "pen2": "ipend2",
                "pen4": "ipend4",
                "pen5": "ipend5",
                "pen10": "ipend10",
                player: "player",
                player_id: "player_id",
                position: "position",
                "fac": "ifol",
                "hit": "iht",
                "ozf": "iozfl",
                "nzf": "inzfl",
                "dzf": "idzfl",
                "block": "ibs",
                "opp_on_f": "forwards",
                "opp_on_f_id": "forwards_id",
                "opp_on_d": "defense",
                "opp_on_d_id": "defense_id",
                "event_on_f": "opp_forwards",
                "event_on_f_id": "opp_forwards_id",
                "event_on_d": "opp_defense",
                "event_on_d_id": "opp_defense_id",
            }

            event_types = ["BLOCK", "FAC", "HIT", "PENL"]

            mask_1 = np.logical_and(
                df[player] != "BENCH", df.event_type.isin(event_types)
            )

            opps = (
                df[mask_1]
                .copy()
                .groupby(opp_group_list, as_index=False)
                .agg(stats_1)
                .rename(columns=new_cols_1)
            )

            # Getting primary assists and primary assists xG from player 2

            stats_2 = ["goal", "pred_goal"]

            stats_2 = {x: "sum" for x in stats_2 if x in df.columns}

            new_cols_2 = {
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                "goal": "a1",
                "pred_goal": "a1_xg",
                position: "position",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

            mask_2 = np.logical_and(
                df[player] != "BENCH",
                df.event_type.isin([x.upper() for x in stats_2.keys()]),
            )

            own = (
                df[mask_2]
                .copy()
                .groupby(event_group_list, as_index=False)
                .agg(stats_2)
                .rename(columns=new_cols_2)
            )

            player_df = opps.merge(
                own, left_on=merge_list, right_on=merge_list, how="outer"
            ).fillna(0)

        if player == "event_player_3":
            group_list = group_base + strength_group

            if teammates is True:
                group_list = group_list + teammates_group

            if score is True:
                group_list = group_list + score_group

            if opposition is True:
                group_list = group_list + opposition_group

                if "opp_team" not in group_list:
                    group_list.append("opp_team")

            stats_list = ["goal", "pred_goal"]

            stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            player_df = df[mask].groupby(group_list, as_index=False).agg(stats_dict)

            new_cols = {
                "goal": "a2",
                "pred_goal": "a2_xg",
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                position: "position",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

            player_df = player_df.rename(columns=new_cols)

        ind_stats = ind_stats.merge(player_df, on=merge_list, how="outer").fillna(0)

    # Fixing some stats

    ind_stats["gax"] = ind_stats.g - ind_stats.ixg

    columns = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "player_id",
        "position",
        "team",
        "opp_team",
        "game_period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_id",
        "own_goalie",
        "own_goalie_id",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
        "g",
        "a1",
        "a2",
        "isf",
        "iff",
        "icf",
        "ixg",
        "gax",
        "ihdg",
        "ihdf",
        "ihdsf",
        "ihdm",
        "imsf",
        "isb",
        "ibs",
        "igive",
        "itake",
        "ihf",
        "iht",
        "ifow",
        "ifol",
        "iozfw",
        "iozfl",
        "inzfw",
        "inzfl",
        "idzfw",
        "idzfl",
        "a1_xg",
        "a2_xg",
        "ipent0",
        "ipent2",
        "ipent4",
        "ipent5",
        "ipent10",
        "ipend0",
        "ipend2",
        "ipend4",
        "ipend5",
        "ipend10",
    ]

    columns = [x for x in columns if x in ind_stats.columns]

    ind_stats = ind_stats[columns]

    stats = [
        "g",
        "a1",
        "a2",
        "isf",
        "iff",
        "icf",
        "ixg",
        "gax",
        "ihdg",
        "ihdf",
        "ihdsf",
        "ihdm",
        "imsf",
        "isb",
        "ibs",
        "igive",
        "itake",
        "ihf",
        "iht",
        "ifow",
        "ifol",
        "iozfw",
        "iozfl",
        "inzfw",
        "inzfl",
        "idzfw",
        "idzfl",
        "a1_xg",
        "a2_xg",
        "ipent0",
        "ipent2",
        "ipent4",
        "ipent5",
        "ipent10",
        "ipend0",
        "ipend2",
        "ipend4",
        "ipend5",
        "ipend10",
    ]

    stats = [x for x in stats if x in ind_stats.columns]

    ind_stats = ind_stats.loc[(ind_stats[stats] != 0).any(axis=1)]

    return ind_stats


def prep_oi(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of on-ice stats from play-by-play data.

    Nested within `prep_stats` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `prep_pbp` function
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        score (bool):
            Determines if stats are cut by score state
        teammates (bool):
            Determines if stats are cut by teammates on ice
        opposition (bool):
            Determines if stats are cut by opponents on ice

    """
    df = pbp.copy()

    stats_list = [
        "block",
        "fac",
        "goal",
        "goal_adj",
        "hd_fenwick",
        "hd_goal",
        "hd_miss",
        "hd_shot",
        "hit",
        "miss",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "shot",
        "shot_adj",
        "corsi",
        "corsi_adj",
        "fenwick",
        "fenwick_adj",
        "pred_goal",
        "pred_goal_adj",
        "ozf",
        "nzf",
        "dzf",
        "event_length",
    ]

    stats_dict = {x: "sum" for x in stats_list if x in df.columns}

    players = [f"event_on_{x}" for x in range(1, 8)] + [
        f"opp_on_{x}" for x in range(1, 8)
    ]

    event_list = []

    opp_list = []

    for player in players:
        position = f"{player}_pos"

        player_id = f"{player}_id"

        if level == "session" or level == "season":
            group_list = ["season", "session"]

        if level == "game":
            group_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
            ]

        if level == "period":
            group_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "game_period",
            ]

        # Accounting for desired player

        if "event_on" in player:
            if level == "session" or level == "season":
                group_list.append("event_team")

            strength_group = ["strength_state"]

            teammates_group = [
                "event_on_f",
                "event_on_f_id",
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
            ]

            score_group = ["score_state"]

            opposition_group = [
                "opp_on_f",
                "opp_on_f_id",
                "opp_on_d",
                "opp_on_d_id",
                "opp_on_g",
                "opp_on_g_id",
            ]

            col_names = {
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                position: "position",
                "goal": "gf",
                "goal_adj": "gf_adj",
                "hit": "hf",
                "miss": "msf",
                "block": "bsf",
                "pen0": "pent0",
                "pen2": "pent2",
                "pen4": "pent4",
                "pen5": "pent5",
                "pen10": "pent10",
                "corsi": "cf",
                "corsi_adj": "cf_adj",
                "fenwick": "ff",
                "fenwick_adj": "ff_adj",
                "pred_goal": "xgf",
                "pred_goal_adj": "xgf_adj",
                "FAC": "fow",
                "ozf": "ozfw",
                "dzf": "dzfw",
                "nzf": "nzfw",
                "shot": "sf",
                "shot_adj": "sf_adj",
                "hd_goal": "hdgf",
                "hd_shot": "hdsf",
                "hd_fenwick": "hdff",
                "hd_miss": "hdmsf",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

        if "opp_on" in player:
            if level == "session" or level == "season":
                group_list.append("opp_team")

            strength_group = ["opp_strength_state"]

            teammates_group = [
                "opp_on_f",
                "opp_on_f_id",
                "opp_on_d",
                "opp_on_d_id",
                "opp_on_g",
                "opp_on_g_id",
            ]

            score_group = ["opp_score_state"]

            opposition_group = [
                "event_on_f",
                "event_on_f_id",
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
            ]

            col_names = {
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_goalie": "own_goalie",
                "own_goalie": "opp_goalie",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                player: "player",
                player_id: "player_id",
                position: "position",
                "block": "bsa",
                "goal": "ga",
                "goal_adj": "ga_adj",
                "hit": "ht",
                "miss": "msa",
                "pen0": "pend0",
                "pen2": "pend2",
                "pen4": "pend4",
                "pen5": "pend5",
                "pen10": "pend10",
                "shot": "sa",
                "shot_adj": "sa_adj",
                "corsi": "ca",
                "corsi_adj": "ca_adj",
                "fenwick": "fa",
                "fenwick_adj": "fa_adj",
                "pred_goal": "xga",
                "pred_goal_adj": "xga_adj",
                "fac": "fol",
                "ozf": "dzfl",
                "dzf": "ozfl",
                "nzf": "nzfl",
                "hd_goal": "hdga",
                "hd_shot": "hdsa",
                "hd_fenwick": "hdfa",
                "hd_miss": "hdmsa",
                "event_on_f": "opp_forwards",
                "event_on_f_id": "opp_forwards_id",
                "event_on_d": "opp_defense",
                "event_on_d_id": "opp_defense_id",
                "event_on_g": "opp_goalie",
                "event_on_g_id": "opp_goalie_id",
                "opp_on_f": "forwards",
                "opp_on_f_id": "forwards_id",
                "opp_on_d": "defense",
                "opp_on_d_id": "defense_id",
                "opp_on_g": "own_goalie",
                "opp_on_g_id": "own_goalie_id",
            }

        group_list = group_list + [player, player_id, position] + strength_group

        if teammates is True:
            group_list = group_list + teammates_group

        if score is True:
            group_list = group_list + score_group

        if opposition is True:
            group_list = group_list + opposition_group

        player_df = df.groupby(group_list, as_index=False).agg(stats_dict)

        col_names = {
            key: value for key, value in col_names.items() if key in player_df.columns
        }

        player_df = player_df.rename(columns=col_names)

        if "event_on" in player:
            event_list.append(player_df)

        else:
            opp_list.append(player_df)

    # On-ice stats

    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "player",
        "player_id",
        "position",
        "game_period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_id",
        "own_goalie",
        "own_goalie_id",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
    ]

    event_stats = pd.concat(event_list, ignore_index=True)

    stats_dict = {x: "sum" for x in event_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in event_stats.columns]

    event_stats = event_stats.groupby(group_list, as_index=False).agg(stats_dict)

    opp_stats = pd.concat(opp_list, ignore_index=True)

    stats_dict = {x: "sum" for x in opp_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in opp_stats.columns]

    opp_stats = opp_stats.groupby(group_list, as_index=False).agg(stats_dict)

    merge_cols = [
        x for x in merge_cols if x in event_stats.columns and x in opp_stats.columns
    ]

    oi_stats = event_stats.merge(opp_stats, on=merge_cols, how="outer").fillna(0)

    oi_stats["toi"] = (oi_stats.event_length_x + oi_stats.event_length_y) / 60

    oi_stats = oi_stats.drop(["event_length_x", "event_length_y"], axis=1)

    fo_list = ["ozf", "dzf", "nzf"]

    for fo in fo_list:
        oi_stats[fo] = oi_stats[f"{fo}w"] + oi_stats[f"{fo}l"]

    oi_stats["fac"] = oi_stats.ozf + oi_stats.nzf + oi_stats.dzf

    columns = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "player_id",
        "position",
        "team",
        "opp_team",
        "game_period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_id",
        "own_goalie",
        "own_goalie_id",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "sf",
        "sf_adj",
        "hdsf",
        "ff",
        "ff_adj",
        "hdff",
        "cf",
        "cf_adj",
        "xgf",
        "xgf_adj",
        "bsf",
        "msf",
        "hdmsf",
        "ga",
        "ga_adj",
        "hdga",
        "sa",
        "sa_adj",
        "hdsa",
        "fa",
        "fa_adj",
        "hdfa",
        "ca",
        "ca_adj",
        "xga",
        "xga_adj",
        "bsa",
        "msa",
        "hdmsa",
        "hf",
        "ht",
        "ozf",
        "nzf",
        "dzf",
        "fow",
        "fol",
        "ozfw",
        "ozfl",
        "nzfw",
        "nzfl",
        "dzfw",
        "dzfl",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
    ]

    columns = [x for x in columns if x in oi_stats.columns]

    oi_stats = oi_stats[columns]

    stats = [
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "sf",
        "sf_adj",
        "hdsf",
        "ff",
        "ff_adj",
        "hdff",
        "cf",
        "cf_adj",
        "xgf",
        "xgf_adj",
        "bsf",
        "msf",
        "hdmsf",
        "ga",
        "ga_adj",
        "hdga",
        "sa",
        "sa_adj",
        "hdsa",
        "fa",
        "fa_adj",
        "hdfa",
        "ca",
        "ca_adj",
        "xga",
        "xga_adj",
        "bsa",
        "msa",
        "hdmsa",
        "hf",
        "ht",
        "ozf",
        "nzf",
        "dzf",
        "fow",
        "fol",
        "ozfw",
        "ozfl",
        "nzfw",
        "nzfl",
        "dzfw",
        "dzfl",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
    ]

    stats = [x.lower() for x in stats if x.lower() in oi_stats.columns]

    oi_stats = oi_stats.loc[(oi_stats[stats] != 0).any(axis=1)]

    return oi_stats


def prep_zones(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of zone stats from play-by-play data.

    Nested within `prep_stats` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `prep_pbp` function
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        score (bool):
            Determines if stats are cut by score state
        teammates (bool):
            Determines if stats are cut by teammates on ice
        opposition (bool):
            Determines if stats are cut by opponents on ice

    """
    conds = np.logical_and(
        pbp.event_type == "CHANGE",
        np.logical_or.reduce([pbp.ozs > 0, pbp.nzs > 0, pbp.dzs > 0, pbp.otf > 0]),
    )

    df = pbp.loc[conds].copy()

    players_on = df.players_on.str.split(", ", expand=True)

    new_cols = {x: f"player_{x+1}" for x in players_on.columns}

    players_on = players_on.rename(columns=new_cols)

    players_on_id = df.players_on_id.str.split(", ", expand=True)

    new_cols = {x: f"player_{x+1}_id" for x in players_on_id.columns}

    players_on_id = players_on_id.rename(columns=new_cols)

    players_on_pos = df.players_on_pos.str.split(", ", expand=True)

    new_cols = {x: f"player_{x+1}_pos" for x in players_on_pos.columns}

    players_on_pos = players_on_pos.rename(columns=new_cols)

    players_on = players_on.merge(players_on_id, left_index=True, right_index=True)

    players_on = players_on.merge(players_on_pos, left_index=True, right_index=True)

    if level == "session" or level == "season":
        group_list = ["season", "session", "event_team", "strength_state"]

    if level == "game":
        group_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "event_team",
            "strength_state",
            "opp_team",
        ]

    if level == "period":
        group_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "game_period",
            "event_team",
            "strength_state",
            "opp_team",
        ]

    if score:
        group_list.append("score_state")

    if teammates:
        group_list = group_list + [
            "event_on_f",
            "event_on_f_id",
            "event_on_d",
            "event_on_d_id",
            "event_on_g",
            "event_on_g_id",
        ]

    if opposition:
        group_list = group_list + [
            "opp_on_f",
            "opp_on_f_id",
            "opp_on_d",
            "opp_on_d_id",
            "opp_on_g",
            "opp_on_g_id",
        ]

    stats = ["ozs", "nzs", "dzs", "otf"]

    keep_cols = group_list + stats

    players_on = df[keep_cols].merge(players_on, left_index=True, right_index=True)

    zones = pd.DataFrame(columns=group_list + ["player", "player_id", "position"])

    player_list = [f"player_{x}" for x in range(1, 6)]

    zones_list = []

    for player in player_list:
        group_cols = group_list + [player, f"{player}_id", f"{player}_pos"]

        new_cols = {
            player: "player",
            f"{player}_id": "player_id",
            f"{player}_pos": "position",
        }

        agg_stats = {x: "sum" for x in stats}

        player_df = (
            players_on.groupby(group_cols, as_index=False)
            .agg(agg_stats)
            .rename(columns=new_cols)
        )

        # zones = zones.merge(player_df, how = 'outer', on = group_list + ['player', 'player_id'])

        zones_list.append(player_df)

    zones = pd.concat(zones_list, ignore_index=True)

    agg_stats = {x: "sum" for x in stats}

    zones = zones.groupby(
        group_list + ["player", "player_id", "position"], as_index=False
    ).agg(agg_stats)

    new_cols = {
        "event_team": "team",
        "event_on_f": "forwards",
        "event_on_f_id": "forwards_id",
        "event_on_d": "defense",
        "event_on_d_id": "defense_id",
        "event_on_g": "own_goalie",
        "event_on_g_id": "own_goalie_id",
        "opp_on_f": "opp_forwards",
        "opp_on_f_id": "opp_forwards_id",
        "opp_on_d": "opp_defense",
        "opp_on_d_id": "opp_defense_id",
        "opp_on_g": "opp_goalie",
        "opp_on_g_id": "opp_goalie_id",
    }

    zones = zones.rename(columns=new_cols)

    columns = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "player",
        "player_id",
        "position",
        "strength_state",
        "score_state",
        "game_period",
        "opp_team",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "own_goalie",
        "own_goalie_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
        "opp_goalie",
        "opp_goalie_id",
        "ozs",
        "nzs",
        "dzs",
        "otf",
    ]

    columns = [x for x in columns if x in zones.columns]

    zones = zones[columns]

    zones[["player", "player_id"]] = zones[["player", "player_id"]].replace("", np.nan)

    zones = zones.dropna(subset=["player", "player_id"])

    return zones
