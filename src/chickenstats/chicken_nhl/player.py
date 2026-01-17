from typing import Literal

import pandas as pd
import polars as pl

from chickenstats.utilities import ChickenSession


def _finalize_dataframe(backend: Literal["pandas", "polars"], data: list | dict) -> pd.DataFrame | pl.DataFrame:
    """Docstring."""
    if backend == "polars":
        df = pl.DataFrame(data)

    elif backend == "pandas":
        df = pl.DataFrame(data)

    return df


class Player:
    """Class instance for player information and statistics."""

    def __init__(self, player_id: int | str, backend: Literal["polars", "pandas"] = "polars"):
        """Instantiates player information."""
        # Setting up initial information

        self.backend = backend  # Whether to use polars or pandas as backend for dataframes

        self.player_id = player_id

        self._base_api_url = "https://api-web.nhle.com/v1"
        self.base_url = self._base_api_url + f"/player/{player_id}"
        self.landing_url = self.base_url + "/landing"
        self.current_game_log_url = self.base_url + "/game-log/now"

        self.session = ChickenSession()  # Setting up requests sessions object to re-use

        # Getting the landing page information

        self._landing_info = self._scrape_landing()

        # Basic player information from landing page

        stats_keys = ["featuredStats", "careerTotals", "last5Games", "seasonTotals"]  # dictionary keys to leave behind

        self.player_info = {
            k: v for k, v in self._landing_info.items() if k not in stats_keys and k != "currentTeamRoster"
        }

        self.first_name = self.player_info["firstName"]["default"]
        self.last_name = self.player_info["lastName"]["default"]
        self.player_name = f"{self.first_name} {self.last_name}"

        self.is_active = self.player_info["isActive"]
        self.current_team_id = self.player_info["currentTeamId"]
        self.current_team = self.player_info["currentTeamAbbrev"]
        self.current_team_name = self.player_info["teamCommonName"]["default"]
        self.current_team_full_name = self.player_info["fullTeamName"]["default"]
        self.current_team_full_name_fr = self.player_info["fullTeamName"]["fr"]

        # Basic stats from landing page

        self._featured_stats = self._landing_info["featuredStats"]
        self._current_featured_season = self._featured_stats["season"]
        self._featured_regular_season_stats = self._featured_stats["regularSeason"]["subSeason"]
        self._featured_career_stats = self._featured_stats["regularSeason"]["career"]

        self._career_totals = self._landing_info["careerTotals"]
        self._career_regular_season_stats = self._career_totals["regularSeason"]
        self._career_playoff_stats = self._career_totals["playoffs"]

        self._last_five_games = self._landing_info["last5Games"]

        self._season_totals = self._landing_info["seasonTotals"]

        # Scraping game log information

        self._current_game_logs = self._scrape_current_logs()
        self._game_logs = self._current_game_logs["gameLog"]

        # Basic stats from game logs

        self._active_seasons_data = {x["season"]: x["gameTypes"] for x in self._current_game_logs["playerStatsSeasons"]}

        self.active_seasons = [k for k, v in self._active_seasons_data.items() if 2 in v]
        self.playoff_seasons = [k for k, v in self._active_seasons_data.items() if 3 in v]

    def _scrape_landing(self) -> dict:
        """Scrapes landing page information for player."""
        with self.session as s:
            response = s.get(self.landing_url)

        return response.json()

    def _scrape_current_logs(self) -> dict:
        """Scrapes game logs for latest season for player."""
        with self.session as s:
            response = s.get(self.current_game_log_url)

        return response.json()

    def _munge_career_regular_season_stats(self) -> None:
        """Docstring."""
        old_stats = self._career_regular_season_stats

        new_stats = {
            "season": self._current_featured_season,
            "games_played": old_stats.get("gamesPlayed"),
            "goals": old_stats.get("goals"),
            "shots": old_stats.get("shots"),
            "shooting_pct": old_stats.get("shootingPctg"),
            "ot_goals": old_stats.get("otGoals"),
            "game_winning_goals": old_stats.get("gameWinningGoals"),
            "pp_goals": old_stats.get("powerPlayGoals"),
            "sh_goals": old_stats.get("shorthandedGoals"),
            "assists": old_stats.get("assists"),
            "pp_assists": old_stats.get("powerPlayPoints", 0) - old_stats.get("powerPlayGoals", 0),
            "sh_assists": old_stats.get("shorthandedPoints", 0) - old_stats.get("shorthandedGoals", 0),
            "points": old_stats.get("points"),
            "plus_minus": old_stats.get("plusMinus"),
            "pp_points": old_stats.get("powerPlayPoints"),
            "sh_points": old_stats.get("shorthandedPoints"),
            "pim": old_stats.get("pim"),
        }

        self._career_regular_season_stats = new_stats
