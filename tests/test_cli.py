"""The chickenstats command, with the sign-in itself replaced."""

from unittest.mock import patch

from typer.testing import CliRunner

from chickenstats.api._auth import Credentials, load_cached_credentials, save_credentials
from chickenstats.cli import app

runner = CliRunner()


def _login(tmp_path, env):
    """Run `chickenstats login --password` and return the host it signed in to."""
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats.cli.password_login", return_value=Credentials("a", "r")) as login,
    ):
        result = runner.invoke(app, ["login", "--password"], input="a@b.c\nsecret\n", env=env)

    assert result.exit_code == 0, result.output
    return login.call_args.kwargs["host"]


def test_login_host_defaults_to_the_public_api(tmp_path):
    assert _login(tmp_path, {"CHICKENSTATS_API_HOST": ""}) == "https://api.chickenstats.com"


def test_login_host_reads_the_environment(tmp_path):
    assert _login(tmp_path, {"CHICKENSTATS_API_HOST": "https://staging.example.com"}) == "https://staging.example.com"


def test_login_reports_a_refused_host(tmp_path):
    result = runner.invoke(app, ["login", "--password", "--host", "http://api.example.com"], input="a@b.c\nsecret\n")

    assert result.exit_code == 1
    assert "Refusing" in result.output


def test_login_password_caches_the_login(tmp_path):
    path = tmp_path / "credentials"
    creds = Credentials("access", "refresh", "a@b.c", "https://staging.example.com")
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", path),
        patch("chickenstats.cli.password_login", return_value=creds) as login,
        patch("chickenstats.cli.browser_login") as browser,
    ):
        result = runner.invoke(app, ["login", "--password"], input="a@b.c\nsecret\n", env={"CHICKENSTATS_API_HOST": ""})
        saved = load_cached_credentials()

    assert result.exit_code == 0, result.output
    assert login.call_args.args == ("a@b.c", "secret")
    browser.assert_not_called()
    assert saved == creds
    assert "Signed in as a@b.c" in result.output


def test_login_uses_the_browser_by_default(tmp_path):
    path = tmp_path / "credentials"
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", path),
        patch("chickenstats.cli.browser_login", return_value=Credentials("access", "refresh")) as browser,
        patch("chickenstats.cli.password_login") as login,
    ):
        result = runner.invoke(app, ["login"], env={"CHICKENSTATS_API_HOST": ""})
        saved = load_cached_credentials()

    assert result.exit_code == 0, result.output
    browser.assert_called_once_with(host="https://api.chickenstats.com")
    login.assert_not_called()
    assert saved == Credentials("access", "refresh")
    assert "Signed in as your account" in result.output


def test_logout_removes_the_cached_login(tmp_path):
    path = tmp_path / "credentials"
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", path):
        save_credentials(Credentials("access", "refresh"))
        result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0, result.output
    assert not path.exists()
    assert "Signed out" in result.output


def test_whoami_names_the_cached_login(tmp_path):
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"):
        save_credentials(Credentials("access", "refresh", "a@b.c", "https://staging.example.com"))
        result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 0, result.output
    assert "a@b.c" in result.output
    assert "https://staging.example.com" in result.output


def test_whoami_with_no_login_exits_with_an_error(tmp_path):
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"):
        result = runner.invoke(app, ["whoami"])

    assert result.exit_code == 1
    assert "Not logged in" in result.output
