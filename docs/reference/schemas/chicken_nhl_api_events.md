---
icon: material/table
description: "Columns, dtypes and nullability of api_events in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: api_events**

Returned by `Scraper.api_events`, `Game.api_events_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 4 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 5 | `event_idx` | `Int64` | no |  | Index ID for event, e.g., 667 |
| 6 | `period` | `Int64` | no |  | Period number of the event, e.g., 3 |
| 7 | `period_type` | `String` | no |  |  |
| 8 | `period_seconds` | `Int64` | no | seconds | Time elapsed in the period, in seconds, e.g., 1178 |
| 9 | `game_seconds` | `Int64` | no | seconds | Time elapsed in the game, in seconds, e.g., 3578 |
| 10 | `event_team` | `String` | yes |  | Team that performed the action for the event, e.g., NSH |
| 11 | `event` | `String` | no |  | Type of event that occurred, e.g., GOAL |
| 12 | `event_code` | `Int64` | no |  | Code to indicate type of event that occurred, e.g., 505 |
| 13 | `description` | `String` | yes |  | Description of the event, e.g., None |
| 14 | `coords_x` | `Int64` | yes | feet | x-coordinates where the event occurred, e.g, -96 |
| 15 | `coords_y` | `Int64` | yes | feet | y-coordinates where the event occurred, e.g., 11 |
| 16 | `zone` | `String` | yes |  | Zone where the event occurred, relative to the event team, e.g., D |
| 17 | `player_1` | `String` | yes |  | Player that performed the action, e.g., PEKKA RINNE |
| 18 | `player_1_eh_id` | `String` | yes |  | Evolving Hockey ID for player_1, e.g., PEKKA.RINNE |
| 19 | `player_1_position` | `String` | yes |  | Position player_1 plays, e.g., G |
| 20 | `player_1_type` | `String` | yes |  | Type of player, e.g., GOAL SCORER |
| 21 | `player_1_api_id` | `Int64` | yes |  | NHL API ID for player_1, e.g., 8471469 |
| 22 | `player_1_team_jersey` | `String` | yes |  | Combination of team and jersey used for player identification, e.g., NSH35 |
| 23 | `player_2` | `String` | yes |  | Player that performed the action, e.g., None |
| 24 | `player_2_eh_id` | `String` | yes |  | Evolving Hockey ID for player_2, e.g., None |
| 25 | `player_2_position` | `String` | yes |  | Position player_2 plays, e.g., None |
| 26 | `player_2_type` | `String` | yes |  | Type of player, e.g., None |
| 27 | `player_2_api_id` | `Int64` | yes |  | NHL API ID for player_2, e.g., None |
| 28 | `player_2_team_jersey` | `String` | yes |  | Combination of team and jersey used for player identification, e.g., None |
| 29 | `player_3` | `String` | yes |  | Player that performed the action, e.g., None |
| 30 | `player_3_eh_id` | `String` | yes |  | Evolving Hockey ID for player_3, e.g., None |
| 31 | `player_3_position` | `String` | yes |  | Position player_3 plays, e.g., None |
| 32 | `player_3_type` | `String` | yes |  | Type of player, e.g., None |
| 33 | `player_3_api_id` | `Int64` | yes |  | NHL API ID for player_3, e.g., None |
| 34 | `player_3_team_jersey` | `String` | yes |  | Combination of team and jersey used for player identification, e.g., None |
| 35 | `strength` | `Int64` | yes |  | Code to indicate strength state, e.g., 1560 |
| 36 | `shot_type` | `String` | yes |  | Type of shot taken, if event is a shot, e.g., WRIST |
| 37 | `miss_reason` | `String` | yes |  | Reason shot missed, None when the API gives none, e.g., WIDE OF NET |
| 38 | `highlight_clip_url` | `String` | yes |  | URL to the NHL's highlight clip for the event, if available (goals only), e.g., https://nhl.com/video/min-buf-jokiharju-scores-goal-against-wild-6340906550112 |
| 39 | `opp_goalie` | `String` | yes |  | Opposing goalie, e.g., None |
| 40 | `opp_goalie_eh_id` | `String` | yes |  | Evolving Hockey ID for opposing goalie, e.g., None |
| 41 | `opp_goalie_api_id` | `Int64` | yes |  | NHL API ID for opposing goalie, e.g., None |
| 42 | `opp_goalie_team_jersey` | `String` | yes |  | Combination of team and jersey used for player identification, e.g., None |
| 43 | `event_team_id` | `Int64` | yes |  | NHL ID for the event team, e.g., 18 |
| 44 | `stoppage_reason` | `String` | yes |  | Reason the play was stopped, None when the API gives none, e.g., ICING |
| 45 | `stoppage_reason_secondary` | `String` | yes |  | Secondary reason play was stopped, None when the API gives none, e.g., TV TIMEOUT |
| 46 | `penalty_type` | `String` | yes |  | Type of penalty taken, e.g., None |
| 47 | `penalty_reason` | `String` | yes |  | Reason for the penalty, None when the API gives none, e.g., HOOKING |
| 48 | `penalty_duration` | `Int64` | yes |  | Duration of the penalty, e.g., None |
| 49 | `home_team_defending_side` | `String` | yes |  | Side of the ice the home team is defending, e.g., right |
| 50 | `version` | `Int64` | no |  | Increases with simultaneous events, used for combining events in the scraper, e.g., 1 |
