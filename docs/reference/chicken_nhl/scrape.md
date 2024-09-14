---
icon: material/download
description: "Reference materials and information for chickenstats.chicken_nhl.scrape"
---

# :material-download: **chicken_nhl.scrape**

Reference materials for `chickenstats.chicken_nhl.scrape`. `Scraper`, `Season`, and `Game` 
account for most of the functionality for `chickenstats.chicken_nhl`.

For more detailed walk-throughs or examples, please consult the **[:material-school: User Guide](../../guide/guide.md)**

##::: chicken_nhl.scrape.Scraper
    handler: python
    options:
        members:
            - play_by_play
            - stats
            - prep_stats
            - lines
            - prep_lines
            - team_stats
            - prep_team_stats
            - rosters
            - changes
            - shifts
            - api_events
            - api_rosters
            - html_events
            - html_rosters
            - ind_stats
            - oi_stats
            - add_games
        group_by_category: false

##::: chicken_nhl.scrape.Game
    handler: python
    options:
        members:
            - play_by_play
            - play_by_play_ext
            - rosters
            - changes
            - shifts
            - api_events
            - api_rosters
            - html_events
            - html_rosters

##::: chicken_nhl.scrape.Season
    handler: python
    options:
        members:
            - schedule
            - standings
