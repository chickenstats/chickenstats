---
icon: material/table
description: "Columns, dtypes and nullability of ind_stats in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: ind_stats**

Returned by `evolving_hockey.prep_ind`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 for 2023-24 season |
| 2 | `session` | `String` | no |  | Whether games are regular season, playoffs, or pre-season, e.g., R; not at season level |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2023020001 |
| 4 | `game_date` | `String` | no |  | Date game was played, e.g., 2023-10-10 |
| 5 | `player` | `String` | no |  | Player's name, e.g., FILIP FORSBERG |
| 6 | `eh_id` | `String` | no |  | Evolving Hockey ID for the player, e.g., FILIP.FORSBERG |
| 7 | `position` | `String` | no |  | Player's position, e.g., L |
| 8 | `team` | `String` | no |  | Player's team, e.g., NSH |
| 9 | `opp_team` | `String` | no |  | Opposing team, e.g., TBL |
| 10 | `strength_state` | `String` | no |  | Strength state, e.g., 5v5 |
| 11 | `period` | `Int64` | no |  | Period, e.g., 3 |
| 12 | `score_state` | `String` | no |  | Score state, e.g., 2v1 |
| 13 | `forwards` | `String` | yes |  | Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY |
| 14 | `forwards_eh_id` | `String` | yes |  | Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY |
| 15 | `defense` | `String` | yes |  | Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER |
| 16 | `defense_eh_id` | `String` | yes |  | Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER |
| 17 | `own_goalie` | `String` | yes |  | Own goalie, e.g., JUUSE SAROS |
| 18 | `own_goalie_eh_id` | `String` | yes |  | Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS |
| 19 | `opp_forwards` | `String` | yes |  | Opposing forwards, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS |
| 20 | `opp_forwards_eh_id` | `String` | yes |  | Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS |
| 21 | `opp_defense` | `String` | yes |  | Opposing defense, e.g., NICK PERBIX, VICTOR HEDMAN |
| 22 | `opp_defense_eh_id` | `String` | yes |  | Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN |
| 23 | `opp_goalie` | `String` | yes |  | Opposing goalie, e.g., JONAS JOHANSSON |
| 24 | `opp_goalie_eh_id` | `String` | yes |  | Opposing goalie's Evolving Hockey ID, e.g., JONAS.JOHANSSON |
| 25 | `games_played` | `Int64` | no |  | Number of games the row covers; 1 at game level. A game counts when the row's player, line or team has ice time or an event in it, the same games its stats are summed from, e.g., 1 |
| 26 | `g` | `Int64` | no |  | Individual goals scored, e.g., 0 |
| 27 | `g_adj` | `Float64` | no |  | Score- and venue-adjusted individual goals scored, e.g., 0.0 |
| 28 | `ihdg` | `Int64` | no |  | Individual high-danger goals scored, e.g., 0 |
| 29 | `a1` | `Int64` | no |  | Individual primary assists, e.g., 0 |
| 30 | `a2` | `Int64` | no |  | Individual secondary assists, e.g., 0 |
| 31 | `ixg` | `Float64` | yes |  | Individual xG for, e.g., 1.014336 |
| 32 | `ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual xG for, e.g., 1.101715 |
| 33 | `base_ixg` | `Float64` | yes |  | Individual base xG for, only with ``base_xg`` |
| 34 | `base_ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual base xG for, only with ``base_xg`` |
| 35 | `context_ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual context xG for, only with ``context_xg`` |
| 36 | `context_ixg` | `Float64` | yes |  | Individual context xG for, only with ``context_xg`` |
| 37 | `isf` | `Int64` | no |  | Individual shots taken, e.g., 3 |
| 38 | `isf_adj` | `Float64` | no |  | Score- and venue-adjusted individual shots taken, e.g., 3.262966 |
| 39 | `ihdsf` | `Int64` | no |  | High-danger shots taken, e.g., 3 |
| 40 | `imsf` | `Int64` | no |  | Individual missed shots, e.g., 0 |
| 41 | `imsf_adj` | `Float64` | no |  | Score- and venue-adjusted individual missed shots, e.g., 0.0 |
| 42 | `ihdm` | `Int64` | no |  | High-danger missed shots, e.g., 0 |
| 43 | `iff` | `Int64` | no |  | Individual fenwick for, e.g., 3 |
| 44 | `iff_adj` | `Float64` | no |  | Score- and venue-adjusted individual fenwick events, e.g., 3.279018 |
| 45 | `ihdf` | `Int64` | no |  | High-danger fenwick events for, e.g., 3 |
| 46 | `isb` | `Int64` | no |  | Shots taken that were blocked, e.g., 0 |
| 47 | `isb_adj` | `Float64` | no |  | Score- and venue-adjusted individual shots blocked, e.g., 0.0 |
| 48 | `icf` | `Int64` | no |  | Individual corsi for, e.g., 3 |
| 49 | `icf_adj` | `Float64` | no |  | Score- and venue-adjusted individual corsi events, e.g., 3.279018 |
| 50 | `ibs` | `Int64` | no |  | Individual shots blocked on defense, e.g., 0 |
| 51 | `ibs_adj` | `Float64` | no |  | Score- and venue-adjusted shots blocked, e.g., 0.0 |
| 52 | `igive` | `Int64` | no |  | Individual giveaways, e.g., 0 |
| 53 | `itake` | `Int64` | no |  | Individual takeaways, e.g., 0 |
| 54 | `ihf` | `Int64` | no |  | Individual hits for, e.g., 0 |
| 55 | `iht` | `Int64` | no |  | Individual hits taken, e.g., 0 |
| 56 | `ifow` | `Int64` | no |  | Individual faceoffs won, e.g., 0 |
| 57 | `ifol` | `Int64` | no |  | Individual faceoffs lost, e.g., 0 |
| 58 | `iozfw` | `Int64` | no |  | Individual faceoffs won in offensive zone, e.g., 0 |
| 59 | `iozfl` | `Int64` | no |  | Individual faceoffs lost in offensive zone, e.g., 0 |
| 60 | `inzfw` | `Int64` | no |  | Individual faceoffs won in neutral zone, e.g., 0 |
| 61 | `inzfl` | `Int64` | no |  | Individual faceoffs lost in neutral zone, e.g., 0 |
| 62 | `idzfw` | `Int64` | no |  | Individual faceoffs won in defensive zone, e.g., 0 |
| 63 | `idzfl` | `Int64` | no |  | Individual faceoffs lost in defensive zone, e.g., 0 |
| 64 | `a1_xg` | `Float64` | yes |  | xG on primary assists, e.g., 0 |
| 65 | `a2_xg` | `Float64` | yes |  | xG on secondary assists, e.g., 0 |
| 66 | `ipent0` | `Int64` | no |  | Individual penalty shots against, e.g., 0 |
| 67 | `ipent2` | `Int64` | no |  | Individual minor penalties taken, e.g., 0 |
| 68 | `ipent4` | `Int64` | no |  | Individual double minor penalties taken, e.g., 0 |
| 69 | `ipent5` | `Int64` | no |  | Individual major penalties taken, e.g., 0 |
| 70 | `ipent10` | `Int64` | no |  | Individual 10-minute penalties taken, such as misconducts, e.g., 0 |
| 71 | `ipend0` | `Int64` | no |  | Individual penalty shots drawn, e.g., 0 |
| 72 | `ipend2` | `Int64` | no |  | Individual minor penalties drawn, e.g., 0 |
| 73 | `ipend4` | `Int64` | no |  | Individual double minor penalties drawn, e.g., 0 |
| 74 | `ipend5` | `Int64` | no |  | Individual major penalties drawn, e.g., 0 |
| 75 | `ipend10` | `Int64` | no |  | Individual 10-minute penalties drawn, such as misconducts, e.g., 0 |
