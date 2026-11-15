"""The saved login for the chickenstats API.

Backs both `chickenstats login` (chickenstats.cli) and ChickenUser's saved-login
fallback. There are two ways to sign in: a named API token (cs_...), or the device
flow, where the person approves a code on chickenstats.com.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import chickenstats_api
import chickenstats_api.exceptions
import urllib3
from requests.utils import get_environ_proxies

from chickenstats.api._api_constants import REQUEST_TIMEOUT
from chickenstats.exceptions import AuthError
from chickenstats.utilities.utilities import _default_user_agent

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

_DEFAULT_HOST = "https://api.chickenstats.com"
# An account with an unverified email gets no refresh token
_UNVERIFIED_EMAIL_MESSAGE = "Sign-in returned no refresh token. Verify your email address, then sign in again."

CREDENTIALS_PATH = Path.home() / ".chickenstats" / "credentials"

# Plain http would expose a token on the wire, so only a server on this machine may use it
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")

# Serializes refreshes in a process; the lock file does so across processes
_REFRESH_LOCK = threading.Lock()


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


def _session_client(access_token: str, host: str) -> chickenstats_api.ApiClient:
    """Build an SDK client for `host` that sends `access_token`."""
    api_client = build_api_client(host)
    api_client.configuration.access_token = access_token
    return api_client


@dataclass
class Credentials:
    """A saved login. A named API token (cs_...) is saved as the access token, with no refresh token."""

    access_token: str
    refresh_token: str | None
    email: str | None = None
    host: str = _DEFAULT_HOST


# ---------------------------------------------------------------------------
# POST /auth/token and its errors
# ---------------------------------------------------------------------------

REFRESH_GRANT = "refresh_token"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


class GrantError(AuthError):
    """A refused POST /auth/token, with the OAuth error code the server gave."""

    def __init__(self, message: str, error: str | None = None, status: int | None = None):
        super().__init__(message)
        self.error = error
        self.status = status


def oauth_error(exc: chickenstats_api.ApiException) -> tuple[str | None, str | None]:
    """Return the OAuth error code and description of an SDK error, when the server sent them."""
    data = getattr(exc, "data", None)
    if data is None:
        # The SDK only parses the status codes the spec lists, so read the body for the rest
        try:
            body = json.loads(exc.body or "")
        except (TypeError, ValueError):
            body = None
        data = body if isinstance(body, dict) else {}
        if not data.get("error"):
            data = dict(re.findall(r'(\w+)="([^"]*)"', (exc.headers or {}).get("WWW-Authenticate", ""))) or data
        detail = data.get("detail")
        return data.get("error"), data.get("error_description") or (detail if isinstance(detail, str) else None)
    return getattr(data, "error", None), getattr(data, "error_description", None) or getattr(data, "detail", None)


def request_token(
    api_client: chickenstats_api.ApiClient, timeout: tuple[float, float] = REQUEST_TIMEOUT, **fields: str
) -> chickenstats_api.Token:
    """Post one grant to /auth/token and return the token response.

    Raises:
        GrantError: If the server refuses the grant. Its `error` is the OAuth code, such as
            invalid_grant or authorization_pending.
    """
    try:
        return chickenstats_api.AuthApi(api_client).get_token(**fields, _request_timeout=timeout)
    except chickenstats_api.ApiException as exc:
        error, description = oauth_error(exc)
        raise GrantError(f"Sign-in failed: {description or error or exc.reason}", error, exc.status) from exc


# ---------------------------------------------------------------------------
# Credential file (~/.chickenstats/credentials)
# ---------------------------------------------------------------------------


def load_cached_credentials() -> Credentials | None:
    """Return cached credentials, or None if the file doesn't exist or is unreadable.

    Deliberately silent on any error (missing file, bad JSON, missing keys):
    ChickenUser treats a corrupt file the same as no saved login.
    """
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_PATH.read_text())
        return Credentials(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
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
def credentials_lock() -> Generator[None]:
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
        token = request_token(
            build_api_client(host, proxy, ca_bundle), grant_type=REFRESH_GRANT, refresh_token=refresh_token
        )
    except GrantError as exc:
        raise AuthError("Your chickenstats sign-in has ended. Run `chickenstats login` again.") from exc
    return token.model_dump()


# ---------------------------------------------------------------------------
# Device sign-in: the person approves a code on chickenstats.com
# ---------------------------------------------------------------------------


def device_login(
    host: str = _DEFAULT_HOST,
    show: Callable[[str, str], None] = lambda uri, code: print(f"Open {uri} and enter {code}"),
    sleep: Callable[[float], None] = time.sleep,
) -> Credentials:
    """Sign in by approving a code on chickenstats.com, and return the Credentials.

    Parameters:
        host: The API host.
        show: Called once with the page to open and the code to enter there.
        sleep: Waits between polls; tests pass a stub.

    Raises:
        AuthError: If the code is denied or expires, or the server refuses the sign-in.
    """
    api_client = build_api_client(host)
    try:
        device = chickenstats_api.AuthApi(api_client).start_device_sign_in(_request_timeout=REQUEST_TIMEOUT)
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"Could not start a device sign-in: {oauth_error(exc)[1] or exc.reason}") from exc

    show(device.verification_uri_complete or device.verification_uri, device.user_code)
    interval = device.interval or 5

    while True:
        sleep(interval)
        try:
            token = request_token(api_client, grant_type=DEVICE_GRANT, device_code=device.device_code)
            break
        except GrantError as exc:
            # A busy or briefly unavailable server is worth waiting out
            if exc.error == "authorization_pending" or exc.status in (429, 503):
                continue
            if exc.error == "slow_down":
                interval += 5
                continue
            if exc.error == "access_denied":
                raise AuthError("The sign-in was denied.") from exc
            if exc.error == "expired_token":
                raise AuthError("The code expired. Run `chickenstats login` again.") from exc
            raise

    if not token.refresh_token:
        raise AuthError(_UNVERIFIED_EMAIL_MESSAGE)
    return Credentials(token.access_token, token.refresh_token, _email_of(token.access_token, host), host)


def token_login(token: str, host: str = _DEFAULT_HOST) -> Credentials:
    """Check a named API token against the server and return it as Credentials to save.

    Raises:
        AuthError: If the server refuses the token, or it is a session token rather than a named one.
    """
    try:
        me = chickenstats_api.AuthApi(_session_client(token, host)).whoami(_request_timeout=REQUEST_TIMEOUT)
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"The token was refused: {oauth_error(exc)[1] or exc.reason}") from exc
    if me.kind != "named":
        raise AuthError("That is a sign-in session, not a named API token. Make one on chickenstats.com/account/api.")
    return Credentials(token, None, None, host)


def _email_of(access_token: str, host: str) -> str | None:
    """Return the signed-in email, or None if the server doesn't say."""
    with suppress(chickenstats_api.ApiException):
        auth = chickenstats_api.AuthApi(_session_client(access_token, host))
        return auth.whoami(_request_timeout=REQUEST_TIMEOUT).email
    return None


# ---------------------------------------------------------------------------
# Calls with a saved login: sign-out, whoami and named tokens
# ---------------------------------------------------------------------------


def with_saved_login(creds: Credentials, call: Callable[[chickenstats_api.ApiClient], object]):
    """Run `call` with the saved login's client, refreshing and saving it once if the access token expired.

    Raises:
        AuthError: If the sign-in has ended and can't be refreshed.
    """
    try:
        return call(_session_client(creds.access_token, creds.host))
    except chickenstats_api.exceptions.UnauthorizedException as exc:
        if oauth_error(exc)[1] != "token_expired" or not creds.refresh_token:
            raise AuthError("Your chickenstats sign-in has ended. Run `chickenstats login` again.") from exc

    with credentials_lock():
        saved = load_cached_credentials()
        if saved is not None and saved.refresh_token and saved.refresh_token != creds.refresh_token:
            creds.access_token, creds.refresh_token = saved.access_token, saved.refresh_token
        else:
            data = refresh_access_token(creds.refresh_token, creds.host)
            creds.access_token, creds.refresh_token = data["access_token"], data["refresh_token"]
            save_credentials(creds)
    return call(_session_client(creds.access_token, creds.host))


def revoke_saved_login(creds: Credentials) -> None:
    """End the saved session on the server. A saved named API token is left working; revoke it by name."""
    if not creds.refresh_token:
        return
    try:
        chickenstats_api.AuthApi(build_api_client(creds.host)).revoke_token(
            token=creds.refresh_token, token_type_hint="refresh_token", _request_timeout=REQUEST_TIMEOUT
        )
    except chickenstats_api.ApiException as exc:
        raise AuthError(f"Could not sign out on the server: {oauth_error(exc)[1] or exc.reason}") from exc
    except urllib3.exceptions.HTTPError as exc:
        raise AuthError(f"Could not reach {creds.host} to sign out: {exc}") from exc
