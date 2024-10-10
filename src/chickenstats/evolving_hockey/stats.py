import pandas as pd

from typing import Literal

from chickenstats.evolving_hockey.base import (
    munge_pbp,
    munge_rosters,
    add_positions,
    prep_ind,
    prep_oi,
    prep_zones,
)

from chickenstats.evolving_hockey.validation import PBPSchema, StatSchema, LineSchema

from chickenstats.chicken_nhl.validation import TeamStatSchema

from chickenstats.utilities.utilities import ChickenProgress


def prep_pbp(
    pbp: pd.DataFrame | list[pd.DataFrame],
    shifts: pd.DataFrame | list[pd.DataFrame],
    columns: Literal["light", "full", "all"] = "full",
    disable_progress_bar: bool = False,
) -> pd.DataFrame:
    """Prepares a play-by-play dataframe using EvolvingHockey data, but with additional stats and information.

    Columns keyword argument determines information returned. Used in later aggregation
    functions. Returns a DataFrame.

    Parameters:
        pbp (pd.DataFrame):
            Pandas DataFrame of CSV file downloaded from play-by-play query tool at evolving-hockey.com
        shifts (pd.DataFrame):
            Pandas DataFrame of CSV file downloaded from shifts query tool at evolving-hockey.com
        columns (str):
            Whether to return additional columns or more sparse play-by-play dataframe
        disable_progress_bar (bool):
            Whether to disable progress bar

    Returns:
        season (int):
            8-digit season code, e.g., 20192020
        session (str):
            Regular season or playoffs, e.g., R
        game_id (int):
            10-digit game identifier, e.g., 2019020684
        game_date (str):
            Date of game in Eastern time-zone, e.g., 2020-01-09
        event_index (int):
            Unique index number of event, in chronological order, e.g.,
        game_period (int):
            Game period, e.g., 3
        game_seconds (int):
            Game time elapsed in seconds, e.g., 3578
        period_seconds (int):
            Period time elapsed in seconds, e.g., 1178
        clock_time (str):
            Time shown on clock, e.g., 0:22
        strength_state (str):
            Strength state from the perspective of the event team, e.g., 5vE
        score_state (str):
            Score state from the perspective of the event team, e.g., 5v2
        event_type (str):
            Name of the event, e.g., GOAL
        event_description (str):
            Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
        event_detail (str | None):
            Additional information about the event, e.g., Wrist
        event_zone (str | None):
            Zone location of event, e.g., DEF
        event_team (str | None):
            3-letter abbreviation of the team for the event, e.g., NSH
        opp_team (str | None):
            3-letter abbreviation of the opposing team for the event, e.g., CHI
        is_home (int | None):
            Dummy variable to signify whether event team is home team, e.g., 0
        coords_x (int | None):
            X coordinates of event, e.g., -96
        coords_y (int | None):
            Y coordinates of event, e.g., 11
        event_player_1 (str):
            Name of the first event player, e.g., PEKKA.RINNE
        event_player_1_id (str):
            Identifier that can be used to match with Evolving Hockey data, e.g., PEKKA.RINNE
        event_player_1_pos (str):
            Player's position for the game, may differ from primary position, e.g., G
        event_player_2 (str):
            Name of the second event player
        event_player_2_id (str):
            Identifier that can be used to match with Evolving Hockey data
        event_player_2_pos (str):
            Player's position for the game, may differ from primary position
        event_player_3 (str):
            Name of the third event player
        event_player_3_id (str):
            Identifier that can be used to match with Evolving Hockey data
        event_player_3_pos (str):
            Player's position for the game, may differ from primary position
        event_length (int):
            Length of time elapsed in seconds since previous event, e.g., 5
        high_danger (int):
            Whether shot event is from high-danger area, e.g., 0
        danger (int):
            Whether shot event is from danger area,
            exclusive of high-danger area, e.g., 0
        pbp_distance (float):
            Distance from opponent net, in feet, according to play-by-play description, e.g., 185.0
        event_distance (float):
            Distance from opponent net, in feet, e.g., 185.326738
        event_angle (float):
            Angle of opponent's net from puck, in degrees, e.g., 57.528808
        opp_strength_state (str):
            Strength state from the perspective of the opposing team, e.g., Ev5
        opp_score_state (str):
            Score state from the perspective of the opposing team, e.g., 2v5
        event_on_f (str):
            Names of the event team's forwards that are on the ice during the event,
            e.g., NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
        event_on_f_id (str):
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
        event_on_d (str):
            Names of the event team's defensemen that are on the ice during the event,
            e.g., MATTIAS EKHOLM, ROMAN JOSI
        event_on_d_id (str):
            EH IDs of the event team's defensemen that are on the ice during the event,
            e.g., MATTIAS.EKHOLM, ROMAN.JOSI
        event_on_g (str):
            Name of the goalie for the event team, e.g., PEKKA RINNE
        event_on_g_id (str):
            Identifier for the event team goalie that can be used to match with Evolving Hockey data, e.g., PEKKA.RINNE
        event_on_1 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., CALLE.JARNKROK
        event_on_1_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., CALLE.JARNKROK
        event_on_1_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., C
        event_on_2 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., MATTIAS.EKHOLM
        event_on_2_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., MATTIAS.EKHOLM
        event_on_2_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., D
        event_on_3 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., MIKAEL.GRANLUND
        event_on_3_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., MIKAEL.GRANLUND
        event_on_3_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., C
        event_on_4 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., NICK.BONINO
        event_on_4_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., NICK.BONINO
        event_on_4_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., C
        event_on_5 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., PEKKA.RINNE
        event_on_5_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., PEKKA.RINNE
        event_on_5_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., G
        event_on_6 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., ROMAN.JOSI
        event_on_6_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., ROMAN.JOSI
        event_on_6_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., D
        event_on_7 (str):
            Name of one the event team's players that are on the ice during the event,
            e.g., NaN
        event_on_7_id (str):
            EH ID of one the event team's players that are on the ice during the event,
            e.g., NaN
        event_on_7_pos (str):
            Position of one the event team's players that are on the ice during the event,
            e.g., NaN
        opp_on_f (str):
            Names of the opponent's forwards that are on the ice during the event,
            e.g., ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
        opp_on_f_id (str):
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
        opp_on_d (str):
            Names of the opposing team's defensemen that are on the ice during the event,
            e.g., DUNCAN KEITH, ERIK GUSTAFSSON
        opp_on_d_id (str):
            EH IDs of the opposing team's defensemen that are on the ice during the event,
            e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
        opp_on_g (str):
            Name of the opposing goalie for the event team, e.g., EMPTY NET
        opp_on_g_id (str):
            Identifier for the opposing goalie that can be used to match with Evolving Hockey data, e.g., EMPTY NET
        opp_on_1 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., ALEX.DEBRINCAT
        opp_on_1_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., ALEX.DEBRINCAT
        opp_on_1_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., R
        opp_on_2 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., DUNCAN.KEITH
        opp_on_2_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., DUNCAN.KEITH
        opp_on_2_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., D
        opp_on_3 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., ERIK.GUSTAFSSON2
        opp_on_3_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., ERIK.GUSTAFSSON2
        opp_on_3_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., D
        opp_on_4 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., JONATHAN.TOEWS
        opp_on_4_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., JONATHAN.TOEWS
        opp_on_4_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., C
        opp_on_5 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., KIRBY.DACH
        opp_on_5_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., KIRBY.DACH
        opp_on_5_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., C
        opp_on_6 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., PATRICK.KANE
        opp_on_6_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., PATRICK.KANE
        opp_on_6_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., R
        opp_on_7 (str):
            Name of one the opposing team's players that are on the ice during the event,
            e.g., NaN
        opp_on_7_id (str):
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g., NaN
        opp_on_7_pos (str):
            Position of one the opposing team's players that are on the ice during the event,
            e.g., NaN
        change (int):
            Dummy variable to indicate whether event is a change, e.g., 0
        zone_start (str):
            Zone where the changed, e.g., OFF or OTF
        num_on (int | None):
            Number of players entering the ice, e.g., 6
        num_off (int | None):
            Number of players exiting the ice, e.g., 0
        players_on (str):
            Names of players on, in jersey order,
            e.g., FILIP FORSBERG, ALEX CARRIER, ROMAN JOSI, MIKAEL GRANLUND, JUUSE SAROS, MATT DUCHENE
        players_on_id (str):
            Evolving Hockey IDs of players on, in jersey order,
            e.g., FILIP.FORSBERG, ALEX.CARRIER, ROMAN.JOSI, MIKAEL.GRANLUND, JUUSE.SAROS, MATT.DUCHENE
        players_on_pos (str):
            Positions of players on, in jersey order,
            e.g., L, D, D, C, G, C
        players_off (str):
            Names of players off, in jersey order
        players_off_id (str):
            Evolving Hockey IDs of players off, in jersey order
        players_off_pos (str):
            Positions of players off, in jersey order
        shot (int):
            Dummy variable to indicate whether event is a shot, e.g., 1
        shot_adj (float):
            Score and venue-adjusted shot value, e.g., 0
        goal (int):
            Dummy variable to indicate whether event is a goal, e.g., 1
        goal_adj (float):
            Score and venue-adjusted shot value, e.g., 0
        pred_goal (float):
            Predicted goal value (xG), e.g., 0.482589
        pred_goal_adj (float):
            Score and venue-adjusted predicted goal (xG) value, e.g., 0
        miss (int):
            Dummy variable to indicate whether event is a missed shot, e.g., 0
        block (int):
            Dummy variable to indicate whether event is a block, e.g., 0
        corsi (int):
            Dummy variable to indicate whether event is a corsi event, e.g., 1
        corsi_adj (float):
            Score and venue-adjusted corsi value, e.g., 0
        fenwick (int):
            Dummy variable to indicate whether event is a fenwick event, e.g., 1
        fenwick_adj (float):
             Score and venue-adjusted fenwick value, e.g., 0
        hd_shot (int):
            Dummy variable to indicate whether event is a high-danger shot event, e.g., 0
        hd_goal (int):
            Dummy variable to indicate whether event is a high-danger goal event, e.g., 0
        hd_miss (int):
            Dummy variable to indicate whether event is a high-danger miss event, e.g., 0
        hd_fenwick (int):
            Dummy variable to indicate whether event is a high-danger fenwick event, e.g., 0
        fac (int):
            Dummy variable to indicate whether event is a faceoff, e.g., 0
        hit (int):
            Dummy variable to indicate whether event is a hit, e.g., 0
        give (int):
            Dummy variable to indicate whether event is a giveaway, e.g., 0
        take (int):
            Dummy variable to indicate whether event is a takeaway, e.g., 0
        pen0 (int):
            Dummy variable to indicate whether event is a penalty with no minutes, e.g., 0
        pen2 (int):
            Dummy variable to indicate whether event is a two-minute penalty, e.g., 0
        pen4 (int):
            Dummy variable to indicate whether event is a four-minute penalty, e.g., 0
        pen5 (int):
            Dummy variable to indicate whether event is a five-minute penalty, e.g., 0
        pen10 (int):
            Dummy variable to indicate whether event is a ten-minute penalty, e.g., 0
        stop (int):
            Dummy variable to indicate whether event is a stoppage, e.g., 0
        ozf (int):
            Dummy variable to indicate whether event is an offensive zone faceoff e.g., 0
        nzf (int):
            Dummy variable to indicate whether event is a neutral zone faceoff, e.g., 0
        dzf (int):
            Dummy variable to indicate whether event is a defensive zone faceoff, e.g., 0
        ozs (int):
            Dummy variable to indicate whether an event is an offensive zone change, e.g., 0
        nzs (int):
            Dummy variable to indicate whether an event is a neutral zone change, e.g., 0
        dzs (int):
            Dummy variable to indicate whether an event is an defensive zone change, e.g., 0
        otf (int):
            Dummy variable to indicate whether an event is an on-the-fly change, e.g., 0

    Examples:
        Play-by-play DataFrame
        >>> shifts_raw = pd.read_csv("./raw_shifts.csv")
        >>> pbp_raw = pd.read_csv("./raw_pbp.csv")
        >>> pbp = prep_pbp(pbp_raw, shifts_raw)

    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        if isinstance(pbp, pd.DataFrame):
            progress_total = 1

            pbp = [pbp]

        elif isinstance(pbp, list):
            progress_total = len(pbp)

        if isinstance(shifts, pd.DataFrame):
            shifts = [shifts]

        if len(pbp) != len(shifts):
            raise Exception("Number of play-by-play and shift CSV files does not match")

        pbar_message = "Prepping play-by-play data..."

        csv_task = progress.add_task(pbar_message, total=progress_total)

        pbp_concat = []

        for idx, (pbp_raw, shifts_raw) in enumerate(zip(pbp, shifts)):
            rosters = munge_rosters(shifts_raw)

            pbp_clean = munge_pbp(pbp_raw)

            pbp_clean = add_positions(pbp_clean, rosters)

            cols = [
                "id",
                "season",
                "session",
                "game_id",
                "game_date",
                "event_index",
                "game_period",
                "game_seconds",
                "period_seconds",
                "clock_time",
                "strength_state",
                "score_state",
                "event_type",
                "event_description",
                "event_detail",
                "event_zone",
                "event_team",
                "opp_team",
                "is_home",
                "coords_x",
                "coords_y",
                "event_player_1",
                "event_player_1_id",
                "event_player_1_pos",
                "event_player_2",
                "event_player_2_id",
                "event_player_2_pos",
                "event_player_3",
                "event_player_3_id",
                "event_player_3_pos",
                "event_length",
                "high_danger",
                "danger",
                "pbp_distance",
                "event_distance",
                "event_angle",
                "event_on_f",
                "event_on_f_id",
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
                "opp_on_f",
                "opp_on_f_id",
                "opp_on_d",
                "opp_on_d_id",
                "opp_on_g",
                "opp_on_g_id",
                "change",
                "zone_start",
                "num_on",
                "num_off",
                "players_on",
                "players_on_id",
                "players_on_pos",
                "players_off",
                "players_off_id",
                "players_off_pos",
                "shot",
                "shot_adj",
                "goal",
                "goal_adj",
                "pred_goal",
                "pred_goal_adj",
                "miss",
                "block",
                "corsi",
                "corsi_adj",
                "fenwick",
                "fenwick_adj",
                "hd_shot",
                "hd_goal",
                "hd_miss",
                "hd_fenwick",
                "fac",
                "hit",
                "give",
                "take",
                "pen0",
                "pen2",
                "pen4",
                "pen5",
                "pen10",
                "stop",
                "ozf",
                "nzf",
                "dzf",
                "ozs",
                "nzs",
                "dzs",
                "otf",
            ]

            if columns in ["full", "all"]:
                event_cols = [
                    "event_on_1",
                    "event_on_1_id",
                    "event_on_1_pos",
                    "event_on_2",
                    "event_on_2_id",
                    "event_on_2_pos",
                    "event_on_3",
                    "event_on_3_id",
                    "event_on_3_pos",
                    "event_on_4",
                    "event_on_4_id",
                    "event_on_4_pos",
                    "event_on_5",
                    "event_on_5_id",
                    "event_on_5_pos",
                    "event_on_6",
                    "event_on_6_id",
                    "event_on_6_pos",
                    "event_on_7",
                    "event_on_7_id",
                    "event_on_7_pos",
                ]

                event_pos = cols.index("event_on_g_id") + 1

                cols[event_pos:event_pos] = event_cols

                opp_cols = [
                    "opp_on_1",
                    "opp_on_1_id",
                    "opp_on_1_pos",
                    "opp_on_2",
                    "opp_on_2_id",
                    "opp_on_2_pos",
                    "opp_on_3",
                    "opp_on_3_id",
                    "opp_on_3_pos",
                    "opp_on_4",
                    "opp_on_4_id",
                    "opp_on_4_pos",
                    "opp_on_5",
                    "opp_on_5_id",
                    "opp_on_5_pos",
                    "opp_on_6",
                    "opp_on_6_id",
                    "opp_on_6_pos",
                    "opp_on_7",
                    "opp_on_7_id",
                    "opp_on_7_pos",
                ]

                opp_pos = cols.index("opp_on_g_id") + 1

                cols[opp_pos:opp_pos] = opp_cols

                other_cols = ["opp_strength_state", "opp_score_state"]

                other_pos = cols.index("event_angle") + 1

                cols[other_pos:other_pos] = other_cols

            if columns == "all":
                more_cols = [
                    "home_zone",
                    "home_team",
                    "away_team",
                    "home_goalie",
                    "away_goalie",
                    "home_skaters",
                    "away_skaters",
                    "home_score",
                    "away_score",
                    "home_zonestart",
                    "face_index",
                    "pen_index",
                    "shift_index",
                    "game_score_state",
                    "game_strength_state",
                ]

                pos = cols.index("is_home") + 1

                cols[pos:pos] = more_cols

            cols = [x for x in cols if x in pbp_clean]

            pbp_clean = pbp_clean[cols]

            cols = [x for x in list(PBPSchema.dtypes.keys()) if x in pbp_clean.columns]

            pbp_clean = PBPSchema.validate(pbp_clean[cols])

            pbp_concat.append(pbp_clean)

            if progress_total == 1 or idx + 1 == progress_total:
                pbp_clean = pd.concat(pbp_concat, ignore_index=True)

                pbar_message = "Finished loading play-by-play data"

            progress.update(csv_task, description=pbar_message, advance=1, refresh=True)

    return pbp_clean


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

        merge_cols = [
            x
            for x in merge_cols
            if x in ind.columns and x in oi.columns and x in zones.columns
        ]

        stats = oi.merge(
            ind, how="left", left_on=merge_cols, right_on=merge_cols
        ).fillna(0)

        stats = stats.merge(
            zones, how="left", left_on=merge_cols, right_on=merge_cols
        ).fillna(0)

        stats = stats.loc[stats.toi > 0].reset_index(drop=True).copy()

        columns = [x for x in StatSchema.dtypes.keys() if x in stats.columns]

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
        >>> lines = prep_lines(
        ...     pbp, position="f", level="session", teammates=True, opposition=True
        ... )

    """
    with ChickenProgress(disable=disable_progress_bar) as progress:
        pbar_message = "Prepping lines data..."

        lines_task = progress.add_task(pbar_message, total=1)

        # Creating the "for" dataframe

        # Accounting for desired level of aggregation

        if level == "session" or level == "season":
            group_base = ["season", "session", "event_team", "strength_state"]

        if level == "game":
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "strength_state",
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
                "strength_state",
            ]

        # Accounting for score state

        if score is True:
            group_base = group_base + ["score_state"]

        # Accounting for desired position

        group_list = group_base + [f"event_on_{position}", f"event_on_{position}_id"]

        # Accounting for teammates

        if teammates is True:
            if position == "f":
                group_list = group_list + [
                    "event_on_d",
                    "event_on_d_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

            if position == "d":
                group_list = group_list + [
                    "event_on_f",
                    "event_on_f_id",
                    "event_on_g",
                    "event_on_g_id",
                ]

        # Accounting for opposition

        if opposition is True:
            group_list = group_list + [
                "opp_on_f",
                "opp_on_f_id",
                "opp_on_d",
                "opp_on_d_id",
                "opp_on_g",
                "opp_on_g_id",
            ]

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

        columns = dict(zip(stats, columns))

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
            group_base = [
                "season",
                "game_id",
                "game_date",
                "session",
                "event_team",
                "opp_team",
                "opp_strength_state",
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
                "opp_strength_state",
            ]

        # Accounting for score state

        if score is True:
            group_base = group_base + ["opp_score_state"]

        # Accounting for desired position

        group_list = group_base + [f"opp_on_{position}", f"opp_on_{position}_id"]

        # Accounting for teammates

        if teammates is True:
            if position == "f":
                group_list = group_list + [
                    "opp_on_d",
                    "opp_on_d_id",
                    "opp_on_g",
                    "opp_on_g_id",
                ]

            if position == "d":
                group_list = group_list + [
                    "opp_on_f",
                    "opp_on_f_id",
                    "opp_on_g",
                    "opp_on_g_id",
                ]

        # Accounting for opposition

        if opposition is True:
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

        columns = dict(zip(stats, columns))

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
                merge_list = [
                    "season",
                    "session",
                    "team",
                    "strength_state",
                    "forwards",
                    "forwards_id",
                ]

            if position == "d":
                merge_list = [
                    "season",
                    "session",
                    "team",
                    "strength_state",
                    "defense",
                    "defense_id",
                ]

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

        if score is True:
            merge_list.append("score_state")

        if teammates is True:
            if position == "f":
                merge_list = merge_list + [
                    "defense",
                    "defense_id",
                    "own_goalie",
                    "own_goalie_id",
                ]

            if position == "d":
                merge_list = merge_list + [
                    "forwards",
                    "forwards_id",
                    "own_goalie",
                    "own_goalie_id",
                ]

        if opposition is True:
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

        lines = lines_f.merge(
            lines_a, how="outer", on=merge_list, suffixes=("_x", "")
        ).fillna(0)

        lines.toi = (lines.toi_x + lines.toi) / 60

        lines = lines.drop(columns="toi_x")

        lines["ozf"] = lines.ozfw + lines.ozfl

        lines["nzf"] = lines.nzfw + lines.nzfl

        lines["dzf"] = lines.dzfw + lines.dzfl

        cols = [x for x in LineSchema.dtypes.keys() if x in lines.columns]

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

        if strengths is True:
            group_list.append("strength_state")

        if level == "game" or level == "period":
            group_list.insert(3, "opp_team")

            group_list[2:2] = ["game_id", "game_date"]

        if level == "period":
            group_list.append("game_period")

        if score is True:
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

        new_cols = dict(zip(agg_stats, new_cols))

        new_cols.update({"event_team": "team"})

        stats_for = (
            pbp.groupby(group_list, as_index=False)
            .agg(agg_dict)
            .rename(columns=new_cols)
        )

        # Getting the "against" stats

        group_list = ["season", "session", "opp_team"]

        if strengths is True:
            group_list.append("opp_strength_state")

        if level == "game" or level == "period":
            group_list.insert(3, "event_team")

            group_list[2:2] = ["game_id", "game_date"]

        if level == "period":
            group_list.append("game_period")

        if score is True:
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

        new_cols = dict(zip(agg_stats, new_cols))

        new_cols.update(
            {
                "opp_team": "team",
                "opp_score_state": "score_state",
                "opp_strength_state": "strength_state",
                "event_team": "opp_team",
            }
        )

        stats_against = (
            pbp.groupby(group_list, as_index=False)
            .agg(agg_dict)
            .rename(columns=new_cols)
        )

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

        merge_list = [
            x
            for x in merge_list
            if x in stats_for.columns and x in stats_against.columns
        ]

        team_stats = stats_for.merge(stats_against, on=merge_list, how="outer")

        team_stats["toi"] = (team_stats.toi_x + team_stats.toi_y) / 60

        team_stats = team_stats.drop(["toi_x", "toi_y"], axis=1)

        fos = ["ozf", "nzf", "dzf"]

        for fo in fos:
            team_stats[fo] = team_stats[f"{fo}w"] + team_stats[f"{fo}w"]

        team_stats = team_stats.dropna(subset="toi").reset_index(drop=True)

        cols = [x for x in TeamStatSchema.dtypes.keys() if x in team_stats.columns]

        team_stats = TeamStatSchema.validate(team_stats[cols])

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
