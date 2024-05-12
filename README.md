# chickenstats

<div style="text-align: center;">

[![Hero image - scatter plot with drumsticks and tooltips](https://raw.githubusercontent.com/chickenandstats/chickenstats/main/assets/hero_transparent.png)](https://chickenstats.com)

[![PyPI - Version](https://img.shields.io/pypi/v/chickenstats?color=BrightGreen)](https://pypi.org/project/chickenstats)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/chickenstats?color=BrightGreen)](https://pypi.org/project/chickenstats)
[![tests](https://github.com/chickenandstats/chickenstats/actions/workflows/tests.yml/badge.svg)](https://github.com/chickenandstats/chickenstats/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/chickenandstats/chickenstats/graph/badge.svg?token=Z1ETX5L8FL)](https://codecov.io/gh/chickenandstats/chickenstats)
![GitHub Release Date - Published_At](https://img.shields.io/github/release-date/chickenandstats/chickenstats?color=BrightGreen)
![GitHub License](https://img.shields.io/github/license/chickenandstats/chickenstats?color=BrightGreen)

</div>

---

## About

`chickenstats` is a Python package for scraping & analyzing sports data. With just a few lines of code:
* **Scrape & manipulate** data from various NHL endpoints, leveraging `chickenstats.chicken_nhl`, which includes
a **proprietary xG model** for shot quality metrics
* **Augment play-by-play data** & **generate custom aggregations** from raw csv files downloaded from
[Evolving-Hockey](https://evolving-hockey.com) *(subscription required)* with `chickenstats.evolving_hockey`

For more in-depth explanations, tutorials, & detailed reference materials, consult the
[**Documentation**](https://chickenstats.com). 

---

## Compatibility

`chickenstats` requires Python 3.10 or greater & runs on the latest stable versions of Linux, macOS, & Windows
operating systems.

---

## Installation

Very simple - install using PyPi. Best practice is to develop in an isolated virtual environment (conda or otherwise),
but who's a chicken to judge?

```sh
pip install chickenstats
```

To confirm installation & confirm the latest version (1.7.8):

```sh
pip show chickenstats
```

---

## Usage

`chickenstats` is structured as two underlying modules, each used with different data sources:
* `chickenstats.chicken_nhl`
* `chickenstats.evolving_hockey`

The package is under active development - features will be added or modified over time. 

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
nsh_schedule_reg = nsh_schedule.loc[nsh_schedule.game_state == "OFF"].reset_index(drop=True)

# Extract game IDs, excluding pre-season games
game_ids = nsh_schedule_reg.game_id.tolist()[:10]

# Create a scraper object using the game IDs
scraper = Scraper(game_ids)

# Scrape play-by-play data
play_by_play = scraper.play_by_play
```

### evolving_hockey
 
The `chickenstats.evolving_hockey` module manipulates raw csv files downloaded from
[Evolving-Hockey](https://evolving-hockey.com). Using their original shifts & play-by-play data, users can add additional
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
forward_lines = prep_lines(play_by_play, level='game', position='f', opposition=True)
```

---

## Acknowledgements

`chickenstats` wouldn't be possible without the support & efforts of countless others. I am obviously
extremely grateful, even if there are too many of you to thank individually. However, this chicken will do his best.

First & foremost is my wife - the lovely Mrs. Chicken has been patient, understanding, & supportive throughout the countless
hours of development, sometimes to her detriment.

Sincere apologies to the friends & family that have put up with me since my entry into Python, programming, & data
analysis in January 2021. Thank you for being excited for me & with me throughout all of this, especially when you've
had to fake it...

Thank you to the hockey analytics community on (the artist formerly known as) Twitter. You're producing
& reacting to cutting-edge statistical analyses, while providing a supportive, welcoming environment for newcomers.
Thank y'all for everything that you do. This is by no means exhaustive, but there are a few people worth
calling out specifically:
* Josh & Luke Younggren ([@EvolvingWild](https://twitter.com/EvolvingWild))
* Bryan Bastin ([@BryanBastin](https://twitter.com/BryanBastin))
* Max Tixador ([@woumaxx](https://twitter.com/woumaxx))
* Micah Blake McCurdy ([@IneffectiveMath](https://twitter.com/IneffectiveMath))
* Prashanth Iyer ([@iyer_prashanth](https://twitter.com/iyer_prashanth))
* The Bucketless ([@the_bucketless](https://twitter.com/the_bucketless))
* Shayna Goldman ([@hayyyshayyy](https://twitter.com/hayyyshayyy))
* Dom Luszczyszyn ([@domluszczyszyn](https://twitter.com/domluszczyszyn))

I'm also grateful to the thriving community of Python educators & open-source contributors on Twitter. Thank y'all
for your knowledge & practical advice. Matt Harrison ([@__mharrison__](https://twitter.com/__mharrison__))
deserves a special mention for his books on Pandas and XGBoost, both of which are available at his online
[store](https://store.metasnake.com). Again, not exhaustive, but others worth thanking individually:
* Will McGugan ([@willmcgugan](https://twitter.com/willmcgugan))
* Rodrigo Girão Serrão ([@mathsppblog](https://twitter.com/mathsppblog))
* Mike Driscoll ([@driscollis](https://twitter.com/driscollis))
* Trey Hunner ([@treyhunner](https://twitter.com/treyhunner))
* Pawel Jastrzebski ([@pawjast](https://twitter.com/pawjast))

Finally, this library depends on a host of other open-source packages. `chickenstats` is possible because of the efforts
of thousands of individuals, represented below:
* [Pandas](https://pandas.pydata.org)
* [scikit-Learn](https://scikit-learn.org/stable/)
* [matplotlib](https://matplotlib.org)
* [Rich](https://github.com/Textualize/rich)
* [Pydantic](https://github.com/pydantic/pydantic)
* [Pandera](https://pandera.readthedocs.io/en/stable/)
* [XGBoost](https://xgboost.readthedocs.io/en/stable/)
* [Mkdocs](https://www.mkdocs.org)
* [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
* [MlFlow](https://mlflow.org/docs/latest/index.html)
* [Optuna](https://optuna.readthedocs.io/en/stable/)
* [Black](https://github.com/psf/black)
* [Ruff](https://github.com/astral-sh/ruff)
* [Jupyter](https://jupyter.org)
* [Pytest](https://docs.pytest.org/en/8.2.x/)
* [Tox](https://tox.wiki/en/4.15.0/)
* [Caddy](https://caddyserver.com)
* [Yellowbrick](https://www.scikit-yb.org/en/latest/)
* [Shap](https://shap.readthedocs.io/en/latest/)
* [Seaborn](https://seaborn.pydata.org)
* [hockey-rink](https://github.com/the-bucketless/hockey_rink)
