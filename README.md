# chickenstats

<div style="text-align: center;">

[![Hero image - scatter plot with drumsticks and tooltips](assets/hero_white.png)](https://chickenstats.com)

[![PyPI - Version](https://img.shields.io/pypi/v/chickenstats?color=BrightGreen)](https://pypi.org/project/chickenstats)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/chickenstats?color=BrightGreen)](https://pypi.org/project/chickenstats)
[![tests](https://github.com/chickenandstats/chickenstats/actions/workflows/tests.yml/badge.svg)](https://github.com/chickenandstats/chickenstats/actions/workflows/tests.yml)
[![docs](https://github.com/chickenandstats/chickenstats/actions/workflows/docs.yml/badge.svg)](https://github.com/chickenandstats/chickenstats/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/chickenandstats/chickenstats/graph/badge.svg?token=Z1ETX5L8FL)](https://codecov.io/gh/chickenandstats/chickenstats)
![GitHub Release Date - Published_At](https://img.shields.io/github/release-date/chickenandstats/chickenstats?color=BrightGreen)
![GitHub License](https://img.shields.io/github/license/chickenandstats/chickenstats?color=BrightGreen)

</div>

---

## Introduction

`chickenstats` is a Python package for scraping & analyzing sports statistics. With just a few lines of code,
download & manipulate data from various NHL endpoints, [CapFriendly](https://capfriendly.com), &
[Evolving-Hockey](https://evolving-hockey.com) (subscription required). Compatible with Python
versions 3.10, 3.11, & 3.12 on Windows, Mac, & Linux operating systems.

---

## Installation

Very simple - install using PyPi. Best practice is to develop in an isolated virtual environment (conda or otherwise),
but who's a chicken to judge?

```sh
pip install chickenstats
```

## Usage

`chickenstats` is structured as three underlying modules, each used with different data sources:
* `chickenstats.chicken_nhl`
* `chickenstats.evolving_hockey`
* `chickenstats.capfriendly`

Although this guide is enough to get started with each, consult the [**Documentation**](https://chickenstats.com)
as needed for additional reference materials and tutorials.

### chicken_nhl

The `chickenstats.chicken_nhl` module scrapes & manipulates data directly from various NHL endpoints,
with outputs including schedule & game results, rosters, & play-by-play data. 

The below example scrapes the schedule for the Nashville Predators, extracts the game IDs, then
scrapes play-by-play data for the first ten regular season games.

```python
from chickenstats.chicken_nhl import Season, Scraper

# Create a Season object for the current season
season = Season(2023)

# Download the Nashville schedule & filter for regular season games
nsh_schedule = season.schedule('NSH')
nsh_schedule_reg = nsh_schedule.loc[nsh_schedule.session == 2].reset_index(drop = True)

# Extract game IDs, excluding pre-season games
game_ids = nsh_schedule_reg.game_id.tolist()[:10]

# Create a scraper object using the game IDs
scraper = Scraper(game_ids)

# Scrape play-by-play data
play_by_play = scraper.play_by_play
```

### evolving_hockey
 
The `chickenstats.evolving_hockey` module manipulates raw csv files downloaded from
[Evolving-Hockey](https://evolving-hockey.com). Using their original shifts & play-by-play data, adds additional
information & aggregate for individual & on-ice statistics,
including high-danger shooting events, xG & adjusted xG, faceoffs, & changes.

```python
import pandas as pd
from chickenstats.evolving_hockey import prep_pbp, prep_stats, prep_lines

# The prep_pbp function takes the raw event and shifts dataframes
raw_shifts = pd.read_csv('./raw_shifts.csv')
raw_pbp = pd.read_csv('./raw_pbp.csv')

play_by_play = prep_pbp(raw_pbp, raw_shifts)

# You can use the play_by_play dataframe in various aggregations
# These are individual game statistics, including on-ice & usage,
# accounting for teammates & opposition on-ice
individual_game = prep_stats(play_by_play, level='game', teammates=True, opposition=True)

# These are game statistics for forward-line combinations, accounting for opponents on-ice
forward_lines = prep_lines(play_by_play, position='f', opposition=True)
```

### capfriendly

Use `chickenstats.capfriendly` to scrape salary & contract information from [CapFriendly](https://capfriendly.com).
Information available includes AAV, contract term, player age, signing date, draft year, amongst others. 

```python
from chickenstats.capfriendly import scrape_capfriendly

# Scrape CapFriendly data for the current year
cf = scrape_capfriendly(2023)
```

