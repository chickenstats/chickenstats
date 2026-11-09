---
icon: material/table
description: "Columns, dtypes and nullability of xg_fields in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: xg_fields**

Returned by `Scraper.xg_fields`, `Game.xg_fields_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 2 | `event_idx` | `Int64` | no |  | Index ID for event, e.g., 331 |
| 3 | `period` | `Int64` | no |  | Period number of the event, e.g., 3 |
| 4 | `period_seconds` | `Int64` | no | seconds | Time elapsed in the period, in seconds, e.g., 1178 |
| 5 | `score_diff` | `Int64` | no |  | Score differential from event team's perspective, e.g., 2 |
| 6 | `danger` | `Int64` | no |  | Whether shot event occurred from danger area, e.g., 0 |
| 7 | `high_danger` | `Int64` | no |  | Whether shot event occurred from high-danger area, e.g., 0 |
| 8 | `position` | `String` | no |  | Player's position, e.g., L |
| 9 | `shot_type` | `String` | no |  | Type of shot taken, if event is a shot, e.g., WRIST |
| 10 | `strength_state` | `String` | no |  | Strength state, e.g., 5vE |
| 11 | `event_distance` | `Float64` | yes | feet | Calculated distance of event from goal, e.g, 185.32673849177834 |
| 12 | `event_angle` | `Float64` | yes | degrees | Angle of event towards goal, e.g., 57.52880770915151 |
| 13 | `coords_x` | `Float64` | yes | feet | x-coordinates where the event occurred, e.g, -96 |
| 14 | `coords_y` | `Float64` | yes | feet | y-coordinates where the event occurred, e.g., 11 |
| 15 | `is_rebound` | `Int64` | no |  |  |
| 16 | `rush_attempt` | `Int64` | no |  |  |
| 17 | `is_scramble` | `Int64` | no |  |  |
| 18 | `is_home` | `Int64` | no |  | Whether event team is home, e.g., 0 |
| 19 | `seconds_since_last` | `Float64` | yes | seconds |  |
| 20 | `distance_from_last` | `Float64` | yes | feet |  |
| 21 | `play_speed` | `Float64` | yes |  |  |
| 22 | `prior_event_angle` | `Float64` | yes | degrees |  |
| 23 | `prior_event_distance` | `Float64` | yes | feet |  |
| 24 | `seconds_since_stoppage` | `Float64` | yes | seconds |  |
| 25 | `abs_y_distance` | `Float64` | yes | feet |  |
| 26 | `prior_event_same` | `String` | yes |  |  |
| 27 | `prior_event_opp` | `String` | yes |  |  |
| 28 | `prior_shot_type` | `String` | yes |  |  |
| 29 | `prior_face` | `Int64` | no |  |  |
| 30 | `seconds_since_event_team_change` | `Float64` | yes | seconds |  |
| 31 | `seconds_since_opp_team_change` | `Float64` | yes | seconds |  |
