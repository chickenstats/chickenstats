---
icon: material/table
description: "Columns, dtypes and nullability of html_events in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: html_events**

Returned by `Scraper.html_events`, `Game.html_events_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 4 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 5 | `event_idx` | `Int64` | no |  | Index ID for event, e.g., 331 |
| 6 | `period` | `Int64` | no |  | Period number of the event, e.g., 3 |
| 7 | `period_time` | `String` | no | MM:SS | Time elapsed in the period, e.g., 19:38 |
| 8 | `period_seconds` | `Int64` | no | seconds | Time elapsed in the period, in seconds, e.g., 1178 |
| 9 | `game_seconds` | `Int64` | no | seconds | Time elapsed in the game, in seconds, e.g., 3578 |
| 10 | `event_team` | `String` | yes |  | Team that performed the action for the event, None for an event of neither team, a league challenge, a faceoff with no winner or a row whose description names no team, e.g., NSH |
| 11 | `event` | `String` | no |  | Type of event that occurred, e.g., GOAL |
| 12 | `description` | `String` | yes |  | Description of the event, e.g., NSH #35 RINNE(1), WRIST, DEF. ZONE, 185 FT. |
| 13 | `player_1` | `String` | yes |  | Player that performed the action, None for a player on neither roster, e.g., PEKKA RINNE |
| 14 | `player_1_eh_id` | `String` | yes |  | Evolving Hockey ID for player_1, None for a player on neither roster, e.g., PEKKA.RINNE |
| 15 | `player_1_position` | `String` | yes |  | Position player_1 plays, e.g., G |
| 16 | `player_2` | `String` | yes |  | Player that performed the action, None for a player on neither roster, e.g., None |
| 17 | `player_2_eh_id` | `String` | yes |  | Evolving Hockey ID for player_2, None for a player on neither roster, e.g., None |
| 18 | `player_2_position` | `String` | yes |  | Position player_2 plays, e.g., None |
| 19 | `player_3` | `String` | yes |  | Player that performed the action, None for a player on neither roster, e.g., None |
| 20 | `player_3_eh_id` | `String` | yes |  | Evolving Hockey ID for player_3, None for a player on neither roster, e.g., None |
| 21 | `player_3_position` | `String` | yes |  | Position player_3 plays, e.g., None |
| 22 | `zone` | `String` | yes |  | Zone where the event occurred, relative to the event team, e.g., DEF |
| 23 | `shot_type` | `String` | yes |  | Type of shot taken, if event is a shot, e.g., WRIST |
| 24 | `pbp_distance` | `Int64` | yes | feet | Distance of event from goal from description, e.g., 185 |
| 25 | `penalty_length` | `Int64` | yes | minutes | Duration of the penalty, e.g., None |
| 26 | `penalty` | `String` | yes |  | Reason for the penalty, e.g., None |
| 27 | `strength` | `String` | yes |  | Code to indicate strength state, e.g., EV |
| 28 | `away_skaters` | `String` | yes |  | Away skaters on-ice, e.g., 13C, 19C, 64C, 14D, 59D, 35G |
| 29 | `home_skaters` | `String` | yes |  | Home skaters on-ice, e.g., 19C, 77C, 12R, 88R, 2D, 56D |
| 30 | `version` | `Int64` | no |  | Increases with simultaneous events, used for combining events in the scraper, e.g., 1 |
