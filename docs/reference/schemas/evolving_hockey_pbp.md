---
icon: material/table
description: "Columns, dtypes and nullability of play-by-play in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: play-by-play**

Returned by `evolving_hockey.prep_pbp`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit |
|--:|--------|-------|----------|------|
| 1 | `id` | `Int64` | no |  |
| 2 | `season` | `Int64` | no |  |
| 3 | `session` | `String` | no |  |
| 4 | `game_id` | `Int64` | no |  |
| 5 | `game_date` | `String` | no |  |
| 6 | `event_index` | `Int64` | no |  |
| 7 | `period` | `Int64` | no |  |
| 8 | `period_seconds` | `Int64` | no | seconds |
| 9 | `game_seconds` | `Int64` | no | seconds |
| 10 | `clock_time` | `String` | no |  |
| 11 | `strength_state` | `String` | yes |  |
| 12 | `event_team` | `String` | yes |  |
| 13 | `opp_team` | `String` | yes |  |
| 14 | `event_type` | `String` | no |  |
| 15 | `event_description` | `String` | yes |  |
| 16 | `event_detail` | `String` | yes |  |
| 17 | `event_zone` | `String` | yes |  |
| 18 | `coords_x` | `Float64` | yes | feet |
| 19 | `coords_y` | `Float64` | yes | feet |
| 20 | `high_danger` | `Int64` | no |  |
| 21 | `danger` | `Int64` | no |  |
| 22 | `event_player_1` | `String` | yes |  |
| 23 | `event_player_1_eh_id` | `String` | yes |  |
| 24 | `event_player_1_pos` | `String` | yes |  |
| 25 | `event_player_2` | `String` | yes |  |
| 26 | `event_player_2_eh_id` | `String` | yes |  |
| 27 | `event_player_2_pos` | `String` | yes |  |
| 28 | `event_player_3` | `String` | yes |  |
| 29 | `event_player_3_eh_id` | `String` | yes |  |
| 30 | `event_player_3_pos` | `String` | yes |  |
| 31 | `score_state` | `String` | yes |  |
| 32 | `event_length` | `Int64` | no | seconds |
| 33 | `event_distance` | `Float64` | yes | feet |
| 34 | `pbp_distance` | `Float64` | yes | feet |
| 35 | `event_angle` | `Float64` | yes | degrees |
| 36 | `home_score` | `Int64` | yes |  |
| 37 | `away_score` | `Int64` | yes |  |
| 38 | `is_home` | `Int64` | yes |  |
| 39 | `home_team` | `String` | yes |  |
| 40 | `away_team` | `String` | yes |  |
| 41 | `home_skaters` | `Int64` | yes |  |
| 42 | `away_skaters` | `Int64` | yes |  |
| 43 | `home_zone` | `String` | yes |  |
| 44 | `home_goalie` | `String` | yes |  |
| 45 | `away_goalie` | `String` | yes |  |
| 46 | `home_zonestart` | `Float64` | yes |  |
| 47 | `face_index` | `Int64` | yes |  |
| 48 | `pen_index` | `Int64` | yes |  |
| 49 | `shift_index` | `Int64` | yes |  |
| 50 | `game_score_state` | `String` | yes |  |
| 51 | `game_strength_state` | `String` | yes |  |
| 52 | `forwards` | `String` | yes |  |
| 53 | `forwards_eh_id` | `String` | yes |  |
| 54 | `defense` | `String` | yes |  |
| 55 | `defense_eh_id` | `String` | yes |  |
| 56 | `own_goalie` | `String` | yes |  |
| 57 | `own_goalie_eh_id` | `String` | yes |  |
| 58 | `event_on_1` | `String` | yes |  |
| 59 | `event_on_1_eh_id` | `String` | yes |  |
| 60 | `event_on_1_pos` | `String` | yes |  |
| 61 | `event_on_2` | `String` | yes |  |
| 62 | `event_on_2_eh_id` | `String` | yes |  |
| 63 | `event_on_2_pos` | `String` | yes |  |
| 64 | `event_on_3` | `String` | yes |  |
| 65 | `event_on_3_eh_id` | `String` | yes |  |
| 66 | `event_on_3_pos` | `String` | yes |  |
| 67 | `event_on_4` | `String` | yes |  |
| 68 | `event_on_4_eh_id` | `String` | yes |  |
| 69 | `event_on_4_pos` | `String` | yes |  |
| 70 | `event_on_5` | `String` | yes |  |
| 71 | `event_on_5_eh_id` | `String` | yes |  |
| 72 | `event_on_5_pos` | `String` | yes |  |
| 73 | `event_on_6` | `String` | yes |  |
| 74 | `event_on_6_eh_id` | `String` | yes |  |
| 75 | `event_on_6_pos` | `String` | yes |  |
| 76 | `event_on_7` | `String` | yes |  |
| 77 | `event_on_7_eh_id` | `String` | yes |  |
| 78 | `event_on_7_pos` | `String` | yes |  |
| 79 | `opp_strength_state` | `String` | yes |  |
| 80 | `opp_score_state` | `String` | yes |  |
| 81 | `opp_forwards` | `String` | yes |  |
| 82 | `opp_forwards_eh_id` | `String` | yes |  |
| 83 | `opp_defense` | `String` | yes |  |
| 84 | `opp_defense_eh_id` | `String` | yes |  |
| 85 | `opp_goalie` | `String` | yes |  |
| 86 | `opp_goalie_eh_id` | `String` | yes |  |
| 87 | `opp_on_1` | `String` | yes |  |
| 88 | `opp_on_1_eh_id` | `String` | yes |  |
| 89 | `opp_on_1_pos` | `String` | yes |  |
| 90 | `opp_on_2` | `String` | yes |  |
| 91 | `opp_on_2_eh_id` | `String` | yes |  |
| 92 | `opp_on_2_pos` | `String` | yes |  |
| 93 | `opp_on_3` | `String` | yes |  |
| 94 | `opp_on_3_eh_id` | `String` | yes |  |
| 95 | `opp_on_3_pos` | `String` | yes |  |
| 96 | `opp_on_4` | `String` | yes |  |
| 97 | `opp_on_4_eh_id` | `String` | yes |  |
| 98 | `opp_on_4_pos` | `String` | yes |  |
| 99 | `opp_on_5` | `String` | yes |  |
| 100 | `opp_on_5_eh_id` | `String` | yes |  |
| 101 | `opp_on_5_pos` | `String` | yes |  |
| 102 | `opp_on_6` | `String` | yes |  |
| 103 | `opp_on_6_eh_id` | `String` | yes |  |
| 104 | `opp_on_6_pos` | `String` | yes |  |
| 105 | `opp_on_7` | `String` | yes |  |
| 106 | `opp_on_7_eh_id` | `String` | yes |  |
| 107 | `opp_on_7_pos` | `String` | yes |  |
| 108 | `num_on` | `Float64` | yes |  |
| 109 | `num_off` | `Float64` | yes |  |
| 110 | `players_on` | `String` | yes |  |
| 111 | `players_on_eh_id` | `String` | yes |  |
| 112 | `players_on_pos` | `String` | yes |  |
| 113 | `players_off` | `String` | yes |  |
| 114 | `players_off_eh_id` | `String` | yes |  |
| 115 | `players_off_pos` | `String` | yes |  |
| 116 | `zone_start` | `String` | yes |  |
| 117 | `goal` | `Int64` | no |  |
| 118 | `hd_goal` | `Int64` | no |  |
| 119 | `goal_adj` | `Float64` | no |  |
| 120 | `pred_goal` | `Float64` | yes |  |
| 121 | `pred_goal_adj` | `Float64` | yes |  |
| 122 | `shot` | `Int64` | no |  |
| 123 | `hd_shot` | `Int64` | no |  |
| 124 | `shot_adj` | `Float64` | no |  |
| 125 | `miss` | `Int64` | no |  |
| 126 | `miss_adj` | `Float64` | no |  |
| 127 | `hd_miss` | `Int64` | no |  |
| 128 | `fenwick` | `Int64` | no |  |
| 129 | `hd_fenwick` | `Int64` | no |  |
| 130 | `fenwick_adj` | `Float64` | no |  |
| 131 | `corsi` | `Int64` | no |  |
| 132 | `corsi_adj` | `Float64` | no |  |
| 133 | `block` | `Int64` | no |  |
| 134 | `block_adj` | `Float64` | no |  |
| 135 | `teammate_block` | `Int64` | no |  |
| 136 | `teammate_block_adj` | `Float64` | no |  |
| 137 | `shootout_attempt` | `Int64` | no |  |
| 138 | `shootout_goal` | `Int64` | no |  |
| 139 | `hit` | `Int64` | no |  |
| 140 | `give` | `Int64` | no |  |
| 141 | `take` | `Int64` | no |  |
| 142 | `fac` | `Int64` | no |  |
| 143 | `pen0` | `Int64` | no |  |
| 144 | `pen2` | `Int64` | no |  |
| 145 | `pen4` | `Int64` | no |  |
| 146 | `pen5` | `Int64` | no |  |
| 147 | `pen10` | `Int64` | no |  |
| 148 | `change` | `Int64` | no |  |
| 149 | `stop` | `Int64` | no |  |
| 150 | `ozf` | `Int64` | no |  |
| 151 | `nzf` | `Int64` | no |  |
| 152 | `dzf` | `Int64` | no |  |
| 153 | `ozs` | `Int64` | no |  |
| 154 | `nzs` | `Int64` | no |  |
| 155 | `dzs` | `Int64` | no |  |
| 156 | `otf` | `Int64` | no |  |
