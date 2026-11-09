---
icon: material/table
description: "Columns, dtypes and nullability of changes in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: changes**

Returned by `Scraper.changes`, `Game.changes_df`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `season` | `Int64` | no |  | Season as 8-digit number, e.g., 20192020 for 2019-20 season |
| 2 | `session` | `String` | no |  | Whether game is regular season, playoffs, or pre-season, e.g., R |
| 3 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 4 | `cs_version` | `String` | yes |  | Version of chickenstats that produced the row, e.g., 1.9.0 |
| 5 | `event_team` | `String` | no |  | Team that performed the change, e.g., NSH |
| 6 | `event` | `String` | no |  | Type of event, e.g., CHANGE |
| 7 | `event_type` | `String` | no |  | Type of change, e.g., AWAY CHANGE |
| 8 | `description` | `String` | no |  | Description of the change, e.g., PLAYERS ON: MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE / PLAYERS OFF: YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN |
| 9 | `period` | `Int64` | no |  | Period number of the event, e.g., 3 |
| 10 | `period_seconds` | `Int64` | no | seconds | Time elapsed in the period, in seconds, e.g., 1178 |
| 11 | `game_seconds` | `Int64` | no | seconds | Time elapsed in the game, in seconds, e.g., 3578 |
| 12 | `change_on_count` | `Int64` | no |  | Number of players on, e.g., 4 |
| 13 | `change_off_count` | `Int64` | no |  | Number of players off, e.g., 4 |
| 14 | `change_on` | `String` | no |  | Names of players on, e.g., MATTIAS EKHOLM, CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE |
| 15 | `change_on_jersey` | `String` | no |  | Jerseys for the players on, e.g., NSH14, NSH19, NSH64, NSH95 |
| 16 | `change_on_eh_id` | `String` | no |  | Evolving Hockey IDs of the players on, e.g., MATTIAS.EKHOLM, CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE |
| 17 | `change_on_api_id` | `String` | no |  | NHL API IDs of the players on, e.g., 8475166, 8477293, 8475798, 8477492 |
| 18 | `change_on_positions` | `String` | no |  | Positions of the players on, e.g., D, C, C, C |
| 19 | `change_off` | `String` | no |  | Names of players off, e.g., YANNICK WEBER, FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN |
| 20 | `change_off_jersey` | `String` | no |  | Jerseys for the players off, e.g., NSH7, NSH9, NSH33, NSH92 |
| 21 | `change_off_eh_id` | `String` | no |  | Evolving Hockey IDs of the players off, e.g., YANNICK.WEBER, FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN |
| 22 | `change_off_api_id` | `String` | no |  | NHL API IDs of the players off, e.g., 8470621, 8476887, 8478042, 8474679 |
| 23 | `change_off_positions` | `String` | no |  | Positions of the players off, e.g., D, L, L, C |
| 24 | `change_on_forwards_count` | `Int64` | no |  | Number of forwards on, e.g., 3 |
| 25 | `change_off_forwards_count` | `Int64` | no |  | Number of forwards off, e.g., 3 |
| 26 | `change_on_forwards` | `String` | no |  | Names of forwards on, e.g., CALLE JARNKROK, MIKAEL GRANLUND, MATT DUCHENE |
| 27 | `change_on_forwards_jersey` | `String` | no |  | Jerseys for the forwards on, e.g., NSH19, NSH64, NSH95 |
| 28 | `change_on_forwards_eh_id` | `String` | no |  | Evolving Hockey IDs of the forwards on, e.g., CALLE.JARNKROK, MIKAEL.GRANLUND, MATT.DUCHENE |
| 29 | `change_on_forwards_api_id` | `String` | no |  | NHL API IDs of the forwards on, e.g., 8477293, 8475798, 8477492 |
| 30 | `change_off_forwards` | `String` | no |  | Names of forwards off, e.g., FILIP FORSBERG, VIKTOR ARVIDSSON, RYAN JOHANSEN |
| 31 | `change_off_forwards_jersey` | `String` | no |  | Jerseys for the forwards off, e.g., NSH9, NSH33, NSH92 |
| 32 | `change_off_forwards_eh_id` | `String` | no |  | Evolving Hockey IDs of the forwards off, e.g., FILIP.FORSBERG, VIKTOR.ARVIDSSON, RYAN.JOHANSEN |
| 33 | `change_off_forwards_api_id` | `String` | no |  | NHL API IDs of the forwards off, e.g., 8476887, 8478042, 8474679 |
| 34 | `change_on_defense_count` | `Int64` | no |  | Number of defense on, e.g., 1 |
| 35 | `change_off_defense_count` | `Int64` | no |  | Number of defense off, e.g., 1 |
| 36 | `change_on_defense` | `String` | no |  | Names of defense on, e.g., MATTIAS EKHOLM |
| 37 | `change_on_defense_jersey` | `String` | no |  | Jerseys for the defense on, e.g., NSH14 |
| 38 | `change_on_defense_eh_id` | `String` | no |  | Evolving Hockey IDs of the defense on, e.g., MATTIAS.EKHOLM |
| 39 | `change_on_defense_api_id` | `String` | no |  | NHL API IDs of the defense on, e.g., 8475166 |
| 40 | `change_off_defense` | `String` | no |  | Names of defense off, e.g., YANNICK WEBER |
| 41 | `change_off_defense_jersey` | `String` | no |  | Jerseys for the defense off, e.g., NSH7 |
| 42 | `change_off_defense_eh_id` | `String` | no |  | Evolving Hockey IDs of the defense off, e.g., YANNICK.WEBER |
| 43 | `change_off_defense_api_id` | `String` | no |  | NHL API IDs of the defense off, e.g., 8470621 |
| 44 | `change_on_goalie_count` | `Int64` | no |  | Number of goalies on, e.g., 0 |
| 45 | `change_off_goalie_count` | `Int64` | no |  | Number of goalies off, e.g., 0 |
| 46 | `change_on_goalie` | `String` | no |  | Name of goalie on, e.g., None |
| 47 | `change_on_goalie_jersey` | `String` | no |  | Jersey for the goalie on, e.g., None |
| 48 | `change_on_goalie_eh_id` | `String` | no |  | Evolving Hockey ID of the goalie on, e.g., None |
| 49 | `change_on_goalie_api_id` | `String` | no |  | NHL API ID of the goalie on, e.g., None |
| 50 | `change_off_goalie` | `String` | no |  | Name of goalie off, e.g., None |
| 51 | `change_off_goalie_jersey` | `String` | no |  | Jersey for the goalie off, e.g., None |
| 52 | `change_off_goalie_eh_id` | `String` | no |  | Evolving Hockey ID of the goalie off, e.g., None |
| 53 | `change_off_goalie_api_id` | `String` | no |  | NHL API ID of the goalie off, e.g., None |
| 54 | `is_home` | `Int64` | no |  | Whether change team is home, e.g., 0 |
| 55 | `is_away` | `Int64` | no |  | Whether change team is away, e.g., 1 |
| 56 | `team_venue` | `String` | no |  | Whether team is home or away, e.g., AWAY |
