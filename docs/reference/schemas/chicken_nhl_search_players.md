---
icon: material/table
description: "Columns, dtypes and nullability of search_players in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: search_players**

Returned by `search_players`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player_id` | `Int64` | no |  | NHL API player ID, e.g., 8476887 |
| 2 | `player_name` | `String` | no |  | Player's name, e.g., Filip Forsberg |
| 3 | `position_code` | `String` | yes |  | Position code, C, L, R, D or G, e.g., L |
| 4 | `team_abbrev` | `String` | yes |  | Three-letter code of the player's current team, null for a player without one, e.g., NSH |
| 5 | `last_team_abbrev` | `String` | yes |  | Three-letter code of the last team the player was on, e.g., NSH |
| 6 | `last_season_id` | `Int64` | yes |  | Last season the player was on a team, as 8-digit number, e.g., 20242025 |
| 7 | `sweater_number` | `Int64` | yes |  | Sweater number, e.g., 9 |
| 8 | `active` | `Boolean` | yes |  | Whether the player is active, e.g., True |
| 9 | `height` | `String` | yes |  | Height in feet and inches, e.g., 6'1" |
| 10 | `height_in_inches` | `Int64` | yes | inches | Height in inches, e.g., 73 |
| 11 | `height_in_centimeters` | `Int64` | yes | centimeters | Height in centimeters, e.g., 185 |
| 12 | `weight_in_pounds` | `Int64` | yes | pounds | Weight in pounds, e.g., 205 |
| 13 | `weight_in_kilograms` | `Int64` | yes | kilograms | Weight in kilograms, e.g., 93 |
| 14 | `birth_city` | `String` | yes |  | City of birth, e.g., Ostervala |
| 15 | `birth_state_province` | `String` | yes |  | State or province of birth, null outside North America, e.g., ON |
| 16 | `birth_country` | `String` | yes |  | Three-letter code of the country of birth, e.g., SWE |
