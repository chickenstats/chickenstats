import json
import os
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
import urllib3

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats_api.exceptions import BadRequestException, ServiceException, UnauthorizedException

from chickenstats.api.api import ChickenStats
from chickenstats.exceptions import APIDownloadError, UnsupportedBackendError


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _make_page(data, total, has_next):
    """Fake paginated response matching the chickenstats_api response shape."""
    page = MagicMock()
    page.data = data
    page.total = total
    page.count = len(data)
    page.has_next = has_next
    return page


API_ENV_VARS = [
    "CHICKENSTATS_API_USERNAME",
    "CHICKENSTATS_API_PASSWORD",
    "CHICKENSTATS_API_HOST",
    "CHICKENSTATS_API_CF_CLIENT_ID",
    "CHICKENSTATS_API_CF_CLIENT_SECRET",
]


@pytest.fixture
def credentials_path(tmp_path, monkeypatch):
    """Point the cached login at an empty temporary folder and clear the API environment variables."""
    path = tmp_path / "credentials"
    monkeypatch.setattr("chickenstats.api._auth.CREDENTIALS_PATH", path)
    for name in API_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    return path


@pytest.fixture
def login_api(credentials_path):
    """The SDK with its network calls patched out; yields the mocked LoginApi class."""
    with (
        patch("chickenstats.api.api.chickenstats_api.Configuration"),
        patch("chickenstats.api.api.chickenstats_api.ApiClient"),
        patch("chickenstats.api.api.chickenstats_api.LoginApi") as MockLogin,
    ):
        token = MagicMock()
        token.access_token = "test-token"
        token.refresh_token = "test-refresh-token"
        MockLogin.return_value.login_firebase_token.return_value = token
        yield MockLogin


@pytest.fixture
def cs(login_api):
    """A new ChickenStats instance for each test, logged in with a test username and password."""
    return ChickenStats(username="tester", password="secret")


# -----------------------------------------------------------------------------
# Where the login comes from
# -----------------------------------------------------------------------------


class TestLoginSource:
    def test_username_and_password_are_posted(self, login_api):
        cs = ChickenStats(username="tester", password="secret")

        login_api.return_value.login_firebase_token.assert_called_once_with(
            username="tester", password="secret", _request_timeout=(3.05, 60)
        )
        assert cs.user.access_token == "test-token"
        assert cs.user.refresh_token == "test-refresh-token"

    def test_no_login_raises_a_clear_error(self, login_api):
        """With no username, password or cached login, the client says how to log in instead of posting (R47)."""
        from chickenstats.exceptions import AuthError

        with pytest.raises(AuthError, match="chickenstats login"):
            ChickenStats()

        login_api.return_value.login_firebase_token.assert_not_called()

    def test_a_bad_backend_raises_before_logging_in(self, login_api):
        with pytest.raises(UnsupportedBackendError):
            ChickenStats(username="tester", password="secret", backend="dask")  # ty: ignore[no-matching-overload]

        login_api.return_value.login_firebase_token.assert_not_called()

    def test_a_timeout_reaches_every_request(self, login_api):
        """A stalled connection fails after the timeout instead of blocking for good (N43)."""
        cs = ChickenStats(username="tester", password="secret", timeout=(1, 2))
        api_method = MagicMock(return_value="ok")

        cs._call(api_method, foo=1)

        api_method.assert_called_once_with(foo=1, _request_timeout=(1, 2))
        assert login_api.return_value.login_firebase_token.call_args.kwargs["_request_timeout"] == (1, 2)

    def test_cached_login_is_used_without_logging_in(self, login_api, credentials_path):
        credentials_path.write_text(json.dumps({"access_token": "cached-token", "refresh_token": "cached-refresh"}))

        cs = ChickenStats()

        login_api.return_value.login_firebase_token.assert_not_called()
        assert cs.user.access_token == "cached-token"
        assert cs.user.refresh_token == "cached-refresh"


# -----------------------------------------------------------------------------
# _finalize_dataframe
# -----------------------------------------------------------------------------


class TestFinalizeDataframe:
    def test_polars_returns_polars(self, cs):
        cs.backend = "polars"
        result = cs._finalize_dataframe([{"col": 1}, {"col": 2}])
        assert isinstance(result, pl.DataFrame)

    def test_polars_drops_all_null_columns(self, cs):
        cs.backend = "polars"
        result = cs._finalize_dataframe([{"col": 1, "empty": None}, {"col": 2, "empty": None}])
        assert "empty" not in result.columns

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_pandas_returns_pandas(self, cs):
        cs.backend = "pandas"
        result = cs._finalize_dataframe([{"col": 1}, {"col": 2}])
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
    def test_pandas_drops_all_null_columns(self, cs):
        cs.backend = "pandas"
        result = cs._finalize_dataframe([{"col": 1, "empty": None}, {"col": 2, "empty": None}])
        assert "empty" not in result.columns

    def test_invalid_backend_raises(self, cs):
        cs.backend = "invalid"
        with pytest.raises(UnsupportedBackendError, match="Unsupported backend"):
            cs._finalize_dataframe([{"col": 1}])
        cs.backend = "polars"  # restore


# -----------------------------------------------------------------------------
# _fetch_paginated
# -----------------------------------------------------------------------------


class TestFetchPaginated:
    def test_single_page_returns_all_rows(self, cs):
        rows = [{"a": 1}, {"a": 2}]
        api_method = MagicMock(return_value=_make_page(rows, total=2, has_next=False))
        result = cs._fetch_paginated(
            api_method, limit=100, progress=MagicMock(), progress_task=MagicMock(), pbar_message="test"
        )
        assert result.to_dicts() == rows
        api_method.assert_called_once_with(limit=100, offset=0, _request_timeout=(3.05, 60))

    def test_multi_page_concatenates_all_rows(self, cs):
        page1 = _make_page([{"a": 1}], total=2, has_next=True)
        page2 = _make_page([{"a": 2}], total=2, has_next=False)
        api_method = MagicMock(side_effect=[page1, page2])
        result = cs._fetch_paginated(
            api_method, limit=1, progress=MagicMock(), progress_task=MagicMock(), pbar_message="test"
        )
        assert len(result) == 2
        assert api_method.call_count == 2


class TestPageErrors:
    """A 502 lost the whole download, and the default page size was refused below the contributor tier (bC-02, in-10)."""

    @staticmethod
    def _fetch(cs, api_method, limit=50_000):
        return cs._fetch_paginated(
            api_method, limit=limit, progress=MagicMock(), progress_task=MagicMock(), pbar_message="test"
        )

    @staticmethod
    def _api_error(status, headers=None):
        error = ServiceException(status=status, reason="error")
        error.headers = headers
        return error

    @staticmethod
    def _tier_error(cap):
        detail = f"limit=50000 exceeds the maximum of {cap} rows per request for the 'free' tier."
        return BadRequestException(status=400, reason="Bad Request", body=json.dumps({"detail": detail}))

    @pytest.fixture
    def sleep(self):
        with patch("chickenstats.api.api.time.sleep") as mocked:
            yield mocked

    def test_a_502_on_page_two_recovers(self, cs, sleep):
        pages = [_make_page([{"a": 1}], 2, True), self._api_error(502), _make_page([{"a": 2}], 2, False)]
        api_method = MagicMock(side_effect=pages)

        assert self._fetch(cs, api_method).to_dicts() == [{"a": 1}, {"a": 2}]
        assert [call.kwargs["offset"] for call in api_method.call_args_list] == [0, 1, 1]
        sleep.assert_called_once_with(1)

    def test_a_dropped_connection_recovers(self, cs, sleep):
        pages = [urllib3.exceptions.ProtocolError("reset"), _make_page([{"a": 1}], 1, False)]

        assert self._fetch(cs, MagicMock(side_effect=pages)).to_dicts() == [{"a": 1}]

    @pytest.mark.parametrize(("retry_after", "wait"), [("7", 7.0), ("100000", 60.0), ("soon", 1)])
    def test_a_429_waits_for_retry_after(self, cs, sleep, retry_after, wait):
        pages = [self._api_error(429, {"Retry-After": retry_after}), _make_page([], 0, False)]
        self._fetch(cs, MagicMock(side_effect=pages))

        sleep.assert_called_once_with(wait)

    def test_the_retries_are_capped_and_the_error_has_the_offset(self, cs, sleep):
        pages = [_make_page([{"a": 1}], 2, True), *[self._api_error(503) for _ in range(4)]]
        api_method = MagicMock(side_effect=pages)

        with pytest.raises(APIDownloadError, match="stopped at offset 1") as error:
            self._fetch(cs, api_method)

        assert (error.value.offset, error.value.status) == (1, 503)
        assert api_method.call_count == 5
        assert [call.args[0] for call in sleep.call_args_list] == [1, 2, 4]

    def test_a_500_is_not_retried(self, cs, sleep):
        api_method = MagicMock(side_effect=self._api_error(500))

        with pytest.raises(ServiceException):
            self._fetch(cs, api_method)

        assert api_method.call_count == 1

    def test_a_tier_below_the_default_gets_its_own_page_size(self, cs):
        pages = [self._tier_error(1000), _make_page([{"a": 1}], 2, True), _make_page([{"a": 2}], 2, False)]
        api_method = MagicMock(side_effect=pages)

        assert self._fetch(cs, api_method).to_dicts() == [{"a": 1}, {"a": 2}]
        assert [call.kwargs["limit"] for call in api_method.call_args_list] == [50_000, 1000, 1000]

    def test_the_tier_page_size_lasts_for_the_session(self, cs):
        self._fetch(cs, MagicMock(side_effect=[self._tier_error(1000), _make_page([], 0, False)]))

        api_method = MagicMock(return_value=_make_page([], 0, False))
        self._fetch(cs, api_method)

        assert api_method.call_args.kwargs["limit"] == 1000

    def test_a_limit_the_caller_chose_is_left_alone(self, cs):
        cs.limit = 50_000
        api_method = MagicMock(side_effect=self._tier_error(1000))

        with pytest.raises(BadRequestException):
            self._fetch(cs, api_method)

        assert api_method.call_count == 1

    def test_any_other_400_is_raised(self, cs):
        error = BadRequestException(status=400, reason="Bad Request", body=json.dumps({"detail": "bad season"}))

        with pytest.raises(BadRequestException):
            self._fetch(cs, MagicMock(side_effect=error))


class TestPageFrames:
    """pl.DataFrame read 100 rows, so a column of leading nulls crashed on its first value (bC-01)."""

    @staticmethod
    def _fetch(cs, pages):
        return cs._fetch_paginated(
            MagicMock(side_effect=pages),
            limit=100,
            progress=MagicMock(),
            progress_task=MagicMock(),
            pbar_message="test",
        )

    def test_a_column_of_leading_nulls_keeps_its_values(self, cs):
        rows = [{"xg": None} for _ in range(200)] + [{"xg": 0}, {"xg": 0.5}]

        result = self._fetch(cs, [_make_page(rows, 202, False)])

        assert result.schema["xg"] == pl.Float64
        assert result["xg"].tail(2).to_list() == [0.0, 0.5]

    def test_pages_with_different_types_combine(self, cs):
        pages = [
            _make_page([{"id": 1, "xg": None}], 3, True),
            _make_page([{"id": 2, "xg": 1}], 3, True),
            _make_page([{"id": 3, "xg": 0.5}], 3, False),
        ]

        result = self._fetch(cs, pages)

        assert result["id"].to_list() == [1, 2, 3]
        assert result["xg"].to_list() == [None, 1.0, 0.5]

    def test_a_last_empty_page_is_ignored(self, cs):
        pages = [_make_page([{"id": 1}], 1, True), _make_page([], 1, False)]

        assert self._fetch(cs, pages).to_dicts() == [{"id": 1}]

    def test_a_download_with_no_rows_is_empty(self, cs):
        assert self._fetch(cs, [_make_page([], 0, False)]).is_empty()


# -----------------------------------------------------------------------------
# _call — 401 auto-refresh
# -----------------------------------------------------------------------------


def _unauthorized():
    """Build an UnauthorizedException without needing a real HTTP response."""
    return UnauthorizedException(status=401, reason="Unauthorized")


class TestCallRefreshesOn401:
    def test_passes_through_when_no_error(self, cs):
        api_method = MagicMock(return_value="ok")
        assert cs._call(api_method, foo=1) == "ok"
        api_method.assert_called_once_with(foo=1, _request_timeout=(3.05, 60))

    def test_refreshes_and_retries_once_on_401(self, cs):
        api_method = MagicMock(side_effect=[_unauthorized(), "ok"])
        with patch.object(cs.user, "refresh") as mock_refresh:
            cs.user.refresh_token = "refresh-token"
            assert cs._call(api_method) == "ok"
            mock_refresh.assert_called_once()
        assert api_method.call_count == 2

    def test_raises_without_refresh_token(self, cs):
        api_method = MagicMock(side_effect=_unauthorized())
        with patch.object(cs.user, "refresh") as mock_refresh:
            cs.user.refresh_token = None
            with pytest.raises(UnauthorizedException):
                cs._call(api_method)
            mock_refresh.assert_not_called()
        assert api_method.call_count == 1

    def test_does_not_retry_twice(self, cs):
        """A 401 that survives the refresh propagates instead of looping."""
        api_method = MagicMock(side_effect=[_unauthorized(), _unauthorized()])
        with patch.object(cs.user, "refresh"):
            cs.user.refresh_token = "refresh-token"
            with pytest.raises(UnauthorizedException):
                cs._call(api_method)
        assert api_method.call_count == 2


# -----------------------------------------------------------------------------
# Live endpoint tests — require credentials and a running API
# Run with: pytest -m live
#
# Each one checks a fact about a finished game or season that cannot change.
# Game 2023020001 is NSH at TBL on 2023-10-10, a 5-3 TBL win in regulation.
# -----------------------------------------------------------------------------

LIVE_GAME_ID = 2023020001


def _has_api_credentials() -> bool:
    """Return True when a cached login, a username and password, or a Cloudflare service token is available."""
    from chickenstats.api._auth import CREDENTIALS_PATH

    def env(name):
        return os.environ.get(name)

    password = env("CHICKENSTATS_API_USERNAME") and env("CHICKENSTATS_API_PASSWORD")
    service_token = env("CHICKENSTATS_API_CF_CLIENT_ID") and env("CHICKENSTATS_API_CF_CLIENT_SECRET")
    return bool(CREDENTIALS_PATH.exists() or password or service_token)


@pytest.fixture(scope="class")
def live_api():
    """One logged-in client for the live tests."""
    return ChickenStats()


@pytest.mark.live
@pytest.mark.skipif(
    not _has_api_credentials(),
    reason="no chickenstats API credentials: run `chickenstats login`, or set CHICKENSTATS_API_USERNAME and "
    "CHICKENSTATS_API_PASSWORD, or CHICKENSTATS_API_CF_CLIENT_ID and CHICKENSTATS_API_CF_CLIENT_SECRET",
)
class TestChickenStatsLive:
    @staticmethod
    def _assert_regular_season_2023(game_ids):
        assert sorted(game_ids) == list(range(2023020001, 2023021313))

    def test_check_pbp_game_ids(self, live_api):
        """32 teams playing 82 games is 1312 games, which also shows the ID pages are not cut short."""
        game_ids = live_api.check_pbp_game_ids(season=[20232024], sessions=["R"])
        self._assert_regular_season_2023(game_ids)

    def test_check_stats_game_ids(self, live_api):
        self._assert_regular_season_2023(live_api.check_stats_game_ids(season=[20232024], sessions=["R"]))

    def test_check_team_stats_game_ids(self, live_api):
        self._assert_regular_season_2023(live_api.check_team_stats_game_ids(season=[20232024], sessions=["R"]))

    def test_check_lines_game_ids(self, live_api):
        self._assert_regular_season_2023(live_api.check_lines_game_ids(season=[20232024], sessions=["R"]))

    def test_check_roster_game_ids(self, live_api):
        game_ids = live_api.check_roster_game_ids()
        assert LIVE_GAME_ID in game_ids
        assert len(game_ids) == len(set(game_ids))

    def test_check_pbp_play_ids_match_the_play_by_play(self, live_api):
        play_ids = live_api.check_pbp_play_ids(game_id=[LIVE_GAME_ID])
        pbp = live_api.download_pbp(game_id=[LIVE_GAME_ID], disable_progress_bar=True)

        assert len(play_ids) == len(set(play_ids)) == pbp.height
        assert set(play_ids) == set(pbp["id"].to_list())

    def test_download_pbp(self, live_api):
        goals = live_api.download_pbp(game_id=[LIVE_GAME_ID], event=["GOAL"], disable_progress_bar=True)

        assert {"id", "game_id", "event", "event_team", "strength_state"} <= set(goals.columns)
        assert goals["game_id"].unique().to_list() == [LIVE_GAME_ID]
        assert goals["event"].unique().to_list() == ["GOAL"]
        assert goals["event_team"].value_counts().sort("event_team").rows() == [("NSH", 3), ("TBL", 5)]

    def test_download_game_stats(self, live_api):
        stats = live_api.download_game_stats(game_id=[LIVE_GAME_ID], disable_progress_bar=True)

        assert {"game_id", "api_id", "team", "strength_state", "toi"} <= set(stats.columns)
        assert stats["game_id"].unique().to_list() == [LIVE_GAME_ID]
        assert stats["api_id"].n_unique() == 38
        assert set(stats["team"].unique().to_list()) == {"NSH", "TBL"}

    def test_download_rapm(self, live_api):
        rapm = live_api.download_rapm(season=[20242025], disable_progress_bar=True)

        assert not rapm.is_empty()
        assert {"api_id", "season", "rapm_off", "rapm_def"} <= set(rapm.columns)
        assert rapm["season"].unique().to_list() == [20242025]

    def test_download_pred_goal(self, live_api):
        pred_goal = live_api.download_pred_goal(season=[20242025], game_id=[2024020001], disable_progress_bar=True)

        assert not pred_goal.is_empty()
        assert pred_goal["game_id"].unique().to_list() == [2024020001]
        assert pred_goal["pred_goal"].is_between(0, 1).all()

    def test_get_live_games(self, live_api):
        games = live_api.get_live_games()

        assert isinstance(games, pl.DataFrame)
        if not games.is_empty():
            assert {"game_id", "home_team", "away_team", "game_state"} <= set(games.columns)

    def test_download_live_pbp(self, live_api):
        pbp = live_api.download_live_pbp(disable_progress_bar=True)

        assert isinstance(pbp, pl.DataFrame)
        if not pbp.is_empty():
            assert {"id", "game_id", "event"} <= set(pbp.columns)

    def test_download_rosters(self, live_api):
        rosters = live_api.download_rosters(game_id=[LIVE_GAME_ID], disable_progress_bar=True)

        assert rosters["game_id"].unique().to_list() == [LIVE_GAME_ID]
        assert set(rosters["team"].unique().to_list()) == {"NSH", "TBL"}
        assert rosters["api_id"].n_unique() >= 38

    def test_download_shifts(self, live_api):
        shifts = live_api.download_shifts(game_id=[LIVE_GAME_ID], disable_progress_bar=True)

        assert shifts["game_id"].unique().to_list() == [LIVE_GAME_ID]
        assert set(shifts["team"].unique().to_list()) == {"NSH", "TBL"}
        assert shifts["api_id"].n_unique() == 38

    def test_download_changes(self, live_api):
        changes = live_api.download_changes(game_id=[LIVE_GAME_ID], disable_progress_bar=True)

        assert changes["game_id"].unique().to_list() == [LIVE_GAME_ID]
        assert set(changes["event_team"].unique().to_list()) == {"NSH", "TBL"}

    def test_download_games(self, live_api):
        games = live_api.download_games(season=[20232024], sessions=["R"], team=["NSH"], disable_progress_bar=True)

        assert games.height == 82
        assert ((games["home_team"] == "NSH") | (games["away_team"] == "NSH")).all()
        assert LIVE_GAME_ID in games["game_id"].to_list()

    def test_download_players(self, live_api):
        players = live_api.download_players(name=["FILIP FORSBERG", "ROMAN JOSI"], disable_progress_bar=True)

        assert set(players["api_id"].to_list()) == {8476887, 8474600}


def test_the_network_guard_stops_urllib3(blocked_urls):
    """The API SDK calls urllib3 directly, so the guard has to cover it as well as requests."""
    with pytest.raises(urllib3.exceptions.HTTPError, match="network access is blocked"):
        urllib3.PoolManager().request("GET", "https://api.chickenstats.com/health")

    assert blocked_urls == ["https://api.chickenstats.com/health"]
    blocked_urls.clear()
