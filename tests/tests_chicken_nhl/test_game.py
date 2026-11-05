import re
import warnings
from unittest.mock import MagicMock, patch

import numpy as np
import polars as pl
import pytest
from invariants import REGRESSION_GAME_IDS
from requests.exceptions import RetryError

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl._game_html_events import _GameHTMLEventsMixin
from chickenstats.chicken_nhl._game_utils import parse_time, prefetch_concurrent
from chickenstats.chicken_nhl.game import Game
from chickenstats.exceptions import InvalidGameIDError, InvalidInputError, UnsupportedBackendError


# -----------------------------------------------------------------------------
# parse_time (module-level utility)
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# Representative game IDs used across all behavioral tests
#
#   2023020001 — regular season (R), modern API format     → polars default
#   2017030111 — playoff (P), 20-min OT, no shootout       → pandas
#   2010020012 — historical era, pre-lockout               → polars
#   2022020194 — regular season (R), OT game               → pandas
#                exercises period-4 R-session shift end-time branch
# -----------------------------------------------------------------------------

_skip_no_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
_BEHAVIORAL = [
    (2023020001, "polars"),
    pytest.param(2017030111, "pandas", marks=_skip_no_pandas),
    (2010020012, "polars"),
    pytest.param(2022020194, "pandas", marks=_skip_no_pandas),
]


class TestGame:
    def test_game_fail(self):
        with pytest.raises(InvalidGameIDError):
            Game("FAIL")

    @pytest.mark.parametrize(
        "game_id", [2023020001, "2023020001", " 2023020001 ", 2023020001.0, "2023020001.0", np.int64(2023020001)]
    )
    def test_game_id_forms(self, game_id):
        game = Game(game_id)

        assert game.game_id == 2023020001
        assert game.html_id == "020001"

    @pytest.mark.parametrize(
        "game_id",
        [True, False, np.True_, None, 2023, 20230200011, -202302000, 2023020001.5, float("nan"), float("inf")],
    )
    def test_a_bad_game_id_raises(self, game_id):
        with pytest.raises(InvalidGameIDError) as caught:
            Game(game_id)

        assert caught.value.game_id is game_id

    def test_an_unknown_session_names_the_code(self):
        with pytest.raises(InvalidGameIDError, match="unknown session code '09'") as caught:
            Game(2023090001)

        assert isinstance(caught.value, InvalidInputError)

    def test_a_bad_backend_raises(self):
        with pytest.raises(UnsupportedBackendError):
            Game(2023020001, backend="dask")  # ty: ignore[no-matching-overload]

    def test_warns_before_the_first_supported_season(self):
        with pytest.warns(UserWarning, match="Game 2006020001 is from before 2007-08"):
            Game(2006020001)

    def test_a_supported_season_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Game(2010020001)

    def test_repr(self):
        game = Game(2023020001)
        r = repr(game)
        assert "Game(game_id=" in r
        assert "season=" in r
        assert "session=" in r

    def test_cached_property_is_cached(self):
        game = Game(2023020001)
        assert game.api_events is game.api_events

    # -----------------------------------------------------------------------------
    # api_events + api_events_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_api_events(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        events = game.api_events
        assert isinstance(events, list) and len(events) > 0
        df = game.api_events_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
    @pytest.mark.regression
    @pytest.mark.parametrize("game_id", REGRESSION_GAME_IDS)
    def test_api_events_regression(self, game_id):
        game = Game(game_id)
        assert isinstance(game.api_events, list) and len(game.api_events) > 0

    @pytest.mark.nhl
    @pytest.mark.regression
    @pytest.mark.parametrize(
        "game_id,event_idx,player,coords",
        [(2016021165, 84, "ZDENO CHARA", (75, -1)), (2012020671, 618, "STEVE EMINGER", (-8, 42))],
    )
    def test_event_matches_the_api_event_it_agrees_with(self, game_id, event_idx, player, coords):
        event = next(event for event in Game(game_id).play_by_play if event["event_idx"] == event_idx)
        assert player in (event["player_1"], event["player_2"])
        assert (event["coords_x"], event["coords_y"]) == coords

    # -----------------------------------------------------------------------------
    # api_rosters + api_rosters_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_api_rosters(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters = game.api_rosters
        assert isinstance(rosters, list) and len(rosters) > 0
        df = game.api_rosters_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    # -----------------------------------------------------------------------------
    # changes + changes_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_changes(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        changes = game.changes
        assert isinstance(changes, list) and len(changes) > 0
        df = game.changes_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    # -----------------------------------------------------------------------------
    # html_events + html_events_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_html_events(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        events = game.html_events
        assert isinstance(events, list) and len(events) > 0
        df = game.html_events_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    # -----------------------------------------------------------------------------
    # html_rosters + html_rosters_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_html_rosters(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters = game.html_rosters
        assert isinstance(rosters, list) and len(rosters) > 0
        df = game.html_rosters_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    # -----------------------------------------------------------------------------
    # rosters + rosters_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_rosters(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        rosters = game.rosters
        assert isinstance(rosters, list) and len(rosters) > 0
        df = game.rosters_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    @pytest.mark.nhl
    @pytest.mark.regression
    def test_a_scratch_added_to_the_api_roster_has_one_row(self):
        horton = [player for player in Game(2013020971).rosters if player["team_jersey"] == "CBJ8"]
        assert [(player["player_name"], player["api_id"]) for player in horton] == [("NATHAN HORTON", 8470596)]

    # -----------------------------------------------------------------------------
    # shifts + shifts_df
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_shifts(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        shifts = game.shifts
        assert isinstance(shifts, list) and len(shifts) > 0
        df = game.shifts_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    # -----------------------------------------------------------------------------
    # play_by_play + play_by_play_ext + play_by_play_df (merged)
    # -----------------------------------------------------------------------------

    @pytest.mark.nhl
    @pytest.mark.parametrize("game_id,backend", _BEHAVIORAL)
    def test_play_by_play(self, game_id, backend):
        game = Game(game_id=game_id, backend=backend)
        assert isinstance(game.play_by_play, list) and len(game.play_by_play) > 0
        assert isinstance(game.play_by_play_ext, list) and len(game.play_by_play_ext) > 0
        df = game.play_by_play_df
        if backend == "pandas" and HAS_PANDAS:
            assert isinstance(df, pd.DataFrame) and not df.empty
        else:
            assert isinstance(df, pl.DataFrame) and len(df) > 0

    @pytest.mark.nhl
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

    # -----------------------------------------------------------------------------
    # prefetch (merged with prefetch_caches_data)
    # -----------------------------------------------------------------------------

    def test_prefetch(self):
        game = Game(2023020001)
        result = game.prefetch()
        assert result is None
        for prop in ("api_events", "api_rosters", "html_events", "html_rosters", "shifts"):
            assert prop in game.__dict__
            assert isinstance(getattr(game, prop), list)

    @pytest.mark.nhl
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

    def test_current_period_is_set_when_the_api_response_loads(self):
        game = Game(2023020001)
        assert game.current_period == 0

        _ = game.api_events
        assert (game.current_period, game.current_period_type) == (3, "REG")

    def test_prefetch_concurrent_swallows_exceptions(self, caplog):
        """A failing prefetch task must not raise, and must be logged at WARNING (not DEBUG)
        so a persistently failing prefetch is visible without enabling debug logging."""

        def failing_task():
            raise RuntimeError("simulated failure")

        with caplog.at_level("WARNING"):
            prefetch_concurrent(failing_task)

        assert any(
            record.levelname == "WARNING" and "Prefetch task failed" in record.message for record in caplog.records
        )

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

    def test_munge_shifts_period_5_shootout_no_crash(self):
        """A broken shift clock in period >= 5 (e.g. a regular-season shootout) must not raise
        UnboundLocalError. Previously only `period < 4 or session == "P"` and
        `period == 4 and session == "R"` were handled, leaving period >= 5 with no fix values
        assigned. It should now get the same 5-minute-period fix period == 4 gets, since both
        are non-playoff periods past regulation.
        """
        game = Game(2023020001)  # session == "R"
        assert game.session == "R"

        shift = {
            "season": game.season,
            "session": game.session,
            "game_id": game.game_id,
            "team": "NSH",
            "team_name": "Nashville Predators",
            "team_jersey": "NSH9999",
            "team_venue": "HOME",
            "player_name": "TEST PLAYER",
            "jersey": 99,
            "shift_count": 1,
            "start_time": "0:00",
            "end_time": "0:00",
            "duration": "0:10",
            "shift_start": "0:00 / 20:00",
            "period": 5,
            "shift_end": "0:00 / 0:00",
        }
        actives = {"NSH9999": {"eh_id": "TEST.PLAYER", "api_id": 1, "position": "L", "team_venue": "HOME"}}

        result = game._munge_shifts([shift], actives, {})

        assert len(result) == 1
        assert result[0]["end_time"] == "5:00"
        assert result[0]["end_time_seconds"] == 300
        assert result[0]["shift_end"] == "5:00 / 0:00"

    def test_munge_shifts_repairs_a_0_00_end_as_end_minus_start(self):
        """A '0:00 / 0:00' end runs to the period's end, so the duration is that minus the start (R126)."""
        game = Game(2023020001)
        shift = {
            "season": game.season,
            "session": game.session,
            "game_id": game.game_id,
            "team": "NSH",
            "team_name": "Nashville Predators",
            "team_jersey": "NSH9999",
            "team_venue": "HOME",
            "player_name": "TEST PLAYER",
            "jersey": 99,
            "shift_count": 1,
            "start_time": "19:15",
            "end_time": "0:00",
            "duration": "0:30",
            "shift_start": "19:15 / 0:45",
            "period": 2,
            "shift_end": "0:00 / 0:00",
        }
        actives = {"NSH9999": {"eh_id": "TEST.PLAYER", "api_id": 1, "position": "L", "team_venue": "HOME"}}

        result = game._munge_shifts([shift], actives, {})

        assert (result[0]["end_time_seconds"], result[0]["duration_seconds"], result[0]["duration"]) == (
            1200,
            45,
            "00:45",
        )

    @pytest.mark.parametrize(("game_id", "length", "end"), [(2024190001, 600, "10:00"), (2024200007, 1200, "20:00")])
    def test_munge_shifts_keeps_a_4_nations_overtime_length(self, game_id, length, end):
        """A 4 Nations round-robin overtime was 10 minutes and the final's 20, not the NHL's 5 (bA-08)."""
        game = Game(game_id)
        shift = {
            "season": game.season,
            "session": game.session,
            "game_id": game.game_id,
            "team": "CAN",
            "team_name": "CANADA",
            "team_jersey": "CAN99",
            "team_venue": "HOME",
            "player_name": "TEST PLAYER",
            "jersey": 99,
            "shift_count": 1,
            "start_time": "0:00",
            "end_time": "0:00",
            "duration": "0:10",
            "shift_start": "0:00 / 0:00",
            "period": 4,
            "shift_end": "0:00 / 0:00",
        }
        actives = {"CAN99": {"eh_id": "TEST.PLAYER", "api_id": 1, "position": "L", "team_venue": "HOME"}}

        result = game._munge_shifts([shift], actives, {})

        assert (result[0]["end_time_seconds"], result[0]["end_time"]) == (length, end)

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

    def test_html_events_empty_raw_returns_empty_while_the_game_is_played(self):
        """An official game with no events fails instead (test_a_finished_game_whose_report_has_no_rows_fails)."""
        game = Game(2023020001)
        game._raw_html_events = []
        game.game_state = "LIVE"
        with patch.object(game, "_fetch_api_data"), patch.object(game, "_fetch_html_events", return_value=[]):
            game.__dict__["rosters"] = []
            result = game.html_events
        assert result == []


@pytest.mark.parametrize(("game_id", "session"), [(2024190001, "FO"), (2024200007, "FO"), (2023020001, "R")])
def test_four_nations_game_ids_are_their_own_session(game_id, session):
    """The 4 Nations Face-Off games are game type 19 and their final game type 20 (N89)."""
    assert Game(game_id).session == session


@pytest.mark.parametrize(
    ("game_id", "overtime", "shootout_seconds"),
    [
        (2023010001, 300, 3900),
        (2023020001, 300, 3900),
        (2023030111, 1200, 4800),
        (2024190001, 600, 4200),
        (2024200007, 1200, 4800),
    ],
)
def test_one_game_clock_for_every_game_type(game_id, overtime, shootout_seconds):
    """Overtime length and the shootout's place on the game clock come from the game type alone (bA-08, hk-03)."""
    from chickenstats.chicken_nhl._game_utils import game_seconds, overtime_seconds, period_length

    assert (overtime_seconds(game_id), Game(game_id)._overtime) == (overtime, overtime)
    assert (period_length(3, overtime), period_length(4, overtime)) == (1200, overtime)
    assert game_seconds(5, 0, overtime) == shootout_seconds


def test_teammates_with_the_same_name_keep_their_own_shifts():
    """The shift parser keyed players by a name-derived ID, so a second player with the same name took over the
    first one's entry and the first lost every shift (bA-12)."""
    game = Game(2023020001)
    response = game._requests_session.get(game.home_shifts_endpoint)
    html = response.content.decode("utf-8")
    response._content = html.replace("11 GLENDENING, LUKE", "11 POINT, BRAYDEN").encode()

    shifts = game._parse_team_shifts("HOME", response)
    by_jersey = {jersey: sum(1 for s in shifts if s["jersey"] == jersey) for jersey in (11, 21)}

    assert "11 POINT, BRAYDEN" in response.content.decode("utf-8")
    assert by_jersey[11] > 0 and by_jersey[21] > 0


def test_a_line_change_in_a_shootout_sorts_first_in_its_second():
    """Shootout rows sort by report index and a line change has none, so a change in the shootout period
    compared None with an int and the merge raised (R127)."""
    game = Game(2023020125)
    change = dict(game.changes[0], period=5, period_seconds=0)
    changes = [dict(c) for c in game.changes] + [change]

    def shootout_rows(changes):
        merged = game._merge_pbp_events(game.html_events, game.api_events, changes, game.rosters)
        return [event["event"] for event in merged if event["period"] == 5]

    without_change = shootout_rows([dict(c) for c in game.changes])

    assert shootout_rows(changes) == ["CHANGE", *without_change]
    assert without_change[0] == "PSTR"


def test_every_shift_duration_is_written_like_the_report(fixture_game):
    durations = fixture_game.shifts["duration"].to_list()

    assert all(len(duration) == 5 and duration[2] == ":" for duration in durations)


class TestOlderSeasons:
    """Games from before 2010-11, where the NHL API has few plays and no coordinates. Game 2007020083 is saved."""

    GAME_ID = 2007020083
    ESPN = "chickenstats.chicken_nhl._game_pbp.espn_coordinates"

    def test_a_2007_08_shot_has_its_shooter(self, espn_coordinates_game):
        shots = espn_coordinates_game.play_by_play.filter(pl.col("event") == "SHOT")

        assert shots.height > 40
        assert shots["description"].str.contains("#").sum() == 0
        assert shots["player_1"].null_count() == 0

    def test_espn_fills_in_the_coordinates(self, espn_coordinates_game):
        plays = espn_coordinates_game.play_by_play.filter(pl.col("event").is_in(["SHOT", "MISS"]), pl.col("period") < 5)

        assert plays.height > 50
        # An event that ties with another at one second and cannot be told apart gets nothing, not a guess
        assert plays["coords_x"].null_count() < 5
        assert plays["event_distance"].null_count() == plays["coords_x"].null_count()

    def test_a_shootout_is_recognized_without_api_events(self):
        game = Game(self.GAME_ID)
        game._fetch_api_data()
        assert game.api_response is not None
        game.api_response["plays"] = []

        plays = game.play_by_play

        assert game.api_events == []
        assert sum(play["shootout_attempt"] for play in plays) > 0

    def test_a_failed_espn_response_does_not_fail_the_game(self):
        with patch(self.ESPN, return_value={}) as espn:
            plays = Game(self.GAME_ID).play_by_play

        assert espn.call_count == 1
        assert len(plays) > 0
        assert all(play["coords_x"] is None for play in plays if play["event"] == "SHOT")

    def test_coordinates_from_the_api_are_kept(self):
        game = Game(self.GAME_ID)
        goals = [event for event in game.html_events if event["event"] == "GOAL"]
        game.__dict__["_espn_coordinates"] = {goal["event_idx"]: {"coords_x": 99, "coords_y": 99} for goal in goals}
        api_events = [dict(event, coords_x=1, coords_y=2) for event in game.api_events]

        merged = game._merge_pbp_events(goals, api_events, [], game.rosters)
        matched = [event for event in merged if event.get("event_idx_api") is not None]

        assert matched
        assert {(event["coords_x"], event["coords_y"]) for event in matched} == {(1, 2)}

    def test_the_report_decides_the_player_when_the_api_disagrees(self):
        """An assist the API credits to someone else must not pair one player's name with another's ID."""
        game = Game(self.GAME_ID)
        goal = next(event for event in game.html_events if event["event"] == "GOAL" and event["player_2"])
        api_goal = next(
            event
            for event in game.api_events
            if (event["period"], event["period_seconds"], event["event"])
            == (goal["period"], goal["period_seconds"], "GOAL")
        )
        wrong = dict(api_goal, player_2_api_id=1)

        merged = game._merge_pbp_events([goal], [wrong], [], game.rosters)[0]

        roster = {player["eh_id"]: player["api_id"] for player in game.rosters}
        assert merged["player_2_api_id"] == roster[goal["player_2_eh_id"]]

    def test_a_supported_later_season_never_asks_espn(self):
        with patch(self.ESPN) as espn:
            assert Game(2023020001)._espn_coordinates == {}

        espn.assert_not_called()

    @pytest.mark.parametrize(
        ("season", "last_event", "period", "ended"),
        [
            (20072008, "PEND", 3, True),
            (20072008, "PEND", 2, False),
            (20072008, "BLOCK", 2, False),
            (20102011, "PEND", 3, False),
        ],
    )
    def test_a_report_can_end_at_the_last_period_end(self, season, last_event, period, ended):
        game = MagicMock(season=season)

        assert _GameHTMLEventsMixin._has_game_end(game, [{"event": last_event, "period": period}]) is ended

    @pytest.mark.parametrize(
        ("raw_name", "expected"),
        [
            ("COLIN (JOHN) WHITE  (A)", "COLIN WHITE"),
            ("BATES (JON) BATTAGLIA", "BATES BATTAGLIA"),
            ("JOE SAKIC (C)", "JOE SAKIC"),
        ],
    )
    def test_a_formal_name_in_a_roster_report_is_dropped(self, raw_name, expected):
        player = {
            "jersey": "5",
            "position": "D",
            "player_name": raw_name,
            "team_name": "COLORADO AVALANCHE",
            "team_venue": "HOME",
            "status": "ACTIVE",
            "starter": 0,
        }

        assert Game(self.GAME_ID)._munge_single_html_player(player)["player_name"] == expected

    def test_a_roster_report_can_write_the_canadiens_backwards(self):
        """Some 2007-10 reports say CANADIENS MONTREAL, which no team code matched."""
        game = Game(2023020411)
        get_report = game._get_report

        def reversed_name(url, report):
            response = get_report(url, report)
            assert response is not None
            response._content = re.sub(rb"MONTR\S{1,8}AL CANADIENS", b"CANADIENS MONTREAL", response.content)
            return response

        game._get_report = reversed_name  # ty: ignore[invalid-assignment]

        assert {player["team"] for player in game.html_rosters} == {"MTL", "BUF"}
