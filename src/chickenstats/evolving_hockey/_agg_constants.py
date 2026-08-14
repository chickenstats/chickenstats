"""Column constants for the evolving_hockey aggregation pipeline.

Imports shared stat lists from chicken_nhl and defines EH-specific column name lists.
"""

from chickenstats.chicken_nhl._agg_constants import (
    P60_STATS,
    OI_PERCENT_STATS_FOR,
    OI_PERCENT_STATS_AGAINST,
    build_group_list,
)

__all__ = [
    "P60_STATS",
    "OI_PERCENT_STATS_FOR",
    "OI_PERCENT_STATS_AGAINST",
    "build_group_list",
    "TEAMMATES_COLS",
    "OPPOSITION_COLS",
    "IND_STATS",
    "OI_STATS",
    "ZONE_STATS",
    "TEAM_REPLACE",
]

# EvolvingHockey.com CSV exports abbreviate these four teams with a period
# (e.g. "S.J") instead of the standard three-letter code. Used to normalize
# team abbreviations in both raw PBP/roster munging (pbp.py) and the
# GAR/xGAR CSV loaders (_aggregation.py).
TEAM_REPLACE = {"S.J": "SJS", "N.J": "NJD", "T.B": "TBL", "L.A": "LAK"}

# On-ice composite columns — already named correctly in PBP output
TEAMMATES_COLS = ["forwards", "forwards_eh_id", "defense", "defense_eh_id", "own_goalie", "own_goalie_eh_id"]

OPPOSITION_COLS = [
    "opp_forwards",
    "opp_forwards_eh_id",
    "opp_defense",
    "opp_defense_eh_id",
    "opp_goalie",
    "opp_goalie_eh_id",
]

# Individual stats to aggregate from PBP (raw event-level columns)
IND_STATS = [
    "goal",
    "goal_adj",
    "hd_goal",
    "pred_goal",
    "pred_goal_adj",
    "shot",
    "shot_adj",
    "hd_shot",
    "miss",
    "miss_adj",
    "hd_miss",
    "fenwick",
    "fenwick_adj",
    "hd_fenwick",
    "corsi",
    "corsi_adj",
    "block",
    "block_adj",
    "hit",
    "give",
    "take",
    "fac",
    "ozf",
    "nzf",
    "dzf",
    "pen0",
    "pen2",
    "pen4",
    "pen5",
    "pen10",
]

# On-ice stats to aggregate (for/against)
OI_STATS = [
    "goal",
    "goal_adj",
    "hd_goal",
    "pred_goal",
    "pred_goal_adj",
    "shot",
    "shot_adj",
    "hd_shot",
    "miss",
    "hd_miss",
    "fenwick",
    "fenwick_adj",
    "hd_fenwick",
    "corsi",
    "corsi_adj",
    "block",
    "hit",
    "give",
    "take",
    "fac",
    "ozf",
    "nzf",
    "dzf",
    "pen0",
    "pen2",
    "pen4",
    "pen5",
    "pen10",
    "event_length",
]

# Zone start stats
ZONE_STATS = ["ozs", "nzs", "dzs", "otf"]
