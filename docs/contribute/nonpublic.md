---

icon: material/download

---

# :material-download: **chicken_nhl.scrape**

Reference materials for `chickenstats.chicken_nhl.scrape`. `Scraper`, `Season`, and `Game` 
account for most of the functionality for `chickenstats.chicken_nhl`.

For more detailed walk-throughs or examples, please consult the **[:material-school: User Guide](../guide/guide.md)**

##::: chicken_nhl.scrape.Scraper
    handler: python
    options:
        members:
            - _scrape

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
