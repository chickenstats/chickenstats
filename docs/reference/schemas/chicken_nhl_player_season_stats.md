---
icon: material/table
description: "Columns, dtypes and nullability of player_season_stats in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: player_season_stats**

Returned by `Player.season_stats`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player_id` | `Int64` | no |  | NHL API player ID, e.g., 8476887 |
| 2 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 |
| 3 | `session` | `String` | no |  | Whether the stats are regular season (R) or playoffs (P), e.g., R |
| 4 | `league` | `String` | no |  | League the stats are from, as the NHL API abbreviates it, e.g., NHL |
| 5 | `team_name` | `String` | no |  | Name of the player's team, e.g., Nashville Predators |
| 6 | `games_played` | `Int64` | yes |  | Games played, e.g., 82 |
| 7 | `goals` | `Int64` | yes |  | Goals, e.g., 45 |
| 8 | `assists` | `Int64` | yes |  | Assists, e.g., 31 |
| 9 | `points` | `Int64` | yes |  | Goals plus assists, null when the NHL API gives none, e.g., 76 |
| 10 | `plus_minus` | `Int64` | yes |  | Even-strength and shorthanded goals for minus against while on the ice, e.g., 10 |
| 11 | `pim` | `Int64` | yes |  | Penalty minutes, e.g., 24 |
| 12 | `shots` | `Int64` | yes |  | Shots on goal, e.g., 269 |
| 13 | `shooting_pct` | `Float64` | yes |  | Goals divided by shots, e.g., 0.1673 |
| 14 | `faceoff_pct` | `Float64` | yes |  | Share of faceoffs won, e.g., 0.3284 |
| 15 | `power_play_goals` | `Int64` | yes |  | Power-play goals, e.g., 13 |
| 16 | `power_play_points` | `Int64` | yes |  | Power-play points, e.g., 26 |
| 17 | `shorthanded_goals` | `Int64` | yes |  | Shorthanded goals, e.g., 0 |
| 18 | `shorthanded_points` | `Int64` | yes |  | Shorthanded points, e.g., 0 |
| 19 | `game_winning_goals` | `Int64` | yes |  | Game-winning goals, e.g., 6 |
| 20 | `ot_goals` | `Int64` | yes |  | Overtime goals, e.g., 1 |
| 21 | `avg_toi` | `Float64` | yes | minutes | Average time on ice per game, in minutes, e.g., 18.166667 |
| 22 | `toi` | `Float64` | yes | minutes | Time on ice, in minutes; for a season or career, a goalie's total, e.g., 20.6 |
| 23 | `games_started` | `Int64` | yes |  | Games started in goal, e.g., 64 |
| 24 | `wins` | `Int64` | yes |  | Goalie wins, e.g., 35 |
| 25 | `losses` | `Int64` | yes |  | Goalie regulation losses, e.g., 24 |
| 26 | `ot_losses` | `Int64` | yes |  | Goalie overtime and shootout losses, e.g., 5 |
| 27 | `ties` | `Int64` | yes |  | Goalie ties, before the shootout began in 2005-06, e.g., 0 |
| 28 | `shots_against` | `Int64` | yes |  | Shots on goal faced, e.g., 2003 |
| 29 | `goals_against` | `Int64` | yes |  | Goals allowed, e.g., 180 |
| 30 | `goals_against_avg` | `Float64` | yes | per 60 minutes | Goals allowed per 60 minutes, e.g., 2.729884 |
| 31 | `save_pct` | `Float64` | yes |  | Saves divided by shots against, e.g., 0.912007 |
| 32 | `shutouts` | `Int64` | yes |  | Shutouts, e.g., 3 |
