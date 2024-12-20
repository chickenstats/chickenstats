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


def norm_coords(data: pd.DataFrame, norm_column: str, norm_value: str) -> pd.DataFrame:
    """Normalize coordinates based on specified team."""
    norm_conditions = np.logical_and(data[norm_column] == norm_value, data.coords_x < 0)

    data["norm_coords_x"] = np.where(norm_conditions, data.coords_x * -1, data.coords_x)

    data["norm_coords_y"] = np.where(norm_conditions, data.coords_y * -1, data.coords_y)

    opp_conditions = np.logical_and(data[norm_column] != norm_value, data.coords_x > 0)

    data["norm_coords_x"] = np.where(
        opp_conditions, data.coords_x * -1, data.norm_coords_x
    )

    data["norm_coords_y"] = np.where(
        opp_conditions, data.coords_y * -1, data.norm_coords_y
    )

    return data


def prep_p60(df: pd.DataFrame) -> pd.DataFrame:
    """Adds columns to normalize statistics on a 60-minute basis.

    Parameters:
        df (pd.DataFrame):
            Statistics data from chickenstats.chicken_nhl.Scraper

    Returns:
        season (int):
            Season as 8-digit number, e.g., 2023 for 2023-24 season
        session (str):
            Whether game is regular season, playoffs, or pre-season, e.g., R
        game_id (int):
            Unique game ID assigned by the NHL, e.g., 2023020001
        game_date (int):
            Date game was played, e.g., 2023-10-10
        player (str):
            Player's name, e.g., FILIP FORSBERG
        eh_id (str):
            Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
        api_id (str):
            NHL API ID for the player, e.g., 8476887
        position (str):
            Player's position, e.g., L
        team (str):
            Player's team, e.g., NSH
        opp_team (str):
            Opposing team, e.g., TBL
        strength_state (str):
            Strength state, e.g., 5v5
        period (int):
            Period, e.g., 3
        score_state (str):
            Score state, e.g., 2v1
        forwards (str):
            Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
        forwards_eh_id (str):
            Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
        forwards_api_id (str):
            Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
        defense (str):
            Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
        defense_eh_id (str):
            Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
        defense_api_id (str):
            Defense teammates' NHL API IDs, e.g., 8474151, 8478851
        own_goalie (str):
            Own goalie, e.g., JUUSE SAROS
        own_goalie_eh_id (str):
            Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
        own_goalie_api_id (str):
            Own goalie's NHL API ID, e.g., 8477424
        opp_forwards (str):
            Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
        opp_forwards_eh_id (str):
            Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
        opp_forwards_api_id (str):
            Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
        opp_defense (str):
            Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
        opp_defense_eh_id (str):
            Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
        opp_defense_api_id (str):
            Opposing defense's NHL API IDs, e.g., 8480246, 8475167
        opp_goalie (str):
            Opposing goalie, e.g., JONAS JOHANSSON
        opp_goalie_eh_id (str):
            Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
        opp_goalie_api_id (str):
            Opposing goalie's NHL API ID, e.g., 8477992
        toi (float):
            Time on-ice, in minutes, e.g, 0.483333
        g (int):
            Goals scored, e.g, 0
        ihdg (int):
            High-danger goals scored, e.g, 0
        a1 (int):
            Primary assists, e.g, 0
        a2 (int):
            Secondary assists, e.g, 0
        ixg (float):
            Individual xG for, e.g, 1.014336
        isf (int):
            Individual shots taken, e.g, 3
        ihdsf (int):
            High-danger shots taken, e.g, 3
        imsf (int):
            Individual missed shots, e.g, 0
        ihdm (int):
            High-danger missed shots, e.g, 0
        iff (int):
            Individual fenwick for, e.g., 3
        ihdf (int):
            High-danger fenwick for, e.g., 3
        isb (int):
            Shots taken that were blocked, e.g, 0
        icf (int):
            Individual corsi for, e.g., 3
        ibs (int):
            Individual shots blocked on defense, e.g, 0
        igive (int):
            Individual giveaways, e.g, 0
        itake (int):
            Individual takeaways, e.g, 0
        ihf (int):
            Individual hits for, e.g, 0
        iht (int):
            Individual hits taken, e.g, 0
        ifow (int):
            Individual faceoffs won, e.g, 0
        ifol (int):
            Individual faceoffs lost, e.g, 0
        iozfw (int):
            Individual faceoffs won in offensive zone, e.g, 0
        iozfl (int):
            Individual faceoffs lost in offensive zone, e.g, 0
        inzfw (int):
            Individual faceoffs won in neutral zone, e.g, 0
        inzfl (int):
            Individual faceoffs lost in neutral zone, e.g, 0
        idzfw (int):
            Individual faceoffs won in defensive zone, e.g, 0
        idzfl (int):
            Individual faceoffs lost in defensive zone, e.g, 0
        a1_xg (float):
            xG on primary assists, e.g, 0
        a2_xg (float):
            xG on secondary assists, e.g, 0
        ipent0 (int):
            Individual penalty shots against, e.g, 0
        ipent2 (int):
            Individual minor penalties taken, e.g, 0
        ipent4 (int):
            Individual double minor penalties taken, e.g, 0
        ipent5 (int):
            Individual major penalties taken, e.g, 0
        ipent10 (int):
            Individual game misconduct penalties taken, e.g, 0
        ipend0 (int):
            Individual penalty shots drawn, e.g, 0
        ipend2 (int):
            Individual minor penalties taken, e.g, 0
        ipend4 (int):
            Individual double minor penalties drawn, e.g, 0
        ipend5 (int):
            Individual major penalties drawn, e.g, 0
        ipend10 (int):
            Individual game misconduct penalties drawn, e.g, 0
        gf (int):
            Goals for (on-ice), e.g, 0
        hdgf (int):
            High-danger goals for (on-ice), e.g, 0
        ga (int):
            Goals against (on-ice), e.g, 0
        hdga (int):
            High-danger goals against (on-ice), e.g, 0
        xgf (float):
            xG for (on-ice), e.g., 1.258332
        xga (float):
            xG against (on-ice), e.g, 0.000000
        sf (int):
            Shots for (on-ice), e.g, 4
        sa (int):
            Shots against (on-ice), e.g, 0
        hdsf (int):
            High-danger shots for (on-ice), e.g, 3
        hdsa (int):
            High-danger shots against (on-ice), e.g, 0
        ff (int):
            Fenwick for (on-ice), e.g, 4
        fa (int):
            Fenwick against (on-ice), e.g, 0
        hdff (int):
            High-danger fenwick for (on-ice), e.g, 3
        hdfa (int):
            High-danger fenwick against (on-ice), e.g, 0
        cf (int):
            Corsi for (on-ice), e.g, 4
        ca (int):
            Corsi against (on-ice), e.g, 0
        bsf (int):
            Shots taken that were blocked (on-ice), e.g, 0
        bsa (int):
            Shots blocked (on-ice), e.g, 0
        msf (int):
            Missed shots taken (on-ice), e.g, 0
        msa (int):
            Missed shots against (on-ice), e.g, 0
        hdmsf (int):
            High-danger missed shots taken (on-ice), e.g, 0
        hdmsa (int):
            High-danger missed shots against (on-ice), e.g, 0
        teammate_block (int):
            Shots blocked by teammates (on-ice), e.g, 0
        hf (int):
            Hits for (on-ice), e.g, 0
        ht (int):
            Hits taken (on-ice), e.g, 0
        give (int):
            Giveaways (on-ice), e.g, 0
        take (int):
            Takeaways (on-ice), e.g, 0
        ozf (int):
            Offensive zone faceoffs (on-ice), e.g, 0
        nzf (int):
            Neutral zone faceoffs (on-ice), e.g, 1
        dzf (int):
            Defensive zone faceoffs (on-ice), e.g, 0
        fow (int):
            Faceoffs won (on-ice), e.g, 1
        fol (int):
            Faceoffs lost (on-ice), e.g, 0
        ozfw (int):
            Offensive zone faceoffs won (on-ice), e.g, 0
        ozfl (int):
            Offensive zone faceoffs lost (on-ice), e.g, 0
        nzfw (int):
            Neutral zone faceoffs won (on-ice), e.g, 1
        nzfl (int):
            Neutral zone faceoffs lost (on-ice), e.g, 0
        dzfw (int):
            Defensive zone faceoffs won (on-ice), e.g, 0
        dzfl (int):
            Defensive zone faceoffs lost (on-ice), e.g, 0
        pent0 (int):
            Penalty shots allowed (on-ice), e.g, 0
        pent2 (int):
            Minor penalties taken (on-ice), e.g, 0
        pent4 (int):
            Double minor penalties taken (on-ice), e.g, 0
        pent5 (int):
            Major penalties taken (on-ice), e.g, 0
        pent10 (int):
            Game misconduct penalties taken (on-ice), e.g, 0
        pend0 (int):
            Penalty shots drawn (on-ice), e.g, 0
        pend2 (int):
            Minor penalties drawn (on-ice), e.g, 0
        pend4 (int):
            Double minor penalties drawn (on-ice), e.g, 0
        pend5 (int):
            Major penalties drawn (on-ice), e.g, 0
        pend10 (int):
            Game misconduct penalties drawn (on-ice), e.g, 0
        ozs (int):
            Offensive zone starts, e.g, 0
        nzs (int):
            Neutral zone starts, e.g, 0
        dzs (int):
            Defenzive zone starts, e.g, 0
        otf (int):
            On-the-fly starts, e.g, 0
        g_p60 (float):
            Goals scored per 60 minutes
        ihdg_p60 (float):
            Individual high-danger goals scored per 60
        a1_p60 (float):
            Primary assists per 60 minutes
        a2_p60 (float):
            Secondary per 60 minutes
        ixg_p60 (float):
            Individual xG for per 60 minutes
        isf_p60 (float):
            Individual shots for per 60 minutes
        ihdsf_p60 (float):
            Individual high-danger shots for per 60 minutes
        imsf_p60 (float):
            Individual missed shorts for per 60 minutes
        ihdm_p60 (float):
            Individual high-danger missed shots for per 60 minutes
        iff_p60 (float):
            Individual fenwick for per 60 minutes
        ihdff_p60 (float):
            Individual high-danger fenwick for per 60 minutes
        isb_p60 (float):
            Individual shots blocked (for) per 60 minutes
        icf_p60 (float):
            Individual corsi for per 60 minutes
        ibs_p60 (float):
            Individual blocked shots (against) per 60 minutes
        igive_p60 (float):
            Individual giveaways per 60 minutes
        itake_p60 (float):
            Individual takeaways per 60 minutes
        ihf_p60 (float):
            Individual hits for per 60 minutes
        iht_p60 (float):
            Individual hits taken per 60 minutes
        a1_xg_p60 (float):
            Individual primary assists' xG per 60 minutes
        a2_xg_p60 (float):
            Individual secondary assists' xG per 60 minutes
        ipent0_p60 (float):
            Individual penalty shots taken per 60 minutes
        ipent2_p60 (float):
            Individual minor penalties taken per 60 minutes
        ipent4_p60 (float):
            Individual double minor penalties taken per 60 minutes
        ipent5_p60 (float):
            Individual major penalties taken per 60 minutes
        ipent10_p60 (float):
            Individual game misconduct pentalties taken per 60 minutes
        ipend0_p60 (float):
            Individual penalty shots drawn per 60 minutes
        ipend2_p60 (float):
            Individual minor penalties drawn per 60 minutes
        ipend4_p60 (float):
            Individual double minor penalties drawn per 60 minutes
        ipend5_p60 (float):
            Individual major penalties drawn per 60 minutes
        ipend10_p60 (float):
            Individual game misconduct penalties drawn per 60 minutes
        gf_p60 (float):
            Goals for (on-ice) per 60 minutes
        ga_p60 (float):
            Goals against (on-ice) per 60 minutes
        hdgf_p60 (float):
            High-danger goals for (on-ice) per 60 minutes
        hdga_p60 (float):
            High-danger goals against (on-ice) per 60 minutes
        xgf_p60 (float):
            xG for (on-ice) per 60 minutes
        xga_p60 (float):
            xG against (on-ice) per 60 minutes
        sf_p60 (float):
            Shots for (on-ice) per 60 minutes
        sa_p60 (float):
            Shots against (on-ice) per 60 minutes
        hdsf_p60 (float):
            High-danger shots for (on-ice) per 60 minutes
        hdsa_p60 (float):
            High danger shots against (on-ice) per 60 minutes
        ff_p60 (float):
            Fenwick for (on-ice) per 60 minutes
        fa_p60 (float):
            Fenwick against (on-ice) per 60 minutes
        hdff_p60 (float):
            High-danger fenwick for (on-ice) per 60 minutes
        hdfa_p60 (float):
            High-danger fenwick against (on-ice) per 60 minutes
        cf_p60 (float):
            Corsi for (on-ice) per 60 minutes
        ca_p60 (float):
            Corsi against (on-ice) per 60 minutes
        bsf_p60 (float):
            Blocked shots for (on-ice) per 60 minutes
        bsa_p60 (float):
            Blocked shots against (on-ice) per 60 minutes
        msf_p60 (float):
            Missed shots for (on-ice) per 60 minutes
        msa_p60 (float):
            Missed shots against (on-ice) per 60 minutes
        hdmsf_p60 (float):
            High-danger missed shots for (on-ice) per 60 minutes
        hdmsa_p60 (float):
            High-danger missed shots against (on-ice) per 60 minutes
        teammate_block_p60 (float):
            Shots blocked by teammates (on-ice) per 60 minutes
        hf_p60 (float):
            Hits  for (on-ice) per 60 minutes
        ht_p60 (float):
            Hits taken (on-ice) per 60 minutes
        give_p60 (float):
            Giveaways (on-ice) per 60 minutes
        take_p60 (float):
            Takeaways (on-ice) per 60 minutes
        pent0_p60 (float):
            Penalty shots taken (on-ice) per 60 minutes
        pent2_p60 (float):
            Minor penalties taken (on-ice) per 60 minutes
        pent4_p60 (float):
            Double minor penalties taken (on-ice) per 60 minutes
        pent5_p60 (float):
            Major penalties taken (on-ice) per 60 minutes
        pent10_p60 (float):
            Game misconduct pentalties taken (on-ice) per 60 minutes
        pend0_p60 (float):
            Penalty shots drawn (on-ice) per 60 minutes
        pend2_p60 (float):
            Minor penalties drawn (on-ice) per 60 minutes
        pend4_p60 (float):
            Double minor penalties drawn (on-ice) per 60 minutes
        pend5_p60 (float):
            Major penalties drawn (on-ice) per 60 minutes
        pend10_p60 (float):
            Game misconduct penalties drawn (on-ice) per 60 minutes

    """
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
    """Adds columns for on-ice percentages (e.g., xGF%).

    Parameters:
        df (pd.DataFrame):
            Statistics data from chickenstats.chicken_nhl.Scraper

    Returns:
        season (int):
            Season as 8-digit number, e.g., 2023 for 2023-24 season
        session (str):
            Whether game is regular season, playoffs, or pre-season, e.g., R
        game_id (int):
            Unique game ID assigned by the NHL, e.g., 2023020001
        game_date (int):
            Date game was played, e.g., 2023-10-10
        player (str):
            Player's name, e.g., FILIP FORSBERG
        eh_id (str):
            Evolving Hockey ID for the player, e.g., FILIP.FORSBERG
        api_id (str):
            NHL API ID for the player, e.g., 8476887
        position (str):
            Player's position, e.g., L
        team (str):
            Player's team, e.g., NSH
        opp_team (str):
            Opposing team, e.g., TBL
        strength_state (str):
            Strength state, e.g., 5v5
        period (int):
            Period, e.g., 3
        score_state (str):
            Score state, e.g., 2v1
        forwards (str):
            Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY
        forwards_eh_id (str):
            Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
        forwards_api_id (str):
            Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158
        defense (str):
            Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER
        defense_eh_id (str):
            Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER
        defense_api_id (str):
            Defense teammates' NHL API IDs, e.g., 8474151, 8478851
        own_goalie (str):
            Own goalie, e.g., JUUSE SAROS
        own_goalie_eh_id (str):
            Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS
        own_goalie_api_id (str):
            Own goalie's NHL API ID, e.g., 8477424
        opp_forwards (str):
            Opposing forwards, e.g, BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS
        opp_forwards_eh_id (str):
            Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS
        opp_forwards_api_id (str):
            Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564
        opp_defense (str):
            Opposing defense, e.g, NICK PERBIX, VICTOR HEDMAN
        opp_defense_eh_id (str):
            Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN
        opp_defense_api_id (str):
            Opposing defense's NHL API IDs, e.g., 8480246, 8475167
        opp_goalie (str):
            Opposing goalie, e.g., JONAS JOHANSSON
        opp_goalie_eh_id (str):
            Opposing goalie's Evolving Hockey ID, e.g, JONAS.JOHANSSON
        opp_goalie_api_id (str):
            Opposing goalie's NHL API ID, e.g., 8477992
        toi (float):
            Time on-ice, in minutes, e.g, 0.483333
        g (int):
            Goals scored, e.g, 0
        ihdg (int):
            High-danger goals scored, e.g, 0
        a1 (int):
            Primary assists, e.g, 0
        a2 (int):
            Secondary assists, e.g, 0
        ixg (float):
            Individual xG for, e.g, 1.014336
        isf (int):
            Individual shots taken, e.g, 3
        ihdsf (int):
            High-danger shots taken, e.g, 3
        imsf (int):
            Individual missed shots, e.g, 0
        ihdm (int):
            High-danger missed shots, e.g, 0
        iff (int):
            Individual fenwick for, e.g., 3
        ihdf (int):
            High-danger fenwick for, e.g., 3
        isb (int):
            Shots taken that were blocked, e.g, 0
        icf (int):
            Individual corsi for, e.g., 3
        ibs (int):
            Individual shots blocked on defense, e.g, 0
        igive (int):
            Individual giveaways, e.g, 0
        itake (int):
            Individual takeaways, e.g, 0
        ihf (int):
            Individual hits for, e.g, 0
        iht (int):
            Individual hits taken, e.g, 0
        ifow (int):
            Individual faceoffs won, e.g, 0
        ifol (int):
            Individual faceoffs lost, e.g, 0
        iozfw (int):
            Individual faceoffs won in offensive zone, e.g, 0
        iozfl (int):
            Individual faceoffs lost in offensive zone, e.g, 0
        inzfw (int):
            Individual faceoffs won in neutral zone, e.g, 0
        inzfl (int):
            Individual faceoffs lost in neutral zone, e.g, 0
        idzfw (int):
            Individual faceoffs won in defensive zone, e.g, 0
        idzfl (int):
            Individual faceoffs lost in defensive zone, e.g, 0
        a1_xg (float):
            xG on primary assists, e.g, 0
        a2_xg (float):
            xG on secondary assists, e.g, 0
        ipent0 (int):
            Individual penalty shots against, e.g, 0
        ipent2 (int):
            Individual minor penalties taken, e.g, 0
        ipent4 (int):
            Individual double minor penalties taken, e.g, 0
        ipent5 (int):
            Individual major penalties taken, e.g, 0
        ipent10 (int):
            Individual game misconduct penalties taken, e.g, 0
        ipend0 (int):
            Individual penalty shots drawn, e.g, 0
        ipend2 (int):
            Individual minor penalties taken, e.g, 0
        ipend4 (int):
            Individual double minor penalties drawn, e.g, 0
        ipend5 (int):
            Individual major penalties drawn, e.g, 0
        ipend10 (int):
            Individual game misconduct penalties drawn, e.g, 0
        gf (int):
            Goals for (on-ice), e.g, 0
        hdgf (int):
            High-danger goals for (on-ice), e.g, 0
        ga (int):
            Goals against (on-ice), e.g, 0
        hdga (int):
            High-danger goals against (on-ice), e.g, 0
        xgf (float):
            xG for (on-ice), e.g., 1.258332
        xga (float):
            xG against (on-ice), e.g, 0.000000
        sf (int):
            Shots for (on-ice), e.g, 4
        sa (int):
            Shots against (on-ice), e.g, 0
        hdsf (int):
            High-danger shots for (on-ice), e.g, 3
        hdsa (int):
            High-danger shots against (on-ice), e.g, 0
        ff (int):
            Fenwick for (on-ice), e.g, 4
        fa (int):
            Fenwick against (on-ice), e.g, 0
        hdff (int):
            High-danger fenwick for (on-ice), e.g, 3
        hdfa (int):
            High-danger fenwick against (on-ice), e.g, 0
        cf (int):
            Corsi for (on-ice), e.g, 4
        ca (int):
            Corsi against (on-ice), e.g, 0
        bsf (int):
            Shots taken that were blocked (on-ice), e.g, 0
        bsa (int):
            Shots blocked (on-ice), e.g, 0
        msf (int):
            Missed shots taken (on-ice), e.g, 0
        msa (int):
            Missed shots against (on-ice), e.g, 0
        hdmsf (int):
            High-danger missed shots taken (on-ice), e.g, 0
        hdmsa (int):
            High-danger missed shots against (on-ice), e.g, 0
        teammate_block (int):
            Shots blocked by teammates (on-ice), e.g, 0
        hf (int):
            Hits for (on-ice), e.g, 0
        ht (int):
            Hits taken (on-ice), e.g, 0
        give (int):
            Giveaways (on-ice), e.g, 0
        take (int):
            Takeaways (on-ice), e.g, 0
        ozf (int):
            Offensive zone faceoffs (on-ice), e.g, 0
        nzf (int):
            Neutral zone faceoffs (on-ice), e.g, 1
        dzf (int):
            Defensive zone faceoffs (on-ice), e.g, 0
        fow (int):
            Faceoffs won (on-ice), e.g, 1
        fol (int):
            Faceoffs lost (on-ice), e.g, 0
        ozfw (int):
            Offensive zone faceoffs won (on-ice), e.g, 0
        ozfl (int):
            Offensive zone faceoffs lost (on-ice), e.g, 0
        nzfw (int):
            Neutral zone faceoffs won (on-ice), e.g, 1
        nzfl (int):
            Neutral zone faceoffs lost (on-ice), e.g, 0
        dzfw (int):
            Defensive zone faceoffs won (on-ice), e.g, 0
        dzfl (int):
            Defensive zone faceoffs lost (on-ice), e.g, 0
        pent0 (int):
            Penalty shots allowed (on-ice), e.g, 0
        pent2 (int):
            Minor penalties taken (on-ice), e.g, 0
        pent4 (int):
            Double minor penalties taken (on-ice), e.g, 0
        pent5 (int):
            Major penalties taken (on-ice), e.g, 0
        pent10 (int):
            Game misconduct penalties taken (on-ice), e.g, 0
        pend0 (int):
            Penalty shots drawn (on-ice), e.g, 0
        pend2 (int):
            Minor penalties drawn (on-ice), e.g, 0
        pend4 (int):
            Double minor penalties drawn (on-ice), e.g, 0
        pend5 (int):
            Major penalties drawn (on-ice), e.g, 0
        pend10 (int):
            Game misconduct penalties drawn (on-ice), e.g, 0
        ozs (int):
            Offensive zone starts, e.g, 0
        nzs (int):
            Neutral zone starts, e.g, 0
        dzs (int):
            Defenzive zone starts, e.g, 0
        otf (int):
            On-the-fly starts, e.g, 0
        gf_percent (float):
            On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
        hdgf_percent (float):
            On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA)
        xgf_percent (float):
            On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
        sf_percent (float):
            On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
        hdsf_percent (float):
            On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA)
        ff_percent (float):
            On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
        hdff_percent (float):
            On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA)
        cf_percent (float):
            On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
        bsf_percent (float):
            On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
        msf_percent (float):
            On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
        hdmsf_percent (float):
            On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA)
        hf_percent (float):
            On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
        take_percent (float):
            On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)
    """
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
