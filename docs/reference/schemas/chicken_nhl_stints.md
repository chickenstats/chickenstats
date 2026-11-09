---
icon: material/table
description: "Columns, dtypes and nullability of stints in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: stints**

Returned by `Scraper.stints`, `prep_stints`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 for 2023-24 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2023020001 |
| 4 | `game_date` | `String` | no |  | Date of the game, e.g., 2023-10-10 |
| 5 | `period` | `Int64` | no |  | Period, e.g., 3 |
| 6 | `stint_id` | `Int64` | no |  | Sequential stint number within the game and period, e.g., 42 |
| 7 | `toi_seconds` | `Int64` | no | seconds | Time on-ice for the stint, in seconds, e.g., 37; 0 for a stint whose events share one second |
| 8 | `strength_state` | `String` | no |  | Home then away skaters, with E for an empty net, e.g., 5v4 |
| 9 | `home_team` | `String` | no |  | Home team, e.g., NSH |
| 10 | `away_team` | `String` | no |  | Away team, e.g., TBL |
| 11 | `home_skater_ids` | `List(String)` | no |  | Home skater NHL API IDs, goalies excluded |
| 12 | `away_skater_ids` | `List(String)` | no |  | Away skater NHL API IDs, goalies excluded |
| 13 | `home_goalie_ids` | `List(String)` | no |  | Home goalie NHL API IDs on the ice |
| 14 | `away_goalie_ids` | `List(String)` | no |  | Away goalie NHL API IDs on the ice |
| 15 | `home_skater_count` | `Int64` | no |  | Number of home skaters on the ice, e.g., 5 |
| 16 | `away_skater_count` | `Int64` | no |  | Number of away skaters on the ice, e.g., 4 |
| 17 | `home_sf` | `Int64` | no |  | Home shots on goal, e.g., 1 |
| 18 | `away_sf` | `Int64` | no |  | Away shots on goal, e.g., 0 |
| 19 | `home_ff` | `Int64` | no |  | Home unblocked shot attempts, e.g., 2 |
| 20 | `away_ff` | `Int64` | no |  | Away unblocked shot attempts, e.g., 1 |
| 21 | `home_cf` | `Int64` | no |  | Home shot attempts, e.g., 3 |
| 22 | `away_cf` | `Int64` | no |  | Away shot attempts, e.g., 1 |
| 23 | `home_gf` | `Int64` | no |  | Home goals, e.g., 0 |
| 24 | `away_gf` | `Int64` | no |  | Away goals, e.g., 1 |
| 25 | `home_xgf` | `Float64` | yes |  | Home expected goals, e.g., 0.06 |
| 26 | `away_xgf` | `Float64` | yes |  | Away expected goals, e.g., 0.12 |
| 27 | `home_base_xgf` | `Float64` | yes |  | Home base expected goals, only with ``base_xg`` |
| 28 | `away_base_xgf` | `Float64` | yes |  | Away base expected goals, only with ``base_xg`` |
| 29 | `home_context_xgf` | `Float64` | yes |  | Home context expected goals, only with ``context_xg`` |
| 30 | `away_context_xgf` | `Float64` | yes |  | Away context expected goals, only with ``context_xg`` |
| 31 | `home_delta_xgf` | `Float64` | yes |  | Home context minus base expected goals |
| 32 | `away_delta_xgf` | `Float64` | yes |  | Away context minus base expected goals |
| 33 | `home_score_3` | `Int64` | no |  | Home score state as -1 trailing, 0 tied, or 1 leading |
| 34 | `home_score_7` | `Int64` | no |  | Home score differential, clamped to +/-3, e.g., -2 |
| 35 | `away_score_3` | `Int64` | no |  | Away score state as -1 trailing, 0 tied, or 1 leading |
| 36 | `away_score_7` | `Int64` | no |  | Away score differential, clamped to +/-3, e.g., 2 |
| 37 | `home_b2b` | `Boolean` | no |  | Whether the home team played the previous day, e.g., False |
| 38 | `away_b2b` | `Boolean` | no |  | Whether the away team played the previous day, e.g., True |
| 39 | `nzs` | `Boolean` | no |  | Whether the stint started with a neutral-zone faceoff, e.g., False |
| 40 | `home_ozs` | `Boolean` | no |  | Whether the home team started the stint in its offensive zone, e.g., True |
| 41 | `home_dzs` | `Boolean` | no |  | Whether the home team started the stint in its defensive zone, e.g., False |
| 42 | `away_ozs` | `Boolean` | no |  | Whether the away team started the stint in its offensive zone, e.g., False |
| 43 | `away_dzs` | `Boolean` | no |  | Whether the away team started the stint in its defensive zone, e.g., True |
