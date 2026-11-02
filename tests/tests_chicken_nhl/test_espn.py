"""Tests for the ESPN coordinate source, run from trimmed real responses in mock_data/espn."""

import json
from pathlib import Path

import pytest
import requests

from chickenstats.chicken_nhl._espn import (
    espn_coordinates,
    fetch_espn_summary,
    find_espn_id,
    match_coordinates,
    normalize_plays,
)
from chickenstats.utilities import ChickenSession

MOCK_DIR = Path(__file__).parent / "mock_data" / "espn"
BUFFALO_ID = "271121002"
FINAL_ID = "280602005"


def load(name: str) -> dict:
    return json.loads((MOCK_DIR / name).read_text(encoding="utf-8"))


class FakeResponse(requests.Response):
    def __init__(self, payload=None, status_code: int = 200, bad_json: bool = False):
        super().__init__()
        self.status_code = status_code
        self._content = b"not JSON" if bad_json else json.dumps(payload).encode()


class FakeSession(ChickenSession):
    """Answers each request from a list of responses, in order; an exception in the list is raised."""

    def __init__(self, *responses):
        super().__init__()
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, params))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def play(event: str, x: object = 10, y: object = 5, **overrides) -> dict:
    """A raw ESPN play in the real shape, for the cases the saved games do not have."""
    return {
        "type": {"text": event},
        "period": {"number": 1},
        "clock": {"displayValue": "1:00"},
        "team": {"id": "2"},
        "coordinate": {"x": x, "y": y},
        "participants": [{"athlete": {"displayName": "Maxim Afinogenov"}}],
        **overrides,
    }


def summary_of(*plays: dict) -> dict:
    return {
        "header": {
            "competitions": [{"competitors": [{"homeAway": "home", "team": {"id": "2", "abbreviation": "BUF"}}]}]
        },
        "plays": list(plays),
    }


def normalized(event: str, x: int, y: int, players: set[str], team: str = "BUF", **overrides) -> dict:
    return {
        "period": 1,
        "period_seconds": 60,
        "event": event,
        "event_team": team,
        "coords_x": x,
        "coords_y": y,
        "players": players,
        **overrides,
    }


def html(event_idx: int, event: str, description: str, team: str = "BUF", **overrides) -> dict:
    return {
        "event_idx": event_idx,
        "period": 1,
        "period_seconds": 60,
        "event": event,
        "event_team": team,
        "description": description,
        **overrides,
    }


class TestFindEspnId:
    def test_finds_the_game_on_the_date(self):
        session = FakeSession(FakeResponse(load("scoreboard_20071121.json")))

        assert find_espn_id("2007-11-21", "BUF", "OTT", session) == BUFFALO_ID
        assert session.calls[0][1] == {"dates": "20071121"}

    @pytest.mark.parametrize("home_team", ["ARI", "PHX"])
    def test_espn_abbreviations_are_mapped(self, home_team):
        """ESPN has this game as LA at PHX."""
        session = FakeSession(FakeResponse(load("scoreboard_20071121.json")))

        assert find_espn_id("2007-11-21", home_team, "LAK", session) == "271121024"

    def test_home_and_away_are_not_interchangeable(self):
        session = FakeSession(FakeResponse(load("scoreboard_20071121.json")))

        assert find_espn_id("2007-11-21", "OTT", "BUF", session) is None

    @pytest.mark.parametrize(
        "response",
        [
            FakeResponse(status_code=404),
            FakeResponse(status_code=500),
            FakeResponse(bad_json=True),
            FakeResponse(["not", "a", "dict"]),
            FakeResponse({}),
            requests.exceptions.ConnectionError("down"),
            requests.exceptions.Timeout("slow"),
        ],
    )
    def test_a_failure_returns_none(self, response):
        assert find_espn_id("2007-11-21", "BUF", "OTT", FakeSession(response)) is None


class TestFetchEspnSummary:
    def test_returns_the_summary(self):
        summary = load(f"summary_{BUFFALO_ID}.json")
        session = FakeSession(FakeResponse(summary))

        assert fetch_espn_summary(BUFFALO_ID, session) == summary
        assert session.calls[0][1] == {"event": BUFFALO_ID}

    def test_a_404_returns_none(self):
        assert fetch_espn_summary("1", FakeSession(FakeResponse(status_code=404))) is None


class TestNormalizePlays:
    def test_reads_a_saved_game(self):
        plays = normalize_plays(load(f"summary_{BUFFALO_ID}.json"))

        goal = next(x for x in plays if x["event"] == "GOAL")
        assert goal == {
            "period": 1,
            "period_seconds": 86,
            "event": "GOAL",
            "event_team": "BUF",
            "coords_x": 77,
            "coords_y": -4,
            "players": {"RYAN", "GAUSTAD", "PAILLE"},
        }

    def test_a_turnover_is_one_type_and_a_stoppage_is_dropped(self):
        plays = normalize_plays(load(f"summary_{BUFFALO_ID}.json"))

        assert {x["event"] for x in plays} == {"FAC", "HIT", "SHOT", "GOAL", "MISS", "BLOCK", "TURN", "PENL"}

    @pytest.mark.parametrize(
        "bad_play",
        [
            {key: value for key, value in play("Shot").items() if key != "type"},  # ESPN's shootout attempts
            {key: value for key, value in play("Shot").items() if key != "coordinate"},
            {key: value for key, value in play("Shot").items() if key != "team"},
            {key: value for key, value in play("Shot").items() if key != "clock"},
            {key: value for key, value in play("Shot").items() if key != "period"},
            play("Shot", x=None),
            play("Shot", x="10"),
            play("Shot", x=-2147483648),
            play("Shot", y=44),
            play("Period Start"),
            play("Shot", team={"id": "999"}),
            play("Penalty", x=-97, y=40),
        ],
    )
    def test_a_play_that_cannot_be_used_is_dropped(self, bad_play):
        assert normalize_plays(summary_of(bad_play)) == []

    def test_the_penalty_placeholder_is_a_real_spot_for_other_events(self):
        assert normalize_plays(summary_of(play("Hit", x=-97, y=40)))[0]["coords_x"] == -97

    def test_coordinates_are_not_rescaled(self):
        plays = normalize_plays(summary_of(play("Shot", x=69, y=-23)))

        assert (plays[0]["coords_x"], plays[0]["coords_y"]) == (69, -23)

    def test_surnames_are_ascii_and_upper_case(self):
        participants = [
            {"athlete": {"displayName": "Tomáš Kaberle"}},
            {"athlete": {"displayName": "   "}},
            {"athlete": {}},
            {},
        ]

        plays = normalize_plays(summary_of(play("Shot", participants=participants)))

        assert plays[0]["players"] == {"KABERLE"}

    def test_a_play_with_no_participants_is_kept(self):
        plays = normalize_plays(summary_of(play("Shot", participants=[])))

        assert plays[0]["players"] == set()

    def test_an_empty_summary_has_no_plays(self):
        assert normalize_plays({}) == []


class TestMatchCoordinates:
    @pytest.fixture
    def events(self) -> dict:
        return load("html_events.json")

    def test_a_saved_regular_season_game(self, events):
        matches = match_coordinates(events["2007020300"], normalize_plays(load(f"summary_{BUFFALO_ID}.json")))

        assert matches[3] == {"coords_x": -60, "coords_y": -42}  # hit
        assert matches[5] == {"coords_x": 43, "coords_y": 33}  # shot
        assert matches[9] == {"coords_x": 77, "coords_y": -4}  # goal
        assert matches[17] == {"coords_x": -35, "coords_y": 7}  # miss
        assert matches[23] == {"coords_x": -56, "coords_y": -15}  # giveaway
        assert matches[33] == {"coords_x": -80, "coords_y": 0}  # penalty

    def test_a_block_credited_to_the_shooters_team(self, events):
        """In this game ESPN has each block on the shooter's team and the HTML report on the blocker's."""
        matches = match_coordinates(events["2007020300"], normalize_plays(load(f"summary_{BUFFALO_ID}.json")))

        assert matches[91] == {"coords_x": 65, "coords_y": 5}
        assert matches[112] == {"coords_x": 52, "coords_y": -8}

    def test_tied_shots_are_settled_by_the_player(self, events):
        """Datsyuk and Filppula have a shot at the same second of overtime in the 2008 final."""
        matches = match_coordinates(events["2007030415"], normalize_plays(load(f"summary_{FINAL_ID}.json")))

        assert matches[321] == {"coords_x": 55, "coords_y": -6}
        assert matches[323] == {"coords_x": 65, "coords_y": 8}

    def test_a_third_overtime(self, events):
        matches = match_coordinates(events["2007030415"], normalize_plays(load(f"summary_{FINAL_ID}.json")))

        assert matches[473] == {"coords_x": 6, "coords_y": 36}  # takeaway
        assert matches[518] == {"coords_x": -60, "coords_y": 17}  # the winning goal

    def test_only_listed_events_are_matched(self, events):
        matches = match_coordinates(events["2007030415"], normalize_plays(load(f"summary_{FINAL_ID}.json")))

        assert 322 not in matches  # stoppage

    def test_an_event_espn_does_not_have_gets_nothing(self):
        assert match_coordinates([html(1, "HIT", "BUF #51 CAMPBELL HIT OTT #20 VERMETTE")], []) == {}

    def test_the_wrong_team_does_not_match(self):
        plays = [normalized("SHOT", 10, 5, {"RYAN"}, team="OTT")]

        assert match_coordinates([html(1, "SHOT", "BUF ONGOAL - 37 RYAN")], plays) == {}

    def test_the_wrong_second_does_not_match(self):
        plays = [normalized("SHOT", 10, 5, {"RYAN"}, period_seconds=61)]

        assert match_coordinates([html(1, "SHOT", "BUF ONGOAL - 37 RYAN")], plays) == {}

    def test_the_wrong_period_does_not_match(self):
        plays = [normalized("SHOT", 10, 5, {"RYAN"}, period=2)]

        assert match_coordinates([html(1, "SHOT", "BUF ONGOAL - 37 RYAN")], plays) == {}

    def test_a_giveaway_and_takeaway_at_one_second_are_split_by_player(self):
        plays = [normalized("TURN", 10, 5, {"LYDMAN"}), normalized("TURN", -20, 8, {"ROY"})]
        events = [html(1, "GIVE", "BUF GIVEAWAY - #5 LYDMAN"), html(2, "TAKE", "BUF TAKEAWAY - #9 ROY")]

        assert match_coordinates(events, plays) == {
            1: {"coords_x": 10, "coords_y": 5},
            2: {"coords_x": -20, "coords_y": 8},
        }

    def test_a_tie_that_cannot_be_settled_gets_no_guess(self):
        plays = [normalized("SHOT", 10, 5, {"RYAN"}), normalized("SHOT", 30, 7, {"RYAN"})]

        assert match_coordinates([html(1, "SHOT", "BUF ONGOAL - 37 RYAN")], plays) == {}

    def test_one_play_is_not_used_for_two_shots(self):
        plays = [normalized("SHOT", 10, 5, {"RYAN"})]
        events = [html(1, "SHOT", "BUF ONGOAL - 37 RYAN"), html(2, "SHOT", "BUF ONGOAL - 37 RYAN")]

        assert match_coordinates(events, plays) == {1: {"coords_x": 10, "coords_y": 5}}

    def test_penalties_of_one_player_share_a_play(self):
        plays = [normalized("PENL", 84, 0, {"AVERY"})]
        events = [
            html(1, "PENL", "BUF #16 AVERY ROUGHING(2 MIN)"),
            html(2, "PENL", "BUF #16 AVERY MISCONDUCT (10 MIN)"),
        ]

        assert match_coordinates(events, plays) == {
            1: {"coords_x": 84, "coords_y": 0},
            2: {"coords_x": 84, "coords_y": 0},
        }


class TestEspnCoordinates:
    @pytest.fixture(autouse=True)
    def gaps(self, monkeypatch) -> list[float]:
        """Record the waits between requests instead of sitting through them."""
        slept: list[float] = []
        monkeypatch.setattr("chickenstats.chicken_nhl._espn.time.sleep", slept.append)
        return slept

    @pytest.fixture
    def events(self) -> list[dict]:
        return load("html_events.json")["2007020300"]

    def test_the_two_requests_are_spaced(self, events, gaps):
        session = FakeSession(
            FakeResponse(load("scoreboard_20071121.json")), FakeResponse(load(f"summary_{BUFFALO_ID}.json"))
        )

        espn_coordinates("2007-11-21", "BUF", "OTT", events, session)

        assert gaps == [0.5]

    def test_a_fractional_location_is_not_used(self):
        """A play's coordinates are validated as integers, so a fraction would fail the game."""
        assert normalize_plays(summary_of(play("Shot", x=10.5, y=5))) == []

    def test_finds_fetches_and_matches(self, events):
        session = FakeSession(
            FakeResponse(load("scoreboard_20071121.json")), FakeResponse(load(f"summary_{BUFFALO_ID}.json"))
        )

        matches = espn_coordinates("2007-11-21", "BUF", "OTT", events, session)

        assert matches[9] == {"coords_x": 77, "coords_y": -4}
        assert len(session.calls) == 2

    def test_a_game_espn_does_not_list_makes_one_request(self, events):
        session = FakeSession(FakeResponse(load("scoreboard_20071121.json")))

        assert espn_coordinates("2007-11-21", "TOR", "OTT", events, session) == {}
        assert len(session.calls) == 1

    @pytest.mark.parametrize(
        "responses",
        [
            [FakeResponse(status_code=500)],
            [requests.exceptions.ConnectionError("down")],
            [FakeResponse(bad_json=True)],
            [FakeResponse({"events": "not a list of events"})],
            [FakeResponse({"events": [{"competitions": [{"competitors": ["not a dict"]}]}]})],
            [FakeResponse(load("scoreboard_20071121.json")), FakeResponse(status_code=404)],
            [FakeResponse(load("scoreboard_20071121.json")), requests.exceptions.Timeout("slow")],
            [FakeResponse(load("scoreboard_20071121.json")), FakeResponse({"plays": ["not a dict"]})],
            [FakeResponse(load("scoreboard_20071121.json")), FakeResponse({"header": "not a dict"})],
            [FakeResponse(load("scoreboard_20071121.json")), FakeResponse({"plays": 7})],
        ],
    )
    def test_any_failure_returns_nothing(self, events, responses):
        assert espn_coordinates("2007-11-21", "BUF", "OTT", events, FakeSession(*responses)) == {}

    def test_a_real_session_with_no_network_returns_nothing(self, events, blocked_urls):
        """The blocked request is the point of this test, so it is cleared for the guard."""
        with ChickenSession() as session:
            assert espn_coordinates("2007-11-21", "BUF", "OTT", events, session) == {}

        assert blocked_urls
        blocked_urls.clear()
