import pandas as pd
import polars as pl
import pytest

from chickenstats.chicken_nhl.scraper import Scraper


class TestScraper:
    @pytest.mark.parametrize("game_ids", [[2023020001, 2023020002, 2023020003, 2023020004, 2023020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_api_events(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        api_events = scraper.api_events

        if backend == "pandas":
            assert isinstance(api_events, pd.DataFrame)

        if backend == "polars":
            assert isinstance(api_events, pl.DataFrame)

    @pytest.mark.parametrize("game_ids", [[2022020001, 2022020002, 2022020003, 2022020004, 2022020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_api_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        api_rosters = scraper.api_rosters

        if backend == "pandas":
            assert isinstance(api_rosters, pd.DataFrame)

        if backend == "polars":
            assert isinstance(api_rosters, pl.DataFrame)

    @pytest.mark.parametrize("game_ids", [[2021020001, 2021020002, 2021020003, 2021020004, 2021020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_changes(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        changes = scraper.changes

        if backend == "pandas":
            assert isinstance(changes, pd.DataFrame)

        if backend == "polars":
            assert isinstance(changes, pl.DataFrame)

    @pytest.mark.parametrize("game_ids", [[2020020001, 2020020002, 2020020003, 2020020004, 2020020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_html_events(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        html_events = scraper.html_events

        if backend == "pandas":
            assert isinstance(html_events, pd.DataFrame)

        if backend == "polars":
            assert isinstance(html_events, pl.DataFrame)

    @pytest.mark.parametrize("game_ids", [[2019020001, 2019020002, 2019020003, 2019020004, 2019020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_html_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        html_rosters = scraper.html_rosters

        if backend == "pandas":
            assert isinstance(html_rosters, pd.DataFrame)

        if backend == "polars":
            assert isinstance(html_rosters, pl.DataFrame)

    @pytest.mark.parametrize(
        "game_ids",
        [
            [
                2018020001,
                2018020002,
                2018020003,
                2018020004,
                2018020005,
                2023020124,
                2023020124,
                2023020570,
                2023020070,
                2023020021,
                2023020955,
                2023020288,
                2023020005,
                2023020066,
                2023020070,
                2023020039,
                2023020004,
                2023020018,
                2023020005,
            ]
        ],
    )
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_play_by_play(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        play_by_play = scraper.play_by_play

        if backend == "pandas":
            assert isinstance(play_by_play, pd.DataFrame)

        if backend == "polars":
            assert isinstance(play_by_play, pl.DataFrame)

    @pytest.mark.parametrize("game_ids", [[2017020001, 2017020002, 2017020003, 2017020004, 2017020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_rosters(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        rosters = scraper.rosters

        if backend == "pandas":
            assert isinstance(rosters, pd.DataFrame)

        if backend == "polars":
            assert isinstance(rosters, pl.DataFrame)

    @pytest.mark.parametrize("game_ids", [[2016020001, 2016020002, 2016020003, 2016020004, 2016020005]])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_shifts(self, game_ids, backend):
        scraper = Scraper(game_ids=game_ids, backend=backend)

        shifts = scraper.shifts

        if backend == "pandas":
            assert isinstance(shifts, pd.DataFrame)

        if backend == "polars":
            assert isinstance(shifts, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "period", "season"])
    @pytest.mark.parametrize("strength_state", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("teammates", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_stats(self, level, strength_state, score, teammates, opposition, backend):
        game_id = 2023020001
        scraper = Scraper(game_ids=game_id, backend=backend)
        scraper.prep_stats(
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
            disable_progress_bar=True,
        )

        stats = scraper.stats

        if backend == "pandas":
            assert isinstance(stats, pd.DataFrame)

        if backend == "polars":
            assert isinstance(stats, pl.DataFrame)

    @pytest.mark.parametrize("position", ["f", "d"])
    @pytest.mark.parametrize("level", ["game", "period", "season"])
    @pytest.mark.parametrize("strength_state", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("teammates", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_lines(self, position, level, score, strength_state, teammates, opposition, backend):
        game_id = 2023020001
        scraper = Scraper(game_ids=game_id, backend=backend)
        scraper.prep_lines(
            position=position,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
            disable_progress_bar=True,
        )

        lines = scraper.lines

        if backend == "pandas":
            assert isinstance(lines, pd.DataFrame)

        if backend == "polars":
            assert isinstance(lines, pl.DataFrame)

    @pytest.mark.parametrize("level", ["game", "period", "season"])
    @pytest.mark.parametrize("strength_state", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_team_stats(self, level, score, strength_state, opposition, backend):
        game_id = 2023020001
        scraper = Scraper(game_ids=game_id, backend=backend)
        scraper.prep_team_stats(
            level=level, score=score, strength_state=strength_state, opposition=opposition, disable_progress_bar=True
        )

        team_stats = scraper.team_stats

        if backend == "pandas":
            assert isinstance(team_stats, pd.DataFrame)

        if backend == "polars":
            assert isinstance(team_stats, pl.DataFrame)
