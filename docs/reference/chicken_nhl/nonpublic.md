---

icon: material/download

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
            - rosters
            - changes
            - shifts
            - api_events
            - api_rosters
            - html_events
            - html_rosters
            - add_games

##::: chickenstats.chicken_nhl.scrape.Game
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

##::: chickenstats.chicken_nhl.scrape.Season
    handler: python
    options:
        members:
            - schedule
            - standings
