import pandas as pd
import numpy as np

from chickenstats.chicken_nhl import Season

from pathlib import Path


def process_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    predictions["draw"] = np.where(predictions.home_win == predictions.away_win, 1, 0)

    group_list = ["game_id", "home_team", "away_team"]

    agg_stats_sum = ["home_win", "away_win", "draw"]
    agg_stats_mean = [
        x for x in predictions.columns if x not in group_list and x not in agg_stats_sum
    ]
    agg_stats = {x: "sum" for x in agg_stats_sum} | {x: "mean" for x in agg_stats_mean}

    pred_results = predictions.groupby(group_list, as_index=False).agg(agg_stats)

    for stat in agg_stats_sum:
        pred_results[f"pred_{stat}_percent"] = pred_results[stat] / pred_results[
            agg_stats_sum
        ].sum(axis=1)

    rename_columns = {x: f"pred_{x}" for x in agg_stats_sum} | {
        x: f"{x}_mean" for x in agg_stats_mean
    }

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


def process_winners(
    predicted_results: pd.DataFrame, schedule: pd.DataFrame
) -> pd.DataFrame:
    """Docstring."""
    condition = schedule.game_state == "OFF"
    finished_games = schedule.loc[condition].reset_index(drop=True)

    winners = np.where(
        finished_games.home_score > finished_games.away_score,
        finished_games.home_team,
        finished_games.away_team,
    )

    winners_dict = dict(zip(finished_games.game_id, winners))

    predicted_results["actual_winner"] = predicted_results.game_id.map(winners_dict)
    predicted_results["pred_correct"] = np.where(
        predicted_results.pred_winner == predicted_results.actual_winner, 1, 0
    )

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


predictions_path = Path("./simulations/predictions.csv")
predictions = pd.read_csv(predictions_path)

season = Season(2024)
schedule = season.schedule()

predicted_results = process_predictions(predictions)
predicted_results = process_winners(
    predicted_results=predicted_results, schedule=schedule
)

predicted_results_path = Path("./simulations/predicted_results.csv")
predicted_results.to_csv(predicted_results_path, index=False)
