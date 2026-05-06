from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest
from requests.exceptions import RetryError

from chickenstats.chicken_nhl._game_utils import parse_time, prefetch_concurrent
from chickenstats.chicken_nhl.game import Game


# ---------------------------------------------------------------------------
# parse_time (module-level utility)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "time_str,expected",
    [
        ("5:30", 330),
        ("0:00", 0),
        ("20:00", 1200),
        ("", 0),  # empty string — guard path
        ("abc", 0),  # unparseable — ValueError path
        ("1:xx", 0),  # partially unparseable
    ],
)
def test_parse_time(time_str, expected):
    assert parse_time(time_str) == expected


# ---------------------------------------------------------------------------
# Representative game IDs used across all behavioral tests
#
#   2023020001 — regular season (R), modern API format     → polars default
#   2017030111 — playoff (P), 20-min OT, no shootout       → pandas
#   2010020012 — historical era, pre-lockout               → polars
#   2022020194 — regular season (R), OT game               → pandas
#                exercises period-4 R-session shift end-time branch
# ---------------------------------------------------------------------------

_BEHAVIORAL = [(2023020001, "polars"), (2017030111, "pandas"), (2010020012, "polars"), (2022020194, "pandas")]


class TestGame:
    def test_game_fail(self):
        with pytest.raises(Exception):
            Game("FAIL")

    def test_repr(self):
        game = Game(2023020001)
        r = repr(game)
        assert "Game(game_id=" in r
        assert "season=" in r
        assert "session=" in r

    def test_cached_property_is_cached(self):
        game = Game(2023020001)
        assert game.api_events is game.api_events

    # -------------------------------------------------------------------------
    # api_events + api_events_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_api_events(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        events = game.api_events
        assert isinstance(events, list) and len(events) > 0
        df = game.api_events_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2022020194,
            2022020673,
            2016020001,
            2018021187,
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
            2019020682,
            2020020456,
            2020020846,
            2020020860,
            2021020482,
            2023020838,
            2023021279,
        ],
    )
    def test_api_events_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.api_events, list) and len(game.api_events) > 0

    # -------------------------------------------------------------------------
    # api_rosters + api_rosters_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_api_rosters(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters = game.api_rosters
        assert isinstance(rosters, list) and len(rosters) > 0
        df = game.api_rosters_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2023020022,
            2016020082,
            2014020804,
            2018020310,
            2010020090,
            2023020222,
            2016020182,
            2014020814,
            2018020314,
            2010020100,
            2013020971,
        ],
    )
    def test_api_rosters_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.api_rosters, list) and len(game.api_rosters) > 0

    # -------------------------------------------------------------------------
    # changes + changes_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_changes(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        changes = game.changes
        assert isinstance(changes, list) and len(changes) > 0
        df = game.changes_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2022020092,
            2017020102,
            2020020204,
            2016020910,
            2012020070,
            2022020192,
            2017020122,
            2020020234,
            2016020911,
            2012020071,
        ],
    )
    def test_changes_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.changes, list) and len(game.changes) > 0

    # -------------------------------------------------------------------------
    # html_events + html_events_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_html_events(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        events = game.html_events
        assert isinstance(events, list) and len(events) > 0
        df = game.html_events_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
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
    def test_html_events_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.html_events, list) and len(game.html_events) > 0

    # -------------------------------------------------------------------------
    # html_rosters + html_rosters_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_html_rosters(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters = game.html_rosters
        assert isinstance(rosters, list) and len(rosters) > 0
        df = game.html_rosters_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2023020022,
            2016020082,
            2014020804,
            2018020310,
            2010020090,
            2019020665,
            2023020122,
            2016020182,
            2018020318,
            2010020098,
        ],
    )
    def test_html_rosters_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.html_rosters, list) and len(game.html_rosters) > 0

    # -------------------------------------------------------------------------
    # rosters + rosters_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_rosters(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters = game.rosters
        assert isinstance(rosters, list) and len(rosters) > 0
        df = game.rosters_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2022020032,
            2012020182,
            2017020814,
            2011020312,
            2022020091,
            2022020132,
            2012020132,
            2017020816,
            2011020342,
            2022020191,
        ],
    )
    def test_rosters_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.rosters, list) and len(game.rosters) > 0

    # -------------------------------------------------------------------------
    # shifts + shifts_df
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_shifts(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        shifts = game.shifts
        assert isinstance(shifts, list) and len(shifts) > 0
        df = game.shifts_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2023020092,
            2016020102,
            2014020204,
            2018020910,
            2010020070,
            2020020860,
            2023020292,
            2016020142,
            2014020294,
            2018020916,
            2010020170,
            2025020551,
        ],
    )
    def test_shifts_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.shifts, list) and len(game.shifts) > 0

    # -------------------------------------------------------------------------
    # play_by_play + play_by_play_ext + play_by_play_df (merged)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_play_by_play(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        assert isinstance(game.play_by_play, list) and len(game.play_by_play) > 0
        assert isinstance(game.play_by_play_ext, list) and len(game.play_by_play_ext) > 0
        df = game.play_by_play_df
        if backend == "pandas":
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id",
        [
            2011020022,
            2012020082,
            2017020804,
            2011020310,
            2012020090,
            2011020822,
            2012020382,
            2017020884,
            2011020318,
            2012020390,
        ],
    )
    def test_play_by_play_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.play_by_play, list) and len(game.play_by_play) > 0
        assert isinstance(game.play_by_play_ext, list) and len(game.play_by_play_ext) > 0

    # -------------------------------------------------------------------------
    # prefetch (merged with prefetch_caches_data)
    # -------------------------------------------------------------------------

    def test_prefetch(self):
        game = Game(2023020001)
        result = game.prefetch()
        assert result is None
        for prop in ("api_events", "api_rosters", "html_events", "html_rosters", "shifts"):
            assert prop in game.__dict__
            assert isinstance(getattr(game, prop), list)

    @pytest.mark.regression
    @pytest.mark.parametrize("game_id", [2019020684, 2016020001])
    def test_prefetch_regression(self, game_id):
        game = Game(game_id)
        game.prefetch()
        assert "api_events" in game.__dict__
        assert "html_events" in game.__dict__


class TestGameCoverage:
    """Targeted tests for error paths and edge cases via mocks."""

    def test_map_player_metadata_block_no_jersey(self):
        from chickenstats.chicken_nhl._game_utils import map_player_metadata

        event = {"event": "BLOCK", "player_1_api_id": None}
        result = map_player_metadata(event, {})
        assert result["event_team"] == "OTHER"
        assert result["player_1"] == "REFEREE"
        assert result["player_1_eh_id"] == "REFEREE"

    def test_fut_game_state_no_period_attrs(self):
        game = Game(2023020001)
        assert hasattr(game, "current_period")

    def test_prefetch_concurrent_swallows_exceptions(self):
        def failing_task():
            raise RuntimeError("simulated failure")

        prefetch_concurrent(failing_task)

    def test_prefetch_concurrent_mixed_tasks(self):
        results = []

        def good_task():
            results.append(1)

        def bad_task():
            raise ValueError("boom")

        prefetch_concurrent(good_task, bad_task)
        assert results == [1]

    def test_fetch_html_events_retry_error(self):
        game = Game(2023020001)
        game._raw_html_events = None
        mock_session = MagicMock()
        mock_session.get.side_effect = RetryError("timeout")
        game._requests_session = mock_session
        result = game._fetch_html_events()
        assert result == []
        assert game._raw_html_events == []

    def test_fetch_html_events_empty_soup(self):
        game = Game(2023020001)
        game._raw_html_events = None
        mock_response = MagicMock()
        mock_response.content = b""
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        game._requests_session = mock_session
        result = game._fetch_html_events()
        assert result == []

    def test_fetch_html_rosters_404(self):
        game = Game(2023020001)
        game._raw_html_rosters = None
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        game._requests_session = mock_session
        result = game._fetch_html_rosters()
        assert result == []
        assert game._raw_html_rosters == []

    def test_fetch_html_rosters_retry_error(self):
        game = Game(2023020001)
        game._raw_html_rosters = None
        mock_session = MagicMock()
        mock_session.get.side_effect = RetryError("connection failed")
        game._requests_session = mock_session
        result = game._fetch_html_rosters()
        assert result == []
        assert game._raw_html_rosters == []

    def test_changes_empty_shifts_returns_empty(self):
        game = Game(2023020001)
        game.__dict__["shifts"] = []
        game._raw_shifts = []
        result = game.changes
        assert result == []

    def test_shifts_empty_raw_returns_empty(self):
        game = Game(2023020001)
        game._raw_shifts = []
        with patch.object(game, "_fetch_shifts", return_value=[]):
            game.__dict__["rosters"] = []
            result = game.shifts
        assert result == []

    def test_html_events_empty_raw_returns_empty(self):
        game = Game(2023020001)
        game._raw_html_events = []
        with patch.object(game, "_fetch_html_events", return_value=[]):
            game.__dict__["rosters"] = []
            result = game.html_events
        assert result == []

    def test_changes_shootout_game_seconds(self):
        """Regular-season OT period (period 4, R) uses 3600 + time_seconds."""
        # 2023020001 is a regular season game — if it went to OT, period-4 changes
        # use 3600 base. We verify the formula is applied (game_seconds >= 3600).
        game = Game(2023020001)
        changes = game.changes
        ot_changes = [c for c in changes if c.get("period") == 4 and game.session == "R"]
        for c in ot_changes:
            assert c.get("game_seconds", 0) >= 3600
