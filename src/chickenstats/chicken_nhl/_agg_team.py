from typing import Literal

import pandas as pd
import polars as pl
from polars import Int64, String

from chickenstats.chicken_nhl._agg_transforms import prep_p60, prep_oi_percent
from chickenstats.chicken_nhl.validation_pandas import team_stats_pandera_pandas


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

    cols = [x for x in list(team_stats_pandera_pandas.dtypes.keys()) if x in team_stats]

    team_stats = team_stats[cols]

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    team_stats = team_stats_pandera_pandas.validate(team_stats)

    return team_stats


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

    cols = [x for x in team_stats_pandera_pandas.dtypes.keys() if x in team_stats]

    team_stats = team_stats.select(cols)

    team_stats = prep_p60(team_stats)

    team_stats = prep_oi_percent(team_stats)

    return team_stats
