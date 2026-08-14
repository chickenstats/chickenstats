"""`chickenstats` CLI -- currently just auth (login/logout/whoami).

Installed via `[project.scripts]` in pyproject.toml. Kept deliberately
separate from chickenstats.api.api (ChickenUser/ChickenStats) -- this module
owns the interactive/terminal-output side of auth, api.py owns the
programmatic side; both call into chickenstats.api._auth for the actual
credential logic so there's one implementation of "what a cached login is."
"""

from __future__ import annotations

import typer
from rich.console import Console

from chickenstats.api._auth import (
    AuthError,
    browser_login,
    clear_credentials,
    load_cached_credentials,
    password_login,
    save_credentials,
)

app = typer.Typer(name="chickenstats", help="chickenstats API command-line tools.", no_args_is_help=True)
console = Console()


@app.command()
def login(
    password: bool = typer.Option(
        False, "--password", help="Sign in with your chickenstats email/password instead of a browser."
    ),
    host: str = typer.Option("https://api.chickenstats.com", "--host", help="chickenstats API host."),
) -> None:
    """Sign in and cache credentials locally.

    Defaults to browser-based Google sign-in; pass --password to sign in with your
    chickenstats email/password instead (prompted interactively, never as a CLI
    argument -- avoids it landing in shell history). Either way,
    chickenstats.api.ChickenStats() picks up the cached login automatically
    afterward -- no username/password/env vars needed in your own code.
    """
    try:
        if password:
            email = typer.prompt("Email")
            pwd = typer.prompt("Password", hide_input=True)
            creds = password_login(email, pwd, host=host)
        else:
            creds = browser_login(host=host)
    except AuthError as exc:
        console.print(f"[red]Login failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    save_credentials(creds)
    who = creds.email or "your account"
    console.print(f"[green]Signed in as {who}.[/green] Credentials cached at ~/.chickenstats/credentials")


@app.command()
def logout() -> None:
    """Remove cached credentials (~/.chickenstats/credentials)."""
    clear_credentials()
    console.print("[green]Signed out.[/green] Cached credentials removed.")


@app.command()
def whoami() -> None:
    """Show the currently cached login, if any."""
    creds = load_cached_credentials()
    if creds is None:
        console.print("Not logged in. Run [bold]chickenstats login[/bold] to sign in.")
        raise typer.Exit(code=1)
    console.print(f"Logged in as [bold]{creds.email or '(unknown email)'}[/bold] ({creds.host})")


def main() -> None:
    """Entry point for the `chickenstats` console script (see pyproject.toml)."""
    app()


if __name__ == "__main__":
    main()
