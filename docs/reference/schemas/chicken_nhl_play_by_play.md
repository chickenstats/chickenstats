---
icon: material/table
description: "Columns, dtypes and nullability of play_by_play in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: play_by_play**

Returned by `Scraper.play_by_play`, `Game.play_by_play_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `id` | `Int64` | no |  | The play ID for a given play, combining the game ID and the event_idx, e.g., 20190206840667 |
| 2 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 3 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 4 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 5 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 6 | `game_date` | `String` | no |  | Date game was played, e.g., 2020-01-09 |
| 7 | `event_idx` | `Int64` | no |  | Index ID for event, e.g., 667 |
| 8 | `period` | `Int64` | no |  | Period number of the event, e.g., 3 |
| 9 | `period_seconds` | `Int64` | no | seconds | Time elapsed in the period, in seconds, e.g., 1178 |
| 10 | `game_seconds` | `Int64` | no | seconds | Time elapsed in the game, in seconds, e.g., 3578 |
| 11 | `strength_state` | `String` | no |  | Strength state, e.g., 5vE |
| 12 | `event_team` | `String` | yes |  | Team that performed the action for the event, None for a faceoff with no winner, e.g., NSH |
| 13 | `opp_team` | `String` | yes |  | Opposing team, None for a faceoff with no winner, e.g., CHI |
| 14 | `event` | `String` | no |  | Type of event that occurred, e.g., GOAL |
| 15 | `description` | `String` | yes |  | Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT. |
| 16 | `zone` | `String` | yes |  | Zone where the event occurred, relative to the event team, e.g., DEF |
| 17 | `coords_x` | `Int64` | yes | feet | x-coordinates where the event occurred, e.g, -96 |
| 18 | `coords_y` | `Int64` | yes | feet | y-coordinates where the event occurred, e.g., 11 |
| 19 | `danger` | `Int64` | yes |  | Whether shot event occurred from danger area, e.g., 0 |
| 20 | `high_danger` | `Int64` | yes |  | Whether shot event occurred from high-danger area, e.g., 0 |
| 21 | `player_1` | `String` | yes |  | Player that performed the action, e.g., PEKKA RINNE |
| 22 | `player_1_eh_id` | `String` | yes |  | Evolving Hockey ID for player_1, e.g., PEKKA.RINNE |
| 23 | `player_1_eh_id_api` | `String` | yes |  | Evolving Hockey ID for player_1 from the api_events (for debugging), e.g., PEKKA.RINNE |
| 24 | `player_1_api_id` | `Int64` | yes |  | NHL API ID for player_1, e.g., 8471469 |
| 25 | `player_1_position` | `String` | yes |  | Position player_1 plays, e.g., G |
| 26 | `player_1_type` | `String` | yes |  | Type of player, e.g., GOAL SCORER |
| 27 | `player_2` | `String` | yes |  | Player that performed the action, e.g., None |
| 28 | `player_2_eh_id` | `String` | yes |  | Evolving Hockey ID for player_2, e.g., None |
| 29 | `player_2_eh_id_api` | `String` | yes |  | Evolving Hockey ID for player_2 from the api_events (for debugging), e.g., None |
| 30 | `player_2_api_id` | `Int64` | yes |  | NHL API ID for player_2, e.g., None |
| 31 | `player_2_position` | `String` | yes |  | Position player_2 plays, e.g., None |
| 32 | `player_2_type` | `String` | yes |  | Type of player, e.g., None |
| 33 | `player_3` | `String` | yes |  | Player that performed the action, e.g., None |
| 34 | `player_3_eh_id` | `String` | yes |  | Evolving Hockey ID for player_3, e.g., None |
| 35 | `player_3_eh_id_api` | `String` | yes |  | Evolving Hockey ID for player_3 from the api_events (for debugging), e.g., None |
| 36 | `player_3_api_id` | `Int64` | yes |  | NHL API ID for player_3, e.g., None |
| 37 | `player_3_position` | `String` | yes |  | Position player_3 plays, e.g., None |
| 38 | `player_3_type` | `String` | yes |  | Type of player, e.g., None |
| 39 | `score_state` | `String` | no |  | Score of the game from event team's perspective, e.g., 4v2 |
| 40 | `score_diff` | `Int64` | no |  | Score differential from event team's perspective, e.g., 2 |
| 41 | `forwards_percent` | `Float64` | no | share, 0 to 1 | Percentage of skaters (i.e., excluding goalies) on-ice that play forward positions (i,e., F, C, L, R), e.g, 0.6 |
| 42 | `opp_forwards_percent` | `Float64` | no | share, 0 to 1 | Percentage of opposing skaters (i.e., excluding goalies) on-ice that play forward positions (i.e., F, C, L, R), e.g., 0.667 |
| 43 | `shot_type` | `String` | yes |  | Type of shot taken, if event is a shot, e.g., WRIST |
| 44 | `highlight_clip_url` | `String` | yes |  | URL to the NHL's highlight clip for the event, if available (goals only), e.g., https://nhl.com/video/min-buf-jokiharju-scores-goal-against-wild-6340906550112 |
| 45 | `event_length` | `Int64` | no | seconds | Time elapsed between this event and the next event, e.g., 0 |
| 46 | `event_distance` | `Float64` | yes | feet | Calculated distance of event from goal, e.g, 185.32673849177834 |
| 47 | `pbp_distance` | `Int64` | yes | feet | Distance of event from goal from description, e.g., 185 |
| 48 | `event_angle` | `Float64` | yes | degrees | Angle of event towards goal, e.g., 57.52880770915151 |
| 49 | `penalty` | `String` | yes |  | Name of penalty, e.g., None |
| 50 | `penalty_length` | `Int64` | yes | minutes | Duration of penalty, e.g., None |
| 51 | `home_score` | `Int64` | no |  | Home team's score, e.g., 2 |
| 52 | `home_score_diff` | `Int64` | no |  | Home team's score differential, e.g., -2 |
| 53 | `away_score` | `Int64` | no |  | Away team's score, e.g., 4 |
| 54 | `away_score_diff` | `Int64` | no |  | Away team's score differential, e.g., 2 |
| 55 | `is_home` | `Int64` | no |  | Whether event team is home, e.g., 0 |
| 56 | `is_away` | `Int64` | no |  | Whether event is away, e.g., 1 |
| 57 | `home_team` | `String` | no |  | Home team, e.g., CHI |
| 58 | `away_team` | `String` | no |  | Away team, e.g., NSH |
| 59 | `home_skaters` | `Int64` | no |  | Number of home team skaters on-ice (excl. goalies), e.g., 6 |
| 60 | `away_skaters` | `Int64` | no |  | Number of away team skaters on-ice (excl. goalies), e.g., 5 |
| 61 | `home_on` | `String` | yes |  | Name of home team's skaters on-ice (incl. goalies), e.g., DUNCAN KEITH, PATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, ERIK GUSTAFSSON, KIRBY DACH |
| 62 | `home_on_eh_id` | `String` | yes |  | Evolving Hockey IDs of home team's skaters on-ice (incl. goalies), e.g., DUNCAN.KEITH, PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, ERIK.GUSTAFSSON2, KIRBY.DACH |
| 63 | `home_on_api_id` | `String` | yes |  | NHL API IDs of home team's skaters on-ice (incl. goalies), e.g., 8470281, 8474141, 8473604, 8479337, 8476979, 8481523 |
| 64 | `home_on_positions` | `String` | yes |  | Positions of home team's skaters on-ice (incl. goalies), e.g., D, R, C, R, D, C |
| 65 | `away_on` | `String` | yes |  | Name of away team's skaters on-ice (incl. goalies), e.g., PEKKA RINNE, NICK BONINO, ROMAN JOSI, MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND |
| 66 | `away_on_eh_id` | `String` | yes |  | Evolving Hockey IDs of away team's skaters on-ice (incl. goalies), e.g., PEKKA.RINNE, NICK.BONINO, ROMAN.JOSI, MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND |
| 67 | `away_on_api_id` | `String` | yes |  | NHL API IDs of away team's skaters on-ice (incl. goalies), e.g., 8471469, 8474009, 8474600, 8475218, 8475714, 8475798 |
| 68 | `away_on_positions` | `String` | yes |  | Positions of away team's skaters on-ice (incl. goalies), e.g., G, C, D, D, C, C |
| 69 | `event_team_skaters` | `Int64` | yes |  | Number of event team skaters on-ice (excl. goalies), e.g., 5 |
| 70 | `teammates` | `String` | yes |  | Name of event team's players on-ice (incl. goalies), e.g., PEKKA RINNE, NICK BONINO, ROMAN JOSI, MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND |
| 71 | `teammates_eh_id` | `String` | yes |  | Evolving Hockey IDs of event team's players on-ice (incl. goalies), e.g., PEKKA.RINNE, NICK.BONINO, ROMAN.JOSI, MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND |
| 72 | `teammates_api_id` | `String` | yes |  | NHL API IDs of event team's players on-ice (incl. goalies), e.g., 8471469, 8474009, 8474600, 8475218, 8475714, 8475798 |
| 73 | `teammates_positions` | `String` | yes |  | Positions of event team's players on-ice (incl. goalies), e.g., G, C, D, D, C, C |
| 74 | `own_goalie` | `String` | yes |  | Name of the event team's goalie, e.g., PEKKA RINNE |
| 75 | `own_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the event team's goalie, e.g., PEKKA.RINNE |
| 76 | `own_goalie_api_id` | `Int64` | yes |  | NHL API ID of the event team's goalie, e.g., 8471469 |
| 77 | `forwards` | `String` | yes |  | Name of event team's forwards on-ice, e.g., NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND |
| 78 | `forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of event team's forwards on-ice, e.g., NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND |
| 79 | `forwards_api_id` | `String` | yes |  | NHL API IDs of event team's forwards on-ice, e.g., 8474009, 8475714, 8475798 |
| 80 | `forwards_count` | `Int64` | yes |  | Number of teammate skaters on-ice (i.e., excluding goalies) who play forward positions (i.e., F, C, L, R), e.g., 3 |
| 81 | `defense` | `String` | yes |  | Name of event team's defense on-ice, e.g., ROMAN JOSI, MATTIAS EKHOLM |
| 82 | `defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of event team's defense on-ice, e.g., ROMAN.JOSI, MATTIAS.EKHOLM |
| 83 | `defense_api_id` | `String` | yes |  | NHL API IDs of event team's skaters on-ice, e.g., 8474600, 8475218 |
| 84 | `defense_count` | `Int64` | yes |  | Number of teammate skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2 |
| 85 | `opp_strength_state` | `String` | yes |  | Strength state from opposing team's perspective, e.g., Ev5 |
| 86 | `opp_score_state` | `String` | yes |  | Score state from opposing team's perspective, e.g., 2v4 |
| 87 | `opp_score_diff` | `Int64` | yes |  | Score differential from opposing team's perspective, e.g., -2 |
| 88 | `opp_team_skaters` | `Int64` | yes |  | Number of opposing team skaters on-ice (excl. goalies), e.g., 6 |
| 89 | `opp_team_on` | `String` | yes |  | Name of opposing team's players on-ice (incl. goalies), e.g., DUNCAN KEITH, PATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, ERIK GUSTAFSSON, KIRBY DACH |
| 90 | `opp_team_on_eh_id` | `String` | yes |  | Evolving Hockey IDs of opposing team's players on-ice (incl. goalies), e.g., DUNCAN.KEITH, PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, ERIK.GUSTAFSSON2, KIRBY.DACH |
| 91 | `opp_team_on_api_id` | `String` | yes |  | NHL API IDs of opposing team's players on-ice (incl. goalies), e.g., 8470281, 8474141, 8473604, 8479337, 8476979, 8481523 |
| 92 | `opp_team_on_positions` | `String` | yes |  | Positions of opposing team's players on-ice (incl. goalies), e.g., D, R, C, R, D, C |
| 93 | `opp_goalie` | `String` | yes |  | Name of the opposing team's goalie, e.g., None |
| 94 | `opp_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the opposing team's goalie, e.g., None |
| 95 | `opp_goalie_api_id` | `Int64` | yes |  | NHL API ID of the opposing team's goalie, e.g., None |
| 96 | `opp_forwards` | `String` | yes |  | Name of opposing team's forwards on-ice, e.g., PATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, KIRBY DACH |
| 97 | `opp_forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of opposing team's forwards on-ice, e.g., PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, KIRBY.DACH |
| 98 | `opp_forwards_api_id` | `String` | yes |  | NHL API IDs of opposing team's forwards on-ice, e.g., 8474141, 8473604, 8479337, 8481523 |
| 99 | `opp_forwards_count` | `Int64` | yes |  | Number of opposing skaters on-ice (i.e., excluding goalies) who play forward positions (i.e., F, C, L, R), e.g., 4 |
| 100 | `opp_defense` | `String` | yes |  | Name of opposing team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON |
| 101 | `opp_defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of opposing team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2 |
| 102 | `opp_defense_api_id` | `String` | yes |  | NHL API IDs of opposing team's skaters on-ice, e.g., 8470281, 8476979 |
| 103 | `opp_defense_count` | `Int64` | yes |  | Number of opposing skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2 |
| 104 | `home_forwards` | `String` | yes |  | Name of home team's forwards on-ice, e.g., PATRICK KANE, JONATHAN TOEWS, ALEX DEBRINCAT, KIRBY DACH |
| 105 | `home_forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of home team's forwards on-ice, e.g., PATRICK.KANE, JONATHAN.TOEWS, ALEX.DEBRINCAT, KIRBY.DACH |
| 106 | `home_forwards_api_id` | `String` | yes |  | NHL API IDs of home team's forwards on-ice, e.g., 8474141, 8473604, 8479337, 8481523 |
| 107 | `home_forwards_count` | `Int64` | yes |  | Number of home skaters on-ice (i.e., excluding goalies) who play forward positions (i.e., F, C, L, R), e.g., 4 |
| 108 | `home_forwards_percent` | `Float64` | no | share, 0 to 1 | Percentage of home skaters (i.e., excluding goalies) on-ice that play forward positions (i.e., F, C, L, R), e.g., 0.667 |
| 109 | `home_defense` | `String` | yes |  | Name of home team's defense on-ice, e.g., DUNCAN KEITH, ERIK GUSTAFSSON |
| 110 | `home_defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of home team's defense on-ice, e.g., DUNCAN.KEITH, ERIK.GUSTAFSSON2 |
| 111 | `home_defense_api_id` | `String` | yes |  | NHL API IDs of home team's skaters on-ice, e.g., 8470281, 8476979 |
| 112 | `home_defense_count` | `Int64` | yes |  | Number of home skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2 |
| 113 | `home_goalie` | `String` | yes |  | Name of the home team's goalie, e.g., None |
| 114 | `home_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the home team's goalie, e.g., None |
| 115 | `home_goalie_api_id` | `String` | yes |  | NHL API ID of the home team's goalie, e.g., None |
| 116 | `away_forwards` | `String` | yes |  | Name of away team's forwards on-ice, e.g., NICK BONINO, CALLE JARNKROK, MIKAEL GRANLUND |
| 117 | `away_forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of away team's forwards on-ice, e.g., NICK.BONINO, CALLE.JARNKROK, MIKAEL.GRANLUND |
| 118 | `away_forwards_api_id` | `String` | yes |  | NHL API IDs of away team's forwards on-ice, e.g., 8474009, 8475714, 8475798 |
| 119 | `away_forwards_count` | `Int64` | yes |  | Number of away skaters on-ice (i.e., excluding goalies) who play forward positions (i.e., F, C, L, R), e.g., 3 |
| 120 | `away_forwards_percent` | `Float64` | no | share, 0 to 1 | Percentage of away skaters (i.e., excluding goalies) on-ice that play forward positions (i.e., F, C, L, R), e.g., 0.6 |
| 121 | `away_defense` | `String` | yes |  | Name of away team's defense on-ice, e.g., ROMAN JOSI, MATTIAS EKHOLM |
| 122 | `away_defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of away team's defense on-ice, e.g., ROMAN.JOSI, MATTIAS.EKHOLM |
| 123 | `away_defense_api_id` | `String` | yes |  | NHL API IDs of away team's skaters on-ice, e.g., 8474600, 8475218 |
| 124 | `away_defense_count` | `Int64` | yes |  | Number of away skaters on-ice (i.e., excluding goalies) who play defensive positions (i.e., D), e.g., 2 |
| 125 | `away_goalie` | `String` | yes |  | Name of the away team's goalie, e.g., PEKKA RINNE |
| 126 | `away_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the away team's goalie, e.g., PEKKA.RINNE |
| 127 | `away_goalie_api_id` | `String` | yes |  | NHL API ID of the away team's goalie, e.g., 8471469 |
| 128 | `change_on_count` | `Int64` | yes |  | Number of players on, e.g., None |
| 129 | `change_off_count` | `Int64` | yes |  | Number of players off, e.g., None |
| 130 | `zone_start` | `String` | yes |  | The zone where the change occurred (OFF, DEF, NEU, or OTF), None at an end-zone faceoff with no winner, e.g., None |
| 131 | `change_on` | `String` | yes |  | Names of the players on, e.g., None |
| 132 | `change_on_eh_id` | `String` | yes |  | Evolving Hockey IDs of the players on, e.g., None |
| 133 | `change_on_api_id` | `String` | yes |  | NHL API IDs of the players on, e.g., None |
| 134 | `change_on_positions` | `String` | yes |  | Positions of the players on, e.g., None |
| 135 | `change_off` | `String` | yes |  | Names of the players off, e.g., None |
| 136 | `change_off_eh_id` | `String` | yes |  | Evolving Hockey IDs of the players off, e.g., None |
| 137 | `change_off_api_id` | `String` | yes |  | NHL API IDs of the players off, e.g., None |
| 138 | `change_off_positions` | `String` | yes |  | Positions of the players off, e.g., None |
| 139 | `change_on_forwards_count` | `Int64` | yes |  | Number of forwards changing on, e.g., None |
| 140 | `change_off_forwards_count` | `Int64` | yes |  | Number of forwards off, e.g., None |
| 141 | `change_on_forwards` | `String` | yes |  | Names of the forwards on, e.g., None |
| 142 | `change_on_forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of the forwards on, e.g., None |
| 143 | `change_on_forwards_api_id` | `String` | yes |  | NHL API IDs of the forwards on, e.g., None |
| 144 | `change_off_forwards` | `String` | yes |  | Names of the forwards off, e.g., None |
| 145 | `change_off_forwards_eh_id` | `String` | yes |  | Evolving Hockey IDs of the forwards off, e.g., None |
| 146 | `change_off_forwards_api_id` | `String` | yes |  | NHL API IDs of the forwards off, e.g., None |
| 147 | `change_on_defense_count` | `Int64` | yes |  | Number of defense on, e.g., None |
| 148 | `change_off_defense_count` | `Int64` | yes |  | Number of defense off, e.g., None |
| 149 | `change_on_defense` | `String` | yes |  | Names of the defense on, e.g., None |
| 150 | `change_on_defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of the defense on, e.g., None |
| 151 | `change_on_defense_api_id` | `String` | yes |  | NHL API IDs of the defense on, e.g., None |
| 152 | `change_off_defense` | `String` | yes |  | Names of the defense off, e.g., None |
| 153 | `change_off_defense_eh_id` | `String` | yes |  | Evolving Hockey IDs of the defense off, e.g., None |
| 154 | `change_off_defense_api_id` | `String` | yes |  | NHL API IDs of the defense off, e.g., None |
| 155 | `change_on_goalie_count` | `Int64` | yes |  | Number of goalies on, e.g., None |
| 156 | `change_off_goalie_count` | `Int64` | yes |  | Number of goalies off, e.g., None |
| 157 | `change_on_goalie` | `String` | yes |  | Name of goalie on, e.g., None |
| 158 | `change_on_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the goalie on, e.g., None |
| 159 | `change_on_goalie_api_id` | `String` | yes |  | NHL API ID of the goalie on, e.g., None |
| 160 | `change_off_goalie` | `String` | yes |  | Name of the goalie off, e.g., None |
| 161 | `change_off_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID of the goalie off, e.g., None |
| 162 | `change_off_goalie_api_id` | `String` | yes |  | NHL API ID of the goalie off, e.g., None |
| 163 | `goal` | `Int64` | no |  | Dummy indicator whether event is a goal, e.g., 1 |
| 164 | `goal_adj` | `Float64` | no |  | Score- and venue-adjusted value for a goal, e.g., 1.0 |
| 165 | `hd_goal` | `Int64` | no |  | Dummy indicator whether event is a high-danger goal, e.g., 0 |
| 166 | `shot` | `Int64` | no |  | Dummy indicator whether event is a shot, e.g., 1 |
| 167 | `shot_adj` | `Float64` | no |  | Score- and venue-adjusted value for a shot, e.g., 1.0 |
| 168 | `hd_shot` | `Int64` | no |  | Dummy indicator whether event is a high-danger shot, e.g., 0 |
| 169 | `miss` | `Int64` | no |  | Dummy indicator whether event is a miss, e.g., 0 |
| 170 | `miss_adj` | `Float64` | no |  | Score- and venue-adjusted value for a missed shot, e.g., 0.0 |
| 171 | `hd_miss` | `Int64` | no |  | Dummy indicator whether event is a high-danger missed shot, e.g., 0 |
| 172 | `fenwick` | `Int64` | no |  | Dummy indicator whether event is a fenwick event, e.g., 1 |
| 173 | `fenwick_adj` | `Float64` | no |  | Score- and venue-adjusted value for a fenwick event, e.g., 1.0 |
| 174 | `hd_fenwick` | `Int64` | no |  | Dummy indicator whether event is a high-danger fenwick event, e.g., 0 |
| 175 | `corsi` | `Int64` | no |  | Dummy indicator whether event is a corsi event, e.g., 1 |
| 176 | `corsi_adj` | `Float64` | no |  | Score- and venue-adjusted value for a corsi event, e.g., 1.0 |
| 177 | `block` | `Int64` | no |  | Dummy indicator whether event is a block, e.g., 0 |
| 178 | `block_adj` | `Float64` | no |  | Score- and venue-adjusted value for a blocked shot, e.g., 0.0 |
| 179 | `teammate_block` | `Int64` | no |  | Dummy indicator whether event is a shot blocked by a teammate, e.g., 0 |
| 180 | `teammate_block_adj` | `Float64` | no |  | Score- and venue-adjusted value for a shot blocked by a teammate, e.g., 0.0 |
| 181 | `hit` | `Int64` | no |  | Dummy indicator whether event is a hit, e.g., 0 |
| 182 | `give` | `Int64` | no |  | Dummy indicator whether event is a give, e.g., 0 |
| 183 | `take` | `Int64` | no |  | Dummy indicator whether event is a take, e.g., 0 |
| 184 | `fac` | `Int64` | no |  | Dummy indicator whether event is a faceoff, e.g., 0 |
| 185 | `penl` | `Int64` | no |  | Dummy indicator whether event is a penalty, e.g., 0 |
| 186 | `change` | `Int64` | no |  | Dummy indicator whether event is a change, e.g., 0 |
| 187 | `stop` | `Int64` | no |  | Dummy indicator whether event is a stop, e.g., 0 |
| 188 | `chl` | `Int64` | no |  | Dummy indicator whether event is a challenge, e.g., 0 |
| 189 | `ozf` | `Int64` | no |  | Dummy indicator whether event is a offensive zone faceoff, e.g., 0 |
| 190 | `nzf` | `Int64` | no |  | Dummy indicator whether event is a neutral zone faceoff, e.g., 0 |
| 191 | `dzf` | `Int64` | no |  | Dummy indicator whether event is a defensive zone faceoff, e.g., 0 |
| 192 | `ozc` | `Int64` | no |  | Dummy indicator whether event is a offensive zone change, e.g., 0 |
| 193 | `nzc` | `Int64` | no |  | Dummy indicator whether event is a neutral zone change, e.g., 0 |
| 194 | `dzc` | `Int64` | no |  | Dummy indicator whether event is a defensive zone change, e.g., 0 |
| 195 | `otf` | `Int64` | no |  | Dummy indicator whether event is an on-the-fly change, e.g., 0 |
| 196 | `pen0` | `Int64` | no |  | Dummy indicator whether event is a penalty, e.g., 0 |
| 197 | `pen2` | `Int64` | no |  | Dummy indicator whether event is a minor penalty, e.g., 0 |
| 198 | `pen4` | `Int64` | no |  | Dummy indicator whether event is a double minor penalty, e.g., 0 |
| 199 | `pen5` | `Int64` | no |  | Dummy indicator whether event is a major penalty, e.g., 0 |
| 200 | `pen10` | `Int64` | no |  | Dummy indicator whether event is a 10-minute penalty, such as a misconduct, e.g., 0 |
| 201 | `shootout_attempt` | `Int64` | no |  | Dummy indicator whether event is a shootout attempt, not counted as a goal, shot, fenwick or corsi event, e.g., 0 |
| 202 | `shootout_goal` | `Int64` | no |  | Dummy indicator whether event is a shootout goal, e.g., 0 |
