---
icon: material/hockey-puck
description: "Guide to chickenstats.evolving_hockey"
---

# :material-hockey-puck: **evolving_hockey**

Usage information about the `evolving_hockey` module.

For in-depth materials, please consult the **[:material-bookshelf: Reference](../../reference/reference.md)**

## :fontawesome-solid-user-large: **Basic usage**

### **Import module**

The `evolving_hockey` module and relevant functions can be imported using the below snippet:

```python
from chickenstats.evolving_hockey import prep_pbp, prep_stats, prep_lines, prep_team
```

### **Play-by-play data**

All functions will need a cleaned play-by-play dataframe in order to aggregate the statistics:

```python
shifts_raw = pd.read_csv('shifts_raw.csv') # (1)! 
pbp_raw = pd.read_csv('pbp_raw.csv') # (2)!

pbp = prep_pbp(pbp_raw, shifts_raw)
```

1. Get a Pandas DataFrame of shifts data from Evolving-Hockey.com
2. Ditto for play-by-play data from Evolving-Hockey.com

### **Individual stats**

You can use the cleaned play-by-play data to see individual stats, grouped at various levels. This example
aggregates skaters' individual and on-ice statistics to the game level, grouped by teammates and opposition:

```python
stats = prep_stats(pbp, level = "game", teammates = True, opposition = True)
```

This example groups individual and on-ice stats to the session level, grouping by score state:

```python
stats = prep_stats(pbp, level = "period", score_state = True)
```

Basic game-level statistics can be viewed with the default keyword arguments:

```python
stats = prep_stats(pbp)
```

### **Line stats**

You can also aggregate the data for forward or defensive (or both) line stats. This first example aggregates line stats
to the game level, grouped by opposition:

```python
lines = prep_lines(pbp, positions = 'f', opposition = True)
```

Similarly to the `prep_stats` function, you can group by teammates and score state:

```python
lines = prep_lines(pbp, positions = 'd', teammates = True, score_state = True)
```

### **Team stats**

Aggregate team statistics in the same way as `prep_stats` and `prep_lines` functions. This examples aggregates team stats
to game level:

```python
teams = prep_teams(pbp, level = 'game')
```

You can also group by score state:

```python
teams = prep_teams(pbp, level = 'period', score_state = True)
```
