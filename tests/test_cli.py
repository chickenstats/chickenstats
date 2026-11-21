"""The chickenstats command, with the sign-in itself replaced."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import urllib3
from typer.testing import CliRunner

from chickenstats.api._auth import Credentials, load_cached_credentials, save_credentials
from chickenstats.exceptions import AuthError
from chickenstats.cli import app

runner = CliRunner()
NO_TOKEN = {"CHICKENSTATS_API_TOKEN": None}


def _approve(host, show):
    """Stand in for device_login: show the code, then return an approved login."""
    show("https://chickenstats.com/device?user_code=BDFG-HJKL", "BDFG-HJKL")
    return Credentials("access", "refresh", "a@b.c", host)


def _login(tmp_path, args, env):
    """Run `chickenstats login` with the device flow replaced and return the result and the saved login."""
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats.cli.device_login", _approve),
        patch("chickenstats.cli.webbrowser.open") as browser,
    ):
        result = runner.invoke(app, ["login", *args], env=env)
        saved = load_cached_credentials()

    return result, saved, browser


def test_login_runs_the_device_flow_and_opens_the_link(tmp_path):
    result, saved, browser = _login(tmp_path, [], {"CHICKENSTATS_API_HOST": "", "DISPLAY": ":0"})

    assert result.exit_code == 0, result.output
    assert "BDFG-HJKL" in result.output
    browser.assert_called_once_with("https://chickenstats.com/device?user_code=BDFG-HJKL")
    assert saved == Credentials("access", "refresh", "a@b.c", "https://api.chickenstats.com")
    assert "Signed in as a@b.c" in result.output


def test_login_with_no_display_only_prints_the_link(tmp_path, monkeypatch):
    monkeypatch.setattr("chickenstats.cli.sys.platform", "linux")
    result, _, browser = _login(tmp_path, [], {"CHICKENSTATS_API_HOST": "", "DISPLAY": "", "WAYLAND_DISPLAY": ""})

    assert result.exit_code == 0, result.output
    assert "BDFG-HJKL" in result.output
    browser.assert_not_called()


def test_login_host_reads_the_environment(tmp_path):
    result, saved, _ = _login(tmp_path, [], {"CHICKENSTATS_API_HOST": "https://staging.example.com"})

    assert result.exit_code == 0, result.output
    assert saved is not None
    assert saved.host == "https://staging.example.com"


def test_login_reports_a_refused_host(tmp_path):
    with patch("chickenstats.cli.webbrowser.open") as browser:
        result = runner.invoke(app, ["login", "--host", "http://api.example.com"])

    assert result.exit_code == 1
    assert "Refusing" in result.output
    browser.assert_not_called()


def test_logout_revokes_and_removes_the_cached_login(tmp_path):
    path = tmp_path / "credentials"
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", path), patch("chickenstats_api.AuthApi") as auth:
        save_credentials(Credentials("access", "refresh"))
        result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0, result.output
    assert auth.return_value.revoke_token.call_args.kwargs["token"] == "refresh"
    assert not path.exists()
    assert "Signed out" in result.output


def test_logout_everywhere_ends_every_session(tmp_path):
    path = tmp_path / "credentials"
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", path), patch("chickenstats_api.AuthApi") as auth:
        save_credentials(Credentials("access", "refresh"))
        result = runner.invoke(app, ["logout", "--everywhere"])

    assert result.exit_code == 0, result.output
    auth.return_value.end_all_sessions.assert_called_once()
    assert not path.exists()


def test_a_failed_revoke_still_removes_the_cached_login(tmp_path):
    path = tmp_path / "credentials"
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", path),
        patch("chickenstats.cli.revoke_saved_login", side_effect=AuthError("server down")),
    ):
        save_credentials(Credentials("access", "refresh"))
        result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0, result.output
    assert "server down" in result.output
    assert not path.exists()


def test_whoami_names_the_signed_in_account(tmp_path):
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats_api.AuthApi") as auth,
    ):
        auth.return_value.whoami.return_value = MagicMock(kind="session", email="a@b.c", tier="premium", prefix=None)
        save_credentials(Credentials("access", "refresh", "a@b.c", "https://staging.example.com"))
        result = runner.invoke(app, ["whoami"], env=NO_TOKEN)

    assert result.exit_code == 0, result.output
    assert "a@b.c" in result.output
    assert "premium" in result.output
    assert "https://staging.example.com" in result.output


def test_login_token_is_prompted_for_and_saved(tmp_path):
    path = tmp_path / "credentials"
    creds = Credentials("cs_1a2b3c4d_secret", None)
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", path),
        patch("chickenstats.cli.token_login", return_value=creds) as login,
    ):
        result = runner.invoke(
            app, ["login", "--token"], input="cs_1a2b3c4d_secret\n", env={"CHICKENSTATS_API_HOST": ""}
        )
        saved = load_cached_credentials()

    assert result.exit_code == 0, result.output
    assert login.call_args.args == ("cs_1a2b3c4d_secret",)
    assert saved == creds
    assert "cs_1a2b3c4d_secret" not in result.output
    assert "Signed in as a named API token" in result.output


def test_whoami_with_a_saved_named_token_shows_its_prefix_and_tier(tmp_path):
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats_api.AuthApi") as auth,
    ):
        auth.return_value.whoami.return_value = MagicMock(kind="named", email=None, tier="free", prefix="cs_1a2b3c4d")
        save_credentials(Credentials("cs_1a2b3c4d_secret", None))
        result = runner.invoke(app, ["whoami"], env=NO_TOKEN)

    assert result.exit_code == 0, result.output
    assert "cs_1a2b3c4d" in result.output and "free" in result.output
    assert "secret" not in result.output


def test_tokens_list_and_revoke(tmp_path):
    listed = MagicMock(id="6f1c", prefix="cs_1a2b3c4d", created_at=datetime(2026, 11, 14), last_used_at=None)
    listed.name, listed.expires_at = "studio cron", None
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats_api.UsersApi") as users,
    ):
        users.return_value.list_api_tokens.return_value = [listed]
        save_credentials(Credentials("access", "refresh"))
        shown = runner.invoke(app, ["tokens", "list"])
        revoked = runner.invoke(app, ["tokens", "revoke", "6f1c"])

    assert shown.exit_code == 0, shown.output
    assert "studio cron" in shown.output
    assert "2026-11-14" in shown.output
    assert revoked.exit_code == 0, revoked.output
    assert users.return_value.revoke_api_token.call_args.kwargs["token_id"] == "6f1c"


def test_whoami_with_no_login_exits_with_an_error(tmp_path):
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"):
        result = runner.invoke(app, ["whoami"], env=NO_TOKEN)

    assert result.exit_code == 1
    assert "Not logged in" in result.output


def test_tokens_revoke_all(tmp_path):
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats_api.UsersApi") as users,
    ):
        save_credentials(Credentials("access", "refresh"))
        result = runner.invoke(app, ["tokens", "revoke", "--all"])

    assert result.exit_code == 0, result.output
    users.return_value.revoke_all_api_tokens.assert_called_once()
    users.return_value.revoke_api_token.assert_not_called()


def test_tokens_revoke_needs_an_id_or_all(tmp_path):
    with patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"):
        save_credentials(Credentials("access", "refresh"))
        result = runner.invoke(app, ["tokens", "revoke"])

    assert result.exit_code == 1
    assert "token id or --all" in result.output


def test_whoami_reports_a_token_from_the_environment(tmp_path):
    env = {"CHICKENSTATS_API_TOKEN": "cs_1a2b3c4d_secret", "CHICKENSTATS_API_HOST": "https://staging.example.com"}
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats_api.AuthApi") as auth,
    ):
        auth.return_value.whoami.return_value = MagicMock(kind="named", email=None, tier="free", prefix="cs_1a2b3c4d")
        result = runner.invoke(app, ["whoami"], env=env)

    assert result.exit_code == 0, result.output
    assert "cs_1a2b3c4d" in result.output and "secret" not in result.output
    assert "CHICKENSTATS_API_TOKEN" in result.output
    assert "staging.example.com" in result.output


def test_login_reports_an_unreachable_host(tmp_path):
    unreachable = urllib3.exceptions.ProtocolError("connection refused")
    with (
        patch("chickenstats.api._auth.CREDENTIALS_PATH", tmp_path / "credentials"),
        patch("chickenstats.cli.device_login", side_effect=unreachable),
    ):
        result = runner.invoke(app, ["login", "--host", "https://down.example.com"])

    assert result.exit_code == 1
    assert "could not reach https://down.example.com" in result.output
    assert "Traceback" not in result.output


def test_login_names_where_it_saved_the_login(tmp_path):
    result, _, _ = _login(tmp_path, [], NO_TOKEN)

    assert str(tmp_path / "credentials") in result.output.replace("\n", "")
