import pandas as pd

from chickenstats.chicken_nhl.scrape import Game, Season, Scraper
import pytest


class TestGame:
    @pytest.mark.parametrize(
        "game_id",
        [
            2023020001,
            2022020194,
            2022020673,
            2010020012,
            2016020001,
            2018021187,
            2017030111,
            2010021176,
            2011020069,
            2012020095,
            2012020341,
            2012020627,
            2012020660,
            2012020671,
            2012030224,
            2013020305,
            2013030142,
            2013030155,
            2013020445,
            2014020120,
            2014020356,
            2014020417,
            2014020506,
            2014020939,
            2014020945,
            2014021127,
            2014021128,
            2014021203,
            2014030311,
            2014030315,
            2015020193,
            2015020401,
            2015020839,
            2015020917,
            2015021092,
            2016020049,
            2016020177,
            2016020256,
            2016020326,
            2016020433,
            2016020519,
            2016020625,
            2016020883,
            2016020963,
            2016021111,
            2016021165,
        ],
    )
    def test_api_events(self, game_id):
        game = Game(game_id)

        api_events = game.api_events
        assert isinstance(api_events, list) is True

    def test_game_fail(self):
        game_id = "FAIL"

        with pytest.raises(Exception):
            Game(game_id)

    @pytest.mark.parametrize(
        "game_id",
        [
            2016030216,
            2017020033,
            2017020096,
            2017020209,
            2017020233,
            2017020548,
            2017020601,
            2017020615,
            2017020796,
            2017020835,
            2017020836,
            2017021136,
            2017021161,
            2018020006,
            2018020009,
            2018020049,
            2018020115,
            2018020122,
            2018020153,
            2018020211,
            2018020309,
            2018020363,
            2018020519,
            2018020561,
            2018020752,
            2018020794,
            2018020795,
            2018020841,
            2018020969,
            2018021087,
            2018021124,
            2018021171,
            2019020006,
            2019020136,
            2019020147,
            2019020179,
            2019020239,
            2019020316,
            2020020456,
            2019020682,
            2020020846,
            2020020860,
            2021020482,
            2023020838,
            2023021279,
        ],
    )
    def test_api_events_df(self, game_id):
        game = Game(game_id)

        api_events_df = game.api_events_df
        assert isinstance(api_events_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id", [2023020022, 2016020082, 2014020804, 2018020310, 2010020090]
    )
    def test_api_rosters(self, game_id):
        game = Game(game_id)

        api_rosters = game.api_rosters
        assert isinstance(api_rosters, list) is True

    @pytest.mark.parametrize(
        "game_id",
        [2023020222, 2016020182, 2014020814, 2018020314, 2010020100, 2013020971],
    )
    def test_api_rosters_df(self, game_id):
        game = Game(game_id)

        api_rosters_df = game.api_rosters_df
        assert isinstance(api_rosters_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id", [2022020092, 2017020102, 2020020204, 2016020910, 2012020070]
    )
    def test_changes(self, game_id):
        game = Game(game_id)

        changes = game.changes
        assert isinstance(changes, list) is True

    @pytest.mark.parametrize(
        "game_id", [2022020192, 2017020122, 2020020234, 2016020911, 2012020071]
    )
    def test_changes_df(self, game_id):
        game = Game(game_id)

        changes_df = game.changes_df
        assert isinstance(changes_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id",
        [
            2023020001,
            2016020002,
            2014020004,
            2018020010,
            2010020022,
            2022030111,
            2019020127,
            2011020069,
            2011020553,
            2012020660,
            2012020018,
            2013020083,
            2013020274,
            2013020644,
            2013020971,
            2014020120,
            2014020600,
            2014020672,
            2014021118,
            2015020193,
        ],
    )
    def test_html_events(self, game_id):
        game = Game(game_id)

        html_events = game.html_events
        assert isinstance(html_events, list) is True

    # Change game IDs
    @pytest.mark.parametrize(
        "game_id",
        [
            2015020904,
            2015020917,
            2016020256,
            2016020625,
            2016021070,
            2016021127,
            2017020463,
            2017020796,
            2018020009,
            2018020989,
            2017021161,
            2018020363,
            2018021087,
            2018021133,
            2019020179,
            2019020316,
            2021020224,
        ],
    )
    def test_html_events_df(self, game_id):
        game = Game(game_id)

        html_events_df = game.html_events_df
        assert isinstance(html_events_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id",
        [2023020022, 2016020082, 2014020804, 2018020310, 2010020090, 2019020665],
    )
    def test_html_rosters(self, game_id):
        game = Game(game_id)

        html_rosters = game.html_rosters
        assert isinstance(html_rosters, list) is True

    @pytest.mark.parametrize(
        "game_id", [2023020122, 2016020182, 2014020804, 2018020318, 2010020098]
    )
    def test_html_rosters_df(self, game_id):
        game = Game(game_id)

        html_rosters_df = game.html_rosters_df
        assert isinstance(html_rosters_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id", [2011020022, 2012020082, 2017020804, 2011020310, 2012020090]
    )
    def test_play_by_play(self, game_id):
        game = Game(game_id)

        play_by_play = game.play_by_play
        assert isinstance(play_by_play, list) is True

    # Change game IDs
    @pytest.mark.parametrize(
        "game_id", [2011020822, 2012020382, 2017020884, 2011020318, 2012020390]
    )
    def test_play_by_play_df(self, game_id):
        game = Game(game_id)

        play_by_play_df = game.play_by_play_df
        assert isinstance(play_by_play_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id", [2022020032, 2012020182, 2017020814, 2011020312, 2022020091]
    )
    def test_rosters(self, game_id):
        game = Game(game_id)

        rosters = game.rosters
        assert isinstance(rosters, list) is True

    @pytest.mark.parametrize(
        "game_id", [2022020132, 2012020132, 2017020816, 2011020342, 2022020191]
    )
    def test_rosters_df(self, game_id):
        game = Game(game_id)

        rosters_df = game.rosters_df
        assert isinstance(rosters_df, pd.DataFrame) is True

    @pytest.mark.parametrize(
        "game_id",
        [2023020092, 2016020102, 2014020204, 2018020910, 2010020070, 2020020860],
    )
    def test_shifts(self, game_id):
        game = Game(game_id)

        shifts = game.shifts
        assert isinstance(shifts, list) is True

    @pytest.mark.parametrize(
        "game_id", [2023020292, 2016020142, 2014020294, 2018020916, 2010020170]
    )
    def test_shifts_df(self, game_id):
        game = Game(game_id)

        shifts_df = game.shifts_df
        assert isinstance(shifts_df, pd.DataFrame) is True


class TestScraper:
    @pytest.mark.parametrize(
        "game_ids", [[2023020001, 2023020002, 2023020003, 2023020004, 2023020005]]
    )
    def test_api_events(self, game_ids):
        scraper = Scraper(game_ids)

        api_events = scraper.api_events

        assert isinstance(api_events, pd.DataFrame)

    @pytest.mark.parametrize(
        "game_ids", [[2022020001, 2022020002, 2022020003, 2022020004, 2022020005]]
    )
    def test_api_rosters(self, game_ids):
        scraper = Scraper(game_ids)

        api_rosters = scraper.api_rosters

        assert isinstance(api_rosters, pd.DataFrame)

    @pytest.mark.parametrize(
        "game_ids", [[2021020001, 2021020002, 2021020003, 2021020004, 2021020005]]
    )
    def test_changes(self, game_ids):
        scraper = Scraper(game_ids)

        changes = scraper.changes

        assert isinstance(changes, pd.DataFrame)

    @pytest.mark.parametrize(
        "game_ids", [[2020020001, 2020020002, 2020020003, 2020020004, 2020020005]]
    )
    def test_html_events(self, game_ids):
        scraper = Scraper(game_ids)

        html_events = scraper.html_events

        assert isinstance(html_events, pd.DataFrame)

    @pytest.mark.parametrize(
        "game_ids", [[2019020001, 2019020002, 2019020003, 2019020004, 2019020005]]
    )
    def test_html_rosters(self, game_ids):
        scraper = Scraper(game_ids)

        html_rosters = scraper.html_rosters

        assert isinstance(html_rosters, pd.DataFrame)

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
    def test_play_by_play(self, game_ids):
        scraper = Scraper(game_ids)

        play_by_play = scraper.play_by_play

        assert isinstance(play_by_play, pd.DataFrame)

    @pytest.mark.parametrize(
        "game_ids", [[2017020001, 2017020002, 2017020003, 2017020004, 2017020005]]
    )
    def test_rosters(self, game_ids):
        scraper = Scraper(game_ids)

        rosters = scraper.rosters

        assert isinstance(rosters, pd.DataFrame)

    @pytest.mark.parametrize(
        "game_ids", [[2016020001, 2016020002, 2016020003, 2016020004, 2016020005]]
    )
    def test_shifts(self, game_ids):
        scraper = Scraper(game_ids)

        shifts = scraper.shifts

        assert isinstance(shifts, pd.DataFrame)

    @pytest.mark.parametrize("level", ["game", "period", "season"])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("teammates", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    def test_stats(self, level, score, teammates, opposition):
        game_id = 2023020001
        scraper = Scraper(game_id)
        scraper.prep_stats(
            level=level,
            score=score,
            teammates=teammates,
            opposition=opposition,
            disable_progress_bar=True,
        )

        stats = scraper.stats

        assert isinstance(stats, pd.DataFrame) is True

    @pytest.mark.parametrize("position", ["F", "D"])
    @pytest.mark.parametrize("level", ["game", "period", "season"])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("teammates", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    def test_lines(self, position, level, score, teammates, opposition):
        game_id = 2023020001
        scraper = Scraper(game_id)
        scraper.prep_lines(
            position=position,
            level=level,
            score=score,
            teammates=teammates,
            opposition=opposition,
            disable_progress_bar=True,
        )

        lines = scraper.lines

        assert isinstance(lines, pd.DataFrame) is True

    @pytest.mark.parametrize("level", ["game", "period", "season"])
    @pytest.mark.parametrize("strengths", [True, False])
    @pytest.mark.parametrize("score", [True, False])
    @pytest.mark.parametrize("opposition", [True, False])
    def test_team_stats(self, level, score, strengths, opposition):
        game_id = 2023020001
        scraper = Scraper(game_id)
        scraper.prep_team_stats(
            level=level,
            score=score,
            strengths=strengths,
            opposition=opposition,
            disable_progress_bar=True,
        )

        team_stats = scraper.team_stats

        assert isinstance(team_stats, pd.DataFrame) is True


class TestSeason:
    @pytest.mark.parametrize(
        "year", [2023, 20232024, 1917, 1942, 1967, 1982, 1991, 2011]
    )
    def test_schedule(self, year):
        season = Season(year)

        schedule = season.schedule()

        assert isinstance(schedule, pd.DataFrame)

    def test_schedule_nashville(self):
        season = Season(2023)

        schedule = season.schedule("NSH")

        assert isinstance(schedule, pd.DataFrame)

        schedule = season.schedule("TBL")

        assert isinstance(schedule, pd.DataFrame)

    def test_season_fail(self):
        with pytest.raises(Exception):
            Season(2030)

    def test_standings(self):
        season = Season(2023)
        standings = season.standings

        assert isinstance(standings, pd.DataFrame) is True
