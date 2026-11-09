---
icon: material/table
description: "Columns, dtypes and nullability of play-by-play in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: play-by-play**

Returned by `evolving_hockey.prep_pbp`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `id` | `Int64` | no |  | Play ID, the game ID followed by event_index padded to four digits, e.g., 20230200010149 |
| 2 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 |
| 3 | `session` | `String` | no |  | Whether game is regular season or playoffs, e.g., R |
| 4 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2023020001 |
| 5 | `game_date` | `String` | no |  | Date game was played, e.g., 2023-10-10 |
| 6 | `event_index` | `Int64` | no |  | Index of the event in the game, as the export gives it, e.g., 149 |
| 7 | `period` | `Int64` | no |  | Period number of the event, 0 when the export gives none, e.g., 1 |
| 8 | `period_seconds` | `Int64` | no | seconds | Time elapsed in the period, in seconds, 0 in a regular-season shootout, e.g., 588 |
| 9 | `game_seconds` | `Int64` | no | seconds | Time elapsed in the game, in seconds, 0 when the export gives none, e.g., 588 |
| 10 | `clock_time` | `String` | no | MM:SS | Time left in the period, as the export gives it, e.g., 10:12 |
| 11 | `strength_state` | `String` | yes |  | Skaters on the ice for the event team, then the other team, with E for an empty net, null when the event has no team, e.g., 5v5 |
| 12 | `event_team` | `String` | yes |  | Team that performed the event, null when the event has no team, e.g., TBL |
| 13 | `opp_team` | `String` | yes |  | Team that did not perform the event, null when the event has no team, e.g., NSH |
| 14 | `event_type` | `String` | no |  | Type of event, as the export gives it, e.g., GOAL |
| 15 | `event_description` | `String` | yes |  | Description of the event, as the export gives it, e.g., TBL #86 KUCHEROV(1), SLAP , OFF. ZONE, 42 FT. |
| 16 | `event_detail` | `String` | yes |  | Shot type of a shot attempt or length of a penalty, as the export gives it, e.g., Slap |
| 17 | `event_zone` | `String` | yes |  | Zone where the event occurred, relative to the event team, null when the export gives none, e.g., OFF |
| 18 | `coords_x` | `Float64` | yes | feet | x-coordinate where the event occurred, null when the export gives none, e.g., 50.0 |
| 19 | `coords_y` | `Float64` | yes | feet | y-coordinate where the event occurred, null when the export gives none, e.g., -16.0 |
| 20 | `high_danger` | `Int64` | no |  | Whether the event is an unblocked shot attempt from the high-danger area of the offensive zone, e.g., 0 |
| 21 | `danger` | `Int64` | no |  | Whether the event is an unblocked shot attempt from the danger area of the offensive zone, outside the high-danger area, e.g., 1 |
| 22 | `event_player_1` | `String` | yes |  | First player in the event, such as the shooter, the faceoff winner, the hitter or the penalized player, e.g., NIKITA KUCHEROV |
| 23 | `event_player_1_eh_id` | `String` | yes |  | Evolving Hockey ID for event_player_1, e.g., NIKITA.KUCHEROV |
| 24 | `event_player_1_pos` | `String` | yes |  | Position of event_player_1, from the shifts export, e.g., R |
| 25 | `event_player_2` | `String` | yes |  | Second player in the event, such as the primary assist, the faceoff loser, the player hit, the blocker or the player who drew the penalty, e.g., VICTOR HEDMAN |
| 26 | `event_player_2_eh_id` | `String` | yes |  | Evolving Hockey ID for event_player_2, e.g., VICTOR.HEDMAN |
| 27 | `event_player_2_pos` | `String` | yes |  | Position of event_player_2, from the shifts export, e.g., D |
| 28 | `event_player_3` | `String` | yes |  | Third player in the event, the secondary assist, e.g., BRAYDEN POINT |
| 29 | `event_player_3_eh_id` | `String` | yes |  | Evolving Hockey ID for event_player_3, e.g., BRAYDEN.POINT |
| 30 | `event_player_3_pos` | `String` | yes |  | Position of event_player_3, from the shifts export, e.g., C |
| 31 | `score_state` | `String` | yes |  | Score from the event team's perspective, or the home team's when the event has no team, e.g., 0v0 |
| 32 | `event_length` | `Int64` | no | seconds | Time between this event and the next, in seconds, as the export gives it, e.g., 0 |
| 33 | `event_distance` | `Float64` | yes | feet | Distance of the event from the goal, as the export gives it, e.g., 42.154478 |
| 34 | `pbp_distance` | `Float64` | yes | feet | Distance of the event from the goal, from the description, as the export gives it, e.g., 42.0 |
| 35 | `event_angle` | `Float64` | yes | degrees | Angle of the event towards the goal, as the export gives it, e.g., 22.306205 |
| 36 | `home_score` | `Int64` | yes |  | Home team's score. Only with columns="all", e.g., 0 |
| 37 | `away_score` | `Int64` | yes |  | Away team's score. Only with columns="all", e.g., 0 |
| 38 | `is_home` | `Int64` | yes |  | Whether the event team is the home team, 0 when the event has no team, e.g., 1 |
| 39 | `home_team` | `String` | yes |  | Home team. Only with columns="all", e.g., TBL |
| 40 | `away_team` | `String` | yes |  | Away team. Only with columns="all", e.g., NSH |
| 41 | `home_skaters` | `Int64` | yes |  | Home team skaters on the ice, as the export gives it. Only with columns="all", e.g., 5 |
| 42 | `away_skaters` | `Int64` | yes |  | Away team skaters on the ice, as the export gives it. Only with columns="all", e.g., 5 |
| 43 | `home_zone` | `String` | yes |  | Zone where the event occurred, relative to the home team, as the export writes it. Only with columns="all", e.g., Off |
| 44 | `home_goalie` | `String` | yes |  | Home team's goalie, as the export writes the name, null when the export gives none. Only with columns="all", e.g., JONAS.JOHANSSON |
| 45 | `away_goalie` | `String` | yes |  | Away team's goalie, as the export writes the name, null when the export gives none. Only with columns="all", e.g., JUUSE.SAROS |
| 46 | `home_zonestart` | `Float64` | yes |  | The export's home_zonestart column, passed through unchanged. Only with columns="all", e.g., None |
| 47 | `face_index` | `Int64` | yes |  | The export's face_index column, passed through unchanged. Only with columns="all", e.g., 4 |
| 48 | `pen_index` | `Int64` | yes |  | The export's pen_index column, passed through unchanged. Only with columns="all", e.g., 0 |
| 49 | `shift_index` | `Int64` | yes |  | The export's shift_index column, passed through unchanged. Only with columns="all", e.g., 104 |
| 50 | `game_score_state` | `String` | yes |  | Score from the home team's perspective. Only with columns="all", e.g., 0v0 |
| 51 | `game_strength_state` | `String` | yes |  | Strength state from the home team's perspective, as the export gives it. Only with columns="all", e.g., 5v5 |
| 52 | `forwards` | `String` | yes |  | Names of the event team's forwards on the ice, sorted by name, null when there are none, e.g., BRAYDEN POINT, NIKITA KUCHEROV, STEVEN STAMKOS |
| 53 | `forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of the event team's forwards on the ice, in the same order, e.g., BRAYDEN.POINT, NIKITA.KUCHEROV, STEVEN.STAMKOS |
| 54 | `defense` | `String` | yes |  | Names of the event team's defense on the ice, sorted by name, null when there are none, e.g., NICK PERBIX, VICTOR HEDMAN |
| 55 | `defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of the event team's defense on the ice, in the same order, e.g., NICK.PERBIX, VICTOR.HEDMAN |
| 56 | `own_goalie` | `String` | yes |  | Event team's goalie on the ice, null for an empty net or an event with no team, e.g., JONAS JOHANSSON |
| 57 | `own_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the event team's goalie, e.g., JONAS.JOHANSSON |
| 58 | `event_on_1` | `String` | yes |  | Player in on-ice slot 1 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 59 | `event_on_1_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_1, e.g., NIKITA.KUCHEROV |
| 60 | `event_on_1_pos` | `String` | yes |  | Position of event_on_1, e.g., R |
| 61 | `event_on_2` | `String` | yes |  | Player in on-ice slot 2 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 62 | `event_on_2_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_2, e.g., NIKITA.KUCHEROV |
| 63 | `event_on_2_pos` | `String` | yes |  | Position of event_on_2, e.g., R |
| 64 | `event_on_3` | `String` | yes |  | Player in on-ice slot 3 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 65 | `event_on_3_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_3, e.g., NIKITA.KUCHEROV |
| 66 | `event_on_3_pos` | `String` | yes |  | Position of event_on_3, e.g., R |
| 67 | `event_on_4` | `String` | yes |  | Player in on-ice slot 4 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 68 | `event_on_4_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_4, e.g., NIKITA.KUCHEROV |
| 69 | `event_on_4_pos` | `String` | yes |  | Position of event_on_4, e.g., R |
| 70 | `event_on_5` | `String` | yes |  | Player in on-ice slot 5 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 71 | `event_on_5_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_5, e.g., NIKITA.KUCHEROV |
| 72 | `event_on_5_pos` | `String` | yes |  | Position of event_on_5, e.g., R |
| 73 | `event_on_6` | `String` | yes |  | Player in on-ice slot 6 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 74 | `event_on_6_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_6, e.g., NIKITA.KUCHEROV |
| 75 | `event_on_6_pos` | `String` | yes |  | Position of event_on_6, e.g., R |
| 76 | `event_on_7` | `String` | yes |  | Player in on-ice slot 7 of the event team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 77 | `event_on_7_eh_id` | `String` | yes |  | Evolving Hockey ID for event_on_7, e.g., NIKITA.KUCHEROV |
| 78 | `event_on_7_pos` | `String` | yes |  | Position of event_on_7, e.g., R |
| 79 | `opp_strength_state` | `String` | yes |  | Strength state from the other team's perspective, null when the event has no team. Only with columns="full" or "all", e.g., 5v5 |
| 80 | `opp_score_state` | `String` | yes |  | Score from the other team's perspective, or the away team's when the event has no team. Only with columns="full" or "all", e.g., 0v0 |
| 81 | `opp_forwards` | `String` | yes |  | Names of the other team's forwards on the ice, sorted by name, null when there are none, e.g., FILIP FORSBERG, JUUSO PARSSINEN, RYAN O'REILLY |
| 82 | `opp_forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of the other team's forwards on the ice, in the same order, e.g., FILIP.FORSBERG, JUUSO.PARSSINEN, RYAN.O'REILLY |
| 83 | `opp_defense` | `String` | yes |  | Names of the other team's defense on the ice, sorted by name, null when there are none, e.g., LUKE SCHENN, ROMAN JOSI |
| 84 | `opp_defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of the other team's defense on the ice, in the same order, e.g., LUKE.SCHENN, ROMAN.JOSI |
| 85 | `opp_goalie` | `String` | yes |  | Other team's goalie on the ice, null for an empty net or an event with no team, e.g., JUUSE SAROS |
| 86 | `opp_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the other team's goalie, e.g., JUUSE.SAROS |
| 87 | `opp_on_1` | `String` | yes |  | Player in on-ice slot 1 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 88 | `opp_on_1_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_1, e.g., NIKITA.KUCHEROV |
| 89 | `opp_on_1_pos` | `String` | yes |  | Position of opp_on_1, e.g., R |
| 90 | `opp_on_2` | `String` | yes |  | Player in on-ice slot 2 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 91 | `opp_on_2_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_2, e.g., NIKITA.KUCHEROV |
| 92 | `opp_on_2_pos` | `String` | yes |  | Position of opp_on_2, e.g., R |
| 93 | `opp_on_3` | `String` | yes |  | Player in on-ice slot 3 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 94 | `opp_on_3_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_3, e.g., NIKITA.KUCHEROV |
| 95 | `opp_on_3_pos` | `String` | yes |  | Position of opp_on_3, e.g., R |
| 96 | `opp_on_4` | `String` | yes |  | Player in on-ice slot 4 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 97 | `opp_on_4_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_4, e.g., NIKITA.KUCHEROV |
| 98 | `opp_on_4_pos` | `String` | yes |  | Position of opp_on_4, e.g., R |
| 99 | `opp_on_5` | `String` | yes |  | Player in on-ice slot 5 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 100 | `opp_on_5_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_5, e.g., NIKITA.KUCHEROV |
| 101 | `opp_on_5_pos` | `String` | yes |  | Position of opp_on_5, e.g., R |
| 102 | `opp_on_6` | `String` | yes |  | Player in on-ice slot 6 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 103 | `opp_on_6_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_6, e.g., NIKITA.KUCHEROV |
| 104 | `opp_on_6_pos` | `String` | yes |  | Position of opp_on_6, e.g., R |
| 105 | `opp_on_7` | `String` | yes |  | Player in on-ice slot 7 of the other team, null when the slot is empty or the event has no team. Only with columns="full" or "all", e.g., NIKITA KUCHEROV |
| 106 | `opp_on_7_eh_id` | `String` | yes |  | Evolving Hockey ID for opp_on_7, e.g., NIKITA.KUCHEROV |
| 107 | `opp_on_7_pos` | `String` | yes |  | Position of opp_on_7, e.g., R |
| 108 | `num_on` | `Float64` | yes |  | Number of players coming on in a change, null for other events, e.g., 1.0 |
| 109 | `num_off` | `Float64` | yes |  | Number of players going off in a change, null for other events, e.g., 1.0 |
| 110 | `players_on` | `String` | yes |  | Names of the players coming on in a change, null for other events, e.g., YAKOV TRENIN |
| 111 | `players_on_eh_id` | `String` | yes |  | Evolving Hockey IDs of the players coming on, e.g., YAKOV.TRENIN |
| 112 | `players_on_pos` | `String` | yes |  | Positions of the players coming on, e.g., C |
| 113 | `players_off` | `String` | yes |  | Names of the players going off in a change, null for other events, e.g., FILIP FORSBERG |
| 114 | `players_off_eh_id` | `String` | yes |  | Evolving Hockey IDs of the players going off, e.g., FILIP.FORSBERG |
| 115 | `players_off_pos` | `String` | yes |  | Positions of the players going off, e.g., L |
| 116 | `zone_start` | `String` | yes |  | For a change, the zone of a faceoff in the same second, relative to the changing team (OFF, DEF or NEU), or OTF when there is none; null for other events, e.g., OTF |
| 117 | `goal` | `Int64` | no |  | Dummy indicator whether event is a goal, 0 for a shootout goal, e.g., 1 |
| 118 | `hd_goal` | `Int64` | no |  | Dummy indicator whether event is a high-danger goal, e.g., 0 |
| 119 | `goal_adj` | `Float64` | no |  | Score- and venue-adjusted value for a goal, e.g., 0.97653 |
| 120 | `pred_goal` | `Float64` | yes |  | The export's xG for an unblocked shot attempt, null for other events and shootout attempts, e.g., 0.023173 |
| 121 | `pred_goal_adj` | `Float64` | yes |  | Score- and venue-adjusted pred_goal, e.g., 0.022491 |
| 122 | `shot` | `Int64` | no |  | Dummy indicator whether event is a shot on goal, goals included, 0 in a shootout, e.g., 1 |
| 123 | `hd_shot` | `Int64` | no |  | Dummy indicator whether event is a high-danger shot on goal, e.g., 0 |
| 124 | `shot_adj` | `Float64` | no |  | Score- and venue-adjusted value for a shot on goal, e.g., 0.977604 |
| 125 | `miss` | `Int64` | no |  | Dummy indicator whether event is a missed shot, 0 in a shootout, e.g., 0 |
| 126 | `miss_adj` | `Float64` | no |  | Score- and venue-adjusted value for a missed shot, e.g., 0.0 |
| 127 | `hd_miss` | `Int64` | no |  | Dummy indicator whether event is a high-danger missed shot, e.g., 0 |
| 128 | `fenwick` | `Int64` | no |  | Dummy indicator whether event is a fenwick event, shot plus miss, e.g., 1 |
| 129 | `hd_fenwick` | `Int64` | no |  | Dummy indicator whether event is a high-danger fenwick event, e.g., 0 |
| 130 | `fenwick_adj` | `Float64` | no |  | Score- and venue-adjusted value for a fenwick event, e.g., 0.974523 |
| 131 | `corsi` | `Int64` | no |  | Dummy indicator whether event is a corsi event, fenwick plus block, e.g., 1 |
| 132 | `corsi_adj` | `Float64` | no |  | Score- and venue-adjusted value for a corsi event, e.g., 0.976102 |
| 133 | `block` | `Int64` | no |  | Dummy indicator whether event is a blocked shot, teammate blocks included, e.g., 0 |
| 134 | `block_adj` | `Float64` | no |  | Score- and venue-adjusted value for a blocked shot, e.g., 0.0 |
| 135 | `teammate_block` | `Int64` | no |  | Dummy indicator whether event is a shot blocked by a teammate, e.g., 0 |
| 136 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0 |
| 137 | `shootout_attempt` | `Int64` | no |  | Dummy indicator whether event is an unblocked shot attempt in a regular-season shootout, e.g., 0 |
| 138 | `shootout_goal` | `Int64` | no |  | Dummy indicator whether event is a goal in a regular-season shootout, e.g., 0 |
| 139 | `hit` | `Int64` | no |  | Dummy indicator whether event is a hit, e.g., 0 |
| 140 | `give` | `Int64` | no |  | Dummy indicator whether event is a give, e.g., 0 |
| 141 | `take` | `Int64` | no |  | Dummy indicator whether event is a take, e.g., 0 |
| 142 | `fac` | `Int64` | no |  | Dummy indicator whether event is a faceoff, e.g., 0 |
| 143 | `pen0` | `Int64` | no |  | Dummy indicator whether event is a penalty, e.g., 0 |
| 144 | `pen2` | `Int64` | no |  | Dummy indicator whether event is a minor penalty, e.g., 0 |
| 145 | `pen4` | `Int64` | no |  | Dummy indicator whether event is a double minor penalty, e.g., 0 |
| 146 | `pen5` | `Int64` | no |  | Dummy indicator whether event is a major penalty, e.g., 0 |
| 147 | `pen10` | `Int64` | no |  | Dummy indicator whether event is a 10-minute penalty, such as a misconduct, e.g., 0 |
| 148 | `change` | `Int64` | no |  | Dummy indicator whether event is a change, e.g., 0 |
| 149 | `stop` | `Int64` | no |  | Dummy indicator whether event is a stop, e.g., 0 |
| 150 | `ozf` | `Int64` | no |  | Dummy indicator whether event is a offensive zone faceoff, e.g., 0 |
| 151 | `nzf` | `Int64` | no |  | Dummy indicator whether event is a neutral zone faceoff, e.g., 0 |
| 152 | `dzf` | `Int64` | no |  | Dummy indicator whether event is a defensive zone faceoff, e.g., 0 |
| 153 | `ozs` | `Int64` | no |  | Dummy indicator whether event is a change with an offensive zone start, e.g., 0 |
| 154 | `nzs` | `Int64` | no |  | Dummy indicator whether event is a change with a neutral zone start, e.g., 0 |
| 155 | `dzs` | `Int64` | no |  | Dummy indicator whether event is a change with a defensive zone start, e.g., 0 |
| 156 | `otf` | `Int64` | no |  | Dummy indicator whether event is an on-the-fly change, e.g., 0 |
