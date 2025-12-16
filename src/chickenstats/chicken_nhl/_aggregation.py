from typing import Literal

import numpy as np
import pandas as pd
import polars as pl
from polars import Int64, String, Float64, List, Datetime, Struct

from chickenstats.chicken_nhl._validation import IndStatSchema


def prep_ind_pandas(
    df: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of individual stats from play-by-play data.

    Parameters:
        df (pd.DataFrame):
            Play-by-play data to aggregate for individual statistics
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
        g (int):
            Individual goals scored, e.g, 0
        g_adj (float):
            Score- and venue-adjusted individual goals scored, e.g., 0.0
        ihdg (int):
            Individual high-danger goals scored, e.g, 0
        a1 (int):
            Individual primary assists, e.g, 0
        a2 (int):
            Individual secondary assists, e.g, 0
        ixg (float):
            Individual xG for, e.g, 1.014336
        ixg_adj (float):
            Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
        isf (int):
            Individual shots taken, e.g, 3
        isf_adj (float):
            Score- and venue-adjusted individual shots taken, e.g., 3.262966
        ihdsf (int):
            High-danger shots taken, e.g, 3
        imsf (int):
            Individual missed shots, e.g, 0
        imsf_adj (float):
            Score- and venue-adjusted individual missed shots, e.g., 0.0
        ihdm (int):
            High-danger missed shots, e.g, 0
        iff (int):
            Individual fenwick for, e.g., 3
        iff_adj (float):
            Score- and venue-adjusted individual fenwick events, e.g., 3.279018
        ihdf (int):
            High-danger fenwick events for, e.g., 3
        isb (int):
            Shots taken that were blocked, e.g, 0
        isb_adj (float):
            Score- and venue-adjusted individual shots blocked, e.g, 0.0
        icf (int):
            Individual corsi for, e.g., 3
        icf_adj (float):
            Score- and venue-adjusted individual corsi events, e.g, 3.279018
        ibs (int):
            Individual shots blocked on defense, e.g, 0
        ibs_adj (float):
            Score- and venue-adjusted shots blocked, e.g., 0.0
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

    Examples:
        Converts a play-by-play dataframe to aggregated individual statistics
        >>> ind_stats = prep_ind_pandas(play_by_play)

        Aggregates individual stats to game level
        >>> ind_stats = prep_ind_polars(play_by_play, level="game")

        Aggregates individual stats to season level
        >>> ind_stats = prep_ind_polars(play_by_play, level="season")

        Aggregates individual stats to game level, accounting for teammates on-ice
        >>> ind_stats = prep_ind_polars(play_by_play, level="game", teammates=True)

    """
    df = df.copy()

    players = ["player_1", "player_2", "player_3"]

    merge_list = ["season", "session", "player", "eh_id", "api_id", "position", "team"]

    if level == "session" or level == "season":
        merge_list = merge_list

    if level == "game":
        merge_list.extend(["game_id", "game_date", "opp_team"])

    if level == "period":
        merge_list.extend(["game_id", "game_date", "opp_team", "period"])

    if strength_state:
        merge_list.append("strength_state")

    if score:
        merge_list.append("score_state")

    if teammates:
        merge_list.extend(
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

    if opposition:
        merge_list.extend(
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

        if "opp_team" not in merge_list:
            merge_list.append("opp_team")

    ind_stats = pd.DataFrame(columns=merge_list)

    for player in players:
        player_eh_id = f"{player}_eh_id"
        player_api_id = f"{player}_api_id"
        position = f"{player}_position"

        group_base = ["season", "session", "event_team", player, player_eh_id, player_api_id, position]

        if level == "session" or level == "season":
            group_base = group_base

        if level == "game":
            group_base.extend(["game_id", "game_date", "opp_team"])

        if level == "period":
            group_base.extend(["game_id", "game_date", "opp_team", "period"])

        if opposition and "opp_team" not in group_base:
            group_base.append("opp_team")

        mask = df[player] != "BENCH"

        if player == "player_1":
            group_list = group_base.copy()

            if strength_state:
                group_list.append("strength_state")

            if teammates:
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

            if score:
                group_list.append("score_state")

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

            stats_list = [
                "block",
                "block_adj",
                "fac",
                "give",
                "goal",
                "goal_adj",
                "hd_fenwick",
                "hd_goal",
                "hd_miss",
                "hd_shot",
                "hit",
                "miss",
                "miss_adj",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "shot",
                "shot_adj",
                "take",
                # "corsi",
                "fenwick",
                "fenwick_adj",
                "pred_goal",
                "pred_goal_adj",
                "ozf",
                "nzf",
                "dzf",
            ]

            stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            new_cols = {
                "block": "ibs",
                "block_adj": "ibs_adj",
                "fac": "ifow",
                "give": "igive",
                "goal": "g",
                "goal_adj": "g_adj",
                "hd_fenwick": "ihdf",
                "hd_goal": "ihdg",
                "hd_miss": "ihdm",
                "hd_shot": "ihdsf",
                "hit": "ihf",
                "miss": "imsf",
                "miss_adj": "imsf_adj",
                "pen0": "ipent0",
                "pen2": "ipent2",
                "pen4": "ipent4",
                "pen5": "ipent5",
                "pen10": "ipent10",
                "shot": "isf",
                "shot_adj": "isf_adj",
                "take": "itake",
                "fenwick": "iff",
                "fenwick_adj": "iff_adj",
                "pred_goal": "ixg",
                "pred_goal_adj": "ixg_adj",
                "ozf": "iozfw",
                "nzf": "inzfw",
                "dzf": "idzfw",
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
            }

            mask = np.logical_and.reduce(
                [df[player] != "BENCH", ~df.description.astype(str).str.contains("BLOCKED BY TEAMMATE", na=False)]
            )

            player_df = df[mask].copy().groupby(group_list, as_index=False).agg(stats_dict).rename(columns=new_cols)

            # drop_list = [x for x in stats if x not in new_cols.keys() and x in player_df.columns]

        if player == "player_2":
            # Getting on-ice stats against for player 2

            opp_group_list = group_base.copy()

            if strength_state:
                opp_group_list.append("opp_strength_state")

            event_group_list = group_base.copy()

            if strength_state:
                event_group_list.append("strength_state")

            if not opposition and level in ["season", "session"]:
                opp_group_list.remove("event_team")
                opp_group_list.append("opp_team")

            if teammates:
                opp_group_list.extend(
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

                event_group_list.extend(
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

            if score:
                opp_group_list.append("opp_score_state")
                event_group_list.append("score_state")

            if opposition:
                opp_group_list.extend(
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

                event_group_list.extend(
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

            stats_1 = ["block", "block_adj", "fac", "hit", "pen0", "pen2", "pen4", "pen5", "pen10", "ozf", "nzf", "dzf"]

            stats_1 = {x: "sum" for x in stats_1 if x.lower() in df.columns}

            new_cols_1 = {
                "opp_goalie": "own_goalie",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
                "own_goalie": "opp_goalie",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
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
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "fac": "ifol",
                "hit": "iht",
                "ozf": "iozfl",
                "nzf": "inzfl",
                "dzf": "idzfl",
                "block": "isb",
                "block_adj": "isb_adj",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_forwards_api_id": "forwards_api_id",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_defense_api_id": "defense_api_id",
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "forwards_api_id": "opp_forwards_api_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "defense_api_id": "opp_defense_api_id",
            }

            event_types = ["BLOCK", "FAC", "HIT", "PENL"]

            mask_1 = np.logical_and.reduce(
                [
                    df[player] != "BENCH",
                    df.event.isin(event_types),
                    ~df.description.astype(str).str.contains("BLOCKED BY TEAMMATE", na=False),
                ]
            )

            opps = df[mask_1].copy().groupby(opp_group_list, as_index=False).agg(stats_1).rename(columns=new_cols_1)

            # Getting primary assists and primary assists xG from player 2

            stats_2 = ["goal", "pred_goal", "teammate_block", "teammate_block_adj"]

            stats_2 = {x: "sum" for x in stats_2 if x in df.columns}

            new_cols_2 = {
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                "goal": "a1",
                "pred_goal": "a1_xg",
                position: "position",
                "teammate_block": "isb",
                "teammate_block_adj": "isb_adj",
            }

            event_types = ["BLOCK", "GOAL"]

            mask_2 = np.logical_and.reduce([df[player] != "BENCH", df.event.isin(event_types)])

            own = df[mask_2].copy().groupby(event_group_list, as_index=False).agg(stats_2).rename(columns=new_cols_2)

            player_df = opps.merge(own, left_on=merge_list, right_on=merge_list, how="outer").fillna(0)

            player_df["isb"] = player_df.isb_x + player_df.isb_y
            player_df["isb_adj"] = player_df.isb_adj_x + player_df.isb_adj_y

        if player == "player_3":
            group_list = group_base.copy()

            if strength_state:
                group_list.append("strength_state")

            if teammates:
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

            if score:
                group_list.append("score_state")

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

            stats_list = ["goal", "pred_goal"]

            stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            player_df = df[mask].groupby(group_list, as_index=False).agg(stats_dict)

            new_cols = {
                "goal": "a2",
                "pred_goal": "a2_xg",
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
            }

            player_df = player_df.rename(columns=new_cols)

        ind_stats = ind_stats.merge(player_df, on=merge_list, how="outer").infer_objects(copy=False).fillna(0)

    # Fixing some stats

    ind_stats["icf"] = ind_stats.iff + ind_stats.isb
    ind_stats["icf_adj"] = ind_stats.iff_adj + ind_stats.isb_adj

    ind_stats["gax"] = ind_stats.g - ind_stats.ixg

    columns = [x for x in list(IndStatSchema.dtypes.keys()) if x in ind_stats.columns]

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

    ind_stats = ind_stats.loc[(ind_stats[stats] > 0).any(axis=1)]

    ind_stats = IndStatSchema.validate(ind_stats)

    return ind_stats


def prep_ind_polars(
    df: pl.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Prepares DataFrame of individual stats from play-by-play data.

    Parameters:
        df (pd.DataFrame):
            Play-by-play data to aggregate for individual statistics
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
        g (int):
            Individual goals scored, e.g, 0
        g_adj (float):
            Score- and venue-adjusted individual goals scored, e.g., 0.0
        ihdg (int):
            Individual high-danger goals scored, e.g, 0
        a1 (int):
            Individual primary assists, e.g, 0
        a2 (int):
            Individual secondary assists, e.g, 0
        ixg (float):
            Individual xG for, e.g, 1.014336
        ixg_adj (float):
            Score- and venue-adjusted indiviudal xG for, e.g., 1.101715
        isf (int):
            Individual shots taken, e.g, 3
        isf_adj (float):
            Score- and venue-adjusted individual shots taken, e.g., 3.262966
        ihdsf (int):
            High-danger shots taken, e.g, 3
        imsf (int):
            Individual missed shots, e.g, 0
        imsf_adj (float):
            Score- and venue-adjusted individual missed shots, e.g., 0.0
        ihdm (int):
            High-danger missed shots, e.g, 0
        iff (int):
            Individual fenwick for, e.g., 3
        iff_adj (float):
            Score- and venue-adjusted individual fenwick events, e.g., 3.279018
        ihdf (int):
            High-danger fenwick events for, e.g., 3
        isb (int):
            Shots taken that were blocked, e.g, 0
        isb_adj (float):
            Score- and venue-adjusted individual shots blocked, e.g, 0.0
        icf (int):
            Individual corsi for, e.g., 3
        icf_adj (float):
            Score- and venue-adjusted individual corsi events, e.g, 3.279018
        ibs (int):
            Individual shots blocked on defense, e.g, 0
        ibs_adj (float):
            Score- and venue-adjusted shots blocked, e.g., 0.0
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

    Examples:
        Converts a play-by-play dataframe to aggregated individual statistics
        >>> ind_stats = prep_ind_polars(play_by_play)

        Aggregates individual stats to game level
        >>> ind_stats = prep_ind_polars(play_by_play, level="game")

        Aggregates individual stats to season level
        >>> ind_stats = prep_ind_polars(play_by_play, level="season")

        Aggregates individual stats to game level, accounting for teammates on-ice
        >>> ind_stats = prep_ind_polars(play_by_play, level="game", teammates=True)
    """
    df = df.clone()

    players = ["player_1", "player_2", "player_3"]

    merge_list = ["season", "session", "player", "eh_id", "api_id", "position", "team"]

    if level == "session" or level == "season":
        merge_list = merge_list

    if level == "game":
        merge_list.extend(["game_id", "game_date", "opp_team"])

    if level == "period":
        merge_list.extend(["game_id", "game_date", "opp_team", "period"])

    if strength_state:
        merge_list.append("strength_state")

    if score:
        merge_list.append("score_state")

    if teammates:
        merge_list.extend(
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

    if opposition:
        merge_list.extend(
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

        if "opp_team" not in merge_list:
            merge_list.append("opp_team")

    polars_schema = {
        "season": Int64,
        "session": String,
        "team": String,
        "player": String,
        "eh_id": String,
        "api_id": Int64,
        "position": String,
        "game_id": Int64,
        "game_date": String,
        "opp_team": String,
        "period": Int64,
        "strength_state": String,
        "forwards": String,
        "forwards_eh_id": String,
        "forwards_api_id": String,
        "defense": String,
        "defense_eh_id": String,
        "defense_api_id": String,
        "own_goalie": String,
        "own_goalie_eh_id": String,
        "own_goalie_api_id": String,
        "score_state": String,
        "opp_forwards": String,
        "opp_forwards_eh_id": String,
        "opp_forwards_api_id": String,
        "opp_defense": String,
        "opp_defense_eh_id": String,
        "opp_defense_api_id": String,
        "opp_goalie": String,
        "opp_goalie_eh_id": String,
        "opp_goalie_api_id": String,
    }

    polars_schema = {column: polars_schema[column] for column in merge_list}

    ind_stats = pl.DataFrame(schema=polars_schema)

    for player in players:
        player_eh_id = f"{player}_eh_id"
        player_api_id = f"{player}_api_id"
        position = f"{player}_position"

        group_base = ["season", "session", "event_team", player, player_eh_id, player_api_id, position]

        if level == "session" or level == "season":
            group_base = group_base

        if level == "game":
            group_base.extend(["game_id", "game_date", "opp_team"])

        if level == "period":
            group_base.extend(["game_id", "game_date", "opp_team", "period"])

        if opposition and "opp_team" not in group_base:
            group_base.append("opp_team")

        # mask = df[player] != "BENCH"

        filter_df = df.filter(pl.col(player) != "BENCH")

        if player == "player_1":
            group_list = group_base.copy()

            if strength_state:
                group_list.append("strength_state")

            if teammates:
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

            if score:
                group_list.append("score_state")

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

            stats_list = [
                "block",
                "block_adj",
                "fac",
                "give",
                "goal",
                "goal_adj",
                "hd_fenwick",
                "hd_goal",
                "hd_miss",
                "hd_shot",
                "hit",
                "miss",
                "miss_adj",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "shot",
                "shot_adj",
                "take",
                # "corsi",
                "fenwick",
                "fenwick_adj",
                "pred_goal",
                "pred_goal_adj",
                "ozf",
                "nzf",
                "dzf",
            ]

            # stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            agg_stats = [pl.sum(x).sum() for x in stats_list if x in df.columns]

            new_cols = {
                "block": "ibs",
                "block_adj": "ibs_adj",
                "fac": "ifow",
                "give": "igive",
                "goal": "g",
                "goal_adj": "g_adj",
                "hd_fenwick": "ihdf",
                "hd_goal": "ihdg",
                "hd_miss": "ihdm",
                "hd_shot": "ihdsf",
                "hit": "ihf",
                "miss": "imsf",
                "miss_adj": "imsf_adj",
                "pen0": "ipent0",
                "pen2": "ipent2",
                "pen4": "ipent4",
                "pen5": "ipent5",
                "pen10": "ipent10",
                "shot": "isf",
                "shot_adj": "isf_adj",
                "take": "itake",
                "fenwick": "iff",
                "fenwick_adj": "iff_adj",
                "pred_goal": "ixg",
                "pred_goal_adj": "ixg_adj",
                "ozf": "iozfw",
                "nzf": "inzfw",
                "dzf": "idzfw",
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
            }

            filter_df = df.filter(pl.col(player) != "BENCH", ~pl.col("description").str.contains("BLOCKED BY TEAMMATE"))

            player_df = filter_df.group_by(group_list).agg(agg_stats)

            rename_cols = {column: new_cols[column] for column in new_cols if column in player_df.columns}

            player_df = player_df.rename(rename_cols)

        if player == "player_2":
            # Getting on-ice stats against for player 2

            opp_group_list = group_base.copy()

            if strength_state:
                opp_group_list.append("opp_strength_state")

            event_group_list = group_base.copy()

            if strength_state:
                event_group_list.append("strength_state")

            if not opposition and level in ["season", "session"]:
                opp_group_list.remove("event_team")
                opp_group_list.append("opp_team")

            if teammates:
                opp_group_list.extend(
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

                event_group_list.extend(
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

            if score:
                opp_group_list.append("opp_score_state")
                event_group_list.append("score_state")

            if opposition:
                opp_group_list.extend(
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

                event_group_list.extend(
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

            stats_1 = ["block", "block_adj", "fac", "hit", "pen0", "pen2", "pen4", "pen5", "pen10", "ozf", "nzf", "dzf"]

            agg_stats_1 = [pl.sum(x) for x in stats_1 if x.lower() in df.columns]

            event_types = ["BLOCK", "FAC", "HIT", "PENL"]

            opps = (
                df.filter(
                    pl.col(player) != "BENCH",
                    ~pl.col("description").str.contains("BLOCKED BY TEAMMATE"),
                    pl.col("event").is_in(event_types),
                )
                .group_by(opp_group_list)
                .agg(agg_stats_1)
            )

            new_cols_1 = {
                "opp_goalie": "own_goalie",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
                "own_goalie": "opp_goalie",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
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
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "fac": "ifol",
                "hit": "iht",
                "ozf": "iozfl",
                "nzf": "inzfl",
                "dzf": "idzfl",
                "block": "isb",
                "block_adj": "isb_adj",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_forwards_api_id": "forwards_api_id",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_defense_api_id": "defense_api_id",
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "forwards_api_id": "opp_forwards_api_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "defense_api_id": "opp_defense_api_id",
            }

            rename_cols = {column: new_cols_1[column] for column in new_cols_1 if column in opps.columns}

            opps = opps.rename(rename_cols)

            # Getting primary assists and primary assists xG from player 2

            stats_2 = ["goal", "pred_goal", "teammate_block", "teammate_block_adj"]

            agg_stats_2 = [pl.sum(x) for x in stats_2 if x in df.columns]

            event_types = ["BLOCK", "GOAL"]

            own = (
                df.filter(pl.col(player) != "BENCH", pl.col("event").is_in(event_types))
                .group_by(event_group_list)
                .agg(agg_stats_2)
            )

            new_cols_2 = {
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                "goal": "a1",
                "pred_goal": "a1_xg",
                position: "position",
                "teammate_block": "isb",
                "teammate_block_adj": "isb_adj",
            }

            rename_cols = {column: new_cols_2[column] for column in new_cols_2 if column in own.columns}

            own = own.rename(rename_cols)

            player_df = opps.join(own, on=merge_list, how="full", coalesce=True).fill_null(0)

        if player == "player_3":
            group_list = group_base.copy()

            if strength_state:
                group_list.append("strength_state")

            if teammates:
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

            if score:
                group_list.append("score_state")

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

            stats_list = ["goal", "pred_goal"]

            agg_stats = [pl.sum(x) for x in stats_list if x in df.columns]

            player_df = df.filter(pl.col(player) != "BENCH").group_by(group_list).agg(agg_stats)

            new_cols = {
                "goal": "a2",
                "pred_goal": "a2_xg",
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
            }

            rename_cols = {column: new_cols[column] for column in new_cols if column in player_df.columns}

            player_df = player_df.rename(rename_cols)

        ind_stats = ind_stats.join(player_df, on=merge_list, how="full", coalesce=True).fill_null(0)

    # Fixing some stats

    ind_stats = ind_stats.with_columns(
        isb=pl.col("isb") + pl.col("isb_right"),
        isb_adj=pl.col("isb_adj") + pl.col("isb_adj_right"),
        icf=pl.col("iff") + pl.col("isb"),
        icf_adj=pl.col("iff_adj") + pl.col("isb_adj"),
        gax=pl.col("g") - pl.col("ixg"),
    )

    columns = [x for x in list(IndStatSchema.dtypes.keys()) if x in ind_stats.columns]

    ind_stats = ind_stats.select(columns)

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

    ind_stats = ind_stats.remove(pl.all_horizontal(pl.col(stats) == 0))

    return ind_stats
