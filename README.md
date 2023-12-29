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

`chickenstats` is a Python package for scraping & analyzing sports statistics - download & manipulate data from various
NHL endpoints, CapFriendly, & Evolving-Hockey in just a few lines of code. Compatible with Python
versions 3.10, 3.11, & 3.12 on Windows, Mac, & Linux operating systems.

---

## Installation

Very simple - install using PyPi. Best practice is to develop in an isolated virtual environment (conda or otherwise),
but who's a chicken to judge?

```sh
pip install chickenstats
```

## Examples

See the [**Documentation**](https://chickenstats.com) for more details,
additional reference materials, and tutorials.

`chickenstats` is structured as three separate modules, each with different data sources:
* `chickenstats.chicken_nhl`
* `chickenstats.evolving_hockey`
* `chickenstats.capfriendly`

### `chickenstats.chicken_nhl`

The `chicken_nhl` module scrapes & manipulates data directly from various NHL endpoints, with outputs including schedule &
game results, rosters, & play-by-play data. 

The below example scrapes the schedule for the Nashville Predators, extracts the game IDs, then
scrapes play-by-play data for the first ten regular season games.

```python

from chickenstats.chicken_nhl import Season, Scraper

# Create a Season object for the current season
season = Season(2023)

# Download the Nashville schedule
nsh_schedule = season.schedule('NSH')

# Extract game IDs, excluding pre-season games
game_ids = nsh_schedule.loc[nsh_schedule.session == 2].game_id.tolist()[:10]

# Create a scraper object using the game IDs
scraper = Scraper(game_ids)

# Scrape play-by-play data
play_by_play = scraper.play_by_play
```

 
