---
icon: material/table-cog
description: "The columns, dtypes and nullability of every frame chickenstats returns"
---

<!-- Written by scripts/schema_catalog.py --write. Change the schema, not this page. -->

# :material-table-cog: **Output schemas**

Each page lists a frame's columns in the order the frame returns them. A frame returns only the
columns its options ask for, and the rest keep their order. For example, `game_id` and `game_date`
appear only at game and period level, `session` is left out at season level, the lineup columns
appear only with `teammates=True` or `opposition=True`, and the `base_xg` and `context_xg`
columns appear only when play-by-play has them.

These pages are the contract for what each frame returns, with the pandas, pyarrow and narwhals
backends converting the dtypes shown here:

- Adding, removing, renaming or moving a column, or changing its dtype, nullability or unit, is a
  breaking change. It is listed under "Breaking changes" in the changelog for its release.
- A test compares every frame with a checked-in snapshot of these tables, so none of these changes
  can ship by accident.

| Frame | Returned by | Columns |
|-------|-------------|--------:|
| [chicken_nhl: play_by_play](chicken_nhl_play_by_play.md) | `Scraper.play_by_play`, `Game.play_by_play_df` | 202 |
| [chicken_nhl: play_by_play_ext](chicken_nhl_play_by_play_ext.md) | `Scraper.play_by_play_ext`, `build_play_by_play_ext` | 87 |
| [chicken_nhl: xg_fields](chicken_nhl_xg_fields.md) | `Scraper.xg_fields`, `Game.xg_fields_df` | 31 |
| [chicken_nhl: api_events](chicken_nhl_api_events.md) | `Scraper.api_events`, `Game.api_events_df` | 50 |
| [chicken_nhl: api_rosters](chicken_nhl_api_rosters.md) | `Scraper.api_rosters`, `Game.api_rosters_df` | 15 |
| [chicken_nhl: html_events](chicken_nhl_html_events.md) | `Scraper.html_events`, `Game.html_events_df` | 30 |
| [chicken_nhl: html_rosters](chicken_nhl_html_rosters.md) | `Scraper.html_rosters`, `Game.html_rosters_df` | 14 |
| [chicken_nhl: rosters](chicken_nhl_rosters.md) | `Scraper.rosters`, `Game.rosters_df` | 16 |
| [chicken_nhl: shifts](chicken_nhl_shifts.md) | `Scraper.shifts`, `Game.shifts_df` | 26 |
| [chicken_nhl: changes](chicken_nhl_changes.md) | `Scraper.changes`, `Game.changes_df` | 56 |
| [chicken_nhl: stats](chicken_nhl_stats.md) | `Scraper.stats`, `prep_stats` | 283 |
| [chicken_nhl: ind_stats](chicken_nhl_ind_stats.md) | `Scraper.ind_stats`, `prep_ind` | 81 |
| [chicken_nhl: oi_stats](chicken_nhl_oi_stats.md) | `Scraper.oi_stats`, `prep_oi` | 109 |
| [chicken_nhl: lines](chicken_nhl_lines.md) | `Scraper.lines`, `prep_lines` | 187 |
| [chicken_nhl: team_stats](chicken_nhl_team_stats.md) | `Scraper.team_stats`, `prep_team_stats` | 169 |
| [chicken_nhl: stints](chicken_nhl_stints.md) | `Scraper.stints`, `prep_stints` | 43 |
| [chicken_nhl: schedule](chicken_nhl_schedule.md) | `Season.schedule`, `multi_season_schedule` | 23 |
| [chicken_nhl: standings](chicken_nhl_standings.md) | `Season.standings` | 57 |
| [evolving_hockey: play-by-play](evolving_hockey_pbp.md) | `evolving_hockey.prep_pbp` | 156 |
| [evolving_hockey: stats](evolving_hockey_stats.md) | `evolving_hockey.prep_stats` | 276 |
| [evolving_hockey: ind_stats](evolving_hockey_ind_stats.md) | `evolving_hockey.prep_ind` | 74 |
| [evolving_hockey: oi_stats](evolving_hockey_oi_stats.md) | `evolving_hockey.prep_oi` | 102 |
| [evolving_hockey: lines](evolving_hockey_lines.md) | `evolving_hockey.prep_lines` | 181 |
| [evolving_hockey: team_stats](evolving_hockey_team_stats.md) | `evolving_hockey.prep_team_stats` | 169 |
| [evolving_hockey: gar](evolving_hockey_gar.md) | `evolving_hockey.prep_gar` | 32 |
| [evolving_hockey: xgar](evolving_hockey_xgar.md) | `evolving_hockey.prep_xgar` | 27 |
