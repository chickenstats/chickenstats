"""The chickenstats command, with the sign-in itself replaced."""

from unittest.mock import patch

from typer.testing import CliRunner

from chickenstats.api._auth import Credentials
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
