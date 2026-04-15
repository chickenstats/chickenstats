from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cached_property
import logging
from typing import Literal

from chickenstats.utilities import ChickenSession
from chickenstats.utilities.enums import Backend

logger = logging.getLogger(__name__)


class Player:
    """Class instance for player information and statistics."""

    def __init__(self, player_id: int | str, backend: Backend | Literal["polars", "pandas"] = "polars"):
        """Instantiates player endpoints and session — no network calls are made here."""
        self.backend = backend
        self.player_id = player_id

        self._base_api_url = "https://api-web.nhle.com/v1"
        self.base_url = f"{self._base_api_url}/player/{player_id}"
        self.landing_url = f"{self.base_url}/landing"
        self.current_game_log_url = f"{self.base_url}/game-log/now"

        self._requests_session = ChickenSession()

    def __repr__(self) -> str:
        """Return string representation of the Player instance."""
        return f"Player(player_id={self.player_id!r}, backend={self.backend!r})"

    # ------------------------------------------------------------------
    # Raw network fetchers (lazy, cached)
    # ------------------------------------------------------------------

    @cached_property
    def _landing_info(self) -> dict:
        """Fetches the player landing page from the NHL API."""
        with self._requests_session as s:
            return s.get(self.landing_url).json()

    @cached_property
    def _current_game_logs(self) -> dict:
        """Fetches the current-season game log from the NHL API."""
        with self._requests_session as s:
            return s.get(self.current_game_log_url).json()

    # ------------------------------------------------------------------
    # Player identity (derived from landing info)
    # ------------------------------------------------------------------

    @cached_property
    def player_info(self) -> dict:
        """Basic player metadata, with stats keys excluded."""
        stats_keys = {"featuredStats", "careerTotals", "last5Games", "seasonTotals", "currentTeamRoster"}
        return {k: v for k, v in self._landing_info.items() if k not in stats_keys}

    @property
    def first_name(self) -> str:
        """Player's first name."""
        return self.player_info["firstName"]["default"]

    @property
    def last_name(self) -> str:
        """Player's last name."""
        return self.player_info["lastName"]["default"]

    @property
    def player_name(self) -> str:
        """Player's full name (first + last)."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        """Whether the player is currently active on an NHL roster."""
        return self.player_info["isActive"]

    @property
    def current_team_id(self) -> int:
        """NHL team ID for the player's current team."""
        return self.player_info["currentTeamId"]

    @property
    def current_team(self) -> str:
        """Three-letter abbreviation of the player's current team."""
        return self.player_info["currentTeamAbbrev"]

    @property
    def current_team_name(self) -> str:
        """Common name of the player's current team (e.g. 'Predators')."""
        return self.player_info["teamCommonName"]["default"]

    @property
    def current_team_full_name(self) -> str:
        """Full English name of the player's current team (e.g. 'Nashville Predators')."""
        return self.player_info["fullTeamName"]["default"]

    @property
    def current_team_full_name_fr(self) -> str:
        """Full French name of the player's current team."""
        return self.player_info["fullTeamName"]["fr"]

    # ------------------------------------------------------------------
    # Featured / career stats (derived from landing info)
    # ------------------------------------------------------------------

    @cached_property
    def _featured_stats(self) -> dict:
        return self._landing_info["featuredStats"]

    @property
    def _current_featured_season(self) -> int:
        return self._featured_stats["season"]

    @property
    def _featured_regular_season_stats(self) -> dict:
        return self._featured_stats["regularSeason"]["subSeason"]

    @property
    def _featured_career_stats(self) -> dict:
        return self._featured_stats["regularSeason"]["career"]

    @cached_property
    def _career_totals(self) -> dict:
        return self._landing_info["careerTotals"]

    @cached_property
    def _career_regular_season_stats(self) -> dict:
        return self._career_totals["regularSeason"]

    @property
    def _career_playoff_stats(self) -> dict | None:
        return self._career_totals.get("playoffs")

    @property
    def _last_five_games(self) -> list:
        return self._landing_info["last5Games"]

    @property
    def _season_totals(self) -> list:
        return self._landing_info["seasonTotals"]

    # ------------------------------------------------------------------
    # Season / game log data (derived from game logs)
    # ------------------------------------------------------------------

    @property
    def _game_logs(self) -> list:
        return self._current_game_logs["gameLog"]

    @cached_property
    def _active_seasons_data(self) -> dict:
        return {x["season"]: x["gameTypes"] for x in self._current_game_logs["playerStatsSeasons"]}

    @cached_property
    def active_seasons(self) -> list:
        """List of regular-season seasons the player has appeared in."""
        return [k for k, v in self._active_seasons_data.items() if 2 in v]

    @cached_property
    def playoff_seasons(self) -> list:
        """List of playoff seasons the player has appeared in."""
        return [k for k, v in self._active_seasons_data.items() if 3 in v]

    # ------------------------------------------------------------------
    # Prefetch
    # ------------------------------------------------------------------

    def prefetch(self) -> None:
        """Pre-fetch landing page and game log data concurrently.

        Calling this before accessing any property runs both network requests
        in parallel so subsequent property accesses use cached results.
        """

        def _get_landing():
            _ = self._landing_info

        def _get_logs():
            _ = self._current_game_logs

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(task) for task in [_get_landing, _get_logs]]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:  # noqa: BLE001  # pyright: ignore[reportBroadExceptionCaught]
                    logger.debug("Failed to fetch player data endpoint", exc_info=True)

    # ------------------------------------------------------------------
    # Stats processing
    # ------------------------------------------------------------------

    def _munge_career_regular_season_stats(self) -> None:
        """Processes career regular season stats into a standardized format."""
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
