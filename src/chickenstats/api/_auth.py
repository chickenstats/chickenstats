"""Cached-credential login for the chickenstats API.

Backs both `chickenstats login` (chickenstats.cli) and ChickenUser's own
cached-credential fallback (chickenstats.api.api).

Browser OAuth flow (`browser_login`): a local loopback HTTP server catches Google's
redirect, mirroring how `gh`/`supabase`/`firebase-tools` CLIs do this -- no password
ever touches this process. Three hops, none of which need a client secret (PKCE
instead, the modern recommended flow for installed/native apps):

1. Google OAuth 2.0 authorization code + PKCE -> a Google ID token.
2. Firebase Identity Toolkit's `accounts:signInWithIdp` -- exchanges the Google ID
   token for a Firebase ID token, the same REST endpoint every non-JS Firebase Auth
   client (Admin SDKs, this one) uses for "Sign in with Google" without the JS SDK's
   popup-based `signInWithPopup`.
3. chickenstats-api's own `POST /login/verify-token` (app/api/routers/login.py in the
   chickenstats-api repo) -- exchanges the Firebase ID token for this API's own local
   access_token + refresh_token, the same route the web frontend's Google Sign-In
   button already uses.

Needs a real Google OAuth 2.0 Client ID of type "Desktop app" (or "TVs and Limited
Input devices" with PKCE) registered in the chickenstats-api-502204 GCP project --
_GOOGLE_OAUTH_CLIENT_ID below is a placeholder, not a real one, until that's created
in Google Cloud Console (APIs & Services -> Credentials -> Create OAuth client ID).
No client secret needed with PKCE.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import stat
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# TODO: replace with a real "Desktop app" OAuth 2.0 Client ID from
# https://console.cloud.google.com/apis/credentials?project=chickenstats-api-502204
# -- browser_login() will fail with a clear error until this is set for real.
_GOOGLE_OAUTH_CLIENT_ID = "REPLACE_ME.apps.googleusercontent.com"

_GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_FIREBASE_SIGNIN_WITH_IDP_ENDPOINT = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp"
# Firebase Web API keys are meant to be public/embedded in client code (unlike a
# service-account key) -- this is the same value app/frontend/_login.py's own
# inline JS already embeds, in the chickenstats-api repo.
_FIREBASE_WEB_API_KEY = "AIzaSyAJ1qwrlQMmpIpE7Eu0w0htyAMjQP880gw"

_DEFAULT_HOST = "https://api.chickenstats.com"

CREDENTIALS_PATH = Path.home() / ".chickenstats" / "credentials"

_CALLBACK_TIMEOUT_SECONDS = 120


class AuthError(Exception):
    """Raised for any failure in the browser login flow or credential refresh."""


@dataclass
class Credentials:
    access_token: str
    refresh_token: str
    email: str | None = None
    host: str = _DEFAULT_HOST


# ---------------------------------------------------------------------------
# Credential file (~/.chickenstats/credentials)
# ---------------------------------------------------------------------------


def load_cached_credentials() -> Credentials | None:
    """Return cached credentials, or None if the file doesn't exist or is unreadable.

    Deliberately silent on any error (missing file, bad JSON, missing keys) --
    ChickenUser's own fallback logic treats "no cached credentials" as a normal
    case, not something to raise on, so a corrupted cache file just means
    falling back to username/password like before this existed.
    """
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_PATH.read_text())
        return Credentials(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            email=data.get("email"),
            host=data.get("host", _DEFAULT_HOST),
        )
    except Exception:
        return None


def save_credentials(creds: Credentials) -> None:
    """Write credentials to ~/.chickenstats/credentials, chmod 600 (owner read/write only).

    Matches the ~/.aws/credentials / ~/.config/gcloud/ convention -- a local
    plaintext file is the accepted norm for this kind of cached CLI credential,
    but permissions still matter (no other local user should be able to read it).
    """
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(
        json.dumps(
            {
                "access_token": creds.access_token,
                "refresh_token": creds.refresh_token,
                "email": creds.email,
                "host": creds.host,
            },
            indent=2,
        )
    )
    CREDENTIALS_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)


def clear_credentials() -> None:
    """Delete the cached credentials file, if present (used by `chickenstats logout`)."""
    CREDENTIALS_PATH.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Refresh -- also used by ChickenUser on a 401, not just the CLI
# ---------------------------------------------------------------------------


def refresh_access_token(refresh_token: str, host: str = _DEFAULT_HOST) -> dict:
    """Call POST /login/refresh directly and return the raw response body.

    chickenstats_api's generated client doesn't have this route yet (see this
    module's own docstring) -- returns the raw {access_token, refresh_token,
    token_type} response body. Raises AuthError on any non-2xx response
    (expired/revoked/invalid refresh token) rather than a raw requests
    exception, so callers can catch one thing.
    """
    resp = requests.post(f"{host.rstrip('/')}/api/v1/login/refresh", json={"refresh_token": refresh_token}, timeout=15)
    if not resp.ok:
        raise AuthError(f"Refresh token rejected ({resp.status_code}) -- run `chickenstats login` again.")
    return resp.json()


# ---------------------------------------------------------------------------
# Browser OAuth login (Google -> Firebase -> chickenstats-api)
# ---------------------------------------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class _CallbackServer(HTTPServer):
    """An HTTPServer with the extra attributes _CallbackHandler stashes results on.

    A real, typed subclass instead of dynamically bolting attributes onto a bare
    HTTPServer -- keeps the type checker honest and avoids ignore comments.
    """

    auth_code: str | None = None
    received_state: str | None = None
    error: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    """Captures Google's redirect (?code=...&state=...) on the loopback server.

    Stores the result on the server instance itself (server.auth_code/server.state)
    rather than a module-level global, so a fresh HTTPServer per login() call can't
    leak state between calls.
    """

    server: _CallbackServer

    def do_GET(self):  # noqa: N802 -- BaseHTTPRequestHandler's own naming convention
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        self.server.auth_code = params.get("code", [None])[0]
        self.server.received_state = params.get("state", [None])[0]
        self.server.error = params.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if self.server.error:
            body = "<h1>Login failed</h1><p>You can close this tab and check the terminal.</p>"
        else:
            body = "<h1>chickenstats: signed in</h1><p>You can close this tab.</p>"
        self.wfile.write(body.encode())

    def log_message(self, format, *args):  # noqa: A002 -- silence default request logging
        pass


def browser_login(host: str = _DEFAULT_HOST) -> Credentials:
    """Run the full browser OAuth flow and return the resulting Credentials.

    Does not write the credentials file itself -- callers (cli.py's `login`
    command) decide when/whether to persist, keeping this function usable for
    a one-off in-memory login too.
    """
    if _GOOGLE_OAUTH_CLIENT_ID.startswith("REPLACE_ME"):
        raise AuthError(
            "browser_login() needs a real Google OAuth Client ID -- see this module's "
            "own docstring (chickenstats/api/_auth.py) for how to create one."
        )

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    server = _CallbackServer(("127.0.0.1", 0), _CallbackHandler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    auth_url = f"{_GOOGLE_AUTH_ENDPOINT}?" + urlencode(
        {
            "client_id": _GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            # Always show the account chooser -- a CLI shouldn't silently reuse
            # whatever Google session happens to already be active in the browser.
            "prompt": "select_account",
        }
    )

    print("Opening your browser to sign in with Google...")
    print(f"If it doesn't open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server.timeout = _CALLBACK_TIMEOUT_SECONDS
    server.handle_request()  # blocks for exactly one request, then returns
    server.server_close()

    if server.error:
        raise AuthError(f"Google sign-in failed: {server.error}")
    if server.received_state != state:
        raise AuthError("State mismatch on OAuth callback -- possible CSRF, aborting.")
    if not server.auth_code:
        raise AuthError("No authorization code received (timed out or cancelled).")

    google_id_token = _exchange_google_code(server.auth_code, verifier, redirect_uri)
    firebase_id_token, email = _exchange_google_for_firebase(google_id_token)
    access_token, refresh_token = _exchange_firebase_for_local(firebase_id_token, host)

    return Credentials(access_token=access_token, refresh_token=refresh_token, email=email, host=host)


def _exchange_google_code(code: str, verifier: str, redirect_uri: str) -> str:
    resp = requests.post(
        _GOOGLE_TOKEN_ENDPOINT,
        data={
            "client_id": _GOOGLE_OAUTH_CLIENT_ID,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    if not resp.ok:
        raise AuthError(f"Google token exchange failed: {resp.text}")
    return resp.json()["id_token"]


def _exchange_google_for_firebase(google_id_token: str) -> tuple[str, str | None]:
    """Identity Toolkit's accounts:signInWithIdp -- Google ID token -> Firebase ID token."""
    resp = requests.post(
        _FIREBASE_SIGNIN_WITH_IDP_ENDPOINT,
        params={"key": _FIREBASE_WEB_API_KEY},
        json={
            "postBody": f"id_token={google_id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnIdpCredential": True,
            "returnSecureToken": True,
        },
        timeout=15,
    )
    if not resp.ok:
        raise AuthError(f"Firebase sign-in failed: {resp.text}")
    data = resp.json()
    return data["idToken"], data.get("email")


def _exchange_firebase_for_local(firebase_id_token: str, host: str) -> tuple[str, str]:
    """Exchange a Firebase ID token for this API's own local tokens.

    chickenstats-api's own POST /login/verify-token -- same route the web
    frontend's Google Sign-In button uses (app/frontend/_login.py,
    chickenstats-api repo). Returns (access_token, refresh_token).
    """
    resp = requests.post(
        f"{host.rstrip('/')}/api/v1/login/verify-token", json={"id_token": firebase_id_token}, timeout=15
    )
    if not resp.ok:
        raise AuthError(f"chickenstats API sign-in failed: {resp.text}")
    data = resp.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise AuthError(
            "chickenstats API didn't return a refresh_token -- is the backend "
            "running the version with POST /login/refresh support?"
        )
    return data["access_token"], refresh_token
