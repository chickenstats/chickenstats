---
icon: material/table
description: "Columns, dtypes and nullability of stats in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: stats**

Returned by `evolving_hockey.prep_stats`. See [Output schemas](index.md) for what these columns promise.

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
| 25 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
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
| 76 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 77 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 78 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 79 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 80 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 81 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 82 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 83 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 84 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 85 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 86 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 87 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 88 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 89 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 90 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 91 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 92 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 93 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 94 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 95 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 96 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 97 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 98 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 99 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 100 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 101 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 102 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 103 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 104 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 105 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 106 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 107 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 108 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 109 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 110 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 111 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 112 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 113 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 114 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 115 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 116 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 117 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 118 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 119 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 120 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 121 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 122 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 123 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 124 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 125 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 126 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 127 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 128 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 129 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 130 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 131 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 132 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 133 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 134 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 135 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 136 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 137 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 138 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 139 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 140 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 141 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 142 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 143 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 144 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 145 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 146 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 147 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 148 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 149 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 150 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 151 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 152 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
| 153 | `g_p60` | `Float64` | yes | per 60 minutes | Goals scored per 60 minutes |
| 154 | `g_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals scored per 60 minutes |
| 155 | `ihdg_p60` | `Float64` | yes | per 60 minutes | Individual high-danger goals scored per 60 minutes |
| 156 | `a1_p60` | `Float64` | yes | per 60 minutes | Primary assists per 60 minutes |
| 157 | `a2_p60` | `Float64` | yes | per 60 minutes | Secondary assists per 60 minutes |
| 158 | `ixg_p60` | `Float64` | yes | per 60 minutes | Individual xG for per 60 minutes |
| 159 | `ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual xG for per 60 minutes |
| 160 | `base_ixg_p60` | `Float64` | yes | per 60 minutes | Individual base xG for per 60 minutes, only with ``base_xg`` |
| 161 | `base_ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual base xG for per 60 minutes, only with ``base_xg`` |
| 162 | `context_ixg_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual context xG for per 60 minutes, only with ``context_xg`` |
| 163 | `context_ixg_p60` | `Float64` | yes | per 60 minutes | Individual context xG for per 60 minutes, only with ``context_xg`` |
| 164 | `isf_p60` | `Float64` | yes | per 60 minutes | Individual shots for per 60 minutes |
| 165 | `isf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual shots for per 60 minutes |
| 166 | `ihdsf_p60` | `Float64` | yes | per 60 minutes | Individual high-danger shots for per 60 minutes |
| 167 | `imsf_p60` | `Float64` | yes | per 60 minutes | Individual missed shots for per 60 minutes |
| 168 | `imsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual missed shots for per 60 minutes |
| 169 | `ihdm_p60` | `Float64` | yes | per 60 minutes | Individual high-danger missed shots for per 60 minutes |
| 170 | `iff_p60` | `Float64` | yes | per 60 minutes | Individual fenwick for per 60 minutes |
| 171 | `iff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual fenwick for per 60 minutes |
| 172 | `ihdf_p60` | `Float64` | yes | per 60 minutes | Individual high-danger fenwick for per 60 minutes |
| 173 | `isb_p60` | `Float64` | yes | per 60 minutes | Individual shots blocked (for) per 60 minutes |
| 174 | `isb_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual shots blocked (for) per 60 minutes |
| 175 | `icf_p60` | `Float64` | yes | per 60 minutes | Individual corsi for per 60 minutes |
| 176 | `icf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual corsi for per 60 minutes |
| 177 | `ibs_p60` | `Float64` | yes | per 60 minutes | Individual blocked shots (against) per 60 minutes |
| 178 | `ibs_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted individual blocked shots (against) per 60 minutes |
| 179 | `igive_p60` | `Float64` | yes | per 60 minutes | Individual giveaways per 60 minutes |
| 180 | `itake_p60` | `Float64` | yes | per 60 minutes | Individual takeaways per 60 minutes |
| 181 | `ihf_p60` | `Float64` | yes | per 60 minutes | Individual hits for per 60 minutes |
| 182 | `iht_p60` | `Float64` | yes | per 60 minutes | Individual hits taken per 60 minutes |
| 183 | `a1_xg_p60` | `Float64` | yes | per 60 minutes | Individual primary assists' xG per 60 minutes |
| 184 | `a2_xg_p60` | `Float64` | yes | per 60 minutes | Individual secondary assists' xG per 60 minutes |
| 185 | `ipent0_p60` | `Float64` | yes | per 60 minutes | Individual penalty shots taken per 60 minutes |
| 186 | `ipent2_p60` | `Float64` | yes | per 60 minutes | Individual minor penalties taken per 60 minutes |
| 187 | `ipent4_p60` | `Float64` | yes | per 60 minutes | Individual double minor penalties taken per 60 minutes |
| 188 | `ipent5_p60` | `Float64` | yes | per 60 minutes | Individual major penalties taken per 60 minutes |
| 189 | `ipent10_p60` | `Float64` | yes | per 60 minutes | Individual 10-minute penalties taken per 60 minutes |
| 190 | `ipend0_p60` | `Float64` | yes | per 60 minutes | Individual penalty shots drawn per 60 minutes |
| 191 | `ipend2_p60` | `Float64` | yes | per 60 minutes | Individual minor penalties drawn per 60 minutes |
| 192 | `ipend4_p60` | `Float64` | yes | per 60 minutes | Individual double minor penalties drawn per 60 minutes |
| 193 | `ipend5_p60` | `Float64` | yes | per 60 minutes | Individual major penalties drawn per 60 minutes |
| 194 | `ipend10_p60` | `Float64` | yes | per 60 minutes | Individual 10-minute penalties drawn per 60 minutes |
| 195 | `gf_p60` | `Float64` | yes | per 60 minutes | Goals for (on-ice) per 60 minutes |
| 196 | `ga_p60` | `Float64` | yes | per 60 minutes | Goals against (on-ice) per 60 minutes |
| 197 | `gf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals for (on-ice) per 60 minutes |
| 198 | `ga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals against (on-ice) per 60 minutes |
| 199 | `hdgf_p60` | `Float64` | yes | per 60 minutes | High-danger goals for (on-ice) per 60 minutes |
| 200 | `hdga_p60` | `Float64` | yes | per 60 minutes | High-danger goals against (on-ice) per 60 minutes |
| 201 | `xgf_p60` | `Float64` | yes | per 60 minutes | xG for (on-ice) per 60 minutes |
| 202 | `xga_p60` | `Float64` | yes | per 60 minutes | xG against (on-ice) per 60 minutes |
| 203 | `xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG for (on-ice) per 60 minutes |
| 204 | `xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG against (on-ice) per 60 minutes |
| 205 | `base_xgf_p60` | `Float64` | yes | per 60 minutes | Base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 206 | `base_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 207 | `context_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 208 | `base_xga_p60` | `Float64` | yes | per 60 minutes | Base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 209 | `base_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 210 | `context_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 211 | `context_xgf_p60` | `Float64` | yes | per 60 minutes | Context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 212 | `context_xga_p60` | `Float64` | yes | per 60 minutes | Context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 213 | `sf_p60` | `Float64` | yes | per 60 minutes | Shots for (on-ice) per 60 minutes |
| 214 | `sa_p60` | `Float64` | yes | per 60 minutes | Shots against (on-ice) per 60 minutes |
| 215 | `sf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots for (on-ice) per 60 minutes |
| 216 | `sa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots against (on-ice) per 60 minutes |
| 217 | `hdsf_p60` | `Float64` | yes | per 60 minutes | High-danger shots for (on-ice) per 60 minutes |
| 218 | `hdsa_p60` | `Float64` | yes | per 60 minutes | High-danger shots against (on-ice) per 60 minutes |
| 219 | `ff_p60` | `Float64` | yes | per 60 minutes | Fenwick for (on-ice) per 60 minutes |
| 220 | `fa_p60` | `Float64` | yes | per 60 minutes | Fenwick against (on-ice) per 60 minutes |
| 221 | `ff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick for (on-ice) per 60 minutes |
| 222 | `fa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick against (on-ice) per 60 minutes |
| 223 | `hdff_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick for (on-ice) per 60 minutes |
| 224 | `hdfa_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick against (on-ice) per 60 minutes |
| 225 | `cf_p60` | `Float64` | yes | per 60 minutes | Corsi for (on-ice) per 60 minutes |
| 226 | `ca_p60` | `Float64` | yes | per 60 minutes | Corsi against (on-ice) per 60 minutes |
| 227 | `cf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi for (on-ice) per 60 minutes |
| 228 | `ca_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi against (on-ice) per 60 minutes |
| 229 | `bsf_p60` | `Float64` | yes | per 60 minutes | Blocked shots for (on-ice) per 60 minutes |
| 230 | `bsa_p60` | `Float64` | yes | per 60 minutes | Blocked shots against (on-ice) per 60 minutes |
| 231 | `bsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots for (on-ice) per 60 minutes |
| 232 | `bsa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots against (on-ice) per 60 minutes |
| 233 | `msf_p60` | `Float64` | yes | per 60 minutes | Missed shots for (on-ice) per 60 minutes |
| 234 | `msa_p60` | `Float64` | yes | per 60 minutes | Missed shots against (on-ice) per 60 minutes |
| 235 | `msf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots for (on-ice) per 60 minutes |
| 236 | `msa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots against (on-ice) per 60 minutes |
| 237 | `hdmsf_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots for (on-ice) per 60 minutes |
| 238 | `hdmsa_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots against (on-ice) per 60 minutes |
| 239 | `teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts for blocked by a teammate (on-ice) per 60 minutes |
| 240 | `opp_teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts against blocked by one of the opponent's teammates (on-ice) per 60 minutes |
| 241 | `hf_p60` | `Float64` | yes | per 60 minutes | Hits for (on-ice) per 60 minutes |
| 242 | `ht_p60` | `Float64` | yes | per 60 minutes | Hits taken (on-ice) per 60 minutes |
| 243 | `pent0_p60` | `Float64` | yes | per 60 minutes | Penalty shots taken (on-ice) per 60 minutes |
| 244 | `pent2_p60` | `Float64` | yes | per 60 minutes | Minor penalties taken (on-ice) per 60 minutes |
| 245 | `pent4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties taken (on-ice) per 60 minutes |
| 246 | `pent5_p60` | `Float64` | yes | per 60 minutes | Major penalties taken (on-ice) per 60 minutes |
| 247 | `pent10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties taken (on-ice) per 60 minutes |
| 248 | `pend0_p60` | `Float64` | yes | per 60 minutes | Penalty shots drawn (on-ice) per 60 minutes |
| 249 | `pend2_p60` | `Float64` | yes | per 60 minutes | Minor penalties drawn (on-ice) per 60 minutes |
| 250 | `pend4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties drawn (on-ice) per 60 minutes |
| 251 | `pend5_p60` | `Float64` | yes | per 60 minutes | Major penalties drawn (on-ice) per 60 minutes |
| 252 | `pend10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties drawn (on-ice) per 60 minutes |
| 253 | `gf_percent` | `Float64` | yes | share, 0 to 1 | On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA) |
| 254 | `gf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted goals for as a percentage of total on-ice adjusted goals i.e., GF_adj / (GF_adj + GA_adj) |
| 255 | `hdgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA) |
| 256 | `xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + xGA) |
| 257 | `xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted xG for as a percentage of total on-ice adjusted xG i.e., xGF_adj / (xGF_adj + xGA_adj) |
| 258 | `base_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice base xG for as a percentage of total on-ice base xG, only with ``base_xg`` i.e., base_xGF / (base_xGF + base_xGA) |
| 259 | `base_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted base xG for as a percentage of total on-ice adjusted base xG, only with ``base_xg`` i.e., base_xGF_adj / (base_xGF_adj + base_xGA_adj) |
| 260 | `context_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted context xG for as a percentage of total on-ice adjusted context xG, only with ``context_xg`` i.e., context_xGF_adj / (context_xGF_adj + context_xGA_adj) |
| 261 | `context_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice context xG for as a percentage of total on-ice context xG, only with ``context_xg`` i.e., context_xGF / (context_xGF + context_xGA) |
| 262 | `sf_percent` | `Float64` | yes | share, 0 to 1 | On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA) |
| 263 | `sf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted shots for as a percentage of total on-ice adjusted shots i.e., SF_adj / (SF_adj + SA_adj) |
| 264 | `hdsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA) |
| 265 | `ff_percent` | `Float64` | yes | share, 0 to 1 | On-ice fenwick for as a percentage of total on-ice fenwick i.e., FF / (FF + FA) |
| 266 | `ff_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted fenwick for as a percentage of total on-ice adjusted fenwick i.e., FF_adj / (FF_adj + FA_adj) |
| 267 | `hdff_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA) |
| 268 | `cf_percent` | `Float64` | yes | share, 0 to 1 | On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA) |
| 269 | `cf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted corsi for as a percentage of total on-ice adjusted corsi i.e., CF_adj / (CF_adj + CA_adj) |
| 270 | `bsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA) |
| 271 | `bsf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted blocked shots for as a percentage of total on-ice adjusted blocked shots i.e., BSF_adj / (BSF_adj + BSA_adj) |
| 272 | `msf_percent` | `Float64` | yes | share, 0 to 1 | On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA) |
| 273 | `msf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted missed shots for as a percentage of total on-ice adjusted missed shots i.e., MSF_adj / (MSF_adj + MSA_adj) |
| 274 | `hdmsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA) |
| 275 | `hf_percent` | `Float64` | yes | share, 0 to 1 | On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT) |
| 276 | `take_percent` | `Float64` | yes | share, 0 to 1 | On-ice takeaways as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give) |
