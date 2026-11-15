"""The API client through the real SDK, with only the connection pool replaced.

These read the query string as it goes out and parse real response bodies, which mocked SDK methods cannot do.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from chickenstats_api.exceptions import UnauthorizedException

from chickenstats.api._auth import Credentials, save_credentials
from chickenstats.api.api import ChickenStats
from chickenstats.exceptions import AuthError, ChickenstatsError


def _row(row_id: int) -> dict:
    """Return a play-by-play row with the fields the SDK requires."""
    counts = (
        "event_idx",
        "period",
        "period_seconds",
        "game_seconds",
        "score_diff",
        "home_score",
        "home_score_diff",
        "away_score",
        "away_score_diff",
        "is_home",
        "is_away",
        "home_skaters",
        "away_skaters",
    )
    return {
        **dict.fromkeys(counts, 1),
        "id": row_id,
        "season": 20232024,
        "session": "R",
        "game_id": 2023020001,
        "event": "SHOT",
        "forwards_percent": 0.5,
        "opp_forwards_percent": 0.5,
    }


def _page(ids: list[int], total: int, offset: int, has_next: bool) -> tuple[int, dict]:
    body = {
        "count": len(ids),
        "total": total,
        "limit": 50_000,
        "offset": offset,
        "has_next": has_next,
        "data": [_row(row_id) for row_id in ids],
    }
    return 200, body


class FakePool:
    """Stands in for the SDK's urllib3 pool: serves queued responses and records each query."""

    def __init__(self, responses: list[tuple[int, dict]]):
        self.responses = list(responses)
        self.queries: list[dict] = []
        self.sent: list[tuple[str, str, str | None]] = []

    def request(self, method, url, **kwargs):
        self.queries.append(parse_qs(urlsplit(url).query))
        self.sent.append((method, urlsplit(url).path, (kwargs.get("headers") or {}).get("Authorization")))
        status, body = self.responses.pop(0)
        return SimpleNamespace(
            status=status, reason="reason", data=json.dumps(body).encode(), headers={"content-type": "application/json"}
        )


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Return a function giving a logged-in ChickenStats whose SDK talks to a FakePool."""
    monkeypatch.setattr("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials")

    def build(responses):
        cs = ChickenStats(token="test-token")

        pool = FakePool(responses)
        cs.user.api_client.rest_client.pool_manager = pool  # ty: ignore[invalid-assignment]
        return cs, pool

    return build


def test_a_scalar_season_is_one_season_on_the_wire(client):
    cs, pool = client([_page([1], 1, 0, False)])

    cs.download_pbp(season="20232024", sessions="R", disable_progress_bar=True)

    assert pool.queries[0]["season"] == ["20232024"]
    assert pool.queries[0]["sessions"] == ["R"]


def test_the_default_page_size_is_on_the_wire(client):
    cs, pool = client([_page([1], 1, 0, False)])

    cs.download_pbp(disable_progress_bar=True)

    assert pool.queries[0]["limit"] == ["50000"]


def test_three_pages_keep_their_order_and_offsets(client):
    cs, pool = client([_page([1, 2], 5, 0, True), _page([3, 4], 5, 2, True), _page([5], 5, 4, False)])

    pbp = cs.download_pbp(disable_progress_bar=True)

    assert pbp["id"].to_list() == [1, 2, 3, 4, 5]
    assert [query["offset"] for query in pool.queries] == [["0"], ["2"], ["4"]]


def test_a_502_on_page_two_recovers(client):
    cs, pool = client([_page([1], 2, 0, True), (502, {"detail": "bad gateway"}), _page([2], 2, 1, False)])

    with patch("chickenstats.api.api.time.sleep"):
        pbp = cs.download_pbp(disable_progress_bar=True)

    assert pbp["id"].to_list() == [1, 2]
    assert [query["offset"] for query in pool.queries] == [["0"], ["1"], ["1"]]


def test_a_free_tier_default_download_succeeds(client):
    detail = "limit=50000 exceeds the maximum of 1000 rows per request for the 'free' tier."
    cs, pool = client([(400, {"detail": detail}), _page([1], 1, 0, False)])

    pbp = cs.download_pbp(disable_progress_bar=True)

    assert pbp["id"].to_list() == [1]
    assert [query["limit"] for query in pool.queries] == [["50000"], ["1000"]]


# -----------------------------------------------------------------------------
# A 401 refreshes the token through the real refresh endpoint (N74)
# -----------------------------------------------------------------------------

# A refresh posts a grant to /auth/token
TOKEN = ("POST", "/api/v1/auth/token", None)
PBP = "/api/v1/chicken_nhl/play_by_play"


def _token(number: int) -> tuple[int, dict]:
    return 200, {
        "access_token": f"access-{number}",
        "token_type": "Bearer",
        "expires_in": 86400,
        "refresh_token": f"refresh-{number}",
    }


@pytest.fixture
def wire(tmp_path, monkeypatch):
    """Return a function giving a ChickenStats from a saved login whose every SDK client uses one FakePool."""
    monkeypatch.setattr("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials")
    for name in ("CHICKENSTATS_API_TOKEN", "CHICKENSTATS_API_HOST"):
        monkeypatch.delenv(name, raising=False)
    save_credentials(Credentials("access-1", "refresh-1"))

    def build(responses):
        pool = FakePool(responses)
        monkeypatch.setattr("chickenstats_api.rest.urllib3.PoolManager", lambda **kwargs: pool)
        return ChickenStats(), pool

    return build


def test_a_401_refreshes_and_the_retry_sends_the_new_token(wire):
    cs, pool = wire([(401, {"detail": "expired"}), _token(2), _page([1], 1, 0, False)])

    pbp = cs.download_pbp(disable_progress_bar=True)

    assert pbp["id"].to_list() == [1]
    assert pool.sent == [("GET", PBP, "Bearer access-1"), TOKEN, ("GET", PBP, "Bearer access-2")]
    assert cs.access_token == cs.user.access_token == "access-2"


def test_a_rejected_refresh_raises_auth_error(wire):
    cs, pool = wire([(401, {"detail": "expired"}), (401, {"detail": "revoked"})])

    with pytest.raises(AuthError, match="chickenstats login") as error:
        cs.download_pbp(disable_progress_bar=True)

    assert isinstance(error.value, ChickenstatsError)
    assert pool.sent == [("GET", PBP, "Bearer access-1"), TOKEN]


def test_an_expired_token_refreshes(wire):
    expired = (401, {"error": "invalid_token", "error_description": "token_expired"})
    cs, pool = wire([expired, _token(2), _page([1], 1, 0, False)])

    cs.download_pbp(disable_progress_bar=True)

    assert pool.sent.count(TOKEN) == 1


@pytest.mark.parametrize("reason", ["token_revoked", "invalid_token"])
def test_a_revoked_or_invalid_token_asks_to_sign_in_without_refreshing(wire, reason):
    cs, pool = wire([(401, {"error": "invalid_token", "error_description": reason})])

    with pytest.raises(AuthError, match="chickenstats login"):
        cs.download_pbp(disable_progress_bar=True)

    assert pool.sent == [("GET", PBP, "Bearer access-1")]


def test_two_401s_in_a_row_refresh_once(wire):
    cs, pool = wire([(401, {"detail": "expired"}), _token(2), (401, {"detail": "forbidden"})])

    with pytest.raises(UnauthorizedException):
        cs.download_pbp(disable_progress_bar=True)

    assert [request for request in pool.sent if request[1] == PBP] == [
        ("GET", PBP, "Bearer access-1"),
        ("GET", PBP, "Bearer access-2"),
    ]
    assert pool.sent.count(TOKEN) == 1


# -----------------------------------------------------------------------------
# The check_* methods page through the ID endpoints (N75)
# -----------------------------------------------------------------------------

_CHECK_METHODS = [
    "check_pbp_game_ids",
    "check_pbp_play_ids",
    "check_stats_game_ids",
    "check_team_stats_game_ids",
    "check_lines_game_ids",
    "check_roster_game_ids",
]


@pytest.mark.parametrize("method", _CHECK_METHODS)
def test_a_check_method_reads_every_page(client, method):
    cs, pool = client([(200, [1, 2]), (200, [3, 4]), (200, [5])])
    cs.limit = 2

    assert getattr(cs, method)() == [1, 2, 3, 4, 5]
    assert [query["offset"] for query in pool.queries] == [["0"], ["2"], ["4"]]
    assert [query["limit"] for query in pool.queries] == [["2"], ["2"], ["2"]]


def test_a_last_full_page_is_followed_by_an_empty_one(client):
    cs, pool = client([(200, [1, 2]), (200, [3, 4]), (200, [5, 6]), (200, [])])
    cs.limit = 2

    assert cs.check_pbp_play_ids(season=20232024) == [1, 2, 3, 4, 5, 6]
    assert [query["offset"] for query in pool.queries] == [["0"], ["2"], ["4"], ["6"]]
    assert all(query["season"] == ["20232024"] for query in pool.queries)


def test_the_default_id_page_size_is_on_the_wire(client):
    cs, pool = client([(200, [1, 2])])

    assert cs.check_pbp_game_ids() == [1, 2]
    assert pool.queries[0]["limit"] == ["50000"]


def test_a_free_tier_check_reads_every_page_at_its_cap(client):
    detail = "limit=50000 exceeds the maximum of 2 rows per request for the 'free' tier."
    cs, pool = client([(400, {"detail": detail}), (200, [1, 2]), (200, [3])])

    assert cs.check_stats_game_ids() == [1, 2, 3]
    assert [(query["limit"], query["offset"]) for query in pool.queries] == [
        (["50000"], ["0"]),
        (["2"], ["0"]),
        (["2"], ["2"]),
    ]
