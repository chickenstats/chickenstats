"""`chickenstats` CLI: signing in and out, and named API tokens.

Installed via `[project.scripts]` in pyproject.toml. The credential logic lives in
chickenstats.api._auth, which ChickenUser and ChickenStats share.
"""

from __future__ import annotations

import os
import sys
import webbrowser

import chickenstats_api
import typer
import urllib3
from rich.console import Console
from rich.table import Table

from chickenstats.api._api_constants import REQUEST_TIMEOUT
from chickenstats.api import _auth
from chickenstats.api._auth import (
    AuthError,
    Credentials,
    clear_credentials,
    device_login,
    load_cached_credentials,
    oauth_error,
    revoke_saved_login,
    save_credentials,
    token_login,
    with_saved_login,
)

app = typer.Typer(name="chickenstats", help="chickenstats API command-line tools.", no_args_is_help=True)
tokens = typer.Typer(help="List and revoke named API tokens.", no_args_is_help=True)
app.add_typer(tokens, name="tokens")
console = Console()


def _fail(message: str) -> typer.Exit:
    """Print an error and return the exit to raise."""
    console.print(f"[red]{message}[/red]")
    return typer.Exit(code=1)


def _saved() -> Credentials:
    """Return the saved login, or exit saying how to sign in."""
    creds = load_cached_credentials()
    if creds is None:
        console.print("Not logged in. Run [bold]chickenstats login[/bold] to sign in.")
        raise typer.Exit(code=1)
    return creds


def _with_saved(creds: Credentials | None, call):
    """Run an SDK call with a login (the saved one by default), exiting with the reason if it fails."""
    try:
        return with_saved_login(creds or _saved(), call)
    except AuthError as exc:
        raise _fail(str(exc)) from exc
    except chickenstats_api.ApiException as exc:
        raise _fail(oauth_error(exc)[1] or str(exc.reason)) from exc
    except urllib3.exceptions.HTTPError as exc:
        raise _fail(f"Could not reach the chickenstats API: {exc}") from exc


def _show_code(uri: str, code: str) -> None:
    """Print the device sign-in link and code, and open the link in a browser if there is one."""
    console.print(f"Open [bold]{uri}[/bold] on any device and approve the code [bold]{code}[/bold].")
    # With no display, webbrowser would start a text browser in this terminal
    if sys.platform in ("darwin", "win32") or os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        webbrowser.open(uri)


@app.command()
def login(
    token: bool = typer.Option(False, "--token", help="Save a named API token from chickenstats.com/account/api."),
    host: str = typer.Option(
        "https://api.chickenstats.com", "--host", envvar="CHICKENSTATS_API_HOST", help="chickenstats API host."
    ),
) -> None:
    """Sign in and save the login, which ChickenStats() then uses on its own.

    Shows a link and a code to approve on chickenstats.com. With --token, asks for a
    named API token instead, so it stays out of shell history.
    """
    try:
        if token:
            creds = token_login(typer.prompt("Token", hide_input=True).strip(), host=host)
        else:
            creds = device_login(host=host, show=_show_code)
    except AuthError as exc:
        raise _fail(f"Login failed: {exc}") from exc
    except urllib3.exceptions.HTTPError as exc:
        raise _fail(f"Login failed: could not reach {host}.") from exc

    save_credentials(creds)
    who = creds.email or ("a named API token" if creds.refresh_token is None else "your account")
    console.print(f"[green]Signed in as {who}.[/green] Credentials cached at {_auth.CREDENTIALS_PATH}")


@app.command()
def logout(
    everywhere: bool = typer.Option(
        False, "--everywhere", help="Sign out every session of the account. Named API tokens keep working."
    ),
) -> None:
    """Sign out on the server and remove the saved login (~/.chickenstats/credentials)."""
    creds = load_cached_credentials()
    if creds is None:
        console.print("Not logged in.")
        return

    try:
        if everywhere:
            if creds.refresh_token is None:
                raise AuthError("A named API token can't sign out sessions. Run `chickenstats login` to do this.")
            with_saved_login(
                creds,
                lambda client: chickenstats_api.AuthApi(client).end_all_sessions(_request_timeout=REQUEST_TIMEOUT),
            )
        else:
            revoke_saved_login(creds)
    except AuthError as exc:
        console.print(f"[yellow]{exc}[/yellow]")

    clear_credentials()
    console.print("[green]Signed out.[/green] Cached credentials removed.")


@app.command()
def whoami() -> None:
    """Show who the saved login, or CHICKENSTATS_API_TOKEN, is signed in as."""
    env_token = os.environ.get("CHICKENSTATS_API_TOKEN")
    if env_token:
        host = os.environ.get("CHICKENSTATS_API_HOST", "https://api.chickenstats.com")
        creds, source = Credentials(env_token, None, None, host), " from CHICKENSTATS_API_TOKEN"
    else:
        creds, source = _saved(), ""
    me = _with_saved(creds, lambda client: chickenstats_api.AuthApi(client).whoami(_request_timeout=REQUEST_TIMEOUT))
    if me.kind == "named":
        console.print(f"Using the named API token {me.prefix}{source} ({me.tier}) on {creds.host}")
    else:
        console.print(f"Logged in as [bold]{me.email}[/bold] ({me.tier}) on {creds.host}")


@tokens.command("list")
def list_tokens() -> None:
    """List the account's named API tokens."""
    found = _with_saved(
        None, lambda client: chickenstats_api.UsersApi(client).list_api_tokens(_request_timeout=REQUEST_TIMEOUT)
    )
    if not found:
        console.print("No named API tokens.")
        return

    table = Table("id", "name", "prefix", "created", "last used", "expires")
    for item in found:
        table.add_row(
            str(item.id),
            item.name,
            item.prefix,
            f"{item.created_at:%Y-%m-%d}",
            f"{item.last_used_at:%Y-%m-%d}" if item.last_used_at else "never",
            f"{item.expires_at:%Y-%m-%d}" if item.expires_at else "never",
        )
    console.print(table)


@tokens.command("revoke")
def revoke_token(
    token_id: str | None = typer.Argument(None, help="The id from `chickenstats tokens list`."),
    revoke_all: bool = typer.Option(False, "--all", help="Revoke every named API token on the account."),
) -> None:
    """Revoke a named API token, or all of them. Anything still using one stops working."""
    if revoke_all == (token_id is not None):
        raise _fail("Give a token id or --all, not both.")

    users = chickenstats_api.UsersApi
    if token_id is None:
        _with_saved(None, lambda client: users(client).revoke_all_api_tokens(_request_timeout=REQUEST_TIMEOUT))
        console.print("[green]Revoked every named API token.[/green]")
    else:
        _with_saved(
            None, lambda client: users(client).revoke_api_token(token_id=token_id, _request_timeout=REQUEST_TIMEOUT)
        )
        console.print(f"[green]Revoked {token_id}.[/green]")


def main() -> None:
    """Entry point for the `chickenstats` console script (see pyproject.toml)."""
    app()


if __name__ == "__main__":
    main()
