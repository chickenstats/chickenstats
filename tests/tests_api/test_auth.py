"""The cached login, its file and the browser sign-in page, with the SDK's network calls replaced."""

import sys
from unittest.mock import patch

import pytest

from chickenstats.api._auth import (
    Credentials,
    _callback_page,
    browser_login,
    password_login,
    require_secure_host,
    same_host,
    save_credentials,
)
from chickenstats.api.api import ChickenUser
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
