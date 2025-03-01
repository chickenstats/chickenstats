---
icon: material/hockey-sticks
description: "Guide to chickenstats.chicken_nhl"
---

# :material-hockey-sticks: **chicken_nhl**

Here is where you can find basic information about using the `chicken_nhl` module.

For more in-depth materials, including source code, please consult the **[:material-bookshelf: Reference](../../reference/reference.md)**

## :fontawesome-solid-user-large: **Basic usage**

### Import module

`chicken_nhl` scrapes data from various official NHL endpoints, combining them into a usable play-by-play
dataframe. The module and the most relevant classes can be imported using the below snippet:

```py
from chickenstats.chicken_nhl import Season, Scraper
```

### `Season` and Game IDs
  
Each NHL game has a 10-digit game ID, with the first four digits indicating the season (e.g., 2024 for 2024-25 season),
the next four digits indicating the "session," or stage during which the game was played (e.g., 02 for the regular season,
03 for the post-season), and the last four digits indicating the game number (e.g., 0001 for the first game of the season).(1)
{ .annotate }

1. This convention changes slightly in the playoffs. Game IDs are 10-digits, but the last four digits indicate the round,
series, and game number (e.g., 0127 is the seventh game in the second series of the first round of the playoffs)

These game IDs can be readily accessed via the `schedule` method of `Season` class. The below snippet scrapes the
schedule for the 2023 playoffs, then stores the first ten game IDs in a list:

```py
season = Season(2023)
playoff_schedule = season.schedule(sessions="P")

game_ids = playoff_schedule.game_id.tolist()[:10]
```

??? info

    It's obviously possible to scrape the regular season, or even a subset of the schedule based on a single team, or
    list of teams, using the below snippets. The example throughout this guide is meant to be lightweight to avoid
    time spent waiting on data to download. 

    To scrape a single team, provide the standard three-letter team code to the team_schedule parameter:

    ```py
    nsh_schedule = season.schedule(team_schedule="NSH")
    ```

    To scrape more than one team, provide the preferred team codes as a list to the same parameter:

    ```py
    teams = ["NSH", "TBL", "DET", "TOR"]
    schedule = season.schedule(team_schedule=teams)
    ```

### `Scraper`

The `Scraper` object is used for scraping data from the API and HTML endpoints:

```py
scraper = Scraper(game_ids) # (1)! 

pbp = scraper.play_by_play # (2)!
```

1. The scraper object takes a list of game IDs
2. Access play-by-play data as a Pandas DataFrame

The `Scraper` object can also be used with individual game IDs:

```py
scraper = Scraper(game_ids[0]) # (1)!
pbp = scraper.play_by_play
```

1. The scraper object takes a single game ID

To see the first 5 goals of the 2023-24 playoffs

```py

pbp.loc[pbp.event == "GOAL"].head(5)

```

{{ read_csv("assets/tables/pbp_first5_goals.csv") }}

### Stats and aggregations

It's very simple to aggregate play-by-play data to the desired level and accounting for teammates or opposition on-ice.

First, start fresh with a new scraper:

```python
scraper = Scraper(game_ids[0])
play_by_play = scraper.play_by_play # (1)!
```

1. We won't strictly use the play-by-play data here, but it will get the scraping started

If you just want game-level individual stats, without accounting for teammates or opposition, just call the
`stats` attribute:

```python
stats = scraper.stats
```

To see the five most dangerous players offensively at 5v5 for the first game in the 2023-24 Stanley Cup Playoffs:

```python
stats.loc[stats.strength_state == "5v5"].sort_values(by="ixg", ascending=False).head(5)
```

{{ read_csv("assets/tables/stats_first5_ixg.csv") }}

If you want anything besides the default options, or if you change your desired aggregation / level of detail,
you can reset the data with the `prep_stats()` method:

```python
scraper.prep_stats(level="game", teammates=True, opposition=True) # (1)!
stats = scraper.stats # (2)!
stats.loc[stats.strength_state == "5v5"].sort_values(by="ixg", ascending=False).head(5)
```

1. Now the individual and on-ice stats are aggregated and account for the teammates and opponents on the ice
2. You can access the data with the `stats` attribute

{{ read_csv("assets/tables/stats_first5_ixg_teammates_opposition.csv") }}

Functionality is very similar for forward lines:

```python
scraper.prep_lines(position="f") # (1)!
forward_lines = scraper.lines

conditions = np.logical_and(forward_lines.toi >= 2,
                            forward_lines.strength_state == "5v5")
forward_lines.loc[conditions].sort_values(by="xgf_percent", ascending=False).head(5)
```

1. Not strictly necessary, the forwards are the default for line aggregations

{{ read_csv("assets/tables/forward_lines_first5_xgf_percent.csv") }}

And defensive pairings:

```python
scraper.prep_lines(position="d") # (1)!
defensive_pairings = scraper.lines # (2)!

conditions = np.logical_and(defensive_pairings.toi >= 2,
                            defensive_pairings.strength_state == "5v5")
defensive_pairings.loc[conditions].sort_values(by="xgf_percent", ascending=False).head(5)
```

1. Resets the saved line stats to be defensive lines, rather than forward lines
2. You can access the new line stats with the `lines` attribute

{{ read_csv("assets/tables/defensive_pairings_first5_xgf_percent.csv") }}

As well as team statistics:

```python
team_stats = scraper.team_stats # (1)!

team_stats.sort_values(by="toi", ascending=False).head(5).to_csv("team_stats_first5_toi.csv", index=False)
```

1. None of the above is necessary with the `team_stats`, if you're fine with the default parameters, which are
aggregated to the game level and account for strength state

{{ read_csv("assets/tables/team_stats_first5_toi.csv") }}

### Standings

You can also use a `Season` object to return that season's standings:

```python
from chickenstats.chicken_nhl import Season

season = Season(2023)
standings = season.standings
```

## :material-palette-advanced: **Advanced usage**

The `Scraper` object should be best for most of your scraping needs. However, there are additional 
properties available with the `Game` object that can be helpful.

### Other `Scraper` data

You can also access other data with the scraper object. The data will be scraped if it has not already been retrieved,
which saves time and is friendlier to data sources:

```py
from chickenstats.chicken_nhl import Season, Scraper

season = Season(2024)
schedule = season.schedule("NSH")
game_ids = schedule.game_id.tolist()[:5]

scraper = Scraper(game_ids)

pbp = scraper.rosters # (1)! 

html_rosters = scraper.html_rosters # (2)! 

html_events = scraper.html_events # (3)! 
```

1. Access roster data from both API and html endpoints
2. HTML rosters are retrieved quickly because they have already been scraped
3. HTML events are scraped, then combined with rosters already stored locally

### `Game` object

The `Game` object only works with a single game ID:

```python
game = Game(2023020001)
```

### Lists, not DataFrames

The `Game` object's familiar functions return lists, instead of Pandas DataFrames:

```python
game.play_by_play # (1)! 

game.play_by_play_df # (2)! 
```

1. Returns a list of play-by-play events
2. Returns a Pandas DataFrame of play-by-play events

### Pre-processing

Data can be inspected at various processing stages through the `Game` object's non-public properties:

```python
game._scrape_html_events # (1)! 

game._munge_html_events # (2)!
```

1. Get the raw HTML events and store the without processing
2. Process the raw HTML events and store them

A list of the non-public properties can be found in
**[:fontawesome-solid-user-group: Contribute](../../contribute/contribute.md)**



