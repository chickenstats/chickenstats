---
icon: material/table
description: "Columns, dtypes and nullability of schedule in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: schedule**

Returned by `Season.schedule`, `multi_season_schedule`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20232024 |
| 2 | `session` | `String` | yes |  | Whether game is regular season (R), playoffs (P), pre-season (PR) or 4 Nations Face-Off (FO), null for any other game type, such as the All-Star Game, e.g., R |
| 3 | `game_type` | `Int64` | no |  | NHL game type: 1 for pre-season, 2 for regular season, 3 for playoffs, 19 for a 4 Nations Face-Off game and 20 for its final, e.g., 2 |
| 4 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2023020001 |
| 5 | `game_date` | `String` | no |  | Date of the game in the venue's time zone, e.g., 2023-10-10 |
| 6 | `start_time` | `String` | no |  | Start time of the game in the venue's time zone, on a 24-hour clock, e.g., 17:30 |
| 7 | `game_state` | `String` | no |  | State of the game as the NHL API gives it, such as FUT or OFF, e.g., OFF |
| 8 | `home_team` | `String` | no |  | Three-letter code of the home team, e.g., TBL |
| 9 | `home_team_id` | `Int64` | no |  | NHL ID of the home team, e.g., 14 |
| 10 | `home_score` | `Int64` | yes |  | Goals scored by the home team, null for a game that has not started, e.g., 5 |
| 11 | `away_team` | `String` | no |  | Three-letter code of the away team, e.g., NSH |
| 12 | `away_team_id` | `Int64` | no |  | NHL ID of the away team, e.g., 18 |
| 13 | `away_score` | `Int64` | yes |  | Goals scored by the away team, null for a game that has not started, e.g., 3 |
| 14 | `venue` | `String` | no |  | Name of the venue, in capitals, e.g., AMALIE ARENA |
| 15 | `venue_timezone` | `String` | no |  | Time zone of the venue, e.g., US/Eastern |
| 16 | `neutral_site` | `Int64` | no |  | Whether the game is played at a neutral site, e.g., 0 |
| 17 | `game_date_dt_local` | `Datetime(time_unit='us', time_zone=None)` | no |  | Start of the game as a timezone-naive datetime in the venue's time zone, which venue_timezone names, e.g., 2023-10-10 17:30:00 |
| 18 | `game_date_dt_utc` | `Datetime(time_unit='us', time_zone='UTC')` | no |  | Start of the game as a datetime in UTC, e.g., 2023-10-10 21:30:00+00:00 |
| 19 | `tv_broadcasts` | `List(Struct({'id': Int64, 'market': String, 'countryCode': String, 'network': String, 'sequenceNumber': Int64}))` | no |  | Broadcasts of the game as the NHL API lists them, one struct per broadcast, e.g., [{'id': 309, 'market': 'N', 'countryCode': 'US', 'network': 'ESPN', 'sequenceNumber': 10}] |
| 20 | `home_logo` | `String` | yes |  | URL of the home team's logo, null when the NHL API gives none, e.g., https://assets.nhle.com/logos/nhl/svg/TBL_light.svg |
| 21 | `home_logo_dark` | `String` | yes |  | URL of the dark version of the home team's logo, null when the NHL API gives none, e.g., https://assets.nhle.com/logos/nhl/svg/TBL_dark.svg |
| 22 | `away_logo` | `String` | yes |  | URL of the away team's logo, null when the NHL API gives none, e.g., https://assets.nhle.com/logos/nhl/svg/NSH_light.svg |
| 23 | `away_logo_dark` | `String` | yes |  | URL of the dark version of the away team's logo, null when the NHL API gives none, e.g., https://assets.nhle.com/logos/nhl/svg/NSH_dark.svg |
