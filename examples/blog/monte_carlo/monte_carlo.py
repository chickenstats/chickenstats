import pandas as pd
import numpy as np
from scipy.stats import poisson

from chickenstats.chicken_nhl import Season, Scraper
from chickenstats.utilities import ChickenProgress

from pathlib import Path

import datetime as dt


def add_strength_state(
    team_stats: pd.DataFrame, schedule: pd.DataFrame
) -> pd.DataFrame:
    """Add a secondary strength state column to team stats data.

    Parameters:
        team_stats (pd.DataFrame):
            Pandas dataframe of team statistics aggregated from the `chickenstats` library
        schedule (pd.DataFrame):
            Schedule as Pandas dataframe from the `chickenstats` library

    """
    df = team_stats.copy(deep=True)

    home_map = dict(zip(schedule.game_id.astype(str), schedule.home_team))

    df["is_home"] = df.game_id.astype(str).map(home_map)

    df.is_home = np.where(df.is_home == df.team, 1, 0)

    pp_list = ["5v4", "5v3", "4v3"]
    sh_list = ["4v5", "3v5", "3v4"]

    conditions = [
        df.strength_state == "5v5",
        df.strength_state.isin(pp_list),
        df.strength_state.isin(sh_list),
    ]

    values = ["5v5", "powerplay", "shorthanded"]

    df["strength_state2"] = np.select(conditions, values, default=None)

    return df


def prep_nhl_stats(team_stats: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """Prepare a dataframe of NHL average statistics by venue and strength state.

    Used to calculate team offensive and defensive ratings.

    Parameters:
        team_stats (pd.DataFrame):
            Pandas dataframe of team statistics aggregated from the `chickenstats` library

    """
    df = team_stats.copy()

    df = add_strength_state(team_stats=df, schedule=schedule)

    group_columns = ["season", "session", "is_home", "strength_state2"]

    stat_cols = {
        x: "sum"
        for x in df.columns
        if x not in group_columns
        and "p60" not in x
        and "percent" not in x
        and df[x].dtype != "object"
    }

    stat_cols.update({"game_id": "nunique"})

    df = df.groupby(group_columns, as_index=False).agg(stat_cols)

    df["toi_gp"] = df.toi / df.game_id

    df["gf_p60"] = df.gf / df.toi * 60
    df["ga_p60"] = df.ga / df.toi * 60

    df["xgf_p60"] = df.xgf / df.toi * 60
    df["xga_p60"] = df.xga / df.toi * 60

    return df


def add_nhl_mean(
    columns: list, team_stats_group: pd.DataFrame, nhl_stats: pd.DataFrame
):
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
            np.logical_and(
                team_stats_group.strength_state2 == "5v5", team_stats_group.is_home == 1
            ),
            np.logical_and(
                team_stats_group.strength_state2 == "5v5", team_stats_group.is_home == 0
            ),
            np.logical_and(
                team_stats_group.strength_state2 == "powerplay",
                team_stats_group.is_home == 1,
            ),
            np.logical_and(
                team_stats_group.strength_state2 == "powerplay",
                team_stats_group.is_home == 0,
            ),
            np.logical_and(
                team_stats_group.strength_state2 == "shorthanded",
                team_stats_group.is_home == 1,
            ),
            np.logical_and(
                team_stats_group.strength_state2 == "shorthanded",
                team_stats_group.is_home == 0,
            ),
        ]

        values = [
            nhl_stats.loc[
                np.logical_and(
                    nhl_stats.strength_state2 == "5v5", nhl_stats.is_home == 1
                )
            ][column],
            nhl_stats.loc[
                np.logical_and(
                    nhl_stats.strength_state2 == "5v5", nhl_stats.is_home == 0
                )
            ][column],
            nhl_stats.loc[
                np.logical_and(
                    nhl_stats.strength_state2 == "powerplay", nhl_stats.is_home == 1
                )
            ][column],
            nhl_stats.loc[
                np.logical_and(
                    nhl_stats.strength_state2 == "powerplay", nhl_stats.is_home == 0
                )
            ][column],
            nhl_stats.loc[
                np.logical_and(
                    nhl_stats.strength_state2 == "shorthanded", nhl_stats.is_home == 1
                )
            ][column],
            nhl_stats.loc[
                np.logical_and(
                    nhl_stats.strength_state2 == "shorthanded", nhl_stats.is_home == 0
                )
            ][column],
        ]

        team_stats_group[f"mean_nhl_{column}"] = np.select(
            conditions, values, default=np.nan
        )

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
        team_stats_group.team_xgf_p60 / team_stats_group.mean_nhl_xgf_p60
    )
    team_stats_group["team_def_strength"] = (
        team_stats_group.team_xga_p60 / team_stats_group.mean_nhl_xga_p60
    )

    team_stats_group["toi_comp"] = (
        team_stats_group.toi_gp / team_stats_group.mean_nhl_toi_gp
    )

    return team_stats_group


def prep_team_strength_scores(
    team_stats: pd.DataFrame,
    nhl_stats: pd.DataFrame,
    schedule: pd.DataFrame,
    predict_columns: list = ["xgf_p60", "xga_p60", "toi_gp"],
) -> pd.DataFrame:
    """Prepare a dataframe of team statistics by venue and strength state, including offensive and defensive ratings.

    Parameters:
        team_stats (pd.DataFrame):
            Pandas dataframe of team statistics aggregated from the `chickenstats` library
        nhl_stats (pd.DataFrame):
            Pandas dataframe of NHL stats aggregated from the `chickenstats` library
        schedule (pd.DataFrame):
            NHL schedule scraped using the `chickenstats` library

    """
    df = team_stats.copy(deep=True)

    df = add_strength_state(team_stats=df, schedule=schedule)

    group_columns = ["season", "session", "team", "is_home", "strength_state2"]

    stat_cols = {
        x: "sum"
        for x in df.columns
        if x not in group_columns
        and "p60" not in x
        and "percent" not in x
        and df[x].dtype != "object"
    }

    stat_cols.update({"game_id": "nunique"})

    df = df.groupby(group_columns, as_index=False).agg(stat_cols)

    df["toi_gp"] = df.toi / df.game_id
    df["team_xgf_p60"] = df.xgf / df.toi * 60
    df["team_xga_p60"] = df.xga / df.toi * 60

    df = add_nhl_mean(columns=predict_columns, team_stats_group=df, nhl_stats=nhl_stats)

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


def prep_todays_games(
    schedule: pd.DataFrame, team_strength_scores: pd.DataFrame, nhl_stats: pd.DataFrame
) -> pd.DataFrame:
    """Docstring."""
    todays_date = dt.datetime.today().strftime("%Y-%m-%d")

    todays_games = schedule.loc[schedule.game_date == todays_date].reset_index(
        drop=True
    )

    strength_states = ["5v5", "powerplay", "shorthanded"]
    short_strengths = {"5v5": "5v5", "powerplay": "pp", "shorthanded": "sh"}
    columns = ["xgf_p60", "xga_p60", "toi_gp"]
    venues = ["away", "home"]

    for strength_state in strength_states:
        for column in columns:
            for dummy_value, venue in enumerate(venues):
                todays_games[
                    f"mean_nhl_{short_strengths[strength_state]}_{venue}_{column}"
                ] = nhl_stats.loc[
                    np.logical_and(
                        nhl_stats.strength_state2 == strength_state,
                        nhl_stats.is_home == dummy_value,
                    )
                ][column].iloc[0]

    todays_games["home_5v5_off_strength"] = np.nan
    todays_games["home_5v5_def_strength"] = np.nan
    todays_games["home_5v5_toi_comp"] = np.nan
    todays_games["home_pp_off_strength"] = np.nan
    todays_games["home_pp_toi_comp"] = np.nan
    todays_games["home_sh_def_strength"] = np.nan
    todays_games["home_sh_toi_comp"] = np.nan

    todays_games["away_5v5_off_strength"] = np.nan
    todays_games["away_5v5_def_strength"] = np.nan
    todays_games["away_5v5_toi_comp"] = np.nan
    todays_games["away_pp_off_strength"] = np.nan
    todays_games["away_pp_toi_comp"] = np.nan
    todays_games["away_sh_def_strength"] = np.nan
    todays_games["away_sh_toi_comp"] = np.nan

    for dummy_value, venue in enumerate(venues):
        for team in todays_games[f"{venue}_team"].unique():
            for strength_state in strength_states:
                if strength_state in ["5v5", "powerplay"]:
                    todays_games[
                        f"{venue}_{short_strengths[strength_state]}_off_strength"
                    ] = np.where(
                        todays_games[f"{venue}_team"] == team,
                        team_strength_scores.loc[
                            np.logical_and.reduce(
                                [
                                    team_strength_scores.is_home == dummy_value,
                                    team_strength_scores.team == team,
                                    team_strength_scores.strength_state2
                                    == strength_state,
                                ]
                            )
                        ].team_off_strength,
                        todays_games[
                            f"{venue}_{short_strengths[strength_state]}_off_strength"
                        ],
                    )

                if strength_state in ["5v5", "shorthanded"]:
                    todays_games[
                        f"{venue}_{short_strengths[strength_state]}_def_strength"
                    ] = np.where(
                        todays_games[f"{venue}_team"] == team,
                        team_strength_scores.loc[
                            np.logical_and.reduce(
                                [
                                    team_strength_scores.is_home == dummy_value,
                                    team_strength_scores.team == team,
                                    team_strength_scores.strength_state2
                                    == strength_state,
                                ]
                            )
                        ].team_def_strength,
                        todays_games[
                            f"{venue}_{short_strengths[strength_state]}_def_strength"
                        ],
                    )

                todays_games[f"{venue}_{short_strengths[strength_state]}_toi_comp"] = (
                    np.where(
                        todays_games[f"{venue}_team"] == team,
                        team_strength_scores.loc[
                            np.logical_and.reduce(
                                [
                                    team_strength_scores.is_home == dummy_value,
                                    team_strength_scores.team == team,
                                    team_strength_scores.strength_state2
                                    == strength_state,
                                ]
                            )
                        ].toi_comp,
                        todays_games[
                            f"{venue}_{short_strengths[strength_state]}_toi_comp"
                        ],
                    )
                )

    todays_games["pred_home_toi_5v5"] = (
        todays_games.home_5v5_toi_comp
        * todays_games.away_5v5_toi_comp
        * todays_games.mean_nhl_5v5_home_toi_gp
    )
    todays_games["pred_home_toi_pp"] = (
        todays_games.home_pp_toi_comp
        * todays_games.away_sh_toi_comp
        * todays_games.mean_nhl_pp_home_toi_gp
    )
    todays_games["pred_home_toi_sh"] = (
        todays_games.home_sh_toi_comp
        * todays_games.away_pp_toi_comp
        * todays_games.mean_nhl_sh_home_toi_gp
    )

    todays_games["pred_home_5v5_xgf_p60"] = (
        todays_games.home_5v5_off_strength
        * todays_games.away_5v5_def_strength
        * todays_games.mean_nhl_5v5_home_xgf_p60
    )
    todays_games["pred_home_5v5_xga_p60"] = (
        todays_games.home_5v5_def_strength
        * todays_games.away_5v5_off_strength
        * todays_games.mean_nhl_5v5_home_xga_p60
    )

    todays_games["pred_home_pp_xgf_p60"] = (
        todays_games.home_pp_off_strength
        * todays_games.away_sh_def_strength
        * todays_games.mean_nhl_pp_home_xgf_p60
    )
    todays_games["pred_home_sh_xga_p60"] = (
        todays_games.home_sh_def_strength
        * todays_games.away_pp_off_strength
        * todays_games.mean_nhl_sh_home_xga_p60
    )

    todays_games["pred_away_5v5_xgf_p60"] = (
        todays_games.home_5v5_def_strength
        * todays_games.away_5v5_off_strength
        * todays_games.mean_nhl_5v5_away_xgf_p60
    )
    todays_games["pred_away_5v5_xga_p60"] = (
        todays_games.home_5v5_off_strength
        * todays_games.away_5v5_def_strength
        * todays_games.mean_nhl_5v5_away_xga_p60
    )

    todays_games["pred_away_pp_xgf_p60"] = (
        todays_games.away_pp_off_strength
        * todays_games.home_sh_def_strength
        * todays_games.mean_nhl_pp_away_xgf_p60
    )
    todays_games["pred_away_sh_xga_p60"] = (
        todays_games.away_sh_def_strength
        * todays_games.home_pp_off_strength
        * todays_games.mean_nhl_sh_away_xga_p60
    )

    return todays_games


def simulate_game(game: pd.Series) -> dict:
    """Docstring."""
    prediction = {}

    home_5v5_toi = poisson.ppf(
        (np.random.randint(0, 100) / 100), game.pred_home_toi_5v5
    )
    home_pp_toi = poisson.ppf((np.random.randint(0, 100) / 100), game.pred_home_toi_pp)
    home_sh_toi = poisson.ppf((np.random.randint(0, 100) / 100), game.pred_home_toi_sh)

    total_toi = home_5v5_toi + home_pp_toi + home_sh_toi

    if total_toi > 60:
        home_5v5_toi = home_5v5_toi - ((home_5v5_toi / total_toi) * (total_toi - 60))
        home_pp_toi = home_pp_toi - ((home_pp_toi / total_toi) * (total_toi - 60))
        home_sh_toi = home_sh_toi - ((home_sh_toi / total_toi) * (total_toi - 60))

    home_5v5_xgf_p60 = poisson.ppf(
        (np.random.randint(0, 100) / 100), game.pred_home_5v5_xgf_p60
    )
    home_pp_xgf_p60 = poisson.ppf(
        (np.random.randint(0, 100) / 100), game.pred_home_pp_xgf_p60
    )

    away_5v5_xgf_p60 = poisson.ppf(
        (np.random.randint(0, 100) / 100), game.pred_away_5v5_xgf_p60
    )
    away_pp_xgf_p60 = poisson.ppf(
        (np.random.randint(0, 100) / 100), game.pred_away_pp_xgf_p60
    )

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
            "pred_home_5v5_xgf_p60": home_5v5_xgf_p60,
            "pred_home_pp_xgf_p60": home_5v5_xgf_p60,
            "pred_home_5v5_goals": home_5v5_goals,
            "pred_home_pp_goals": home_pp_goals,
            "pred_home_total_goals": home_total_goals,
            "pred_away_5v5_xgf_p60": away_5v5_xgf_p60,
            "pred_away_pp_xgf_p60": away_5v5_xgf_p60,
            "pred_away_5v5_goals": away_5v5_goals,
            "pred_away_pp_goals": away_pp_goals,
            "pred_away_total_goals": away_total_goals,
            "home_win": home_win,
            "away_win": away_win,
            "draw": draw,
        }
    )

    return prediction


def main() -> None:
    """Main function."""
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

    nhl_stats = prep_nhl_stats(team_stats=team_stats, schedule=schedule)

    team_strength_scores = prep_team_strength_scores(
        team_stats=team_stats, nhl_stats=nhl_stats, schedule=schedule
    )

    todays_games = prep_todays_games(
        schedule=schedule,
        team_strength_scores=team_strength_scores,
        nhl_stats=nhl_stats,
    )

    predictions = []

    total_simulations = 1_000_000

    for idx, game in todays_games.iterrows():
        with ChickenProgress() as progress:
            pbar_message = f"Simulating {game.game_id}..."
            simulation_task = progress.add_task(pbar_message, total=total_simulations)

            for sim_number in range(0, total_simulations):
                prediction = simulate_game(game=game)
                predictions.append(prediction)

                if sim_number == total_simulations - 1:
                    pbar_message = f"Finished simulating {game.game_id}"

                progress.update(
                    simulation_task, description=pbar_message, advance=1, refresh=True
                )

    predictions = pd.DataFrame(predictions)
    predictions.to_csv(
        Path("./simulations/predictions.csv"), mode="a", header=False, index=False
    )

    todays_date = dt.datetime.today().strftime("%Y-%m-%d")
    savefile = Path(
        f"./simulations/strength_scores/team_strength_scores_{todays_date}.csv"
    )
    team_strength_scores.to_csv(savefile, index=False)


if __name__ == "__main__":
    main()
