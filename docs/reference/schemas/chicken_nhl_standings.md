---
icon: material/table
description: "Columns, dtypes and nullability of standings in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: standings**

Returned by `Season.standings`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 |
| 2 | `date` | `String` | no |  | Date of the standings, e.g., 2024-04-18 |
| 3 | `team` | `String` | no |  | Three-letter team code, e.g., NSH |
| 4 | `team_name` | `String` | no |  | Full team name, e.g., Nashville Predators |
| 5 | `conference` | `String` | yes |  | Conference the team plays in, null when the NHL API gives none, e.g., Western |
| 6 | `division` | `String` | yes |  | Division the team plays in, null when the NHL API gives none, e.g., Central |
| 7 | `games_played` | `Int64` | no |  | Games played, e.g., 82 |
| 8 | `points` | `Int64` | yes |  | Standings points, null when the NHL API gives none, e.g., 99 |
| 9 | `points_pct` | `Float64` | yes |  | Points as a share of the points available, 0 when the NHL API gives none, e.g., 0.603659 |
| 10 | `wins` | `Int64` | no |  | Wins, in regulation, overtime or the shootout, e.g., 47 |
| 11 | `regulation_wins` | `Int64` | no |  | Wins in regulation, e.g., 38 |
| 12 | `shootout_wins` | `Int64` | yes |  | Wins in the shootout, null when the NHL API gives none, e.g., 3 |
| 13 | `losses` | `Int64` | no |  | Losses in regulation, e.g., 30 |
| 14 | `ot_losses` | `Int64` | yes |  | Losses in overtime or the shootout, null when the NHL API gives none, e.g., 5 |
| 15 | `shootout_losses` | `Int64` | yes |  | Losses in the shootout, null when the NHL API gives none, e.g., 0 |
| 16 | `ties` | `Int64` | yes |  | Ties, null when the NHL API gives none, e.g., 0 |
| 17 | `win_pct` | `Float64` | no |  | Wins divided by games played, 0 when the NHL API gives none, e.g., 0.573171 |
| 18 | `regulation_win_pct` | `Float64` | no |  | Regulation wins divided by games played, 0 when the NHL API gives none, e.g., 0.463415 |
| 19 | `streak_code` | `String` | yes |  | Result of the team's current streak, W, L or OT, null when the NHL API gives none, e.g., L |
| 20 | `streak_count` | `Int64` | no |  | Games in the team's current streak, 0 when the NHL API gives none, e.g., 1 |
| 21 | `goals_for` | `Int64` | no |  | Goals scored, e.g., 269 |
| 22 | `goals_against` | `Int64` | no |  | Goals allowed, e.g., 248 |
| 23 | `goals_for_pct` | `Float64` | no |  | Goals scored per game played, 0 when the NHL API gives none, e.g., 3.280488 |
| 24 | `goal_differential` | `Int64` | no |  | Goals scored minus goals allowed, e.g., 21 |
| 25 | `goal_differential_pct` | `Float64` | no |  | Goal differential per game played, 0 when the NHL API gives none, e.g., 0.256098 |
| 26 | `home_games_played` | `Int64` | no |  | Games played at home, e.g., 41 |
| 27 | `home_points` | `Int64` | no |  | Standings points from home games, e.g., 48 |
| 28 | `home_goals_for` | `Int64` | no |  | Goals scored in home games, e.g., 135 |
| 29 | `home_goals_against` | `Int64` | no |  | Goals allowed in home games, e.g., 126 |
| 30 | `home_goal_differential` | `Int64` | no |  | Goals scored minus goals allowed in home games, e.g., 9 |
| 31 | `home_wins` | `Int64` | no |  | Wins at home, e.g., 23 |
| 32 | `home_losses` | `Int64` | no |  | Regulation losses at home, e.g., 16 |
| 33 | `home_ot_losses` | `Int64` | no |  | Overtime and shootout losses at home, e.g., 2 |
| 34 | `home_ties` | `Int64` | no |  | Ties at home, e.g., 0 |
| 35 | `home_regulation_wins` | `Int64` | no |  | Regulation wins at home, e.g., 18 |
| 36 | `road_games_played` | `Int64` | no |  | Games played on the road, e.g., 41 |
| 37 | `road_points` | `Int64` | no |  | Standings points from road games, e.g., 51 |
| 38 | `road_goals_for` | `Int64` | no |  | Goals scored in road games, e.g., 134 |
| 39 | `road_goals_against` | `Int64` | no |  | Goals allowed in road games, e.g., 122 |
| 40 | `road_goal_differential` | `Int64` | no |  | Goals scored minus goals allowed in road games, e.g., 12 |
| 41 | `road_wins` | `Int64` | no |  | Wins on the road, e.g., 24 |
| 42 | `road_losses` | `Int64` | no |  | Regulation losses on the road, e.g., 14 |
| 43 | `road_ot_losses` | `Int64` | no |  | Overtime and shootout losses on the road, e.g., 3 |
| 44 | `road_ties` | `Int64` | no |  | Ties on the road, e.g., 0 |
| 45 | `road_regulation_wins` | `Int64` | no |  | Regulation wins on the road, e.g., 20 |
| 46 | `l10_points` | `Int64` | no |  | Standings points in the last ten games, e.g., 9 |
| 47 | `l10_goals_for` | `Int64` | no |  | Goals scored in the last ten games, e.g., 33 |
| 48 | `l10_goals_against` | `Int64` | no |  | Goals allowed in the last ten games, e.g., 38 |
| 49 | `l10_goal_differential` | `Int64` | no |  | Goals scored minus goals allowed in the last ten games, e.g., -5 |
| 50 | `l10_wins` | `Int64` | no |  | Wins in the last ten games, e.g., 4 |
| 51 | `l10_losses` | `Int64` | no |  | Regulation losses in the last ten games, e.g., 5 |
| 52 | `l10_ot_losses` | `Int64` | no |  | Overtime and shootout losses in the last ten games, e.g., 1 |
| 53 | `l10_ties` | `Int64` | no |  | Ties in the last ten games, e.g., 0 |
| 54 | `l10_regulation_wins` | `Int64` | no |  | Regulation wins in the last ten games, e.g., 3 |
| 55 | `team_logo` | `String` | no |  | URL of the team's logo, e.g., https://assets.nhle.com/logos/nhl/svg/NSH_light.svg |
| 56 | `wildcard_sequence` | `Int64` | no |  | Place in the conference's wild-card race, 0 for a team in a top-three division spot, e.g., 1 |
| 57 | `waivers_sequence` | `Int64` | no |  | Place in the waiver priority order, 1 for the first claim, e.g., 22 |
