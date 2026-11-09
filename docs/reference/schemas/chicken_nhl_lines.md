---
icon: material/table
description: "Columns, dtypes and nullability of lines in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: lines**

Returned by `Scraper.lines`, `prep_lines`. See [Output schemas](index.md) for what these columns promise.

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
| 12 | `forwards_api_id` | `String` | yes |  | Forward line members' NHL API IDs, e.g., 8476887, 8481704, 8475158 |
| 13 | `defense` | `String` | yes |  | Defense pair members, e.g., RYAN MCDONAGH, ALEX CARRIER |
| 14 | `defense_eh_id` | `String` | yes |  | Defense pair members' Evolving Hockey IDs, e.g., RYAN.MCDONAGH, ALEX.CARRIER |
| 15 | `defense_api_id` | `String` | yes |  | Defense pair members' NHL API IDs, e.g., 8474151, 8478851 |
| 16 | `own_goalie` | `String` | yes |  | Own goalie, e.g., JUUSE SAROS |
| 17 | `own_goalie_eh_id` | `String` | yes |  | Own goalie's Evolving Hockey ID, e.g., JUUSE.SAROS |
| 18 | `own_goalie_api_id` | `Int64` | yes |  | Own goalie's NHL API ID, e.g., 8477424 |
| 19 | `opp_forwards` | `String` | yes |  | Opposing forwards, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS |
| 20 | `opp_forwards_eh_id` | `String` | yes |  | Opposing forwards' Evolving Hockey IDs, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS |
| 21 | `opp_forwards_api_id` | `String` | yes |  | Opposing forwards' NHL API IDs, e.g., 8478010, 8476453, 8474564 |
| 22 | `opp_defense` | `String` | yes |  | Opposing defense, e.g., NICK PERBIX, VICTOR HEDMAN |
| 23 | `opp_defense_eh_id` | `String` | yes |  | Opposing defense's Evolving Hockey IDs, e.g., NICK.PERBIX, VICTOR.HEDMAN |
| 24 | `opp_defense_api_id` | `String` | yes |  | Opposing defense's NHL API IDs, e.g., 8480246, 8475167 |
| 25 | `opp_goalie` | `String` | yes |  | Opposing goalie, e.g., JONAS JOHANSSON |
| 26 | `opp_goalie_eh_id` | `String` | yes |  | Opposing goalie's Evolving Hockey ID, e.g., JONAS.JOHANSSON |
| 27 | `opp_goalie_api_id` | `Int64` | yes |  | Opposing goalie's NHL API ID, e.g., 8477992 |
| 28 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
| 29 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 30 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 31 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 32 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 33 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 34 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 35 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 36 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 37 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 38 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 39 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 40 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 41 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 42 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 43 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 44 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 45 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 46 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 47 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 48 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 49 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 50 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 51 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 52 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 53 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 54 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 55 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 56 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 57 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 58 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 59 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 60 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 61 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 62 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 63 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 64 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 65 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 66 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 67 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 68 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 69 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 70 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 71 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 72 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 73 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 74 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 75 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 76 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 77 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 78 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 79 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 80 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 81 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 82 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 83 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 84 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 85 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 86 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 87 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 88 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 89 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 90 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 91 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 92 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 93 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 94 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 95 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 96 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 97 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 98 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 99 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 100 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 101 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 102 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 103 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 104 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 105 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
| 106 | `gf_p60` | `Float64` | yes | per 60 minutes | Goals for (on-ice) per 60 minutes |
| 107 | `ga_p60` | `Float64` | yes | per 60 minutes | Goals against (on-ice) per 60 minutes |
| 108 | `gf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals for (on-ice) per 60 minutes |
| 109 | `ga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals against (on-ice) per 60 minutes |
| 110 | `hdgf_p60` | `Float64` | yes | per 60 minutes | High-danger goals for (on-ice) per 60 minutes |
| 111 | `hdga_p60` | `Float64` | yes | per 60 minutes | High-danger goals against (on-ice) per 60 minutes |
| 112 | `xgf_p60` | `Float64` | yes | per 60 minutes | xG for (on-ice) per 60 minutes |
| 113 | `xga_p60` | `Float64` | yes | per 60 minutes | xG against (on-ice) per 60 minutes |
| 114 | `xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG for (on-ice) per 60 minutes |
| 115 | `xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG against (on-ice) per 60 minutes |
| 116 | `base_xgf_p60` | `Float64` | yes | per 60 minutes | Base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 117 | `base_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 118 | `context_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 119 | `base_xga_p60` | `Float64` | yes | per 60 minutes | Base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 120 | `base_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 121 | `context_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 122 | `context_xgf_p60` | `Float64` | yes | per 60 minutes | Context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 123 | `context_xga_p60` | `Float64` | yes | per 60 minutes | Context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 124 | `sf_p60` | `Float64` | yes | per 60 minutes | Shots for (on-ice) per 60 minutes |
| 125 | `sa_p60` | `Float64` | yes | per 60 minutes | Shots against (on-ice) per 60 minutes |
| 126 | `sf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots for (on-ice) per 60 minutes |
| 127 | `sa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots against (on-ice) per 60 minutes |
| 128 | `hdsf_p60` | `Float64` | yes | per 60 minutes | High-danger shots for (on-ice) per 60 minutes |
| 129 | `hdsa_p60` | `Float64` | yes | per 60 minutes | High-danger shots against (on-ice) per 60 minutes |
| 130 | `ff_p60` | `Float64` | yes | per 60 minutes | Fenwick for (on-ice) per 60 minutes |
| 131 | `fa_p60` | `Float64` | yes | per 60 minutes | Fenwick against (on-ice) per 60 minutes |
| 132 | `ff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick for (on-ice) per 60 minutes |
| 133 | `fa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick against (on-ice) per 60 minutes |
| 134 | `hdff_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick for (on-ice) per 60 minutes |
| 135 | `hdfa_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick against (on-ice) per 60 minutes |
| 136 | `cf_p60` | `Float64` | yes | per 60 minutes | Corsi for (on-ice) per 60 minutes |
| 137 | `ca_p60` | `Float64` | yes | per 60 minutes | Corsi against (on-ice) per 60 minutes |
| 138 | `cf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi for (on-ice) per 60 minutes |
| 139 | `ca_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi against (on-ice) per 60 minutes |
| 140 | `bsf_p60` | `Float64` | yes | per 60 minutes | Blocked shots for (on-ice) per 60 minutes |
| 141 | `bsa_p60` | `Float64` | yes | per 60 minutes | Blocked shots against (on-ice) per 60 minutes |
| 142 | `bsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots for (on-ice) per 60 minutes |
| 143 | `bsa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots against (on-ice) per 60 minutes |
| 144 | `msf_p60` | `Float64` | yes | per 60 minutes | Missed shots for (on-ice) per 60 minutes |
| 145 | `msa_p60` | `Float64` | yes | per 60 minutes | Missed shots against (on-ice) per 60 minutes |
| 146 | `msf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots for (on-ice) per 60 minutes |
| 147 | `msa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots against (on-ice) per 60 minutes |
| 148 | `hdmsf_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots for (on-ice) per 60 minutes |
| 149 | `hdmsa_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots against (on-ice) per 60 minutes |
| 150 | `teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts for blocked by a teammate (on-ice) per 60 minutes |
| 151 | `opp_teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts against blocked by one of the opponent's teammates (on-ice) per 60 minutes |
| 152 | `hf_p60` | `Float64` | yes | per 60 minutes | Hits for (on-ice) per 60 minutes |
| 153 | `ht_p60` | `Float64` | yes | per 60 minutes | Hits taken (on-ice) per 60 minutes |
| 154 | `pent0_p60` | `Float64` | yes | per 60 minutes | Penalty shots taken (on-ice) per 60 minutes |
| 155 | `pent2_p60` | `Float64` | yes | per 60 minutes | Minor penalties taken (on-ice) per 60 minutes |
| 156 | `pent4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties taken (on-ice) per 60 minutes |
| 157 | `pent5_p60` | `Float64` | yes | per 60 minutes | Major penalties taken (on-ice) per 60 minutes |
| 158 | `pent10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties taken (on-ice) per 60 minutes |
| 159 | `pend0_p60` | `Float64` | yes | per 60 minutes | Penalty shots drawn (on-ice) per 60 minutes |
| 160 | `pend2_p60` | `Float64` | yes | per 60 minutes | Minor penalties drawn (on-ice) per 60 minutes |
| 161 | `pend4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties drawn (on-ice) per 60 minutes |
| 162 | `pend5_p60` | `Float64` | yes | per 60 minutes | Major penalties drawn (on-ice) per 60 minutes |
| 163 | `pend10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties drawn (on-ice) per 60 minutes |
| 164 | `gf_percent` | `Float64` | yes | share, 0 to 1 | On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA) |
| 165 | `gf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted goals for as a percentage of total on-ice adjusted goals i.e., GF_adj / (GF_adj + GA_adj) |
| 166 | `hdgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA) |
| 167 | `xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + xGA) |
| 168 | `xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted xG for as a percentage of total on-ice adjusted xG i.e., xGF_adj / (xGF_adj + xGA_adj) |
| 169 | `base_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice base xG for as a percentage of total on-ice base xG, only with ``base_xg`` i.e., base_xGF / (base_xGF + base_xGA) |
| 170 | `base_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted base xG for as a percentage of total on-ice adjusted base xG, only with ``base_xg`` i.e., base_xGF_adj / (base_xGF_adj + base_xGA_adj) |
| 171 | `context_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted context xG for as a percentage of total on-ice adjusted context xG, only with ``context_xg`` i.e., context_xGF_adj / (context_xGF_adj + context_xGA_adj) |
| 172 | `context_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice context xG for as a percentage of total on-ice context xG, only with ``context_xg`` i.e., context_xGF / (context_xGF + context_xGA) |
| 173 | `sf_percent` | `Float64` | yes | share, 0 to 1 | On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA) |
| 174 | `sf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted shots for as a percentage of total on-ice adjusted shots i.e., SF_adj / (SF_adj + SA_adj) |
| 175 | `hdsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA) |
| 176 | `ff_percent` | `Float64` | yes | share, 0 to 1 | On-ice fenwick for as a percentage of total on-ice fenwick i.e., FF / (FF + FA) |
| 177 | `ff_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted fenwick for as a percentage of total on-ice adjusted fenwick i.e., FF_adj / (FF_adj + FA_adj) |
| 178 | `hdff_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA) |
| 179 | `cf_percent` | `Float64` | yes | share, 0 to 1 | On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA) |
| 180 | `cf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted corsi for as a percentage of total on-ice adjusted corsi i.e., CF_adj / (CF_adj + CA_adj) |
| 181 | `bsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA) |
| 182 | `bsf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted blocked shots for as a percentage of total on-ice adjusted blocked shots i.e., BSF_adj / (BSF_adj + BSA_adj) |
| 183 | `msf_percent` | `Float64` | yes | share, 0 to 1 | On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA) |
| 184 | `msf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted missed shots for as a percentage of total on-ice adjusted missed shots i.e., MSF_adj / (MSF_adj + MSA_adj) |
| 185 | `hdmsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA) |
| 186 | `hf_percent` | `Float64` | yes | share, 0 to 1 | On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT) |
| 187 | `take_percent` | `Float64` | yes | share, 0 to 1 | On-ice takeaways as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give) |
