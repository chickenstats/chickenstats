---
icon: material/hockey-sticks
description: "Guide to chickenstats.chicken_nhl"
---

# :material-hockey-sticks: **chicken_nhl**

Usage information about the `chicken_nhl` module.

For in-depth materials, please consult the **[:material-bookshelf: Reference](../../reference/reference.md)**

## :fontawesome-solid-user-large: **Basic usage**

### **Import module**

`chicken_nhl` scrapes data from various official NHL endpoints, combining them into a usable play-by-play
dataframe. The module and the most relevant classes can be imported using the below snippet:

```py
from chickenstats.chicken_nhl import Scraper, Season
```

### **`Season` and Game IDs**
  
The module relies on game IDs, which can be found using the `schedule` method of `Season` class:

```py
season = Season(2023)
nsh_schedule = season.schedule(sessions="P") # (1)! 

game_ids = nsh_schedule.game_id.tolist()[:10]
```

1. You could provide three-letter code for subset of schedule, as well as scrape from regular season

### **`Scraper`**

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

### **Stats and aggregations**

Start fresh with a new scraper:

```python
scraper = Scraper(game_ids)
play_by_play = scraper.play_by_play # (1)!
```

1. We won't strictly use the play-by-play data here, but it will get the scraping started

If you just want game-level individual stats, without accounting for teammates or opposition, just call the
`stats` attributes:

```python
stats = scraper.stats
```

If you want anything besides the default options, or if you change your desired aggregation / level of detail,
you can reset the data with the `prep_stats()` method:

```python
scraper.prep_stats(level="game", teammates=True, opposition=True) # (1)!
stats = scraper.stats # (2)!
```

1. Now the individual and on-ice stats are aggregated and account for the teammates and opponents on the ice
2. You can access the data with the `stats` attribute

Functionality is very similar for lines and team stats:

```python
scraper.prep_lines(position="f") # (1)!
forward_lines = scraper.lines

scraper.prep_lines(position="d") # (2)!
defense_lines = scraper.lines # (3)!

team_stats = scraper.team_stats # (4)!
```

1. Not strictly necessary, the forwards are the default for line aggregations
2. Resets the saved line stats to be defensive lines, rather than forward lines
3. You can access the new line stats with the `lines` attribute
4. None of the above is necessary with the `team_stats`, if you're fine with the default parameters

### **Standings**

You can also use a `Season` object to return that season's standings:

```python
from chickenstats.chicken_nhl import Season

season = Season(2023)
standings = season.standings
```

## :material-palette-advanced: **Advanced usage**

The `Scraper` object should be best for most of your scraping needs. However, there are additional 
properties available with the `Game` object that can be helpful.

### **Other `Scraper` data**

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

### **`Game` object**

The `Game` object only works with a single game ID:

```python
game = Game(2023020001)
```

### **Lists, not DataFrames**

The `Game` object's familiar functions return lists, instead of Pandas DataFrames:

```python
game.play_by_play # (1)! 

game.play_by_play_df # (2)! 
```

1. Returns a list of play-by-play events
2. Returns a Pandas DataFrame of play-by-play events

### **Pre-processing**

Data can be inspected at various processing stages through the `Game` object's non-public properties:

```python
game._scrape_html_events # (1)! 

game._munge_html_events # (2)!
```

1. Get the raw HTML events and store the without processing
2. Process the raw HTML events and store them

A list of the non-public properties can be found in
**[:fontawesome-solid-user-group: Contribute](../../contribute/contribute.md)**



