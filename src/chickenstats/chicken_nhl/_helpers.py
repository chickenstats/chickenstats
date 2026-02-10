import importlib.resources
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from xgboost import XGBClassifier


def load_model(model_name: str, model_version: str) -> XGBClassifier:
    """Loads specified xG model from package files."""
    model = XGBClassifier()

    with importlib.resources.as_file(
        importlib.resources.files("chickenstats.chicken_nhl.xg_models").joinpath(f"{model_name}-{model_version}.json")
    ) as file:
        model.load_model(file)

    return model


def load_score_adjustments() -> dict:
    """Loads score adjustments from pickle file."""
    with (
        importlib.resources.as_file(
            importlib.resources.files("chickenstats.chicken_nhl.score_adjustments").joinpath("score_adjustments.pkl")
        ) as file,
        open(file, "rb") as open_file,
    ):
        score_adjustments = pickle.load(open_file)

    return score_adjustments


def calculate_score_adjustment(play: dict, score_adjustments: dict) -> dict:
    """Calculates score adjustment for play."""
    if play["event"] in ["GOAL", "SHOT", "MISS", "BLOCK"]:
        if play["home_score_diff"] < -3:
            home_score_diff = -3
        elif play["home_score_diff"] > 3:
            home_score_diff = 3
        else:
            home_score_diff = play["home_score_diff"]

        if play["event"] == "BLOCK" and play["teammate_block"] == 0:
            event_team = play["opp_team"]
        else:
            event_team = play["event_team"]

        is_home = 1 if event_team == play["home_team"] else 0

        adjusted_columns = ["goal", "pred_goal", "shot", "miss", "block", "teammate_block", "fenwick", "corsi"]

        for adjusted_column in adjusted_columns:
            if play["strength_state"] in ["4v5", "3v5", "3v4"]:
                is_home = 0 if is_home == 1 else 1
                strength_state = play["strength_state"][::-1]

            else:
                strength_state = play["strength_state"]

            if is_home == 1:
                weight_column = f"home_{adjusted_column}_weight"
            else:
                weight_column = f"away_{adjusted_column}_weight"

            if adjusted_column == "miss":
                weight_column = weight_column.replace(adjusted_column, "fenwick")

            if adjusted_column == "block":
                weight_column = weight_column.replace(adjusted_column, "corsi")

            if adjusted_column == "teammate_block":
                weight_column = weight_column.replace(adjusted_column, "corsi")

            if "E" not in strength_state:
                play[f"{adjusted_column}_adj"] = (
                    score_adjustments[strength_state][home_score_diff][weight_column] * play[adjusted_column]
                )

            else:
                play[f"{adjusted_column}_adj"] = play[adjusted_column] * 1

    return play


def return_name_html(info: str) -> str:
    """Fixes names from HTML endpoint. Method originally published by Harry Shomer.

    In the PBP HTML the name is in a format like: 'Center - MIKE RICHARDS'
    Some also have a hyphen in their last name so can't just split by '-'

    Used for consistency with other data providers.
    """
    s = info.index("-")  # Find first hyphen
    return info[s + 1 :].strip(" ")  # The name should be after the first hyphen


def hs_strip_html(td: list) -> list:
    """Strips HTML code from HTML endpoints. Methodology originally published by Harry Shomer.

    Parses HTML for HTML events function
    """
    if not isinstance(td, list):
        td = list(td)

    for y in range(len(td)):
        # Get the 'br' tag for the time column...this gets us time remaining instead of elapsed and remaining combined
        if y == 3:
            td[y] = td[y].get_text()  # This gets us elapsed and remaining combined-< 3:0017:00
            index = td[y].find(":")
            td[y] = td[y][: index + 3]
        elif (y == 6 or y == 7) and td[0] != "#":  # no cover: start
            # 6 & 7-> These are the player 1 ice one's
            # The second statement controls for when it's just a header
            baz = td[y].find_all("td")
            bar = [
                baz[z] for z in range(len(baz)) if z % 4 != 0
            ]  # Because of previous step we get repeats...delete some

            # The setup in the list is now: Name/Number->Position->Blank...and repeat
            # Now strip all the HTML
            players = []
            for i in range(len(bar)):
                if i % 3 == 0:
                    try:
                        name = return_name_html(bar[i].find("font")["title"])
                        number = bar[i].get_text().strip("\n")  # Get number and strip leading/trailing newlines
                    except KeyError:
                        name = ""
                        number = ""
                elif i % 3 == 1 and name != "":
                    position = bar[i].get_text()
                    players.append([name, number, position])

            td[y] = players  # no cover: stop
        else:
            td[y] = td[y].get_text()

    return td


def convert_to_list(obj: str | list | float | int | pd.Series | np.ndarray, object_type: str) -> list:
    """If the object is not a list or list-like, converts the object to a list of length one."""
    if (
        isinstance(obj, str) is True
        or isinstance(obj, int | np.integer) is True
        or isinstance(obj, float | np.float64) is True
    ):
        try:
            obj = [int(obj)]

        except ValueError:
            obj = [obj]

    elif isinstance(obj, pd.Series) is True or isinstance(obj, np.ndarray) is True:
        obj = obj.tolist()

    elif isinstance(obj, tuple):
        obj = list(obj)

    elif isinstance(obj, list):
        pass

    else:
        raise Exception(f"'{obj}' not a supported {object_type} or range of {object_type}s")

    return obj


def norm_coords(data: pd.DataFrame, norm_column: str, norm_value: str) -> pd.DataFrame:
    """Normalize coordinates based on specified team."""
    norm_conditions = np.logical_and(data[norm_column] == norm_value, data.coords_x < 0)

    data["norm_coords_x"] = np.where(norm_conditions, data.coords_x * -1, data.coords_x)

    data["norm_coords_y"] = np.where(norm_conditions, data.coords_y * -1, data.coords_y)

    opp_conditions = np.logical_and(data[norm_column] != norm_value, data.coords_x > 0)

    data["norm_coords_x"] = np.where(opp_conditions, data.coords_x * -1, data.norm_coords_x)

    data["norm_coords_y"] = np.where(opp_conditions, data.coords_y * -1, data.norm_coords_y)

    return data


def charts_directory(target_path: str | Path | None = None) -> None:
    """Creates tutorials directories in target directory. Defaults to current directory."""
    if not target_path:
        target_path = Path.cwd()

    charts_path = target_path / "charts"

    if not charts_path.exists():
        charts_path.mkdir()
