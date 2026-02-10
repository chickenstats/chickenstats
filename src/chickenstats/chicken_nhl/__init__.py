"""
chickenstats.chicken_nhl: Quickly and easily scrape NHL data
=================================

chickenstats.chicken_nhl allows you to quickly and easily scrape and analyze
NHL data from various API and HTML endpoints.

Scrape play-by-play data:
   >>> from chickenstats.chicken_nhl import Season, Scraper
   >>> import polars as pl
   >>> season = Season(2025) # setting the current season
   >>> schedule = season.schedule() # scraping the current season's schedule
   >>> game_ids = schedule.filter(pl.col("game_state") == "OFF")["game_id"].tolist()
   >>> scraper = Scraper(game_ids[:25]) # setting up the scraper object, using only first 25 games
   >>> pbp = scraper.play_by_play # scraping play-by-play data

Aggregating individual statistics:
   >>> stats = scraper.stats # aggregating individual box score and on-ice statistics
   # Resetting stats and aggregating with team and opponent information
   >>> scraper.prep_stats(teammates=True, opposition=True)
   >>> stats = scraper.stats # calling stats again gives you new data

You can also aggregate line and team data:
   >>> lines = scraper.lines # aggregating forward line stats
   # Reseting line stats to defensive line data
   >>> scraper.prep_lines(position="d")
   >>> lines = scraper.lines # calling lines again gives you new data
   >>> team_stats = scraper.team_stats # aggregating team stats

Default backend is polars, but you can also use pandas:
    >>> from chickenstats.chicken_nhl import Season, Scraper
    >>> import pandas as pd
    >>> season = Season(2025, backend="pandas") # setting the current season
    >>> schedule = season.schedule() # scraping the current season's schedule
    >>> game_ids = schedule.loc[schedule.game_state == "OFF"].game_id.tolist()
    >>> scraper = Scraper(game_ids, backend="pandas")
    >>> pbp = scraper.play_by_play # scraping play-by-play data, this time with pandas as the backend

Documentation: https://chickenstats.com/
Source Code: https://github.com/chickenandstats/chickenstats
"""

from chickenstats.chicken_nhl.scraper import Scraper
from chickenstats.chicken_nhl.season import Season
from chickenstats.chicken_nhl.game import Game
from chickenstats.chicken_nhl.player import Player
from chickenstats.chicken_nhl.team import Team