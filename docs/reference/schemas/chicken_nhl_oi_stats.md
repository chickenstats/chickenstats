---
icon: material/table
description: "Columns, dtypes and nullability of oi_stats in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: oi_stats**

Returned by `Scraper.oi_stats`, `prep_oi`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 for 2023-24 season |
| 2 | `session` | `String` | no |  | Whether games are regular season, playoffs, or pre-season, e.g., R; not at season level |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2023020001 |
| 4 | `game_date` | `String` | no |  | Date game was played, e.g., 2023-10-10 |
| 5 | `player` | `String` | no |  | Player's name, e.g., FILIP FORSBERG |
| 6 | `eh_id` | `String` | no |  | Evolving Hockey ID for the player, e.g., FILIP.FORSBERG |
| 7 | `api_id` | `Int64` | no |  | NHL API ID for the player, e.g., 8476887 |
| 8 | `position` | `String` | no |  | Player's position, e.g., L |
| 9 | `team` | `String` | no |  | Player's team, e.g., NSH |
| 10 | `opp_team` | `String` | no |  | Opposing team, e.g., TBL |
| 11 | `strength_state` | `String` | no |  | Strength state, e.g., 5v5 |
| 12 | `period` | `Int64` | no |  | Period, e.g., 3 |
| 13 | `score_state` | `String` | no |  | Score state, e.g., 2v1 |
| 14 | `forwards` | `String` | yes |  | Forward teammates, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY |
| 15 | `forwards_eh_id` | `String` | yes |  | Forward teammates' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY |
| 16 | `forwards_api_id` | `String` | yes |  | Forward teammates' NHL API IDs, e.g., 8476887, 8481704, 8475158 |
| 17 | `defense` | `String` | yes |  | Defense teammates, e.g., RYAN MCDONAGH, ALEX CARRIER |
| 18 | `defense_eh_id` | `String` | yes |  | Defense teammates' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER |
| 19 | `defense_api_id` | `String` | yes |  | Defense teammates' NHL API IDs, e.g., 8474151, 8478851 |
| 20 | `own_goalie` | `String` | yes |  | Own goalie, e.g., JUUSE SAROS |
| 21 | `own_goalie_eh_id` | `String` | yes |  | Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS |
| 22 | `own_goalie_api_id` | `Int64` | yes |  | Own goalie's NHL API ID, e.g., 8477424 |
| 23 | `opp_forwards` | `String` | yes |  | Opposing forwards, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS |
| 24 | `opp_forwards_eh_id` | `String` | yes |  | Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS |
| 25 | `opp_forwards_api_id` | `String` | yes |  | Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564 |
| 26 | `opp_defense` | `String` | yes |  | Opposing defense, e.g., NICK PERBIX, VICTOR HEDMAN |
| 27 | `opp_defense_eh_id` | `String` | yes |  | Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN |
| 28 | `opp_defense_api_id` | `String` | yes |  | Opposing defense's NHL API IDs, e.g., 8480246, 8475167 |
| 29 | `opp_goalie` | `String` | yes |  | Opposing goalie, e.g., JONAS JOHANSSON |
| 30 | `opp_goalie_eh_id` | `String` | yes |  | Opposing goalie's Evolving Hockey ID, e.g., JONAS.JOHANSSON |
| 31 | `opp_goalie_api_id` | `Int64` | yes |  | Opposing goalie's NHL API ID, e.g., 8477992 |
| 32 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
| 33 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 34 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 35 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 36 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 37 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 38 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 39 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 40 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 41 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 42 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 43 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 44 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 45 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 46 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 47 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 48 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 49 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 50 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 51 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 52 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 53 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 54 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 55 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 56 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 57 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 58 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 59 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 60 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 61 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 62 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 63 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 64 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 65 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 66 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 67 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 68 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 69 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 70 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 71 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 72 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 73 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 74 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 75 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 76 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 77 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 78 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 79 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 80 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 81 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 82 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 83 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 84 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 85 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 86 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 87 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 88 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 89 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 90 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 91 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 92 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 93 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 94 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 95 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 96 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 97 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 98 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 99 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 100 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 101 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 102 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 103 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 104 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 105 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 106 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 107 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 108 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 109 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
