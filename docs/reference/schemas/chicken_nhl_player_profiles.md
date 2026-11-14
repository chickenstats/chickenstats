---
icon: material/table
description: "Columns, dtypes and nullability of player_profiles in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: player_profiles**

Returned by `player_profiles`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player_id` | `Int64` | no |  | NHL API player ID, e.g., 8476887 |
| 2 | `player_name` | `String` | no |  | Player's first and last name, e.g., Filip Forsberg |
| 3 | `position_code` | `String` | yes |  | Position code, C, L, R, D or G, e.g., L |
| 4 | `shoots_catches` | `String` | yes |  | Shooting hand for a skater, catching hand for a goalie, L or R, e.g., R |
| 5 | `height_in_inches` | `Float64` | yes | inches | Height in inches, the NHL's current value, e.g., 73.0 |
| 6 | `weight_in_pounds` | `Float64` | yes | pounds | Weight in pounds, the NHL's current value, e.g., 205.0 |
| 7 | `birth_date` | `Date` | yes |  | Date of birth, e.g., 1994-08-13 |
| 8 | `is_active` | `Boolean` | no |  | Whether the player is on an NHL roster now, e.g., True |
| 9 | `left_handed` | `Int8` | yes |  | 1 when shoots_catches is L, 0 when it is R, otherwise null, e.g., 0 |
| 10 | `age` | `Float64` | yes | years | Age in years on the date given, days since birth_date over 365.25, e.g., 29.158111 |
