"""The cached login, its file and the browser sign-in page, with the SDK's network calls replaced."""

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
    _callback_page,
    _exchange_firebase_for_local,
    browser_login,
    build_api_client,
    credentials_lock,
    load_cached_credentials,
    password_login,
    require_secure_host,
    same_host,
    save_credentials,
)
from chickenstats.api.api import ChickenStats, ChickenUser
from chickenstats.exceptions import AuthError

ENV_VARS = [
    "CHICKENSTATS_API_USERNAME",
    "CHICKENSTATS_API_PASSWORD",
    "CHICKENSTATS_API_HOST",
    "CHICKENSTATS_API_CF_CLIENT_ID",
    "CHICKENSTATS_API_CF_CLIENT_SECRET",
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


def _password_sign_in():
    password_login("a@b.c", "secret")


def _google_sign_in():
    _exchange_firebase_for_local("firebase-id-token", "https://api.chickenstats.com")


def _saved() -> Credentials:
    """Return the cached login, which a test expects to exist."""
    credentials = load_cached_credentials()
    assert credentials is not None
    return credentials


class TestCallbackPage:
    def test_renders_without_any_web_framework(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "fasthtml", None)
        monkeypatch.setitem(sys.modules, "fasthtml.common", None)

        page = _callback_page("Signed in", "You're signed in", "Close this tab.")

        assert page.startswith("<!doctype html>")
        assert "<title>Signed in</title>" in page
        assert "<p>Close this tab.</p>" in page

    @pytest.mark.parametrize("position", [0, 1, 2])
    def test_escapes_the_text(self, position):
        text = ["title", "heading", "message"]
        text[position] = "<script>"

        assert "<script>" not in _callback_page(*text)


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

        with pytest.raises(AuthError, match="cached login is for https://api.chickenstats.com"):
            ChickenUser()

    def test_a_password_is_never_sent_over_plain_http(self, credentials_path):
        with patch("chickenstats_api.LoginApi") as login_api, pytest.raises(AuthError, match="Refusing"):
            ChickenUser(username="tester", password="secret", host="http://api.example.com")

        login_api.assert_not_called()

    def test_a_cached_host_on_plain_http_is_refused(self, credentials_path):
        save_credentials(Credentials("cached-access", "cached-refresh", host="http://api.example.com"))

        with pytest.raises(AuthError, match="Refusing"):
            ChickenUser()

    def test_password_login_refuses_plain_http(self, credentials_path):
        with pytest.raises(AuthError, match="Refusing"):
            password_login("a@b.c", "secret", host="http://api.example.com")

    def test_browser_login_refuses_plain_http_before_opening_a_browser(self, credentials_path):
        with patch("chickenstats.api._auth.webbrowser.open") as browser, pytest.raises(AuthError, match="Refusing"):
            browser_login(host="http://api.example.com")

        browser.assert_not_called()


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


class TestRefresh:
    def test_a_refresh_rewrites_the_file_it_came_from(self, cached, server):
        user = ChickenUser()

        user.refresh()

        assert load_cached_credentials() == Credentials("access-1", "refresh-1", "a@b.c")
        assert user.configuration.access_token == "access-1"

    def test_a_password_session_leaves_the_file_alone(self, cached, server):
        token = MagicMock(access_token="password-access", refresh_token="cached-refresh")
        with patch("chickenstats_api.LoginApi") as login_api:
            login_api.return_value.login_firebase_token.return_value = token
            user = ChickenUser(username="tester", password="secret")

        user.refresh()

        assert user.access_token == "access-1"

        assert _saved().access_token == "cached-access"

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
        user = ChickenUser(cf_client_id="id", cf_client_secret="secret")

        with pytest.raises(AuthError, match="No refresh token"):
            user.refresh()

    @pytest.mark.parametrize("login", [_password_sign_in, _google_sign_in])
    def test_a_login_with_no_refresh_token_asks_for_a_verified_email(self, login):
        token = MagicMock(access_token="access", refresh_token=None)
        with patch("chickenstats_api.LoginApi") as login_api:
            login_api.return_value.login_firebase_token.return_value = token
            login_api.return_value.login_verify_token.return_value = token
            with pytest.raises(AuthError, match="Verify your email"):
                login()

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


class TestServiceTokens:
    def test_a_service_token_alone_sends_no_login(self, credentials_path):
        with patch("chickenstats_api.LoginApi") as login_api:
            cs = ChickenStats(cf_client_id="id", cf_client_secret="secret")

        login_api.assert_not_called()
        assert cs.access_token is None
        assert cs.user.api_client.default_headers["CF-Access-Client-Id"] == "id"
        assert cs.user.api_client.default_headers["CF-Access-Client-Secret"] == "secret"

    def test_a_service_token_is_chosen_over_a_cached_login(self, cached):
        user = ChickenUser(cf_client_id="id", cf_client_secret="secret")

        assert user.access_token is None

    def test_half_a_service_token_falls_to_the_cached_login_without_its_headers(self, cached):
        user = ChickenUser(cf_client_id="id")

        assert user.access_token == "cached-access"
        assert "CF-Access-Client-Id" not in user.api_client.default_headers

    def test_half_a_service_token_with_no_cached_login_raises(self, credentials_path):
        with pytest.raises(AuthError, match="No chickenstats login"):
            ChickenUser(cf_client_id="id")

    def test_a_username_alone_still_uses_the_cached_login(self, cached):
        assert ChickenUser(username="tester").access_token == "cached-access"

    def test_login_refuses_a_session_with_no_password(self, cached):
        user = ChickenUser()

        with (
            patch("chickenstats_api.LoginApi") as login_api,
            pytest.raises(AuthError, match="no username and password"),
        ):
            user.reset_password("old", "new")

        login_api.assert_not_called()


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
