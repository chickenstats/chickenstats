---
icon: material/table
description: "Columns, dtypes and nullability of shifts in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: shifts**

Returned by `Scraper.shifts`, `Game.shifts_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 4 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 5 | `team` | `String` | no |  | Team name, e.g., NSH |
| 6 | `team_name` | `String` | no |  | Full team name, e.g., NASHVILLE PREDATORS |
| 7 | `player_name` | `String` | no |  | Player's name, e.g., FILIP FORSBERG |
| 8 | `eh_id` | `String` | no |  | Evolving Hockey ID for the player, e.g., FILIP.FORSBERG |
| 9 | `api_id` | `Int64` | no |  | NHL API ID for the player, e.g., 8475166 |
| 10 | `team_jersey` | `String` | no |  | Team and jersey combination used for player identification, e.g., NSH9 |
| 11 | `position` | `String` | no |  | Player's position, e.g., L |
| 12 | `jersey` | `Int64` | no |  | Player's jersey number, e.g., 9 |
| 13 | `shift_count` | `Int64` | no |  | Shift number for that player, e.g., 1 |
| 14 | `period` | `Int64` | no |  | Period number for the shift, e.g., 1 |
| 15 | `start_time` | `String` | no | MM:SS | Time shift started, e.g., 0:00 |
| 16 | `end_time` | `String` | no | MM:SS | Time shift ended, e.g., 0:18 |
| 17 | `duration` | `String` | no | MM:SS | Length of shift, e.g., 00:18 |
| 18 | `start_time_seconds` | `Int64` | no | seconds | Time shift started in seconds, e.g., 0 |
| 19 | `end_time_seconds` | `Int64` | no | seconds | Time shift ended in seconds, e.g., 18 |
| 20 | `duration_seconds` | `Int64` | no | seconds | Length of shift in seconds, e.g., 18 |
| 21 | `shift_start` | `String` | no | MM:SS | Time the shift started as the original string, e.g., 0:00 / 20:00 |
| 22 | `shift_end` | `String` | no | MM:SS | Time the shift ended as the original string, e.g., 0:18 / 19:42 |
| 23 | `goalie` | `Int64` | no |  | Whether player is a goalie, e.g., 0 |
| 24 | `is_home` | `Int64` | no |  | Whether player is home, e.g., 0 |
| 25 | `is_away` | `Int64` | no |  | Whether player is away, e.g., 1 |
| 26 | `team_venue` | `String` | no |  | Whether player is home or away, e.g., AWAY |
