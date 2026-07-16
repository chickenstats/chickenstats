---
icon: material/hockey-sticks
description: "Non-public methods for chickenstats.chicken_nhl"
---

# :material-hockey-sticks: **`chicken_nhl.scrape`**

Reference materials for the non-public elements of `chickenstats.chicken_nhl.scrape`. These methods and properties can
be used for debugging, or for implementing new features.

For more information about how to contribute, report bugs, or request new features, see
[:fontawesome-solid-user-group: Contribute](../index.md)

##::: chicken_nhl.scraper.Scraper
    handler: python
    options:
        members:
            - _scrape
            - _prep_ind
            - _prep_oi
            - _prep_stats
            - _prep_lines
            - _prep_team_stats

##::: chicken_nhl.game.Game
    handler: python
    options:
        members:
            - _fetch_api_data
            - _munge_single_api_event
            - _munge_api_player
            - _fetch_html_events
            - _munge_html_events
            - _fetch_html_rosters
            - _munge_single_html_player
            - _fetch_shifts
            - _munge_shifts
            - _munge_changes
            - _combine_rosters
            - _merge_pbp_events
            - _track_pbp_state
            - _calculate_pbp_xg
            - _pbp_pipeline

##::: chicken_nhl.season.Season
    handler: python
    options:
        members:
            - _scrape_schedule
            - _munge_schedule
            - _scrape_standings
            - _munge_standings
