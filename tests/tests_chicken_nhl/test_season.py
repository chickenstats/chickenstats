import copy

import pandas as pd
import polars as pl
import pytest

from chickenstats.chicken_nhl.season import Season, _SESSION_CODES


class TestSeason:
    @pytest.mark.parametrize("year", [2023, 20232024, 1917, 1942, 1967, 1982, 1991, 2011])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_schedule(self, year, backend):
        season = Season(year=year, backend=backend)

        schedule = season.schedule()

        if backend == "pandas":
            assert isinstance(schedule, pd.DataFrame)

        if backend == "polars":
            assert isinstance(schedule, pl.DataFrame)

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_schedule_nashville(self, backend):
        season = Season(year=2023, backend=backend)

        schedule = season.schedule("NSH")

        if backend == "pandas":
            assert isinstance(schedule, pd.DataFrame)

        if backend == "polars":
            assert isinstance(schedule, pl.DataFrame)

        schedule = season.schedule("TBL")

        if backend == "pandas":
            assert isinstance(schedule, pd.DataFrame)

        if backend == "polars":
            assert isinstance(schedule, pl.DataFrame)

    def test_season_fail(self):
        with pytest.raises(Exception):
            Season(2030)

    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_standings(self, backend):
        season = Season(year=2023, backend=backend)

        standings = season.standings

        if backend == "pandas":
            assert isinstance(standings, pd.DataFrame)

        if backend == "polars":
            assert isinstance(standings, pl.DataFrame)


# ---------------------------------------------------------------------------
# __init__ branches
# ---------------------------------------------------------------------------


class TestSeasonInit:
    def test_four_digit_year_converts_to_eight(self):
        season = Season(2023)
        assert season.season == 20232024

    def test_eight_digit_year_stored_as_is(self):
        season = Season(20232024)
        assert season.season == 20232024

    def test_custom_standings_date_stored(self):
        season = Season(2023, standings_date="2024-01-15")
        assert season.standings_date == "2024-01-15"

    def test_current_season_standings_date_is_now(self):
        season = Season(20252026)
        assert season.standings_date == "now"

    def test_season_str_format(self):
        season = Season(2023)
        assert season._season_str == "2023-24"

    def test_teams_populated(self):
        season = Season(2023)
        assert isinstance(season.teams, list)
        assert len(season.teams) > 0


# ---------------------------------------------------------------------------
# schedule caching
# ---------------------------------------------------------------------------


class TestScheduleCaching:
    def test_cached_team_not_re_scraped(self):
        """Calling schedule() twice for the same team uses cached data."""
        season = Season(2023)
        schedule1 = season.schedule("NSH")
        scraped_after_first = list(season._scraped_schedule_teams)

        schedule2 = season.schedule("NSH")
        scraped_after_second = list(season._scraped_schedule_teams)

        assert len(schedule1) == len(schedule2)
        assert scraped_after_first == scraped_after_second


# ---------------------------------------------------------------------------
# _munge_schedule sessions filtering
# ---------------------------------------------------------------------------


def _mock_game(**overrides) -> dict:
    """Return a fresh regular-season game dict on each call (avoids in-place mutation)."""
    base = {
        "gameType": 2,
        "season": 20232024,
        "id": 2023020001,
        "startTimeUTC": "2023-10-10T23:00:00Z",
        "venueTimezone": "US/Central",
        "gameState": "OFF",
        "homeTeam": {
            "abbrev": "NSH",
            "id": 18,
            "score": 3,
            "logo": "https://assets.nhle.com/logos/nhl/svg/NSH_light.svg",
            "darkLogo": "https://assets.nhle.com/logos/nhl/svg/NSH_dark.svg",
        },
        "awayTeam": {
            "abbrev": "TOR",
            "id": 10,
            "score": 2,
            "logo": "https://assets.nhle.com/logos/nhl/svg/TOR_light.svg",
            "darkLogo": "https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg",
        },
        "venue": {"default": "Bridgestone Arena"},
        "neutralSite": False,
        "tvBroadcasts": [],
    }
    base.update(overrides)
    return base


class TestMungeSchedule:
    def test_sessions_none_keeps_regular_and_playoffs(self):
        result = Season._munge_schedule([_mock_game()], sessions=None)
        assert len(result) == 1

    def test_sessions_none_filters_preseason(self):
        result = Season._munge_schedule([_mock_game(gameType=1)], sessions=None)
        assert len(result) == 0

    def test_sessions_list_filters_correctly(self):
        games = [_mock_game(), _mock_game(gameType=1)]
        result = Season._munge_schedule(games, sessions=["R"])
        assert len(result) == 1
        assert result[0]["session"] == 2

    def test_sessions_string_filters_correctly(self):
        games = [_mock_game(), _mock_game(gameType=1)]
        result = Season._munge_schedule(games, sessions="R")
        assert len(result) == 1

    def test_z_suffix_utc_time_normalized(self):
        """startTimeUTC ending in 'Z' is parsed successfully."""
        game = _mock_game()
        assert game["startTimeUTC"].endswith("Z")
        result = Season._munge_schedule([game], sessions=None)
        assert len(result) == 1
