---
icon: material/hockey-sticks
description: "Guide to chickenstats.chicken_nhl"
---

# :material-hockey-sticks: **chicken_nhl**

Here is where you can find basic information about using the `chicken_nhl` module.

For more in-depth materials, including source code, please consult the **[:material-bookshelf: Reference](../../reference/index.md)**

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
Nashville Predators' schedule for the 2024-25 season:

```py
season = Season(2024)
nsh_schedule = season.schedule("NSH")

condition = nsh_schedule.game_state == "OFF" # (1)!

game_ids = nsh_schedule.loc[condition].game_id.tolist()
```

1. We want to limit the games we're scraping to those that have already occurred, otherwise there's no data 
:fontawesome-solid-face-smile:

??? tip

    It's obviously possible to scrape only the regular season / playoffs, a combination of the two, 
    a list of teams, or even the 4 Nations Face-Off, using the below snippets. 

    The example throughout this guide is meant to be lightweight to avoid time spent waiting on data to download. 

    To scrape the playoffs, provide the letter "P" to the sessions parameter:

    ```py
    season = Season(2023)
    playoff_schedule = season.schedule(sessions="P")
    ```

    To scrape more than one team, provide the preferred team codes as a list to the same parameter:

    ```py
    teams = ["NSH", "TBL", "DET", "TOR"]
    schedule = season.schedule(team_schedule=teams)
    ```

    To scrape the 4 Nations Face-Off in the 2024-25 season:

    ```py
    season = Season(2024)
    fo_schedule = season.schedule(sessions="FO")
    ```

### `Scraper`

The `Scraper` object is used for scraping data from the API and HTML endpoints:

```py
scraper = Scraper(game_ids) # (1)! 

pbp = scraper.play_by_play # (2)!
```

1. The scraper object takes a list of game IDs
2. Access play-by-play data as a Pandas DataFrame

??? tip

    The `Scraper` object can also be used with individual game IDs:
    
    ```py
    scraper = Scraper(game_ids[0])
    pbp = scraper.play_by_play
    ```

To see the first 5 goals for the Predators' in the 2024-25 season:

```py
conditions = np.logical_and(pbp.event_team == "NSH", pbp.event == "GOAL")
pbp.loc[conditions].head(5)

```

{{ read_csv("assets/tables/chicken_nhl/guide/pbp_first5_goals.csv") }}

### Stats and aggregations

It's very simple to aggregate play-by-play data to the desired level and accounting for teammates or opposition on-ice.

First, start fresh with a new scraper:

```python
scraper = Scraper(game_ids)
play_by_play = scraper.play_by_play # (1)!
```

1. We won't strictly use the play-by-play data here, but it will get the scraping started

If you just want game-level individual stats, without accounting for teammates or opposition, just call the
`stats` attribute:

```python
stats = scraper.stats
```

To see the five "most dangerous" individual games at 5v5 for the Nashville Predators in the 2024-25 season:

```python
conditions = np.logical_and(stats.strength_state == "5v5",
                            stats.team == "NSH")
stats.loc[conditions].sort_values(by="ixg", ascending=False).head(5)
```

{{ read_csv("assets/tables/chicken_nhl/guide/stats_first5_ixg.csv") }}

If you want anything besides the default options, or if you change your desired aggregation / level of detail,
you can reset the data with the `prep_stats()` method:

```python
scraper.prep_stats(level="game", teammates=True, opposition=True) # (1)!
stats = scraper.stats # (2)!

conditions = np.logical_and(stats.strength_state == "5v5",
                            stats.team == "NSH")
stats.loc[conditions].sort_values(by="ixg", ascending=False).head(5)
```

1. Now the individual and on-ice stats are aggregated and account for the teammates and opponents on the ice
2. You can access the data with the `stats` attribute

{{ read_csv("assets/tables/chicken_nhl/guide/stats_first5_ixg_teammates_opposition.csv") }}

Functionality is very similar for forward lines:

```python
scraper.prep_lines(position="f") # (1)!
forward_lines = scraper.lines

conditions = np.logical_and.reduce([forward_lines.toi >= 2,
                                    forward_lines.strength_state == "5v5",
                                    forward_lines.team == "NSH"])
forward_lines.loc[conditions].sort_values(by="xgf_percent", ascending=False).head(5)
```

1. Not strictly necessary, the forwards are the default for line aggregations

{{ read_csv("assets/tables/chicken_nhl/guide/forward_lines_first5_xgf_percent.csv") }}

And defensive pairings:

```python
scraper.prep_lines(position="d") # (1)!
defensive_pairings = scraper.lines # (2)!

conditions = np.logical_and.reduce([defensive_pairings.toi >= 2,
                                    defensive_pairings.strength_state == "5v5",
                                    defensive_pairings.team == "NSH"])
defensive_pairings.loc[conditions].sort_values(by="xgf_percent", ascending=False).head(5)
```

1. Resets the saved line stats to be defensive lines, rather than forward lines
2. You can access the new line stats with the `lines` attribute

{{ read_csv("assets/tables/chicken_nhl/guide/defensive_pairings_first5_xgf_percent.csv") }}

As well as team statistics:

```python
team_stats = scraper.team_stats # (1)!

team_stats.sort_values(by="toi", ascending=False).head(5)
```

1. None of the above is necessary with the `team_stats`, if you're fine with the default parameters, which are
aggregated to the game level and account for strength state

{{ read_csv("assets/tables/chicken_nhl/guide/team_stats_first5_toi.csv") }}

### Standings

You can also use a `Season` object to return that season's standings:

```python
from chickenstats.chicken_nhl import Season

season = Season(2024)
standings = season.standings # (1)!

standings.head(5)
```

1. Standings data are returned for that moment in time - i.e., data will be updated automatically as games are played

{{ read_csv("assets/tables/chicken_nhl/guide/standings_first5.csv") }}

### Data persistence

The `Scraper` object will scrape any data that has not already been retrieved from the source - any data that has
been scraped since initialization is stored in the object. This saves time and is friendlier to the sources. 

The below snippet is a simple illustration. The changes dataframe is built using data from the shifts endpoint, (1) 
as well as the HTML and API rosters endpoints. After calling the changes property, the underlying data are available,
more or less instantaneously.
{ .annotate }

1.  Really the shifts *endpoints* - the home and visiting teams are scraped from separate URLs

```python
changes = scraper.changes # (1)!

rosters = scraper.rosters # (2)!
shifts = scraper.shifts 
```

1. This property scrapes shifts and rosters data, then stores the data for later retrieval
2. Later calls to the `rosters` or `shifts` properties returns the previously-scraped data stored 
by the `Scraper` object, instead of being re-scraped from the sources

The reverse is also true - previously-scraped data stored by the `Scraper` object is 
later used if required by other properties. Continuing the above example, the `HTML_events` 
property will leverage the rosters data previously scraped by the `changes` property:

```python
changes = scraper.changes

html_events = scraper.html_events # (1)!
```

1. Calling the `html_events` property after scraping rosters data will improve the processing speed because
the user has already scraped and processed a portion of the data

Users aren't expected to know which properties scrape which data sources. Optimized scraping and storage
is the default behavior.

The design provides significant user benefits, in addition to reducing unnecessary hits to data sources 
and improving processing and scraping speed. The cons of the increased memory usage are more than outweighed.

## :material-palette-advanced: **Advanced usage**

It's possible to access the various underlying data from the different endpoints using the `Scraper` object, including:

* Play-by-play events from API and HTML endpoints
* Rosters from API and HTML endpoints
* Shifts from the HTML endpoint
* Change events, built from the (HTML) shifts and (combined) rosters data

???+ note

    Each of the below code snippets assume you'll have initialized a `Scraper` object with a game ID, or list of game IDs:
    
    ```python
    
    from chickenstats.chicken_nhl import Season, Scraper
    
    season = Season(2024)
    nsh_schedule = season.schedule("NSH")
    
    condition = nsh_schedule.game_state == "OFF"
    game_ids = nsh_schedule.loc[condition].game_id.tolist()
    
    scraper = Scraper(game_ids)
    ```

=== "Play-by-play events"

    Play-by-play events from the API endpoint:
    
    ```python
    api_events = scraper.api_events
    
    conditions = np.logical_and(api_events.event == "GOAL",
                                api_events.event_team == "NSH")
    
    api_events.loc[conditions].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/api_events_first5_goals.csv") }}
    
    Play-by-play events from the HTML endpoint:
    
    ```python
    html_events = scraper.html_events
    
    conditions = np.logical_and(html_events.event == "GOAL",
                                html_events.event_team == "NSH")
    
    html_events.loc[conditions].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/html_events_first5_goals.csv") }}

=== "Rosters"

    Roster data from the API endpoint:
    
    ```python
    api_rosters = scraper.api_rosters
    
    condition = api_rosters.team == "NSH"
    api_rosters.loc[condition].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/api_rosters_first5.csv") }}

    Roster data from the HTML endpoint:
    
    ```python
    html_rosters = scraper.html_rosters
    
    condition = html_rosters.team == "NSH"
    html_rosters.loc[condition].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/html_rosters_first5.csv") }}
    
    Combined roster data:
    
    ```python
    rosters = scraper.rosters 
    
    condition = rosters.team == "NSH"
    rosters.loc[condition].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/rosters_first5.csv") }}

=== "Shifts"

    Shifts data from the HTML endpoint:
    
    ```python
    shifts = scraper.shifts
    
    condition = shifts.team == "NSH"
    shifts.loc[condition].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/shifts_first5.csv") }}

=== "Changes"

    Changes data built from the HTML shifts:
    
    ```python
    changes = scraper.changes
    
    condition = changes.event_team == "NSH"
    changes.loc[condition].head(5)
    ```
    
    {{ read_csv("assets/tables/chicken_nhl/guide/changes_first5.csv") }}

## :material-bug: **Debugging and raw data**

It's possible to access raw, pre-processed data from each data source, which can be helpful for debugging
or contributing to `chickenstats` design and development.

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
**[:fontawesome-solid-user-group: Contribute](../../contribute/index.md)**



