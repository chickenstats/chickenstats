---

icon: material/wrench

---

# :material-wrench: **Contribute**

See non-public methods and properties for easier contribution to `chickenstats.chicken_nhl` 

For info on actual usage, please consult the **[:material-school: User Guide](../guide/guide.md)**

##::: chickenstats.chicken_nhl.Scraper
    handler: python
    options:
        members:
            - _scrape

##::: chickenstats.chicken_nhl.Game
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

##::: chickenstats.chicken_nhl.Season
    handler: python
    options:
        members:
            - _scrape_schedule
            - _munge_schedule
            - _finalize_schedule
            - _scrape_standings
            - _munge_standings
            - _finalize_standings