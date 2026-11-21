"""The saved login and its file, with the SDK's network calls replaced."""

import json
import os
import stat
import subprocess
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from chickenstats.api._auth import (
    Credentials,
    build_api_client,
    clear_credentials,
    credentials_lock,
    device_login,
    load_cached_credentials,
    oauth_error,
    require_secure_host,
    revoke_saved_login,
    same_host,
    save_credentials,
    token_login,
    with_saved_login,
)
from chickenstats.api.api import ChickenStats, ChickenUser
from chickenstats_api import OAuthError
from chickenstats_api.exceptions import (
    ApiException,
    BadRequestException,
    ForbiddenException,
    ServiceException,
    UnauthorizedException,
)
from chickenstats.exceptions import AuthError

ENV_VARS = [
    "CHICKENSTATS_API_TOKEN",
    "CHICKENSTATS_API_HOST",
    "HTTPS_PROXY",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
]

STAGING = "https://staging.example.com"


@pytest.fixture
def credentials_path(tmp_path, monkeypatch):
    """Point the cached login at an empty temporary folder and clear the API environment variables."""
    path = tmp_path / "home" / "credentials"
    monkeypatch.setattr("chickenstats.api._auth.CREDENTIALS_PATH", path)
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    return path


@pytest.fixture
def cached(credentials_path):
    """A cached login for the default host."""
    save_credentials(Credentials("cached-access", "cached-refresh", "a@b.c"))
    return credentials_path


@pytest.fixture
def server():
    """A refresh endpoint that, like the real one, revokes a refresh token when it is used."""

    class Server:
        valid = "cached-refresh"
        calls = 0

        def refresh(self, refresh_token, host, proxy=None, ca_bundle=None):
            self.calls += 1
            time.sleep(0.05)
            if refresh_token != self.valid:
                raise AuthError("Refresh token rejected")
            self.valid = f"refresh-{self.calls}"
            return {"access_token": f"access-{self.calls}", "refresh_token": self.valid}

    fake = Server()
    with patch("chickenstats.api._auth.refresh_access_token", fake.refresh):
        yield fake


def _saved() -> Credentials:
    """Return the cached login, which a test expects to exist."""
    credentials = load_cached_credentials()
    assert credentials is not None
    return credentials


class TestHosts:
    @pytest.mark.parametrize(
        "host", ["https://api.chickenstats.com", "http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"]
    )
    def test_https_or_a_local_server_is_allowed(self, host):
        require_secure_host(host)

    @pytest.mark.parametrize("host", ["http://api.chickenstats.com", "http://localhost.example.com", "api.example.com"])
    def test_anything_else_is_refused(self, host):
        with pytest.raises(AuthError, match="Refusing to send credentials"):
            require_secure_host(host)

    def test_same_host_ignores_case_and_a_trailing_slash(self):
        assert same_host("https://API.chickenstats.com/", "https://api.chickenstats.com")
        assert not same_host(STAGING, "https://api.chickenstats.com")

    def test_a_cached_login_goes_to_the_host_it_was_made_on(self, credentials_path):
        save_credentials(Credentials("cached-access", "cached-refresh", host=STAGING))

        user = ChickenUser()

        assert user.host == STAGING
        assert user.access_token == "cached-access"

    def test_a_cached_login_is_refused_for_another_host(self, cached, monkeypatch):
        monkeypatch.setenv("CHICKENSTATS_API_HOST", STAGING)

        with pytest.raises(AuthError, match="saved login is for https://api.chickenstats.com"):
            ChickenUser()

    def test_a_token_is_never_sent_over_plain_http(self, credentials_path):
        with pytest.raises(AuthError, match="Refusing"):
            ChickenUser(token="cs_named", host="http://api.example.com")

    def test_a_cached_host_on_plain_http_is_refused(self, credentials_path):
        save_credentials(Credentials("cached-access", "cached-refresh", host="http://api.example.com"))

        with pytest.raises(AuthError, match="Refusing"):
            ChickenUser()


class TestCredentialsFile:
    def test_round_trip(self, credentials_path):
        save_credentials(Credentials("access", "refresh", "a@b.c", STAGING))

        assert load_cached_credentials() == Credentials("access", "refresh", "a@b.c", STAGING)

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
    def test_the_tokens_are_private_from_creation(self, credentials_path):
        modes = []
        replace = os.replace

        def record_mode(source, target):
            modes.append(stat.S_IMODE(os.stat(source).st_mode))
            replace(source, target)

        with patch("chickenstats.api._auth.os.replace", record_mode):
            save_credentials(Credentials("access", "refresh"))

        assert modes == [0o600]
        assert stat.S_IMODE(credentials_path.stat().st_mode) == 0o600
        assert stat.S_IMODE(credentials_path.parent.stat().st_mode) == 0o700

    def test_a_failed_write_keeps_the_old_file(self, cached):
        with patch("chickenstats.api._auth.os.replace", side_effect=OSError("disk full")), pytest.raises(OSError):
            save_credentials(Credentials("new-access", "new-refresh"))

        assert _saved().access_token == "cached-access"
        assert sorted(path.name for path in cached.parent.iterdir()) == ["credentials"]

    def test_no_file_is_no_login(self, credentials_path):
        assert load_cached_credentials() is None

    @pytest.mark.parametrize(
        "text", ["{not json", "[]", '{"refresh_token": "refresh"}', ""], ids=["bad-json", "list", "no-access", "empty"]
    )
    def test_a_corrupt_file_is_no_login(self, credentials_path, text):
        credentials_path.parent.mkdir(parents=True)
        credentials_path.write_text(text)

        assert load_cached_credentials() is None

    def test_a_file_without_a_host_is_for_the_public_api(self, credentials_path):
        credentials_path.parent.mkdir(parents=True)
        credentials_path.write_text(json.dumps({"access_token": "access", "refresh_token": "refresh"}))

        assert load_cached_credentials() == Credentials("access", "refresh", None, "https://api.chickenstats.com")

    def test_a_named_token_is_saved_with_no_refresh_token(self, credentials_path):
        save_credentials(Credentials("cs_1a2b3c4d_secret", None, "a@b.c"))

        assert load_cached_credentials() == Credentials("cs_1a2b3c4d_secret", None, "a@b.c")

    def test_clearing_removes_the_file(self, cached):
        clear_credentials()

        assert not cached.exists()
        assert load_cached_credentials() is None

    def test_clearing_with_no_file_does_nothing(self, credentials_path):
        clear_credentials()

        assert not credentials_path.exists()


class TestRefresh:
    def test_a_refresh_rewrites_the_file_it_came_from(self, cached, server):
        user = ChickenUser()

        user.refresh()

        assert load_cached_credentials() == Credentials("access-1", "refresh-1", "a@b.c")
        assert user.configuration.access_token == "access-1"

    def test_a_refresh_keeps_a_file_for_another_host(self, cached, server):
        user = ChickenUser()
        save_credentials(Credentials("other-access", "other-refresh", host=STAGING))

        user.refresh()

        assert _saved().host == STAGING
        assert _saved().access_token == "other-access"

    def test_a_refresh_does_not_bring_back_a_logged_out_file(self, cached, server):
        user = ChickenUser()
        cached.unlink()

        user.refresh()

        assert not cached.exists()

    def test_no_refresh_token_raises_auth_error(self, credentials_path):
        user = ChickenUser(token="cs_named")

        with pytest.raises(AuthError, match="No refresh token"):
            user.refresh()

    def test_a_rotated_token_is_taken_from_the_file(self, cached, server):
        """Another process used the token first, so this one must not send it again."""
        user = ChickenUser()
        save_credentials(Credentials("their-access", "their-refresh", "a@b.c"))

        user.refresh()

        assert server.calls == 0
        assert user.access_token == "their-access"
        assert user.refresh_token == "their-refresh"

    def test_two_threads_sharing_a_user_refresh_once(self, cached, server):
        user = ChickenUser()
        barrier = threading.Barrier(8)

        def refresh():
            barrier.wait()
            user.refresh()

        threads = [threading.Thread(target=refresh) for _ in range(8)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert server.calls == 1
        assert _saved().access_token == user.access_token

    def test_two_users_in_one_process_both_succeed(self, cached, server):
        users = [ChickenUser(), ChickenUser()]
        errors = []

        def refresh(user):
            try:
                user.refresh()
            except AuthError as exc:
                errors.append(exc)

        threads = [threading.Thread(target=refresh, args=(user,)) for user in users]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors
        assert users[0].refresh_token == users[1].refresh_token == server.valid

    def test_two_processes_refreshing_together_both_succeed(self, cached, tmp_path):
        valid = tmp_path / "valid"
        valid.write_text("cached-refresh")
        go = tmp_path / "go"
        script = tmp_path / "refresh.py"
        script.write_text(_TWO_PROCESSES_SCRIPT)

        processes = [
            subprocess.Popen(
                [sys.executable, str(script), str(cached), str(valid), str(go), str(tmp_path / f"ready{number}")],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
            )
            for number in range(2)
        ]
        for number in range(2):
            _wait_for(tmp_path / f"ready{number}")
        go.touch()

        results = [process.communicate(timeout=30) for process in processes]

        assert [process.returncode for process in processes] == [0, 0], results
        assert results[0][0] == results[1][0]
        assert json.loads(cached.read_text())["refresh_token"] == valid.read_text()

    def test_a_read_only_file_keeps_the_login_in_memory(self, cached, server):
        user = ChickenUser()

        with (
            patch("chickenstats.api._auth.save_credentials", side_effect=PermissionError("read-only")),
            pytest.warns(UserWarning, match="Could not save the refreshed chickenstats login"),
        ):
            user.refresh()

        assert user.access_token == "access-1"
        assert user.refresh_token == "refresh-1"

        with (
            patch("chickenstats.api._auth.save_credentials", side_effect=PermissionError("read-only")),
            pytest.warns(UserWarning, match="Could not save"),
        ):
            user.refresh()

        assert user.access_token == "access-2"
        assert server.calls == 2

    def test_a_folder_that_cannot_hold_a_lock_file_still_refreshes(self, cached, server):
        user = ChickenUser()
        real_open = os.open

        def refuse_the_lock_file(path, *args, **kwargs):
            if str(path).endswith(".lock"):
                raise PermissionError("read-only")
            return real_open(path, *args, **kwargs)

        with patch("chickenstats.api._auth.os.open", side_effect=refuse_the_lock_file):
            user.refresh()

        assert user.access_token == "access-1"


_TWO_PROCESSES_SCRIPT = """
import pathlib
import sys
import time
from unittest.mock import patch

from chickenstats.api import _auth
from chickenstats.api.api import ChickenUser
from chickenstats.exceptions import AuthError

credentials, valid, go, ready = map(pathlib.Path, sys.argv[1:])
_auth.CREDENTIALS_PATH = credentials


def refresh(refresh_token, host, proxy=None, ca_bundle=None):
    if refresh_token != valid.read_text():
        raise AuthError("Refresh token rejected")
    time.sleep(0.3)
    token = f"refresh-{time.monotonic_ns()}"
    valid.write_text(token)
    return {"access_token": f"access-{token}", "refresh_token": token}


user = ChickenUser()
ready.touch()
while not go.exists():
    time.sleep(0.01)

with patch.object(_auth, "refresh_access_token", refresh):
    user.refresh()
print(user.refresh_token)
"""


def _wait_for(path, seconds=30):
    """Wait for a child process to create a file."""
    deadline = time.monotonic() + seconds
    while not path.exists():
        assert time.monotonic() < deadline, f"{path} did not appear"
        time.sleep(0.01)


class TestLock:
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX file locks")
    def test_the_lock_file_is_private(self, credentials_path):
        with credentials_lock():
            lock = credentials_path.with_name("credentials.lock")
            assert stat.S_IMODE(lock.stat().st_mode) == 0o600


class TestTransport:
    def test_the_user_agent_names_chickenstats(self, credentials_path):
        assert build_api_client("https://api.chickenstats.com").user_agent.startswith("chickenstats/")

    def test_a_proxy_comes_from_the_environment(self, credentials_path, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:3128")

        assert build_api_client(STAGING).configuration.proxy == "http://proxy.example.com:3128"

    def test_no_proxy_is_respected(self, credentials_path, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:3128")
        monkeypatch.setenv("NO_PROXY", "staging.example.com")

        assert build_api_client(STAGING).configuration.proxy is None

    def test_an_argument_beats_the_environment(self, credentials_path, monkeypatch):
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.com:3128")
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/env/ca.pem")

        configuration = build_api_client(STAGING, "http://mine:1", "/my/ca.pem").configuration

        assert configuration.proxy == "http://mine:1"
        assert configuration.ssl_ca_cert == "/my/ca.pem"

    @pytest.mark.parametrize("name", ["REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"])
    def test_a_ca_bundle_comes_from_the_environment(self, credentials_path, monkeypatch, name):
        monkeypatch.setenv(name, "/env/ca.pem")

        assert build_api_client(STAGING).configuration.ssl_ca_cert == "/env/ca.pem"

    def test_chicken_stats_passes_them_to_its_client(self, cached):
        cs = ChickenStats(proxy="http://mine:1", ca_bundle="/my/ca.pem")

        assert cs.user.configuration.proxy == "http://mine:1"
        assert cs.user.configuration.ssl_ca_cert == "/my/ca.pem"


def _oauth(exception, status, error, **fields):
    """Build an SDK error carrying an OAuth error body, as the generated client raises it."""
    return exception(status=status, reason="refused", data=OAuthError(error=error, **fields))


class TestOAuthError:
    def test_reads_the_parsed_error(self):
        assert oauth_error(_oauth(BadRequestException, 400, "invalid_grant", error_description="nope")) == (
            "invalid_grant",
            "nope",
        )

    def test_reads_the_body_when_the_sdk_did_not_parse_it(self):
        body = json.dumps({"error": "invalid_client", "error_description": "Unknown client."})
        exc = UnauthorizedException(status=401, reason="Unauthorized", body=body)

        assert oauth_error(exc) == ("invalid_client", "Unknown client.")

    def test_a_detail_that_is_not_text_is_ignored(self):
        exc = UnauthorizedException(status=401, reason="Unauthorized", body=json.dumps({"detail": [{"loc": "x"}]}))

        assert oauth_error(exc) == (None, None)

    @pytest.mark.parametrize("body", [None, "", "not json", "[1, 2]"])
    def test_a_body_without_an_error_gives_nothing(self, body):
        assert oauth_error(UnauthorizedException(status=401, reason="Unauthorized", body=body)) == (None, None)


class TestDeviceLogin:
    @staticmethod
    def _device():
        return MagicMock(
            device_code="device-1",
            user_code="BDFG-HJKL",
            verification_uri="https://chickenstats.com/device",
            verification_uri_complete="https://chickenstats.com/device?user_code=BDFG-HJKL",
            interval=5,
        )

    def test_it_polls_until_approved_and_slows_down_when_asked(self, credentials_path):
        shown, waits = [], []
        token = MagicMock(access_token="access", refresh_token="refresh")
        with patch("chickenstats_api.AuthApi") as auth:
            auth.return_value.start_device_sign_in.return_value = self._device()
            auth.return_value.get_token.side_effect = [
                _oauth(BadRequestException, 400, "authorization_pending"),
                _oauth(BadRequestException, 400, "slow_down"),
                token,
            ]
            auth.return_value.whoami.return_value = MagicMock(kind="session", email="a@b.c")
            creds = device_login(show=lambda uri, code: shown.append((uri, code)), sleep=waits.append)

        assert shown == [("https://chickenstats.com/device?user_code=BDFG-HJKL", "BDFG-HJKL")]
        assert waits == [5, 5, 10]
        assert creds == Credentials("access", "refresh", "a@b.c", "https://api.chickenstats.com")
        assert auth.return_value.get_token.call_args.kwargs == {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": "device-1",
            "_request_timeout": (3.05, 60),
        }

    def test_a_busy_or_unavailable_server_is_waited_out(self, credentials_path):
        token = MagicMock(access_token="access", refresh_token="refresh")
        with patch("chickenstats_api.AuthApi") as auth, patch("chickenstats_api.UsersApi"):
            auth.return_value.start_device_sign_in.return_value = self._device()
            auth.return_value.get_token.side_effect = [
                ApiException(status=429, reason="Too Many Requests"),
                ServiceException(status=503, reason="Service Unavailable"),
                token,
            ]
            creds = device_login(show=lambda uri, code: None, sleep=lambda seconds: None)

        assert creds.refresh_token == "refresh"

    @pytest.mark.parametrize(("error", "message"), [("access_denied", "denied"), ("expired_token", "expired")])
    def test_a_denied_or_expired_code_stops(self, credentials_path, error, message):
        with patch("chickenstats_api.AuthApi") as auth, pytest.raises(AuthError, match=message):
            auth.return_value.start_device_sign_in.return_value = self._device()
            auth.return_value.get_token.side_effect = _oauth(BadRequestException, 400, error)
            device_login(show=lambda uri, code: None, sleep=lambda seconds: None)

    def test_a_login_with_no_refresh_token_asks_for_a_verified_email(self, credentials_path):
        with patch("chickenstats_api.AuthApi") as auth, pytest.raises(AuthError, match="Verify your email"):
            auth.return_value.start_device_sign_in.return_value = self._device()
            auth.return_value.get_token.return_value = MagicMock(access_token="access", refresh_token=None)
            device_login(show=lambda uri, code: None, sleep=lambda seconds: None)


class TestNamedTokens:
    @staticmethod
    def _whoami(kind):
        return MagicMock(kind=kind, tier="free", prefix="cs_1a2b3c4d" if kind == "named" else None)

    def test_a_token_is_checked_with_whoami_and_kept(self, credentials_path):
        with patch("chickenstats_api.AuthApi") as auth:
            auth.return_value.whoami.return_value = self._whoami("named")
            creds = token_login("cs_1a2b3c4d_secret", host=STAGING)

        auth.return_value.whoami.assert_called_once()
        assert creds == Credentials("cs_1a2b3c4d_secret", None, None, STAGING)

    def test_a_refused_token_raises(self, credentials_path):
        revoked = _oauth(UnauthorizedException, 401, "invalid_token", error_description="named_token_revoked")
        with patch("chickenstats_api.AuthApi") as auth, pytest.raises(AuthError, match="named_token_revoked"):
            auth.return_value.whoami.side_effect = revoked
            token_login("cs_1a2b3c4d_secret")

    def test_a_session_token_is_not_saved_as_a_named_one(self, credentials_path):
        with patch("chickenstats_api.AuthApi") as auth, pytest.raises(AuthError, match="not a named API token"):
            auth.return_value.whoami.return_value = self._whoami("session")
            token_login("eyJ.session.jwt")

    @pytest.mark.parametrize(
        ("reason", "message"),
        [("named_token_expired", "has expired"), ("named_token_revoked", "was revoked"), (None, "was rejected")],
    )
    def test_a_rejected_named_token_says_why_and_is_not_refreshed(self, credentials_path, reason, message):
        user = ChickenUser(token="cs_1a2b3c4d_secret")
        rejected = _oauth(UnauthorizedException, 401, "invalid_token", error_description=reason)

        with patch.object(user, "refresh") as refresh, pytest.raises(AuthError, match=message):
            user._call(MagicMock(side_effect=rejected))

        refresh.assert_not_called()

    def test_a_route_needing_a_recent_sign_in_is_not_refreshed(self, cached):
        user = ChickenUser()
        needs = _oauth(UnauthorizedException, 401, "invalid_token", error_description="recent_sign_in_required")

        with patch.object(user, "refresh") as refresh, pytest.raises(AuthError, match="recent sign-in"):
            user._call(MagicMock(side_effect=needs))

        refresh.assert_not_called()

    def test_a_saved_token_is_used_as_a_token(self, credentials_path):
        save_credentials(Credentials("cs_1a2b3c4d_secret", None, "a@b.c"))
        user = ChickenUser()
        revoked = _oauth(UnauthorizedException, 401, "invalid_token", error_description="token_revoked")

        with pytest.raises(AuthError, match="account/api"):
            user._call(MagicMock(side_effect=revoked))

        assert user.token == "cs_1a2b3c4d_secret"


class TestSavedLoginCalls:
    def test_an_expired_session_is_refreshed_saved_and_retried(self, cached, server):
        expired = _oauth(UnauthorizedException, 401, "invalid_token", error_description="token_expired")
        sent = []

        def call(api_client):
            sent.append(api_client.configuration.access_token)
            if len(sent) == 1:
                raise expired
            return "ok"

        assert with_saved_login(_saved(), call) == "ok"
        assert sent == ["cached-access", "access-1"]
        assert _saved() == Credentials("access-1", "refresh-1", "a@b.c")

    def test_a_login_another_process_refreshed_is_used_without_refreshing_again(self, cached, server):
        expired = _oauth(UnauthorizedException, 401, "invalid_token", error_description="token_expired")
        stale = _saved()
        save_credentials(Credentials("access-new", "refresh-new", "a@b.c"))
        sent = []

        def call(api_client):
            sent.append(api_client.configuration.access_token)
            if len(sent) == 1:
                raise expired
            return "ok"

        assert with_saved_login(stale, call) == "ok"
        assert sent == ["cached-access", "access-new"]
        assert server.calls == 0

    def test_the_reason_is_read_from_the_header_when_the_body_has_none(self, cached, server):
        expired = UnauthorizedException(status=401, reason="Unauthorized", body="")
        expired.headers = {"WWW-Authenticate": 'Bearer error="invalid_token", error_description="token_expired"'}
        sent = []

        def call(api_client):
            sent.append(api_client.configuration.access_token)
            if len(sent) == 1:
                raise expired
            return "ok"

        assert with_saved_login(_saved(), call) == "ok"
        assert sent == ["cached-access", "access-1"]

    def test_a_revoked_session_asks_to_sign_in(self, cached, server):
        revoked = _oauth(UnauthorizedException, 401, "invalid_token", error_description="token_revoked")

        with pytest.raises(AuthError, match="chickenstats login"):
            with_saved_login(_saved(), MagicMock(side_effect=revoked))

        assert server.calls == 0

    def test_signing_out_revokes_the_refresh_token(self, cached):
        with patch("chickenstats_api.AuthApi") as auth:
            revoke_saved_login(_saved())

        assert auth.return_value.revoke_token.call_args.kwargs["token"] == "cached-refresh"

    def test_a_saved_named_token_is_not_revoked_by_signing_out(self, credentials_path):
        with patch("chickenstats_api.AuthApi") as auth:
            revoke_saved_login(Credentials("cs_1a2b3c4d_secret", None))

        auth.return_value.revoke_token.assert_not_called()

    def test_logout_revokes_and_removes_the_saved_login(self, cached):
        user = ChickenUser()
        with patch("chickenstats_api.AuthApi") as auth:
            user.logout()

        assert auth.return_value.revoke_token.call_args.kwargs["token"] == "cached-refresh"
        assert not cached.exists()
        assert user.access_token == ""

    def test_logout_everywhere_ends_every_session(self, cached):
        user = ChickenUser()
        with patch("chickenstats_api.AuthApi") as auth:
            user.logout(everywhere=True)

        auth.return_value.end_all_sessions.assert_called_once()
        assert not cached.exists()
