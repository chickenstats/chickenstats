---

icon: material/download

---

# :material-download: **chicken_nhl.scrape**

Reference materials for `chickenstats.chicken_nhl.scrape`. `Scraper`, `Season`, and `Game` 
account for most of the module's functionality.

For more detailed walk-throughs or examples, please consult the **[:material-school: User Guide](../../guide/guide.md)**

##::: chickenstats.chicken_nhl.Scraper
    handler: python
    options:
        members:
            - play_by_play
            - rosters
            - changes
            - shifts
            - api_events
            - api_rosters
            - html_events
            - html_rosters
            - add_games

##::: chickenstats.chicken_nhl.Game
    handler: python
    options:
        members:
            - play_by_play
            - rosters
            - changes
            - shifts
            - api_events
            - api_rosters
            - html_events
            - html_rosters

##::: chickenstats.chicken_nhl.Season
    handler: python
    options:
        members:
            - schedule
            - standings
