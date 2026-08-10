"""Cached-credential login for the chickenstats API.

Backs both `chickenstats login` (chickenstats.cli) and ChickenUser's own
cached-credential fallback.

`browser_login` opens a local loopback server, sends the user through Google
sign-in, then swaps that for a chickenstats access/refresh token pair -- no
password ever touches this process. The OAuth client ID/secret below are a
"Desktop app" credential; Google requires the secret on the token exchange even
for PKCE installed-app flows, but doesn't treat it as sensitive for this client
type (same reason tools like `gcloud` ship theirs in the open), so it's fine
embedded here.
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

import chickenstats_api
import requests

# Desktop-app OAuth client ID/secret -- see this module's docstring for why the
# secret is fine to embed.
_GOOGLE_OAUTH_CLIENT_ID = "572721742848-03580sju886smc8jntggsl9gnlgm8nes.apps.googleusercontent.com"
_GOOGLE_OAUTH_CLIENT_SECRET = "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"

_GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_FIREBASE_SIGNIN_WITH_IDP_ENDPOINT = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp"
# Firebase web API keys are meant to be public, unlike a service-account key.
_FIREBASE_WEB_API_KEY = "AIzaSyAJ1qwrlQMmpIpE7Eu0w0htyAMjQP880gw"

_DEFAULT_HOST = "https://api.chickenstats.com"

CREDENTIALS_PATH = Path.home() / ".chickenstats" / "credentials"

_CALLBACK_TIMEOUT_SECONDS = 120


class AuthError(Exception):
    """Raised for any failure in the browser login flow or credential refresh."""


def _login_api(host: str) -> chickenstats_api.LoginApi:
    """Build an unauthenticated LoginApi client for `host` -- no access_token yet."""
    return chickenstats_api.LoginApi(chickenstats_api.ApiClient(chickenstats_api.Configuration(host=host)))


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
    """Exchange a refresh token for a fresh access_token/refresh_token pair.

    Returns a plain dict, matching what callers already expect. Raises
    AuthError on a rejected/expired refresh token.
    """
    try:
        token = _login_api(host).login_refresh(chickenstats_api.RefreshTokenRequest(refresh_token=refresh_token))
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"Refresh token rejected ({exc.status}) -- run `chickenstats login` again.") from exc
    return token.model_dump()


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
            "client_secret": _GOOGLE_OAUTH_CLIENT_SECRET,
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
    """Exchange a Firebase ID token for this API's own access/refresh tokens."""
    try:
        token = _login_api(host).login_verify_token(chickenstats_api.IdToken(id_token=firebase_id_token))
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"chickenstats API sign-in failed ({exc.status}): {exc.reason}") from exc

    if not token.refresh_token:
        raise AuthError("chickenstats API didn't return a refresh_token.")
    return token.access_token, token.refresh_token
