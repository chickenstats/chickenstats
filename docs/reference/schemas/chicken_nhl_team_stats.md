---
icon: material/table
description: "Columns, dtypes and nullability of team_stats in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: team_stats**

Returned by `Scraper.team_stats`, `prep_team_stats`. See [Output schemas](index.md) for what these columns promise.

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
| 10 | `toi` | `Float64` | no | minutes | Time on-ice, in minutes, e.g., 0.483333 |
| 11 | `gf` | `Int64` | no |  | Goals for (on-ice), e.g., 0 |
| 12 | `ga` | `Int64` | no |  | Goals against (on-ice), e.g., 0 |
| 13 | `gf_adj` | `Float64` | no |  | Score- and venue-adjusted goals for (on-ice), e.g., 0.0 |
| 14 | `ga_adj` | `Float64` | no |  | Score- and venue-adjusted goals against (on-ice), e.g., 0.0 |
| 15 | `hdgf` | `Int64` | no |  | High-danger goals for (on-ice), e.g., 0 |
| 16 | `hdga` | `Int64` | no |  | High-danger goals against (on-ice), e.g., 0 |
| 17 | `xgf` | `Float64` | yes |  | xG for (on-ice), e.g., 1.258332 |
| 18 | `xga` | `Float64` | yes |  | xG against (on-ice), e.g., 0.000000 |
| 19 | `xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted xG for (on-ice), e.g., 1.366730 |
| 20 | `xga_adj` | `Float64` | yes |  | Score- and venue-adjusted xG against (on-ice), e.g., 0.0 |
| 21 | `base_xgf` | `Float64` | yes |  | Base xG for (on-ice), only with ``base_xg`` |
| 22 | `base_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG for (on-ice), only with ``base_xg`` |
| 23 | `context_xgf_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG for (on-ice), only with ``context_xg`` |
| 24 | `base_xga` | `Float64` | yes |  | Base xG against (on-ice), only with ``base_xg`` |
| 25 | `base_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted base xG against (on-ice), only with ``base_xg`` |
| 26 | `context_xga_adj` | `Float64` | yes |  | Score- and venue-adjusted context xG against (on-ice), only with ``context_xg`` |
| 27 | `context_xgf` | `Float64` | yes |  | Context xG for (on-ice), only with ``context_xg`` |
| 28 | `context_xga` | `Float64` | yes |  | Context xG against (on-ice), only with ``context_xg`` |
| 29 | `sf` | `Int64` | no |  | Shots for (on-ice), e.g., 4 |
| 30 | `sa` | `Int64` | no |  | Shots against (on-ice), e.g., 0 |
| 31 | `sf_adj` | `Float64` | no |  | Score- and venue-adjusted shots for (on-ice), e.g., 4.350622 |
| 32 | `sa_adj` | `Float64` | no |  | Score- and venue-adjusted shots against (on-ice), e.g., 0.0 |
| 33 | `hdsf` | `Int64` | no |  | High-danger shots for (on-ice), e.g., 3 |
| 34 | `hdsa` | `Int64` | no |  | High-danger shots against (on-ice), e.g., 0 |
| 35 | `ff` | `Int64` | no |  | Fenwick for (on-ice), e.g., 4 |
| 36 | `fa` | `Int64` | no |  | Fenwick against (on-ice), e.g., 0 |
| 37 | `ff_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events for (on-ice), e.g., 4.372024 |
| 38 | `fa_adj` | `Float64` | no |  | Score- and venue-adjusted fenwick events against (on-ice), e.g., 0.0 |
| 39 | `hdff` | `Int64` | no |  | High-danger fenwick for (on-ice), e.g., 3 |
| 40 | `hdfa` | `Int64` | no |  | High-danger fenwick against (on-ice), e.g., 0 |
| 41 | `cf` | `Int64` | no |  | Corsi for (on-ice), e.g., 4 |
| 42 | `ca` | `Int64` | no |  | Corsi against (on-ice), e.g., 0 |
| 43 | `cf_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events for (on-ice), e.g., 4.372024 |
| 44 | `ca_adj` | `Float64` | no |  | Score- and venue-adjusted corsi events against (on-ice), e.g., 0.0 |
| 45 | `bsf` | `Int64` | no |  | Shot attempts for that were blocked (on-ice), e.g., 0 |
| 46 | `bsa` | `Int64` | no |  | Shot attempts against that were blocked (on-ice), e.g., 0 |
| 47 | `bsf_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots for (on-ice), e.g., 0.0 |
| 48 | `bsa_adj` | `Float64` | no |  | Score- and venue-adjusted blocked shots against (on-ice), e.g., 0.0 |
| 49 | `msf` | `Int64` | no |  | Missed shots taken (on-ice), e.g., 0 |
| 50 | `msa` | `Int64` | no |  | Missed shots against (on-ice), e.g., 0 |
| 51 | `msf_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots for (on-ice), e.g., 0.0 |
| 52 | `msa_adj` | `Float64` | no |  | Score- and venue-adjusted missed shots against (on-ice), e.g., 0.0 |
| 53 | `hdmsf` | `Int64` | no |  | High-danger missed shots taken (on-ice), e.g., 0 |
| 54 | `hdmsa` | `Int64` | no |  | High-danger missed shots against (on-ice), e.g., 0 |
| 55 | `teammate_block` | `Int64` | no |  | Shot attempts for blocked by a teammate, included in bsf (on-ice), e.g., 0 |
| 56 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts for blocked by a teammate, included in bsf_adj (on-ice), e.g., 0.0 |
| 57 | `opp_teammate_block` | `Int64` | no |  | Shot attempts against blocked by the shooter's own teammate, included in bsa (on-ice), e.g., 0 |
| 58 | `opp_teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted shot attempts against blocked by one of the opponent's teammates, included in bsa_adj (on-ice), e.g., 0.0 |
| 59 | `hf` | `Int64` | no |  | Hits for (on-ice), e.g., 0 |
| 60 | `ht` | `Int64` | no |  | Hits taken (on-ice), e.g., 0 |
| 61 | `give` | `Int64` | no |  | Giveaways (on-ice), e.g., 0 |
| 62 | `take` | `Int64` | no |  | Takeaways (on-ice), e.g., 0 |
| 63 | `ozf` | `Int64` | no |  | Offensive zone faceoffs (on-ice), e.g., 0 |
| 64 | `nzf` | `Int64` | no |  | Neutral zone faceoffs (on-ice), e.g., 1 |
| 65 | `dzf` | `Int64` | no |  | Defensive zone faceoffs (on-ice), e.g., 0 |
| 66 | `fow` | `Int64` | no |  | Faceoffs won (on-ice), e.g., 1 |
| 67 | `fol` | `Int64` | no |  | Faceoffs lost (on-ice), e.g., 0 |
| 68 | `ozfw` | `Int64` | no |  | Offensive zone faceoffs won (on-ice), e.g., 0 |
| 69 | `ozfl` | `Int64` | no |  | Offensive zone faceoffs lost (on-ice), e.g., 0 |
| 70 | `nzfw` | `Int64` | no |  | Neutral zone faceoffs won (on-ice), e.g., 1 |
| 71 | `nzfl` | `Int64` | no |  | Neutral zone faceoffs lost (on-ice), e.g., 0 |
| 72 | `dzfw` | `Int64` | no |  | Defensive zone faceoffs won (on-ice), e.g., 0 |
| 73 | `dzfl` | `Int64` | no |  | Defensive zone faceoffs lost (on-ice), e.g., 0 |
| 74 | `pent0` | `Int64` | no |  | Penalty shots allowed (on-ice), e.g., 0 |
| 75 | `pent2` | `Int64` | no |  | Minor penalties taken (on-ice), e.g., 0 |
| 76 | `pent4` | `Int64` | no |  | Double minor penalties taken (on-ice), e.g., 0 |
| 77 | `pent5` | `Int64` | no |  | Major penalties taken (on-ice), e.g., 0 |
| 78 | `pent10` | `Int64` | no |  | 10-minute penalties taken (on-ice), such as misconducts, e.g., 0 |
| 79 | `pend0` | `Int64` | no |  | Penalty shots drawn (on-ice), e.g., 0 |
| 80 | `pend2` | `Int64` | no |  | Minor penalties drawn (on-ice), e.g., 0 |
| 81 | `pend4` | `Int64` | no |  | Double minor penalties drawn (on-ice), e.g., 0 |
| 82 | `pend5` | `Int64` | no |  | Major penalties drawn (on-ice), e.g., 0 |
| 83 | `pend10` | `Int64` | no |  | 10-minute penalties drawn (on-ice), such as misconducts, e.g., 0 |
| 84 | `ozs` | `Int64` | no |  | Offensive zone starts, e.g., 0 |
| 85 | `nzs` | `Int64` | no |  | Neutral zone starts, e.g., 0 |
| 86 | `dzs` | `Int64` | no |  | Defensive zone starts, e.g., 0 |
| 87 | `otf` | `Int64` | no |  | On-the-fly starts, e.g., 0 |
| 88 | `gf_p60` | `Float64` | yes | per 60 minutes | Goals for (on-ice) per 60 minutes |
| 89 | `ga_p60` | `Float64` | yes | per 60 minutes | Goals against (on-ice) per 60 minutes |
| 90 | `gf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals for (on-ice) per 60 minutes |
| 91 | `ga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted goals against (on-ice) per 60 minutes |
| 92 | `hdgf_p60` | `Float64` | yes | per 60 minutes | High-danger goals for (on-ice) per 60 minutes |
| 93 | `hdga_p60` | `Float64` | yes | per 60 minutes | High-danger goals against (on-ice) per 60 minutes |
| 94 | `xgf_p60` | `Float64` | yes | per 60 minutes | xG for (on-ice) per 60 minutes |
| 95 | `xga_p60` | `Float64` | yes | per 60 minutes | xG against (on-ice) per 60 minutes |
| 96 | `xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG for (on-ice) per 60 minutes |
| 97 | `xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted xG against (on-ice) per 60 minutes |
| 98 | `base_xgf_p60` | `Float64` | yes | per 60 minutes | Base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 99 | `base_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG for (on-ice) per 60 minutes, only with ``base_xg`` |
| 100 | `context_xgf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 101 | `base_xga_p60` | `Float64` | yes | per 60 minutes | Base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 102 | `base_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted base xG against (on-ice) per 60 minutes, only with ``base_xg`` |
| 103 | `context_xga_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 104 | `context_xgf_p60` | `Float64` | yes | per 60 minutes | Context xG for (on-ice) per 60 minutes, only with ``context_xg`` |
| 105 | `context_xga_p60` | `Float64` | yes | per 60 minutes | Context xG against (on-ice) per 60 minutes, only with ``context_xg`` |
| 106 | `sf_p60` | `Float64` | yes | per 60 minutes | Shots for (on-ice) per 60 minutes |
| 107 | `sa_p60` | `Float64` | yes | per 60 minutes | Shots against (on-ice) per 60 minutes |
| 108 | `sf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots for (on-ice) per 60 minutes |
| 109 | `sa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted shots against (on-ice) per 60 minutes |
| 110 | `hdsf_p60` | `Float64` | yes | per 60 minutes | High-danger shots for (on-ice) per 60 minutes |
| 111 | `hdsa_p60` | `Float64` | yes | per 60 minutes | High-danger shots against (on-ice) per 60 minutes |
| 112 | `ff_p60` | `Float64` | yes | per 60 minutes | Fenwick for (on-ice) per 60 minutes |
| 113 | `fa_p60` | `Float64` | yes | per 60 minutes | Fenwick against (on-ice) per 60 minutes |
| 114 | `ff_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick for (on-ice) per 60 minutes |
| 115 | `fa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted fenwick against (on-ice) per 60 minutes |
| 116 | `hdff_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick for (on-ice) per 60 minutes |
| 117 | `hdfa_p60` | `Float64` | yes | per 60 minutes | High-danger fenwick against (on-ice) per 60 minutes |
| 118 | `cf_p60` | `Float64` | yes | per 60 minutes | Corsi for (on-ice) per 60 minutes |
| 119 | `ca_p60` | `Float64` | yes | per 60 minutes | Corsi against (on-ice) per 60 minutes |
| 120 | `cf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi for (on-ice) per 60 minutes |
| 121 | `ca_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted corsi against (on-ice) per 60 minutes |
| 122 | `bsf_p60` | `Float64` | yes | per 60 minutes | Blocked shots for (on-ice) per 60 minutes |
| 123 | `bsa_p60` | `Float64` | yes | per 60 minutes | Blocked shots against (on-ice) per 60 minutes |
| 124 | `bsf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots for (on-ice) per 60 minutes |
| 125 | `bsa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted blocked shots against (on-ice) per 60 minutes |
| 126 | `msf_p60` | `Float64` | yes | per 60 minutes | Missed shots for (on-ice) per 60 minutes |
| 127 | `msa_p60` | `Float64` | yes | per 60 minutes | Missed shots against (on-ice) per 60 minutes |
| 128 | `msf_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots for (on-ice) per 60 minutes |
| 129 | `msa_adj_p60` | `Float64` | yes | per 60 minutes | Score- and venue-adjusted missed shots against (on-ice) per 60 minutes |
| 130 | `hdmsf_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots for (on-ice) per 60 minutes |
| 131 | `hdmsa_p60` | `Float64` | yes | per 60 minutes | High-danger missed shots against (on-ice) per 60 minutes |
| 132 | `teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts for blocked by a teammate (on-ice) per 60 minutes |
| 133 | `opp_teammate_block_p60` | `Float64` | yes | per 60 minutes | Shot attempts against blocked by one of the opponent's teammates (on-ice) per 60 minutes |
| 134 | `hf_p60` | `Float64` | yes | per 60 minutes | Hits for (on-ice) per 60 minutes |
| 135 | `ht_p60` | `Float64` | yes | per 60 minutes | Hits taken (on-ice) per 60 minutes |
| 136 | `pent0_p60` | `Float64` | yes | per 60 minutes | Penalty shots taken (on-ice) per 60 minutes |
| 137 | `pent2_p60` | `Float64` | yes | per 60 minutes | Minor penalties taken (on-ice) per 60 minutes |
| 138 | `pent4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties taken (on-ice) per 60 minutes |
| 139 | `pent5_p60` | `Float64` | yes | per 60 minutes | Major penalties taken (on-ice) per 60 minutes |
| 140 | `pent10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties taken (on-ice) per 60 minutes |
| 141 | `pend0_p60` | `Float64` | yes | per 60 minutes | Penalty shots drawn (on-ice) per 60 minutes |
| 142 | `pend2_p60` | `Float64` | yes | per 60 minutes | Minor penalties drawn (on-ice) per 60 minutes |
| 143 | `pend4_p60` | `Float64` | yes | per 60 minutes | Double minor penalties drawn (on-ice) per 60 minutes |
| 144 | `pend5_p60` | `Float64` | yes | per 60 minutes | Major penalties drawn (on-ice) per 60 minutes |
| 145 | `pend10_p60` | `Float64` | yes | per 60 minutes | 10-minute penalties drawn (on-ice) per 60 minutes |
| 146 | `gf_percent` | `Float64` | yes | share, 0 to 1 | On-ice goals for as a percentage of total on-ice goals i.e., GF / (GF + GA) |
| 147 | `gf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted goals for as a percentage of total on-ice adjusted goals i.e., GF_adj / (GF_adj + GA_adj) |
| 148 | `hdgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger goals for as a percentage of total on-ice high-danger goals i.e., HDGF / (HDGF + HDGA) |
| 149 | `xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice xG for as a percentage of total on-ice xG i.e., xGF / (xGF + xGA) |
| 150 | `xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted xG for as a percentage of total on-ice adjusted xG i.e., xGF_adj / (xGF_adj + xGA_adj) |
| 151 | `base_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice base xG for as a percentage of total on-ice base xG, only with ``base_xg`` i.e., base_xGF / (base_xGF + base_xGA) |
| 152 | `base_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted base xG for as a percentage of total on-ice adjusted base xG, only with ``base_xg`` i.e., base_xGF_adj / (base_xGF_adj + base_xGA_adj) |
| 153 | `context_xgf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted context xG for as a percentage of total on-ice adjusted context xG, only with ``context_xg`` i.e., context_xGF_adj / (context_xGF_adj + context_xGA_adj) |
| 154 | `context_xgf_percent` | `Float64` | yes | share, 0 to 1 | On-ice context xG for as a percentage of total on-ice context xG, only with ``context_xg`` i.e., context_xGF / (context_xGF + context_xGA) |
| 155 | `sf_percent` | `Float64` | yes | share, 0 to 1 | On-ice shots for as a percentage of total on-ice shots i.e., SF / (SF + SA) |
| 156 | `sf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted shots for as a percentage of total on-ice adjusted shots i.e., SF_adj / (SF_adj + SA_adj) |
| 157 | `hdsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger shots for as a percentage of total on-ice high-danger shots i.e., HDSF / (HDSF + HDSA) |
| 158 | `ff_percent` | `Float64` | yes | share, 0 to 1 | On-ice fenwick for as a percentage of total on-ice fenwick i.e., FF / (FF + FA) |
| 159 | `ff_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted fenwick for as a percentage of total on-ice adjusted fenwick i.e., FF_adj / (FF_adj + FA_adj) |
| 160 | `hdff_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger fenwick for as a percentage of total on-ice high-danger fenwick i.e., HDFF / (HDFF + HDFA) |
| 161 | `cf_percent` | `Float64` | yes | share, 0 to 1 | On-ice corsi for as a percentage of total on-ice corsi i.e., CF / (CF + CA) |
| 162 | `cf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted corsi for as a percentage of total on-ice adjusted corsi i.e., CF_adj / (CF_adj + CA_adj) |
| 163 | `bsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice blocked shots for as a percentage of total on-ice blocked shots i.e., BSF / (BSF + BSA) |
| 164 | `bsf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted blocked shots for as a percentage of total on-ice adjusted blocked shots i.e., BSF_adj / (BSF_adj + BSA_adj) |
| 165 | `msf_percent` | `Float64` | yes | share, 0 to 1 | On-ice missed shots for as a percentage of total on-ice missed shots i.e., MSF / (MSF + MSA) |
| 166 | `msf_adj_percent` | `Float64` | yes | share, 0 to 1 | On-ice score- and venue-adjusted missed shots for as a percentage of total on-ice adjusted missed shots i.e., MSF_adj / (MSF_adj + MSA_adj) |
| 167 | `hdmsf_percent` | `Float64` | yes | share, 0 to 1 | On-ice high-danger missed shots for as a percentage of total on-ice high-danger missed shots i.e., HDMSF / (HDMSF + HDMSA) |
| 168 | `hf_percent` | `Float64` | yes | share, 0 to 1 | On-ice hits for as a percentage of total on-ice hits i.e., HF / (HF + HT) |
| 169 | `take_percent` | `Float64` | yes | share, 0 to 1 | On-ice takeaways as a percentage of total on-ice giveaways and takeaways i.e., take / (take + give) |
