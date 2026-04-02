from __future__ import annotations

from typing import Literal

import pandas as pd

from chickenstats.chicken_nhl.validation_pandas import team_stats_pandera_pandas
from chickenstats.evolving_hockey.base import prep_ind, prep_oi, prep_zones
from chickenstats.evolving_hockey.validation import LineSchema, StatSchema
from chickenstats.utilities.utilities import ChickenProgress


# Function combining the on-ice and individual stats
def prep_stats(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
) -> pd.DataFrame:
    """Prepares an individual and on-ice stats dataframe using EvolvingHockey data.

    Aggregates to desired level. Capable of returning cuts that account for strength state,
    period, score state, teammates, and opposition.

    Returns a Pandas DataFrame.

    Parameters:
        pbp (pd.DataFrame):
            Dataframe from the prep_pbp function with the default columns argument
        level (str):
            Level to aggregate stats, e.g., 'game'
        score (bool):
            Whether to aggregate to score state level
        teammates (bool):
            Whether to account for teammates when aggregating
        opposition (bool):
            Whether to account for opposition when aggregating
        disable_progress_bar (bool):
            Whether to disable progress bar

    Returns:
        season (int):
            8-digit season code, e.g., 20232024
        session (str):
            Regular season or playoffs, e.g., R
        game_id (int):
            10-digit game identifier, e.g., 2023020015
        game_date (str):
            Date of game in Eastern time-zone, e.g., 2023-10-12
        player (str):
            Name of the player, e.g., FILIP.FORSBERG
        player_id (str):
            Player EH ID, e.g., FILIP.FORSBERG
        position (str):
            Player's position, e.g., L
        team (str):
            3-letter abbreviation of the player's team, e.g., NSH
        opp_team: object
            3-letter abbreviation of the opposing team, e.g., SEA
        strength_state (str):
            Strength state from the perspective of the event team, e.g., 5v5
        score_state (str):
            Score state from the perspective of the event team, e.g., 0v0
        game_period (int):
            Game period, e.g., 1
        forwards (str):
            Names of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
        forwards_id (str):
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
        defense (str):
            Names of the event team's defensemen that are on the ice during the event,
            e.g., ALEX.CARRIER, RYAN.MCDONAGH
        defense_id (str):
            EH IDs of the event team's defensemen that are on the ice during the event,
            e.g., ALEX.CARRIER, RYAN.MCDONAGH
        own_goalie (str):
            Name of the goalie for the event team, e.g., JUUSE.SAROS
        own_goalie_id (str):
            Identifier for the event team goalie that can be used to match with Evolving Hockey data, e.g., JUUSE.SAROS
        opp_forwards (str):
            Names of the opponent's forwards that are on the ice during the event,
            e.g., JARED.MCCANN, JORDAN.EBERLE, MATTY.BENIERS
        opp_forwards_id (str):
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., JARED.MCCANN, JORDAN.EBERLE, MATTY.BENIERS
        opp_defense(str):
            Names of the opposing team's defensemen that are on the ice during the event,
            e.g., JAMIE.OLEKSIAK, WILLIAM.BORGEN
        opp_defense_id (str):
            EH IDs of the opposing team's defensemen that are on the ice during the event,
            e.g., JAMIE.OLEKSIAK, WILLIAM.BORGEN
        opp_goalie (str):
            Name of the opposing goalie for the event team, e.g., PHILIPP.GRUBAUER
        opp_goalie_id (str):
            Identifier for the opposing goalie that can be used to match with Evolving Hockey data,
            e.g., PHILIPP.GRUBAUER
        toi (float):
            Time on-ice in minutes, e.g., 1.616667
        g (float):
            Number of individual goals scored, e.g, 0
        a1 (float):
            Number of primary assists, e.g, 0
        a2 (float):
            Number of secondary assists, e.g, 0
        isf (float):
            Number of indiviudal shots registered, e.g., 0
        iff (float):
            Number of indiviudal fenwick events registered, e.g., 0
        icf (float):
            Number of indiviudal corsi events registered, e.g., 0
        ixg (float):
            Sum value of individual predicted goals (xG), e.g., 0
        gax (float):
            Sum value of goals scored above expected, e.g., 0
        ihdg (float):
            Sum value of individual high-danger goals scored, e.g., 0
        ihdf (float):
            Sum value of individual high-danger fenwick events registered, e.g., 0
        ihdsf (float):
            Sum value of individual high-danger shots taken, e.g., 0
        ihdm (float):
            Sum value of individual high-danger shots missed, e.g., 0
        imsf (float):
            Sum value of individual missed shots, 0
        isb (float):
            Sum value of shots taken that were ultimately blocked, e.g., 0
        ibs (float):
            Sum value of opponent shots taken that the player ultimately blocked, e.g., 0
        igive (float):
            Sum of individual giveaways, e.g., 0
        itake (float):
            Sum of individual takeaways, e.g., 0
        ihf (float):
            Sum of individual hits for, e.g., 0
        iht (float):
            Sum of individual hits taken, e.g., 0
        ifow (float):
            Sum of individual faceoffs won, e.g., 0
        ifol (float):
            Sum of individual faceoffs lost, e.g., 0
        iozfw (float):
            Sum of individual faceoffs won in offensive zone, e.g., 0
        iozfl (float):
            Sum of individual faceoffs lost in offensive zone, e.g., 0
        inzfw (float):
            Sum of individual faceoffs won in neutral zone, e.g., 0
        inzfl (float):
            Sum of individual faceoffs lost in neutral zone, e.g., 0
        idzfw (float):
            Sum of individual faceoffs won in defensive zone, e.g., 0
        idzfl (float):
            Sum of individual faceoffs lost in defensive zone, e.g., 0
        a1_xg (float):
            Sum of xG from primary assists, e.g., 0
        a2_xg (float):
            Sum of xG from secondary assists, e.g., 0
        ipent0 (float):
            Sum of individual 0-minute penalties taken, e.g., 0
        ipent2 (float):
            Sum of individual 2-minute penalties taken, e.g., 0
        ipent4 (float):
            Sum of individual 4-minute penalties taken, e.g., 0
        ipent5 (float):
            Sum of individual 5-minute penalties taken, e.g., 0
        ipent10 (float):
            Sum of individual 10-minute penalties taken, e.g., 0
        ipend0 (float):
            Sum of individual 0-minute penalties drawn, e.g., 0
        ipend2 (float):
            Sum of individual 2-minute penalties drawn, e.g., 0
        ipend4 (float):
            Sum of individual 4-minute penalties drawn, e.g., 0
        ipend5 (float):
            Sum of individual 5-minute penalties drawn, e.g., 0
        ipend10 (float):
            Sum of individual 10-minute penalties drawn, e.g., 0
        ozs (float):
            Sum of changes with offensive zone starts, e.g., 0
        nzs (float):
            Sum of changes with neutral zone starts, e.g., 0
        dzs (float):
            Sum of changes with defensive zone starts, e.g., 1
        otf (float):
            Sum of changes on-the-fly, e.g., 0
        gf (float):
            Sum of goals scored while player is on-ice, e.g., 0
        gf_adj (float):
            Sum of venue- and score-adjusted goals scored while player is on-ice, e.g., 0
        hdgf (float):
            Sum of high-danger goals scored while player is on-ice, e.g., 0
        ga (float):
            Sum of goals allowed while player is on-ice, e.g., 0
        ga_adj (float):
            Sum of venue- and score-adjusted goals allowed while player is on-ice, e.g., 0
        hdga (float):
            Sum of high-danger goals allowed while player is on-ice, e.g., 0
        xgf (float):
            Sum of expected goals generated while player is on-ice, e.g., 0.017266
        xgf_adj (float):
            Sum of venue- and score-adjusted expected goals generated while player is on-ice, e.g., 0.016472
        xga (float):
            Sum of expected goals allowed while player is on-ice, e.g., 0.123475
        xga_adj (float):
            Sum of venue- and score-adjusted expected goals allowed while player is on-ice, e.g., 0.129772
        sf (float):
            Sum of shots taken while player is on-ice, e.g., 1
        sf_adj (float):
            Sum of venue- and score-adjusted shots taken while player is on-ice, e.g., .972
        hdsf (float):
            Sum of high-danger shots taken while player is on-ice, e.g., 0
        sa (float):
            Sum of shots allowed while player is on-ice, e.g., 0
        sa_adj (float):
            Sum of venue- and score-adjusted shots allowed while player is on-ice, e.g., 0
        hdsa (float):
            Sum of high-danger shots allowed while player is on-ice, e.g., 0
        ff (float):
            Sum of fenwick events generated while player is on-ice, e.g., 1
        ff_adj (float):
            Sum of venue- and score-adjusted fenwick events generated while player is on-ice, e.g., 0.968
        hdff (float):
            Sum of high-danger fenwick events generated while player is on-ice, e.g., 0
        fa (float):
            Sum of fenwick events allowed while player is on-ice, e.g., 1
        fa_adj (float):
            Sum of venue- and score-adjusted fenwick events allowed while player is on-ice, e.g., 1.034
        hdfa (float):
            Sum of high-danger fenwick events allowed while player is on-ice, e.g., 1
        cf (float):
            Sum of corsi events generated while player is on-ice, e.g., 1
        cf_adj (float):
            Sum of venue- and score-adjusted corsi events generated while player is on-ice, e.g., 0.970
        ca (float):
            Sum of corsi events allowed while player is on-ice, e.g., 2
        ca_adj (float):
            Sum of venue- and score-adjusted corsi events allowed while player is on-ice, e.g., 2.064
        bsf (float):
            Sum of shots taken that were ultimately blocked while player is on-ice, e.g., 0
        bsa (float):
            Sum of shots allowed that were ultimately blocked while player is on-ice, e.g., 1
        msf (float):
            Sum of shots taken that missed net while player is on-ice, e.g., 0
        hdmsf (float):
            Sum of high-danger shots taken that missed net while player is on-ice, e.g., 0
        msa (float):
            Sum of shots allowed that missed net while player is on-ice, e.g., 1
        hdmsa (float):
            Sum of high-danger shots allowed that missed net while player is on-ice, e.g., 1
        hf (float):
            Sum of hits dished out while player is on-ice, e.g., 0
        ht (float):
            Sum of hits taken while player is on-ice, e.g., 0
        ozf (float):
            Sum of offensive zone faceoffs that occur while player is on-ice, e.g., 0
        nzf (float):
            Sum of neutral zone faceoffs that occur while player is on-ice, e.g., 0
        dzf (float):
            Sum of defensive zone faceoffs that occur while player is on-ice, e.g., 1
        fow (float):
            Sum of faceoffs won while player is on-ice, e.g., 1
        fol (float):
            Sum of faceoffs lost while player is on-ice, e.g., 0
        ozfw (float):
            Sum of offensive zone faceoffs won while player is on-ice, e.g., 0
        ozfl (float):
            Sum of offensive zone faceoffs lost while player is on-ice, e.g., 1
        nzfw (float):
            Sum of neutral zone faceoffs won while player is on-ice, e.g., 0
        nzfl (float):
            Sum of neutral zone faceoffs lost while player is on-ice, e.g., 0
        dzfw (float):
            Sum of defensive zone faceoffs won while player is on-ice, e.g., 1
        dzfl (float):
            Sum of defensive zone faceoffs lost while player is on-ice, e.g., 0
        pent0 (float):
            Sum of individual 0-minute penalties taken while player is on-ice, e.g., 0
        pent2 (float):
            Sum of individual 2-minute penalties taken while player is on-ice, e.g., 0
        pent4 (float):
            Sum of individual 4-minute penalties taken while player is on-ice, e.g., 0
        pent5 (float):
            Sum of individual 5-minute penalties taken while player is on-ice, e.g., 0
        pent10 (float):
            Sum of individual 10-minute penalties taken while player is on-ice, e.g., 0
        pend0 (float):
            Sum of individual 0-minute penalties drawn while player is on-ice, e.g., 0
        pend2 (float):
            Sum of individual 2-minute penalties drawn while player is on-ice, e.g., 0
        pend4 (float):
            Sum of individual 4-minute penalties drawn while player is on-ice, e.g., 0
        pend5 (float):
            Sum of individual 5-minute penalties drawn while player is on-ice, e.g., 0
        pend10 (float):
            Sum of individual 10-minute penalties drawn while player is on-ice, e.g., 0

    Examples:
        Basic play-by-play DataFrame
        >>> shifts_raw = pd.read_csv("./raw_shifts.csv")
        >>> pbp_raw = pd.read_csv("./raw_pbp.csv")
        >>> pbp = prep_pbp(pbp_raw, shifts_raw)

        Basic game-level stats, with no teammates or opposition
        >>> stats = prep_stats(pbp)

        Period-level stats, grouped by teammates
        >>> stats = prep_stats(pbp, level="period", teammates=True)

        Session-level (e.g., regular seasion) stats, grouped by teammates and opposition
        >>> stats = prep_stats(pbp, level="session", teammates=True, opposition=True)

    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        pbar_message = "Prepping stats data..."

        stats_task = progress.add_task(pbar_message, total=1)

        ind = prep_ind(pbp, level, score, teammates, opposition)

        oi = prep_oi(pbp, level, score, teammates, opposition)

        zones = prep_zones(pbp, level, score, teammates, opposition)

        merge_cols = [
            "season",
            "session",
            "game_id",
            "game_date",
            "player",
            "player_id",
            "position",
            "team",
            "opp_team",
            "strength_state",
            "score_state",
            "game_period",
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
        ]

        merge_cols = [x for x in merge_cols if x in ind.columns and x in oi.columns and x in zones.columns]

        stats = oi.merge(ind, how="left", left_on=merge_cols, right_on=merge_cols).fillna(0)

        stats = stats.merge(zones, how="left", left_on=merge_cols, right_on=merge_cols).fillna(0)

        stats = stats.loc[stats.toi > 0].reset_index(drop=True).copy()

        columns = [x for x in StatSchema.dtypes if x in stats.columns]

        stats = StatSchema.validate(stats[columns])

        pbar_message = "Finished prepping stats data"

        progress.update(stats_task, description=pbar_message, advance=1, refresh=True)

    return stats


# Function to prep the lines data
def prep_lines(
    pbp: pd.DataFrame,
    position: Literal["f", "d"] = "f",
    level: Literal["period", "game", "session", "season"] = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
    disable_progress_bar: bool = False,
):
    """Prepares a line stats dataframe using EvolvingHockey data.

    Aggregates to desired level. Capable of returning cuts that account for strength state,
    period, score state, teammates, and opposition.

    Returns a Pandas DataFrame.

    Parameters:
        pbp (pd.DataFrame):
            Dataframe from the prep_pbp function with the default columns argument
        position (str):
            Position to aggregate, forwards or defense, e.g., 'f'
        level (str):
            Level to aggregate stats, e.g., 'game'
        score (bool):
            Whether to aggregate to score state level
        teammates (bool):
            Whether to account for teammates when aggregating
        opposition (bool):
            Whether to account for opposition when aggregating
        disable_progress_bar (bool):
            Whether to disable progress bar

    Returns:
        season (int):
            8-digit season code, e.g., 20232024
        session (str):
            Regular season or playoffs, e.g., R
        game_id (int):
            10-digit game identifier, e.g., 2023020015
        game_date (str):
            Date of game in Eastern time-zone, e.g., 2023-10-12
        team (str):
            3-letter abbreviation of the line's team, e.g., NSH
        opp_team (str):
            3-letter abbreviation of the opposing team, e.g., SEA
        strength_state (str):
            Strength state from the perspective of the event team, e.g., 5v5
        score_state (str):
            Score state from the perspective of the event team, e.g., 0v0
        game_period (int):
            Game period, e.g., 1
        forwards (str):
            Names of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
        forwards_id (str):
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY
        defense (str):
            Names of the event team's defensemen that are on the ice during the event,
            e.g., ALEX.CARRIER, RYAN.MCDONAGH
        defense_id (str):
            EH IDs of the event team's defensemen that are on the ice during the event,
            e.g., ALEX.CARRIER, RYAN.MCDONAGH
        own_goalie (str):
            Name of the goalie for the event team, e.g., JUUSE.SAROS
        own_goalie_id (str):
            Identifier for the event team goalie that can be used to match with Evolving Hockey data, e.g., JUUSE.SAROS
        opp_forwards (str):
            Names of the opponent's forwards that are on the ice during the event,
            e.g., JARED.MCCANN, JORDAN.EBERLE, MATTY.BENIERS
        opp_forwards_id (str):
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., JARED.MCCANN, JORDAN.EBERLE, MATTY.BENIERS
        opp_defense (str):
            Names of the opposing team's defensemen that are on the ice during the event,
            e.g., JAMIE.OLEKSIAK, WILLIAM.BORGEN
        opp_defense_id (str):
            EH IDs of the opposing team's defensemen that are on the ice during the event,
            e.g., JAMIE.OLEKSIAK, WILLIAM.BORGEN
        opp_goalie (str):
            Name of the opposing goalie for the event team, e.g., PHILIPP.GRUBAUER
        opp_goalie_id (str):
            Identifier for the opposing goalie that can be used to match with Evolving Hockey data,
            e.g., PHILIPP.GRUBAUER
        toi (float):
            Time on-ice in minutes, e.g., 1.616667
        gf (float):
            Sum of goals scored while line is on-ice, e.g., 0
        gf_adj (float):
            Sum of venue- and score-adjusted goals scored while line is on-ice, e.g., 0
        hdgf (float):
            Sum of high-danger goals scored while line is on-ice, e.g., 0
        ga (float):
            Sum of goals allowed while line is on-ice, e.g., 0
        ga_adj (float):
            Sum of venue- and score-adjusted goals allowed while line is on-ice, e.g., 0
        hdga (float):
            Sum of high-danger goals allowed while line is on-ice, e.g., 0
        xgf (float):
            Sum of expected goals generated while line is on-ice, e.g., 0.017266
        xgf_adj (float):
            Sum of venue- and score-adjusted expected goals generated while line is on-ice, e.g., 0.016472
        xga (float):
            Sum of expected goals allowed while line is on-ice, e.g., 0.123475
        xga_adj (float):
            Sum of venue- and score-adjusted expected goals allowed while line is on-ice, e.g., 0.129772
        sf (float):
            Sum of shots taken while line is on-ice, e.g., 1
        sf_adj (float):
            Sum of venue- and score-adjusted shots taken while line is on-ice, e.g., .972
        hdsf (float):
            Sum of high-danger shots taken while line is on-ice, e.g., 0
        sa (float):
            Sum of shots allowed while line is on-ice, e.g., 0
        sa_adj (float):
            Sum of venue- and score-adjusted shots allowed while line is on-ice, e.g., 0
        hdsa (float):
            Sum of high-danger shots allowed while line is on-ice, e.g., 0
        ff (float):
            Sum of fenwick events generated while line is on-ice, e.g., 1
        ff_adj (float):
            Sum of venue- and score-adjusted fenwick events generated while line is on-ice, e.g., 0.968
        hdff (float):
            Sum of high-danger fenwick events generated while line is on-ice, e.g., 0
        fa (float):
            Sum of fenwick events allowed while line is on-ice, e.g., 1
        fa_adj (float):
            Sum of venue- and score-adjusted fenwick events allowed while line is on-ice, e.g., 1.034
        hdfa (float):
            Sum of high-danger fenwick events allowed while line is on-ice, e.g., 1
        cf (float):
            Sum of corsi events generated while line is on-ice, e.g., 1
        cf_adj (float):
            Sum of venue- and score-adjusted corsi events generated while line is on-ice, e.g., 0.970
        ca (float):
            Sum of corsi events allowed while line is on-ice, e.g., 2
        ca_adj (float):
            Sum of venue- and score-adjusted corsi events allowed while line is on-ice, e.g., 2.064
        bsf (float):
            Sum of shots taken that were ultimately blocked while line is on-ice, e.g., 0
        bsa (float):
            Sum of shots allowed that were ultimately blocked while line is on-ice, e.g., 1
        msf (float):
            Sum of shots taken that missed net while line is on-ice, e.g., 0
        hdmsf (float):
            Sum of high-danger shots taken that missed net while line is on-ice, e.g., 0
        msa (float):
            Sum of shots allowed that missed net while line is on-ice, e.g., 1
        hdmsa (float):
            Sum of high-danger shots allowed that missed net while line is on-ice, e.g., 1
        hf (float):
            Sum of hits dished out while line is on-ice, e.g., 0
        ht (float):
            Sum of hits taken while line is on-ice, e.g., 0
        ozf (float):
            Sum of offensive zone faceoffs that occur while line is on-ice, e.g., 0
        nzf (float):
            Sum of neutral zone faceoffs that occur while line is on-ice, e.g., 0
        dzf (float):
            Sum of defensive zone faceoffs that occur while line is on-ice, e.g., 1
        fow (float):
            Sum of faceoffs won while line is on-ice, e.g., 1
        fol (float):
            Sum of faceoffs lost while line is on-ice, e.g., 0
        ozfw (float):
            Sum of offensive zone faceoffs won while line is on-ice, e.g., 0
        ozfl (float):
            Sum of offensive zone faceoffs lost while line is on-ice, e.g., 1
        nzfw (float):
            Sum of neutral zone faceoffs won while line is on-ice, e.g., 0
        nzfl (float):
            Sum of neutral zone faceoffs lost while line is on-ice, e.g., 0
        dzfw (float):
            Sum of defensive zone faceoffs won while line is on-ice, e.g., 1
        dzfl (float):
            Sum of defensive zone faceoffs lost while line is on-ice, e.g., 0
        pent0 (float):
            Sum of individual 0-minute penalties taken while line is on-ice, e.g., 0
        pent2 (float):
            Sum of individual 2-minute penalties taken while line is on-ice, e.g., 0
        pent4 (float):
            Sum of individual 4-minute penalties taken while line is on-ice, e.g., 0
        pent5 (float):
            Sum of individual 5-minute penalties taken while line is on-ice, e.g., 0
        pent10 (float):
            Sum of individual 10-minute penalties taken while line is on-ice, e.g., 0
        pend0 (float):
            Sum of individual 0-minute penalties drawn while line is on-ice, e.g., 0
        pend2 (float):
            Sum of individual 2-minute penalties drawn while line is on-ice, e.g., 0
        pend4 (float):
            Sum of individual 4-minute penalties drawn while line is on-ice, e.g., 0
        pend5 (float):
            Sum of individual 5-minute penalties drawn while line is on-ice, e.g., 0
        pend10 (float):
            Sum of individual 10-minute penalties drawn while line is on-ice, e.g., 0

    Examples:
        Basic play-by-play DataFrame
        >>> shifts_raw = pd.read_csv("./raw_shifts.csv")
        >>> pbp_raw = pd.read_csv("./raw_pbp.csv")
        >>> pbp = prep_pbp(pbp_raw, shifts_raw)

        Basic game-level stats for forwards, with no teammates or opposition
        >>> lines = prep_lines(pbp, position="f")

        Period-level stats for defense, grouped by teammates
        >>> lines = prep_lines(pbp, position="d", level="period", teammates=True)

        Session-level (e.g., regular seasion) stats, grouped by teammates and opposition
        >>> lines = prep_lines(pbp, position="f", level="session", teammates=True, opposition=True)

    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        pbar_message = "Prepping lines data..."

        lines_task = progress.add_task(pbar_message, total=1)

        # Creating the "for" dataframe

        # Accounting for desired level of aggregation

        if level == "session" or level == "season":
            group_base = ["season", "session", "event_team", "strength_state"]

        if level == "game":
            group_base = ["season", "game_id", "game_date", "session", "event_team", "opp_team", "strength_state"]

        if level == "period":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "game_period",
                "strength_state",
            ]

        # Accounting for score state

        if score:
            group_base = group_base + ["score_state"]

        # Accounting for desired position

        group_list = group_base + [f"event_on_{position}", f"event_on_{position}_id"]

        # Accounting for teammates

        if teammates:
            if position == "f":
                group_list = group_list + ["event_on_d", "event_on_d_id", "event_on_g", "event_on_g_id"]

            if position == "d":
                group_list = group_list + ["event_on_f", "event_on_f_id", "event_on_g", "event_on_g_id"]

        # Accounting for opposition

        if opposition:
            group_list = group_list + ["opp_on_f", "opp_on_f_id", "opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

            if "opp_team" not in group_list:
                group_list.append("opp_team")

        # Creating dictionary of statistics for the groupby function

        stats = [
            "pred_goal",
            "pred_goal_adj",
            "corsi",
            "corsi_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "miss",
            "block",
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

        agg_stats = {x: "sum" for x in stats if x in pbp.columns}

        # Aggregating the "for" dataframe

        lines_f = pbp.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

        # Creating the dictionary to change column names

        columns = [
            "xgf",
            "xgf_adj",
            "cf",
            "cf_adj",
            "ff",
            "ff_adj",
            "gf",
            "gf_adj",
            "msf",
            "bsf",
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

        columns.update(
            {
                "event_on_f": "forwards",
                "event_on_f_id": "forwards_id",
                "event_team": "team",
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
        )

        # columns = {k: v for k, v in columns.items() if k in lines_f.columns}

        lines_f = lines_f.rename(columns=columns)

        cols = [
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
        ]

        cols = [x for x in cols if x in lines_f]

        for col in cols:
            lines_f[col] = lines_f[col].fillna("EMPTY")

        # Creating the against dataframe

        # Accounting for desired level of aggregation

        if level == "session" or level == "season":
            group_base = ["season", "session", "opp_team", "opp_strength_state"]

        if level == "game":
            group_base = ["season", "game_id", "game_date", "session", "event_team", "opp_team", "opp_strength_state"]

        if level == "period":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "game_period",
                "opp_strength_state",
            ]

        # Accounting for score state

        if score:
            group_base = group_base + ["opp_score_state"]

        # Accounting for desired position

        group_list = group_base + [f"opp_on_{position}", f"opp_on_{position}_id"]

        # Accounting for teammates

        if teammates:
            if position == "f":
                group_list = group_list + ["opp_on_d", "opp_on_d_id", "opp_on_g", "opp_on_g_id"]

            if position == "d":
                group_list = group_list + ["opp_on_f", "opp_on_f_id", "opp_on_g", "opp_on_g_id"]

        # Accounting for opposition

        if opposition:
            group_list = group_list + [
                "event_on_f",
                "event_on_f_id",
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
            ]

            if "event_team" not in group_list:
                group_list.append("event_team")

        # Creating dictionary of statistics for the groupby function

        stats = [
            "pred_goal",
            "pred_goal_adj",
            "corsi",
            "corsi_adj",
            "fenwick",
            "fenwick_adj",
            "goal",
            "goal_adj",
            "miss",
            "block",
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

        agg_stats = {x: "sum" for x in stats if x in pbp.columns}

        # Aggregating "against" dataframe

        lines_a = pbp.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

        # Creating the dictionary to change column names

        columns = [
            "xga",
            "xga_adj",
            "ca",
            "ca_adj",
            "fa",
            "fa_adj",
            "ga",
            "ga_adj",
            "msa",
            "bsa",
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
                "opp_on_f": "forwards",
                "opp_on_f_id": "forwards_id",
                "opp_strength_state": "strength_state",
                "opp_on_d": "defense",
                "opp_on_d_id": "defense_id",
                "event_on_f": "opp_forwards",
                "event_on_f_id": "opp_forwards_id",
                "event_on_d": "opp_defense",
                "event_on_d_id": "opp_defense_id",
                "opp_score_state": "score_state",
                "event_on_g": "opp_goalie",
                "event_on_g_id": "opp_goalie_id",
                "opp_on_g": "own_goalie",
                "opp_on_g_id": "own_goalie_id",
            }
        )

        # columns = {k: v for k, v in columns.items() if k in lines_a.columns}

        lines_a = lines_a.rename(columns=columns)

        cols = [
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
        ]

        cols = [x for x in cols if x in lines_a]

        for col in cols:
            lines_a[col] = lines_a[col].fillna("EMPTY")

        # Merging the "for" and "against" dataframes

        if level == "session" or level == "season":
            if position == "f":
                merge_list = ["season", "session", "team", "strength_state", "forwards", "forwards_id"]

            if position == "d":
                merge_list = ["season", "session", "team", "strength_state", "defense", "defense_id"]

        if level == "game":
            if position == "f":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "forwards",
                    "forwards_id",
                ]

            if position == "d":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "defense",
                    "defense_id",
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
                    "strength_state",
                    "forwards",
                    "forwards_id",
                    "game_period",
                ]

            if position == "d":
                merge_list = [
                    "season",
                    "game_id",
                    "game_date",
                    "session",
                    "team",
                    "opp_team",
                    "strength_state",
                    "defense",
                    "defense_id",
                    "game_period",
                ]

        if score:
            merge_list.append("score_state")

        if teammates:
            if position == "f":
                merge_list = merge_list + ["defense", "defense_id", "own_goalie", "own_goalie_id"]

            if position == "d":
                merge_list = merge_list + ["forwards", "forwards_id", "own_goalie", "own_goalie_id"]

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
                merge_list.insert(3, "opp_team")

        lines = lines_f.merge(lines_a, how="outer", on=merge_list, suffixes=("_x", "")).fillna(0)

        lines.toi = (lines.toi_x + lines.toi) / 60

        lines = lines.drop(columns="toi_x")

        lines["ozf"] = lines.ozfw + lines.ozfl

        lines["nzf"] = lines.nzfw + lines.nzfl

        lines["dzf"] = lines.dzfw + lines.dzfl

        cols = [x for x in LineSchema.dtypes if x in lines.columns]

        lines = lines[cols]

        lines = lines.loc[lines.toi > 0].reset_index(drop=True).copy()

        lines = LineSchema.validate(lines)

        pbar_message = "Finished prepping lines data"

        progress.update(lines_task, description=pbar_message, advance=1, refresh=True)

    return lines


# Function to prep the team stats
def prep_team(
    pbp: pd.DataFrame,
    level: Literal["period", "game", "session", "season"] = "game",
    strengths: bool = True,
    score: bool = False,
    disable_progress_bar: bool = False,
) -> pd.DataFrame:
    """Prepares a team stats dataframe using Evolving Hockey data.

    Aggregates to desired level. Capable of returning cuts that account for strength state,
    period, and score state. Returns a Pandas DataFrame.

    Parameters:
        pbp (pd.DataFrame):
            Dataframe from the prep_pbp function with the default columns argument
        level (str):
            Level to aggregate stats, e.g., 'game'
        strengths (bool):
            Whether to aggregate to strength state level, e.g., True
        score (bool):
            Whether to aggregate to score state level
        disable_progress_bar (bool):
            Whether to disable progress bar

    Returns:
        season (int):
            8-digit season code, e.g., 20232024
        session (str):
            Regular season or playoffs, e.g., R
        game_id (int):
            10-digit game identifier, e.g., 2023020044
        game_date (str):
            Date of game in Eastern time-zone, e.g., 2023-10-17
        team (str):
            3-letter abbreviation of the team, e.g., NSH
        opp_team (str):
            3-letter abbreviation of the opposing team, e.g., EDM
        strength_state (str):
            Strength state from the perspective of the event team, e.g., 5v5
        score_state (str):
            Score state from the perspective of the event team, e.g., 1v6
        game_period (int):
            Game period, e.g., 3
        toi (float):
            Time on-ice in minutes, e.g., 18
        gf (float):
            Sum of goals scored, e.g., 0
        gf_adj (float):
            Sum of venue- and score-adjusted goals scored, e.g., 0
        hdgf (float):
            Sum of high-danger goals scored, e.g., 0
        ga (float):
            Sum of goals allowed, e.g., 0
        ga_adj (float):
            Sum of venue- and score-adjusted goals allowed, e.g., 0
        hdga (float):
            Sum of high-danger goals allowed, e.g., 0
        xgf (float):
            Sum of expected goals generated, e.g., 0.957070
        xgf_adj (float):
            Sum of venue- and score-adjusted expected goals generated, e.g., 0.883376
        xga (float):
            Sum of expected goals allowed, e.g., 0.535971
        xga_adj (float):
            Sum of venue- and score-adjusted expected goals allowed, e.g., 0.584744
        sf (float):
            Sum of shots taken, e.g., 10
        sf_adj (float):
            Sum of venue- and score-adjusted shots taken, e.g., 8.620
        hdsf (float):
            Sum of high-danger shots taken, e.g., 2
        sa (float):
            Sum of shots allowed, e.g., 4
        sa_adj (float):
            Sum of venue- and score-adjusted shots allowed, e.g., 4.764
        hdsa (float):
            Sum of high-danger shots allowed, e.g., 0
        ff (float):
            Sum of fenwick events generated, e.g., 14
        ff_adj (float):
            Sum of venue- and score-adjusted fenwick events generated, e.g., 12.026
        hdff (float):
            Sum of high-danger fenwick events generated, e.g., 2
        fa (float):
            Sum of fenwick events allowed, e.g., 8
        fa_adj (float):
            Sum of venue- and score-adjusted fenwick events allowed, e.g., 9.576
        hdfa (float):
            Sum of high-danger fenwick events allowed, e.g., 1
        cf (float):
            Sum of corsi events generated, e.g., 16
        cf_adj (float):
            Sum of venue- and score-adjusted corsi events generated, e.g., 13.488
        ca (float):
            Sum of corsi events allowed, e.g., 12.0
        ca_adj (float):
            Sum of venue- and score-adjusted corsi events allowed, e.g., 14.760
        bsf (float):
            Sum of shots taken that were ultimately blocked, e.g., 4
        bsa (float):
            Sum of shots allowed that were ultimately blocked, e.g., 2
        msf (float):
            Sum of shots taken that missed net, e.g., 4
        hdmsf (float):
            Sum of high-danger shots taken that missed net, e.g., 0
        msa (float):
            Sum of shots allowed that missed net, e.g., 4
        hdmsa (float):
            Sum of high-danger shots allowed that missed net, e.g., 1
        ozf (float):
            Sum of offensive zone faceoffs that occur, e.g., 6
        nzf (float):
            Sum of neutral zone faceoffs that occur, e.g., 4
        dzf (float):
            Sum of defensive zone faceoffs that occur, e.g., 6
        fow (float):
            Sum of faceoffs won, e.g., 8
        fol (float):
            Sum of faceoffs lost, e.g., 11
        ozfw (float):
            Sum of offensive zone faceoffs won, e.g., 3
        ozfl (float):
            Sum of offensive zone faceoffs lost, e.g., 1
        nzfw (float):
            Sum of neutral zone faceoffs won, e.g., 2
        nzfl (float):
            Sum of neutral zone faceoffs lost, e.g., 3
        dzfw (float):
            Sum of defensive zone faceoffs won, e.g., 3
        dzfl (float):
            Sum of defensive zone faceoffs lost, e.g., 7
        hf (float):
            Sum of hits dished out, e.g., 7
        ht (float):
            Sum of hits taken, e.g., 5
        give (float):
            Sum of giveaways, e.g., 5
        take (float):
            Sum of takeaways, e.g., 1
        pent0 (float):
            Sum of individual 0-minute penalties taken, e.g., 0
        pent2 (float):
            Sum of individual 2-minute penalties taken, e.g., 0
        pent4 (float):
            Sum of individual 4-minute penalties taken, e.g., 0
        pent5 (float):
            Sum of individual 5-minute penalties taken, e.g., 0
        pent10 (float):
            Sum of individual 10-minute penalties taken, e.g., 0
        pend0 (float):
            Sum of individual 0-minute penalties drawn, e.g., 0
        pend2 (float):
            Sum of individual 2-minute penalties drawn, e.g., 0
        pend4 (float):
            Sum of individual 4-minute penalties drawn, e.g., 0
        pend5 (float):
            Sum of individual 5-minute penalties drawn, e.g., 0
        pend10 (float):
            Sum of individual 10-minute penalties drawn, e.g., 0

    Examples:
        Basic play-by-play DataFrame
        >>> shifts_raw = pd.read_csv("./raw_shifts.csv")
        >>> pbp_raw = pd.read_csv("./raw_pbp.csv")
        >>> pbp = prep_pbp(pbp_raw, shifts_raw)

        Basic game-level stats for teams
        >>> team = prep_team(pbp)

        Period-level team stats, grouped by score state
        >>> team = prep_team(pbp, level="period", score=True)
    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        pbar_message = "Prepping team data..."

        team_task = progress.add_task(pbar_message, total=1)

        # Getting the "for" stats

        group_list = ["season", "session", "event_team"]

        if strengths:
            group_list.append("strength_state")

        if level == "game" or level == "period":
            group_list.insert(3, "opp_team")

            group_list[2:2] = ["game_id", "game_date"]

        if level == "period":
            group_list.append("game_period")

        if score:
            group_list.append("score_state")

        agg_stats = [
            "pred_goal",
            "pred_goal_adj",
            "shot",
            "shot_adj",
            "miss",
            "block",
            "corsi",
            "corsi_adj",
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

        agg_dict = {x: "sum" for x in agg_stats if x in pbp.columns}

        new_cols = [
            "xgf",
            "xgf_adj",
            "sf",
            "sf_adj",
            "msf",
            "bsa",
            "cf",
            "cf_adj",
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

        stats_for = pbp.groupby(group_list, as_index=False).agg(agg_dict).rename(columns=new_cols)

        # Getting the "against" stats

        group_list = ["season", "session", "opp_team"]

        if strengths:
            group_list.append("opp_strength_state")

        if level == "game" or level == "period":
            group_list.insert(3, "event_team")

            group_list[2:2] = ["game_id", "game_date"]

        if level == "period":
            group_list.append("game_period")

        if score:
            group_list.append("opp_score_state")

        agg_stats = [
            "pred_goal",
            "pred_goal_adj",
            "shot",
            "shot_adj",
            "miss",
            "block",
            "corsi",
            "corsi_adj",
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

        agg_dict = {x: "sum" for x in agg_stats if x in pbp.columns}

        new_cols = [
            "xga",
            "xga_adj",
            "sa",
            "sa_adj",
            "msa",
            "bsf",
            "ca",
            "ca_adj",
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

        stats_against = pbp.groupby(group_list, as_index=False).agg(agg_dict).rename(columns=new_cols)

        merge_list = [
            "season",
            "session",
            "game_id",
            "game_date",
            "team",
            "opp_team",
            "strength_state",
            "score_state",
            "game_period",
        ]

        merge_list = [x for x in merge_list if x in stats_for.columns and x in stats_against.columns]

        team_stats = stats_for.merge(stats_against, on=merge_list, how="outer")

        team_stats["toi"] = (team_stats.toi_x + team_stats.toi_y) / 60

        team_stats = team_stats.drop(["toi_x", "toi_y"], axis=1)

        fos = ["ozf", "nzf", "dzf"]

        for fo in fos:
            team_stats[fo] = team_stats[f"{fo}w"] + team_stats[f"{fo}w"]

        team_stats = team_stats.dropna(subset="toi").reset_index(drop=True)

        cols = [x for x in team_stats_pandera_pandas.dtypes if x in team_stats.columns]

        team_stats = team_stats_pandera_pandas.validate(team_stats[cols])

        pbar_message = "Finished prepping team data"

        progress.update(team_task, description=pbar_message, advance=1, refresh=True)

    return team_stats


# Function to prep the GAR dataframe
def prep_gar(skater_data: pd.DataFrame, goalie_data: pd.DataFrame) -> pd.DataFrame:
    """Prepares a dataframe of GAR stats using Evolving Hockey data.

    Experimental and not actively maintained

    Parameters:
        skater_data (pd.DataFrame):
            Pandas Dataframe loaded from a CSV file from Evolving Hockey website
        goalie_data (pd.DataFrame):
            Pandas Dataframe loaded from a CSV file from Evolving Hockey website

    """
    gar = pd.concat([skater_data, goalie_data], ignore_index=True)

    new_cols = {x: x.replace(" ", "_").lower() for x in gar.columns}

    gar = gar.rename(columns=new_cols)

    season_split = gar.season.str.split("-", expand=True)

    gar.season = "20" + season_split[0] + "20" + season_split[1]

    gar.birthday = pd.to_datetime(gar.birthday)

    gar.player = gar.player.str.upper()

    gar.eh_id = gar.eh_id.str.replace("..", ".", regex=False)

    replace_teams = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}

    gar.team = gar.team.map(replace_teams).fillna(gar.team)

    gar = gar.rename(columns={"eh_id": "player_id"})

    return gar


# Function to prep the xGAR dataframe
def prep_xgar(data: pd.DataFrame) -> pd.DataFrame:
    """Prepares a dataframe of xGAR stats using Evolving Hockey data.

    Experimental and not actively maintained

    Parameters:
        data (pd.DataFrame):
            Pandas Dataframe loaded from a CSV file from Evolving Hockey website

    """
    xgar = data.copy()

    new_cols = {x: x.replace(" ", "_").lower() for x in xgar.columns}

    xgar = xgar.rename(columns=new_cols)

    season_split = xgar.season.str.split("-", expand=True)

    xgar.season = "20" + season_split[0] + "20" + season_split[1]

    xgar.birthday = pd.to_datetime(xgar.birthday)

    xgar.player = xgar.player.str.upper()

    xgar.eh_id = xgar.eh_id.str.replace("..", ".", regex=False)

    replace_teams = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}

    xgar.team = xgar.team.map(replace_teams).fillna(xgar.team)

    xgar = xgar.rename(columns={"eh_id": "player_id"})

    return xgar
