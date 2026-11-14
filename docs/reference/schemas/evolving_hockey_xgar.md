---
icon: material/table
description: "Columns, dtypes and nullability of xgar in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: xgar**

Returned by `evolving_hockey.prep_xgar`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit | Description |
|--:|--------|-------|----------|------|-------------|
| 1 | `player` | `String` | no |  | Player name, written as chicken_nhl writes it, e.g., ROMAN JOSI |
| 2 | `eh_id` | `String` | no |  | Evolving Hockey ID of the player, e.g., ROMAN.JOSI |
| 3 | `api_id` | `Int64` | yes |  | NHL API ID of the player, null when the export gives none, e.g., 8474600 |
| 4 | `season` | `Int64` | no |  | Season as 8-digit number, from the export's YY-YY season, e.g., 20232024 |
| 5 | `team` | `String` | no |  | Team the player played for, e.g., NSH |
| 6 | `position` | `String` | no |  | Position of the player, as the export gives it, e.g., D |
| 7 | `shoots` | `String` | yes |  | Hand the skater shoots with, null for a goalie, e.g., L |
| 8 | `catches` | `String` | yes |  | Hand the goalie catches with, null for a skater, e.g., None |
| 9 | `birthday` | `Date` | yes |  | Birthday of the player, null when the export gives none or not as a date, e.g., 2000-01-01 |
| 10 | `age` | `Int64` | yes | years | Age of the player, as the export gives it, e.g., 25 |
| 11 | `draft_yr` | `Int64` | yes |  | Year the player was drafted, null when the export gives none, e.g., None |
| 12 | `draft_rd` | `String` | yes |  | Round the player was drafted in, as the export gives it, e.g., None |
| 13 | `draft_ov` | `String` | yes |  | Overall pick the player was drafted with, as the export gives it, e.g., None |
| 14 | `gp` | `Int64` | yes |  | Games played, e.g., 2 |
| 15 | `toi_all` | `Float64` | yes | minutes | Time on ice in all situations, in minutes, null for a goalie, e.g., 48.9 |
| 16 | `xevo_gar` | `Float64` | yes |  | Expected even-strength offense goals above replacement, e.g., 0.5 |
| 17 | `xevd_gar` | `Float64` | yes |  | Expected even-strength defense goals above replacement, e.g., 0.5 |
| 18 | `xppo_gar` | `Float64` | yes |  | Expected power-play offense goals above replacement, e.g., 0.5 |
| 19 | `xshd_gar` | `Float64` | yes |  | Expected shorthanded defense goals above replacement, e.g., 0.5 |
| 20 | `take_gar` | `Float64` | yes |  | Goals above replacement from penalties taken, e.g., 0.5 |
| 21 | `draw_gar` | `Float64` | yes |  | Goals above replacement from penalties drawn, e.g., 0.5 |
| 22 | `xoff_gar` | `Float64` | yes |  | Expected offense goals above replacement, e.g., 0.5 |
| 23 | `xdef_gar` | `Float64` | yes |  | Expected defense goals above replacement, e.g., 0.5 |
| 24 | `pens_gar` | `Float64` | yes |  | Penalty goals above replacement, e.g., 0.5 |
| 25 | `xgar` | `Float64` | yes |  | Total expected goals above replacement, e.g., 0.5 |
| 26 | `xwar` | `Float64` | yes |  | Expected wins above replacement, e.g., 0.5 |
| 27 | `xspar` | `Float64` | yes |  | Expected standings points above replacement, e.g., 0.5 |
