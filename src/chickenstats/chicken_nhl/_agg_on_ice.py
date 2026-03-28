from typing import Literal

import pandas as pd
import polars as pl
from polars import Int64, String
from chickenstats.chicken_nhl._agg_constants import _build_merge_list
from chickenstats.chicken_nhl.validation_pandas import oi_stats_pandera_pandas


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
        "own_goalie",
        "own_goalie_eh_id",
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

    columns = [x for x in list(oi_stats_pandera_pandas.dtypes.keys()) if x in oi_stats.columns]

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

    oi_stats = oi_stats_pandera_pandas.validate(oi_stats)

    return oi_stats


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
        api_id=pl.col("api_id").cast(Int64),
        toi=(pl.col("event_length") + pl.col("event_length_right")) / 60,
        bsf=pl.col("bsf") + pl.col("bsf_right"),
        bsf_adj=pl.col("bsf_adj") + pl.col("bsf_adj_right"),
        cf=pl.col("ff") + pl.col("bsf"),
        cf_adj=pl.col("ff_adj") + pl.col("bsf_adj") + pl.col("bsf_adj_right"),
        ca=pl.col("fa") + pl.col("bsa") + pl.col("teammate_block"),
        ca_adj=pl.col("fa_adj") + pl.col("bsa_adj") + pl.col("teammate_block_adj"),
        ozf=pl.col("ozfw") + pl.col("ozfl"),
        nzf=pl.col("nzfw") + pl.col("nzfl"),
        dzf=pl.col("dzfw") + pl.col("dzfl"),
        fac=(pl.col("ozfw") + pl.col("ozfl") + pl.col("nzfw") + pl.col("nzfl") + pl.col("dzfw") + pl.col("dzfl")),
    )

    columns = [x for x in list(oi_stats_pandera_pandas.dtypes.keys()) if x in oi_stats.columns] + [
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
