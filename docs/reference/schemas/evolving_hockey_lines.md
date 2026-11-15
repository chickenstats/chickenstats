---
icon: material/table
description: "Columns, dtypes and nullability of lines in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: lines**

Returned by `evolving_hockey.prep_lines`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 for 2023-24 season |
| 2 | `session` | `String` | no |  | Whether games are regular season, playoffs, or pre-season, e.g., R; not at season level |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2023020001 |
| 4 | `game_date` | `String` | no |  | Date game was played, e.g., 2023-10-10 |
| 5 | `team` | `String` | no |  | Team, e.g., NSH |
| 6 | `opp_team` | `String` | no |  | Opposing team, e.g., TBL |
| 7 | `strength_state` | `String` | no |  | Strength state, e.g., 5v5 |
| 8 | `period` | `Int64` | no |  | Period, e.g., 3 |
| 9 | `score_state` | `String` | no |  | Score state, e.g., 2v1 |
| 10 | `forwards` | `String` | yes |  | Forward line members, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY |
| 11 | `forwards_eh_id` | `String` | yes |  | Forward line members' Evolving Hockey IDs, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY |
| 12 | `defense` | `String` | yes |  | Defense pair members, e.g., RYAN MCDONAGH, ALEX CARRIER |
| 13 | `defense_eh_id` | `String` | yes |  | Defense pair members' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER |
| 14 | `own_goalie` | `String` | yes |  | Own goalie, e.g., JUUSE SAROS |
| 15 | `own_goalie_eh_id` | `String` | yes |  | Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS |
| 16 | `opp_forwards` | `String` | yes |  | Opposing forwards, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS |
| 17 | `opp_forwards_eh_id` | `String` | yes |  | Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS |
| 18 | `opp_defense` | `String` | yes |  | Opposing defense, e.g., NICK PERBIX, VICTOR HEDMAN |
| 19 | `opp_defense_eh_id` | `String` | yes |  | Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN |
| 20 | `opp_goalie` | `String` | yes |  | Opposing goalie, e.g., JONAS JOHANSSON |
| 21 | `opp_goalie_eh_id` | `String` | yes |  | Opposing goalie's Evolving Hockey ID, e.g., JONAS.JOHANSSON |
| 22 | `games_played` | `Int64` | no |  | Number of games the row covers; 1 at game level. A game counts when the row's player, line or team has ice time or an event in it, the same games its stats are summed from, e.g., 1 |
| 23 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
| 24 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 25 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 26 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 27 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 28 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 29 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 30 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 31 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 32 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 33 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 34 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 35 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 36 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 37 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 38 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 39 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 40 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 41 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 42 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 43 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 44 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 45 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 46 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 47 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 48 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 49 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 50 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 51 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 52 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 53 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 54 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 55 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 56 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 57 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 58 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 59 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 60 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 61 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 62 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 63 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 64 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 65 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 66 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 67 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 68 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 69 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 70 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 71 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 72 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 73 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 74 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 75 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 76 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 77 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 78 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 79 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 80 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 81 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 82 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 83 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 84 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 85 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 86 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 87 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 88 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 89 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 90 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 91 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 92 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 93 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 94 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 95 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 96 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 97 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 98 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 99 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 100 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
| 101 | `gf_p60` | `Float64` | yes | per 60 minutes | Goals for (on-ice) per 60 minutes |
| 102 | `ga_p60` | `Float64` | yes | per 60 minutes | Goals against (on-ice) per 60 minutes |
| 103 | `gf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals for (on-ice) per 60 minutes |
| 104 | `ga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals against (on-ice) per 60 minutes |
| 105 | `hdgf_p60` | `Float64` | yes | per 60 minutes | High-danger goals for (on-ice) per 60 minutes |
| 106 | `hdga_p60` | `Float64` | yes | per 60 minutes | High-danger goals against (on-ice) per 60 minutes |
| 107 | `xgf_p60` | `Float64` | yes | per 60 minutes | xG for (on-ice) per 60 minutes |
| 108 | `xga_p60` | `Float64` | yes | per 60 minutes | xG against (on-ice) per 60 minutes |
| 109 | `xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG for (on-ice) per 60 minutes |
| 110 | `xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG against (on-ice) per 60 minutes |
| 111 | `base_xgf_p60` | `Float64` | yes | per 60 minutes | Base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 112 | `base_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 113 | `context_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 114 | `base_xga_p60` | `Float64` | yes | per 60 minutes | Base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 115 | `base_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 116 | `context_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 117 | `context_xgf_p60` | `Float64` | yes | per 60 minutes | Context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 118 | `context_xga_p60` | `Float64` | yes | per 60 minutes | Context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 119 | `sf_p60` | `Float64` | yes | per 60 minutes | Shots for (on-ice) per 60 minutes |
| 120 | `sa_p60` | `Float64` | yes | per 60 minutes | Shots against (on-ice) per 60 minutes |
| 121 | `sf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots for (on-ice) per 60 minutes |
| 122 | `sa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots against (on-ice) per 60 minutes |
| 123 | `hdsf_p60` | `Float64` | yes | per 60 minutes | High-danger shots for (on-ice) per 60 minutes |
| 124 | `hdsa_p60` | `Float64` | yes | per 60 minutes | High-danger shots against (on-ice) per 60 minutes |
| 125 | `ff_p60` | `Float64` | yes | per 60 minutes | Fenwick for (on-ice) per 60 minutes |
| 126 | `fa_p60` | `Float64` | yes | per 60 minutes | Fenwick against (on-ice) per 60 minutes |
| 127 | `ff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick for (on-ice) per 60 minutes |
| 128 | `fa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick against (on-ice) per 60 minutes |
| 129 | `hdff_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick for (on-ice) per 60 minutes |
| 130 | `hdfa_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick against (on-ice) per 60 minutes |
| 131 | `cf_p60` | `Float64` | yes | per 60 minutes | Corsi for (on-ice) per 60 minutes |
| 132 | `ca_p60` | `Float64` | yes | per 60 minutes | Corsi against (on-ice) per 60 minutes |
| 133 | `cf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi for (on-ice) per 60 minutes |
| 134 | `ca_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi against (on-ice) per 60 minutes |
| 135 | `bsf_p60` | `Float64` | yes | per 60 minutes | Blocked shots for (on-ice) per 60 minutes |
| 136 | `bsa_p60` | `Float64` | yes | per 60 minutes | Blocked shots against (on-ice) per 60 minutes |
| 137 | `bsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots for (on-ice) per 60 minutes |
| 138 | `bsa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots against (on-ice) per 60 minutes |
| 139 | `msf_p60` | `Float64` | yes | per 60 minutes | Missed shots for (on-ice) per 60 minutes |
| 140 | `msa_p60` | `Float64` | yes | per 60 minutes | Missed shots against (on-ice) per 60 minutes |
| 141 | `msf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots for (on-ice) per 60 minutes |
| 142 | `msa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots against (on-ice) per 60 minutes |
| 143 | `hdmsf_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots for (on-ice) per 60 minutes |
| 144 | `hdmsa_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots against (on-ice) per 60 minutes |
| 145 | `teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts for blocked by a teammate (on-ice) per 60 minutes |
| 146 | `opp_teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts against blocked by one of the opponent's teammates (on-ice) per 60 minutes |
| 147 | `hf_p60` | `Float64` | yes | per 60 minutes | Hits for (on-ice) per 60 minutes |
| 148 | `ht_p60` | `Float64` | yes | per 60 minutes | Hits taken (on-ice) per 60 minutes |
| 149 | `pent0_p60` | `Float64` | yes | per 60 minutes | Penalty shots taken (on-ice) per 60 minutes |
| 150 | `pent2_p60` | `Float64` | yes | per 60 minutes | Minor penalties taken (on-ice) per 60 minutes |
| 151 | `pent4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties taken (on-ice) per 60 minutes |
| 152 | `pent5_p60` | `Float64` | yes | per 60 minutes | Major penalties taken (on-ice) per 60 minutes |
| 153 | `pent10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties taken (on-ice) per 60 minutes |
| 154 | `pend0_p60` | `Float64` | yes | per 60 minutes | Penalty shots drawn (on-ice) per 60 minutes |
| 155 | `pend2_p60` | `Float64` | yes | per 60 minutes | Minor penalties drawn (on-ice) per 60 minutes |
| 156 | `pend4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties drawn (on-ice) per 60 minutes |
| 157 | `pend5_p60` | `Float64` | yes | per 60 minutes | Major penalties drawn (on-ice) per 60 minutes |
| 158 | `pend10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties drawn (on-ice) per 60 minutes |
| 159 | `gf_percent` | `Float64` | yes | share, 0 to 1 | On-ice goals for as a share of all on-ice goals, from 0 to 1, i.e., GF / (GF + GA) |
| 160 | `gf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted goals for as a share of all on-ice adjusted goals, from 0 to 1 i.e., GF_adj / (GF_adj + GA_adj) |
| 161 | `hdgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger goals for as a share of all on-ice high-danger goals, from 0 to 1 i.e., HDGF / (HDGF + HDGA) |
| 162 | `xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice xG for as a share of all on-ice xG, from 0 to 1, i.e., xGF / (xGF + xGA) |
| 163 | `xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted xG for as a share of all on-ice adjusted xG, from 0 to 1 i.e., xGF_adj / (xGF_adj + xGA_adj) |
| 164 | `base_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice base xG for as a share of all on-ice base xG, from 0 to 1, only with ``base_xg`` i.e., base_xGF / (base_xGF + base_xGA) |
| 165 | `base_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted base xG for as a percentage of total on-ice adjusted base xG, only with ``base_xg`` i.e., base_xGF_adj / (base_xGF_adj + base_xGA_adj) |
| 166 | `context_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted context xG for as a percentage of total on-ice adjusted context xG, only with ``context_xg`` i.e., context_xGF_adj / (context_xGF_adj + context_xGA_adj) |
| 167 | `context_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice context xG for as a share of all on-ice context xG, from 0 to 1, only with ``context_xg`` i.e., context_xGF / (context_xGF + context_xGA) |
| 168 | `sf_percent` | `Float64` | yes | share, 0 to 1 | On-ice shots for as a share of all on-ice shots, from 0 to 1, i.e., SF / (SF + SA) |
| 169 | `sf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted shots for as a share of all on-ice adjusted shots, from 0 to 1 i.e., SF_adj / (SF_adj + SA_adj) |
| 170 | `hdsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger shots for as a share of all on-ice high-danger shots, from 0 to 1 i.e., HDSF / (HDSF + HDSA) |
| 171 | `ff_percent` | `Float64` | yes | share, 0 to 1 | On-ice fenwick for as a share of all on-ice fenwick, from 0 to 1, i.e., FF / (FF + FA) |
| 172 | `ff_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted fenwick for as a share of all on-ice adjusted fenwick, from 0 to 1 i.e., FF_adj / (FF_adj + FA_adj) |
| 173 | `hdff_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger fenwick for as a share of all on-ice high-danger fenwick, from 0 to 1 i.e., HDFF / (HDFF + HDFA) |
| 174 | `cf_percent` | `Float64` | yes | share, 0 to 1 | On-ice corsi for as a share of all on-ice corsi, from 0 to 1, i.e., CF / (CF + CA) |
| 175 | `cf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted corsi for as a share of all on-ice adjusted corsi, from 0 to 1 i.e., CF_adj / (CF_adj + CA_adj) |
| 176 | `bsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice blocked shots for as a share of all on-ice blocked shots, from 0 to 1, i.e., BSF / (BSF + BSA) |
| 177 | `bsf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted blocked shots for as a share of all on-ice adjusted blocked shots, from 0 to 1 i.e., BSF_adj / (BSF_adj + BSA_adj) |
| 178 | `msf_percent` | `Float64` | yes | share, 0 to 1 | On-ice missed shots for as a share of all on-ice missed shots, from 0 to 1, i.e., MSF / (MSF + MSA) |
| 179 | `msf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted missed shots for as a share of all on-ice adjusted missed shots, from 0 to 1 i.e., MSF_adj / (MSF_adj + MSA_adj) |
| 180 | `hdmsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger missed shots for as a share of all on-ice high-danger missed shots, from 0 to 1 i.e., HDMSF / (HDMSF + HDMSA) |
| 181 | `hf_percent` | `Float64` | yes | share, 0 to 1 | On-ice hits for as a share of all on-ice hits, from 0 to 1, i.e., HF / (HF + HT) |
| 182 | `take_percent` | `Float64` | yes | share, 0 to 1 | On-ice takeaways as a share of all on-ice giveaways and takeaways, from 0 to 1 i.e., take / (take + give) |
