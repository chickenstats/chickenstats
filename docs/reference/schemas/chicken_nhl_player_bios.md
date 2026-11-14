---
icon: material/table
description: "Columns, dtypes and nullability of player_bios in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: player_bios**

Returned by `player_bios`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player_id` | `Int64` | no |  | NHL API player ID, e.g., 8476887 |
| 2 | `player_name` | `String` | no |  | Player's first and last name, e.g., Filip Forsberg |
| 3 | `position_code` | `String` | yes |  | Position code, C, L, R, D or G, e.g., L |
| 4 | `shoots_catches` | `String` | yes |  | Shooting hand for a skater, catching hand for a goalie, L or R, e.g., R |
| 5 | `height_in_inches` | `Int64` | yes | inches | Height in inches, the NHL's current value, e.g., 73 |
| 6 | `weight_in_pounds` | `Int64` | yes | pounds | Weight in pounds, the NHL's current value, e.g., 205 |
| 7 | `birth_date` | `Date` | yes |  | Date of birth, e.g., 1994-08-13 |
| 8 | `is_active` | `Boolean` | no |  | Whether the player is on an NHL roster now, e.g., True |
