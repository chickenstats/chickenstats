---
icon: material/download-box
description: "Get started with chickenstats"
---

# :material-download-box: **Getting started**

Instructions for installing `chickenstats` & basic usage, plus a few simple examples. 
For more detailed tutorials, please consult the respective guides. 

<div class="grid cards" markdown>

[:material-hockey-sticks:{ .lg .middle } __`chicken_nhl`__](../chicken_nhl/chicken_nhl.md)
{ .card }

[:material-hockey-puck:{ .lg .middle } __`evolving_hockey`__](../evolving_hockey/evolving_hockey.md)
{ .card }

</div>

## :material-book: **Requirements**

`chickenstats` requires Python 3.10 or later, preferably the most recent version (3.12).

## :material-download: **Installation**

`chickenstats` can be installed via PyPi:

```shell
pip install chickenstats
```

You can ensure the installation was successful by checking that you have the latest version (1.8.0):

```shell
pip show chickenstats
```

## :fontawesome-solid-user-large: **Basic usage**

=== "**`chicken_nhl`**"

    Once installed in your preferred virtual environment, you can immediately begin using `chickenstats.chicken_nhl`
    in your preferred IDE. First, import the package and the relevant classes:
    
    ```py
    from chickenstats.chicken_nhl import Season, Scraper
    ```
    
    Then, you're off. The `Season` object with the `schedule` property will return NHL game IDs,
    which can be used with the `Scraper` object to retrieve official NHL data and return a play-by-play dataframe. 
    `chicken_nhl` will return approximately one game every 3-4 seconds, 
    with no loss in performance when scraping hundreds (or thousands of games). After scraping, you can aggregate
    individual, line, or team stats, choosing whether to account for strength state, score state, or on-ice players.
    
    The following snippet will scrape the first 100 games of the 2023-24 season:
    
    ```py
    season = Season(2023)
    
    schedule = season.schedule() 
    
    game_ids = schedule.game_id.unique().tolist()[:100]
    
    scraper = Scraper(game_ids)
    
    pbp = scraper.play_by_play
    ```
    
    If you wanted scrape to only one team's schedule and game IDs:
    
    ```py
    season = Season(2023)
    
    nsh_schedule = season.schedule('NSH')
    
    game_ids = nsh_schedule.game_id.tolist()

    scraper = Scraper(game_ids)
    
    pbp = scraper.play_by_play

    ```

    Then, you can aggregate individual stats. Stats are aggregated to game level and account for strength state 
    by default:

    ```py

    stats = scraper.stats

    ```

    If you want to change the level of aggregation, or add teammats / opponents on-ice, use the `prep_stats` method:

    ```py
    scraper.prep_stats(level="season", teammates=True, opposition=True)
    
    stats = scraper.stats

    ```

    The same applies for line-level stats. For forward lines' game stats (default values):

    ```py

    lines = scraper.lines

    ```
    
    To change to defense and add opposition

    ```py

    scraper.prep_lines(position="D", level="game", opposition=True)

    lines = scraper.lines

    ```

    It's possible to aggregate team stats, with the same logic. Default values are game-level, 
    accounting for strength_state:

    ```py

    team_stats = scraper.team_stats

    ```

    To aggregate to season level, accounting for opposition team:

    ```py

    scraper.prep_team_stats(level="season", opposition=True)

    team_stats = scraper.team_stats

    ```

    The `standings` property for the `Season` object will return the latest NHL standings:
    
    ```py
    season = Season(2023)
    standings = season.standings
    ```
    
    For a more detailed walkthrough and additional examples,
    please consult the detailed guide
    **[:material-hockey-sticks: `chicken_nhl`](../chicken_nhl/chicken_nhl.md)**

=== "**`evolving_hockey`**"

    Once installed in your preferred virtual environment, you can immediately begin using `chickenstats.evolving_hockey`
    in your preferred IDE. First, import the package and the relevant functions:
    
    ```py
    from chickenstats.evolving_hockey import prep_pbp, prep_stats, prep_lines, prep_team
    ```
    
    The `evolving_hockey` functions require you to have a valid Evolving-Hockey subscription and access to the data 
    from the query portion of their site. 
    
    The first step is prepare a processed play-by-play dataframe:
    
    ```python
    shifts_raw = pd.read_csv('shifts_raw.csv')
    pbp_raw = pd.read_csv('pbp_raw.csv')
    
    pbp = prep_pbp(pbp_raw, shifts_raw)
    ```
    
    Once you have the processed play-by-play dataframe, you can begin aggregating. 
    
    For game-level individual and on-ice statistics, grouped by teammates:
    
    ```python
    stats = prep_stats(pbp, level = 'game', teammates = True)
    ```
    
    For period-level forward line stats, grouped by score state:
    
    ```python
    lines = prep_lines(pbp, positions = 'f', level = 'period', score_state = True)
    ```

    For game-level team stats:
    
    ```python
    teams = prep_team(pbp, level = "game")
    ```
    
    For a more detailed walkthrough and additional examples,
    please consult the **[:material-school: User Guide](../evolving_hockey/evolving_hockey.md)**

## :material-school: **Tutorials & examples**






