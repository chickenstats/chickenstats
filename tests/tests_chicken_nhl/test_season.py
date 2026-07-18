import copy

import polars as pl
import pytest

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl.season import (
    Season,
    multi_season_schedule,
    add_schedule_context,
    _SESSION_CODES,
    _TEAMS_BY_YEAR,
)

_skip_no_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")


class TestSeason:
    def test_schedule_includes_game_date_dt_local(self):
        """Regression test: game_date_dt_local was silently dropped by a schema/data
        mismatch (present in the raw dict, absent from schedule_polars_schema)."""
        season = Season(year=2023)
        schedule = season.schedule("NSH", disable_progress_bar=True)
        assert "game_date_dt_local" in schedule.columns
        assert schedule.schema["game_date_dt_local"] == pl.Datetime(time_unit="us")

    def test_schedule_game_date_dt_local_preserves_local_wall_clock(self):
        """game_date_dt_local must reflect each game's own venue-local wall-clock time,
        not get silently UTC-shifted (a real risk since different games in one schedule
        can have different venue timezones, and a polars column can only carry one)."""
        season = Season(year=2023)
        schedule = season.schedule("NSH", disable_progress_bar=True)
        row = schedule.filter(pl.col("game_id") == 2023020015)
        assert row["game_date_dt_local"][0].strftime("%H:%M") == "19:00"
        assert row["venue_timezone"][0] == "US/Central"

    @pytest.mark.parametrize(
        "year,backend",
        [
            (2023, "polars"),  # modern season
            pytest.param(1991, "pandas", marks=_skip_no_pandas),  # expansion era
            (1917, "polars"),  # oldest season
        ],
    )
    def test_schedule(self, year, backend):
        season = Season(year=year, backend=backend)
        schedule = season.schedule()
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(schedule, pd.DataFrame)
        if backend == "polars":
            assert isinstance(schedule, pl.DataFrame)

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_schedule_nashville(self, backend):
        season = Season(year=2023, backend=backend)

        schedule = season.schedule("NSH")

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(schedule, pd.DataFrame)

        if backend == "polars":
            assert isinstance(schedule, pl.DataFrame)

        schedule = season.schedule("TBL")

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(schedule, pd.DataFrame)

        if backend == "polars":
            assert isinstance(schedule, pl.DataFrame)

    def test_season_fail(self):
        with pytest.raises(Exception):
            Season(2030)

    def test_season_immediately_after_last_tabled_year_raises(self):
        """The season right after the last entry in _TEAMS_BY_YEAR must raise, not silently
        leave `self.teams` (and therefore `schedule()`) empty.

        Regression test: the previous guard only raised when `first_year != max + 1`, so the
        very next NHL season after the table was last updated passed with `self.teams = None`,
        and `schedule()` would silently return an empty DataFrame instead of erroring.
        """
        next_untabled_year = max(_TEAMS_BY_YEAR) + 1
        with pytest.raises(Exception):
            Season(next_untabled_year)

    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_standings(self, backend):
        season = Season(year=2023, backend=backend)

        standings = season.standings

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(standings, pd.DataFrame)

        if backend == "polars":
            assert isinstance(standings, pl.DataFrame)


class TestMultiSeasonSchedule:
    @pytest.mark.parametrize("backend", [pytest.param("pandas", marks=_skip_no_pandas), "polars"])
    def test_combines_multiple_seasons(self, backend):
        schedule = multi_season_schedule([2021, 2022], teams="NSH", backend=backend, disable_progress_bar=True)

        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(schedule, pd.DataFrame)
            seasons = set(schedule["season"].unique().tolist())
        else:
            assert isinstance(schedule, pl.DataFrame)
            seasons = set(schedule["season"].unique().to_list())

        assert seasons == {20212022, 20222023}

    def test_matches_manual_single_season_loop(self):
        combined = multi_season_schedule([2021, 2022], teams="NSH", disable_progress_bar=True)

        manual = pl.concat([Season(year).schedule("NSH", disable_progress_bar=True) for year in [2021, 2022]])

        assert combined.shape == manual.shape
        assert combined["game_id"].to_list() == manual["game_id"].to_list()

    def test_accepts_range(self):
        schedule = multi_season_schedule(range(2021, 2023), teams="NSH", disable_progress_bar=True)
        assert set(schedule["season"].unique().to_list()) == {20212022, 20222023}


class TestAddScheduleContext:
    def test_long_format_shape(self):
        schedule = pl.DataFrame(
            {
                "season": [20232024, 20232024],
                "session": [2, 2],
                "game_id": [1, 2],
                "game_date": ["2023-10-10", "2023-10-12"],
                "home_team": ["NSH", "TBL"],
                "away_team": ["TBL", "NSH"],
            }
        )
        result = add_schedule_context(schedule)
        assert result.shape[0] == schedule.shape[0] * 2
        assert set(result.columns) == {
            "season",
            "session",
            "game_id",
            "game_date",
            "team",
            "opp_team",
            "home_away",
            "rest_days",
            "back_to_back",
        }

    def test_rest_days_computed_correctly(self):
        schedule = pl.DataFrame(
            {
                "game_id": [1, 2, 3],
                "game_date": ["2023-10-10", "2023-10-12", "2023-10-13"],
                "home_team": ["NSH", "NSH", "NSH"],
                "away_team": ["TBL", "SEA", "BOS"],
            }
        )
        result = add_schedule_context(schedule)
        nsh = result.filter(pl.col("team") == "NSH").sort("game_date")
        assert nsh["rest_days"].to_list() == [None, 2, 1]

    def test_back_to_back_flag(self):
        schedule = pl.DataFrame(
            {
                "game_id": [1, 2, 3],
                "game_date": ["2023-10-10", "2023-10-12", "2023-10-13"],
                "home_team": ["NSH", "NSH", "NSH"],
                "away_team": ["TBL", "SEA", "BOS"],
            }
        )
        result = add_schedule_context(schedule)
        nsh = result.filter(pl.col("team") == "NSH").sort("game_date")
        assert nsh["back_to_back"].to_list() == [None, False, True]

    def test_first_game_has_null_rest_days(self):
        schedule = pl.DataFrame(
            {"game_id": [1], "game_date": ["2023-10-10"], "home_team": ["NSH"], "away_team": ["TBL"]}
        )
        result = add_schedule_context(schedule)
        assert result["rest_days"].to_list() == [None, None]

    def test_home_away_labels(self):
        schedule = pl.DataFrame(
            {"game_id": [1], "game_date": ["2023-10-10"], "home_team": ["NSH"], "away_team": ["TBL"]}
        )
        result = add_schedule_context(schedule)
        home_row = result.filter(pl.col("team") == "NSH")
        away_row = result.filter(pl.col("team") == "TBL")
        assert home_row["home_away"][0] == "home"
        assert home_row["opp_team"][0] == "TBL"
        assert away_row["home_away"][0] == "away"
        assert away_row["opp_team"][0] == "NSH"

    def test_teams_are_independent(self):
        """A team's rest days are computed only against its own prior games, not
        another team's schedule."""
        schedule = pl.DataFrame(
            {
                "game_id": [1, 2, 3, 4],
                "game_date": ["2023-10-10", "2023-10-11", "2023-10-10", "2023-10-20"],
                "home_team": ["NSH", "NSH", "TBL", "TBL"],
                "away_team": ["NYR", "SEA", "BOS", "CGY"],
            }
        )
        result = add_schedule_context(schedule)
        nsh = result.filter(pl.col("team") == "NSH").sort("game_date")
        tbl = result.filter(pl.col("team") == "TBL").sort("game_date")
        assert nsh["rest_days"].to_list() == [None, 1]
        assert tbl["rest_days"].to_list() == [None, 10]

    def test_season_boundary_gap_is_large_not_null(self):
        """A team's first game of a new season isn't null rest days when a prior
        season's game is present in the input — it reflects the real (large) gap."""
        schedule = pl.DataFrame(
            {
                "game_id": [1, 2],
                "game_date": ["2023-04-01", "2023-10-10"],
                "home_team": ["NSH", "NSH"],
                "away_team": ["TBL", "TBL"],
            }
        )
        result = add_schedule_context(schedule)
        nsh = result.filter(pl.col("team") == "NSH").sort("game_date")
        assert nsh["rest_days"].to_list() == [None, 192]
        assert nsh["back_to_back"].to_list() == [None, False]

    @_skip_no_pandas
    def test_pandas_backend_preserved(self):
        schedule = pd.DataFrame(
            {
                "game_id": [1, 2],
                "game_date": ["2023-10-10", "2023-10-12"],
                "home_team": ["NSH", "NSH"],
                "away_team": ["TBL", "SEA"],
            }
        )
        result = add_schedule_context(schedule)
        assert isinstance(result, pd.DataFrame)

    @_skip_no_pandas
    def test_backend_override(self):
        schedule = pl.DataFrame(
            {"game_id": [1], "game_date": ["2023-10-10"], "home_team": ["NSH"], "away_team": ["TBL"]}
        )
        result = add_schedule_context(schedule, backend="pandas")
        assert isinstance(result, pd.DataFrame)

    def test_real_schedule(self):
        schedule = Season(2023).schedule("NSH", disable_progress_bar=True)
        result = add_schedule_context(schedule)
        assert result.shape[0] == schedule.shape[0] * 2
        assert result.filter(pl.col("team") == "NSH")["back_to_back"].sum() > 0


# -----------------------------------------------------------------------------
# __init__ branches
# -----------------------------------------------------------------------------


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

    def test_repr(self):
        season = Season(2023)
        r = repr(season)
        assert "Season(season=" in r
        assert "backend=" in r

    def test_scrape_standings_raises_clear_error_on_http_error(self):
        """A non-2xx response must surface as a clear requests.HTTPError from
        raise_for_status(), not an opaque KeyError deep in _munge_standings."""
        import requests
        from unittest.mock import MagicMock, patch

        season = Season(2023)
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
        with patch.object(season._requests_session, "get", return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                season._scrape_standings()

    def test_float_four_digit_year_converts_to_eight(self):
        """A float year (e.g. 2023.0) must not silently skip both length branches.

        Regression test: str(2023.0) == "2023.0" (len 6), which previously matched
        neither the 8-digit nor 4-digit branch, leaving `self.season` unset and raising
        AttributeError on the very next line.
        """
        season = Season(2023.0)
        assert season.season == 20232024

    def test_float_eight_digit_year_stored_as_is(self):
        season = Season(20232024.0)
        assert season.season == 20232024

    def test_invalid_year_format_raises(self):
        """A year that isn't a recognizable 4- or 8-digit form must raise a clear error
        instead of silently leaving `self.season` unset."""
        from chickenstats.exceptions import InvalidSeasonError

        with pytest.raises(InvalidSeasonError):
            Season("not-a-year")


# -----------------------------------------------------------------------------
# schedule caching
# -----------------------------------------------------------------------------


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

    def test_schedule_with_list_of_teams(self):
        """Passing teams as a list exercises the isinstance(teams, list) branch."""
        season = Season(2023)
        schedule = season.schedule(["NSH", "TBL"])
        if HAS_PANDAS and isinstance(schedule, pd.DataFrame):
            assert not schedule.empty
        else:
            assert len(schedule) > 0

    def test_standings_second_call_uses_cache(self):
        """Second standings call hits the False branch of `if not self._standings:`."""
        season = Season(2023)
        df1 = season.standings
        df2 = season.standings
        assert len(df1) == len(df2)


# -----------------------------------------------------------------------------
# _munge_schedule sessions filtering
# -----------------------------------------------------------------------------


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
