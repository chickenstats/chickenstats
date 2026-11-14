---
icon: material/table
description: "Columns, dtypes and nullability of oi_stats in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: oi_stats**

Returned by `evolving_hockey.prep_oi`. See [Output schemas](index.md) for what these columns promise.

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
| 26 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
| 27 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 28 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 29 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 30 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 31 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 32 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 33 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 34 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 35 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 36 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 37 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 38 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 39 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 40 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 41 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 42 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 43 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 44 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 45 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 46 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 47 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 48 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 49 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 50 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 51 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 52 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 53 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 54 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 55 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 56 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 57 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 58 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 59 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 60 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 61 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 62 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 63 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 64 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 65 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 66 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 67 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 68 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 69 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 70 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 71 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 72 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 73 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 74 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 75 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 76 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 77 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 78 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 79 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 80 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 81 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 82 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 83 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 84 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 85 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 86 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 87 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 88 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 89 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 90 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 91 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 92 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 93 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 94 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 95 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 96 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 97 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 98 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 99 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 100 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 101 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 102 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 103 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
