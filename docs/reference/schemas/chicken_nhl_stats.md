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
| 32 | `games_played` | `Int64` | no |  | Number of games the row covers; 1 at game level. A game counts when the row's player, line or team has ice time or an event in it, the same games its stats are summed from, e.g., 1 |
| 33 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
| 34 | `g` | `Int64` | no |  | Individual goals scored, e.g., 0 |
| 35 | `g_adj` | `Float64` | no |  | Score- and venue-adjusted individual goals scored, e.g., 0.0 |
| 36 | `ihdg` | `Int64` | no |  | Individual high-danger goals scored, e.g., 0 |
| 37 | `a1` | `Int64` | no |  | Individual primary assists, e.g., 0 |
| 38 | `a2` | `Int64` | no |  | Individual secondary assists, e.g., 0 |
| 39 | `ixg` | `Float64` | yes |  | Individual xG for, e.g., 1.014336 |
| 40 | `ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual xG for, e.g., 1.101715 |
| 41 | `base_ixg` | `Float64` | yes |  | Individual base xG for, only with ``base_xg`` |
| 42 | `base_ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual base xG for, only with ``base_xg`` |
| 43 | `context_ixg_adj` | `Float64` | yes |  | Score- and venue-adjusted individual context xG for, only with ``context_xg`` |
| 44 | `context_ixg` | `Float64` | yes |  | Individual context xG for, only with ``context_xg`` |
| 45 | `isf` | `Int64` | no |  | Individual shots taken, e.g., 3 |
| 46 | `isf_adj` | `Float64` | no |  | Score- and venue-adjusted individual shots taken, e.g., 3.262966 |
| 47 | `ihdsf` | `Int64` | no |  | High-danger shots taken, e.g., 3 |
| 48 | `imsf` | `Int64` | no |  | Individual missed shots, e.g., 0 |
| 49 | `imsf_adj` | `Float64` | no |  | Score- and venue-adjusted individual missed shots, e.g., 0.0 |
| 50 | `ihdm` | `Int64` | no |  | High-danger missed shots, e.g., 0 |
| 51 | `iff` | `Int64` | no |  | Individual fenwick for, e.g., 3 |
| 52 | `iff_adj` | `Float64` | no |  | Score- and venue-adjusted individual fenwick events, e.g., 3.279018 |
| 53 | `ihdf` | `Int64` | no |  | High-danger fenwick events for, e.g., 3 |
| 54 | `isb` | `Int64` | no |  | Shots taken that were blocked, e.g., 0 |
| 55 | `isb_adj` | `Float64` | no |  | Score- and venue-adjusted individual shots blocked, e.g., 0.0 |
| 56 | `icf` | `Int64` | no |  | Individual corsi for, e.g., 3 |
| 57 | `icf_adj` | `Float64` | no |  | Score- and venue-adjusted individual corsi events, e.g., 3.279018 |
| 58 | `ibs` | `Int64` | no |  | Individual shots blocked on defense, e.g., 0 |
| 59 | `ibs_adj` | `Float64` | no |  | Score- and venue-adjusted shots blocked, e.g., 0.0 |
| 60 | `igive` | `Int64` | no |  | Individual giveaways, e.g., 0 |
| 61 | `itake` | `Int64` | no |  | Individual takeaways, e.g., 0 |
| 62 | `ihf` | `Int64` | no |  | Individual hits for, e.g., 0 |
| 63 | `iht` | `Int64` | no |  | Individual hits taken, e.g., 0 |
| 64 | `ifow` | `Int64` | no |  | Individual faceoffs won, e.g., 0 |
| 65 | `ifol` | `Int64` | no |  | Individual faceoffs lost, e.g., 0 |
| 66 | `iozfw` | `Int64` | no |  | Individual faceoffs won in offensive zone, e.g., 0 |
| 67 | `iozfl` | `Int64` | no |  | Individual faceoffs lost in offensive zone, e.g., 0 |
| 68 | `inzfw` | `Int64` | no |  | Individual faceoffs won in neutral zone, e.g., 0 |
| 69 | `inzfl` | `Int64` | no |  | Individual faceoffs lost in neutral zone, e.g., 0 |
| 70 | `idzfw` | `Int64` | no |  | Individual faceoffs won in defensive zone, e.g., 0 |
| 71 | `idzfl` | `Int64` | no |  | Individual faceoffs lost in defensive zone, e.g., 0 |
| 72 | `a1_xg` | `Float64` | yes |  | xG on primary assists, e.g., 0 |
| 73 | `a2_xg` | `Float64` | yes |  | xG on secondary assists, e.g., 0 |
| 74 | `ipent0` | `Int64` | no |  | Individual penalty shots against, e.g., 0 |
| 75 | `ipent2` | `Int64` | no |  | Individual minor penalties taken, e.g., 0 |
| 76 | `ipent4` | `Int64` | no |  | Individual double minor penalties taken, e.g., 0 |
| 77 | `ipent5` | `Int64` | no |  | Individual major penalties taken, e.g., 0 |
| 78 | `ipent10` | `Int64` | no |  | Individual 10-minute penalties taken, such as misconducts, e.g., 0 |
| 79 | `ipend0` | `Int64` | no |  | Individual penalty shots drawn, e.g., 0 |
| 80 | `ipend2` | `Int64` | no |  | Individual minor penalties drawn, e.g., 0 |
| 81 | `ipend4` | `Int64` | no |  | Individual double minor penalties drawn, e.g., 0 |
| 82 | `ipend5` | `Int64` | no |  | Individual major penalties drawn, e.g., 0 |
| 83 | `ipend10` | `Int64` | no |  | Individual 10-minute penalties drawn, such as misconducts, e.g., 0 |
| 84 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 85 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 86 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 87 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 88 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 89 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 90 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 91 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 92 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 93 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 94 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 95 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 96 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 97 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 98 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 99 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 100 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 101 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 102 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 103 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 104 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 105 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 106 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 107 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 108 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 109 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 110 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 111 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 112 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 113 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 114 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 115 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 116 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 117 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 118 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 119 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 120 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 121 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 122 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 123 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 124 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 125 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 126 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 127 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 128 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 129 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 130 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 131 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 132 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 133 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 134 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 135 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 136 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 137 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 138 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 139 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 140 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 141 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 142 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 143 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 144 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 145 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 146 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 147 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 148 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 149 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 150 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 151 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 152 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 153 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 154 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 155 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 156 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 157 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 158 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 159 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 160 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
| 161 | `g_p60` | `Float64` | yes | per 60 minutes | Goals scored per 60 minutes |
| 162 | `g_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals scored per 60 minutes |
| 163 | `ihdg_p60` | `Float64` | yes | per 60 minutes | Individual high-danger goals scored per 60 minutes |
| 164 | `a1_p60` | `Float64` | yes | per 60 minutes | Primary assists per 60 minutes |
| 165 | `a2_p60` | `Float64` | yes | per 60 minutes | Secondary assists per 60 minutes |
| 166 | `ixg_p60` | `Float64` | yes | per 60 minutes | Individual xG for per 60 minutes |
| 167 | `ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual xG for per 60 minutes |
| 168 | `base_ixg_p60` | `Float64` | yes | per 60 minutes | Individual base xG for per 60 minutes, only with ``base_xg`` |
| 169 | `base_ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual base xG for per 60 minutes, only with ``base_xg`` |
| 170 | `context_ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual context xG for per 60 minutes, only with ``context_xg`` |
| 171 | `context_ixg_p60` | `Float64` | yes | per 60 minutes | Individual context xG for per 60 minutes, only with ``context_xg`` |
| 172 | `isf_p60` | `Float64` | yes | per 60 minutes | Individual shots for per 60 minutes |
| 173 | `isf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual shots for per 60 minutes |
| 174 | `ihdsf_p60` | `Float64` | yes | per 60 minutes | Individual high-danger shots for per 60 minutes |
| 175 | `imsf_p60` | `Float64` | yes | per 60 minutes | Individual missed shots for per 60 minutes |
| 176 | `imsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual missed shots for per 60 minutes |
| 177 | `ihdm_p60` | `Float64` | yes | per 60 minutes | Individual high-danger missed shots for per 60 minutes |
| 178 | `iff_p60` | `Float64` | yes | per 60 minutes | Individual fenwick for per 60 minutes |
| 179 | `iff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual fenwick for per 60 minutes |
| 180 | `ihdf_p60` | `Float64` | yes | per 60 minutes | Individual high-danger fenwick for per 60 minutes |
| 181 | `isb_p60` | `Float64` | yes | per 60 minutes | Individual shots blocked (for) per 60 minutes |
| 182 | `isb_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual shots blocked (for) per 60 minutes |
| 183 | `icf_p60` | `Float64` | yes | per 60 minutes | Individual corsi for per 60 minutes |
| 184 | `icf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual corsi for per 60 minutes |
| 185 | `ibs_p60` | `Float64` | yes | per 60 minutes | Individual blocked shots (against) per 60 minutes |
| 186 | `ibs_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual blocked shots (against) per 60 minutes |
| 187 | `igive_p60` | `Float64` | yes | per 60 minutes | Individual giveaways per 60 minutes |
| 188 | `itake_p60` | `Float64` | yes | per 60 minutes | Individual takeaways per 60 minutes |
| 189 | `ihf_p60` | `Float64` | yes | per 60 minutes | Individual hits for per 60 minutes |
| 190 | `iht_p60` | `Float64` | yes | per 60 minutes | Individual hits taken per 60 minutes |
| 191 | `a1_xg_p60` | `Float64` | yes | per 60 minutes | Individual primary assists' xG per 60 minutes |
| 192 | `a2_xg_p60` | `Float64` | yes | per 60 minutes | Individual secondary assists' xG per 60 minutes |
| 193 | `ipent0_p60` | `Float64` | yes | per 60 minutes | Individual penalty shots taken per 60 minutes |
| 194 | `ipent2_p60` | `Float64` | yes | per 60 minutes | Individual minor penalties taken per 60 minutes |
| 195 | `ipent4_p60` | `Float64` | yes | per 60 minutes | Individual double minor penalties taken per 60 minutes |
| 196 | `ipent5_p60` | `Float64` | yes | per 60 minutes | Individual major penalties taken per 60 minutes |
| 197 | `ipent10_p60` | `Float64` | yes | per 60 minutes | Individual 10-minute penalties taken per 60 minutes |
| 198 | `ipend0_p60` | `Float64` | yes | per 60 minutes | Individual penalty shots drawn per 60 minutes |
| 199 | `ipend2_p60` | `Float64` | yes | per 60 minutes | Individual minor penalties drawn per 60 minutes |
| 200 | `ipend4_p60` | `Float64` | yes | per 60 minutes | Individual double minor penalties drawn per 60 minutes |
| 201 | `ipend5_p60` | `Float64` | yes | per 60 minutes | Individual major penalties drawn per 60 minutes |
| 202 | `ipend10_p60` | `Float64` | yes | per 60 minutes | Individual 10-minute penalties drawn per 60 minutes |
| 203 | `gf_p60` | `Float64` | yes | per 60 minutes | Goals for (on-ice) per 60 minutes |
| 204 | `ga_p60` | `Float64` | yes | per 60 minutes | Goals against (on-ice) per 60 minutes |
| 205 | `gf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals for (on-ice) per 60 minutes |
| 206 | `ga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals against (on-ice) per 60 minutes |
| 207 | `hdgf_p60` | `Float64` | yes | per 60 minutes | High-danger goals for (on-ice) per 60 minutes |
| 208 | `hdga_p60` | `Float64` | yes | per 60 minutes | High-danger goals against (on-ice) per 60 minutes |
| 209 | `xgf_p60` | `Float64` | yes | per 60 minutes | xG for (on-ice) per 60 minutes |
| 210 | `xga_p60` | `Float64` | yes | per 60 minutes | xG against (on-ice) per 60 minutes |
| 211 | `xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG for (on-ice) per 60 minutes |
| 212 | `xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG against (on-ice) per 60 minutes |
| 213 | `base_xgf_p60` | `Float64` | yes | per 60 minutes | Base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 214 | `base_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 215 | `context_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 216 | `base_xga_p60` | `Float64` | yes | per 60 minutes | Base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 217 | `base_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 218 | `context_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 219 | `context_xgf_p60` | `Float64` | yes | per 60 minutes | Context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 220 | `context_xga_p60` | `Float64` | yes | per 60 minutes | Context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 221 | `sf_p60` | `Float64` | yes | per 60 minutes | Shots for (on-ice) per 60 minutes |
| 222 | `sa_p60` | `Float64` | yes | per 60 minutes | Shots against (on-ice) per 60 minutes |
| 223 | `sf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots for (on-ice) per 60 minutes |
| 224 | `sa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots against (on-ice) per 60 minutes |
| 225 | `hdsf_p60` | `Float64` | yes | per 60 minutes | High-danger shots for (on-ice) per 60 minutes |
| 226 | `hdsa_p60` | `Float64` | yes | per 60 minutes | High-danger shots against (on-ice) per 60 minutes |
| 227 | `ff_p60` | `Float64` | yes | per 60 minutes | Fenwick for (on-ice) per 60 minutes |
| 228 | `fa_p60` | `Float64` | yes | per 60 minutes | Fenwick against (on-ice) per 60 minutes |
| 229 | `ff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick for (on-ice) per 60 minutes |
| 230 | `fa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick against (on-ice) per 60 minutes |
| 231 | `hdff_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick for (on-ice) per 60 minutes |
| 232 | `hdfa_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick against (on-ice) per 60 minutes |
| 233 | `cf_p60` | `Float64` | yes | per 60 minutes | Corsi for (on-ice) per 60 minutes |
| 234 | `ca_p60` | `Float64` | yes | per 60 minutes | Corsi against (on-ice) per 60 minutes |
| 235 | `cf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi for (on-ice) per 60 minutes |
| 236 | `ca_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi against (on-ice) per 60 minutes |
| 237 | `bsf_p60` | `Float64` | yes | per 60 minutes | Blocked shots for (on-ice) per 60 minutes |
| 238 | `bsa_p60` | `Float64` | yes | per 60 minutes | Blocked shots against (on-ice) per 60 minutes |
| 239 | `bsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots for (on-ice) per 60 minutes |
| 240 | `bsa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots against (on-ice) per 60 minutes |
| 241 | `msf_p60` | `Float64` | yes | per 60 minutes | Missed shots for (on-ice) per 60 minutes |
| 242 | `msa_p60` | `Float64` | yes | per 60 minutes | Missed shots against (on-ice) per 60 minutes |
| 243 | `msf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots for (on-ice) per 60 minutes |
| 244 | `msa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots against (on-ice) per 60 minutes |
| 245 | `hdmsf_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots for (on-ice) per 60 minutes |
| 246 | `hdmsa_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots against (on-ice) per 60 minutes |
| 247 | `teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts for blocked by a teammate (on-ice) per 60 minutes |
| 248 | `opp_teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts against blocked by one of the opponent's teammates (on-ice) per 60 minutes |
| 249 | `hf_p60` | `Float64` | yes | per 60 minutes | Hits for (on-ice) per 60 minutes |
| 250 | `ht_p60` | `Float64` | yes | per 60 minutes | Hits taken (on-ice) per 60 minutes |
| 251 | `pent0_p60` | `Float64` | yes | per 60 minutes | Penalty shots taken (on-ice) per 60 minutes |
| 252 | `pent2_p60` | `Float64` | yes | per 60 minutes | Minor penalties taken (on-ice) per 60 minutes |
| 253 | `pent4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties taken (on-ice) per 60 minutes |
| 254 | `pent5_p60` | `Float64` | yes | per 60 minutes | Major penalties taken (on-ice) per 60 minutes |
| 255 | `pent10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties taken (on-ice) per 60 minutes |
| 256 | `pend0_p60` | `Float64` | yes | per 60 minutes | Penalty shots drawn (on-ice) per 60 minutes |
| 257 | `pend2_p60` | `Float64` | yes | per 60 minutes | Minor penalties drawn (on-ice) per 60 minutes |
| 258 | `pend4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties drawn (on-ice) per 60 minutes |
| 259 | `pend5_p60` | `Float64` | yes | per 60 minutes | Major penalties drawn (on-ice) per 60 minutes |
| 260 | `pend10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties drawn (on-ice) per 60 minutes |
| 261 | `gf_percent` | `Float64` | yes | share, 0 to 1 | On-ice goals for as a share of all on-ice goals, from 0 to 1, i.e., GF / (GF + GA) |
| 262 | `gf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted goals for as a share of all on-ice adjusted goals, from 0 to 1 i.e., GF_adj / (GF_adj + GA_adj) |
| 263 | `hdgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger goals for as a share of all on-ice high-danger goals, from 0 to 1 i.e., HDGF / (HDGF + HDGA) |
| 264 | `xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice xG for as a share of all on-ice xG, from 0 to 1, i.e., xGF / (xGF + xGA) |
| 265 | `xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted xG for as a share of all on-ice adjusted xG, from 0 to 1 i.e., xGF_adj / (xGF_adj + xGA_adj) |
| 266 | `base_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice base xG for as a share of all on-ice base xG, from 0 to 1, only with ``base_xg`` i.e., base_xGF / (base_xGF + base_xGA) |
| 267 | `base_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted base xG for as a percentage of total on-ice adjusted base xG, only with ``base_xg`` i.e., base_xGF_adj / (base_xGF_adj + base_xGA_adj) |
| 268 | `context_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted context xG for as a percentage of total on-ice adjusted context xG, only with ``context_xg`` i.e., context_xGF_adj / (context_xGF_adj + context_xGA_adj) |
| 269 | `context_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice context xG for as a share of all on-ice context xG, from 0 to 1, only with ``context_xg`` i.e., context_xGF / (context_xGF + context_xGA) |
| 270 | `sf_percent` | `Float64` | yes | share, 0 to 1 | On-ice shots for as a share of all on-ice shots, from 0 to 1, i.e., SF / (SF + SA) |
| 271 | `sf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted shots for as a share of all on-ice adjusted shots, from 0 to 1 i.e., SF_adj / (SF_adj + SA_adj) |
| 272 | `hdsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger shots for as a share of all on-ice high-danger shots, from 0 to 1 i.e., HDSF / (HDSF + HDSA) |
| 273 | `ff_percent` | `Float64` | yes | share, 0 to 1 | On-ice fenwick for as a share of all on-ice fenwick, from 0 to 1, i.e., FF / (FF + FA) |
| 274 | `ff_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted fenwick for as a share of all on-ice adjusted fenwick, from 0 to 1 i.e., FF_adj / (FF_adj + FA_adj) |
| 275 | `hdff_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger fenwick for as a share of all on-ice high-danger fenwick, from 0 to 1 i.e., HDFF / (HDFF + HDFA) |
| 276 | `cf_percent` | `Float64` | yes | share, 0 to 1 | On-ice corsi for as a share of all on-ice corsi, from 0 to 1, i.e., CF / (CF + CA) |
| 277 | `cf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted corsi for as a share of all on-ice adjusted corsi, from 0 to 1 i.e., CF_adj / (CF_adj + CA_adj) |
| 278 | `bsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice blocked shots for as a share of all on-ice blocked shots, from 0 to 1, i.e., BSF / (BSF + BSA) |
| 279 | `bsf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted blocked shots for as a share of all on-ice adjusted blocked shots, from 0 to 1 i.e., BSF_adj / (BSF_adj + BSA_adj) |
| 280 | `msf_percent` | `Float64` | yes | share, 0 to 1 | On-ice missed shots for as a share of all on-ice missed shots, from 0 to 1, i.e., MSF / (MSF + MSA) |
| 281 | `msf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted missed shots for as a share of all on-ice adjusted missed shots, from 0 to 1 i.e., MSF_adj / (MSF_adj + MSA_adj) |
| 282 | `hdmsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger missed shots for as a share of all on-ice high-danger missed shots, from 0 to 1 i.e., HDMSF / (HDMSF + HDMSA) |
| 283 | `hf_percent` | `Float64` | yes | share, 0 to 1 | On-ice hits for as a share of all on-ice hits, from 0 to 1, i.e., HF / (HF + HT) |
| 284 | `take_percent` | `Float64` | yes | share, 0 to 1 | On-ice takeaways as a share of all on-ice giveaways and takeaways, from 0 to 1 i.e., take / (take + give) |
