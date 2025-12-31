import pandas as pd
import polars as pl
import pytest

from chickenstats.chicken_nhl.season import Season


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
