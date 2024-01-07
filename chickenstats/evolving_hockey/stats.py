import pandas as pd

from chickenstats.evolving_hockey.base import (
    munge_pbp,
    munge_rosters,
    add_positions,
    prep_ind,
    prep_oi,
    prep_zones,
)


# Function combining them all to create dataframe
def prep_pbp(
    pbp: pd.DataFrame, shifts: pd.DataFrame, columns: str = "full"
) -> pd.DataFrame:
    """
    Prepares a play-by-play dataframe using EvolvingHockey data, but with additional stats and information.
    Columns keyword argument determines information returned.

    Used in later aggregation functions. Returns a DataFrame

    Parameters:
        pbp : pd.DataFrame
            Pandas DataFrame of CSV file downloaded from play-by-play query tool at evolving-hockey.com
        shifts : pd.DataFrame
            Pandas DataFrame of CSV file downloaded from shifts query tool at evolving-hockey.com
        columns: str, default='full'
            Whether to return additional columns or more sparse play-by-play dataframe

    Returns:
        season: integer
            8-digit season code, e.g., 20192020
        session: object
            Regular season or playoffs, e.g., R
        game_id: integer
            10-digit game identifier, e.g., 2019020684
        game_date: object
            Date of game in Eastern time-zone, e.g., 2020-01-09
        event_index: object
            Unique index number of event, in chronological order, e.g.,
        game_period: integer
            Game period, e.g., 3
        game_seconds: integer
            Game time elapsed in seconds, e.g., 3578
        period_seconds: integer
            Period time elapsed in seconds, e.g., 1178
        clock_time : object
            Time shown on clock, e.g.,
        strength_state: object
            Strength state from the perspective of the event team, e.g., 5vE
        score_state: object
            Score state from the perspective of the event team, e.g., 5v2
        event_type: object
            Name of the event, e.g., GOAL
        event_description: object
            Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT.
        event_detail: object
            Additional information about the event, e.g., Wrist
        event_zone: object
            Zone location of event, e.g., DEF
        event_team: object
            3-letter abbreviation of the team for the event, e.g., NSH
        opp_team: object
            3-letter abbreviation of the opposing team for the event, e.g., CHI
        is_home: integer
            Dummy variable to signify whether event team is home team, e.g., 0
        coords_x: float
            X coordinates of event, e.g., -96
        coords_y: float
            Y coordinates of event, e.g., 11
        event_player_1: object
            Name of the player, e.g., PEKKA.RINNE
        event_player_1_id: object
            Identifier that can be used to match with Evolving Hockey data, e.g., PEKKA.RINNE
        event_player_1_pos: object
            Player's position for the game, may differ from primary position, e.g., G
        event_player_2: object
            Name of the player
        event_player_2_id: object
            Identifier that can be used to match with Evolving Hockey data
        event_player_2_pos: object
            Player's position for the game, may differ from primary position
        event_player_3: object
            Name of the player
        event_player_3_id: object
            Identifier that can be used to match with Evolving Hockey data
        event_player_3_pos: object
            Player's position for the game, may differ from primary position
        event_length: integer
            Length of time elapsed in seconds since previous event, e.g., 5
        high_danger: integer
            Whether shot event is from high-danger area, e.g., 0
        danger: integer
            Whether shot event is from danger area,
            exclusive of high-danger area, e.g., 0
        pbp_distance: float
            Distance from opponent net, in feet, according to play-by-play description, e.g., 185.0
        event_distance: float
            Distance from opponent net, in feet, e.g., 185.326738
        event_angle: float
            Angle of opponent's net from puck, in degrees, e.g., 57.528808
        opp_strength_state: object
            Strength state from the perspective of the opposing team, e.g., Ev5
        opp_score_state: object
            Score state from the perspective of the opposing team, e.g., 2v5
        event_on_f: object
            Names of the event team's forwards that are on the ice during the event,
            e.g., NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND
        event_on_f_id: object
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND
        event_on_d: object
            Names of the event team's defensemen that are on the ice during the event,
            e.g., MATTIAS EKHOLM, ROMAN JOSI
        event_on_d_id: object
            EH IDs of the event team's defensemen that are on the ice during the event,
            e.g., MATTIAS.EKHOLM, ROMAN.JOSI
        event_on_g: object
            Name of the goalie for the event team, e.g., PEKKA RINNE
        event_on_g_id: object
            Identifier for the event team goalie that can be used to match with Evolving Hockey data, e.g., PEKKA.RINNE
        event_on_1: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_1_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_1_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_2: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_2_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_2_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_3: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_3_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_3_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_4: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_4_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_4_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_5: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_5_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_5_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_6: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_6_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_6_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_7: object
            Name of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_7_id: object
            EH ID of one the event team's players that are on the ice during the event,
            e.g.,
        event_on_7_pos: object
            Position of one the event team's players that are on the ice during the event,
            e.g.,
        opp_on_f: object
            Names of the opponent's forwards that are on the ice during the event,
            e.g., ALEX DEBRINCAT, JONATHAN TOEWS, KIRBY DACH, PATRICK KANE
        opp_on_f_id: object
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., ALEX.DEBRINCAT, JONATHAN.TOEWS, KIRBY.DACH, PATRICK.KANE
        opp_on_d: object
            Names of the opposing team's defensemen that are on the ice during the event,
            e.g., DUNCAN KEITH, ERIK GUSTAFSSON
        opp_on_d_id: object
            EH IDs of the opposing team's defensemen that are on the ice during the event,
            e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2
        opp_on_g: object
            Name of the opposing goalie for the event team, e.g., EMPTY NET
        opp_on_g_id: object
            Identifier for the opposing goalie that can be used to match with Evolving Hockey data, e.g., EMPTY NET
        opp_on_1: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_1_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_1_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_2: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_2_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_2_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_3: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_3_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_3_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_4: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_4_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_4_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_5: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_5_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_5_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_6: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_6_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_6_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_7: object
            Name of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_7_id: object
            EH ID of one the opposing team's players that are on the ice during the event,
            e.g.,
        opp_on_7_pos: object
            Position of one the opposing team's players that are on the ice during the event,
            e.g.,
        change: integer
            Dummy variable to indicate whether event is a change, e.g., 0
        zone_start: object
            Zone where the changed, e.g., OFF or OTF
        num_on: integer
            Number of players entering the ice, e.g., 6
        num_off: integer
            Number of players exiting the ice, e.g., 0
        players_on: string
            Names of players on, in jersey order,
            e.g., FILIP FORSBERG, ALEX CARRIER, ROMAN JOSI, MIKAEL GRANLUND, JUUSE SAROS, MATT DUCHENE
        players_on_id: string
            Evolving Hockey IDs of players on, in jersey order,
            e.g., FILIP.FORSBERG, ALEX.CARRIER, ROMAN.JOSI, MIKAEL.GRANLUND, JUUSE.SAROS, MATT.DUCHENE
        players_on_pos: string
            Positions of players on, in jersey order,
            e.g., L, D, D, C, G, C
        players_off: string
            Names of players off, in jersey order
        players_off_id: string
            Evolving Hockey IDs of players off, in jersey order
        players_off_positions: string
            Positions of players off, in jersey order
        shot: integer
            Dummy variable to indicate whether event is a shot, e.g., 0
        shot_adj: float
            Score and venue-adjusted shot value, e.g.,
        goal: integer
            Dummy variable to indicate whether event is a goal, e.g., 1
        goal_adj: float
            Score and venue-adjusted shot value, e.g.,
        pred_goal: float
            Predicted goal value (xG), e.g.,
        pred_goal_adj: float
            Score and venue-adjusted predicted goal (xG) value, e.g.,
        miss: integer
            Dummy variable to indicate whether event is a missed shot, e.g., 0
        block: integer
            Dummy variable to indicate whether event is a block, e.g., 0
        corsi: integer
            Dummy variable to indicate whether event is a corsi event, e.g., 1
        corsi_adj: float
            Score and venue-adjusted corsi value, e.g.,
        fenwick: integer
            Dummy variable to indicate whether event is a fenwick event, e.g., 1
        fenwick_adj: float
             Score and venue-adjusted fenwick value, e.g.,
        hd_shot: integer
            Dummy variable to indicate whether event is a high-danger shot event, e.g., 0
        hd_goal: integer
            Dummy variable to indicate whether event is a high-danger goal event, e.g., 0
        hd_miss: integer
            Dummy variable to indicate whether event is a high-danger miss event, e.g., 0
        hd_fenwick: integer
            Dummy variable to indicate whether event is a high-danger fenwick event, e.g., 0
        fac: integer
            Dummy variable to indicate whether event is a faceoff, e.g., 0
        hit: integer
            Dummy variable to indicate whether event is a hit, e.g., 0
        give: integer
            Dummy variable to indicate whether event is a giveaway, e.g., 0
        take: integer
            Dummy variable to indicate whether event is a takeaway, e.g., 0
        pen0: integer
            Dummy variable to indicate whether event is a penalty with no minutes, e.g., 0
        pen2: integer
            Dummy variable to indicate whether event is a two-minute penalty, e.g., 0
        pen4: integer
            Dummy variable to indicate whether event is a four-minute penalty, e.g., 0
        pen5: integer
            Dummy variable to indicate whether event is a five-minute penalty, e.g., 0
        pen10: integer
            Dummy variable to indicate whether event is a ten-minute penalty, e.g., 0
        stop: integer
            Dummy variable to indicate whether event is a stoppage, e.g., 0
        ozf: integer
            Dummy variable to indicate whether event is an offensive zone faceoff e.g., 0
        nzf: integer
            Dummy variable to indicate whether event is a neutral zone faceoff, e.g., 0
        dzf: integer
            Dummy variable to indicate whether event is a defensive zone faceoff, e.g., 0
        ozs: integer
            Dummy variable to indicate whether an event is an offensive zone change, e.g., 0
        nzs: integer
            Dummy variable to indicate whether an event is a neutral zone change, e.g., 0
        dzs: integer
            Dummy variable to indicate whether an event is an defensive zone change, e.g., 0
        otf: integer
            Dummy variable to indicate whether an event is an on-the-fly change, e.g., 0

    Examples:
        Play-by-play DataFrame
        >>> raw_shifts = pd.read_csv('./raw_shifts.csv')
        >>> raw_pbp = pd.read_csv('./raw_pbp.csv')
        >>> play_by_play = prep_pbp(raw_pbp, raw_shifts)

    """

    rosters = munge_rosters(shifts)

    pbp = munge_pbp(pbp)

    pbp = add_positions(pbp, rosters)

    if columns in ["light", "full", "all"]:
        cols = [
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

        other_cols = [
            "opp_strength_state",
            "opp_score_state",
        ]

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

    if columns in ["light", "full", "all"]:
        cols = [x for x in cols if x in pbp]

        pbp = pbp[cols]

    return pbp


# Function combining the on-ice and individual stats
def prep_stats(
    df: pd.DataFrame,
    level: str = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
) -> pd.DataFrame:
    """
    Prepares an individual and on-ice stats dataframe using EvolvingHockey data,
    aggregated to desired level. Capable of returning cuts that account for strength state,
    period, score state, teammates, and opposition.

    Returns a DataFrame.

    Parameters:
        df : pd.Dataframe
            Dataframe from the prep_pbp function with the default columns argument
        level : str, default='game'
            Level to aggregate stats, e.g., 'game'
        score: bool, default=False
            Whether to aggregate to score state level
        teammates: bool, default=False
            Whether to account for teammates when aggregating
        opposition: bool, default=False
            Whether to account for opposition when aggregating

    Returns:
        season: integer
            8-digit season code, e.g., 20222023
        session: object
            Regular season or playoffs, e.g., R
        game_id: integer
            10-digit game identifier, e.g.,
        game_date: object
            Date of game in Eastern time-zone, e.g.,
        player: object
            Name of the player, e.g., FILIP.FORSBERG
        player_id: object
            Player EH ID, e.g., FILIP.FORSBERG
        position: object
            Player's position, e.g., L
        team: object
            3-letter abbreviation of the player's team, e.g., NSH
        opp_team: object
            3-letter abbreviation of the opposing team, e.g., NJD
        strength_state: object
            Strength state from the perspective of the event team, e.g., 5v4
        score_state: object
            Score state from the perspective of the event team, e.g., 0v0
        game_period: integer
            Game period, e.g., 1
        forwards: object
            Names of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, MATT.DUCHENE, MIKAEL.GRANLUND, RYAN.JOHANSEN
        forwards_id: object
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, MATT.DUCHENE, MIKAEL.GRANLUND, RYAN.JOHANSEN
        defense: object
            Names of the event team's defensemen that are on the ice during the event,
            e.g., ROMAN.JOSI
        defense_id: object
            EH IDs of the event team's defensemen that are on the ice during the event,
            e.g., ROMAN.JOSI
        own_goalie: object
            Name of the goalie for the event team, e.g., JUUSE.SAROS
        own_goalie_id: object
            Identifier for the event team goalie that can be used to match with Evolving Hockey data, e.g., JUUSE.SAROS
        opp_forwards: object
            Names of the opponent's forwards that are on the ice during the event,
            e.g., DAWSON.MERCER, ERIK.HAULA
        opp_forwards_id: object
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., DAWSON.MERCER, ERIK.HAULA
        opp_defense: object
            Names of the opposing team's defensemen that are on the ice during the event,
            e.g., DAMON.SEVERSON, RYAN.GRAVES
        opp_defense_id: object
            EH IDs of the opposing team's defensemen that are on the ice during the event,
            e.g., DAMON.SEVERSON, RYAN.GRAVES
        opp_goalie: object
            Name of the opposing goalie for the event team, e.g., MACKENZIE.BLACKWOOD
        opp_goalie_id: object
            Identifier for the opposing goalie that can be used to match with Evolving Hockey data, e.g., MACKENZIE.BLACKWOOD
        toi: float
            Time on-ice in minutes, e.g., 1.616667
        g: integer
            Number of individual goals scored, e.g, 0
        a1: integer
            Number of primary assists, e.g, 0
        a2: integer
            Number of secondary assists, e.g, 0
        isf: integer
            Number of indiviudal shots registered, e.g., 0
        iff: integer
            Number of indiviudal fenwick events registered, e.g., 1
        icf: integer
            Number of indiviudal corsi events registered, e.g., 3
        ixg: float
            Sum value of individual predicted goals (xG), e.g., 0.237
        gax: float
            Sum value of goals scored above expected, e.g., -0.237
        ihdg: integer
            Sum value of individual high-danger goals scored, e.g., 0
        ihdsf: integer
            Sum value of individual high-danger shots taken, e.g., 0
        ihdm: integer
            Sum value of individual high-danger shots missed, e.g., 0
        ihdf: integer
            Sum value of individual high-danger fenwick events registered, e.g., 0
        imsf: integer
            Sum value of individual missed shots, 1
        isb: integer
            Sum value of shots taken that were ultimately blocked, e.g., 2
        ibs: integer
            Sum value of opponent shots taken that the player ultimately blocked, e.g.,
        igive: integer
            Sum of individual giveaways, e.g., 0
        itake: integer
            Sum of individual takeaways, e.g., 0
        ihf: integer
            Sum of individual hits for, e.g., 0
        iht: integer
            Sum of individual hits taken, e.g., 0
        ifow: integer
            Sum of individual faceoffs won, e.g., 0
        ifol: integer
            Sum of individual faceoffs lost, e.g., 0
        iozfw: integer
            Sum of individual faceoffs won in offensive zone, e.g., 0
        iozfl: integer
            Sum of individual faceoffs lost in offensive zone, e.g., 0
        inzfw: integer
            Sum of individual faceoffs won in neutral zone, e.g., 0
        inzfl: integer
            Sum of individual faceoffs lost in neutral zone, e.g., 0
        idzfw: integer
            Sum of individual faceoffs won in defensive zone, e.g., 0
        idzfl: integer
            Sum of individual faceoffs lost in defensive zone, e.g., 0
        a1_xg: float
            Sum of xG from primary assists, e.g., 0
        a2_xg: float
            Sum of xG from secondary assists, e.g., 0
        ipent0: integer
            Sum of individual 0-minute penalties taken, e.g., 0
        ipent2: integer
            Sum of individual 2-minute penalties taken, e.g., 0
        ipent4: intger
            Sum of individual 4-minute penalties taken, e.g., 0
        ipent5: integer
            Sum of individual 5-minute penalties taken, e.g., 0
        ipent10: integer
            Sum of individual 10-minute penalties taken, e.g., 0
        ipend0: integer
            Sum of individual 0-minute penalties drawn, e.g., 0
        ipend2: integer
            Sum of individual 2-minute penalties drawn, e.g., 0
        ipend4: integer
            Sum of individual 4-minute penalties drawn, e.g., 0
        ipend5: integer
            Sum of individual 5-minute penalties drawn, e.g., 0
        ipend10: integer
            Sum of individual 10-minute penalties drawn, e.g., 0
        ozs: integer
            Sum of changes with offensive zone starts, e.g., 1
        nzs: integer
            Sum of changes with neutral zone starts, e.g., 0
        dzs: integer
            Sum of changes with defensive zone starts, e.g., 0
        otf: integer
            Sum of changes on-the-fly, e.g., 0
        gf: integer
            Sum of goals scored while player is on-ice, e.g., 0
        gf_adj: float
            Sum of venue- and score-adjusted goals scored while player is on-ice, e.g., 0
        hdgf: integer
            Sum of high-danger goals scored while player is on-ice, e.g., 0
        ga: integer
            Sum of goals allowed while player is on-ice, e.g., 0
        ga_adj: float
            Sum of venue- and score-adjusted goals allowed while player is on-ice, e.g., 0
        hdga: integer
            Sum of high-danger goals allowed while player is on-ice, e.g., 0
        xgf: float
            Sum of expected goals generated while player is on-ice, e.g., 0.425891
        xgf_adj: float
            Sum of venue- and score-adjusted expected goals generated while player is on-ice, e.g., 0.388412
        xga: float
            Sum of expected goals allowed while player is on-ice, e.g., 0
        xga_adj: float
            Sum of venue- and score-adjusted expected goals allowed while player is on-ice, e.g., 0
        sf: integer
            Sum of shots taken while player is on-ice, e.g., 1
        sf_adj: float
            Sum of venue- and score-adjusted shots taken while player is on-ice, e.g., .93
        hdsf: integer
            Sum of high-danger shots taken while player is on-ice, e.g., 0
        sa: integer
            Sum of shots allowed while player is on-ice, e.g., 0
        sa_adj: float
            Sum of venue- and score-adjusted shots allowed while player is on-ice, e.g., 0
        hdsa: integer
            Sum of high-danger shots allowed while player is on-ice, e.g., 0
        ff: integer
            Sum of fenwick events generated while player is on-ice, e.g., 4
        ff_adj: float
            Sum of venue- and score-adjusted fenwick events generated while player is on-ice, e.g., 3.704
        hdff: integer
            Sum of high-danger fenwick events generated while player is on-ice, e.g., 0
        fa: integer
            Sum of fenwick events allowed while player is on-ice, e.g., 0
        fa_adj: float
            Sum of venue- and score-adjusted fenwick events allowed while player is on-ice, e.g., 0
        hdfa: integer
            Sum of high-danger fenwick events allowed while player is on-ice, e.g., 0
        cf: integer
            Sum of corsi events generated while player is on-ice, e.g., 7
        cf_adj: float
            Sum of venue- and score-adjusted corsi events generated while player is on-ice, e.g., 6.51
        ca: integer
            Sum of corsi events allowed while player is on-ice, e.g., 0
        ca_adj: float
            Sum of venue- and score-adjusted corsi events allowed while player is on-ice, e.g., 6.51
        bsf: integer
            Sum of shots taken that were ultimately blocked while player is on-ice, e.g., 3
        bsa: integer
            Sum of shots allowed that were ultimately blocked while player is on-ice, e.g., 0
        msf: integer
            Sum of shots taken that missed net while player is on-ice, e.g., 3
        hdmsf: integer
            Sum of high-danger shots taken that missed net while player is on-ice, e.g., 0
        msa: integer
            Sum of shots allowed that missed net while player is on-ice, e.g., 0
        hdmsa: integer
            Sum of high-danger shots allowed that missed net while player is on-ice, e.g., 0
        hf: integer
            Sum of hits dished out while player is on-ice, e.g., 0
        ht: integer
            Sum of hits taken while player is on-ice, e.g., 1
        ozf: integer
            Sum of offensive zone faceoffs that occur while player is on-ice, e.g., 1
        nzf: integer
            Sum of neutral zone faceoffs that occur while player is on-ice, e.g., 0
        dzf: integer
            Sum of defensive zone faceoffs that occur while player is on-ice, e.g., 1
        fow: integer
            Sum of faceoffs won while player is on-ice, e.g., 0
        fol: integer
            Sum of faceoffs lost while player is on-ice, e.g., 1
        ozfw: integer
            Sum of offensive zone faceoffs won while player is on-ice, e.g., 0
        ozfl: integer
            Sum of offensive zone faceoffs lost while player is on-ice, e.g., 1
        nzfw: integer
            Sum of neutral zone faceoffs won while player is on-ice, e.g., 0
        nzfl: integer
            Sum of neutral zone faceoffs lost while player is on-ice, e.g., 0
        dzfw: integer
            Sum of defensive zone faceoffs won while player is on-ice, e.g., 0
        dzfl: integer
            Sum of defensive zone faceoffs lost while player is on-ice, e.g., 0
        pent0: integer
            Sum of individual 0-minute penalties taken while player is on-ice, e.g., 0
        pent2: integer
            Sum of individual 2-minute penalties taken while player is on-ice, e.g., 0
        pent4: intger
            Sum of individual 4-minute penalties taken while player is on-ice, e.g., 0
        pent5: integer
            Sum of individual 5-minute penalties taken while player is on-ice, e.g., 0
        pent10: integer
            Sum of individual 10-minute penalties taken while player is on-ice, e.g., 0
        pend0: integer
            Sum of individual 0-minute penalties drawn while player is on-ice, e.g., 0
        pend2: integer
            Sum of individual 2-minute penalties drawn while player is on-ice, e.g., 0
        pend4: integer
            Sum of individual 4-minute penalties drawn while player is on-ice, e.g., 0
        pend5: integer
            Sum of individual 5-minute penalties drawn while player is on-ice, e.g., 0
        pend10: integer
            Sum of individual 10-minute penalties drawn while player is on-ice, e.g., 0

    Examples:
        Basic play-by-play DataFrame
        >>> raw_shifts = pd.read_csv('./raw_shifts.csv')
        >>> raw_pbp = pd.read_csv('./raw_pbp.csv')
        >>> pbp = prep_pbp(raw_pbp, raw_shifts)

        Basic game-level stats, with no teammates or opposition
        >>> stats = prep_stats(pbp)

        Period-level stats, grouped by teammates
        >>> stats = prep_stats(pbp, level = 'period', teammates=True)

        Session-level (e.g., regular seasion) stats, grouped by teammates and opposition
        >>> stats = prep_stats(pbp, level='session', teammates=True, opposition=True)

    """

    ind = prep_ind(df, level, score, teammates, opposition)

    oi = prep_oi(df, level, score, teammates, opposition)

    zones = prep_zones(df, level, score, teammates, opposition)

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

    stats = oi.merge(ind, how="left", left_on=merge_cols, right_on=merge_cols).fillna(0)

    stats = stats.merge(
        zones, how="left", left_on=merge_cols, right_on=merge_cols
    ).fillna(0)

    stats = stats.loc[stats.toi > 0].reset_index(drop=True).copy()

    stats_list = [
        "toi",
        "g",
        "a1",
        "a2",
        "isf",
        "iff",
        "icf",
        "ixg",
        "gax",
        "ihdg",
        "ihdsf",
        "ihdm",
        "ihdf",
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
        "ozs",
        "nzs",
        "dzs",
        "otf",
    ]

    for stat in stats_list:
        if stat not in stats.columns:
            stats[stat] = 0

        else:
            stats[stat] = pd.to_numeric(stats[stat].fillna(0))

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
        "toi",
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
        "ozs",
        "nzs",
        "dzs",
        "otf",
        "gf",
        "gf_adj",
        "hdgf",
        "ga",
        "ga_adj",
        "hdga",
        "xgf",
        "xgf_adj",
        "xga",
        "xga_adj",
        "sf",
        "sf_adj",
        "hdsf",
        "sa",
        "sa_adj",
        "hdsa",
        "ff",
        "ff_adj",
        "hdff",
        "fa",
        "fa_adj",
        "hdfa",
        "cf",
        "cf_adj",
        "ca",
        "ca_adj",
        "bsf",
        "bsa",
        "msf",
        "hdmsf",
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

    columns = [x for x in columns if x in stats]

    stats = stats[columns]

    return stats


# Function to prep the lines data
def prep_lines(
    data: pd.DataFrame,
    position: str,
    level: str = "game",
    score: bool = False,
    teammates: bool = False,
    opposition: bool = False,
):
    """
    Prepares an individual and on-ice stats dataframe using EvolvingHockey data,
    aggregated to desired level. Capable of returning cuts that account for strength state,
    period, score state, teammates, and opposition.

    Returns a DataFrame.

    Parameters:
        data : pd.Dataframe
            Dataframe from the prep_pbp function with the default columns argument
        position : str
            Used to indicate whether to include forwards or defense
        level : str, default='game'
            Level to aggregate stats, e.g., 'game'
        score: bool, default=False
            Whether to aggregate to score state level
        teammates: bool, default=False
            Whether to account for teammates when aggregating
        opposition: bool, default=False
            Whether to account for opposition when aggregating

    Returns:
        season: integer
            8-digit season code, e.g., 20222023
        session: object
            Regular season or playoffs, e.g., R
        game_id: integer
            10-digit game identifier, e.g.,
        game_date: object
            Date of game in Eastern time-zone, e.g.,
        team: object
            3-letter abbreviation of the player's team, e.g., NSH
        opp_team: object
            3-letter abbreviation of the opposing team, e.g., NJD
        strength_state: object
            Strength state from the perspective of the event team, e.g., 5v4
        score_state: object
            Score state from the perspective of the event team, e.g., 0v0
        game_period: integer
            Game period, e.g., 1
        forwards: object
            Names of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, MATT.DUCHENE, MIKAEL.GRANLUND, RYAN.JOHANSEN
        forwards_id: object
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., FILIP.FORSBERG, MATT.DUCHENE, MIKAEL.GRANLUND, RYAN.JOHANSEN
        defense: object
            Names of the event team's defensemen that are on the ice during the event,
            e.g., ROMAN.JOSI
        defense_id: object
            EH IDs of the event team's defensemen that are on the ice during the event,
            e.g., ROMAN.JOSI
        own_goalie: object
            Name of the goalie for the event team, e.g., JUUSE.SAROS
        own_goalie_id: object
            Identifier for the event team goalie that can be used to match with Evolving Hockey data, e.g., JUUSE.SAROS
        opp_forwards: object
            Names of the opponent's forwards that are on the ice during the event,
            e.g., DAWSON.MERCER, ERIK.HAULA
        opp_forwards_id: object
            EH IDs of the event team's forwards that are on the ice during the event,
            e.g., DAWSON.MERCER, ERIK.HAULA
        opp_defense: object
            Names of the opposing team's defensemen that are on the ice during the event,
            e.g., DAMON.SEVERSON, RYAN.GRAVES
        opp_defense_id: object
            EH IDs of the opposing team's defensemen that are on the ice during the event,
            e.g., DAMON.SEVERSON, RYAN.GRAVES
        opp_goalie: object
            Name of the opposing goalie for the event team, e.g., MACKENZIE.BLACKWOOD
        opp_goalie_id: object
            Identifier for the opposing goalie that can be used to match with Evolving Hockey data, e.g., MACKENZIE.BLACKWOOD
        toi: float
            Time on-ice in minutes, e.g., 1.616667
        gf: integer
            Sum of goals scored while line is on-ice, e.g., 0
        gf_adj: float
            Sum of venue- and score-adjusted goals scored while line is on-ice, e.g., 0
        hdgf: integer
            Sum of high-danger goals scored while line is on-ice, e.g., 0
        ga: integer
            Sum of goals allowed while line is on-ice, e.g., 0
        ga_adj: float
            Sum of venue- and score-adjusted goals allowed while line is on-ice, e.g., 0
        hdga: integer
            Sum of high-danger goals allowed while line is on-ice, e.g., 0
        xgf: float
            Sum of expected goals generated while line is on-ice, e.g., 0.425891
        xgf_adj: float
            Sum of venue- and score-adjusted expected goals generated while line is on-ice, e.g., 0.388412
        xga: float
            Sum of expected goals allowed while line is on-ice, e.g., 0
        xga_adj: float
            Sum of venue- and score-adjusted expected goals allowed while line is on-ice, e.g., 0
        sf: integer
            Sum of shots taken while line is on-ice, e.g., 1
        sf_adj: float
            Sum of venue- and score-adjusted shots taken while line is on-ice, e.g., .93
        hdsf: integer
            Sum of high-danger shots taken while line is on-ice, e.g., 0
        sa: integer
            Sum of shots allowed while line is on-ice, e.g., 0
        sa_adj: float
            Sum of venue- and score-adjusted shots allowed while line is on-ice, e.g., 0
        hdsa: integer
            Sum of high-danger shots allowed while line is on-ice, e.g., 0
        ff: integer
            Sum of fenwick events generated while line is on-ice, e.g., 4
        ff_adj: float
            Sum of venue- and score-adjusted fenwick events generated while line is on-ice, e.g., 3.704
        hdff: integer
            Sum of high-danger fenwick events generated while line is on-ice, e.g., 0
        fa: integer
            Sum of fenwick events allowed while line is on-ice, e.g., 0
        fa_adj: float
            Sum of venue- and score-adjusted fenwick events allowed while line is on-ice, e.g., 0
        hdfa: integer
            Sum of high-danger fenwick events allowed while line is on-ice, e.g., 0
        cf: integer
            Sum of corsi events generated while line is on-ice, e.g., 7
        cf_adj: float
            Sum of venue- and score-adjusted corsi events generated while line is on-ice, e.g., 6.51
        ca: integer
            Sum of corsi events allowed while line is on-ice, e.g., 0
        ca_adj: float
            Sum of venue- and score-adjusted corsi events allowed while line is on-ice, e.g., 6.51
        bsf: integer
            Sum of shots taken that were ultimately blocked while line is on-ice, e.g., 3
        bsa: integer
            Sum of shots allowed that were ultimately blocked while line is on-ice, e.g., 0
        msf: integer
            Sum of shots taken that missed net while line is on-ice, e.g., 3
        hdmsf: integer
            Sum of high-danger shots taken that missed net while line is on-ice, e.g., 0
        msa: integer
            Sum of shots allowed that missed net while line is on-ice, e.g., 0
        hdmsa: integer
            Sum of high-danger shots allowed that missed net while line is on-ice, e.g., 0
        hf: integer
            Sum of hits dished out while line is on-ice, e.g., 0
        ht: integer
            Sum of hits taken while line is on-ice, e.g., 1
        ozf: integer
            Sum of offensive zone faceoffs that occur while line is on-ice, e.g., 1
        nzf: integer
            Sum of neutral zone faceoffs that occur while line is on-ice, e.g., 0
        dzf: integer
            Sum of defensive zone faceoffs that occur while line is on-ice, e.g., 1
        fow: integer
            Sum of faceoffs won while line is on-ice, e.g., 0
        fol: integer
            Sum of faceoffs lost while line is on-ice, e.g., 1
        ozfw: integer
            Sum of offensive zone faceoffs won while line is on-ice, e.g., 0
        ozfl: integer
            Sum of offensive zone faceoffs lost while line is on-ice, e.g., 1
        nzfw: integer
            Sum of neutral zone faceoffs won while line is on-ice, e.g., 0
        nzfl: integer
            Sum of neutral zone faceoffs lost while line is on-ice, e.g., 0
        dzfw: integer
            Sum of defensive zone faceoffs won while line is on-ice, e.g., 0
        dzfl: integer
            Sum of defensive zone faceoffs lost while line is on-ice, e.g., 0
        pent0: integer
            Sum of individual 0-minute penalties taken while line is on-ice, e.g., 0
        pent2: integer
            Sum of individual 2-minute penalties taken while line is on-ice, e.g., 0
        pent4: intger
            Sum of individual 4-minute penalties taken while line is on-ice, e.g., 0
        pent5: integer
            Sum of individual 5-minute penalties taken while line is on-ice, e.g., 0
        pent10: integer
            Sum of individual 10-minute penalties taken while line is on-ice, e.g., 0
        pend0: integer
            Sum of individual 0-minute penalties drawn while line is on-ice, e.g., 0
        pend2: integer
            Sum of individual 2-minute penalties drawn while line is on-ice, e.g., 0
        pend4: integer
            Sum of individual 4-minute penalties drawn while line is on-ice, e.g., 0
        pend5: integer
            Sum of individual 5-minute penalties drawn while line is on-ice, e.g., 0
        pend10: integer
            Sum of individual 10-minute penalties drawn while line is on-ice, e.g., 0

    Examples:
        Basic play-by-play DataFrame
        >>> raw_shifts = pd.read_csv('./raw_shifts.csv')
        >>> raw_pbp = pd.read_csv('./raw_pbp.csv')
        >>> pbp = prep_pbp(raw_pbp, raw_shifts)

        Basic game-level stats for forwards, with no teammates or opposition
        >>> lines = prep_lines(pbp, position='f')

        Period-level stats for defense, grouped by teammates
        >>> lines = prep_lines(pbp, position='d', level='period', teammates=True)

        Session-level (e.g., regular seasion) stats, grouped by teammates and opposition
        >>> lines = prep_lines(pbp, position='f', level='session', teammates=True, opposition=True)

    """

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
        if position.lower() in ["f", "for", "fwd", "fwds", "forward", "forwards"]:
            group_list = group_list + [
                "event_on_d",
                "event_on_d_id",
                "event_on_g",
                "event_on_g_id",
            ]

        if position.lower() in [
            "d",
            "def",
            "defense",
        ]:
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

    agg_stats = {x: "sum" for x in stats if x in data.columns}

    # Aggregating the "for" dataframe

    lines_f = data.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

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
        if position.lower() in ["f", "for", "fwd", "fwds", "forward", "forwards"]:
            group_list = group_list + [
                "opp_on_d",
                "opp_on_d_id",
                "opp_on_g",
                "opp_on_g_id",
            ]

        if position.lower() in [
            "d",
            "def",
            "defense",
        ]:
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

    agg_stats = {x: "sum" for x in stats if x in data.columns}

    # Aggregating "aggainst" dataframe

    lines_a = data.groupby(group_list, as_index=False, dropna=False).agg(agg_stats)

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
        if position.lower() in ["f", "for", "fwd", "fwds", "forward", "forwards"]:
            merge_list = [
                "season",
                "session",
                "team",
                "strength_state",
                "forwards",
                "forwards_id",
            ]

        if position.lower() in [
            "d",
            "def",
            "defense",
        ]:
            merge_list = [
                "season",
                "session",
                "team",
                "strength_state",
                "defense",
                "defense_id",
            ]

    if level == "game":
        if position.lower() in ["f", "for", "fwd", "fwds", "forward", "forwards"]:
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

        if position.lower() in [
            "d",
            "def",
            "defense",
        ]:
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
        if position.lower() in ["f", "for", "fwd", "fwds", "forward", "forwards"]:
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

        if position.lower() in [
            "d",
            "def",
            "defense",
        ]:
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

    lines = lines_f.merge(
        lines_a, how="outer", on=merge_list, suffixes=("_x", "")
    ).fillna(0)

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

    cols = [x for x in cols if x in lines]

    for col in cols:
        lines[col] = lines[col].fillna("EMPTY")

    lines.toi = lines.toi_x + lines.toi

    lines = lines.drop(columns="toi_x")

    lines["ozf"] = lines.ozfw + lines.ozfl

    lines["nzf"] = lines.nzfw + lines.nzfl

    lines["dzf"] = lines.dzfw + lines.dzfl

    stats = [
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "ga",
        "ga_adj",
        "hdga",
        "xgf",
        "xgf_adj",
        "xga",
        "xga_adj",
        "sf",
        "sf_adj",
        "hdsf",
        "sa",
        "sa_adj",
        "hdsa",
        "ff",
        "ff_adj",
        "hdff",
        "fa",
        "fa_adj",
        "hdfa",
        "cf",
        "cf_adj",
        "ca",
        "ca_adj",
        "bsf",
        "bsa",
        "msf",
        "hdmsf",
        "msa",
        "hdmsa",
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

    for stat in stats:
        if stat not in lines.columns:
            lines[stat] = 0

        else:
            lines[stat] = pd.to_numeric(lines[stat].fillna(0))

    cols = [
        "season",
        "session",
        "game_id",
        "game_date",
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
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "ga",
        "ga_adj",
        "hdga",
        "xgf",
        "xgf_adj",
        "xga",
        "xga_adj",
        "sf",
        "sf_adj",
        "hdsf",
        "sa",
        "sa_adj",
        "hdsa",
        "ff",
        "ff_adj",
        "hdff",
        "fa",
        "fa_adj",
        "hdfa",
        "cf",
        "cf_adj",
        "ca",
        "ca_adj",
        "bsf",
        "bsa",
        "msf",
        "hdmsf",
        "msa",
        "hdmsa",
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

    cols = [x for x in cols if x in lines.columns]

    lines = lines[cols]

    lines = lines.loc[lines.toi > 0].reset_index(drop=True).copy()

    return lines


# Function to prep the team stats
def prep_team(
    data: pd.DataFrame, level: str = "game", strengths: bool = True, score: bool = False
) -> pd.DataFrame:
    """
    Prepares an individual and on-ice stats dataframe using EvolvingHockey data,
    aggregated to desired level. Capable of returning cuts that account for strength state,
    period, score state, teammates, and opposition.

    Returns a DataFrame.

    Parameters:
        data : pd.Dataframe
            Pandas DataFrame from the prep_pbp function with the default columns argument
        level : str, default='game'
            Level to aggregate stats, e.g., 'game'
        strengths: bool, default=True
            Whether to aggregate to strength-state level
        score: bool, default=False
            Whether to aggregate to score state level


    Returns:
        Stuff
            Description
    """

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

    agg_dict = {x: "sum" for x in agg_stats if x in data.columns}

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
        data.groupby(group_list, as_index=False).agg(agg_dict).rename(columns=new_cols)
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

    agg_dict = {x: "sum" for x in agg_stats if x in data.columns}

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
        data.groupby(group_list, as_index=False).agg(agg_dict).rename(columns=new_cols)
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
        x for x in merge_list if x in stats_for.columns and x in stats_against.columns
    ]

    team_stats = stats_for.merge(stats_against, on=merge_list, how="outer")

    team_stats["toi"] = (team_stats.toi_x + team_stats.toi_y) / 60

    team_stats = team_stats.drop(["toi_x", "toi_y"], axis=1)

    fos = ["ozf", "nzf", "dzf"]

    for fo in fos:
        team_stats[fo] = team_stats[f"{fo}w"] + team_stats[f"{fo}w"]

    team_stats = team_stats.dropna(subset="toi").reset_index(drop=True)

    stats = [
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "ga",
        "ga_adj",
        "hdga",
        "xgf",
        "xgf_adj",
        "xga",
        "xga_adj",
        "sf",
        "sf_adj",
        "hdsf",
        "sa",
        "sa_adj",
        "hdsa",
        "ff",
        "ff_adj",
        "hdff",
        "fa",
        "fa_adj",
        "hdfa",
        "cf",
        "cf_adj",
        "ca",
        "ca_adj",
        "bsf",
        "bsa",
        "msf",
        "hdmsf",
        "msa",
        "hdmsa",
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

    for stat in stats:
        if stat not in team_stats.columns:
            team_stats[stat] = 0

        else:
            team_stats[stat] = pd.to_numeric(team_stats[stat].fillna(0))

    cols = [
        "season",
        "session",
        "game_id",
        "game_date",
        "team",
        "opp_team",
        "strength_state",
        "score_state",
        "game_period",
        "toi",
        "gf",
        "gf_adj",
        "hdgf",
        "ga",
        "ga_adj",
        "hdga",
        "xgf",
        "xgf_adj",
        "xga",
        "xga_adj",
        "sf",
        "sf_adj",
        "hdsf",
        "sa",
        "sa_adj",
        "hdsa",
        "ff",
        "ff_adj",
        "hdff",
        "fa",
        "fa_adj",
        "hdfa",
        "cf",
        "cf_adj",
        "ca",
        "ca_adj",
        "bsf",
        "bsa",
        "msf",
        "hdmsf",
        "msa",
        "hdmsa",
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

    cols = [x for x in cols if x in team_stats]

    team_stats = team_stats[cols]

    return team_stats


# Function to prep the GAR dataframe
def prep_gar(skater_data: pd.DataFrame, goalie_data: pd.DataFrame) -> pd.DataFrame:
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
