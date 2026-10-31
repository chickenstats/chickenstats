"""Offline tests that replay NHL responses captured while a game was in progress.

Each directory under ``mock_data/live`` holds the five responses for one game at
one moment, named ``<game_id>_<state>``. No network access is needed.
"""

import json
import logging
import os
from unittest.mock import patch

import pytest
import requests

from chickenstats.chicken_nhl import Game, Scraper
from chickenstats.chicken_nhl._game_pbp import finished_game_anomalies
from chickenstats.exceptions import GameNotStartedError, ReportUnavailableError

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "mock_data")
LIVE_DATA_DIR = os.path.join(MOCK_DATA_DIR, "live")

REPORT_FILES = {"PL": "events.html", "RO": "rosters.html", "TH": "shifts_home.html", "TV": "shifts_away.html"}


def snapshot_session_get(
    snapshot: str,
    drop_last_api_event: str | None = None,
    missing_reports: tuple = (),
    drop_api_detail: tuple[str, str] | None = None,
    report_edit: tuple[str, str, str] | None = None,
):
    """Build a requests Session.get replacement that serves one captured snapshot.

    ``drop_last_api_event`` removes the final event of that type (an API
    ``typeDescKey``, e.g. ``"faceoff"``) from the API feed, as when the feed is a
    moment behind the HTML reports. ``missing_reports`` lists HTML reports
    (``"PL"``, ``"RO"``, ``"TH"``, ``"TV"``) that return a 404.
    ``drop_api_detail`` is an (API ``typeDescKey``, detail key) pair: that key is
    removed from the final event of that type, as seen briefly for the shooter of
    a blocked shot on game 2026020052 just after it ended. ``report_edit`` is a
    (report, old text, new text) triple: the last occurrence of the old text in that
    HTML report is replaced, as when a row has only been partly written.
    """
    snapshot_dir = os.path.join(LIVE_DATA_DIR, snapshot)
    game_id = os.path.basename(os.path.normpath(snapshot_dir)).split("_")[0]
    if not game_id.isdigit():
        game_id = "2023020001"
    html_id = game_id[4:]

    def mock_session_get(self, url, *args, **kwargs):
        response = requests.Response()
        response.url = url
        response.status_code = 404

        filename = None
        if f"gamecenter/{game_id}/play-by-play" in url:
            filename = "play_by_play.json"
        else:
            for report, report_file in REPORT_FILES.items():
                if f"/{report}{html_id}.HTM" in url and report not in missing_reports:
                    filename = report_file

        if filename is not None:
            response.status_code = 200
            with open(os.path.join(snapshot_dir, filename), "rb") as f:
                response._content = f.read()

            if drop_last_api_event and filename == "play_by_play.json":
                payload = json.loads(response._content)
                plays = payload["plays"]
                del plays[max(i for i, play in enumerate(plays) if play["typeDescKey"] == drop_last_api_event)]
                response._content = json.dumps(payload).encode()

            if drop_api_detail and filename == "play_by_play.json":
                event_type, detail = drop_api_detail
                payload = json.loads(response._content)
                last_event = [play for play in payload["plays"] if play["typeDescKey"] == event_type][-1]
                del last_event["details"][detail]
                response._content = json.dumps(payload).encode()

            if report_edit and filename == REPORT_FILES.get(report_edit[0]):
                _, old, new = report_edit
                before, found, after = response._content.rpartition(old.encode())
                assert found, f"{old!r} is not in {filename}"
                response._content = before + new.encode() + after

        return response

    return mock_session_get


# Each case is a snapshot and a Game product that should build from it
LIVE_CASES = [
    # PL report ends with a partial row for the event in progress
    ("2026020052_LIVE_P3", "html_events"),
    ("2026020052_LIVE_P3", "play_by_play"),
    ("2026020052_LIVE_P3", "shifts"),
    ("2026020052_LIVE_P3", "rosters"),
]


@pytest.mark.parametrize("snapshot, product", LIVE_CASES)
def test_live_snapshot_builds(snapshot, product):
    """A game in progress should produce rows for every product."""
    game_id = int(snapshot.split("_")[0])

    with patch("requests.Session.get", snapshot_session_get(snapshot)):
        rows = getattr(Game(game_id), product)

    assert len(rows) > 0


def test_faceoff_missing_from_api_feed():
    """A faceoff the API feed doesn't have yet still gives its line changes a zone start."""
    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR, drop_last_api_event="faceoff")):
        play_by_play = Game(2023020001).play_by_play

    assert len(play_by_play) > 0

    unmatched_faceoffs = {
        (event["period"], event["game_seconds"])
        for event in play_by_play
        if event["event"] == "FAC" and event["coords_x"] is None
    }
    changes = [
        event
        for event in play_by_play
        if event["event"] == "CHANGE" and (event["period"], event["game_seconds"]) in unmatched_faceoffs
    ]

    assert changes
    assert all(event["zone_start"] in ("OFF", "DEF", "NEU") for event in changes)


def test_shot_missing_from_api_feed():
    """A shot the API feed doesn't have yet is kept, with null location fields."""
    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR, drop_last_api_event="shot-on-goal")):
        game = Game(2023020001)
        play_by_play = game.play_by_play
        xg_fields = game.xg_fields

    shots = [event for event in play_by_play if event["event"] == "SHOT" and event["coords_x"] is None]
    assert len(shots) == 1

    unlocated = [fields for fields in xg_fields if fields["event_idx"] == shots[0]["event_idx"]]
    assert len(unlocated) == 1
    for field in ("coords_x", "coords_y", "event_distance", "event_angle", "abs_y_distance"):
        assert unlocated[0][field] is None

    assert all(fields["coords_x"] is not None for fields in xg_fields if fields is not unlocated[0])
    assert game.xg_fields_df.height == len(xg_fields)


def in_progress(get):
    """Wrap a Session.get so the saved game's API response reads as a game in its third period."""

    def wrapped(self, url, *args, **kwargs):
        response = get(self, url, *args, **kwargs)
        if "gamecenter/2023020001/play-by-play" in str(url):
            body = json.loads(response.content)
            body["gameState"] = "LIVE"
            response._content = json.dumps(body).encode()
        return response

    return wrapped


def test_a_finished_game_without_its_roster_report_fails():
    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR, missing_reports=("RO",))):
        game = Game(2023020001)
        with pytest.raises(ReportUnavailableError, match="RO"):
            _ = game.play_by_play


def test_roster_report_missing():
    """While a game is in progress, the API roster alone identifies the players until the roster report is posted."""
    with patch("requests.Session.get", in_progress(snapshot_session_get(MOCK_DATA_DIR, missing_reports=("RO",)))):
        game = Game(2023020001)
        rosters = game.rosters
        shifts = game.shifts
        play_by_play = game.play_by_play

    assert len(rosters) == 40
    assert all(player["status"] == "ACTIVE" for player in rosters)

    assert len(shifts) > 0
    assert all(shift["api_id"] and shift["position"] for shift in shifts)

    shots = [event for event in play_by_play if event["event"] == "SHOT"]
    assert shots
    assert all(event["player_1"] and event["strength_state"] != "EvE" for event in shots)


MISSING_PLAYER_CASES = [
    ("blocked-shot", "shootingPlayerId", "BLOCK", "player_2_api_id"),
    ("faceoff", "winningPlayerId", "FAC", "player_1_api_id"),
    ("faceoff", "losingPlayerId", "FAC", "player_2_api_id"),
    ("hit", "hittingPlayerId", "HIT", "player_1_api_id"),
    ("hit", "hitteePlayerId", "HIT", "player_2_api_id"),
    ("giveaway", "playerId", "GIVE", "player_1_api_id"),
    ("takeaway", "playerId", "TAKE", "player_1_api_id"),
]


@pytest.mark.parametrize("event_type, detail, event, player_field", MISSING_PLAYER_CASES)
def test_api_event_without_player(event_type, detail, event, player_field):
    """An event the API feed lists without one of its players keeps its other details."""
    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR, drop_api_detail=(event_type, detail))):
        game = Game(2023020001)
        api_events = game.api_events
        play_by_play = game.play_by_play

    api_matches = [row for row in api_events if row["event"] == event]
    assert api_matches[-1][player_field] is None
    assert api_matches[-1]["coords_x"] is not None
    assert all(row[player_field] is not None for row in api_matches[:-1])

    # The event stays in the play-by-play; when the missing player is the one the HTML
    # report is matched on, that single row has no coordinates until the feed fills it in
    pbp_matches = [row for row in play_by_play if row["event"] == event]
    assert len(pbp_matches) == len(api_matches)
    assert sum(row["coords_x"] is None for row in pbp_matches) <= 1


STOPPAGE_DETAILS = [({"secondaryReason": "tv-timeout"}, "TV TIMEOUT"), ({}, ""), (None, "")]


@pytest.mark.parametrize("details, secondary_reason", STOPPAGE_DETAILS)
def test_stoppage_without_reason(details, secondary_reason):
    """A stoppage the API feed lists without a reason, or without any details, is still a STOP."""
    stoppage = {
        "eventId": 867,
        "periodDescriptor": {"number": 3, "periodType": "REG", "maxRegulationPeriods": 3},
        "timeInPeriod": "19:24",
        "timeRemaining": "00:36",
        "situationCode": "1551",
        "homeTeamDefendingSide": "left",
        "typeCode": 516,
        "typeDescKey": "stoppage",
        "sortOrder": 791,
    }
    if details is not None:
        stoppage["details"] = details

    event = Game(2023020001)._munge_single_api_event(stoppage, {}, {})

    assert event["event"] == "STOP"
    assert event["stoppage_reason"] == ""
    assert event["stoppage_reason_secondary"] == secondary_reason


def test_stoppage_without_details_in_play_by_play():
    """A stoppage with no details in the API feed still pairs with its HTML report row."""
    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR)):
        expected = Game(2023020001).play_by_play

    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR, drop_api_detail=("stoppage", "reason"))):
        game = Game(2023020001)
        api_events = game.api_events
        play_by_play = game.play_by_play

    assert not [row for row in api_events if row["event"] == "stoppage"]
    assert [row["stoppage_reason"] for row in api_events if row["event"] == "STOP"].count("") == 1

    stops = [row for row in play_by_play if row["event"] == "STOP"]
    assert [row["event_idx"] for row in stops] == [row["event_idx"] for row in expected if row["event"] == "STOP"]
    assert len(play_by_play) == len(expected)


def test_faceoff_without_winner_in_html_report():
    """A faceoff the HTML report lists before its winner is kept, with both players and no winning team."""
    complete = "FLA won Off. Zone - FLA #8 TKACHUK vs LAK #56 HAULA"
    partial = "FLA #8 TKACHUK vs LAK #56 HAULA"
    snapshot = "2026020052_LIVE_P3"

    with patch("requests.Session.get", snapshot_session_get(snapshot)):
        expected = Game(2026020052).html_events

    with patch("requests.Session.get", snapshot_session_get(snapshot, report_edit=("PL", complete, partial))):
        game = Game(2026020052)
        html_events = game.html_events
        play_by_play = game.play_by_play

    faceoffs = [event for event in html_events if event["event"] == "FAC"]
    assert len(faceoffs) == sum(event["event"] == "FAC" for event in expected)

    unresolved = [event for event in faceoffs if not event["event_team"]]
    assert len(unresolved) == 1
    assert unresolved[0]["player_1"] and unresolved[0]["player_2"]

    assert sum(event["event"] == "FAC" for event in play_by_play) == len(faceoffs)


def test_period_and_game_markers_translated():
    """Period and game markers come without details and still get their short event codes."""
    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR)):
        api_events = Game(2023020001).api_events

    events = [row["event"] for row in api_events]

    assert events.count("PSTR") == 3
    assert events.count("PEND") == 3
    assert events.count("GEND") == 1
    assert all(event.isupper() for event in events)


# -----------------------------------------------------------------------------
# A game that has not started
# -----------------------------------------------------------------------------


def serve_edited_api_response(edit):
    """A Session.get that serves the saved game's API response after edit(response), and everything else as saved."""
    served_get = requests.Session.get

    def get(self, url, *args, **kwargs):
        response = served_get(self, url, *args, **kwargs)
        if "gamecenter/2023020001/play-by-play" in str(url):
            body = json.loads(response.content)
            edit(body)
            response._content = json.dumps(body).encode()
        return response

    return get


def as_pregame(body: dict) -> None:
    """Edit an API response to look like one for a game at PRE: no period yet, and no plays."""
    body["gameState"] = "PRE"
    body.pop("periodDescriptor", None)
    body["plays"] = []


def test_a_game_that_has_not_started_says_so():
    with patch.object(requests.Session, "get", serve_edited_api_response(as_pregame)):
        game = Game(2023020001)
        with pytest.raises(GameNotStartedError, match="has not started"):
            _ = game.play_by_play

    assert (game.game_state, game.current_period) == ("PRE", 0)


def test_a_scraper_keeps_a_game_that_has_not_started_apart_from_failures():
    """The game is not a failure; it is listed as not started, and refresh() fetches it once it has (tu-04)."""
    with patch.object(requests.Session, "get", serve_edited_api_response(as_pregame)):
        scraper = Scraper([2023020001], disable_progress_bar=True)
        with pytest.warns(UserWarning, match="1 game\\(s\\) have not started") as warned:
            play_by_play = scraper.play_by_play

    not_started = scraper.not_started_games
    scraper.refresh()
    started = scraper.play_by_play

    assert (scraper.failed_games, not_started, play_by_play.height) == ([], [2023020001], 0)
    assert [warning.filename for warning in warned if "not started" in str(warning.message)] == [__file__]
    assert scraper.not_started_games == []
    assert started.height == 781


def test_a_response_that_fails_to_parse_is_not_kept():
    """A failed parse leaves no response behind, so the next access fetches it again."""

    def without_venue(body: dict) -> None:
        body.pop("venue")

    with patch.object(requests.Session, "get", serve_edited_api_response(without_venue)):
        game = Game(2023020001)
        with pytest.raises(KeyError):
            game._fetch_api_data()

    assert game.api_response is None
    game._fetch_api_data()
    assert game.api_response is not None


def test_a_cut_off_shift_report_keeps_its_whole_rows_while_the_game_is_in_progress(caplog):
    """A home shift report cut off mid-row keeps the home team's whole shifts, and the cut is logged."""
    served_get = requests.Session.get

    def cut_home_shifts(self, url, *args, **kwargs):
        response = served_get(self, url, *args, **kwargs)
        if "/TH020001.HTM" in str(url):
            response._content = response.content[: int(len(response.content) * 0.6)]
        return response

    with patch("requests.Session.get", in_progress(cut_home_shifts)), caplog.at_level(logging.WARNING):
        shifts = Game(2023020001).shifts

    home = [shift for shift in shifts if shift["team_venue"] == "HOME"]
    assert 0 < len(home) < len([shift for shift in shifts if shift["team_venue"] == "AWAY"])
    assert any("TH (cut off before its end)" in record.getMessage() for record in caplog.records)


# -----------------------------------------------------------------------------
# What a finished game should not have
# -----------------------------------------------------------------------------


def test_finished_game_anomalies_are_counted():
    play = {"event": "SHOT", "event_team": "NSH", "strength_state": "5v5", "home_skaters": 5, "away_skaters": 5}
    events = [
        play,
        {**play, "event": "FAC", "event_team": None},
        {**play, "home_skaters": 0},
        {**play, "away_skaters": 7, "strength_state": "ILLEGAL"},
        {**play, "home_skaters": 1, "away_skaters": 0, "strength_state": "1v0"},
    ]

    assert finished_game_anomalies(events) == [
        "1 faceoff(s) with no winning team",
        "2 play(s) with no skaters or more than six on a side",
        "1 event(s) in an ILLEGAL strength state",
    ]


@pytest.mark.parametrize(
    "fixture",
    [
        "fixture_game",
        "shootout_game",
        "long_shootout_game",
        "playoff_overtime_game",
        "second_nashville_game",
        "old_regular_season_game",
        "old_playoff_game",
    ],
)
def test_saved_games_have_no_finished_game_anomalies(request, fixture):
    assert finished_game_anomalies(request.getfixturevalue(fixture).play_by_play.to_dicts()) == []


def test_a_finished_game_whose_html_report_has_a_faceoff_with_no_winner_is_logged(caplog):
    """The API still names the winner, so play-by-play has one, but the report itself is logged as wrong."""
    complete = "TBL won Def. Zone - NSH #10 SISSONS vs TBL #71 CIRELLI"
    partial = "NSH #10 SISSONS vs TBL #71 CIRELLI"

    with patch("requests.Session.get", snapshot_session_get(MOCK_DATA_DIR, report_edit=("PL", complete, partial))):
        with caplog.at_level(logging.WARNING):
            _ = Game(2023020001).play_by_play

    assert any("HTML events report has 1 faceoff(s) with no winner" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize(
    "type_desc_key, code",
    [
        ("faceoff", "FAC"),
        ("hit", "HIT"),
        ("giveaway", "GIVE"),
        ("takeaway", "TAKE"),
        ("shot-on-goal", "SHOT"),
        ("missed-shot", "MISS"),
        ("blocked-shot", "BLOCK"),
        ("goal", "GOAL"),
        ("penalty", "PENL"),
    ],
)
def test_an_api_event_without_details_gets_its_event_code(type_desc_key, code):
    """The feed can list an event before its details; it still gets the code its HTML row has."""
    sort_order = {}

    def without_details(body: dict) -> None:
        play = next(play for play in body["plays"] if play["typeDescKey"] == type_desc_key)
        play.pop("details", None)
        sort_order["value"] = play["sortOrder"]

    expected = sum(event["event"] == code for event in Game(2023020001).play_by_play)
    with patch.object(requests.Session, "get", serve_edited_api_response(without_details)):
        game = Game(2023020001)
        event = next(event for event in game.api_events if event["event_idx"] == sort_order["value"])
        play_by_play = game.play_by_play

    assert event["event"] == code
    assert sum(row["event"] == code for row in play_by_play) == expected
