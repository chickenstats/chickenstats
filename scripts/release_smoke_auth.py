#!/usr/bin/env python3
"""Check the chickenstats sign-in against a live API before a release is published.

    release_smoke_auth.py                                  run against https://api.chickenstats.com
    release_smoke_auth.py --host https://staging.example   another host
    release_smoke_auth.py --require-token                  fail, not skip, without CHICKENSTATS_API_TOKEN
    release_smoke_auth.py --revoke-test-token ID           also revoke a throwaway named token

Signs in with the device flow through the real `chickenstats` CLI, so approve the code on
chickenstats.com when it is shown. Then checks whoami, a small read, refresh rotation, the
named token in CHICKENSTATS_API_TOKEN, `tokens list` and `logout --everywhere`.

The login is saved under a temporary home folder, which is deleted at the end, so the saved
login in ~/.chickenstats is never read or changed. Prints PASS, FAIL or SKIP for each step
and exits 1 if any step fails.

Standard library plus chickenstats.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import chickenstats_api

from chickenstats.api import ChickenStats, ChickenUser, _auth
from chickenstats.exceptions import AuthError

PLAYER = "FILIP FORSBERG"


class Skip(Exception):
    """The step can't run here, which is not a failure."""


def check(condition: object, reason: str) -> None:
    """Fail the step with `reason` unless `condition` holds."""
    if not condition:
        raise AssertionError(reason)


def prefix(token: str | None) -> str:
    """Show only the start of a token."""
    return f"{token[:8]}..." if token else "none"


def last_line(result: subprocess.CompletedProcess) -> str:
    """The last line the CLI printed, for a failure reason."""
    lines = (result.stdout + result.stderr).strip().splitlines()
    return f"exit {result.returncode}: {lines[-1] if lines else 'no output'}"


class Smoke:
    """The steps, sharing one temporary home folder."""

    def __init__(self, args: argparse.Namespace, home: Path):
        """Keep the saved login under `home`, for this process and for the CLI."""
        self.args, self.home, self.failed = args, home, False
        self.creds: _auth.Credentials  # set by the login step
        # Set aside so the saved-login steps don't pick it up; step 5 passes it on purpose
        self.named_token = os.environ.pop("CHICKENSTATS_API_TOKEN", None)
        os.environ.pop("CHICKENSTATS_API_HOST", None)
        # The CLI finds the file from HOME; this process read it at import, so point it here too
        _auth.CREDENTIALS_PATH = home / ".chickenstats" / "credentials"

    def cli(self, *command: str, home: Path | None = None, capture: bool = True, timeout: float = 60, **env: str):
        """Run the chickenstats CLI from this install with a temporary home folder."""
        folder = str(home or self.home)
        child_env = {**os.environ, "HOME": folder, "USERPROFILE": folder, "COLUMNS": "200", **env}
        args = [sys.executable, "-m", "chickenstats.cli", *command]
        return subprocess.run(args, env=child_env, capture_output=capture, text=True, timeout=timeout)

    def read(self, token: str | None = None) -> str:
        """Download a few rows, with the named token or else the saved login."""
        players = ChickenStats(token=token, host=self.args.host, limit=5)
        frame = players.download_players(PLAYER, disable_progress_bar=True)
        check(frame.height > 0, f"no rows for {PLAYER}")
        return f"read {frame.height} row(s)"

    def run(self, name: str, step) -> bool:
        """Run one step and print its result line."""
        try:
            status, reason = "PASS", step()
        except Skip as exc:
            status, reason = "SKIP", str(exc)
        except subprocess.TimeoutExpired as exc:
            status, reason = "FAIL", f"timed out after {exc.timeout:.0f}s"
        except Exception as exc:
            message = (str(exc).strip().splitlines() or [""])[0][:200]
            status, reason = "FAIL", message if isinstance(exc, AssertionError) else f"{type(exc).__name__}: {message}"
        self.failed |= status == "FAIL"
        print(f"{status} {name}: {reason}", flush=True)
        return status != "FAIL"

    def login(self) -> str:
        """1: sign in with the device flow and check the saved file has a refresh token."""
        print(f"Signing in to {self.args.host}: approve the code below on chickenstats.com", flush=True)
        result = self.cli("login", "--host", self.args.host, capture=False, timeout=self.args.timeout)
        check(result.returncode == 0, f"chickenstats login exited {result.returncode}")
        creds = _auth.load_cached_credentials()
        if creds is None or not creds.refresh_token:
            raise AssertionError("the saved login has no refresh token")
        self.creds = creds
        return f"signed in as {self.creds.email}, refresh token {prefix(self.creds.refresh_token)}"

    def whoami(self) -> str:
        """2: `chickenstats whoami` prints the signed-in email."""
        result = self.cli("whoami")
        check(result.returncode == 0, last_line(result))
        check(self.creds.email and self.creds.email in result.stdout, "whoami did not print the email")
        return f"printed {self.creds.email}"

    def refresh(self) -> str:
        """4: refresh rotates the saved refresh token, and reads still work."""
        user = ChickenUser(host=self.args.host)
        before = user.refresh_token
        user.refresh()
        saved = _auth.load_cached_credentials()
        if saved is None or saved.refresh_token in (None, before):
            raise AssertionError("the saved refresh token did not change")
        check(saved.refresh_token == user.refresh_token, "the saved refresh token is not the one in use")
        return f"refresh token rotated to {prefix(saved.refresh_token)}, {self.read()}"

    def named(self) -> str:
        """5: a named token reads, passes the `login --token` check, and whoami reports it."""
        if not self.named_token:
            check(not self.args.require_token, "CHICKENSTATS_API_TOKEN is not set")
            raise Skip("CHICKENSTATS_API_TOKEN is not set")
        reason = self.read(self.named_token)
        _auth.token_login(self.named_token, self.args.host)
        result = self.cli("whoami", CHICKENSTATS_API_TOKEN=self.named_token, CHICKENSTATS_API_HOST=self.args.host)
        check(result.returncode == 0 and self.named_token[:8] in result.stdout, last_line(result))
        return f"token {prefix(self.named_token)} {reason}, whoami reports it"

    def tokens(self) -> str:
        """6: `chickenstats tokens list` works, and revoke when asked."""
        result = self.cli("tokens", "list")
        check(result.returncode == 0, last_line(result))
        if not self.args.revoke_test_token:
            return "listed"
        # Only a throwaway token: the one in CHICKENSTATS_API_TOKEN must keep working afterwards
        listed = _auth.with_saved_login(self.creds, lambda client: chickenstats_api.UsersApi(client).list_api_tokens())
        target = next((t for t in listed if t.id == self.args.revoke_test_token), None)
        if target is None:
            raise AssertionError(f"no token with id {self.args.revoke_test_token}")
        if self.named_token and self.named_token.startswith(target.prefix):
            raise AssertionError("refusing to revoke the token in CHICKENSTATS_API_TOKEN; make a second, throwaway one")
        result = self.cli("tokens", "revoke", self.args.revoke_test_token)
        check(result.returncode == 0, last_line(result))
        return f"listed, revoked {self.args.revoke_test_token}"

    def logout(self) -> str:
        """7: sign out everywhere ends the session but not the named token."""
        held = ChickenUser(host=self.args.host)
        result = self.cli("logout", "--everywhere")
        # The CLI removes the file and exits 0 even when the server refuses, printing why first
        check(result.returncode == 0 and result.stdout.strip().startswith("Signed out"), last_line(result))
        check(not _auth.CREDENTIALS_PATH.exists(), "the credentials file is still there")
        try:
            held.test_token()
            raise AssertionError("the old session still works after logout --everywhere")
        except AuthError:
            pass
        try:
            ChickenUser(host=self.args.host)
            raise AssertionError("a new ChickenUser still found a login")
        except AuthError:
            pass
        reason = "old session refused"
        if self.named_token:
            reason += f", named token still works ({self.read(self.named_token)})"
        return reason


def main() -> int:
    """Run every step and print a summary."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="https://api.chickenstats.com", help="chickenstats API host")
    parser.add_argument("--timeout", type=float, default=300, help="seconds to wait for the device approval")
    parser.add_argument("--require-token", action="store_true", help="fail step 5 without CHICKENSTATS_API_TOKEN")
    parser.add_argument("--revoke-test-token", metavar="ID", help="revoke this named token in step 6")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="chickenstats-smoke-") as home:
        smoke = Smoke(args, Path(home))
        if smoke.run("1 device login", smoke.login):
            smoke.run("2 whoami", smoke.whoami)
            smoke.run("3 read with saved login", smoke.read)
            smoke.run("4 refresh", smoke.refresh)
            smoke.run("5 named token", smoke.named)
            smoke.run("6 tokens", smoke.tokens)
            smoke.run("7 logout everywhere", smoke.logout)
        else:
            print("The other steps need the device login, so they did not run.")

    print("FAILED: do not publish." if smoke.failed else "All steps passed.")
    return 1 if smoke.failed else 0


if __name__ == "__main__":
    sys.exit(main())
