import pandas as pd
import polars as pl
from polars import Int64, String
from chickenstats.chicken_nhl._agg_transforms import prep_p60, prep_oi_percent
from chickenstats.chicken_nhl.validation_pandas import stats_pandera_pandas


def prep_stats_pandas(ind_stats_df: pd.DataFrame, oi_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Prepares DataFrame of individual and on-ice stats from play-by-play data.

    Nested within `prep_stats` method.

    Parameters:
        ind_stats_df (pd.DataFrame):
            Dataframe of individual statistics to aggregate
        oi_stats_df (pd.DataFrame):
            Dataframe of on-ice statistics to aggregate

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

    columns = [x for x in list(stats_pandera_pandas.dtypes.keys()) if x in stats.columns]

    stats = stats[columns]

    stats = prep_p60(stats)

    stats = prep_oi_percent(stats)

    stats = stats_pandera_pandas.validate(stats)

    return stats


def prep_stats_polars(ind_stats_df: pl.DataFrame, oi_stats_df: pl.DataFrame) -> pd.DataFrame:
    """Prepares DataFrame of individual and on-ice stats from play-by-play data.

    Nested within `prep_stats` method.

    Parameters:
        ind_stats_df (pl.DataFrame):
            Dataframe of individual statistics to aggregate
        oi_stats_df (pl.DataFrame):
            Dataframe of on-ice statistics to aggregate

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

    columns = [x for x in list(stats_pandera_pandas.dtypes.keys()) if x in stats.columns]

    integer_columns = ["api_id", "own_goalie_api_id", "opp_goalie_api_id"]
    integer_columns = (pl.col(x).cast(pl.Int64) for x in integer_columns if x in stats.columns)

    sort_stuff = {
        "season": False,
        "session": True,
        "game_id": False,
        "team": False,
        "player": False,
        "strength_state": True,
        "period": False,
        "score_state": False,
        "toi": True,
        "own_goalie": False,
        "forwards": False,
    }

    sort_list = [x for x in sort_stuff.keys() if x in stats.columns]
    descending_list = [v for k, v in sort_stuff.items() if k in stats.columns]

    stats = stats.select(columns).with_columns(integer_columns).sort(by=sort_list, descending=descending_list)

    stats = prep_p60(stats)
    stats = prep_oi_percent(stats)

    return stats
