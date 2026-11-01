"""The cached login, its file and the browser sign-in page, with the SDK's network calls replaced."""

import os
import stat
import sys
from unittest.mock import patch

import pytest

from chickenstats.api._auth import (
    Credentials,
    _callback_page,
    browser_login,
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
