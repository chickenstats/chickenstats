---
icon: material/table
description: "Columns, dtypes and nullability of schedule in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: schedule**

Returned by `Season.schedule`, `multi_season_schedule`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | yes |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_type` | `Int64` | no |  |  |
| 4 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 5 | `game_date` | `String` | no |  | Date game was played, e.g., 2020-01-09 |
| 6 | `start_time` | `String` | no |  |  |
| 7 | `game_state` | `String` | no |  |  |
| 8 | `home_team` | `String` | no |  | Home team, e.g., CHI |
| 9 | `home_team_id` | `Int64` | no |  |  |
| 10 | `home_score` | `Int64` | yes |  | Home team's score, e.g., 2 |
| 11 | `away_team` | `String` | no |  | Away team, e.g., NSH |
| 12 | `away_team_id` | `Int64` | no |  |  |
| 13 | `away_score` | `Int64` | yes |  | Away team's score, e.g., 4 |
| 14 | `venue` | `String` | no |  |  |
| 15 | `venue_timezone` | `String` | no |  |  |
| 16 | `neutral_site` | `Int64` | no |  |  |
| 17 | `game_date_dt_local` | `Datetime(time_unit='us', time_zone=None)` | no |  |  |
| 18 | `game_date_dt_utc` | `Datetime(time_unit='us', time_zone='UTC')` | no |  |  |
| 19 | `tv_broadcasts` | `List(Struct({'id': Int64, 'market': String, 'countryCode': String, 'network': String, 'sequenceNumber': Int64}))` | no |  |  |
| 20 | `home_logo` | `String` | yes |  |  |
| 21 | `home_logo_dark` | `String` | yes |  |  |
| 22 | `away_logo` | `String` | yes |  |  |
| 23 | `away_logo_dark` | `String` | yes |  |  |
