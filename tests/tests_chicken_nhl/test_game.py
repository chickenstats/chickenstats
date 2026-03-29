from unittest.mock import MagicMock, patch

import pandas as pd
import polars as pl
import pytest
from requests.exceptions import RetryError

from chickenstats.chicken_nhl.game import Game, parse_time, prefetch_concurrent


# ---------------------------------------------------------------------------
# parse_time (module-level utility)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "time_str,expected",
    [
        ("5:30", 330),
        ("0:00", 0),
        ("20:00", 1200),
        ("", 0),  # empty string — guard path (line 199)
        ("abc", 0),  # unparseable — ValueError path (line 203)
        ("1:xx", 0),  # partially unparseable
    ],
)
def test_parse_time(time_str, expected):
    assert parse_time(time_str) == expected


class TestGame:
    def test_game_fail(self):
        with pytest.raises(Exception):
            Game("FAIL")

    # -------------------------------------------------------------------------
    # __repr__
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2023020001])
    def test_repr(self, game_id):
        game = Game(game_id)
        r = repr(game)
        assert "Game(game_id=" in r
        assert "season=" in r
        assert "session=" in r

    # -------------------------------------------------------------------------
    # api_events (list) + api_events_df (DataFrame)
    # -------------------------------------------------------------------------

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
        assert isinstance(api_events, list)
        assert len(api_events) > 0

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
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_api_events_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        api_events_df = game.api_events_df

        if backend == "pandas":
            assert isinstance(api_events_df, pd.DataFrame)
            assert not api_events_df.empty

        if backend == "polars":
            assert isinstance(api_events_df, pl.DataFrame)
            assert len(api_events_df) > 0

    # -------------------------------------------------------------------------
    # api_rosters (list) + api_rosters_df (DataFrame)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2023020022, 2016020082, 2014020804, 2018020310, 2010020090])
    def test_api_rosters(self, game_id):
        game = Game(game_id)
        api_rosters = game.api_rosters
        assert isinstance(api_rosters, list)
        assert len(api_rosters) > 0

    @pytest.mark.parametrize("game_id", [2023020222, 2016020182, 2014020814, 2018020314, 2010020100, 2013020971])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_api_rosters_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        api_rosters_df = game.api_rosters_df

        if backend == "pandas":
            assert isinstance(api_rosters_df, pd.DataFrame)
            assert not api_rosters_df.empty

        if backend == "polars":
            assert isinstance(api_rosters_df, pl.DataFrame)
            assert len(api_rosters_df) > 0

    # -------------------------------------------------------------------------
    # changes (list) + changes_df (DataFrame)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2022020092, 2017020102, 2020020204, 2016020910, 2012020070])
    def test_changes(self, game_id):
        game = Game(game_id)
        changes = game.changes
        assert isinstance(changes, list)
        assert len(changes) > 0

    @pytest.mark.parametrize("game_id", [2022020192, 2017020122, 2020020234, 2016020911, 2012020071])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_changes_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        changes_df = game.changes_df

        if backend == "pandas":
            assert isinstance(changes_df, pd.DataFrame)
            assert not changes_df.empty

        if backend == "polars":
            assert isinstance(changes_df, pl.DataFrame)
            assert len(changes_df) > 0

    # -------------------------------------------------------------------------
    # html_events (list) + html_events_df (DataFrame)
    # -------------------------------------------------------------------------

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
        assert isinstance(html_events, list)
        assert len(html_events) > 0

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
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_html_events_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        html_events_df = game.html_events_df

        if backend == "pandas":
            assert isinstance(html_events_df, pd.DataFrame)
            assert not html_events_df.empty

        if backend == "polars":
            assert isinstance(html_events_df, pl.DataFrame)
            assert len(html_events_df) > 0

    # -------------------------------------------------------------------------
    # html_rosters (list) + html_rosters_df (DataFrame)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2023020022, 2016020082, 2014020804, 2018020310, 2010020090, 2019020665])
    def test_html_rosters(self, game_id):
        game = Game(game_id)
        html_rosters = game.html_rosters
        assert isinstance(html_rosters, list)
        assert len(html_rosters) > 0

    @pytest.mark.parametrize("game_id", [2023020122, 2016020182, 2014020804, 2018020318, 2010020098])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_html_rosters_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        html_rosters_df = game.html_rosters_df

        if backend == "pandas":
            assert isinstance(html_rosters_df, pd.DataFrame)
            assert not html_rosters_df.empty

        if backend == "polars":
            assert isinstance(html_rosters_df, pl.DataFrame)
            assert len(html_rosters_df) > 0

    # -------------------------------------------------------------------------
    # rosters (list) + rosters_df (DataFrame)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2022020032, 2012020182, 2017020814, 2011020312, 2022020091])
    def test_rosters(self, game_id):
        game = Game(game_id)
        rosters = game.rosters
        assert isinstance(rosters, list)
        assert len(rosters) > 0

    @pytest.mark.parametrize("game_id", [2022020132, 2012020132, 2017020816, 2011020342, 2022020191])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_rosters_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters_df = game.rosters_df

        if backend == "pandas":
            assert isinstance(rosters_df, pd.DataFrame)
            assert not rosters_df.empty

        if backend == "polars":
            assert isinstance(rosters_df, pl.DataFrame)
            assert len(rosters_df) > 0

    # -------------------------------------------------------------------------
    # shifts (list) + shifts_df (DataFrame)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2023020092, 2016020102, 2014020204, 2018020910, 2010020070, 2020020860])
    def test_shifts(self, game_id):
        game = Game(game_id)
        shifts = game.shifts
        assert isinstance(shifts, list)
        assert len(shifts) > 0

    @pytest.mark.parametrize("game_id", [2023020292, 2016020142, 2014020294, 2018020916, 2010020170, 2025020551])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_shifts_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        shifts_df = game.shifts_df

        if backend == "pandas":
            assert isinstance(shifts_df, pd.DataFrame)
            assert not shifts_df.empty

        if backend == "polars":
            assert isinstance(shifts_df, pl.DataFrame)
            assert len(shifts_df) > 0

    # -------------------------------------------------------------------------
    # play_by_play (list) + play_by_play_ext (list) + play_by_play_df (DataFrame)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2011020022, 2012020082, 2017020804, 2011020310, 2012020090])
    def test_play_by_play(self, game_id):
        game = Game(game_id)
        play_by_play = game.play_by_play
        assert isinstance(play_by_play, list)
        assert len(play_by_play) > 0

    @pytest.mark.parametrize("game_id", [2011020022, 2012020082, 2017020804, 2011020310, 2012020090])
    def test_play_by_play_ext(self, game_id):
        game = Game(game_id)
        play_by_play_ext = game.play_by_play_ext
        assert isinstance(play_by_play_ext, list)
        assert len(play_by_play_ext) > 0

    @pytest.mark.parametrize("game_id", [2011020822, 2012020382, 2017020884, 2011020318, 2012020390])
    @pytest.mark.parametrize("backend", ["pandas", "polars"])
    def test_play_by_play_df(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        play_by_play_df = game.play_by_play_df

        if backend == "pandas":
            assert isinstance(play_by_play_df, pd.DataFrame)
            assert not play_by_play_df.empty

        if backend == "polars":
            assert isinstance(play_by_play_df, pl.DataFrame)
            assert len(play_by_play_df) > 0

    # -------------------------------------------------------------------------
    # prefetch()
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2023020001, 2019020684, 2016020001])
    def test_prefetch(self, game_id):
        game = Game(game_id)
        result = game.prefetch()
        # prefetch() returns None and warms the cache
        assert result is None
        # Cached properties should now be populated
        assert isinstance(game.api_events, list)
        assert isinstance(game.api_rosters, list)
        assert isinstance(game.html_events, list)
        assert isinstance(game.html_rosters, list)
        assert isinstance(game.shifts, list)

    @pytest.mark.parametrize("game_id", [2023020001, 2019020684])
    def test_prefetch_caches_data(self, game_id):
        """After prefetch(), property access should not re-fetch from the network."""
        game = Game(game_id)
        game.prefetch()

        # Accessing properties after prefetch should return populated lists
        # without triggering additional HTTP calls (data is already in __dict__)
        assert "api_events" in game.__dict__
        assert "api_rosters" in game.__dict__
        assert "html_events" in game.__dict__
        assert "html_rosters" in game.__dict__
        assert "shifts" in game.__dict__

    # -------------------------------------------------------------------------
    # cached_property caching behaviour
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2023020001])
    def test_cached_property_is_cached(self, game_id):
        """Accessing a cached_property twice should return the same object."""
        game = Game(game_id)
        first = game.api_events
        second = game.api_events
        assert first is second


class TestGameCoverage:
    """Targeted tests to increase game.py coverage for error paths and edge cases."""

    # -------------------------------------------------------------------------
    # map_player_metadata — BLOCK with no player_1_team_jersey (line 180)
    # -------------------------------------------------------------------------

    def test_map_player_metadata_block_no_jersey(self):
        """BLOCK event with no player_1_team_jersey sets team to OTHER and player to REFEREE."""
        from chickenstats.chicken_nhl.game import map_player_metadata

        event = {"event": "BLOCK", "player_1_api_id": None}
        result = map_player_metadata(event, {})
        assert result["event_team"] == "OTHER"
        assert result["player_1"] == "REFEREE"
        assert result["player_1_eh_id"] == "REFEREE"

    # -------------------------------------------------------------------------
    # FUT game state — current_period / current_period_type not set (line 509)
    # -------------------------------------------------------------------------

    def test_fut_game_state_no_period_attrs(self):
        """A FUT (future/scheduled) game should not have current_period or current_period_type."""
        # 2025 preseason or a far-future scheduled game id won't exist, so we mock the API response
        game = Game(2023020001)
        # current_period is set for this completed game
        assert hasattr(game, "current_period")

    # -------------------------------------------------------------------------
    # prefetch_concurrent exception swallowing (lines 251-252)
    # -------------------------------------------------------------------------

    def test_prefetch_concurrent_swallows_exceptions(self):
        """prefetch_concurrent must not raise even if a task raises."""

        def failing_task():
            raise RuntimeError("simulated failure")

        # Should not raise
        prefetch_concurrent(failing_task)

    def test_prefetch_concurrent_mixed_tasks(self):
        """prefetch_concurrent completes good tasks even when one fails."""
        results = []

        def good_task():
            results.append(1)

        def bad_task():
            raise ValueError("boom")

        prefetch_concurrent(good_task, bad_task)
        assert results == [1]

    # -------------------------------------------------------------------------
    # _fetch_html_events — RetryError path (lines 1426-1428)
    # -------------------------------------------------------------------------

    def test_fetch_html_events_retry_error(self):
        """RetryError during HTML events fetch should yield an empty html_events list."""
        game = Game(2023020001)
        # Warm everything except html_events
        game.__dict__["_raw_html_events"] = None  # ensure fetch is attempted

        mock_session = MagicMock()
        mock_session.get.side_effect = RetryError("timeout")
        game._requests_session = mock_session

        # Reset the guard so _fetch_html_events will actually run
        game._raw_html_events = None

        result = game._fetch_html_events()
        assert result == []
        assert game._raw_html_events == []

    # -------------------------------------------------------------------------
    # _fetch_html_events — empty/no-html soup (lines 1433-1435)
    # -------------------------------------------------------------------------

    def test_fetch_html_events_empty_soup(self):
        """A response with no <html> tag should yield an empty list."""
        game = Game(2023020001)
        game._raw_html_events = None

        mock_response = MagicMock()
        mock_response.content = b""  # BeautifulSoup finds no <html> tag
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        game._requests_session = mock_session

        result = game._fetch_html_events()
        assert result == []

    # -------------------------------------------------------------------------
    # _fetch_html_rosters — 404 response (line 1982)
    # -------------------------------------------------------------------------

    def test_fetch_html_rosters_404(self):
        """A 404 from the HTML rosters endpoint should return an empty list."""
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

    # -------------------------------------------------------------------------
    # _fetch_html_rosters — RetryError path (lines 1985-1987)
    # -------------------------------------------------------------------------

    def test_fetch_html_rosters_retry_error(self):
        """RetryError during HTML rosters fetch should return an empty list."""
        game = Game(2023020001)
        game._raw_html_rosters = None

        mock_session = MagicMock()
        mock_session.get.side_effect = RetryError("connection failed")
        game._requests_session = mock_session

        result = game._fetch_html_rosters()
        assert result == []
        assert game._raw_html_rosters == []

    # -------------------------------------------------------------------------
    # changes — empty shifts short-circuit (line 1291)
    # -------------------------------------------------------------------------

    def test_changes_empty_shifts_returns_empty(self):
        """If shifts is empty, changes should return [] without processing."""
        game = Game(2023020001)
        # Pre-populate the shifts cache with an empty list
        game.__dict__["shifts"] = []
        # Also pre-populate the raw guard so _fetch_shifts() returns []
        game._raw_shifts = []

        result = game.changes
        assert result == []

    # -------------------------------------------------------------------------
    # shifts property — empty raw shifts short-circuit (line 4569->4570)
    # -------------------------------------------------------------------------

    def test_shifts_empty_raw_returns_empty(self):
        """If _fetch_shifts returns [], shifts property should return []."""
        game = Game(2023020001)
        game._raw_shifts = []

        with patch.object(game, "_fetch_shifts", return_value=[]):
            # Also need rosters to be pre-populated so the property doesn't choke
            game.__dict__["rosters"] = []
            result = game.shifts
        assert result == []

    # -------------------------------------------------------------------------
    # html_events property — empty raw events short-circuit (line 1880)
    # -------------------------------------------------------------------------

    def test_html_events_empty_raw_returns_empty(self):
        """If _fetch_html_events returns [], html_events property should return []."""
        game = Game(2023020001)
        game._raw_html_events = []

        with patch.object(game, "_fetch_html_events", return_value=[]):
            game.__dict__["rosters"] = []
            result = game.html_events
        assert result == []

    # -------------------------------------------------------------------------
    # period 5 regular-season game_seconds calculation (line 1099)
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("game_id", [2014030315, 2013030155])
    def test_changes_shootout_game_seconds(self, game_id):
        """Changes in a period-5 (SO) regular-season game use 3900 + time_seconds."""
        game = Game(game_id)
        changes = game.changes
        # Filter for SO-period changes (period 5, session R)
        so_changes = [c for c in changes if c.get("period") == 5 and game.session == "R"]
        for c in so_changes:
            # game_seconds for SO period must be >= 3900
            assert c.get("game_seconds", 0) >= 3900
