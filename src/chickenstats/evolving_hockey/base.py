from typing import Literal

import numpy as np
import pandas as pd


def prep_ind(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of individual stats from play-by-play data.

    Nested within `prep_stats` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `prep_pbp` function
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        score (bool):
            Determines if stats are cut by score state
        teammates (bool):
            Determines if stats are cut by teammates on ice
        opposition (bool):
            Determines if stats are cut by opponents on ice

    """
    df = pbp.copy()

    players = ["event_player_1", "event_player_2", "event_player_3"]

    if level == "session" or level == "season":
        merge_list = ["season", "session", "player", "player_id", "position", "team", "strength_state"]

    if level == "game":
        merge_list = [
            "season",
            "session",
            "player",
            "player_id",
            "position",
            "team",
            "strength_state",
            "game_id",
            "game_date",
            "opp_team",
        ]

    if level == "period":
        merge_list = [
            "season",
            "session",
            "player",
            "player_id",
            "position",
            "team",
            "strength_state",
            "game_id",
            "game_date",
            "opp_team",
            "game_period",
        ]

    if score:
        merge_list.append("score_state")

    if teammates:
        merge_list = merge_list + ["forwards", "forwards_id", "defense", "defense_id", "own_goalie", "own_goalie_id"]

    if opposition:
        merge_list = merge_list + [
            "opp_forwards",
            "opp_forwards_id",
            "opp_defense",
            "opp_defense_id",
            "opp_goalie",
            "opp_goalie_id",
        ]

        if "opp_team" not in merge_list:
            merge_list.append("opp_team")

    ind_stats = pd.DataFrame(columns=merge_list)  # ty: ignore[invalid-argument-type]

    for player in players:
        player_id = f"{player}_id"

        position = f"{player}_pos"

        if level == "session" or level == "season":
            group_base = ["season", "session", "event_team", player, player_id, position]

        if level == "game":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                player,
                player_id,
                position,
            ]

        if level == "period":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "game_period",
                player,
                player_id,
                position,
            ]

        if opposition is True and "opp_team" not in group_base:
            group_base.append("opp_team")

        mask = df[player] != "BENCH"

        if player == "event_player_1":
            strength_group = ["strength_state"]
            group_list = group_base + strength_group

            if teammates:
                teammates_group = [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

                group_list = group_list + teammates_group

            if score:
                score_group = ["score_state"]
                group_list = group_list + score_group

            if opposition:
                opposition_group = ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

                group_list = group_list + opposition_group

            stats_list = [
                "block",
                "fac",
                "give",
                "goal",
                "hd_fenwick",
                "hd_goal",
                "hd_miss",
                "hd_shot",
                "hit",
                "miss",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "shot",
                "take",
                "corsi",
                "fenwick",
                "pred_goal",
                "ozf",
                "nzf",
                "dzf",
            ]

            stats_dict = {x: "sum" for x in stats_list if x in df.columns}

            new_cols = {
                "block": "isb",
                "fac": "ifow",
                "give": "igive",
                "goal": "g",
                "hd_fenwick": "ihdf",
                "hd_goal": "ihdg",
                "hd_miss": "ihdm",
                "hd_shot": "ihdsf",
                "hit": "ihf",
                "miss": "imsf",
                "pen0": "ipent0",
                "pen2": "ipent2",
                "pen4": "ipent4",
                "pen5": "ipent5",
                "pen10": "ipent10",
                "shot": "isf",
                "take": "itake",
                "corsi": "icf",
                "fenwick": "iff",
                "pred_goal": "ixg",
                "ozf": "iozfw",
                "nzf": "inzfw",
                "dzf": "idzfw",
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                position: "position",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

            player_df = df[mask].copy().groupby(group_list, as_index=False).agg(stats_dict).rename(columns=new_cols)

            # drop_list = [x for x in stats if x not in new_cols.keys() and x in player_df.columns]

        if player == "event_player_2":
            # Getting on-ice stats against for player 2

            opp_strength = ["opp_strength_state"]
            event_strength = ["strength_state"]

            opp_group_list = group_base + opp_strength
            event_group_list = group_base + event_strength

            if not opposition and level in ["season", "session"]:
                opp_group_list.remove("event_team")
                opp_group_list.append("opp_team")

            if teammates:
                opp_teammates = ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

                event_teammates = [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

                opp_group_list = opp_group_list + opp_teammates
                event_group_list = event_group_list + event_teammates

            if score:
                opp_score = ["opp_score_state"]
                event_score = ["score_state"]

                opp_group_list = opp_group_list + opp_score
                event_group_list = event_group_list + event_score

            if opposition:
                opp_opposition = [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

                event_opposition = ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

                opp_group_list = opp_group_list + opp_opposition
                event_group_list = event_group_list + event_opposition

            stats_1 = ["block", "fac", "hit", "pen0", "pen2", "pen4", "pen5", "pen10", "ozf", "nzf", "dzf"]

            stats_1 = {x: "sum" for x in stats_1 if x.lower() in df.columns}

            new_cols_1 = {
                "opp_on_g": "own_goalie",
                "opp_on_g_id": "own_goalie_id",
                "event_on_g": "opp_goalie",
                "event_on_g_id": "opp_goalie_id",
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
                player_id: "player_id",
                position: "position",
                "fac": "ifol",
                "hit": "iht",
                "ozf": "iozfl",
                "nzf": "inzfl",
                "dzf": "idzfl",
                "block": "ibs",
                "opp_on_f": "forwards",
                "opp_on_f_id": "forwards_id",
                "opp_on_d": "defense",
                "opp_on_d_id": "defense_id",
                "event_on_f": "opp_forwards",
                "event_on_f_id": "opp_forwards_id",
                "event_on_d": "opp_defense",
                "event_on_d_id": "opp_defense_id",
            }

            event_types = ["BLOCK", "FAC", "HIT", "PENL"]

            mask_1 = np.logical_and(df[player] != "BENCH", df.event_type.isin(event_types))

            opps = df[mask_1].copy().groupby(opp_group_list, as_index=False).agg(stats_1).rename(columns=new_cols_1)

            # Getting primary assists and primary assists xG from player 2

            stats_2 = ["goal", "pred_goal"]

            stats_2 = {x: "sum" for x in stats_2 if x in df.columns}

            new_cols_2 = {
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                "goal": "a1",
                "pred_goal": "a1_xg",
                position: "position",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

            mask_2 = np.logical_and(df[player] != "BENCH", df.event_type.isin([x.upper() for x in stats_2]))

            own = df[mask_2].copy().groupby(event_group_list, as_index=False).agg(stats_2).rename(columns=new_cols_2)

            player_df = opps.merge(own, left_on=merge_list, right_on=merge_list, how="outer").fillna(0)

        if player == "event_player_3":
            group_list = group_base + strength_group

            if teammates:
                group_list = group_list + teammates_group

            if score:
                group_list = group_list + score_group

            if opposition:
                group_list = group_list + opposition_group

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
                player_id: "player_id",
                position: "position",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

            player_df = player_df.rename(columns=new_cols)

        ind_stats = ind_stats.merge(player_df, on=merge_list, how="outer").fillna(0)

    # Fixing some stats

    ind_stats["gax"] = ind_stats.g - ind_stats.ixg

    columns = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "player_id",
        "position",
        "team",
        "opp_team",
        "game_period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_id",
        "own_goalie",
        "own_goalie_id",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
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

    columns = [x for x in columns if x in ind_stats.columns]

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

    ind_stats = ind_stats.loc[(ind_stats[stats] != 0).any(axis=1)]

    return ind_stats


def prep_oi(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of on-ice stats from play-by-play data.

    Nested within `prep_stats` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `prep_pbp` function
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        score (bool):
            Determines if stats are cut by score state
        teammates (bool):
            Determines if stats are cut by teammates on ice
        opposition (bool):
            Determines if stats are cut by opponents on ice

    """
    df = pbp.copy()

    stats_list = [
        "block",
        "fac",
        "goal",
        "goal_adj",
        "hd_fenwick",
        "hd_goal",
        "hd_miss",
        "hd_shot",
        "hit",
        "miss",
        "pen0",
        "pen2",
        "pen4",
        "pen5",
        "pen10",
        "shot",
        "shot_adj",
        "corsi",
        "corsi_adj",
        "fenwick",
        "fenwick_adj",
        "pred_goal",
        "pred_goal_adj",
        "ozf",
        "nzf",
        "dzf",
        "event_length",
    ]

    stats_dict = {x: "sum" for x in stats_list if x in df.columns}

    players = [f"event_on_{x}" for x in range(1, 8)] + [f"opp_on_{x}" for x in range(1, 8)]

    event_list = []

    opp_list = []

    for player in players:
        position = f"{player}_pos"

        player_id = f"{player}_id"

        if level == "session" or level == "season":
            group_list = ["season", "session"]

        if level == "game":
            group_list = ["season", "game_id", "game_date", "session", "event_team", "opp_team"]

        if level == "period":
            group_list = ["season", "game_id", "game_date", "session", "event_team", "opp_team", "game_period"]

        # Accounting for desired player

        if "event_on" in player:
            if level == "session" or level == "season":
                group_list.append("event_team")

            strength_group = ["strength_state"]

            teammates_group = [
                "event_on_f",
                "event_on_f_id",
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
            ]

            score_group = ["score_state"]

            opposition_group = ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

            col_names = {
                "event_team": "team",
                player: "player",
                player_id: "player_id",
                position: "position",
                "goal": "gf",
                "goal_adj": "gf_adj",
                "hit": "hf",
                "miss": "msf",
                "block": "bsf",
                "pen0": "pent0",
                "pen2": "pent2",
                "pen4": "pent4",
                "pen5": "pent5",
                "pen10": "pent10",
                "corsi": "cf",
                "corsi_adj": "cf_adj",
                "fenwick": "ff",
                "fenwick_adj": "ff_adj",
                "pred_goal": "xgf",
                "pred_goal_adj": "xgf_adj",
                "FAC": "fow",
                "ozf": "ozfw",
                "dzf": "dzfw",
                "nzf": "nzfw",
                "shot": "sf",
                "shot_adj": "sf_adj",
                "hd_goal": "hdgf",
                "hd_shot": "hdsf",
                "hd_fenwick": "hdff",
                "hd_miss": "hdmsf",
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_on_d": "defense",
                "event_on_d_id": "defense_id",
                "event_on_g": "own_goalie",
                "event_on_g_id": "own_goalie_id",
                "opp_on_f": "opp_forwards",
                "opp_on_f_id": "opp_forwards_id",
                "opp_on_d": "opp_defense",
                "opp_on_d_id": "opp_defense_id",
                "opp_on_g": "opp_goalie",
                "opp_on_g_id": "opp_goalie_id",
            }

        if "opp_on" in player:
            if level == "session" or level == "season":
                group_list.append("opp_team")

            strength_group = ["opp_strength_state"]

            teammates_group = ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

            score_group = ["opp_score_state"]

            opposition_group = [
                "event_on_f",
                "event_on_f_id",
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
            ]

            col_names = {
                "opp_team": "team",
                "event_team": "opp_team",
                "opp_goalie": "own_goalie",
                "own_goalie": "opp_goalie",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                player: "player",
                player_id: "player_id",
                position: "position",
                "block": "bsa",
                "goal": "ga",
                "goal_adj": "ga_adj",
                "hit": "ht",
                "miss": "msa",
                "pen0": "pend0",
                "pen2": "pend2",
                "pen4": "pend4",
                "pen5": "pend5",
                "pen10": "pend10",
                "shot": "sa",
                "shot_adj": "sa_adj",
                "corsi": "ca",
                "corsi_adj": "ca_adj",
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
                "event_on_f": "opp_forwards",
                "event_on_f_id": "opp_forwards_id",
                "event_on_d": "opp_defense",
                "event_on_d_id": "opp_defense_id",
                "event_on_g": "opp_goalie",
                "event_on_g_id": "opp_goalie_id",
                "opp_on_f": "forwards",
                "opp_on_f_id": "forwards_id",
                "opp_on_d": "defense",
                "opp_on_d_id": "defense_id",
                "opp_on_g": "own_goalie",
                "opp_on_g_id": "own_goalie_id",
            }

        group_list = group_list + [player, player_id, position] + strength_group

        if teammates:
            group_list = group_list + teammates_group

        if score:
            group_list = group_list + score_group

        if opposition:
            group_list = group_list + opposition_group

        player_df = df.groupby(group_list, as_index=False).agg(stats_dict)

        col_names = {key: value for key, value in col_names.items() if key in player_df.columns}

        player_df = player_df.rename(columns=col_names)

        if "event_on" in player:
            event_list.append(player_df)

        else:
            opp_list.append(player_df)

    # On-ice stats

    merge_cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "player",
        "player_id",
        "position",
        "game_period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_id",
        "own_goalie",
        "own_goalie_id",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
    ]

    event_stats = pd.concat(event_list, ignore_index=True)

    stats_dict = {x: "sum" for x in event_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in event_stats.columns]

    event_stats = event_stats.groupby(group_list, as_index=False).agg(stats_dict)

    opp_stats = pd.concat(opp_list, ignore_index=True)

    stats_dict = {x: "sum" for x in opp_stats.columns if x not in merge_cols}

    group_list = [x for x in merge_cols if x in opp_stats.columns]

    opp_stats = opp_stats.groupby(group_list, as_index=False).agg(stats_dict)

    merge_cols = [x for x in merge_cols if x in event_stats.columns and x in opp_stats.columns]

    oi_stats = event_stats.merge(opp_stats, on=merge_cols, how="outer").fillna(0)

    oi_stats["toi"] = (oi_stats.event_length_x + oi_stats.event_length_y) / 60

    oi_stats = oi_stats.drop(["event_length_x", "event_length_y"], axis=1)

    fo_list = ["ozf", "dzf", "nzf"]

    for fo in fo_list:
        oi_stats[fo] = oi_stats[f"{fo}w"] + oi_stats[f"{fo}l"]

    oi_stats["fac"] = oi_stats.ozf + oi_stats.nzf + oi_stats.dzf

    columns = [
        "season",
        "session",
        "game_id",
        "game_date",
        "player",
        "player_id",
        "position",
        "team",
        "opp_team",
        "game_period",
        "strength_state",
        "score_state",
        "opp_goalie",
        "opp_goalie_id",
        "own_goalie",
        "own_goalie_id",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
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

    columns = [x for x in columns if x in oi_stats.columns]

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

    return oi_stats


def prep_zones(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """Prepares DataFrame of zone stats from play-by-play data.

    Nested within `prep_stats` function.

    Parameters:
        pbp (pd.DataFrame):
            Data returned from `prep_pbp` function
        level (str):
            Determines the level of aggregation. One of season, session, game, period
        score (bool):
            Determines if stats are cut by score state
        teammates (bool):
            Determines if stats are cut by teammates on ice
        opposition (bool):
            Determines if stats are cut by opponents on ice

    """
    conds = np.logical_and(
        pbp.event_type == "CHANGE", np.logical_or.reduce([pbp.ozs > 0, pbp.nzs > 0, pbp.dzs > 0, pbp.otf > 0])
    )

    df = pbp.loc[conds].copy()

    players_on = df.players_on.str.split(", ", expand=True)

    new_cols = {x: f"player_{x + 1}" for x in players_on.columns}

    players_on = players_on.rename(columns=new_cols)

    players_on_id = df.players_on_id.str.split(", ", expand=True)

    new_cols = {x: f"player_{x + 1}_id" for x in players_on_id.columns}

    players_on_id = players_on_id.rename(columns=new_cols)

    players_on_pos = df.players_on_pos.str.split(", ", expand=True)

    new_cols = {x: f"player_{x + 1}_pos" for x in players_on_pos.columns}

    players_on_pos = players_on_pos.rename(columns=new_cols)

    players_on = players_on.merge(players_on_id, left_index=True, right_index=True)

    players_on = players_on.merge(players_on_pos, left_index=True, right_index=True)

    if level == "session" or level == "season":
        group_list = ["season", "session", "event_team", "strength_state"]

    if level == "game":
        group_list = ["season", "session", "game_id", "game_date", "event_team", "strength_state", "opp_team"]

    if level == "period":
        group_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "game_period",
            "event_team",
            "strength_state",
            "opp_team",
        ]

    if score:
        group_list.append("score_state")

    if teammates:
        group_list = group_list + [
            "event_on_f",
            "event_on_f_id",
            "event_on_d",
            "event_on_d_id",
            "event_on_g",
            "event_on_g_id",
        ]

    if opposition:
        group_list = group_list + ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

    stats = ["ozs", "nzs", "dzs", "otf"]

    keep_cols = group_list + stats

    players_on = df[keep_cols].merge(players_on, left_index=True, right_index=True)

    # zones = pd.DataFrame(columns=group_list + ["player", "player_id", "position"])

    player_list = [f"player_{x}" for x in range(1, 6)]

    zones_list = []

    for player in player_list:
        group_cols = group_list + [player, f"{player}_id", f"{player}_pos"]

        new_cols = {player: "player", f"{player}_id": "player_id", f"{player}_pos": "position"}

        agg_stats = {x: "sum" for x in stats}

        player_df = players_on.groupby(group_cols, as_index=False).agg(agg_stats).rename(columns=new_cols)

        # zones = zones.merge(player_df, how = 'outer', on = group_list + ['player', 'player_id'])

        zones_list.append(player_df)

    zones = pd.concat(zones_list, ignore_index=True)

    agg_stats = {x: "sum" for x in stats}

    zones = zones.groupby(group_list + ["player", "player_id", "position"], as_index=False).agg(agg_stats)

    new_cols = {
        "event_team": "team",
        "event_on_f": "forwards",
        "event_on_f_id": "forwards_id",
        "event_on_d": "defense",
        "event_on_d_id": "defense_id",
        "event_on_g": "own_goalie",
        "event_on_g_id": "own_goalie_id",
        "opp_on_f": "opp_forwards",
        "opp_on_f_id": "opp_forwards_id",
        "opp_on_d": "opp_defense",
        "opp_on_d_id": "opp_defense_id",
        "opp_on_g": "opp_goalie",
        "opp_on_g_id": "opp_goalie_id",
    }

    zones = zones.rename(columns=new_cols)

    columns = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "player",
        "player_id",
        "position",
        "strength_state",
        "score_state",
        "game_period",
        "opp_team",
        "forwards",
        "forwards_id",
        "defense",
        "defense_id",
        "own_goalie",
        "own_goalie_id",
        "opp_forwards",
        "opp_forwards_id",
        "opp_defense",
        "opp_defense_id",
        "opp_goalie",
        "opp_goalie_id",
        "ozs",
        "nzs",
        "dzs",
        "otf",
    ]

    columns = [x for x in columns if x in zones.columns]

    zones = zones[columns]

    zones[["player", "player_id"]] = zones[["player", "player_id"]].replace("", np.nan)

    zones = zones.dropna(subset=["player", "player_id"])

    return zones
