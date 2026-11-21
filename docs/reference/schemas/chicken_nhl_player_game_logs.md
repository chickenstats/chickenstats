---
icon: material/table
description: "Columns, dtypes and nullability of player_game_logs in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: player_game_logs**

Returned by `Player.game_logs`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player_id` | `Int64` | no |  | NHL API player ID, e.g., 8476887 |
| 2 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20262027 |
| 3 | `session` | `String` | no |  | Whether the game is regular season (R), playoffs (P) or pre-season (PR), e.g., R |
| 4 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2026020076 |
| 5 | `game_date` | `Date` | no |  | Date of the game, e.g., 2026-10-10 |
| 6 | `team` | `String` | no |  | Three-letter code of the player's team, e.g., NSH |
| 7 | `opponent` | `String` | no |  | Three-letter code of the opposing team, e.g., OTT |
| 8 | `is_home` | `Boolean` | no |  | Whether the player's team was at home, e.g., False |
| 9 | `goals` | `Int64` | no |  | Goals, e.g., 0 |
| 10 | `assists` | `Int64` | no |  | Assists, e.g., 0 |
| 11 | `points` | `Int64` | yes |  | Goals plus assists, null when the NHL API gives none, e.g., 76 |
| 12 | `plus_minus` | `Int64` | yes |  | Even-strength and shorthanded goals for minus against while on the ice, e.g., 10 |
| 13 | `pim` | `Int64` | no |  | Penalty minutes, e.g., 2 |
| 14 | `shots` | `Int64` | yes |  | Shots on goal, e.g., 269 |
| 15 | `shifts` | `Int64` | yes |  | Shifts, e.g., 23 |
| 16 | `power_play_goals` | `Int64` | yes |  | Power-play goals, e.g., 13 |
| 17 | `power_play_points` | `Int64` | yes |  | Power-play points, e.g., 26 |
| 18 | `shorthanded_goals` | `Int64` | yes |  | Shorthanded goals, e.g., 0 |
| 19 | `shorthanded_points` | `Int64` | yes |  | Shorthanded points, e.g., 0 |
| 20 | `game_winning_goals` | `Int64` | yes |  | Game-winning goals, e.g., 6 |
| 21 | `ot_goals` | `Int64` | yes |  | Overtime goals, e.g., 1 |
| 22 | `toi` | `Float64` | no | minutes | Time on ice, in minutes, e.g., 20.6 |
| 23 | `games_started` | `Int64` | yes |  | Games started in goal, e.g., 64 |
| 24 | `decision` | `String` | yes |  | Goalie's decision, W, L or O for an overtime or shootout loss, e.g., W |
| 25 | `shots_against` | `Int64` | yes |  | Shots on goal faced, e.g., 2003 |
| 26 | `goals_against` | `Int64` | yes |  | Goals allowed, e.g., 180 |
| 27 | `save_pct` | `Float64` | yes |  | Saves divided by shots against, e.g., 0.912007 |
| 28 | `shutouts` | `Int64` | yes |  | Shutouts, e.g., 3 |
