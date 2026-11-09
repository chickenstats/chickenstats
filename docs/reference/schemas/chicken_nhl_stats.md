---
icon: material/table
description: "Columns, dtypes and nullability of stats in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: stats**

Returned by `Scraper.stats`, `prep_stats`. See [Output schemas](index.md) for what these columns promise.

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
| 33 | `g` | `Int64` | no |  | Individual goals scored, e.g., 0 |
| 34 | `g_adj` | `Float64` | no |  | Score- and venue-adjusted individual goals scored, e.g., 0.0 |
| 35 | `ihdg` | `Int64` | no |  | Individual high-danger goals scored, e.g., 0 |
| 36 | `a1` | `Int64` | no |  | Individual primary assists, e.g., 0 |
| 37 | `a2` | `Int64` | no |  | Individual secondary assists, e.g., 0 |
| 38 | `ixg` | `Float64` | yes |  | Individual xG for, e.g., 1.014336 |
| 39 | `ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual xG for, e.g., 1.101715 |
| 40 | `base_ixg` | `Float64` | yes |  | Individual base xG for, only with ``base_xg`` |
| 41 | `base_ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual base xG for, only with ``base_xg`` |
| 42 | `context_ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual context xG for, only with ``context_xg`` |
| 43 | `context_ixg` | `Float64` | yes |  | Individual context xG for, only with ``context_xg`` |
| 44 | `isf` | `Int64` | no |  | Individual shots taken, e.g., 3 |
| 45 | `isf_adj` | `Float64` | no |  | Score- and venue-adjusted individual shots taken, e.g., 3.262966 |
| 46 | `ihdsf` | `Int64` | no |  | High-danger shots taken, e.g., 3 |
| 47 | `imsf` | `Int64` | no |  | Individual missed shots, e.g., 0 |
| 48 | `imsf_adj` | `Float64` | no |  | Score- and venue-adjusted individual missed shots, e.g., 0.0 |
| 49 | `ihdm` | `Int64` | no |  | High-danger missed shots, e.g., 0 |
| 50 | `iff` | `Int64` | no |  | Individual fenwick for, e.g., 3 |
| 51 | `iff_adj` | `Float64` | no |  | Score- and venue-adjusted individual fenwick events, e.g., 3.279018 |
| 52 | `ihdf` | `Int64` | no |  | High-danger fenwick events for, e.g., 3 |
| 53 | `isb` | `Int64` | no |  | Shots taken that were blocked, e.g., 0 |
| 54 | `isb_adj` | `Float64` | no |  | Score- and venue-adjusted individual shots blocked, e.g., 0.0 |
| 55 | `icf` | `Int64` | no |  | Individual corsi for, e.g., 3 |
| 56 | `icf_adj` | `Float64` | no |  | Score- and venue-adjusted individual corsi events, e.g., 3.279018 |
| 57 | `ibs` | `Int64` | no |  | Individual shots blocked on defense, e.g., 0 |
| 58 | `ibs_adj` | `Float64` | no |  | Score- and venue-adjusted shots blocked, e.g., 0.0 |
| 59 | `igive` | `Int64` | no |  | Individual giveaways, e.g., 0 |
| 60 | `itake` | `Int64` | no |  | Individual takeaways, e.g., 0 |
| 61 | `ihf` | `Int64` | no |  | Individual hits for, e.g., 0 |
| 62 | `iht` | `Int64` | no |  | Individual hits taken, e.g., 0 |
| 63 | `ifow` | `Int64` | no |  | Individual faceoffs won, e.g., 0 |
| 64 | `ifol` | `Int64` | no |  | Individual faceoffs lost, e.g., 0 |
| 65 | `iozfw` | `Int64` | no |  | Individual faceoffs won in offensive zone, e.g., 0 |
| 66 | `iozfl` | `Int64` | no |  | Individual faceoffs lost in offensive zone, e.g., 0 |
| 67 | `inzfw` | `Int64` | no |  | Individual faceoffs won in neutral zone, e.g., 0 |
| 68 | `inzfl` | `Int64` | no |  | Individual faceoffs lost in neutral zone, e.g., 0 |
| 69 | `idzfw` | `Int64` | no |  | Individual faceoffs won in defensive zone, e.g., 0 |
| 70 | `idzfl` | `Int64` | no |  | Individual faceoffs lost in defensive zone, e.g., 0 |
| 71 | `a1_xg` | `Float64` | yes |  | xG on primary assists, e.g., 0 |
| 72 | `a2_xg` | `Float64` | yes |  | xG on secondary assists, e.g., 0 |
| 73 | `ipent0` | `Int64` | no |  | Individual penalty shots against, e.g., 0 |
| 74 | `ipent2` | `Int64` | no |  | Individual minor penalties taken, e.g., 0 |
| 75 | `ipent4` | `Int64` | no |  | Individual double minor penalties taken, e.g., 0 |
| 76 | `ipent5` | `Int64` | no |  | Individual major penalties taken, e.g., 0 |
| 77 | `ipent10` | `Int64` | no |  | Individual 10-minute penalties taken, such as misconducts, e.g., 0 |
| 78 | `ipend0` | `Int64` | no |  | Individual penalty shots drawn, e.g., 0 |
| 79 | `ipend2` | `Int64` | no |  | Individual minor penalties drawn, e.g., 0 |
| 80 | `ipend4` | `Int64` | no |  | Individual double minor penalties drawn, e.g., 0 |
| 81 | `ipend5` | `Int64` | no |  | Individual major penalties drawn, e.g., 0 |
| 82 | `ipend10` | `Int64` | no |  | Individual 10-minute penalties drawn, such as misconducts, e.g., 0 |
| 83 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 84 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 85 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 86 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 87 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 88 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 89 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 90 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 91 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 92 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 93 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 94 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 95 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 96 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 97 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 98 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 99 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 100 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 101 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 102 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 103 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 104 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 105 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 106 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 107 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 108 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 109 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 110 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 111 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 112 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 113 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 114 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 115 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 116 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 117 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 118 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 119 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 120 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 121 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 122 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 123 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 124 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 125 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 126 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 127 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 128 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 129 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 130 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 131 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 132 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 133 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 134 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 135 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 136 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 137 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 138 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 139 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 140 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 141 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 142 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 143 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 144 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 145 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 146 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 147 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 148 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 149 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 150 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 151 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 152 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 153 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 154 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 155 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 156 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 157 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 158 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 159 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
| 160 | `g_p60` | `Float64` | yes | per 60 minutes | Goals scored per 60 minutes |
| 161 | `g_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals scored per 60 minutes |
| 162 | `ihdg_p60` | `Float64` | yes | per 60 minutes | Individual high-danger goals scored per 60 minutes |
| 163 | `a1_p60` | `Float64` | yes | per 60 minutes | Primary assists per 60 minutes |
| 164 | `a2_p60` | `Float64` | yes | per 60 minutes | Secondary assists per 60 minutes |
| 165 | `ixg_p60` | `Float64` | yes | per 60 minutes | Individual xG for per 60 minutes |
| 166 | `ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual xG for per 60 minutes |
| 167 | `base_ixg_p60` | `Float64` | yes | per 60 minutes | Individual base xG for per 60 minutes, only with ``base_xg`` |
| 168 | `base_ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual base xG for per 60 minutes, only with ``base_xg`` |
| 169 | `context_ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual context xG for per 60 minutes, only with ``context_xg`` |
| 170 | `context_ixg_p60` | `Float64` | yes | per 60 minutes | Individual context xG for per 60 minutes, only with ``context_xg`` |
| 171 | `isf_p60` | `Float64` | yes | per 60 minutes | Individual shots for per 60 minutes |
| 172 | `isf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual shots for per 60 minutes |
| 173 | `ihdsf_p60` | `Float64` | yes | per 60 minutes | Individual high-danger shots for per 60 minutes |
| 174 | `imsf_p60` | `Float64` | yes | per 60 minutes | Individual missed shots for per 60 minutes |
| 175 | `imsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual missed shots for per 60 minutes |
| 176 | `ihdm_p60` | `Float64` | yes | per 60 minutes | Individual high-danger missed shots for per 60 minutes |
| 177 | `iff_p60` | `Float64` | yes | per 60 minutes | Individual fenwick for per 60 minutes |
| 178 | `iff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual fenwick for per 60 minutes |
| 179 | `ihdf_p60` | `Float64` | yes | per 60 minutes | Individual high-danger fenwick for per 60 minutes |
| 180 | `isb_p60` | `Float64` | yes | per 60 minutes | Individual shots blocked (for) per 60 minutes |
| 181 | `isb_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual shots blocked (for) per 60 minutes |
| 182 | `icf_p60` | `Float64` | yes | per 60 minutes | Individual corsi for per 60 minutes |
| 183 | `icf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual corsi for per 60 minutes |
| 184 | `ibs_p60` | `Float64` | yes | per 60 minutes | Individual blocked shots (against) per 60 minutes |
| 185 | `ibs_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual blocked shots (against) per 60 minutes |
| 186 | `igive_p60` | `Float64` | yes | per 60 minutes | Individual giveaways per 60 minutes |
| 187 | `itake_p60` | `Float64` | yes | per 60 minutes | Individual takeaways per 60 minutes |
| 188 | `ihf_p60` | `Float64` | yes | per 60 minutes | Individual hits for per 60 minutes |
| 189 | `iht_p60` | `Float64` | yes | per 60 minutes | Individual hits taken per 60 minutes |
| 190 | `a1_xg_p60` | `Float64` | yes | per 60 minutes | Individual primary assists' xG per 60 minutes |
| 191 | `a2_xg_p60` | `Float64` | yes | per 60 minutes | Individual secondary assists' xG per 60 minutes |
| 192 | `ipent0_p60` | `Float64` | yes | per 60 minutes | Individual penalty shots taken per 60 minutes |
| 193 | `ipent2_p60` | `Float64` | yes | per 60 minutes | Individual minor penalties taken per 60 minutes |
| 194 | `ipent4_p60` | `Float64` | yes | per 60 minutes | Individual double minor penalties taken per 60 minutes |
| 195 | `ipent5_p60` | `Float64` | yes | per 60 minutes | Individual major penalties taken per 60 minutes |
| 196 | `ipent10_p60` | `Float64` | yes | per 60 minutes | Individual 10-minute penalties taken per 60 minutes |
| 197 | `ipend0_p60` | `Float64` | yes | per 60 minutes | Individual penalty shots drawn per 60 minutes |
| 198 | `ipend2_p60` | `Float64` | yes | per 60 minutes | Individual minor penalties drawn per 60 minutes |
| 199 | `ipend4_p60` | `Float64` | yes | per 60 minutes | Individual double minor penalties drawn per 60 minutes |
| 200 | `ipend5_p60` | `Float64` | yes | per 60 minutes | Individual major penalties drawn per 60 minutes |
| 201 | `ipend10_p60` | `Float64` | yes | per 60 minutes | Individual 10-minute penalties drawn per 60 minutes |
| 202 | `gf_p60` | `Float64` | yes | per 60 minutes | Goals for (on-ice) per 60 minutes |
| 203 | `ga_p60` | `Float64` | yes | per 60 minutes | Goals against (on-ice) per 60 minutes |
| 204 | `gf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals for (on-ice) per 60 minutes |
| 205 | `ga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals against (on-ice) per 60 minutes |
| 206 | `hdgf_p60` | `Float64` | yes | per 60 minutes | High-danger goals for (on-ice) per 60 minutes |
| 207 | `hdga_p60` | `Float64` | yes | per 60 minutes | High-danger goals against (on-ice) per 60 minutes |
| 208 | `xgf_p60` | `Float64` | yes | per 60 minutes | xG for (on-ice) per 60 minutes |
| 209 | `xga_p60` | `Float64` | yes | per 60 minutes | xG against (on-ice) per 60 minutes |
| 210 | `xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG for (on-ice) per 60 minutes |
| 211 | `xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG against (on-ice) per 60 minutes |
| 212 | `base_xgf_p60` | `Float64` | yes | per 60 minutes | Base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 213 | `base_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 214 | `context_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 215 | `base_xga_p60` | `Float64` | yes | per 60 minutes | Base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 216 | `base_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 217 | `context_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 218 | `context_xgf_p60` | `Float64` | yes | per 60 minutes | Context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 219 | `context_xga_p60` | `Float64` | yes | per 60 minutes | Context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 220 | `sf_p60` | `Float64` | yes | per 60 minutes | Shots for (on-ice) per 60 minutes |
| 221 | `sa_p60` | `Float64` | yes | per 60 minutes | Shots against (on-ice) per 60 minutes |
| 222 | `sf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots for (on-ice) per 60 minutes |
| 223 | `sa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots against (on-ice) per 60 minutes |
| 224 | `hdsf_p60` | `Float64` | yes | per 60 minutes | High-danger shots for (on-ice) per 60 minutes |
| 225 | `hdsa_p60` | `Float64` | yes | per 60 minutes | High-danger shots against (on-ice) per 60 minutes |
| 226 | `ff_p60` | `Float64` | yes | per 60 minutes | Fenwick for (on-ice) per 60 minutes |
| 227 | `fa_p60` | `Float64` | yes | per 60 minutes | Fenwick against (on-ice) per 60 minutes |
| 228 | `ff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick for (on-ice) per 60 minutes |
| 229 | `fa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick against (on-ice) per 60 minutes |
| 230 | `hdff_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick for (on-ice) per 60 minutes |
| 231 | `hdfa_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick against (on-ice) per 60 minutes |
| 232 | `cf_p60` | `Float64` | yes | per 60 minutes | Corsi for (on-ice) per 60 minutes |
| 233 | `ca_p60` | `Float64` | yes | per 60 minutes | Corsi against (on-ice) per 60 minutes |
| 234 | `cf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi for (on-ice) per 60 minutes |
| 235 | `ca_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi against (on-ice) per 60 minutes |
| 236 | `bsf_p60` | `Float64` | yes | per 60 minutes | Blocked shots for (on-ice) per 60 minutes |
| 237 | `bsa_p60` | `Float64` | yes | per 60 minutes | Blocked shots against (on-ice) per 60 minutes |
| 238 | `bsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots for (on-ice) per 60 minutes |
| 239 | `bsa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots against (on-ice) per 60 minutes |
| 240 | `msf_p60` | `Float64` | yes | per 60 minutes | Missed shots for (on-ice) per 60 minutes |
| 241 | `msa_p60` | `Float64` | yes | per 60 minutes | Missed shots against (on-ice) per 60 minutes |
| 242 | `msf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots for (on-ice) per 60 minutes |
| 243 | `msa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots against (on-ice) per 60 minutes |
| 244 | `hdmsf_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots for (on-ice) per 60 minutes |
| 245 | `hdmsa_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots against (on-ice) per 60 minutes |
| 246 | `teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts for blocked by a teammate (on-ice) per 60 minutes |
| 247 | `opp_teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts against blocked by one of the opponent's teammates (on-ice) per 60 minutes |
| 248 | `hf_p60` | `Float64` | yes | per 60 minutes | Hits for (on-ice) per 60 minutes |
| 249 | `ht_p60` | `Float64` | yes | per 60 minutes | Hits taken (on-ice) per 60 minutes |
| 250 | `pent0_p60` | `Float64` | yes | per 60 minutes | Penalty shots taken (on-ice) per 60 minutes |
| 251 | `pent2_p60` | `Float64` | yes | per 60 minutes | Minor penalties taken (on-ice) per 60 minutes |
| 252 | `pent4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties taken (on-ice) per 60 minutes |
| 253 | `pent5_p60` | `Float64` | yes | per 60 minutes | Major penalties taken (on-ice) per 60 minutes |
| 254 | `pent10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties taken (on-ice) per 60 minutes |
| 255 | `pend0_p60` | `Float64` | yes | per 60 minutes | Penalty shots drawn (on-ice) per 60 minutes |
| 256 | `pend2_p60` | `Float64` | yes | per 60 minutes | Minor penalties drawn (on-ice) per 60 minutes |
| 257 | `pend4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties drawn (on-ice) per 60 minutes |
| 258 | `pend5_p60` | `Float64` | yes | per 60 minutes | Major penalties drawn (on-ice) per 60 minutes |
| 259 | `pend10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties drawn (on-ice) per 60 minutes |
| 260 | `gf_percent` | `Float64` | yes | share, 0 to 1 | On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA) |
| 261 | `gf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted goals for as a percentage of total on-ice adjusted goals i.e., GF_adj / (GF_adj + GA_adj) |
| 262 | `hdgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA) |
| 263 | `xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + xGA) |
| 264 | `xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted xG for as a percentage of total on-ice adjusted xG i.e., xGF_adj / (xGF_adj + xGA_adj) |
| 265 | `base_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice base xG for as a percentage of total on-ice base xG, only with ``base_xg`` i.e., base_xGF / (base_xGF + base_xGA) |
| 266 | `base_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted base xG for as a percentage of total on-ice adjusted base xG, only with ``base_xg`` i.e., base_xGF_adj / (base_xGF_adj + base_xGA_adj) |
| 267 | `context_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted context xG for as a percentage of total on-ice adjusted context xG, only with ``context_xg`` i.e., context_xGF_adj / (context_xGF_adj + context_xGA_adj) |
| 268 | `context_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice context xG for as a percentage of total on-ice context xG, only with ``context_xg`` i.e., context_xGF / (context_xGF + context_xGA) |
| 269 | `sf_percent` | `Float64` | yes | share, 0 to 1 | On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA) |
| 270 | `sf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted shots for as a percentage of total on-ice adjusted shots i.e., SF_adj / (SF_adj + SA_adj) |
| 271 | `hdsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA) |
| 272 | `ff_percent` | `Float64` | yes | share, 0 to 1 | On-ice fenwick for as a percentage of total on-ice fenwick i.e., FF / (FF + FA) |
| 273 | `ff_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted fenwick for as a percentage of total on-ice adjusted fenwick i.e., FF_adj / (FF_adj + FA_adj) |
| 274 | `hdff_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA) |
| 275 | `cf_percent` | `Float64` | yes | share, 0 to 1 | On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA) |
| 276 | `cf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted corsi for as a percentage of total on-ice adjusted corsi i.e., CF_adj / (CF_adj + CA_adj) |
| 277 | `bsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA) |
| 278 | `bsf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted blocked shots for as a percentage of total on-ice adjusted blocked shots i.e., BSF_adj / (BSF_adj + BSA_adj) |
| 279 | `msf_percent` | `Float64` | yes | share, 0 to 1 | On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA) |
| 280 | `msf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted missed shots for as a percentage of total on-ice adjusted missed shots i.e., MSF_adj / (MSF_adj + MSA_adj) |
| 281 | `hdmsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA) |
| 282 | `hf_percent` | `Float64` | yes | share, 0 to 1 | On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT) |
| 283 | `take_percent` | `Float64` | yes | share, 0 to 1 | On-ice takeaways as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give) |
