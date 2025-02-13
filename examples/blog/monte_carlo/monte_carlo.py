import pandas as pd
import numpy as np
from scipy.stats import poisson

from chickenstats.chicken_nhl import Season, Scraper
from chickenstats.utilities import ChickenProgress

from pathlib import Path

import datetime as dt

import argparse


def add_strength_state(team_stats: pd.DataFrame, schedule: pd.DataFrame, latest_date: str) -> pd.DataFrame:
    """Add a secondary strength state column to team stats data.

    Parameters:
        team_stats (pd.DataFrame):
            Pandas dataframe of team statistics aggregated from the `chickenstats` library
        schedule (pd.DataFrame):
            Schedule as Pandas dataframe from the `chickenstats` library
        latest_date (str):
            Most recent date for predictions

    """
    df = team_stats.copy(deep=True)

    home_map = dict(zip(schedule.game_id.astype(str), schedule.home_team, strict=False))

    df["is_home"] = df.game_id.astype(str).map(home_map)

    df.is_home = np.where(df.is_home == df.team, 1, 0)

    pp_list = ["5v4", "5v3", "4v3"]
    sh_list = ["4v5", "3v5", "3v4"]

    conditions = [df.strength_state == "5v5", df.strength_state.isin(pp_list), df.strength_state.isin(sh_list)]

    values = ["5v5", "powerplay", "shorthanded"]

    df["strength_state2"] = np.select(conditions, values, default=None)

    df = df.loc[df.game_date <= latest_date].reset_index(drop=True)

    return df


def prep_nhl_stats(team_stats: pd.DataFrame, schedule: pd.DataFrame, latest_date: str) -> pd.DataFrame:
    """Prepare a dataframe of NHL average statistics by venue and strength state.

    Used to calculate team offensive and defensive ratings.

    Parameters:
        team_stats (pd.DataFrame):
            Pandas dataframe of team statistics aggregated from the `chickenstats` library
        schedule (pd.DataFrame):
            Pandas dataframe of the NHL schedule from the `chickenstats` library
        latest_date (str):
            Most recent date for predictions

    """
    df = team_stats.copy()

    df = add_strength_state(team_stats=df, schedule=schedule, latest_date=latest_date)

    group_columns = ["season", "session", "is_home", "strength_state2"]

    stat_cols = {
        x: "sum"
        for x in df.columns
        if x not in group_columns and "p60" not in x and "percent" not in x and df[x].dtype != "object"
    }

    stat_cols.update({"game_id": "nunique"})

    df = df.groupby(group_columns, as_index=False).agg(stat_cols)

    df["g_score_ax"] = df.gf_adj - df.xgf_adj
    df["g_save_ax"] = df.xga_adj - df.ga_adj

    df["toi_gp"] = df.toi / df.game_id

    df["gf_p60"] = df.gf / df.toi * 60
    df["ga_p60"] = df.ga / df.toi * 60

    df["gf_adj_p60"] = df.gf_adj / df.toi * 60
    df["ga_adj_p60"] = df.ga_adj / df.toi * 60

    df["xgf_p60"] = df.xgf / df.toi * 60
    df["xga_p60"] = df.xga / df.toi * 60

    df["xgf_adj_p60"] = df.xgf_adj / df.toi * 60
    df["xga_adj_p60"] = df.xga_adj / df.toi * 60

    df["g_score_ax_p60"] = df.g_score_ax / df.toi * 60
    df["g_save_ax_p60"] = df.g_save_ax / df.toi * 60

    return df


def add_nhl_mean(columns: list, team_stats_group: pd.DataFrame, nhl_stats: pd.DataFrame):
    """Function to add the mean NHL value for a given statistics.

    Nested within the `prep_team_stats` functions.

    Parameters:
        columns (list):
            The mean values to return
        team_stats_group (pd.DataFrame):
            Team stats aggregated from `chickenstats` library, grouped by season, session, venue, and strength state
            Mean values are appended to this dataframe
        nhl_stats (pd.DataFrame):
            The season-level NHL stats to use for the mean values, aggregated using `chickenstats` library

    """
    team_stats_group = team_stats_group.copy(deep=True)
    nhl_stats = nhl_stats.copy(deep=True)

    for column in columns:
        conditions = [
            np.logical_and(team_stats_group.strength_state2 == "5v5", team_stats_group.is_home == 1),
            np.logical_and(team_stats_group.strength_state2 == "5v5", team_stats_group.is_home == 0),
            np.logical_and(team_stats_group.strength_state2 == "powerplay", team_stats_group.is_home == 1),
            np.logical_and(team_stats_group.strength_state2 == "powerplay", team_stats_group.is_home == 0),
            np.logical_and(team_stats_group.strength_state2 == "shorthanded", team_stats_group.is_home == 1),
            np.logical_and(team_stats_group.strength_state2 == "shorthanded", team_stats_group.is_home == 0),
        ]

        values = [
            nhl_stats.loc[np.logical_and(nhl_stats.strength_state2 == "5v5", nhl_stats.is_home == 1)][column],
            nhl_stats.loc[np.logical_and(nhl_stats.strength_state2 == "5v5", nhl_stats.is_home == 0)][column],
            nhl_stats.loc[np.logical_and(nhl_stats.strength_state2 == "powerplay", nhl_stats.is_home == 1)][column],
            nhl_stats.loc[np.logical_and(nhl_stats.strength_state2 == "powerplay", nhl_stats.is_home == 0)][column],
            nhl_stats.loc[np.logical_and(nhl_stats.strength_state2 == "shorthanded", nhl_stats.is_home == 1)][column],
            nhl_stats.loc[np.logical_and(nhl_stats.strength_state2 == "shorthanded", nhl_stats.is_home == 0)][column],
        ]

        team_stats_group[f"mean_nhl_{column}"] = np.select(conditions, values, default=np.nan)

    return team_stats_group


def calculate_team_strength(team_stats_group: pd.DataFrame) -> pd.DataFrame:
    """Function to calculate a team's xG strength as a proportion of the NHL mean.

    Values are segmented by venue and strength state.

    Parameters:
        team_stats_group (pd.DataFrame):
            Team stats aggregated from `chickenstats` library, grouped by season, session, venue, and strength state

    """
    team_stats_group = team_stats_group.copy(deep=True)

    team_stats_group["team_off_strength"] = (
        (team_stats_group.team_xgf_adj_p60 / team_stats_group.mean_nhl_xgf_adj_p60).astype(float).fillna(1.0)
    )
    team_stats_group["team_def_strength"] = (
        (team_stats_group.team_xga_adj_p60 / team_stats_group.mean_nhl_xga_adj_p60).astype(float).fillna(1.0)
    )

    team_stats_group["toi_comp"] = (
        (team_stats_group.toi_gp / team_stats_group.mean_nhl_toi_gp).astype(float).fillna(1.0)
    )

    team_stats_group["team_scoring_strength"] = (
        (team_stats_group.team_g_score_ax_p60 / team_stats_group.mean_nhl_g_score_ax_p60).astype(float).fillna(1.0)
    )

    team_stats_group["team_goalie_strength"] = (
        (team_stats_group.team_g_save_ax_p60 / team_stats_group.mean_nhl_g_save_ax_p60).astype(float).fillna(1.0)
    )

    return team_stats_group


def prep_team_strength_scores(
    team_stats: pd.DataFrame, nhl_stats: pd.DataFrame, schedule: pd.DataFrame, latest_date: str, predict_columns=None
) -> pd.DataFrame:
    """Prepare a dataframe of team statistics by venue and strength state, including offensive and defensive ratings.

    Parameters:
        team_stats (pd.DataFrame):
            Pandas dataframe of team statistics aggregated from the `chickenstats` library
        nhl_stats (pd.DataFrame):
            Pandas dataframe of NHL stats aggregated from the `chickenstats` library
        schedule (pd.DataFrame):
            NHL schedule scraped using the `chickenstats` library
        latest_date (str):
            Most recent date to predict
        predict_columns (None):
            Columns to use to predict the winning team

    """
    if predict_columns is None:
        predict_columns = [
            "xgf_p60",
            "xga_p60",
            "xgf_adj_p60",
            "xga_adj_p60",
            "gf_p60",
            "ga_p60",
            "gf_adj_p60",
            "ga_adj_p60",
            "g_score_ax_p60",
            "g_save_ax_p60",
            "toi_gp",
        ]

    df = team_stats.copy(deep=True)

    df = add_strength_state(team_stats=df, schedule=schedule, latest_date=latest_date)

    group_columns = ["season", "session", "team", "is_home", "strength_state2"]

    stat_cols = {
        x: "sum"
        for x in df.columns
        if x not in group_columns and "p60" not in x and "percent" not in x and df[x].dtype != "object"
    }

    stat_cols.update({"game_id": "nunique"})

    df = df.groupby(group_columns, as_index=False).agg(stat_cols)

    strength_states = ["5v5", "powerplay", "shorthanded"]
    venues = ["away", "home"]
    teams = df.team.unique().tolist()

    concat_list = [df]

    for team in teams:
        for strength_state in strength_states:
            for dummy_value, venue in enumerate(venues):
                conditions = np.logical_and.reduce(
                    [df.strength_state2 == strength_state, df.is_home == dummy_value, df.team == team]
                )

                if df.loc[conditions].empty:
                    concat_list.append(
                        pd.DataFrame(
                            {
                                "season": 20242025,
                                "session": "R",
                                "team": team,
                                "is_home": dummy_value,
                                "strength_state2": strength_state,
                            },
                            index=[0],
                        )
                    )

    df = pd.concat(concat_list, axis=0, ignore_index=True)

    df["g_score_ax"] = df.gf_adj - df.xgf_adj
    df["g_save_ax"] = df.xga_adj - df.ga_adj

    df["toi_gp"] = df.toi / df.game_id

    df["team_xgf_p60"] = df.xgf / df.toi * 60
    df["team_xga_p60"] = df.xga / df.toi * 60
    df["team_xgf_adj_p60"] = df.xgf_adj / df.toi * 60
    df["team_xga_adj_p60"] = df.xga_adj / df.toi * 60

    df["team_gf_p60"] = df.gf / df.toi * 60
    df["team_ga_p60"] = df.ga / df.toi * 60
    df["team_gf_adj_p60"] = df.gf_adj / df.toi * 60
    df["team_ga_adj_p60"] = df.ga_adj / df.toi * 60

    df["team_g_score_ax_p60"] = df.g_score_ax / df.toi * 60
    df["team_g_save_ax_p60"] = df.g_save_ax / df.toi * 60

    df = add_nhl_mean(columns=predict_columns, team_stats_group=df, nhl_stats=nhl_stats)

    columns = [
        "team_xgf_p60",
        "team_xga_p60",
        "team_xgf_adj_p60",
        "team_xga_adj_p60",
        "team_gf_p60",
        "team_ga_p60",
        "team_gf_adj_p60",
        "team_ga_adj_p60",
    ]

    for column in columns:
        mean_column_name = column.replace("team_", "mean_nhl_")

        if column not in df.columns:
            df[column] = df.apply(lambda x: x[mean_column_name], axis=1)

        else:
            df[column] = df.apply(lambda x: np.where(pd.isnull(x[column]), x[mean_column_name], x[column]), axis=1)

    df = calculate_team_strength(team_stats_group=df)

    return df


def calculate_toi(game: pd.Series, team_strength_scores: pd.DataFrame) -> pd.DataFrame:
    """Function to calculate the predicted time-on-ice for a given game, by strength state, for the home team.

    Parameters:
        game (pd.Series):
            A row from today's games while iterating
        team_strength_scores (pd.DataFrame):
            Pandas dataframe of team strength scores to calculate the matchups

    """
    pass


def prep_team_scores_dict(team_strength_scores: pd.DataFrame) -> dict:
    """Docstring."""
    strength_scores_dict = {}

    for team in team_strength_scores.team.unique():
        team_scores_dict = {}

        for strength_state in team_strength_scores.strength_state2.unique():
            strength_state_dict = {}

            for venue_dummy in range(0, 2):
                conditions = np.logical_and.reduce(
                    [
                        team_strength_scores.team == team,
                        team_strength_scores.strength_state2 == strength_state,
                        team_strength_scores.is_home == venue_dummy,
                    ]
                )
                data = team_strength_scores.loc[conditions].iloc[0]

                venue_scores_dict = {
                    "games_played": data.game_id,
                    "toi": data.toi,
                    "gf": data.gf,
                    "ga": data.ga,
                    "gf_adj": data.gf_adj,
                    "ga_adj": data.ga_adj,
                    "hdgf": data.hdgf,
                    "hdga": data.hdga,
                    "xgf": data.xgf,
                    "xga": data.xga,
                    "xgf_adj": data.xga_adj,
                    "xga_adj": data.xga_adj,
                    "sf": data.sf,
                    "sa": data.sa,
                    "sf_adj": data.sf_adj,
                    "sa_adj": data.sf_adj,
                    "hdsf": data.hdsf,
                    "hdsa": data.hdsa,
                    "ff": data.ff,
                    "fa": data.fa,
                    "ff_adj": data.ff_adj,
                    "fa_adj": data.fa_adj,
                    "hdff": data.hdff,
                    "hdfa": data.hdfa,
                    "cf": data.cf,
                    "ca": data.ca,
                    "cf_adj": data.cf_adj,
                    "ca_adj": data.ca_adj,
                    "bsf": data.bsf,
                    "bsa": data.bsa,
                    "bsf_adj": data.bsf_adj,
                    "bsa_adj": data.bsa_adj,
                    "msf": data.msf,
                    "msa": data.msa,
                    "msf_adj": data.msf_adj,
                    "msa_adj": data.msa_adj,
                    "hdmsf": data.hdmsf,
                    "hdmsa": data.hdmsa,
                    "teammate_block": data.teammate_block,
                    "teammate_block_adj": data.teammate_block_adj,
                    "hf": data.hf,
                    "ht": data.ht,
                    "give": data.give,
                    "take": data["take"],
                    "ozf": data.ozf,
                    "nzf": data.nzf,
                    "dzf": data.dzf,
                    "fow": data.fow,
                    "fol": data.fol,
                    "ozfw": data.ozfw,
                    "ozfl": data.ozfl,
                    "nzfw": data.nzfw,
                    "nzfl": data.nzfl,
                    "dzfw": data.dzfw,
                    "dzfl": data.dzfl,
                    "pent0": data.pent0,
                    "pent2": data.pent2,
                    "pent4": data.pent4,
                    "pent5": data.pent5,
                    "pent10": data.pent10,
                    "pend0": data.pend0,
                    "pend2": data.pend2,
                    "pend4": data.pend4,
                    "pend5": data.pend5,
                    "pend10": data.pend10,
                    "ozs": data.ozs,
                    "nzs": data.nzs,
                    "dzs": data.dzs,
                    "otf": data.otf,
                    "g_score_ax": data.g_score_ax,
                    "g_save_ax": data.g_save_ax,
                    "toi_gp": data.toi_gp,
                    "team_xgf_p60": data.team_xgf_p60,
                    "team_xga_p60": data.team_xga_p60,
                    "team_xgf_adj_p60": data.team_xgf_adj_p60,
                    "team_xga_adj_p60": data.team_xga_adj_p60,
                    "team_gf_p60": data.team_gf_p60,
                    "team_ga_p60": data.team_ga_p60,
                    "team_gf_adj_p60": data.team_gf_adj_p60,
                    "team_ga_adj_p60": data.team_ga_adj_p60,
                    "team_g_score_ax_p60": data.team_g_score_ax_p60,
                    "team_g_save_ax_p60": data.team_g_save_ax_p60,
                    "mean_nhl_xgf_p60": data.mean_nhl_xgf_p60,
                    "mean_nhl_xga_p60": data.mean_nhl_xga_p60,
                    "mean_nhl_xgf_adj_p60": data.mean_nhl_xgf_adj_p60,
                    "mean_nhl_xga_adj_p60": data.mean_nhl_xga_adj_p60,
                    "mean_nhl_g_score_ax_p60": data.mean_nhl_g_score_ax_p60,
                    "mean_nhl_g_save_ax_p60": data.mean_nhl_g_save_ax_p60,
                    "mean_nhl_toi_gp": data.mean_nhl_toi_gp,
                    "team_off_strength": data.team_off_strength,
                    "team_def_strength": data.team_def_strength,
                    "toi_comp": data.toi_comp,
                    "team_scoring_strength": data.team_scoring_strength,
                    "team_goalie_strength": data.team_goalie_strength,
                }

                strength_state_dict.update({venue_dummy: venue_scores_dict})

            team_scores_dict.update({strength_state: strength_state_dict})

        strength_scores_dict.update({team: team_scores_dict})

    return strength_scores_dict


def prep_todays_games(
    schedule: pd.DataFrame, team_strength_scores: pd.DataFrame, nhl_stats: pd.DataFrame, todays_date: str
) -> pd.DataFrame:
    """Docstring."""
    todays_games = schedule.loc[schedule.game_date == todays_date].reset_index(drop=True)

    strength_states = ["5v5", "powerplay", "shorthanded"]
    short_strengths = {"5v5": "5v5", "powerplay": "pp", "shorthanded": "sh"}
    columns = [
        "xgf_p60",
        "xga_p60",
        "xgf_adj_p60",
        "xga_adj_p60",
        "gf_p60",
        "ga_p60",
        "gf_adj_p60",
        "ga_adj_p60",
        "toi_gp",
    ]
    venues = ["away", "home"]

    concat_list = [todays_games]

    for strength_state in strength_states:
        for column in columns:
            for dummy_value, venue in enumerate(venues):
                series_name = f"mean_nhl_{short_strengths[strength_state]}_{venue}_{column}"
                series_data = nhl_stats.loc[
                    np.logical_and(nhl_stats.strength_state2 == strength_state, nhl_stats.is_home == dummy_value)
                ][column].iloc[0]
                series_index = todays_games.index

                new_series = pd.Series(data=series_data, index=series_index, name=series_name)
                concat_list.append(new_series)

    todays_games = pd.concat(concat_list, axis=1)

    todays_games["home_5v5_off_strength"] = np.nan
    todays_games["home_5v5_def_strength"] = np.nan
    todays_games["home_5v5_scoring_strength"] = np.nan
    todays_games["home_5v5_goalie_strength"] = np.nan
    todays_games["home_5v5_toi_comp"] = np.nan
    todays_games["home_pp_off_strength"] = np.nan
    todays_games["home_pp_scoring_strength"] = np.nan
    todays_games["home_pp_toi_comp"] = np.nan
    todays_games["home_sh_def_strength"] = np.nan
    todays_games["home_sh_goalie_strength"] = np.nan
    todays_games["home_sh_toi_comp"] = np.nan

    todays_games["away_5v5_off_strength"] = np.nan
    todays_games["away_5v5_def_strength"] = np.nan
    todays_games["away_5v5_scoring_strength"] = np.nan
    todays_games["away_5v5_goalie_strength"] = np.nan
    todays_games["away_5v5_toi_comp"] = np.nan
    todays_games["away_pp_off_strength"] = np.nan
    todays_games["away_pp_scoring_strength"] = np.nan
    todays_games["away_pp_toi_comp"] = np.nan
    todays_games["away_sh_def_strength"] = np.nan
    todays_games["away_sh_goalie_strength"] = np.nan
    todays_games["away_sh_toi_comp"] = np.nan

    strength_scores_dict = prep_team_scores_dict(team_strength_scores=team_strength_scores)

    for dummy_value, venue in enumerate(venues):
        for strength_state in strength_states:
            todays_games[f"{venue}_{short_strengths[strength_state]}_off_strength"] = todays_games.apply(
                lambda x: strength_scores_dict[x[f"{venue}_team"]][strength_state][dummy_value]["team_off_strength"],
                axis=1,
            )

            todays_games[f"{venue}_{short_strengths[strength_state]}_scoring_strength"] = todays_games.apply(
                lambda x: strength_scores_dict[x[f"{venue}_team"]][strength_state][dummy_value][
                    "team_scoring_strength"
                ],
                axis=1,
            )

            todays_games[f"{venue}_{short_strengths[strength_state]}_def_strength"] = todays_games.apply(
                lambda x: strength_scores_dict[x[f"{venue}_team"]][strength_state][dummy_value]["team_def_strength"],
                axis=1,
            )

            todays_games[f"{venue}_{short_strengths[strength_state]}_goalie_strength"] = todays_games.apply(
                lambda x: strength_scores_dict[x[f"{venue}_team"]][strength_state][dummy_value]["team_goalie_strength"],
                axis=1,
            )

            todays_games[f"{venue}_{short_strengths[strength_state]}_toi_comp"] = todays_games.apply(
                lambda x: strength_scores_dict[x[f"{venue}_team"]][strength_state][dummy_value]["toi_comp"], axis=1
            )

    concat_list = [todays_games]

    series_name = "pred_home_toi_5v5"
    series_data = (
        todays_games.home_5v5_toi_comp * todays_games.away_5v5_toi_comp * todays_games.mean_nhl_5v5_home_toi_gp
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_toi_pp"
    series_data = todays_games.home_pp_toi_comp * todays_games.away_sh_toi_comp * todays_games.mean_nhl_pp_home_toi_gp
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_toi_sh"
    series_data = todays_games.home_sh_toi_comp * todays_games.away_pp_toi_comp * todays_games.mean_nhl_sh_home_toi_gp
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_5v5_xgf_p60"
    series_data = (
        todays_games.home_5v5_off_strength * todays_games.away_5v5_def_strength * todays_games.mean_nhl_5v5_home_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_5v5_xga_p60"
    series_data = (
        todays_games.home_5v5_def_strength * todays_games.away_5v5_off_strength * todays_games.mean_nhl_5v5_home_xga_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_5v5_gf_p60"
    series_data = (
        todays_games.home_5v5_off_strength
        * todays_games.away_5v5_def_strength
        * todays_games.home_5v5_scoring_strength
        * todays_games.away_5v5_goalie_strength
        * todays_games.mean_nhl_5v5_home_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_5v5_ga_p60"
    series_data = (
        todays_games.home_5v5_def_strength
        * todays_games.away_5v5_off_strength
        * todays_games.home_5v5_goalie_strength
        * todays_games.away_5v5_scoring_strength
        * todays_games.mean_nhl_5v5_home_xga_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_pp_xgf_p60"
    series_data = (
        todays_games.home_pp_off_strength * todays_games.away_sh_def_strength * todays_games.mean_nhl_pp_home_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_sh_xga_p60"
    series_data = (
        todays_games.home_sh_def_strength * todays_games.away_pp_off_strength * todays_games.mean_nhl_sh_home_xga_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_home_pp_gf_p60"
    series_data = (
        todays_games.home_pp_off_strength
        * todays_games.away_sh_def_strength
        * todays_games.home_pp_scoring_strength
        * todays_games.away_sh_goalie_strength
        * todays_games.mean_nhl_pp_home_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_away_5v5_gf_p60"
    series_data = (
        todays_games.away_5v5_off_strength
        * todays_games.home_5v5_def_strength
        * todays_games.away_5v5_scoring_strength
        * todays_games.home_5v5_goalie_strength
        * todays_games.mean_nhl_5v5_away_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_away_5v5_ga_p60"
    series_data = (
        todays_games.away_5v5_def_strength
        * todays_games.home_5v5_off_strength
        * todays_games.away_5v5_goalie_strength
        * todays_games.home_5v5_scoring_strength
        * todays_games.mean_nhl_5v5_away_xga_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    #

    series_name = "pred_away_5v5_xgf_p60"
    series_data = (
        todays_games.home_5v5_def_strength * todays_games.away_5v5_off_strength * todays_games.mean_nhl_5v5_away_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_away_5v5_xga_p60"
    series_data = (
        todays_games.home_5v5_off_strength * todays_games.away_5v5_def_strength * todays_games.mean_nhl_5v5_away_xga_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_away_pp_xgf_p60"
    series_data = (
        todays_games.away_pp_off_strength * todays_games.home_sh_def_strength * todays_games.mean_nhl_pp_away_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_away_sh_xga_p60"
    series_data = (
        todays_games.away_sh_def_strength * todays_games.home_pp_off_strength * todays_games.mean_nhl_sh_away_xga_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    series_name = "pred_away_pp_gf_p60"
    series_data = (
        todays_games.away_pp_off_strength
        * todays_games.home_sh_def_strength
        * todays_games.away_pp_scoring_strength
        * todays_games.home_sh_goalie_strength
        * todays_games.mean_nhl_pp_away_xgf_p60
    )
    concat_list.append(pd.Series(data=series_data, name=series_name, index=todays_games.index))

    todays_games = pd.concat(concat_list, axis=1)

    return todays_games


def simulate_game(game: pd.Series) -> dict:
    """Docstring."""
    prediction = {}

    home_5v5_toi = poisson.ppf(random_float(), game.pred_home_toi_5v5)
    home_pp_toi = poisson.ppf(random_float(), game.pred_home_toi_pp)
    home_sh_toi = poisson.ppf(random_float(), game.pred_home_toi_sh)

    total_toi = home_5v5_toi + home_pp_toi + home_sh_toi

    if total_toi > 60:
        home_5v5_toi = home_5v5_toi - ((home_5v5_toi / total_toi) * (total_toi - 60))
        home_pp_toi = home_pp_toi - ((home_pp_toi / total_toi) * (total_toi - 60))
        home_sh_toi = home_sh_toi - ((home_sh_toi / total_toi) * (total_toi - 60))

    home_5v5_xgf_p60 = poisson.ppf(random_float(), game.pred_home_5v5_xgf_p60)
    home_5v5_gf_p60 = poisson.ppf(random_float(), game.pred_home_5v5_gf_p60)
    home_pp_xgf_p60 = poisson.ppf(random_float(), game.pred_home_pp_xgf_p60)
    home_pp_gf_p60 = poisson.ppf(random_float(), game.pred_home_pp_gf_p60)

    away_5v5_xgf_p60 = poisson.ppf(random_float(), game.pred_away_5v5_xgf_p60)
    away_5v5_gf_p60 = poisson.ppf(random_float(), game.pred_away_5v5_gf_p60)
    away_pp_xgf_p60 = poisson.ppf(random_float(), game.pred_away_pp_xgf_p60)
    away_pp_gf_p60 = poisson.ppf(random_float(), game.pred_away_pp_gf_p60)

    home_5v5_goals = home_5v5_xgf_p60 * (home_5v5_toi / 60)
    home_pp_goals = home_pp_xgf_p60 * (home_pp_toi / 60)
    home_total_goals = home_5v5_goals + home_pp_goals

    away_5v5_goals = away_5v5_xgf_p60 * (home_5v5_toi / 60)
    away_pp_goals = away_pp_xgf_p60 * (home_sh_toi / 60)
    away_total_goals = away_5v5_goals + away_pp_goals

    if home_total_goals > away_total_goals:
        home_win = 1
        away_win = 0
        draw = 0

    elif away_total_goals > home_total_goals:
        home_win = 0
        away_win = 1
        draw = 0

    else:
        home_win = 0
        away_win = 0
        draw = 1

    prediction.update(
        {
            "game_id": game.game_id,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "pred_home_5v5_toi": home_5v5_toi,
            "pred_home_pp_toi": home_pp_toi,
            "pred_home_sh_toi": home_sh_toi,
            "pred_away_5v5_toi": home_5v5_toi,
            "pred_away_pp_toi": home_sh_toi,
            "pred_away_sh_toi": home_pp_toi,
            "pred_home_5v5_gf_p60": home_5v5_gf_p60,
            "pred_home_5v5_xgf_p60": home_5v5_xgf_p60,
            "pred_home_pp_gf_p60": home_pp_gf_p60,
            "pred_home_pp_xgf_p60": home_pp_xgf_p60,
            "pred_home_5v5_goals": home_5v5_goals,
            "pred_home_pp_goals": home_pp_goals,
            "pred_home_total_goals": home_total_goals,
            "pred_away_5v5_gf_p60": away_5v5_gf_p60,
            "pred_away_5v5_xgf_p60": away_5v5_xgf_p60,
            "pred_away_pp_gf_p60": away_pp_gf_p60,
            "pred_away_pp_xgf_p60": away_pp_xgf_p60,
            "pred_away_5v5_goals": away_5v5_goals,
            "pred_away_pp_goals": away_pp_goals,
            "pred_away_total_goals": away_total_goals,
            "home_win": home_win,
            "away_win": away_win,
            "draw": draw,
        }
    )

    return prediction


def process_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    # predictions["draw"] = np.where(predictions.home_win == predictions.away_win, 1, 0)

    group_list = ["game_id", "home_team", "away_team"]

    agg_stats_sum = ["home_win", "away_win", "draw"]
    agg_stats_mean = [x for x in predictions.columns if x not in group_list and x not in agg_stats_sum]
    agg_stats = {x: "sum" for x in agg_stats_sum} | {x: "mean" for x in agg_stats_mean}

    pred_results = predictions.groupby(group_list, as_index=False).agg(agg_stats)

    for stat in agg_stats_sum:
        pred_results[f"pred_{stat}_percent"] = pred_results[stat] / pred_results[agg_stats_sum].sum(axis=1)

    rename_columns = {x: f"pred_{x}" for x in agg_stats_sum} | {x: f"{x}_mean" for x in agg_stats_mean}

    pred_results = pred_results.rename(columns=rename_columns)

    pred_results["pred_winner"] = np.where(
        pred_results.pred_home_win_percent > pred_results.pred_away_win_percent,
        pred_results.home_team,
        pred_results.away_team,
    )

    columns = [
        "game_id",
        "home_team",
        "away_team",
        "pred_winner",
        "pred_home_win",
        "pred_away_win",
        "pred_draw",
        "pred_home_win_percent",
        "pred_away_win_percent",
        "pred_draw_percent",
        "pred_home_5v5_goals_mean",
        "pred_home_pp_goals_mean",
        "pred_home_total_goals_mean",
        "pred_home_5v5_xgf_p60_mean",
        "pred_home_pp_xgf_p60_mean",
        "pred_away_5v5_goals_mean",
        "pred_away_pp_goals_mean",
        "pred_away_total_goals_mean",
        "pred_away_5v5_xgf_p60_mean",
        "pred_away_pp_xgf_p60_mean",
        "pred_home_5v5_toi_mean",
        "pred_home_pp_toi_mean",
        "pred_home_sh_toi_mean",
        "pred_away_5v5_toi_mean",
        "pred_away_pp_toi_mean",
        "pred_away_sh_toi_mean",
    ]

    pred_results = pred_results[columns]

    return pred_results


def process_winners(predicted_results: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    condition = schedule.game_state == "OFF"
    finished_games = schedule.loc[condition].reset_index(drop=True)

    winners = np.where(
        finished_games.home_score > finished_games.away_score, finished_games.home_team, finished_games.away_team
    )

    winners_dict = dict(zip(finished_games.game_id.astype(int), winners, strict=False))

    predicted_results["actual_winner"] = predicted_results.game_id.astype(int).map(winners_dict)
    predicted_results["pred_correct"] = np.where(predicted_results.pred_winner == predicted_results.actual_winner, 1, 0)

    columns = [
        "game_id",
        "home_team",
        "away_team",
        "pred_winner",
        "actual_winner",
        "pred_correct",
        "pred_home_win",
        "pred_away_win",
        "pred_draw",
        "pred_home_win_percent",
        "pred_away_win_percent",
        "pred_draw_percent",
        "pred_home_5v5_goals_mean",
        "pred_home_pp_goals_mean",
        "pred_home_total_goals_mean",
        "pred_home_5v5_xgf_p60_mean",
        "pred_home_pp_xgf_p60_mean",
        "pred_away_5v5_goals_mean",
        "pred_away_pp_goals_mean",
        "pred_away_total_goals_mean",
        "pred_away_5v5_xgf_p60_mean",
        "pred_away_pp_xgf_p60_mean",
        "pred_home_5v5_toi_mean",
        "pred_home_pp_toi_mean",
        "pred_home_sh_toi_mean",
        "pred_away_5v5_toi_mean",
        "pred_away_pp_toi_mean",
        "pred_away_sh_toi_mean",
    ]

    predicted_results = predicted_results[columns]

    return predicted_results


def random_float() -> np.float64:
    """Docstring."""
    random_generator = np.random.default_rng()

    return random_generator.triangular(left=0.0, mode=0.5, right=1.0)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--all_dates", help="Upload play-by-play data", action="store_true")
    parser.add_argument(
        "-s",
        "--simulations",
        help="Number of simulations per game to run",
        action="store",
        default="1_000_000",
        type=int,
    )
    parser.add_argument(
        "-n",
        "--number_of_cores",
        help="Number of cores / pools for multiprocessing",
        action="store",
        default="4",
        type=int,
    )
    args = parser.parse_args()

    team_stats_filepath = Path("./data/team_stats.csv")

    if team_stats_filepath.exists():
        existing_team_stats = pd.read_csv(team_stats_filepath)
        existing_game_ids = existing_team_stats.game_id.unique().tolist()

    else:
        existing_team_stats = pd.DataFrame()
        existing_game_ids = []

    season = Season(2024)
    schedule = season.schedule()

    condition = schedule.game_state == "OFF"
    game_ids = schedule.loc[condition].game_id.unique().tolist()
    game_ids = [x for x in game_ids if x not in existing_game_ids]

    if game_ids:
        scraper = Scraper(game_ids, disable_progress_bar=True)
        scraper.prep_team_stats(level="game", disable_progress_bar=True)
        team_stats = scraper.team_stats

    else:
        team_stats = pd.DataFrame()

    if team_stats_filepath.exists():
        concat_list = [existing_team_stats, team_stats]
        team_stats = pd.concat(concat_list, ignore_index=True)

    team_stats.to_csv(team_stats_filepath, index=False)

    today_date = dt.datetime.today().strftime("%Y-%m-%d")

    if not args.all_dates:
        condition = schedule.game_date == today_date

    else:
        condition = schedule.game_date <= today_date

    game_ids_dates = schedule.loc[condition][["game_id", "game_date"]].drop_duplicates()
    simulation_game_dates = game_ids_dates.game_date.unique().tolist()

    if args.all_dates:
        simulation_game_dates = simulation_game_dates[20:]

    for simulation_date in simulation_game_dates:
        nhl_stats = prep_nhl_stats(team_stats=team_stats, schedule=schedule, latest_date=simulation_date)

        team_strength_scores = prep_team_strength_scores(
            team_stats=team_stats, nhl_stats=nhl_stats, schedule=schedule, latest_date=simulation_date
        )

        todays_games = prep_todays_games(
            schedule=schedule,
            team_strength_scores=team_strength_scores,
            nhl_stats=nhl_stats,
            todays_date=simulation_date,
        )

        # print(todays_games)

        total_simulations = args.simulations

        for idx, game in todays_games.iterrows():
            predictions = []

            with ChickenProgress() as progress:
                pbar_message = f"Simulating {game.game_id}..."
                simulation_task = progress.add_task(pbar_message, total=total_simulations)

                for sim_number in range(0, total_simulations):
                    prediction = simulate_game(game=game)
                    predictions.append(prediction)

                    if sim_number == total_simulations - 1:
                        pbar_message = f"Finished simulating {game.game_id}"

                    progress.update(simulation_task, description=pbar_message, advance=1, refresh=True)

            predictions = pd.DataFrame(predictions)

            predicted_results = process_predictions(predictions=predictions)
            predicted_results = process_winners(predicted_results=predicted_results, schedule=schedule)

            predicted_results_path = Path("./simulations/predicted_results_experiment.csv")

            if predicted_results_path.exists():
                mode = "a"
                headers = False

            else:
                mode = "w"
                headers = True

            predicted_results.to_csv(predicted_results_path, mode=mode, header=headers, index=False)


if __name__ == "__main__":
    main()
