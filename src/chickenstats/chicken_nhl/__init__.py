"""chickenstats.chicken_nhl: Scrape and aggregate NHL data.
=================================

chickenstats.chicken_nhl allows you to quickly and easily scrape, aggregate, and analyze
NHL data from various API and HTML endpoints.

Scrape play-by-play data:
   >>> from chickenstats.chicken_nhl import Season, Scraper
   >>> import polars as pl
   >>> season = Season(2025)  # setting the current season
   >>> schedule = season.schedule()  # scraping the current season's schedule
   >>> game_ids = schedule.filter(pl.col("game_state") == "OFF")["game_id"].to_list()
   >>> scraper = Scraper(game_ids[:25])  # setting up the scraper object, using only first 25 games
   >>> pbp = scraper.play_by_play  # scraping play-by-play data

Aggregating individual statistics:
   >>> stats = scraper.stats  # aggregating individual box score and on-ice statistics
   # Resetting stats and aggregating with team and opponent information
   >>> stats = scraper.prep_stats(teammates=True, opposition=True).stats    # calling stats again gives you new data

You can also aggregate line and team data:
   >>> lines = scraper.lines  # aggregating forward line stats
   # Resetting line stats to defensive line data
   >>> defense = scraper.prep_lines(position="d").lines # calling lines again gives you new data
   >>> team_stats = scraper.team_stats  # aggregating team stats

Default backend is polars, but you can also use pandas:
    >>> from chickenstats.chicken_nhl import Season, Scraper
    >>> import pandas as pd
    >>> season = Season(2025, backend="pandas")  # setting the current season
    >>> schedule = season.schedule()  # scraping the current season's schedule
    >>> game_ids = schedule.loc[schedule.game_state == "OFF"].game_id.tolist()
    >>> scraper = Scraper(game_ids, backend="pandas")
    >>> pbp = scraper.play_by_play  # scraping play-by-play data, this time with pandas as the backend

Documentation: https://docs.chickenstats.com/
Source Code: https://github.com/chickenstats/chickenstats
"""

from chickenstats.chicken_nhl.scraper import Scraper
from chickenstats.chicken_nhl.season import Season, multi_season_schedule, add_schedule_context
from chickenstats.chicken_nhl.game import Game
from chickenstats.chicken_nhl.player import (Player, search_players)
from chickenstats.chicken_nhl.team import Team
from chickenstats.chicken_nhl._aggregation import (
    build_play_by_play_ext,
    prep_ind,
    prep_oi,
    prep_stats,
    prep_lines,
    prep_team_stats,
    prep_rolling_stats,
)

__all__ = [
    "Scraper",
    "Season",
    "multi_season_schedule",
    "add_schedule_context",
    "Game",
    "Player",
    "search_players",
    "Team",
    "build_play_by_play_ext",
    "prep_ind",
    "prep_oi",
    "prep_stats",
    "prep_lines",
    "prep_team_stats",
    "prep_rolling_stats",
]
