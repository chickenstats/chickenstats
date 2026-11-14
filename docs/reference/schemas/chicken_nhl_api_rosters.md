---
icon: material/table
description: "Columns, dtypes and nullability of api_rosters in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: api_rosters**

Returned by `Scraper.api_rosters`, `Game.api_rosters_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 4 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 5 | `team` | `String` | no |  | Team name, e.g., NSH |
| 6 | `team_venue` | `String` | no |  | Whether team is home or away, e.g., AWAY |
| 7 | `player_name` | `String` | no |  | Player's name, e.g., FILIP FORSBERG |
| 8 | `eh_id` | `String` | no |  | Evolving Hockey ID for the player, e.g., FILIP.FORSBERG |
| 9 | `api_id` | `Int64` | no |  | NHL API ID for the player, e.g., 8476887 |
| 10 | `team_jersey` | `String` | no |  | Team and jersey combination used for player identification, e.g., NSH9 |
| 11 | `jersey` | `Int64` | no |  | Player's jersey number, e.g., 9 |
| 12 | `position` | `String` | no |  | Player's position, e.g., L |
| 13 | `first_name` | `String` | no |  | Player's first name, e.g., FILIP |
| 14 | `last_name` | `String` | no |  | Player's last name, e.g., FORSBERG |
| 15 | `headshot_url` | `String` | yes |  | URL to retrieve player's headshot, None when the API gives none |
