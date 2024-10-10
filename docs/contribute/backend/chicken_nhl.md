---
icon: material/hockey-sticks
description: "Non-public methods for chickenstats.chicken_nhl"
---

# :material-hockey-sticks: **`chicken_nhl.scrape`**

Reference materials for the non-public elements of `chickenstats.chicken_nhl.scrape`. These methods and properties can
be used for debugging, or for implementing new features.

For more information about how to contribute, report bugs, or request new features, see
[:fontawesome-solid-user-group: Contribute](../contribute.md)

##::: chicken_nhl.scrape.Scraper
    handler: python
    options:
        members:
            - _scrape
            - _prep_xg
            - _prep_ind
            - _prep_oi
            - _prep_stats
            - _prep_lines
            - _prep_team_stats

##::: chicken_nhl.scrape.Game
    handler: python
    options:
        members:
            - _munge_api_events
            - _munge_api_rosters
            - _munge_changes
            - _scrape_html_events
            - _munge_html_events
            - _scrape_html_rosters
            - _munge_html_rosters
            - _combine_events
            - _munge_play_by_play
            - _combine_rosters
            - _scrape_shifts
            - _munge_shifts

##::: chicken_nhl.scrape.Season
    handler: python
    options:
        members:
            - _scrape_schedule
            - _munge_schedule
            - _finalize_schedule
            - _scrape_standings
            - _munge_standings
            - _finalize_standings
