---
icon: material/table
description: "Columns, dtypes and nullability of standings in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: standings**

Returned by `Season.standings`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `date` | `String` | no |  |  |
| 3 | `team` | `String` | no |  | Team name, e.g., NSH |
| 4 | `team_name` | `String` | no |  | Full team name, e.g., NASHVILLE PREDATORS |
| 5 | `conference` | `String` | yes |  |  |
| 6 | `division` | `String` | yes |  |  |
| 7 | `games_played` | `Int64` | no |  |  |
| 8 | `points` | `Int64` | yes |  |  |
| 9 | `points_pct` | `Float64` | yes |  |  |
| 10 | `wins` | `Int64` | no |  |  |
| 11 | `regulation_wins` | `Int64` | no |  |  |
| 12 | `shootout_wins` | `Int64` | yes |  |  |
| 13 | `losses` | `Int64` | no |  |  |
| 14 | `ot_losses` | `Int64` | yes |  |  |
| 15 | `shootout_losses` | `Int64` | yes |  |  |
| 16 | `ties` | `Int64` | yes |  |  |
| 17 | `win_pct` | `Float64` | no |  |  |
| 18 | `regulation_win_pct` | `Float64` | no |  |  |
| 19 | `streak_code` | `String` | no |  |  |
| 20 | `streak_count` | `Int64` | no |  |  |
| 21 | `goals_for` | `Int64` | no |  |  |
| 22 | `goals_against` | `Int64` | no |  |  |
| 23 | `goals_for_pct` | `Float64` | no |  |  |
| 24 | `goal_differential` | `Int64` | no |  |  |
| 25 | `goal_differential_pct` | `Float64` | no |  |  |
| 26 | `home_games_played` | `Int64` | no |  |  |
| 27 | `home_points` | `Int64` | no |  |  |
| 28 | `home_goals_for` | `Int64` | no |  |  |
| 29 | `home_goals_against` | `Int64` | no |  |  |
| 30 | `home_goal_differential` | `Int64` | no |  |  |
| 31 | `home_wins` | `Int64` | no |  |  |
| 32 | `home_losses` | `Int64` | no |  |  |
| 33 | `home_ot_losses` | `Int64` | no |  |  |
| 34 | `home_ties` | `Int64` | no |  |  |
| 35 | `home_regulation_wins` | `Int64` | no |  |  |
| 36 | `road_games_played` | `Int64` | no |  |  |
| 37 | `road_points` | `Int64` | no |  |  |
| 38 | `road_goals_for` | `Int64` | no |  |  |
| 39 | `road_goals_against` | `Int64` | no |  |  |
| 40 | `road_goal_differential` | `Int64` | no |  |  |
| 41 | `road_wins` | `Int64` | no |  |  |
| 42 | `road_losses` | `Int64` | no |  |  |
| 43 | `road_ot_losses` | `Int64` | no |  |  |
| 44 | `road_ties` | `Int64` | no |  |  |
| 45 | `road_regulation_wins` | `Int64` | no |  |  |
| 46 | `l10_points` | `Int64` | no |  |  |
| 47 | `l10_goals_for` | `Int64` | no |  |  |
| 48 | `l10_goals_against` | `Int64` | no |  |  |
| 49 | `l10_goal_differential` | `Int64` | no |  |  |
| 50 | `l10_wins` | `Int64` | no |  |  |
| 51 | `l10_losses` | `Int64` | no |  |  |
| 52 | `l10_ot_losses` | `Int64` | no |  |  |
| 53 | `l10_ties` | `Int64` | no |  |  |
| 54 | `l10_regulation_wins` | `Int64` | no |  |  |
| 55 | `team_logo` | `String` | no |  |  |
| 56 | `wildcard_sequence` | `Int64` | no |  |  |
| 57 | `waivers_sequence` | `Int64` | no |  |  |
