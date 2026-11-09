---
icon: material/table
description: "Columns, dtypes and nullability of xgar in chickenstats.evolving_hockey"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table: **evolving_hockey: xgar**

Returned by `evolving_hockey.prep_xgar`. See [Output schemas](index.md) for what these columns promise.

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
| 16 | `xevo_gar` | `Float64` | yes |  |
| 17 | `xevd_gar` | `Float64` | yes |  |
| 18 | `xppo_gar` | `Float64` | yes |  |
| 19 | `xshd_gar` | `Float64` | yes |  |
| 20 | `take_gar` | `Float64` | yes |  |
| 21 | `draw_gar` | `Float64` | yes |  |
| 22 | `xoff_gar` | `Float64` | yes |  |
| 23 | `xdef_gar` | `Float64` | yes |  |
| 24 | `pens_gar` | `Float64` | yes |  |
| 25 | `xgar` | `Float64` | yes |  |
| 26 | `xwar` | `Float64` | yes |  |
| 27 | `xspar` | `Float64` | yes |  |
