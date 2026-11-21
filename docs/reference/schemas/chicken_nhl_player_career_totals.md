---
icon: material/table
description: "Columns, dtypes and nullability of player_career_totals in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: player_career_totals**

Returned by `Player.career_totals`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player_id` | `Int64` | no |  | NHL API player ID, e.g., 8476887 |
| 2 | `session` | `String` | no |  | Whether the totals are regular season (R) or playoffs (P), e.g., R |
| 3 | `games_played` | `Int64` | yes |  | Games played, e.g., 82 |
| 4 | `goals` | `Int64` | yes |  | Goals, e.g., 45 |
| 5 | `assists` | `Int64` | yes |  | Assists, e.g., 31 |
| 6 | `points` | `Int64` | yes |  | Goals plus assists, null when the NHL API gives none, e.g., 76 |
| 7 | `plus_minus` | `Int64` | yes |  | Even-strength and shorthanded goals for minus against while on the ice, e.g., 10 |
| 8 | `pim` | `Int64` | yes |  | Penalty minutes, e.g., 24 |
| 9 | `shots` | `Int64` | yes |  | Shots on goal, e.g., 269 |
| 10 | `shooting_pct` | `Float64` | yes |  | Goals divided by shots, e.g., 0.1673 |
| 11 | `faceoff_pct` | `Float64` | yes |  | Share of faceoffs won, e.g., 0.3284 |
| 12 | `power_play_goals` | `Int64` | yes |  | Power-play goals, e.g., 13 |
| 13 | `power_play_points` | `Int64` | yes |  | Power-play points, e.g., 26 |
| 14 | `shorthanded_goals` | `Int64` | yes |  | Shorthanded goals, e.g., 0 |
| 15 | `shorthanded_points` | `Int64` | yes |  | Shorthanded points, e.g., 0 |
| 16 | `game_winning_goals` | `Int64` | yes |  | Game-winning goals, e.g., 6 |
| 17 | `ot_goals` | `Int64` | yes |  | Overtime goals, e.g., 1 |
| 18 | `avg_toi` | `Float64` | yes | minutes | Average time on ice per game, in minutes, e.g., 18.166667 |
| 19 | `toi` | `Float64` | yes | minutes | Time on ice, in minutes; for a season or career, a goalie's total, e.g., 20.6 |
| 20 | `games_started` | `Int64` | yes |  | Games started in goal, e.g., 64 |
| 21 | `wins` | `Int64` | yes |  | Goalie wins, e.g., 35 |
| 22 | `losses` | `Int64` | yes |  | Goalie regulation losses, e.g., 24 |
| 23 | `ot_losses` | `Int64` | yes |  | Goalie overtime and shootout losses, e.g., 5 |
| 24 | `ties` | `Int64` | yes |  | Goalie ties, before the shootout began in 2005-06, e.g., 0 |
| 25 | `shots_against` | `Int64` | yes |  | Shots on goal faced, e.g., 2003 |
| 26 | `goals_against` | `Int64` | yes |  | Goals allowed, e.g., 180 |
| 27 | `goals_against_avg` | `Float64` | yes | per 60 minutes | Goals allowed per 60 minutes, e.g., 2.729884 |
| 28 | `save_pct` | `Float64` | yes |  | Saves divided by shots against, e.g., 0.912007 |
| 29 | `shutouts` | `Int64` | yes |  | Shutouts, e.g., 3 |
