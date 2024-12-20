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

`chickenstats` requires Python 3.10 or greater & runs on the latest stable versions of Linux, Mac, & Windows
operating systems.

---

## Installation

Very simple - install using PyPi. Best practice is to develop in an isolated virtual environment (conda or otherwise),
but who's a chicken to judge?

```sh
pip install chickenstats
```

To confirm installation & confirm the latest version (1.8.0):

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

`chickenstats.chicken_nhl` allows you to scrape play-by-play data and aggregate individual, line, and team statistics.
After importing the module, scrape the schedule for game IDs, then play-by-play data for your team of choice:

```python
from chickenstats.chicken_nhl import Season, Scraper

season = Season(2024)

schedule = season.schedule("NSH")
game_ids = schedule.loc[schedule.game_state == "OFF"].game_id.tolist()

scraper = Scraper(game_ids)

play_by_play = scraper.play_by_play
```

You can then aggregate the play-by-play data for individual and on-ice statistics with one line of code:

```python
stats = scraper.stats
```

It's very easy to introduce additional detail to the aggregations, including for teammates on-ice:

```python
scraper.prep_stats(teammates=True)
stats = scraper.stats
```

There is similar functionality for line and team stats:

```python
scraper.prep_lines(position="f")
forward_lines = scraper.lines

team_stats = scraper.team_stats
```

For additional information on usage and functionality, consult the relevant
[user guide](https://chickenstats.com/latest/guide/chicken_nhl/chicken_nhl/)

### evolving_hockey
 
The `chickenstats.evolving_hockey` module manipulates raw csv files downloaded from
[Evolving-Hockey](https://evolving-hockey.com). Using their original shifts & play-by-play data, users can add additional
information & aggregate for individual & on-ice statistics,
including high-danger shooting events, xG & adjusted xG, faceoffs, & changes.

First, prep a play-by-play dataframe using raw play-by-play and shifts CSV files from the
[Evolving-Hockey website](https://evolving-hockey.com):

```python
import pandas as pd
from chickenstats.evolving_hockey import prep_pbp, prep_stats, prep_lines

raw_shifts = pd.read_csv('./raw_shifts.csv')
raw_pbp = pd.read_csv('./raw_pbp.csv')

play_by_play = prep_pbp(raw_pbp, raw_shifts)
```

You can use the play_by_play dataframe in various aggregations. This will return individual game statistics,
including on-ice (e.g., GF, xGF) & usage (i.e., zone starts), accounting for teammates & opposition on-ice:

```python
individual_game = prep_stats(play_by_play, level='game', teammates=True, opposition=True)
```

This will return game statistics for forward-line combinations, accounting for opponents on-ice:

```python
forward_lines = prep_lines(play_by_play, level='game', position='f', opposition=True)
```

For additional information on usage and functionality, consult the relevant
[user guide](https://chickenstats.com/latest/guide/evolving_hockey/evolving_hockey/)

---

## **Help**

If you need help with any aspect of `chickenstats`, from installation to usage, please don't hesitate to reach out!
You can find me on :material-bluesky: Bluesky at **[@chickenandstats.com](https://bsky.app/profile/chickenandstats.com)** or :material-email: 
email me at **[chicken@chickenandstats.com](mailto:chicken@chickenandstats.com)**.

Please report any bugs or issues via the `chickenstats` **[issues](https://github.com/chickenandstats/chickenstats/issues)** page, where you can also post feature requests.
Before doing so, please check the [roadmap](./contribute/roadmap.md), there might already be plans to include your request.

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
* [uv](https://github.com/astral-sh/uv)
* [Jupyter](https://jupyter.org)
* [Pytest](https://docs.pytest.org/en/8.2.x/)
* [Tox](https://tox.wiki/en/4.15.0/)
* [Caddy](https://caddyserver.com)
* [Yellowbrick](https://www.scikit-yb.org/en/latest/)
* [Shap](https://shap.readthedocs.io/en/latest/)
* [Seaborn](https://seaborn.pydata.org)
* [hockey-rink](https://github.com/the-bucketless/hockey_rink)
