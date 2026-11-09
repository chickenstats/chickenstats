---
icon: material/table
description: "Columns, dtypes and nullability of gar in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: gar**

Returned by `evolving_hockey.prep_gar`. See [Output schemas](index.md) for what these columns promise.

| # | Column | Dtype | Nullable | Unit |
|--:|--------|-------|----------|------|
| 1 | `player` | `String` | no |  |
| 2 | `eh_id` | `String` | no |  |
| 3 | `api_id` | `Int64` | yes |  |
| 4 | `season` | `Int64` | no |  |
| 5 | `team` | `String` | no |  |
| 6 | `position` | `String` | no |  |
| 7 | `shoots` | `String` | yes |  |
| 8 | `catches` | `String` | yes |  |
| 9 | `birthday` | `Date` | yes |  |
| 10 | `age` | `Int64` | yes |  |
| 11 | `draft_yr` | `Int64` | yes |  |
| 12 | `draft_rd` | `String` | yes |  |
| 13 | `draft_ov` | `String` | yes |  |
| 14 | `gp` | `Int64` | yes |  |
| 15 | `toi_all` | `Float64` | yes |  |
| 16 | `toi_ev` | `Float64` | yes |  |
| 17 | `toi_pp` | `Float64` | yes |  |
| 18 | `toi_sh` | `Float64` | yes |  |
| 19 | `fa_ev` | `Int64` | yes |  |
| 20 | `fa_sh` | `Int64` | yes |  |
| 21 | `evo_gar` | `Float64` | yes |  |
| 22 | `evd_gar` | `Float64` | yes |  |
| 23 | `ppo_gar` | `Float64` | yes |  |
| 24 | `shd_gar` | `Float64` | yes |  |
| 25 | `take_gar` | `Float64` | yes |  |
| 26 | `draw_gar` | `Float64` | yes |  |
| 27 | `off_gar` | `Float64` | yes |  |
| 28 | `def_gar` | `Float64` | yes |  |
| 29 | `pens_gar` | `Float64` | yes |  |
| 30 | `gar` | `Float64` | yes |  |
| 31 | `war` | `Float64` | yes |  |
| 32 | `spar` | `Float64` | yes |  |
