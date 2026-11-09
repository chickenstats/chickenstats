---
icon: material/download
description: "Reference materials and information for chickenstats.chicken_nhl.scrape"
---

# :material-download: **chicken_nhl.scrape**

Reference materials for `chickenstats.chicken_nhl.scrape`. `Scraper`, `Season`, and `Game` 
account for most of the functionality for `chickenstats.chicken_nhl`.

For more detailed walk-throughs or examples, please consult the **[:material-school: User Guide](../../guide/index.md)**

##::: chickenstats.chicken_nhl.scraper.Scraper
    handler: python
    options:
        show_bases: false
        members:
            - play_by_play
            - stats
            - prep_stats
            - lines
            - prep_lines
            - team_stats
            - prep_team_stats
            - stints
            - prep_stints
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
            - refresh
            - save
            - load
            - failed_games
            - failure_reasons
            - not_started_games
            - game_states
            - provisional_games
        group_by_category: false

##::: chickenstats.chicken_nhl.game.Game
    handler: python
    options:
        show_bases: false
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

##::: chickenstats.chicken_nhl.season.Season
    handler: python
    options:
        members:
            - schedule
            - standings

##::: chickenstats.chicken_nhl.season.multi_season_schedule
    handler: python

##::: chickenstats.chicken_nhl.season.add_schedule_context
    handler: python

##::: chickenstats.chicken_nhl.team.Team
    handler: python
    options:
        members:
            - logo

##::: chickenstats.chicken_nhl.player.Player
    handler: python
    options:
        members:
            - player_info
            - player_name
            - first_name
            - last_name
            - is_active
            - position_code
            - shoots_catches
            - height_in_inches
            - weight_in_pounds
            - birth_date
            - current_team
            - current_team_id
            - current_team_name
            - current_team_full_name
            - current_team_full_name_fr
            - active_seasons
            - playoff_seasons
            - prefetch

##::: chickenstats.chicken_nhl.player.search_players
    handler: python

##::: chickenstats.chicken_nhl.player.player_bios
    handler: python
