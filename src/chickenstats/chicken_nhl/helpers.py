import importlib.resources
from xgboost import XGBClassifier

import numpy as np
import pandas as pd


def load_model(model_name: str, model_version: str) -> XGBClassifier:
    """Loads specified xG model from package files."""
    model = XGBClassifier()

    with importlib.resources.as_file(
        importlib.resources.files("chickenstats.chicken_nhl.xg_models").joinpath(
            f"{model_name}-{model_version}.json"
        )
    ) as file:
        model.load_model(file)

    return model


def return_name_html(info: str) -> str:
    """Fixes names from HTML endpoint. Method originally published by Harry Shomer.

    In the PBP html the name is in a format like: 'Center - MIKE RICHARDS'
    Some also have a hyphen in their last name so can't just split by '-'.

    Used for consistency with other data providers.
    """
    s = info.index("-")  # Find first hyphen
    return info[s + 1 :].strip(" ")  # The name should be after the first hyphen


def hs_strip_html(td: list) -> list:
    """Strips HTML code from HTML endpoints. Methodology originally published by Harry Shomer.

    Parses html for html events function
    """
    for y in range(len(td)):
        # Get the 'br' tag for the time column...this gets us time remaining instead of elapsed and remaining combined
        if y == 3:
            td[y] = td[
                y
            ].get_text()  # This gets us elapsed and remaining combined-< 3:0017:00
            index = td[y].find(":")
            td[y] = td[y][: index + 3]
        elif (y == 6 or y == 7) and td[0] != "#":  # Not covered by tests
            # 6 & 7-> These are the player 1 ice one's
            # The second statement controls for when it's just a header
            baz = td[y].find_all("td")
            bar = [
                baz[z] for z in range(len(baz)) if z % 4 != 0
            ]  # Because of previous step we get repeats...delete some

            # The setup in the list is now: Name/Number->Position->Blank...and repeat
            # Now strip all the html
            players = []
            for i in range(len(bar)):
                if i % 3 == 0:
                    try:
                        name = return_name_html(bar[i].find("font")["title"])
                        number = (
                            bar[i].get_text().strip("\n")
                        )  # Get number and strip leading/trailing newlines
                    except KeyError:
                        name = ""
                        number = ""
                elif i % 3 == 1:
                    if name != "":
                        position = bar[i].get_text()
                        players.append([name, number, position])

            td[y] = players
        else:
            td[y] = td[y].get_text()

    return td


def convert_to_list(
    obj: str | list | float | int | pd.Series | np.ndarray, object_type: str
) -> list:
    """If the object is not a list or list-like, converts the object to a list of length one."""
    if (
        isinstance(obj, str) is True
        or isinstance(obj, (int, np.integer)) is True
        or isinstance(obj, (float, np.float64)) is True
    ):
        obj = [int(obj)]

    elif isinstance(obj, pd.Series) is True or isinstance(obj, np.ndarray) is True:
        obj = obj.tolist()

    elif isinstance(obj, tuple) is True:
        obj = list(obj)

    elif isinstance(obj, list) is True:
        pass

    else:
        raise Exception(
            f"'{obj}' not a supported {object_type} or range of {object_type}s"
        )

    return obj


def norm_coords(data: pd.DataFrame, norm_team: str) -> pd.DataFrame:
    """Normalize coordinates based on specified team."""
    norm_team_conds = np.logical_and(data.event_team == norm_team, data.coords_x < 0)

    data["norm_coords_x"] = np.where(norm_team_conds, data.coords_x * -1, data.coords_x)

    data["norm_coords_y"] = np.where(norm_team_conds, data.coords_y * -1, data.coords_y)

    opp_team_conds = np.logical_and(data.event_team != norm_team, data.coords_x > 0)

    data["norm_coords_x"] = np.where(
        opp_team_conds, data.coords_x * -1, data.norm_coords_x
    )

    data["norm_coords_y"] = np.where(
        opp_team_conds, data.coords_y * -1, data.norm_coords_y
    )

    return data


def prep_p60(df: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    stats_list = [
        "g",
        "ihdg",
        "a1",
        "a2",
        "ixg",
        "isf",
        "ihdsf",
        "imsf",
        "ihdm",
        "iff",
        "ihdf",
        "isb",
        "icf",
        "ibs",
        "igive",
        "itake",
        "ihf",
        "iht",
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
        "gf",
        "ga",
        "hdgf",
        "hdga",
        "xgf",
        "xga",
        "sf",
        "sa",
        "hdsf",
        "hdsa",
        "ff",
        "fa",
        "hdff",
        "hdfa",
        "cf",
        "ca",
        "bsf",
        "bsa",
        "msf",
        "msa",
        "hdmsf",
        "hdmsa",
        "teammate_block",
        "hf",
        "ht",
        "give",
        "take",
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

    stats_list = [x for x in stats_list if x in df.columns]

    for stat in stats_list:
        df[f"{stat}_p60"] = (df[f"{stat}"] / df.toi) * 60

    return df


def prep_oi_percent(df: pd.DataFrame) -> pd.DataFrame:
    """Docstring."""
    stats_for = [
        "gf",
        "hdgf",
        "xgf",
        "sf",
        "hdsf",
        "ff",
        "hdff",
        "cf",
        "bsf",
        "msf",
        "hdmsf",
        "hf",
        "take",
    ]

    stats_against = [
        "ga",
        "hdga",
        "xga",
        "sa",
        "hdsa",
        "fa",
        "hdfa",
        "ca",
        "bsa",
        "msa",
        "hdmsa",
        "ht",
        "give",
    ]

    stats_tuples = list(zip(stats_for, stats_against))

    for stat_for, stat_against in stats_tuples:
        if stat_for not in df.columns:
            df[f"{stat_for}_percent"] = 0

        elif stat_against not in df.columns:
            df[f"{stat_for}_percent"] = 1

        else:
            df[f"{stat_for}_percent"] = df[f"{stat_for}"] / (
                df[f"{stat_for}"] + df[f"{stat_against}"]
            )

    return df
