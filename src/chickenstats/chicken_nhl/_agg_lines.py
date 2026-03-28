from typing import Literal

import pandas as pd
import polars as pl
from polars import Int64, String

from chickenstats.chicken_nhl._agg_constants import _build_merge_list
from chickenstats.chicken_nhl._agg_transforms import prep_p60, prep_oi_percent
from chickenstats.chicken_nhl.validation_pandas import line_stats_pandera_pandas


def prep_lines_pandas(
    df: pd.DataFrame,
    df_ext: pd.DataFrame,
    position: Literal["f", "d"] = "f",
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of line-level stats from play-by-play data.

    Nested within `prep_lines` method.

    Parameters:
        df (pd.DataFrame):
            Play-by-play dataframe to aggregate lines stats
        df_ext (pd.DataFrame):
            Extended play-by-play dataframe to aggregate lines stats
        position (str):
            Determines what positions to aggregate. One of F or D
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        strength_state (bool):
            Determines if stats account for strength state
        score (bool):
            Determines if stats account for score state
        teammates (bool):
            Determines if stats account for teammates on ice
        opposition (bool):
            Determines if stats account for opponents on ice

    Returns:
        season (int):
            Season as 8-digit number, e.g., 2023 for 2023-24 season
        session (str):
            Whether game is regular season, playoffs, or pre-season, e.g., R
        game_id (int):
            Unique game ID assigned by the NHL, e.g., 2023020001
        game_date (int):
            Date game was played, e.g., 2023-10-10
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
        gf (int):
            Goals for (on-ice), e.g, 0
        ga (int):
            Goals against (on-ice), e.g, 0
        gf_adj (float):
            Score- and venue-adjusted goals for (on-ice), e.g., 0.0
        ga_adj (float):
            Score- and venue-adjusted goals against (on-ice), e.g., 0.0
        hdgf (int):
            High-danger goals for (on-ice), e.g, 0
        hdga (int):
            High-danger goals against (on-ice), e.g, 0
        xgf (float):
            xG for (on-ice), e.g., 1.258332
        xga (float):
            xG against (on-ice), e.g, 0.000000
        xgf_adj (float):
            Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
        xga_adj (float):
            Score- and venue-adjusted xG against (on-ice), e.g., 0.0
        sf (int):
            Shots for (on-ice), e.g, 4
        sa (int):
            Shots against (on-ice), e.g, 0
        sf_adj (float):
            Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
        sa_adj (float):
            Score- and venue-adjusted shots against (on-ice), e.g., 0.0
        hdsf (int):
            High-danger shots for (on-ice), e.g, 3
        hdsa (int):
            High-danger shots against (on-ice), e.g, 0
        ff (int):
            Fenwick for (on-ice), e.g, 4
        fa (int):
            Fenwick against (on-ice), e.g, 0
        ff_adj (float):
            Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
        fa_adj (float):
            Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
        hdff (int):
            High-danger fenwick for (on-ice), e.g, 3
        hdfa (int):
            High-danger fenwick against (on-ice), e.g, 0
        cf (int):
            Corsi for (on-ice), e.g, 4
        ca (int):
            Corsi against (on-ice), e.g, 0
        cf_adj (float):
            Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
        ca_adj (float):
            Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
        bsf (int):
            Shots taken that were blocked (on-ice), e.g, 0
        bsa (int):
            Shots blocked (on-ice), e.g, 0
        bsf_adj (float):
            Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
        bsa_adj (float):
            Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
        msf (int):
            Missed shots taken (on-ice), e.g, 0
        msa (int):
            Missed shots against (on-ice), e.g, 0
        msf_adj (float):
            Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
        msa_adj (float):
            Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
        hdmsf (int):
            High-danger missed shots taken (on-ice), e.g, 0
        hdmsa (int):
            High-danger missed shots against (on-ice), e.g, 0
        teammate_block (int):
            Shots blocked by teammates (on-ice), e.g, 0
        teammate_block_adj (float):
            Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
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
        gf_percent (float):
            On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
        hdgf_percent (float):
            On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
            (HDGF + HDGA)
        xgf_percent (float):
            On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
        sf_percent (float):
            On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
        hdsf_percent (float):
            On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
            (HDSF + HDSA)
        ff_percent (float):
            On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
        hdff_percent (float):
            On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
            (HDFF + HDFA)
        cf_percent (float):
            On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
        bsf_percent (float):
            On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
        msf_percent (float):
            On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
        hdmsf_percent (float):
            On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
            HDMSF / (HDMSF + HDMSA)
        hf_percent (float):
            On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
        take_percent (float):
            On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

    Examples:
        First, instantiate the class with a game ID
        >>> game_id = 2023020001
        >>> scraper = Scraper(game_id)

        Prepares on-ice, line-level dataframe with default options
        >>> scraper._prep_lines()

        Line-level statistics, aggregated to season level
        >>> scraper._prep_lines(level="season")

        Line-level statistics, aggregated to game level, accounting for teammates
        >>> scraper._prep_lines(level="game", teammates=True)

    """
    merge_cols = ["id", "event_idx"]

    data = df.merge(df_ext, how="left", on=merge_cols)

    # Creating the "for" dataframe

    # Accounting for desired level of aggregation

    group_list = ["season", "session", "event_team"]

    if level == "session" or level == "season":
        group_list = group_list

    elif level == "game":
        group_list.extend(["game_id", "game_date", "opp_team"])

    elif level == "period":
        group_list.extend(["game_id", "game_date", "opp_team", "period"])

    if strength_state:
        group_list.append("strength_state")

    # Accounting for score state

    if score:
        group_list.append("score_state")

    # Accounting for desired position

    if position == "f":
        group_list.extend(["forwards", "forwards_eh_id", "forwards_api_id"])

    if position == "d":
        group_list.extend(["defense", "defense_eh_id", "defense_api_id"])

    # Accounting for teammates

    if teammates:
        if position == "f":
            group_list.extend(
                ["defense", "defense_eh_id", "defense_api_id", "own_goalie", "own_goalie_eh_id", "own_goalie_api_id"]
            )

        if position == "d":
            group_list.extend(
                ["forwards", "forwards_eh_id", "forwards_api_id", "own_goalie", "own_goalie_eh_id", "own_goalie_api_id"]
            )

    # Accounting for opposition

    if opposition:
        group_list.extend(
            [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_forwards_api_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_defense_api_id",
                "opp_goalie",
                "opp_goalie_eh_id",
                "opp_goalie_api_id",
            ]
        )

        if "opp_team" not in group_list:
            group_list.append("opp_team")

    group_list_order = [
        "season",
        "session",
        "game_id",
        "game_date",
        "event_team",
        "opp_team",
        "period",
        "strength_state",
        "score_state",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
    ]

    group_list = [x for x in group_list_order if x in group_list]

    # Creating dictionary of statistics for the groupby function

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
        "shot",
        "shot_adj",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "event_length",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "hit",
        "give",
        "take",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
    ]

    agg_stats = {x: "sum" for x in stats if x in data.columns}

    # Aggregating the "for" dataframe

    lines_f = data.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

    # Creating the dictionary to change column names

    columns = [
        "xgf",
        "xgf_adj",
        "ff",
        "ff_adj",
        "gf",
        "gf_adj",
        "msf",
        "msf_adj",
        "bsf",
        "bsf_adj",
        "teammate_block",
        "teammate_block_adj",
        "sf",
        "sf_adj",
        "hdgf",
        "hdsf",
        "hdff",
        "hdmsf",
        "toi",
        "fow",
        "ozfw",
        "nzfw",
        "dzfw",
        "hf",
        "give",
        "take",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
    ]

    columns = dict(zip(stats, columns, strict=False))

    # Accounting for positions

    columns.update({"event_team": "team"})

    # columns = {k: v for k, v in columns.items() if k in lines_f.columns}

    lines_f = lines_f.rename(columns=columns)

    cols = [
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    cols = {x: "" for x in cols if x in lines_f}

    lines_f.fillna(cols, inplace=True)

    # Creating the against dataframe

    # Accounting for desired level of aggregation

    group_list = ["season", "session", "opp_team"]

    if level == "session" or level == "season":
        group_list = group_list

    elif level == "game":
        group_list.extend(["game_id", "game_date", "event_team"])

    elif level == "period":
        group_list.extend(["game_id", "game_date", "event_team", "period"])

    if strength_state:
        group_list.append("opp_strength_state")

    # Accounting for score state

    if score:
        group_list.append("opp_score_state")

    # Accounting for desired position

    if position == "f":
        group_list.extend(["opp_forwards", "opp_forwards_eh_id", "opp_forwards_api_id"])

    if position == "d":
        group_list.extend(["opp_defense", "opp_defense_eh_id", "opp_defense_api_id"])

    # Accounting for teammates

    if teammates:
        if position == "f":
            group_list.extend(
                [
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_defense_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]
            )

        if position == "d":
            group_list.extend(
                [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_forwards_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]
            )

    # Accounting for opposition

    if opposition:
        group_list.extend(
            [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]
        )

        if "event_team" not in group_list:
            group_list.append("event_team")

    group_list_order = [
        "season",
        "session",
        "game_id",
        "game_date",
        "event_team",
        "opp_team",
        "strength_state",
        "period",
        "opp_strength_state",
        "opp_score_state",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
    ]

    group_list = [x for x in group_list_order if x in group_list]

    # Creating dictionary of statistics for the groupby function

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "shot",
        "shot_adj",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "event_length",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "hit",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
    ]

    agg_stats = {x: "sum" for x in stats if x in data.columns}

    # Aggregating "against" dataframe

    lines_a = data.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

    # Creating the dictionary to change column names

    columns = [
        "xga",
        "xga_adj",
        "fa",
        "fa_adj",
        "ga",
        "ga_adj",
        "msa",
        "msa_adj",
        "bsa",
        "bsa_adj",
        "sa",
        "sa_adj",
        "hdga",
        "hdsa",
        "hdfa",
        "hdmsa",
        "toi",
        "fol",
        "ozfl",
        "nzfl",
        "dzfl",
        "ht",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
    ]

    columns = dict(zip(stats, columns, strict=False))

    # Accounting for positions

    columns.update(
        {
            "opp_team": "team",
            "event_team": "opp_team",
            "opp_forwards": "forwards",
            "opp_forwards_eh_id": "forwards_eh_id",
            "opp_forwards_api_id": "forwards_api_id",
            "opp_strength_state": "strength_state",
            "opp_defense": "defense",
            "opp_defense_eh_id": "defense_eh_id",
            "opp_defense_api_id": "defense_api_id",
            "forwards": "opp_forwards",
            "forwards_eh_id": "opp_forwards_eh_id",
            "forwards_api_id": "opp_forwards_api_id",
            "defense": "opp_defense",
            "defense_eh_id": "opp_defense_eh_id",
            "defense_api_id": "opp_defense_api_id",
            "opp_score_state": "score_state",
            "own_goalie": "opp_goalie",
            "own_goalie_eh_id": "opp_goalie_eh_id",
            "own_goalie_api_id": "opp_goalie_api_id",
            "opp_goalie": "own_goalie",
            "opp_goalie_eh_id": "own_goalie_eh_id",
            "opp_goalie_api_id": "own_goalie_api_id",
        }
    )

    # columns = {k: v for k, v in columns.items() if k in lines_a.columns}

    lines_a = lines_a.rename(columns=columns)

    cols = [
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    cols = {x: "" for x in cols if x in lines_a}

    lines_a.fillna(cols, inplace=True)

    # Merging the "for" and "against" dataframes

    if level == "session" or level == "season":
        if position == "f":
            merge_list = ["season", "session", "team", "forwards", "forwards_eh_id", "forwards_api_id"]

        if position == "d":
            merge_list = ["season", "session", "team", "defense", "defense_eh_id", "defense_api_id"]

    if level == "game":
        if position == "f":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
            ]

        if position == "d":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "defense",
                "defense_eh_id",
                "defense_api_id",
            ]

    if level == "period":
        if position == "f":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "period",
            ]

        if position == "d":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "period",
            ]

    if strength_state:
        merge_list.append("strength_state")

    if score:
        merge_list.append("score_state")

    if teammates:
        if position == "f":
            merge_list = merge_list + [
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

        if position == "d":
            merge_list = merge_list + [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

    if opposition:
        merge_list = merge_list + [
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]

        if "opp_team" not in merge_list:
            merge_list.insert(3, "opp_team")

    lines = lines_f.merge(lines_a, how="outer", on=merge_list, suffixes=("_x", "_y"))

    null_columns = {x: 0 for x in lines.columns if x not in merge_list}

    lines.fillna(null_columns, inplace=True)

    lines["toi"] = (lines.toi_x + lines.toi_y) / 60

    lines["cf"] = lines.bsf + lines.teammate_block + lines.ff
    lines["cf_adj"] = lines.bsf_adj + lines.teammate_block_adj + lines.ff_adj

    lines["ca"] = lines.bsa + lines.fa
    lines["ca_adj"] = lines.bsa_adj + lines.fa_adj

    lines["ozf"] = lines.ozfw + lines.ozfl

    lines["nzf"] = lines.nzfw + lines.nzfl

    lines["dzf"] = lines.dzfw + lines.dzfl

    cols = [x for x in list(line_stats_pandera_pandas.dtypes.keys()) if x in lines.columns]

    lines = lines[cols].loc[lines.toi > 0].reset_index(drop=True)

    lines = prep_p60(lines)

    lines = prep_oi_percent(lines)

    lines = line_stats_pandera_pandas.validate(lines)

    return lines


def prep_lines_polars(
    df: pl.DataFrame,
    df_ext: pl.DataFrame,
    position: Literal["f", "d"] = "f",
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of line-level stats from play-by-play data.

    Nested within `prep_lines` method.

    Parameters:
        df (pl.DataFrame):
            Play-by-play dataframe to aggregate lines stats
        df_ext (pl.DataFrame):
            Extended play-by-play dataframe to aggregate lines stats
        position (str):
            Determines what positions to aggregate. One of F or D
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        strength_state (bool):
            Determines if stats account for strength state
        score (bool):
            Determines if stats account for score state
        teammates (bool):
            Determines if stats account for teammates on ice
        opposition (bool):
            Determines if stats account for opponents on ice

    Returns:
        season (int):
            Season as 8-digit number, e.g., 2023 for 2023-24 season
        session (str):
            Whether game is regular season, playoffs, or pre-season, e.g., R
        game_id (int):
            Unique game ID assigned by the NHL, e.g., 2023020001
        game_date (int):
            Date game was played, e.g., 2023-10-10
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
        gf (int):
            Goals for (on-ice), e.g, 0
        ga (int):
            Goals against (on-ice), e.g, 0
        gf_adj (float):
            Score- and venue-adjusted goals for (on-ice), e.g., 0.0
        ga_adj (float):
            Score- and venue-adjusted goals against (on-ice), e.g., 0.0
        hdgf (int):
            High-danger goals for (on-ice), e.g, 0
        hdga (int):
            High-danger goals against (on-ice), e.g, 0
        xgf (float):
            xG for (on-ice), e.g., 1.258332
        xga (float):
            xG against (on-ice), e.g, 0.000000
        xgf_adj (float):
            Score- and venue-adjusted xG for (on-ice), e.g., 1.366730
        xga_adj (float):
            Score- and venue-adjusted xG against (on-ice), e.g., 0.0
        sf (int):
            Shots for (on-ice), e.g, 4
        sa (int):
            Shots against (on-ice), e.g, 0
        sf_adj (float):
            Score- and venue-adjusted shots for (on-ice), e.g., 4.350622
        sa_adj (float):
            Score- and venue-adjusted shots against (on-ice), e.g., 0.0
        hdsf (int):
            High-danger shots for (on-ice), e.g, 3
        hdsa (int):
            High-danger shots against (on-ice), e.g, 0
        ff (int):
            Fenwick for (on-ice), e.g, 4
        fa (int):
            Fenwick against (on-ice), e.g, 0
        ff_adj (float):
            Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024
        fa_adj (float):
            Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
        hdff (int):
            High-danger fenwick for (on-ice), e.g, 3
        hdfa (int):
            High-danger fenwick against (on-ice), e.g, 0
        cf (int):
            Corsi for (on-ice), e.g, 4
        ca (int):
            Corsi against (on-ice), e.g, 0
        cf_adj (float):
            Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024
        ca_adj (float):
            Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0
        bsf (int):
            Shots taken that were blocked (on-ice), e.g, 0
        bsa (int):
            Shots blocked (on-ice), e.g, 0
        bsf_adj (float):
            Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0
        bsa_adj (float):
            Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0
        msf (int):
            Missed shots taken (on-ice), e.g, 0
        msa (int):
            Missed shots against (on-ice), e.g, 0
        msf_adj (float):
            Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0
        msa_adj (float):
            Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0
        hdmsf (int):
            High-danger missed shots taken (on-ice), e.g, 0
        hdmsa (int):
            High-danger missed shots against (on-ice), e.g, 0
        teammate_block (int):
            Shots blocked by teammates (on-ice), e.g, 0
        teammate_block_adj (float):
            Score- and venue-adjusted shots blocked by teammates (on-ice), e.g., 0.0
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
        gf_percent (float):
            On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA)
        hdgf_percent (float):
            On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF /
            (HDGF + HDGA)
        xgf_percent (float):
            On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + GxA)
        sf_percent (float):
            On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA)
        hdsf_percent (float):
            On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF /
            (HDSF + HDSA)
        ff_percent (float):
            On-ice fenwick for as a percentage of total on-ice fenick i.e., FF / (FF + FA)
        hdff_percent (float):
            On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF /
            (HDFF + HDFA)
        cf_percent (float):
            On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA)
        bsf_percent (float):
            On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA)
        msf_percent (float):
            On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA)
        hdmsf_percent (float):
            On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e.,
            HDMSF / (HDMSF + HDMSA)
        hf_percent (float):
            On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT)
        take_percent (float):
            On-ice takeaways for as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give)

    Examples:
        First, instantiate the class with a game ID
        >>> game_id = 2023020001
        >>> scraper = Scraper(game_id)

        Prepares on-ice, line-level dataframe with default options
        >>> scraper._prep_lines()

        Line-level statistics, aggregated to season level
        >>> scraper._prep_lines(level="season")

        Line-level statistics, aggregated to game level, accounting for teammates
        >>> scraper._prep_lines(level="game", teammates=True)

    """
    merge_cols = ["id", "event_idx"]

    data = df.join(df_ext, how="left", on=merge_cols, nulls_equal=True)

    # Creating the "for" dataframe

    # Accounting for desired level of aggregation

    group_list = ["season", "session", "event_team"]

    if level == "session" or level == "season":
        group_list = group_list

    elif level == "game":
        group_list.extend(["game_id", "game_date", "opp_team"])

    elif level == "period":
        group_list.extend(["game_id", "game_date", "opp_team", "period"])

    if strength_state:
        group_list.append("strength_state")

    # Accounting for score state

    if score:
        group_list.append("score_state")

    # Accounting for desired position

    if position == "f":
        group_list.extend(["forwards", "forwards_eh_id", "forwards_api_id"])

    if position == "d":
        group_list.extend(["defense", "defense_eh_id", "defense_api_id"])

    # Accounting for teammates

    if teammates:
        if position == "f":
            group_list.extend(
                ["defense", "defense_eh_id", "defense_api_id", "own_goalie", "own_goalie_eh_id", "own_goalie_api_id"]
            )

        if position == "d":
            group_list.extend(
                ["forwards", "forwards_eh_id", "forwards_api_id", "own_goalie", "own_goalie_eh_id", "own_goalie_api_id"]
            )

    # Accounting for opposition

    if opposition:
        group_list.extend(
            [
                "opp_forwards",
                "opp_forwards_eh_id",
                "opp_forwards_api_id",
                "opp_defense",
                "opp_defense_eh_id",
                "opp_defense_api_id",
                "opp_goalie",
                "opp_goalie_eh_id",
                "opp_goalie_api_id",
            ]
        )

        if "opp_team" not in group_list:
            group_list.append("opp_team")

    group_list_order = [
        "season",
        "session",
        "game_id",
        "game_date",
        "event_team",
        "opp_team",
        "period",
        "strength_state",
        "score_state",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
    ]

    group_list = [x for x in group_list_order if x in group_list]

    # Creating dictionary of statistics for the groupby function

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
        "shot",
        "shot_adj",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "event_length",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "hit",
        "give",
        "take",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
    ]

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    # Aggregating the "for" dataframe

    lines_f = data.group_by(group_list).agg(agg_stats)

    # Creating the dictionary to change column names

    columns = [
        "xgf",
        "xgf_adj",
        "ff",
        "ff_adj",
        "gf",
        "gf_adj",
        "msf",
        "msf_adj",
        "bsf",
        "bsf_adj",
        "teammate_block",
        "teammate_block_adj",
        "sf",
        "sf_adj",
        "hdgf",
        "hdsf",
        "hdff",
        "hdmsf",
        "toi",
        "fow",
        "ozfw",
        "nzfw",
        "dzfw",
        "hf",
        "give",
        "take",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
    ]

    columns = dict(zip(stats, columns, strict=False))

    # Accounting for positions

    columns.update({"event_team": "team"})

    columns = {k: v for k, v in columns.items() if k in lines_f.columns}

    lines_f = lines_f.rename(columns)

    cols = [
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    cols = [pl.col(x).fill_null("") for x in cols if x in lines_f]

    lines_f = lines_f.with_columns(cols)

    # Creating the against dataframe

    # Accounting for desired level of aggregation

    group_list = ["season", "session", "opp_team"]

    if level == "session" or level == "season":
        group_list = group_list

    elif level == "game":
        group_list.extend(["game_id", "game_date", "event_team"])

    elif level == "period":
        group_list.extend(["game_id", "game_date", "event_team", "period"])

    if strength_state:
        group_list.append("opp_strength_state")

    # Accounting for score state

    if score:
        group_list.append("opp_score_state")

    # Accounting for desired position

    if position == "f":
        group_list.extend(["opp_forwards", "opp_forwards_eh_id", "opp_forwards_api_id"])

    if position == "d":
        group_list.extend(["opp_defense", "opp_defense_eh_id", "opp_defense_api_id"])

    # Accounting for teammates

    if teammates:
        if position == "f":
            group_list.extend(
                [
                    "opp_defense",
                    "opp_defense_eh_id",
                    "opp_defense_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]
            )

        if position == "d":
            group_list.extend(
                [
                    "opp_forwards",
                    "opp_forwards_eh_id",
                    "opp_forwards_api_id",
                    "opp_goalie",
                    "opp_goalie_eh_id",
                    "opp_goalie_api_id",
                ]
            )

    # Accounting for opposition

    if opposition:
        group_list.extend(
            [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]
        )

        if "event_team" not in group_list:
            group_list.append("event_team")

    group_list_order = [
        "season",
        "session",
        "game_id",
        "game_date",
        "event_team",
        "opp_team",
        "strength_state",
        "period",
        "opp_strength_state",
        "opp_score_state",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
    ]

    group_list = [x for x in group_list_order if x in group_list]

    # Creating dictionary of statistics for the groupby function

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "shot",
        "shot_adj",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "event_length",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "hit",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
    ]

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    # Aggregating "against" dataframe

    lines_a = data.group_by(group_list).agg(agg_stats)

    # Creating the dictionary to change column names

    columns = [
        "xga",
        "xga_adj",
        "fa",
        "fa_adj",
        "ga",
        "ga_adj",
        "msa",
        "msa_adj",
        "bsa",
        "bsa_adj",
        "sa",
        "sa_adj",
        "hdga",
        "hdsa",
        "hdfa",
        "hdmsa",
        "toi",
        "fol",
        "ozfl",
        "nzfl",
        "dzfl",
        "ht",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
    ]

    columns = dict(zip(stats, columns, strict=False))

    # Accounting for positions

    columns.update(
        {
            "opp_team": "team",
            "event_team": "opp_team",
            "opp_forwards": "forwards",
            "opp_forwards_eh_id": "forwards_eh_id",
            "opp_forwards_api_id": "forwards_api_id",
            "opp_strength_state": "strength_state",
            "opp_defense": "defense",
            "opp_defense_eh_id": "defense_eh_id",
            "opp_defense_api_id": "defense_api_id",
            "forwards": "opp_forwards",
            "forwards_eh_id": "opp_forwards_eh_id",
            "forwards_api_id": "opp_forwards_api_id",
            "defense": "opp_defense",
            "defense_eh_id": "opp_defense_eh_id",
            "defense_api_id": "opp_defense_api_id",
            "opp_score_state": "score_state",
            "own_goalie": "opp_goalie",
            "own_goalie_eh_id": "opp_goalie_eh_id",
            "own_goalie_api_id": "opp_goalie_api_id",
            "opp_goalie": "own_goalie",
            "opp_goalie_eh_id": "own_goalie_eh_id",
            "opp_goalie_api_id": "own_goalie_api_id",
        }
    )

    columns = {k: v for k, v in columns.items() if k in lines_a.columns}

    lines_a = lines_a.rename(columns)

    cols = [
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
        "opp_goalie",
        "opp_goalie_eh_id",
    ]

    cols = [pl.col(x).fill_null("") for x in cols if x in lines_a]

    lines_a = lines_a.with_columns(cols)

    # Merging the "for" and "against" dataframes

    if level == "session" or level == "season":
        if position == "f":
            merge_list = ["season", "session", "team", "forwards", "forwards_eh_id", "forwards_api_id"]

        if position == "d":
            merge_list = ["season", "session", "team", "defense", "defense_eh_id", "defense_api_id"]

    if level == "game":
        if position == "f":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
            ]

        if position == "d":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "defense",
                "defense_eh_id",
                "defense_api_id",
            ]

    if level == "period":
        if position == "f":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "period",
            ]

        if position == "d":
            merge_list = [
                "season",
                "game_id",
                "game_date",
                "session",
                "team",
                "opp_team",
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "period",
            ]

    if strength_state:
        merge_list.append("strength_state")

    if score:
        merge_list.append("score_state")

    if teammates:
        if position == "f":
            merge_list = merge_list + [
                "defense",
                "defense_eh_id",
                "defense_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

        if position == "d":
            merge_list = merge_list + [
                "forwards",
                "forwards_eh_id",
                "forwards_api_id",
                "own_goalie",
                "own_goalie_eh_id",
                "own_goalie_api_id",
            ]

    if opposition:
        merge_list = merge_list + [
            "opp_forwards",
            "opp_forwards_eh_id",
            "opp_forwards_api_id",
            "opp_defense",
            "opp_defense_eh_id",
            "opp_defense_api_id",
            "opp_goalie",
            "opp_goalie_eh_id",
            "opp_goalie_api_id",
        ]

        if "opp_team" not in merge_list:
            merge_list.insert(3, "opp_team")

    lines = lines_f.join(lines_a, how="full", on=merge_list, coalesce=True, nulls_equal=True)

    null_columns = (pl.col(x).fill_null(0) for x in lines.columns if x not in merge_list)

    lines = lines.with_columns(null_columns)

    lines = lines.with_columns(
        toi=(lines["toi"] + lines["toi_right"]) / 60,
        cf=lines["bsf"] + lines["teammate_block"] + lines["ff"],
        cf_adj=lines["bsf_adj"] + lines["teammate_block_adj"] + lines["ff_adj"],
        ca=lines["bsa"] + lines["fa"],
        ca_adj=lines["bsa_adj"] + lines["fa_adj"],
        ozf=lines["ozfw"] + lines["ozfl"],
        nzf=lines["nzfw"] + lines["nzfl"],
        dzf=lines["dzfw"] + lines["dzfl"],
    )

    cols = [x for x in list(line_stats_pandera_pandas.dtypes.keys()) if x in lines.columns]

    lines = lines.select(cols).filter(pl.col("toi") > 0)

    lines = prep_p60(lines)

    lines = prep_oi_percent(lines)

    return lines
