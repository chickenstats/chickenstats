from typing import Literal

import numpy as np
import pandas as pd
import polars as pl
from polars import Int64, String, Float64, List, Datetime, Struct

from chickenstats.chicken_nhl._helpers import prep_p60, prep_oi_percent
from chickenstats.chicken_nhl._validation import (
    IndStatSchema,
    OIStatSchema,
    StatSchema,
    StatSchemaPolars,
    LineSchema,
    TeamStatSchema,
)


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

            player_df = (
                df[mask]
                .copy()
                .groupby(group_list, as_index=False, dropna=False)
                .agg(stats_dict)
                .rename(columns=new_cols)
            )

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

            opps = (
                df[mask_1]
                .copy()
                .groupby(opp_group_list, as_index=False, dropna=False)
                .agg(stats_1)
                .rename(columns=new_cols_1)
            )

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

            own = (
                df[mask_2]
                .copy()
                .groupby(event_group_list, as_index=False, dropna=False)
                .agg(stats_2)
                .rename(columns=new_cols_2)
            )

            player_df = opps.merge(own, left_on=merge_list, right_on=merge_list, how="outer")  # .fillna(0)

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

            player_df = df[mask].groupby(group_list, as_index=False, dropna=False).agg(stats_dict)

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

        ind_stats = ind_stats.merge(player_df, on=merge_list, how="outer").infer_objects(copy=False)

    na_columns = [
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
    ]

    null_columns = {x: "" for x in na_columns} | {x: 0 for x in ind_stats.columns if x not in merge_list}

    ind_stats.fillna(null_columns, inplace=True)

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

    ind_stats.dropna(subset=["player", "eh_id", "api_id"], how="any", inplace=True)

    ind_stats = IndStatSchema.validate(ind_stats)

    return ind_stats


def prep_oi_pandas(
    df: pd.DataFrame,
    df_ext: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of on-ice stats from play-by-play data.

    Nested within `prep_stats` method.

    Parameters:
        df (pd.DataFrame):
            Play-by-play data to aggregate for on-ice statistics
        df_ext (pd.DataFrame):
            Extended play-by-play data to aggregate for on-ice statistics
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

    Examples:
        Converts a play-by-play dataframe to aggregated individual statistics
        >>> oi_stats = prep_oi_polars(play_by_play, play_by_play_ext)

        Aggregates individual stats to game level
        >>> oi_stats = prep_oi_polars(play_by_play, play_by_play_ext, level="game")

        Aggregates individual stats to season level
        >>> oi_stats = prep_oi_polars(play_by_play, play_by_play_ext, level="season")

        Aggregates individual stats to game level, accounting for teammates on-ice
        >>> oi_stats = prep_oi_polars(play_by_play, play_by_play_ext, level="game", teammates=True)

    """
    merge_cols = ["id", "event_idx"]

    df = df.merge(df_ext, how="left", on=merge_cols)

    players = (
        [f"event_on_{x}" for x in range(1, 8)]
        + [f"opp_on_{x}" for x in range(1, 8)]
        + [f"change_on_{x}" for x in range(1, 8)]
    )

    event_list = []
    opp_list = []
    zones_list = []

    for player in players:
        position = f"{player}_pos"
        player_eh_id = f"{player}_eh_id"
        player_api_id = f"{player}_api_id"

        group_list = ["season", "session"]

        if level == "session" or level == "season":
            group_list = group_list

        if level == "game":
            group_list.extend(["game_id", "game_date", "event_team", "opp_team"])

        if level == "period":
            group_list.extend(["game_id", "game_date", "event_team", "opp_team", "period"])

        # Accounting for desired player

        if "event_on" in player or "opp_on" in player:
            stats_list = [
                "block",
                "block_adj",
                "teammate_block",
                "teammate_block_adj",
                "fac",
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
                "fenwick",
                "fenwick_adj",
                "pred_goal",
                "pred_goal_adj",
                "ozf",
                "nzf",
                "dzf",
                "event_length",
            ]

        if "change_on" in player:
            stats_list = ["ozc", "nzc", "dzc", "otf"]

        stats_dict = {x: "sum" for x in stats_list if x in df.columns}

        if "event_on" in player or "change_on" in player:
            if level == "session" or level == "season":
                group_list.append("event_team")

            strength_group = ["strength_state"]

            teammates_group = [
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

            score_group = ["score_state"]

            opposition_group = [
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

            if "opp_team" not in group_list:
                opposition_group.insert(0, "opp_team")

            col_names = {
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "goal": "gf",
                "goal_adj": "gf_adj",
                "hit": "hf",
                "miss": "msf",
                "miss_adj": "msf_adj",
                "block": "bsa",
                "block_adj": "bsa_adj",
                "teammate_block": "bsf",
                "teammate_block_adj": "bsf_adj",
                "pen0": "pent0",
                "pen2": "pent2",
                "pen4": "pent4",
                "pen5": "pent5",
                "pen10": "pent10",
                "fenwick": "ff",
                "fenwick_adj": "ff_adj",
                "pred_goal": "xgf",
                "pred_goal_adj": "xgf_adj",
                "fac": "fow",
                "ozf": "ozfw",
                "dzf": "dzfw",
                "nzf": "nzfw",
                "ozc": "ozs",
                "nzc": "nzs",
                "dzc": "dzs",
                "shot": "sf",
                "shot_adj": "sf_adj",
                "hd_goal": "hdgf",
                "hd_shot": "hdsf",
                "hd_fenwick": "hdff",
                "hd_miss": "hdmsf",
            }

        if "opp_on" in player:
            if level == "session" or level == "season":
                group_list.append("opp_team")

            strength_group = ["opp_strength_state"]

            teammates_group = [
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

            score_group = ["opp_score_state"]

            opposition_group = [
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

            if "event_team" not in group_list:
                opposition_group.insert(0, "event_team")

            col_names = {
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_goalie": "own_goalie",
                "own_goalie": "opp_goalie",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "block": "bsf",
                "block_adj": "bsf_adj",
                "goal": "ga",
                "goal_adj": "ga_adj",
                "hit": "ht",
                "miss": "msa",
                "miss_adj": "msa_adj",
                "pen0": "pend0",
                "pen2": "pend2",
                "pen4": "pend4",
                "pen5": "pend5",
                "pen10": "pend10",
                "shot": "sa",
                "shot_adj": "sa_adj",
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
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "forwards_api_id": "opp_forwards_api_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "defense_api_id": "opp_defense_api_id",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_forwards_api_id": "forwards_api_id",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_defense_api_id": "defense_api_id",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
            }

        group_list = group_list + [player, player_eh_id, player_api_id, position]

        if strength_state:
            group_list = group_list + strength_group

        if teammates:
            group_list = group_list + teammates_group

        if score:
            group_list = group_list + score_group

        if opposition:
            group_list = group_list + opposition_group

        player_df = df.groupby(group_list, dropna=False, as_index=False).agg(stats_dict)

        col_names = {key: value for key, value in col_names.items() if key in player_df.columns}

        player_df = player_df.rename(columns=col_names)

        if "event_on" in player:
            event_list.append(player_df)

        elif "opp_on" in player:
            opp_list.append(player_df)

        elif "change_on" in player:
            zones_list.append(player_df)

    # On-ice stats

    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "player",
        "eh_id",
        "api_id",
        "position",
        "period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
    ]

    event_stats = pd.concat(event_list, ignore_index=True)

    stats_dict = {x: "sum" for x in event_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in event_stats.columns]

    event_stats = event_stats.groupby(group_list, dropna=False, as_index=False).agg(stats_dict)

    opp_stats = pd.concat(opp_list, ignore_index=True)

    stats_dict = {x: "sum" for x in opp_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in opp_stats.columns]

    opp_stats = opp_stats.groupby(group_list, dropna=False, as_index=False).agg(stats_dict)

    zones_stats = pd.concat(zones_list, ignore_index=True)

    stats_dict = {x: "sum" for x in zones_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in zones_stats.columns]

    zones_stats = zones_stats.groupby(group_list, dropna=False, as_index=False).agg(stats_dict)

    merge_cols = [
        x for x in merge_cols if x in event_stats.columns and x in opp_stats.columns and x in zones_stats.columns
    ]

    oi_stats = event_stats.merge(opp_stats, on=merge_cols, how="outer")  # .fillna(0)

    oi_stats = oi_stats.merge(zones_stats, on=merge_cols, how="outer")  # .fillna(0)

    na_columns = [
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
    ]

    na_columns = {x: "" for x in na_columns}

    na_values = {x: 0 for x in oi_stats.columns if x not in merge_cols} | na_columns

    oi_stats = oi_stats.fillna(na_values)

    oi_stats["toi"] = (oi_stats.event_length_x + oi_stats.event_length_y) / 60

    oi_stats["bsf"] = oi_stats.bsf_x + oi_stats.bsf_y
    oi_stats["bsf_adj"] = oi_stats.bsf_adj_x + oi_stats.bsf_adj_y

    oi_stats["cf"] = oi_stats.ff + oi_stats.bsf
    oi_stats["cf_adj"] = oi_stats.ff_adj + oi_stats.bsf_adj

    oi_stats["ca"] = oi_stats.fa + oi_stats.bsa + oi_stats.teammate_block
    oi_stats["ca_adj"] = oi_stats.fa_adj + oi_stats.bsa_adj + oi_stats.teammate_block_adj

    fo_list = ["ozf", "dzf", "nzf"]

    for fo in fo_list:
        oi_stats[fo] = oi_stats[f"{fo}w"] + oi_stats[f"{fo}l"]

    oi_stats["fac"] = oi_stats.ozf + oi_stats.nzf + oi_stats.dzf

    columns = [x for x in list(OIStatSchema.dtypes.keys()) if x in oi_stats.columns]

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

    oi_stats.dropna(subset=["player", "eh_id", "api_id"], how="any", inplace=True)

    oi_stats = OIStatSchema.validate(oi_stats)

    return oi_stats


def prep_stats_pandas(ind_stats_df: pd.DataFrame, oi_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Prepares DataFrame of individual and on-ice stats from play-by-play data.

    Nested within `prep_stats` method.

    Parameters:
        ind_stats_df (pd.DataFrame):
            Dataframe of individual statistics to aggregate
        oi_stats_df (pd.DataFrame):
            Dataframe of on-ice statistics to aggregate
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
        toi (float):
            Time on-ice, in minutes, e.g, 0.483333
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

        Prepares individual and on-ice dataframe with default options
        >>> scraper._prep_stats()

        Individual and on-ice statistics, aggregated to season level
        >>> scraper._prep_stats(level="season")

        Individual and on-ice statistics, aggregated to game level, accounting for teammates
        >>> scraper._prep_stats(level="game", teammates=True)

    """
    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "eh_id",
        "api_id",
        "position",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "period",
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

    merge_cols = [x for x in merge_cols if x in ind_stats_df.columns and x in oi_stats_df.columns]

    stats = oi_stats_df.merge(ind_stats_df, how="left", left_on=merge_cols, right_on=merge_cols)

    na_columns = {x: 0 for x in stats.columns if x not in merge_cols}

    stats.fillna(na_columns, inplace=True)

    stats = stats.loc[stats.toi > 0].reset_index(drop=True).copy()

    columns = [x for x in list(StatSchema.dtypes.keys()) if x in stats.columns]

    stats = stats[columns]

    stats = StatSchema.validate(stats)

    return stats


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

    cols = [x for x in list(LineSchema.dtypes.keys()) if x in lines.columns]

    lines = lines[cols].loc[lines.toi > 0].reset_index(drop=True)

    lines = prep_p60(lines)

    lines = prep_oi_percent(lines)

    lines = LineSchema.validate(lines)

    return lines


def prep_team_stats_pandas(
    df: pd.DataFrame,
    df_ext: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    opposition: bool = False,
    score: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of team stats from play-by-play data.

    Nested within `prep_team_stats` method.

    Parameters:
        df (pd.DataFrame):
            Play-by-play data to aggregate for team statistics
        df_ext (pd.DataFrame):
            Extended play-by-play data to aggregate for team statistics
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        strength_state (bool):
            Determines if stats account for strength state
        opposition (bool):
            Determines if stats account for opponents on ice
        score (bool):
            Determines if stats account for score state

    Returns:
        season (int):
            Season as 8-digit number, e.g., 2023 for 2023-24 season
        session (str):
            Whether game is regular season, playoffs, or pre-season, e.g., R
        game_id (int):
            Unique game ID assigned by the NHL, e.g., 2023020001
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
        toi (float):
            Time on-ice, in minutes, e.g, 1.100000
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
            xG for (on-ice), e.g., 1.271583
        xga (float):
            xG against (on-ice), e.g, 0.000000
        xgf_adj (float):
            Score- and venue-adjusted xG for (on-ice), e.g., 1.381123
        xga_adj (float):
            Score- and venue-adjusted xG against (on-ice), e.g., 0.0
        sf (int):
            Shots for (on-ice), e.g, 5
        sa (int):
            Shots against (on-ice), e.g, 0
        sf_adj (float):
            Score- and venue-adjusted shots for (on-ice), e.g., 5.438277
        sa_adj (float):
            Score- and venue-adjusted shots against (on-ice), e.g., 0.0
        hdsf (int):
            High-danger shots for (on-ice), e.g, 3
        hdsa (int):
            High-danger shots against (on-ice), e.g, 0
        ff (int):
            Fenwick for (on-ice), e.g, 5
        fa (int):
            Fenwick against (on-ice), e.g, 0
        ff_adj (float):
            Score- and venue-adjusted fenwick events for (on-ice), e.g., 5.46503
        fa_adj (float):
            Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
        hdff (int):
            High-danger fenwick for (on-ice), e.g, 3
        hdfa (int):
            High-danger fenwick against (on-ice), e.g, 0
        cf (int):
            Corsi for (on-ice), e.g, 5
        ca (int):
            Corsi against (on-ice), e.g, 0
        cf_adj (float):
            Score- and venue-adjusted corsi events for (on-ice), e.g., 5.46503
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
            Neutral zone faceoffs (on-ice), e.g, 4
        dzf (int):
            Defensive zone faceoffs (on-ice), e.g, 0
        fow (int):
            Faceoffs won (on-ice), e.g, 2
        fol (int):
            Faceoffs lost (on-ice), e.g, 0
        ozfw (int):
            Offensive zone faceoffs won (on-ice), e.g, 0
        ozfl (int):
            Offensive zone faceoffs lost (on-ice), e.g, 0
        nzfw (int):
            Neutral zone faceoffs won (on-ice), e.g, 2
        nzfl (int):
            Neutral zone faceoffs lost (on-ice), e.g, 1
        dzfw (int):
            Defensive zone faceoffs won (on-ice), e.g, 0
        dzfl (int):
            Defensive zone faceoffs lost (on-ice), e.g, 1
        pent0 (int):
            Penalty shots allowed (on-ice), e.g, 0
        pent2 (int):
            Minor penalties taken (on-ice), e.g, 1
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

        Team dataframe with default options
        >>> scraper._prep_team_stats()

        Team statistics, aggregated to season level
        >>> scraper._prep_team_stats(level="season")

        Team statistics, aggregated to game level, accounting for teammates
        >>> scraper._prep_team_stats(level="game", teammates=True)

    """
    merge_cols = ["id", "event_idx"]

    data = df.merge(df_ext, how="left", on=merge_cols)

    # Getting the "for" stats

    group_list = ["season", "session", "event_team"]

    if strength_state:
        group_list.append("strength_state")

    if level == "game" or level == "period" or opposition:
        group_list.insert(3, "opp_team")

        group_list[2:2] = ["game_id", "game_date"]

    if level == "period":
        group_list.append("period")

    if score:
        group_list.append("score_state")

    agg_stats = [
        "pred_goal",
        "pred_goal_adj",
        "shot",
        "shot_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "give",
        "take",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "hit",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "event_length",
    ]

    agg_dict = {x: "sum" for x in agg_stats if x in data.columns}

    new_cols = [
        "xgf",
        "xgf_adj",
        "sf",
        "sf_adj",
        "msf",
        "msf_adj",
        "bsa",
        "bsa_adj",
        "teammate_block",
        "teammate_block_adj",
        "ff",
        "ff_adj",
        "gf",
        "gf_adj",
        "give",
        "take",
        "hdgf",
        "hdsf",
        "hdff",
        "hdmsf",
        "hf",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
        "fow",
        "ozfw",
        "nzfw",
        "dzfw",
        "toi",
    ]

    new_cols = dict(zip(agg_stats, new_cols, strict=False))

    new_cols.update({"event_team": "team"})

    stats_for = data.groupby(group_list, as_index=False, dropna=False).agg(agg_dict).rename(columns=new_cols)

    # Getting the "against" stats

    group_list = ["season", "session", "opp_team"]

    if strength_state:
        group_list.append("opp_strength_state")

    if level == "game" or level == "period":
        group_list.insert(3, "event_team")

        group_list[2:2] = ["game_id", "game_date"]

    if level == "period":
        group_list.append("period")

    if score:
        group_list.append("opp_score_state")

    agg_stats = [
        "pred_goal",
        "pred_goal_adj",
        "shot",
        "shot_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "hit",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "event_length",
    ]

    agg_dict = {x: "sum" for x in agg_stats if x in data.columns}

    new_cols = [
        "xga",
        "xga_adj",
        "sa",
        "sa_adj",
        "msa",
        "msa_adj",
        "bsf",
        "bsf_adj",
        "fa",
        "fa_adj",
        "ga",
        "ga_adj",
        "hdga",
        "hdsa",
        "hdfa",
        "hdmsa",
        "ht",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
        "fol",
        "ozfl",
        "nzfl",
        "dzfl",
        "toi",
    ]

    new_cols = dict(zip(agg_stats, new_cols, strict=False))

    new_cols.update(
        {
            "opp_team": "team",
            "opp_score_state": "score_state",
            "opp_strength_state": "strength_state",
            "event_team": "opp_team",
        }
    )

    stats_against = data.groupby(group_list, as_index=False, dropna=False).agg(agg_dict).rename(columns=new_cols)

    merge_list = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "period",
    ]

    merge_list = [x for x in merge_list if x in stats_for.columns and x in stats_against.columns]

    team_stats = stats_for.merge(stats_against, on=merge_list, how="outer")

    team_stats["toi"] = (team_stats.toi_x + team_stats.toi_y) / 60

    team_stats["cf"] = team_stats.ff + team_stats.bsf + team_stats.teammate_block
    team_stats["cf_adj"] = team_stats.ff_adj + team_stats.bsf_adj + team_stats.teammate_block_adj

    team_stats["ca"] = team_stats.fa + team_stats.bsa
    team_stats["ca_adj"] = team_stats.fa_adj + team_stats.bsa_adj

    fos = ["ozf", "nzf", "dzf"]

    for fo in fos:
        team_stats[fo] = team_stats[f"{fo}w"] + team_stats[f"{fo}l"]

    team_stats = team_stats.dropna(subset="toi").reset_index(drop=True)

    cols = [x for x in list(TeamStatSchema.dtypes.keys()) if x in team_stats]

    team_stats = team_stats[cols]

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    team_stats = TeamStatSchema.validate(team_stats)

    return team_stats


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
        "api_id": String,
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

            player_df = opps.join(own, on=merge_list, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

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

        ind_stats = ind_stats.join(player_df, on=merge_list, how="full", coalesce=True, nulls_equal=True)

    # Fixing some stats

    null_columns = (pl.col(x).fill_null(0) for x in ind_stats.columns if x not in merge_list)

    ind_stats = ind_stats.with_columns(null_columns)

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


def prep_oi_polars(
    df: pl.DataFrame,
    df_ext: pl.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pl.DataFrame:
    """Docstring."""
    merge_cols = ["id", "event_idx"]

    df = df.join(df_ext, on=merge_cols, how="left", nulls_equal=True)

    players = (
        [f"event_on_{x}" for x in range(1, 8)]
        + [f"opp_on_{x}" for x in range(1, 8)]
        + [f"change_on_{x}" for x in range(1, 8)]
    )

    event_list = []
    opp_list = []
    zones_list = []

    for player in players:
        position = f"{player}_pos"
        player_eh_id = f"{player}_eh_id"
        player_api_id = f"{player}_api_id"

        group_list = ["season", "session"]

        if level == "session" or level == "season":
            group_list = group_list

        if level == "game":
            group_list.extend(["game_id", "game_date", "event_team", "opp_team"])

        if level == "period":
            group_list.extend(["game_id", "game_date", "event_team", "opp_team", "period"])

        # Accounting for desired player

        if "event_on" in player or "opp_on" in player:
            stats_list = [
                "block",
                "block_adj",
                "teammate_block",
                "teammate_block_adj",
                "fac",
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
                "fenwick",
                "fenwick_adj",
                "pred_goal",
                "pred_goal_adj",
                "ozf",
                "nzf",
                "dzf",
                "event_length",
            ]

        if "change_on" in player:
            stats_list = ["ozc", "nzc", "dzc", "otf"]

        agg_stats = [pl.sum(x) for x in stats_list if x in df.columns]

        if "event_on" in player or "change_on" in player:
            if level == "session" or level == "season":
                group_list.append("event_team")

            strength_group = ["strength_state"]

            teammates_group = [
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

            score_group = ["score_state"]

            opposition_group = [
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

            if "opp_team" not in group_list:
                opposition_group.insert(0, "opp_team")

            col_names = {
                "event_team": "team",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "goal": "gf",
                "goal_adj": "gf_adj",
                "hit": "hf",
                "miss": "msf",
                "miss_adj": "msf_adj",
                "block": "bsa",
                "block_adj": "bsa_adj",
                "teammate_block": "bsf",
                "teammate_block_adj": "bsf_adj",
                "pen0": "pent0",
                "pen2": "pent2",
                "pen4": "pent4",
                "pen5": "pent5",
                "pen10": "pent10",
                "fenwick": "ff",
                "fenwick_adj": "ff_adj",
                "pred_goal": "xgf",
                "pred_goal_adj": "xgf_adj",
                "fac": "fow",
                "ozf": "ozfw",
                "dzf": "dzfw",
                "nzf": "nzfw",
                "ozc": "ozs",
                "nzc": "nzs",
                "dzc": "dzs",
                "shot": "sf",
                "shot_adj": "sf_adj",
                "hd_goal": "hdgf",
                "hd_shot": "hdsf",
                "hd_fenwick": "hdff",
                "hd_miss": "hdmsf",
            }

        if "opp_on" in player:
            if level == "session" or level == "season":
                group_list.append("opp_team")

            strength_group = ["opp_strength_state"]

            teammates_group = [
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

            score_group = ["opp_score_state"]

            opposition_group = [
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

            if "event_team" not in group_list:
                opposition_group.insert(0, "event_team")

            col_names = {
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_goalie": "own_goalie",
                "own_goalie": "opp_goalie",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                player: "player",
                player_eh_id: "eh_id",
                player_api_id: "api_id",
                position: "position",
                "block": "bsf",
                "block_adj": "bsf_adj",
                "goal": "ga",
                "goal_adj": "ga_adj",
                "hit": "ht",
                "miss": "msa",
                "miss_adj": "msa_adj",
                "pen0": "pend0",
                "pen2": "pend2",
                "pen4": "pend4",
                "pen5": "pend5",
                "pen10": "pend10",
                "shot": "sa",
                "shot_adj": "sa_adj",
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
                "forwards": "opp_forwards",
                "forwards_eh_id": "opp_forwards_eh_id",
                "forwards_api_id": "opp_forwards_api_id",
                "defense": "opp_defense",
                "defense_eh_id": "opp_defense_eh_id",
                "defense_api_id": "opp_defense_api_id",
                "own_goalie_eh_id": "opp_goalie_eh_id",
                "own_goalie_api_id": "opp_goalie_api_id",
                "opp_forwards": "forwards",
                "opp_forwards_eh_id": "forwards_eh_id",
                "opp_forwards_api_id": "forwards_api_id",
                "opp_defense": "defense",
                "opp_defense_eh_id": "defense_eh_id",
                "opp_defense_api_id": "defense_api_id",
                "opp_goalie_eh_id": "own_goalie_eh_id",
                "opp_goalie_api_id": "own_goalie_api_id",
            }

        group_list = group_list + [player, player_eh_id, player_api_id, position]

        if strength_state:
            group_list = group_list + strength_group

        if teammates:
            group_list = group_list + teammates_group

        if score:
            group_list = group_list + score_group

        if opposition:
            group_list = group_list + opposition_group

        player_df = df.group_by(group_list).agg(agg_stats)

        col_names = {key: value for key, value in col_names.items() if key in player_df.columns}

        player_df = player_df.rename(col_names).drop_nulls(subset=["player", "eh_id", "api_id"])

        if "event_on" in player:
            event_list.append(player_df)

        elif "opp_on" in player:
            opp_list.append(player_df)

        elif "change_on" in player:
            zones_list.append(player_df)

    # On-ice stats

    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "player",
        "eh_id",
        "api_id",
        "position",
        "period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_eh_id",
        "opp_goalie_api_id",
        "own_goalie",
        "own_goalie_eh_id",
        "own_goalie_api_id",
        "forwards",
        "forwards_eh_id",
        "forwards_api_id",
        "defense",
        "defense_eh_id",
        "defense_api_id",
        "opp_forwards",
        "opp_forwards_eh_id",
        "opp_forwards_api_id",
        "opp_defense",
        "opp_defense_eh_id",
        "opp_defense_api_id",
    ]

    event_stats = pl.concat(event_list)

    agg_stats = [pl.sum(x) for x in event_stats.columns if x not in merge_cols]

    group_list = [x for x in merge_cols if x in event_stats.columns]

    event_stats = event_stats.group_by(group_list).agg(agg_stats).with_columns(event_df=pl.lit(1))

    opp_stats = pl.concat(opp_list)

    agg_stats = [pl.sum(x) for x in opp_stats.columns if x not in merge_cols]

    group_list = [x for x in merge_cols if x in opp_stats.columns]

    opp_stats = opp_stats.group_by(group_list).agg(agg_stats).with_columns(opp_df=pl.lit(1))

    zones_stats = pl.concat(zones_list)

    agg_stats = [pl.sum(x) for x in zones_stats.columns if x not in merge_cols]

    group_list = [x for x in merge_cols if x in zones_stats.columns]

    zones_stats = zones_stats.group_by(group_list).agg(agg_stats).with_columns(zones_df=pl.lit(1))

    merge_cols = [
        x for x in merge_cols if x in event_stats.columns and x in opp_stats.columns and x in zones_stats.columns
    ]

    oi_stats = event_stats.join(opp_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

    oi_stats = oi_stats.join(zones_stats, on=merge_cols, how="full", coalesce=True, nulls_equal=True)  # .fill_null(0)

    null_columns = (pl.col(x).fill_null(0) for x in oi_stats.columns if x not in merge_cols)

    oi_stats = oi_stats.with_columns(null_columns)

    oi_stats = oi_stats.with_columns(
        api_id=pl.col("api_id").cast(String),
        toi=(oi_stats["event_length"] + oi_stats["event_length_right"]) / 60,
        bsf=oi_stats["bsf"] + oi_stats["bsf_right"],
        bsf_adj=oi_stats["bsf_adj"] + oi_stats["bsf_adj_right"],
        cf=oi_stats["ff"] + oi_stats["bsf"],
        cf_adj=oi_stats["ff_adj"] + oi_stats["bsf_adj"],
        ca=oi_stats["fa"] + oi_stats["bsa"] + oi_stats["teammate_block"],
        ca_adj=oi_stats["fa_adj"] + oi_stats["bsa_adj"] + oi_stats["teammate_block_adj"],
        ozf=oi_stats["ozfw"] + oi_stats["ozfl"],
        nzf=oi_stats["nzfw"] + oi_stats["nzfl"],
        dfz=oi_stats["dzfw"] + oi_stats["dzfl"],
        fac=(
            oi_stats["ozfw"]
            + oi_stats["ozfl"]
            + oi_stats["nzfw"]
            + oi_stats["nzfl"]
            + oi_stats["dzfw"]
            + oi_stats["dzfl"]
        ),
    )

    columns = [x for x in list(OIStatSchema.dtypes.keys()) if x in oi_stats.columns] + [
        "event_df",
        "opp_df",
        "zones_df",
    ]

    oi_stats = oi_stats.select(columns)

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

    oi_stats = oi_stats.remove(pl.all_horizontal(pl.col(stats) == 0))

    return oi_stats


def prep_stats_polars(ind_stats_df: pl.DataFrame, oi_stats_df: pl.DataFrame) -> pd.DataFrame:
    """Prepares DataFrame of individual and on-ice stats from play-by-play data.

    Nested within `prep_stats` method.

    Parameters:
        ind_stats_df (pl.DataFrame):
            Dataframe of individual statistics to aggregate
        oi_stats_df (pl.DataFrame):
            Dataframe of on-ice statistics to aggregate
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
        toi (float):
            Time on-ice, in minutes, e.g, 0.483333
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

        Prepares individual and on-ice dataframe with default options
        >>> scraper._prep_stats()

        Individual and on-ice statistics, aggregated to season level
        >>> scraper._prep_stats(level="season")

        Individual and on-ice statistics, aggregated to game level, accounting for teammates
        >>> scraper._prep_stats(level="game", teammates=True)

    """
    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "eh_id",
        "api_id",
        "position",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "period",
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

    merge_cols = [x for x in merge_cols if x in ind_stats_df.columns and x in oi_stats_df.columns]

    stats = oi_stats_df.join(ind_stats_df, how="left", on=merge_cols, nulls_equal=True)

    null_columns = (pl.col(x).fill_null(0) for x in stats.columns if x not in merge_cols)

    stats = stats.with_columns(null_columns)

    stats = stats.filter(pl.col("toi") > 0)

    columns = [x for x in list(StatSchema.dtypes.keys()) if x in stats.columns] + ["event_df", "opp_df", "zones_df"]

    stats = stats.select(columns).with_columns(
        pl.col("api_id").cast(pl.String)
        # pl.col("own_goalie_api_id").cast(pl.Int64),
        # pl.col("opp_goalie_api_id").cast(pl.Int64),
    )

    return stats


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

    cols = [x for x in list(LineSchema.dtypes.keys()) if x in lines.columns]

    lines = lines.select(cols).filter(pl.col("toi") > 0)

    lines = prep_p60(lines)

    lines = prep_oi_percent(lines)

    return lines


def prep_team_stats_polars(
    df: pl.DataFrame,
    df_ext: pl.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strength_state: bool = True,
    opposition: bool = False,
    score: bool = False,
) -> pl.DataFrame:
    """Prepares DataFrame of team stats from play-by-play data.

    Nested within `prep_team_stats` method.

    Parameters:
        df (pd.DataFrame):
            Play-by-play data to aggregate for team statistics
        df_ext (pd.DataFrame):
            Extended play-by-play data to aggregate for team statistics
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        strength_state (bool):
            Determines if stats account for strength state
        opposition (bool):
            Determines if stats account for opponents on ice
        score (bool):
            Determines if stats account for score state

    Returns:
        season (int):
            Season as 8-digit number, e.g., 2023 for 2023-24 season
        session (str):
            Whether game is regular season, playoffs, or pre-season, e.g., R
        game_id (int):
            Unique game ID assigned by the NHL, e.g., 2023020001
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
        toi (float):
            Time on-ice, in minutes, e.g, 1.100000
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
            xG for (on-ice), e.g., 1.271583
        xga (float):
            xG against (on-ice), e.g, 0.000000
        xgf_adj (float):
            Score- and venue-adjusted xG for (on-ice), e.g., 1.381123
        xga_adj (float):
            Score- and venue-adjusted xG against (on-ice), e.g., 0.0
        sf (int):
            Shots for (on-ice), e.g, 5
        sa (int):
            Shots against (on-ice), e.g, 0
        sf_adj (float):
            Score- and venue-adjusted shots for (on-ice), e.g., 5.438277
        sa_adj (float):
            Score- and venue-adjusted shots against (on-ice), e.g., 0.0
        hdsf (int):
            High-danger shots for (on-ice), e.g, 3
        hdsa (int):
            High-danger shots against (on-ice), e.g, 0
        ff (int):
            Fenwick for (on-ice), e.g, 5
        fa (int):
            Fenwick against (on-ice), e.g, 0
        ff_adj (float):
            Score- and venue-adjusted fenwick events for (on-ice), e.g., 5.46503
        fa_adj (float):
            Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0
        hdff (int):
            High-danger fenwick for (on-ice), e.g, 3
        hdfa (int):
            High-danger fenwick against (on-ice), e.g, 0
        cf (int):
            Corsi for (on-ice), e.g, 5
        ca (int):
            Corsi against (on-ice), e.g, 0
        cf_adj (float):
            Score- and venue-adjusted corsi events for (on-ice), e.g., 5.46503
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
            Neutral zone faceoffs (on-ice), e.g, 4
        dzf (int):
            Defensive zone faceoffs (on-ice), e.g, 0
        fow (int):
            Faceoffs won (on-ice), e.g, 2
        fol (int):
            Faceoffs lost (on-ice), e.g, 0
        ozfw (int):
            Offensive zone faceoffs won (on-ice), e.g, 0
        ozfl (int):
            Offensive zone faceoffs lost (on-ice), e.g, 0
        nzfw (int):
            Neutral zone faceoffs won (on-ice), e.g, 2
        nzfl (int):
            Neutral zone faceoffs lost (on-ice), e.g, 1
        dzfw (int):
            Defensive zone faceoffs won (on-ice), e.g, 0
        dzfl (int):
            Defensive zone faceoffs lost (on-ice), e.g, 1
        pent0 (int):
            Penalty shots allowed (on-ice), e.g, 0
        pent2 (int):
            Minor penalties taken (on-ice), e.g, 1
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

        Team dataframe with default options
        >>> scraper._prep_team_stats()

        Team statistics, aggregated to season level
        >>> scraper._prep_team_stats(level="season")

        Team statistics, aggregated to game level, accounting for teammates
        >>> scraper._prep_team_stats(level="game", teammates=True)

    """
    merge_cols = ["id", "event_idx"]

    data = df.join(df_ext, how="left", on=merge_cols, nulls_equal=True)

    # Getting the "for" stats

    group_list = ["season", "session", "event_team"]

    if strength_state:
        group_list.append("strength_state")

    if level == "game" or level == "period" or opposition:
        group_list.insert(3, "opp_team")

        group_list[2:2] = ["game_id", "game_date"]

    if level == "period":
        group_list.append("period")

    if score:
        group_list.append("score_state")

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "shot",
        "shot_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "teammate_block",
        "teammate_block_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "give",
        "take",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "hit",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "event_length",
    ]

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    stats_for = data.group_by(group_list).agg(agg_stats)

    new_cols = [
        "xgf",
        "xgf_adj",
        "sf",
        "sf_adj",
        "msf",
        "msf_adj",
        "bsa",
        "bsa_adj",
        "teammate_block",
        "teammate_block_adj",
        "ff",
        "ff_adj",
        "gf",
        "gf_adj",
        "give",
        "take",
        "hdgf",
        "hdsf",
        "hdff",
        "hdmsf",
        "hf",
        "pent0",
        "pent2",
        "pent4",
        "pent5",
        "pent10",
        "fow",
        "ozfw",
        "nzfw",
        "dzfw",
        "toi",
    ]

    new_cols = dict(zip(stats, new_cols, strict=False))

    new_cols.update({"event_team": "team"})

    new_cols = {k: v for k, v in new_cols.items() if k in stats_for.columns}
    stats_for = stats_for.rename(new_cols)

    # Getting the "against" stats

    group_list = ["season", "session", "opp_team"]

    if strength_state:
        group_list.append("opp_strength_state")

    if level == "game" or level == "period":
        group_list.insert(3, "event_team")

        group_list[2:2] = ["game_id", "game_date"]

    if level == "period":
        group_list.append("period")

    if score:
        group_list.append("opp_score_state")

    stats = [
        "pred_goal",
        "pred_goal_adj",
        "shot",
        "shot_adj",
        "miss",
        "miss_adj",
        "block",
        "block_adj",
        "fenwick",
        "fenwick_adj",
        "goal",
        "goal_adj",
        "hd_goal",
        "hd_shot",
        "hd_fenwick",
        "hd_miss",
        "hit",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "fac",
        "ozf",
        "nzf",
        "dzf",
        "event_length",
    ]

    agg_stats = [pl.sum(x) for x in stats if x in data.columns]

    stats_against = data.group_by(group_list).agg(agg_stats)

    new_cols = [
        "xga",
        "xga_adj",
        "sa",
        "sa_adj",
        "msa",
        "msa_adj",
        "bsf",
        "bsf_adj",
        "fa",
        "fa_adj",
        "ga",
        "ga_adj",
        "hdga",
        "hdsa",
        "hdfa",
        "hdmsa",
        "ht",
        "pend0",
        "pend2",
        "pend4",
        "pend5",
        "pend10",
        "fol",
        "ozfl",
        "nzfl",
        "dzfl",
        "toi",
    ]

    new_cols = dict(zip(stats, new_cols, strict=False))

    new_cols.update(
        {
            "opp_team": "team",
            "opp_score_state": "score_state",
            "opp_strength_state": "strength_state",
            "event_team": "opp_team",
        }
    )

    new_cols = {k: v for k, v in new_cols.items() if k in stats_against.columns}

    stats_against = stats_against.rename(new_cols)

    merge_list = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "period",
    ]

    merge_list = [x for x in merge_list if x in stats_for.columns and x in stats_against.columns]

    team_stats = stats_for.join(stats_against, on=merge_list, how="full", nulls_equal=True)

    team_stats = team_stats.with_columns(
        toi=(team_stats["toi"] + team_stats["toi_right"]) / 60,
        cf=team_stats["ff"] + team_stats["bsf"] + team_stats["teammate_block"],
        cf_adj=team_stats["ff_adj"] + team_stats["bsf_adj"] + team_stats["teammate_block_adj"],
        ca=team_stats["fa"] + team_stats["bsa"],
        ca_adj=team_stats["fa_adj"] + team_stats["bsa_adj"],
        ozf=team_stats["ozfw"] + team_stats["ozfl"],
        nzf=team_stats["nzfw"] + team_stats["nzfl"],
        dzf=team_stats["dzfw"] + team_stats["dzfl"],
    ).filter(pl.col("toi") > 0, pl.col("toi").is_not_null())

    cols = [x for x in TeamStatSchema.dtypes.keys() if x in team_stats]

    team_stats = team_stats.select(cols)

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    return team_stats
