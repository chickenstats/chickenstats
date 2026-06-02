from __future__ import annotations

from importlib.metadata import version

from chickenstats.chicken_nhl import Game, Player, Scraper, Season, Team

__version__ = version("chickenstats")

__all__ = ["__version__", "Game", "Player", "Scraper", "Season", "Team"]
