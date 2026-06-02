from chickenstats.chicken_nhl._scraper_core import _ScraperBasefrom examples.blog.nsh_competition.nsh_competition import play_by_playfrom chickenstats.chicken_nhl._scraper_core import _ScraperBasefrom examples.blog.nsh_competition.nsh_competition import play_by_playfrom chickenstats.chicken_nhl import Scraperfrom chickenstats.chicken_nhl._scraper_core import _ScraperBasefrom chickenstats.chicken_nhl._scraper_core import _ScraperBase---
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
import polars as pl # Polars is the default backend
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
season = Season(2025)
nsh_schedule = season.schedule("NSH")

condition = pl.col("game_state") == "OFF" # (1)!

game_ids = nsh_schedule.filter(condition)["game_id"].to_list()
```

1. We want to limit the games we're scraping to those that have already occurred, otherwise there's no data
:fontawesome-solid-face-smile:

??? tip

    It's obviously possible to scrape only the regular season / playoffs, a combination of the two,
    a list of teams, or even the 4 Nations Face-Off, using the below snippets.

    The example throughout this guide is meant to be lightweight to avoid time spent waiting on data to download.

    To scrape the playoffs, provide the letter "P" to the sessions parameter:

    ```py
    season = Season(2025)
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

To see the first 5 goals for the Nashville Predators in the 2025-26 season:

```py
conditions = (pl.col("event_team") == "NSH", pl.col("event") == "GOAL")
pbp.filter(conditions).head(5)

```

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

To see the five "most dangerous" individual games at 5v5 for the Nashville Predators in the 2025-26 season:

```python
conditions = (pl.col("strength_state") == "5v5", pl.col("team") == "NSH")
stats.filter(conditions).sort("ixg", Descending=True).head(5)
```

If you want anything besides the default options, or if you change your desired aggregation / level of detail,
you can reset the data with the `prep_stats()` method:

```python
stats = scraper.prep_stats(level="game", teammates=True, opposition=True).stats # (1)!

conditions = (pl.col("strength_state") == "5v5", pl.col("team") == "NSH")
stats.filter(conditions).sort("ixg", Descending=True).head(5)
```

1. Now the individual and on-ice stats are aggregated and account for the teammates and opponents on the ice. The
stats property is chained with the prep_stats method, so it can be called immediately afterwards

Functionality is very similar for forward lines:

```python
forward_lines = scraper.prep_lines(position="f").lines  # (1)!

conditions = (pl.col("toi") >= 2,
              pl.col("strength_state") == "5v5",
              pl.col("team") == "NSH")
forward_lines.filter(conditions).sort("xgf_percent", descending=True).head(5)
```

1. Not strictly necessary, the forwards are the default for line aggregations

And defensive pairings:

```python
defensive_pairings = scraper.prep_lines(position="d").lines # (1)!

conditions = (pl.col("toi") >= 2,
              pl.col("strength_state") == "5v5",
              pl.col("team") == "NSH")
defensive_pairings.filter(conditions).sort("xgf_percent", descending=True).head(5)
```

1. Resets the saved line stats to be defensive lines, rather than forward lines.
You can access the new line stats with the `lines` attribute

As well as team statistics:

```python
team_stats = scraper.team_stats # (1)!

team_stats.sort("toi", descending=True).head(5)
```

1. None of the above is necessary with the `team_stats`, if you're fine with the default parameters, which are
aggregated to the game level and account for strength state

### Standings

You can also use a `Season` object to return that season's standings:

```python
from chickenstats.chicken_nhl import Season

season = Season(2025)
standings = season.standings # (1)!

standings.head(5)
```

1. Standings data are returned for that moment in time - i.e., data will be updated automatically as games are played

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

### Accessing underlying data

It's possible to access the various underlying data from the different endpoints using the `Scraper` object, including:

* Play-by-play events from API and HTML endpoints
* Rosters from API and HTML endpoints
* Shifts from the HTML endpoint
* Change events, built from the (HTML) shifts and (combined) rosters data

???+ note

    Each of the below code snippets assume you'll have initialized a `Scraper` object with a game ID, or list of game IDs:

    ```python

    from chickenstats.chicken_nhl import Season, Scraper

    season = Season(2025)
    nsh_schedule = season.schedule("NSH")

    condition = pl.col("game_state") == "OFF"
    game_ids = nsh_schedule.filter(condition)["game_id"].to_list()

    scraper = Scraper(game_ids)
    ```

=== "Play-by-play events"

    Play-by-play events from the API endpoint:

    ```python
    api_events = scraper.api_events

    conditions = (pl.col("event") == "GOAL", pl.col("event_team") == "NSH")

    api_events.filter(conditions).head(5)
    ```

    Play-by-play events from the HTML endpoint:

    ```python
    html_events = scraper.html_events

    conditions = (pl.col("event") == "GOAL", pl.col("event_team") == "NSH")

    html_events.filter(conditions).head(5)
    ```

=== "Rosters"

    Roster data from the API endpoint:

    ```python
    api_rosters = scraper.api_rosters

    condition = pl.col("team") == "NSH"
    api_rosters.filter(condition).head(5)
    ```

    Roster data from the HTML endpoint:

    ```python
    html_rosters = scraper.html_rosters

    condition = pl.col("team") == "NSH"
    html_rosters.filter(condition).head(5)
    ```

    Combined roster data:

    ```python
    rosters = scraper.rosters

    condition = pl.col("team") == "NSH"
    rosters.filter(condition).head(5)
    ```

=== "Shifts"

    Shifts data from the HTML endpoint:

    ```python
    shifts = scraper.shifts

    condition = pl.col("team") == "NSH"
    shifts.filter(condition).head(5)
    ```

=== "Changes"

    Changes data built from the HTML shifts:

    ```python
    changes = scraper.changes

    condition = condition = pl.col("event_team") == "NSH"
    changes.filter(condition).head(5)
    ```

### Different backend dataframes

Although [polars](https://docs.pola.rs/api/python/stable/reference/index.html) is the default backend for
`chicken_nhl`, you can leverage any [narwhals](https://narwhals-dev.github.io/narwhals/)-compatible library, including pandas as pyarrow, simply by providing
a "backend" argument to the `Scraper` object on initialization:

```python
scraper = Scraper(game_ids, backend="pandas")
play_by_play = scraper.play_by_play # returns a pandas dataframe

scraper = Scraper(game_ids, backend="pyarrow")
play_by_play = scraper.play_by_play # returns a pyarrow dataframe
```

Your choices will be carried through to the various aggregations:

```python
scraper = Scraper(game_ids, backend="pandas")
play_by_play = scraper.play_by_play

stats = scraper.prep_stats(level="season").stats    # Returns pandas dataframe
```

You can even provide "narwhals" as an argument to leverage the full package:

```python
scraper = Scraper(game_ids, backend="narwhals")
play_by_play = scraper.play_by_play # returns a narwhals dataframe
play_by_play.to_pandas() # convert to pandas dataframe
play_by_play.to_arrow() # convert to pyarrow dataframe
```

For more details on the library, see [:material-ruler-square: Design](./../../contribute/backend/design.md).
