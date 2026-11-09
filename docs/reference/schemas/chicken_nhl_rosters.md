---
icon: material/table
description: "Columns, dtypes and nullability of rosters in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: rosters**

Returned by `Scraper.rosters`, `Game.rosters_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 4 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 5 | `team` | `String` | no |  | Team name, e.g., NSH |
| 6 | `team_name` | `String` | no |  | Full team name, e.g., NASHVILLE PREDATORS |
| 7 | `team_venue` | `String` | no |  | Whether team is home or away, e.g., AWAY |
| 8 | `player_name` | `String` | no |  | Player's name, e.g., FILIP FORSBERG |
| 9 | `api_id` | `Int64` | yes |  | Player's NHL API ID, e.g., 8476887 |
| 10 | `eh_id` | `String` | no |  | Evolving Hockey ID for the player, e.g., FILIP.FORSBERG |
| 11 | `team_jersey` | `String` | no |  | Team and jersey combination used for player identification, e.g., NSH9 |
| 12 | `jersey` | `Int64` | no |  | Player's jersey number, e.g., 9 |
| 13 | `position` | `String` | no |  | Player's position, e.g., L |
| 14 | `starter` | `Int64` | no |  | Whether the player started the game, e.g., 0 |
| 15 | `status` | `String` | no |  | Whether player is active or scratched, e.g., ACTIVE |
| 16 | `headshot_url` | `String` | yes |  | URL to get player's headshot, e.g., https://assets.nhle.com/mugs/nhl/20192020/NSH/8476887.png |
