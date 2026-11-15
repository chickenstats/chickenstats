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
import html
import json
import os
import secrets
import sys
import tempfile
import threading
import time
import webbrowser
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import chickenstats_api
import requests
from requests.utils import get_environ_proxies

from chickenstats.api._api_constants import REQUEST_TIMEOUT
from chickenstats.exceptions import AuthError
from chickenstats.utilities.utilities import _default_user_agent

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

# Desktop-app OAuth client; the module docstring says why the secret can be embedded
_GOOGLE_OAUTH_CLIENT_ID = "572721742848-03580sju886smc8jntggsl9gnlgm8nes.apps.googleusercontent.com"
_GOOGLE_OAUTH_CLIENT_SECRET = "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"

_GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_FIREBASE_SIGNIN_WITH_IDP_ENDPOINT = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp"
# Firebase web API keys are meant to be public, unlike a service-account key.
_FIREBASE_WEB_API_KEY = "AIzaSyAJ1qwrlQMmpIpE7Eu0w0htyAMjQP880gw"

_DEFAULT_HOST = "https://api.chickenstats.com"
# An account with an unverified email gets no refresh token
_UNVERIFIED_EMAIL_MESSAGE = "Sign-in returned no refresh token. Verify your email address, then sign in again."

CREDENTIALS_PATH = Path.home() / ".chickenstats" / "credentials"

# Plain http would expose a token on the wire, so only a server on this machine may use it
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")

# Serializes refreshes in a process; the lock file does so across processes
_REFRESH_LOCK = threading.Lock()

_CALLBACK_TIMEOUT_SECONDS = 120

# Same palette and logo as the API's browser pages
_BG = "#0a0b0e"
_FG = "#c1c6d6"
_FG_DIM = "#818ea0"
_ACCENT = "#6791e0"
_LOGO_URL = "https://chickenstats.com/images/favicon.png"

_CALLBACK_STYLE = f"""
body {{
  font-family: system-ui, sans-serif; background: {_BG}; color: {_FG};
  display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0;
  padding: 2rem 1rem; box-sizing: border-box;
}}
.card {{ text-align: center; }}
img {{ width: 56px; height: 56px; border-radius: 12px; margin-bottom: 1.25rem; }}
h1 {{ font-size: 1.25rem; font-weight: 500; margin: 0 0 0.5rem; }}
p {{ color: {_FG_DIM}; margin: 0; }}
a {{ color: {_ACCENT}; }}
"""


def _callback_page(title: str, heading: str, message: str) -> str:
    """Render the OAuth loopback callback's success or failure page."""
    return f"""<!doctype html>
<html>
<head>
<title>{html.escape(title)}</title>
<meta charset="utf-8">
<link rel="icon" href="{_LOGO_URL}">
<style>{_CALLBACK_STYLE}</style>
</head>
<body>
<div class="card">
<img src="{_LOGO_URL}" alt="chickenstats">
<h1>{html.escape(heading)}</h1>
<p>{html.escape(message)}</p>
</div>
</body>
</html>
"""


def require_secure_host(host: str) -> None:
    """Raise AuthError unless `host` uses https or is a server on this machine."""
    parts = urlparse(host)
    if parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in _LOCAL_HOSTS):
        return
    raise AuthError(f"Refusing to send credentials to {host}. Use https, or http only for localhost.")


def same_host(first: str, second: str) -> bool:
    """Whether two API hosts are the same, ignoring case and a trailing slash."""
    return first.rstrip("/").lower() == second.rstrip("/").lower()


def _environment_proxy(host: str) -> str | None:
    """Return the proxy the environment sets for `host`, respecting NO_PROXY."""
    proxies = get_environ_proxies(host)
    return proxies.get(urlparse(host).scheme) or proxies.get("all")


def build_api_client(host: str, proxy: str | None = None, ca_bundle: str | None = None) -> chickenstats_api.ApiClient:
    """Build an SDK client for `host`, with no access token yet.

    Parameters:
        host: The API host, which must pass `require_secure_host`.
        proxy: The proxy URL. Defaults to the one the environment sets for `host`.
        ca_bundle: The path to a CA bundle. Defaults to REQUESTS_CA_BUNDLE, then SSL_CERT_FILE.
    """
    require_secure_host(host)

    configuration = chickenstats_api.Configuration(
        host=host, ssl_ca_cert=ca_bundle or os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    )
    configuration.proxy = proxy or _environment_proxy(host)

    api_client = chickenstats_api.ApiClient(configuration)
    api_client.user_agent = _default_user_agent()
    return api_client


def _login_api(host: str, proxy: str | None = None, ca_bundle: str | None = None) -> chickenstats_api.LoginApi:
    """Build an unauthenticated LoginApi client for `host` -- no access_token yet."""
    return chickenstats_api.LoginApi(build_api_client(host, proxy, ca_bundle))


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
    """Write credentials to ~/.chickenstats/credentials, readable only by the owner.

    Matches the ~/.aws/credentials / ~/.config/gcloud/ convention -- a local
    plaintext file is the accepted norm for this kind of cached CLI credential,
    but permissions still matter (no other local user should be able to read it).

    The tokens go to a temporary file, which mkstemp creates with mode 600, and
    that file replaces the old one. The tokens are therefore never readable by
    anyone else, and a reader never sees half a file.

    Raises:
        OSError: If the file cannot be written, as on a read-only mount.
    """
    CREDENTIALS_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=CREDENTIALS_PATH.parent, prefix=".credentials-")
    try:
        with os.fdopen(descriptor, "w") as file:
            json.dump(
                {
                    "access_token": creds.access_token,
                    "refresh_token": creds.refresh_token,
                    "email": creds.email,
                    "host": creds.host,
                },
                file,
                indent=2,
            )
        os.replace(temporary, CREDENTIALS_PATH)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def clear_credentials() -> None:
    """Delete the cached credentials file, if present (used by `chickenstats logout`)."""
    CREDENTIALS_PATH.unlink(missing_ok=True)


def _lock_file(descriptor: int) -> None:
    """Block until this process holds the lock on an open file."""
    if sys.platform == "win32":
        while True:
            # LK_LOCK gives up after ten seconds, and a refresh can take longer
            with suppress(OSError):
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
                return
            time.sleep(0.1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_EX)


def _unlock_file(descriptor: int) -> None:
    """Release the lock on an open file."""
    if sys.platform == "win32":
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


@contextmanager
def credentials_lock() -> Iterator[None]:
    """Hold the refresh lock across threads and processes.

    The server revokes a refresh token when it is used, so two refreshes of one
    token cannot both succeed. Where the lock file cannot be created, as on a
    read-only mount, only threads are serialized.
    """
    with _REFRESH_LOCK:
        descriptor = None
        try:
            CREDENTIALS_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor = os.open(
                CREDENTIALS_PATH.with_name(f"{CREDENTIALS_PATH.name}.lock"), os.O_RDWR | os.O_CREAT, 0o600
            )
            _lock_file(descriptor)
        except OSError:
            pass

        try:
            yield
        finally:
            if descriptor is not None:
                with suppress(OSError):
                    _unlock_file(descriptor)
                os.close(descriptor)


# ---------------------------------------------------------------------------
# Refresh -- also used by ChickenUser on a 401, not just the CLI
# ---------------------------------------------------------------------------


def refresh_access_token(
    refresh_token: str, host: str = _DEFAULT_HOST, proxy: str | None = None, ca_bundle: str | None = None
) -> dict:
    """Exchange a refresh token for a fresh access_token/refresh_token pair.

    Returns a plain dict, matching what callers already expect. Raises
    AuthError on a rejected/expired refresh token.
    """
    try:
        token = _login_api(host, proxy, ca_bundle).login_refresh(
            chickenstats_api.RefreshTokenRequest(refresh_token=refresh_token), _request_timeout=REQUEST_TIMEOUT
        )
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"Refresh token rejected ({exc.status}) -- run `chickenstats login` again.") from exc
    return token.model_dump()


# ---------------------------------------------------------------------------
# Username/password login
# ---------------------------------------------------------------------------


def password_login(email: str, password: str, host: str = _DEFAULT_HOST) -> Credentials:
    """Exchange an email/password for chickenstats access/refresh tokens.

    Same POST /login/firebase-token route ChickenUser's own password-grant login
    already uses (chickenstats.api.api.ChickenUser.login) -- this is just the CLI's
    entry point into it, so `chickenstats login --password` and library users share
    one underlying auth path rather than two implementations of "log in with a
    password."
    """
    try:
        token = _login_api(host).login_firebase_token(
            username=email, password=password, _request_timeout=REQUEST_TIMEOUT
        )
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"Sign-in failed ({exc.status}): {exc.reason}") from exc

    if not token.refresh_token:
        raise AuthError(_UNVERIFIED_EMAIL_MESSAGE)
    return Credentials(access_token=token.access_token, refresh_token=token.refresh_token, email=email, host=host)


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

    Stores the result on the server instance (server.auth_code/server.received_state)
    rather than a module-level global, so a fresh HTTPServer per browser_login() call can't
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
            body = _callback_page(
                "chickenstats: sign-in failed", "Sign-in failed", "You can close this tab and check the terminal."
            )
        else:
            body = _callback_page(
                "chickenstats: signed in", "You're signed in", "You can close this tab and return to the terminal."
            )
        self.wfile.write(body.encode())

    def log_message(self, format, *args):  # noqa: A002 -- silence default request logging
        pass


def browser_login(host: str = _DEFAULT_HOST) -> Credentials:
    """Run the full browser OAuth flow and return the resulting Credentials.

    Does not write the credentials file itself -- callers (cli.py's `login`
    command) decide when/whether to persist, keeping this function usable for
    a one-off in-memory login too.
    """
    require_secure_host(host)

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
            # Always show the account chooser instead of reusing an active Google session
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
        raise AuthError("No authorization code received (timed out or canceled).")

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
        token = _login_api(host).login_verify_token(
            chickenstats_api.IdToken(id_token=firebase_id_token), _request_timeout=REQUEST_TIMEOUT
        )
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"chickenstats API sign-in failed ({exc.status}): {exc.reason}") from exc

    if not token.refresh_token:
        raise AuthError(_UNVERIFIED_EMAIL_MESSAGE)
    return token.access_token, token.refresh_token
