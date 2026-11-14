---
icon: material/table
description: "Columns, dtypes and nullability of play_by_play_ext in chickenstats.chicken_nhl"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **chicken_nhl: play_by_play_ext**

Returned by `Scraper.play_by_play_ext`, `build_play_by_play_ext`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `id` | `Int64` | no |  | Unique play identifier — game_id and event_idx concatenated, e.g., 20190206840667 |
| 2 | `game_id` | `Int64` | no |  | Unique game ID assigned by the NHL, e.g., 2019020684 |
| 3 | `event_idx` | `Int64` | no |  | Index ID for event, e.g., 667 |
| 4 | `event_on_1` | `String` | yes |  | Player name |
| 5 | `event_on_1_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 6 | `event_on_1_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 7 | `event_on_1_pos` | `String` | yes |  | Player position |
| 8 | `event_on_2` | `String` | yes |  | Player name |
| 9 | `event_on_2_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 10 | `event_on_2_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 11 | `event_on_2_pos` | `String` | yes |  | Player position |
| 12 | `event_on_3` | `String` | yes |  | Player name |
| 13 | `event_on_3_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 14 | `event_on_3_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 15 | `event_on_3_pos` | `String` | yes |  | Player position |
| 16 | `event_on_4` | `String` | yes |  | Player name |
| 17 | `event_on_4_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 18 | `event_on_4_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 19 | `event_on_4_pos` | `String` | yes |  | Player position |
| 20 | `event_on_5` | `String` | yes |  | Player name |
| 21 | `event_on_5_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 22 | `event_on_5_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 23 | `event_on_5_pos` | `String` | yes |  | Player position |
| 24 | `event_on_6` | `String` | yes |  | Player name |
| 25 | `event_on_6_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 26 | `event_on_6_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 27 | `event_on_6_pos` | `String` | yes |  | Player position |
| 28 | `event_on_7` | `String` | yes |  | Player name |
| 29 | `event_on_7_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 30 | `event_on_7_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 31 | `event_on_7_pos` | `String` | yes |  | Player position |
| 32 | `opp_on_1` | `String` | yes |  | Player name |
| 33 | `opp_on_1_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 34 | `opp_on_1_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 35 | `opp_on_1_pos` | `String` | yes |  | Player position |
| 36 | `opp_on_2` | `String` | yes |  | Player name |
| 37 | `opp_on_2_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 38 | `opp_on_2_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 39 | `opp_on_2_pos` | `String` | yes |  | Player position |
| 40 | `opp_on_3` | `String` | yes |  | Player name |
| 41 | `opp_on_3_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 42 | `opp_on_3_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 43 | `opp_on_3_pos` | `String` | yes |  | Player position |
| 44 | `opp_on_4` | `String` | yes |  | Player name |
| 45 | `opp_on_4_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 46 | `opp_on_4_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 47 | `opp_on_4_pos` | `String` | yes |  | Player position |
| 48 | `opp_on_5` | `String` | yes |  | Player name |
| 49 | `opp_on_5_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 50 | `opp_on_5_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 51 | `opp_on_5_pos` | `String` | yes |  | Player position |
| 52 | `opp_on_6` | `String` | yes |  | Player name |
| 53 | `opp_on_6_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 54 | `opp_on_6_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 55 | `opp_on_6_pos` | `String` | yes |  | Player position |
| 56 | `opp_on_7` | `String` | yes |  | Player name |
| 57 | `opp_on_7_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 58 | `opp_on_7_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 59 | `opp_on_7_pos` | `String` | yes |  | Player position |
| 60 | `change_on_1` | `String` | yes |  | Player name |
| 61 | `change_on_1_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 62 | `change_on_1_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 63 | `change_on_1_pos` | `String` | yes |  | Player position |
| 64 | `change_on_2` | `String` | yes |  | Player name |
| 65 | `change_on_2_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 66 | `change_on_2_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 67 | `change_on_2_pos` | `String` | yes |  | Player position |
| 68 | `change_on_3` | `String` | yes |  | Player name |
| 69 | `change_on_3_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 70 | `change_on_3_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 71 | `change_on_3_pos` | `String` | yes |  | Player position |
| 72 | `change_on_4` | `String` | yes |  | Player name |
| 73 | `change_on_4_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 74 | `change_on_4_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 75 | `change_on_4_pos` | `String` | yes |  | Player position |
| 76 | `change_on_5` | `String` | yes |  | Player name |
| 77 | `change_on_5_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 78 | `change_on_5_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 79 | `change_on_5_pos` | `String` | yes |  | Player position |
| 80 | `change_on_6` | `String` | yes |  | Player name |
| 81 | `change_on_6_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 82 | `change_on_6_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 83 | `change_on_6_pos` | `String` | yes |  | Player position |
| 84 | `change_on_7` | `String` | yes |  | Player name |
| 85 | `change_on_7_eh_id` | `String` | yes |  | ID used for matching with Evolving Hockey data |
| 86 | `change_on_7_api_id` | `String` | yes |  | ID used for matching NHL API data |
| 87 | `change_on_7_pos` | `String` | yes |  | Player position |
