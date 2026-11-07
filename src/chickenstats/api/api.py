from __future__ import annotations

import json
import os
import re
import threading
import time
import warnings
from typing import TYPE_CHECKING, Any, Generic, Literal, overload

import chickenstats_api
import polars as pl
import urllib3
from chickenstats_api.exceptions import ApiException, BadRequestException, UnauthorizedException

from chickenstats.api._api_constants import (
    IDS_MAX_LIMIT,
    MAX_RETRY_WAIT,
    PAGE_RETRIES,
    PBP_MAX_LIMIT,
    PRED_GOAL_MAX_LIMIT,
    RAW_MAX_LIMIT,
    REQUEST_TIMEOUT,
    RETRY_STATUSES,
    STATS_MAX_LIMIT,
)
from chickenstats.api._api_utils import _to_int_list, _to_str_list
from chickenstats.exceptions import APIDownloadError, AuthError, UnsupportedBackendError
from chickenstats.utilities import ChickenProgress, ChickenProgressIndeterminate
from chickenstats.utilities.enums import Backend
from chickenstats.utilities.types import FrameT
from chickenstats.utilities.utilities import _to_backend, _validate_backend

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    from chickenstats.utilities.types import (
        AnyBackend,
        NarwhalsBackend,
        NarwhalsFrame,
        PandasBackend,
        PolarsBackend,
        PyarrowBackend,
    )


def _page_frame(rows: list) -> pl.DataFrame:
    """Build a frame from one page, reading every row so a column of leading nulls keeps its real type."""
    return pl.DataFrame(rows, infer_schema_length=None)


def _tier_cap(error: BadRequestException) -> int | None:
    """Return the page size the server allows, from the 400 it sends for a limit above the caller's tier."""
    try:
        detail = json.loads(error.body or "")["detail"]
    except (TypeError, ValueError, KeyError):
        return None

    match = re.search(r"exceeds the maximum of (\d+) rows", str(detail))
    return int(match.group(1)) if match else None


def _retry_wait(error: Exception, attempt: int) -> float:
    """Return the seconds to wait before a retry: the server's Retry-After, or a doubling backoff."""
    headers = getattr(error, "headers", None) or {}
    try:
        wait = float(headers.get("Retry-After", 2**attempt))
    except ValueError:
        wait = 2**attempt

    return min(wait, MAX_RETRY_WAIT)


# no cover: start


class ChickenUser:
    """Generate login tokens and user information for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_API_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_API_PASSWORD environment variable
        host (str):
            The URL for the chickenstats API. It must use https, unless it is a server on this
            machine. Default is the CHICKENSTATS_API_HOST environment variable, then the host
            of the cached login, then https://api.chickenstats.com
        cf_client_id (str):
            Cloudflare Access service token client ID, the credential for pipelines. With
            cf_client_secret and no username and password, no login is made and neither a
            cached login nor a bearer token is used.
            Default is the CHICKENSTATS_API_CF_CLIENT_ID environment variable
        cf_client_secret (str):
            Cloudflare Access service token client secret.
            Default is the CHICKENSTATS_API_CF_CLIENT_SECRET environment variable
        timeout (tuple[float, float]):
            Connect and read timeouts, in seconds, for every request. Default is (3.05, 60)
        proxy (str):
            The proxy URL. Default is the proxy the environment sets for the host, respecting NO_PROXY
        ca_bundle (str):
            The path to a CA bundle. Default is the REQUESTS_CA_BUNDLE environment variable,
            then SSL_CERT_FILE

    Attributes:
        username (str):
            The username given on initialization for the chickenstats API
        password (str):
            The password given on initialization for the chickenstats API
        host (str):
            The URL given on initialization for the chickenstats API
        cf_client_id (str):
            Cloudflare Access client ID for programmatic access
        cf_client_secret (str):
            Cloudflare Access client secret for programmatic access
        access_token (str):
            The bearer token generated after logging into the chickenstats API

    Examples:
        Instantiate the object and generate the user information from default values
        >>> user = ChickenUser()

        You can access the bearer token with the access_token attribute
        >>> access_token = user.access_token

        You can access usernames and passwords from the user object
        >>> username = user.username
        >>> password = user.password

    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ):
        """Instantiates the user object for the chickenstats API.

        A username and password are used first, then a Cloudflare service token
        (client ID and secret together), then the cached login from
        `chickenstats login`. A cached login is only sent to the host it was
        made on, and without the Cloudflare headers.

        Raises:
            AuthError: If there is no credential to use, the cached login is for
                another host, or the host would receive credentials over plain http.
        """
        self.timeout = timeout
        self.username = username or os.environ.get("CHICKENSTATS_API_USERNAME")
        self.password = password or os.environ.get("CHICKENSTATS_API_PASSWORD")
        self.cf_client_id = cf_client_id or os.environ.get("CHICKENSTATS_API_CF_CLIENT_ID")
        self.cf_client_secret = cf_client_secret or os.environ.get("CHICKENSTATS_API_CF_CLIENT_SECRET")
        self.proxy = proxy
        self.ca_bundle = ca_bundle
        self.access_token = None
        self.refresh_token = None
        self._refresh_lock = threading.Lock()
        self._saved_refresh_token = None

        from chickenstats.api._auth import _DEFAULT_HOST, build_api_client, load_cached_credentials, same_host

        configured_host = host or os.environ.get("CHICKENSTATS_API_HOST")
        has_password = bool(self.username and self.password)
        has_service_token = bool(self.cf_client_id and self.cf_client_secret)

        cached = None if has_password or has_service_token else load_cached_credentials()
        self._from_cache = cached is not None

        if cached is not None and configured_host and not same_host(cached.host, configured_host):
            raise AuthError(
                f"The cached login is for {cached.host}, not {configured_host}. Run "
                f"`chickenstats login --host {configured_host}`, or pass username and password."
            )

        self.host = configured_host or (cached.host if cached is not None else _DEFAULT_HOST)

        self.api_client = build_api_client(self.host, proxy, ca_bundle)
        self.configuration = self.api_client.configuration

        if cached is not None:
            self._set_tokens(cached.access_token, cached.refresh_token)
            self._saved_refresh_token = cached.refresh_token
            return

        if self.cf_client_id:
            self.api_client.set_default_header("CF-Access-Client-Id", self.cf_client_id)
        if self.cf_client_secret:
            self.api_client.set_default_header("CF-Access-Client-Secret", self.cf_client_secret)

        if has_password:
            self.login()
        elif not has_service_token:
            raise AuthError(
                "No chickenstats login. Run `chickenstats login`, or pass username and password (or set "
                "CHICKENSTATS_API_USERNAME and CHICKENSTATS_API_PASSWORD), or set a Cloudflare service token "
                "with CHICKENSTATS_API_CF_CLIENT_ID and CHICKENSTATS_API_CF_CLIENT_SECRET."
            )

    def _set_tokens(self, access_token: str, refresh_token: str | None) -> None:
        """Use a new pair of tokens for every request from now on."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.configuration.access_token = access_token

    def login(self) -> None:
        """Log the user into the chickenstats API.

        Raises:
            AuthError: If this session has no username and password.
        """
        if not (self.username and self.password):
            raise AuthError("This session has no username and password to log in with.")

        api_instance = chickenstats_api.LoginApi(self.api_client)
        token = api_instance.login_firebase_token(
            username=self.username, password=self.password, _request_timeout=self.timeout
        )
        self._set_tokens(token.access_token, token.refresh_token)

    def refresh(self) -> None:
        """Exchange the cached refresh token for a fresh access token.

        ChickenStats calls this automatically when a request comes back 401,
        so you rarely need it directly. Rotates the refresh token too, and
        rewrites the credentials file if this session started from it.

        Raises:
            AuthError: If this session has no refresh token, or the server rejects it.

        Warns:
            UserWarning: If the credentials file cannot be written. The new tokens stay in use for this session.
        """
        if not self.refresh_token:
            raise AuthError(
                "No refresh token available: this session was started without one. "
                "Run `chickenstats login` or create a new ChickenUser."
            )

        access_token = self.access_token
        with self._refresh_lock:
            # Another thread refreshed while this one waited
            if self.access_token != access_token:
                return
            if self._from_cache:
                self._refresh_from_cache()
            else:
                self._set_tokens(*self._exchange_refresh_token())

    def _exchange_refresh_token(self) -> tuple[str, str]:
        """Return the new access and refresh tokens the server gives for this session's refresh token."""
        from chickenstats.api._auth import refresh_access_token

        data = refresh_access_token(self.refresh_token or "", self.host, self.proxy, self.ca_bundle)
        return data["access_token"], data["refresh_token"]

    def _refresh_from_cache(self) -> None:
        """Refresh a session that came from the credentials file, under a lock shared with other processes."""
        from chickenstats.api._auth import (
            Credentials,
            credentials_lock,
            load_cached_credentials,
            same_host,
            save_credentials,
        )

        with credentials_lock():
            cached = load_cached_credentials()
            current = cached is not None and same_host(cached.host, self.host)

            # Another process used this refresh token, which revoked it, and saved the new pair. The file is
            # compared with what this session last saw there, since a failed save leaves the file behind memory.
            if current and cached.refresh_token != self._saved_refresh_token:
                self._set_tokens(cached.access_token, cached.refresh_token)
                self._saved_refresh_token = cached.refresh_token
                return

            access_token, refresh_token = self._exchange_refresh_token()
            self._set_tokens(access_token, refresh_token)

            # A file that is gone or holds a login for another host was changed on purpose, so it stays as it is
            if not current:
                return

            try:
                save_credentials(Credentials(access_token, refresh_token, cached.email, cached.host))
                self._saved_refresh_token = refresh_token
            except OSError as exc:
                warnings.warn(
                    f"Could not save the refreshed chickenstats login: {exc}. It stays in use for this session, "
                    "but the saved refresh token no longer works, so run `chickenstats login` after it ends.",
                    UserWarning,
                    stacklevel=3,
                )

    def test_token(self):
        """Validate the current access token and return the user's profile.

        Returns:
            UserPublic: The current user's profile, including email, tier, and is_superuser.
        """
        api_instance = chickenstats_api.LoginApi(self.api_client)
        return api_instance.test_token(_request_timeout=self.timeout)

    def reset_password(self, current_password: str, new_password: str) -> None:
        """Update the password for the chickenstats API.

        Parameters:
            current_password (str):
                The current password for the chickenstats API.
            new_password (str):
                The new password for the chickenstats API.
        """
        self.login()

        api_instance = chickenstats_api.UsersApi(self.api_client)
        update_password_body = chickenstats_api.UpdatePassword(
            current_password=current_password, new_password=new_password
        )

        api_instance.update_password_me(update_password_body, _request_timeout=self.timeout)


class ChickenStats(Generic[FrameT]):
    """Generate an API instance for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_API_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_API_PASSWORD environment variable
        host (str):
            The URL for the chickenstats API. It must use https, unless it is a server on this
            machine. Default is the CHICKENSTATS_API_HOST environment variable, then the host
            of the cached login, then https://api.chickenstats.com
        backend (str):
            Output backend for the returned DataFrames — 'polars', 'pandas', 'pyarrow', or
            'narwhals'. Default is 'polars'.
        limit (int | None):
            Batch size for paginated requests. When None, uses the maximum allowed per
            endpoint (50,000 for play-by-play and most other endpoints, 100,000 for pred_goal).
        cf_client_id (str):
            Cloudflare Access service token client ID, the credential for pipelines. With
            cf_client_secret and no username and password, no login is made and neither a
            cached login nor a bearer token is used.
            Default is the CHICKENSTATS_API_CF_CLIENT_ID environment variable
        cf_client_secret (str):
            Cloudflare Access service token client secret.
            Default is the CHICKENSTATS_API_CF_CLIENT_SECRET environment variable
        timeout (tuple[float, float]):
            Connect and read timeouts, in seconds, for every request. Default is (3.05, 60)
        proxy (str):
            The proxy URL. Default is the proxy the environment sets for the host, respecting NO_PROXY
        ca_bundle (str):
            The path to a CA bundle. Default is the REQUESTS_CA_BUNDLE environment variable,
            then SSL_CERT_FILE

    Attributes:
        user (ChickenUser):
            A ChickenUser instance for the chickenstats API
        access_token (str):
            The bearer token the next request sends, the same as user.access_token. A request
            that comes back 401 refreshes it once and is sent again; if the server rejects the
            refresh token, the request raises chickenstats.exceptions.AuthError
        limit (int | None):
            Batch size for paginated requests

    Examples:
        Instantiate the object and generate the user information from default values
        >>> api_instance = ChickenStats()

        You can access the ChickenUser object underlying the instance
        >>> user = api_instance.user
        >>> username = user.username
        >>> user.reset_password(current_password="old_password", new_password="new_password")

        You can access the bearer token with the access_token attribute
        >>> access_token = api_instance.access_token

        You can then access various API endpoints, starting with play-by-play
        >>> seasons = [2024]
        >>> events = ["GOAL", "SHOT", "MISS"]
        >>> strengths = ["5v5"]
        >>> players = ["FILIP FORSBERG"]
        >>> play_by_play = api_instance.download_pbp(
        ...     season=seasons, event=events, player_1=players, strength_state=strengths
        ... )

        This will download stats data, with the progress bar disabled
        >>> stats = api_instance.download_game_stats(
        ...     season=seasons, player=players, strength_state=strengths, disable_progress_bar=True
        ... )

    """

    @overload
    def __init__(
        self: ChickenStats[pl.DataFrame],
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        backend: PolarsBackend = "polars",
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: ChickenStats[pd.DataFrame],
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        *,
        backend: PandasBackend,
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: ChickenStats[pa.Table],
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        *,
        backend: PyarrowBackend,
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: ChickenStats[NarwhalsFrame],
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        *,
        backend: NarwhalsBackend,
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ) -> None: ...
    @overload
    def __init__(
        self: ChickenStats[Any],
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        backend: AnyBackend = "polars",
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ) -> None: ...
    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        backend: Backend | Literal["polars", "pandas", "pyarrow", "narwhals"] = "polars",
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
        timeout: tuple[float, float] = REQUEST_TIMEOUT,
        proxy: str | None = None,
        ca_bundle: str | None = None,
    ):
        """Instantiates the ChickenStats object for the chickenstats API."""
        self.backend = _validate_backend(backend)
        self.user = ChickenUser(
            username=username,
            password=password,
            host=host,
            cf_client_id=cf_client_id,
            cf_client_secret=cf_client_secret,
            timeout=timeout,
            proxy=proxy,
            ca_bundle=ca_bundle,
        )
        self.limit = limit
        self._tier_limit: int | None = None

    @property
    def access_token(self) -> str | None:
        """The bearer token the next request sends, which changes when an expired token is refreshed."""
        return self.user.access_token

    def _finalize_dataframe(self, response) -> FrameT:
        """Finalize a dataframe for the configured backend before returning stats."""
        if self.backend not in (Backend.POLARS, Backend.PANDAS, Backend.PYARROW, Backend.NARWHALS):
            raise UnsupportedBackendError(f"Unsupported backend: {self.backend!r}")

        df = response if isinstance(response, pl.DataFrame) else _page_frame(response)

        # No rows means no columns either, and .row(0) below would raise on it.
        if df.is_empty():
            return _to_backend(df, self.backend)

        # Single vectorized pass over all columns instead of one is_not_null().any() reduction per column.
        has_data = df.select(pl.all().is_not_null().any()).row(0, named=True)
        df = df.select([col for col, keep in has_data.items() if keep])

        return _to_backend(df, self.backend)

    def _call(self, api_method, **kwargs):
        """Call an SDK method, refreshing an expired access token once on a 401.

        Cached credentials outlive their access token, so without this a script
        that worked yesterday fails today with a bare 401 that looks like a
        permissions problem rather than an expiry. Only retried once, and only
        when there's a refresh token to use -- a genuinely revoked or
        unauthorized credential still surfaces as a 401 rather than looping.
        A refresh token the server rejects raises AuthError from the refresh.
        """
        kwargs.setdefault("_request_timeout", self.user.timeout)
        try:
            return api_method(**kwargs)
        except UnauthorizedException:
            if not self.user.refresh_token:
                raise
            self.user.refresh()
            return api_method(**kwargs)

    def _fetch_paginated(self, api_method, limit, progress, progress_task, pbar_message, **kwargs) -> pl.DataFrame:
        """Page through all results from an API endpoint.

        The default page size is the largest any tier allows, and a tier below that gets a 400 naming its own
        maximum. The client takes that size for the rest of the session. A limit the caller chose is left alone.
        """
        pages = []
        offset = 0

        while True:
            response, limit = self._fetch_tier_page(api_method, limit, offset, **kwargs)

            pages.append(_page_frame(response.data))

            if offset == 0:
                progress.update(progress_task, total=response.total, description=pbar_message, refresh=True)

            progress.update(progress_task, advance=response.count, refresh=True)

            if not response.has_next:
                break

            offset += response.count

        # A column can be all null on one page, or integers on one and floats on the next
        return pl.concat(pages, how="diagonal_relaxed")

    def _fetch_tier_page(self, api_method, limit, offset, **kwargs) -> tuple[Any, int]:
        """Fetch one page at the largest size the tier allows, and return it with that size."""
        if self._tier_limit is not None:
            limit = min(limit, self._tier_limit)

        while True:
            try:
                return self._fetch_page(api_method, limit, offset, **kwargs), limit
            except BadRequestException as error:
                cap = _tier_cap(error)
                if self.limit is not None or cap is None or cap >= limit:
                    raise
                self._tier_limit = limit = cap

    def _fetch_ids(self, api_method, **kwargs) -> list[int]:
        """Page through an ID endpoint until a page comes back short.

        The ID endpoints return a bare list with no total or has_next, and the server sends at most
        10,000 IDs, or the tier's maximum, when no limit is given.
        """
        ids: list[int] = []
        limit = self.limit or IDS_MAX_LIMIT

        while True:
            page, limit = self._fetch_tier_page(api_method, limit, len(ids), **kwargs)
            ids.extend(page)

            if len(page) < limit:
                return ids

    def _fetch_page(self, api_method, limit, offset, **kwargs):
        """Fetch one page, retrying a rate limit, a gateway error or a dropped connection."""
        attempt = 0

        while True:
            try:
                return self._call(api_method, limit=limit, offset=offset, **kwargs)
            except (ApiException, urllib3.exceptions.HTTPError) as error:
                status = getattr(error, "status", None)
                if isinstance(error, ApiException) and status not in RETRY_STATUSES:
                    raise
                if attempt == PAGE_RETRIES:
                    raise APIDownloadError(
                        f"The chickenstats API download stopped at offset {offset} after {PAGE_RETRIES} retries: "
                        f"{error}",
                        offset=offset,
                        status=status,
                    ) from error

                time.sleep(_retry_wait(error, attempt))
                attempt += 1

    def check_pbp_game_ids(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the play-by-play endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading play-by-play game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.PlayByPlayApi(self.user.api_client)

            response = self._fetch_ids(
                api_instance.read_pbp_game_ids, season=_to_int_list(season), sessions=_to_str_list(sessions)
            )

            progress.update(
                progress_task,
                description="Downloaded play-by-play game IDs",
                completed=True,
                advance=True,
                refresh=True,
            )

        return response

    def check_pbp_play_ids(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what play IDs are already available from the play-by-play endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading play-by-play play IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.PlayByPlayApi(self.user.api_client)

            response = self._fetch_ids(
                api_instance.read_pbp_play_ids,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
            )

            progress.update(progress_task, description=pbar_message, completed=True, advance=True, refresh=True)

        return response

    def download_pbp(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        event: list[str] | str | None = None,
        player_1: list[str] | str | None = None,
        goalie: list[str] | str | None = None,
        event_team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download play-by-play data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            event (list[str] | None):
                Events (e.g., GOAL) to download. Defaults to all available.
            player_1 (list[str] | None):
                Event players to download. Defaults to all available.
            goalie (list[str] | None):
                Goalies to download. Defaults to all available.
            event_team (list[str] | None):
                Event teams to download. Defaults to all available.
            opp_team (list[str] | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 goals for Filip Forsberg in the last five seasons
            >>> cs_instance = ChickenStats()
            >>> forsberg_goals = cs_instance.download_pbp(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021],
            ...     event=["GOAL"],
            ...     player_1=["FILIP FORSBERG"],
            ...     strength_state=["5v5"],
            ... )

            The endpoint is pretty flexible - you can query multiple players and events
            >>> random_shots = cs_instance.download_pbp(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021],
            ...     event=["GOAL", "SHOT", "MISS"],
            ...     player_1=["FILIP FORSBERG", "STEVEN STAMKOS", "MATT DUCHENE"],
            ...     strength_state=["5v5", "4v4", "3v3"],
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or PBP_MAX_LIMIT

            api_instance = chickenstats_api.PlayByPlayApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_pbp,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
                event=_to_str_list(event),
                player_1=_to_str_list(player_1),
                goalie=_to_str_list(goalie),
                event_team=_to_str_list(event_team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl play-by-play data", refresh=True)

        return df

    def check_stats_game_ids(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the game stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.StatsApi(self.user.api_client)

            response = self._fetch_ids(
                api_instance.read_stats_game_ids, season=_to_int_list(season), sessions=_to_str_list(sessions)
            )

            progress.update(
                progress_task, description="Downloaded stats game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def download_game_stats(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        player: list[str] | str | None = None,
        eh_id: list[str] | str | None = None,
        api_id: list[int] | int | None = None,
        team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        score_state: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        level: str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download individual game stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            player (list[str] | None):
                Players to download. Defaults to all available.
            eh_id (list[str] | None):
                Evolving Hockey ID for players to download. Defaults to all available.
            api_id (list[int] | int | None):
                API ID for players to download. Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            opp_team (list[str] | str | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            score_state (bool):
                Include score state breakdown if True. Defaults to False.
            teammates (bool):
                Include teammate breakdown if True. Defaults to False.
            opposition (bool):
                Include opposition breakdown if True. Defaults to False.
            level (str | None):
                Aggregation level (e.g., "period"). Defaults to game level.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 stats for Filip Forsberg in the last five seasons
            >>> cs_instance = ChickenStats()
            >>> forsberg_stats = cs_instance.download_game_stats(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021],
            ...     player=["FILIP FORSBERG"],
            ...     strength_state=["5v5"],
            ... )

            The endpoint is pretty flexible - you can query multiple players
            >>> random_stats = cs_instance.download_game_stats(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021],
            ...     player=["FILIP FORSBERG", "STEVEN STAMKOS", "MATT DUCHENE"],
            ...     strength_state=["5v5", "4v4", "3v3"],
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.StatsApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_game_stats,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
                player=_to_str_list(player),
                api_id=_to_int_list(api_id),
                eh_id=_to_str_list(eh_id),
                team=_to_str_list(team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
                score_state=score_state,
                teammates=teammates,
                opposition=opposition,
                level=level,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl game stats data", refresh=True)

        return df

    def download_season_stats(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        player: list[str] | str | None = None,
        eh_id: list[str] | str | None = None,
        api_id: list[int] | int | None = None,
        team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        score_state: bool = False,
        teammates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download season-level aggregated stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            player (list[str] | None):
                Players to download. Defaults to all available.
            eh_id (list[str] | None):
                Evolving Hockey ID for players to download. Defaults to all available.
            api_id (list[int] | int | None):
                API ID for players to download. Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            opp_team (list[str] | str | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            score_state (bool):
                Include score state breakdown if True. Defaults to False.
            teammates (bool):
                Include teammate breakdown if True. Defaults to False.
            opposition (bool):
                Include opposition breakdown if True. Defaults to False.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 season stats for Filip Forsberg
            >>> cs_instance = ChickenStats()
            >>> forsberg_season = cs_instance.download_season_stats(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021],
            ...     player=["FILIP FORSBERG"],
            ...     strength_state=["5v5"],
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl season stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.StatsApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_season_stats,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                player=_to_str_list(player),
                api_id=_to_int_list(api_id),
                eh_id=_to_str_list(eh_id),
                team=_to_str_list(team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
                score_state=score_state,
                teammates=teammates,
                opposition=opposition,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl season stats data", refresh=True)

        return df

    def download_game_team_stats(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        score_state: bool = False,
        level: str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download game-level team stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            opp_team (list[str] | str | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            score_state (bool):
                Include score state breakdown if True. Defaults to False.
            level (str | None):
                Aggregation level (e.g., "period"). Defaults to game level.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 game team stats for the Nashville Predators
            >>> cs_instance = ChickenStats()
            >>> nsh_team_stats = cs_instance.download_game_team_stats(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.TeamStatsApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_game_team_stats,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
                team=_to_str_list(team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
                score_state=score_state,
                level=level,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl game team stats data", refresh=True)

        return df

    def download_season_team_stats(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        score_state: bool = False,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download season-level team stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            opp_team (list[str] | str | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            score_state (bool):
                Include score state breakdown if True. Defaults to False.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 season team stats for the Nashville Predators
            >>> cs_instance = ChickenStats()
            >>> nsh_season_team = cs_instance.download_season_team_stats(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl season team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.TeamStatsApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_season_team_stats,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                team=_to_str_list(team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
                score_state=score_state,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl season team stats data", refresh=True)

        return df

    def check_team_stats_game_ids(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the team stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading team stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.TeamStatsApi(self.user.api_client)

            response = self._fetch_ids(
                api_instance.read_team_stats_game_ids, season=_to_int_list(season), sessions=_to_str_list(sessions)
            )

            progress.update(
                progress_task, description="Downloaded team stats game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def check_lines_game_ids(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the lines endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading lines game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.LinesApi(self.user.api_client)

            response = self._fetch_ids(
                api_instance.read_lines_game_ids, season=_to_int_list(season), sessions=_to_str_list(sessions)
            )

            progress.update(
                progress_task, description="Downloaded lines game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def download_game_lines(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        score_state: bool = False,
        level: str | None = None,
        linemates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download game-level line stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            opp_team (list[str] | str | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            score_state (bool):
                Include score state breakdown if True. Defaults to False.
            level (str | None):
                Aggregation level (e.g., "period"). Defaults to game level.
            linemates (bool):
                Include linemate breakdown if True. Defaults to False.
            opposition (bool):
                Include opposition breakdown if True. Defaults to False.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 game line stats for the Nashville Predators
            >>> cs_instance = ChickenStats()
            >>> nsh_lines = cs_instance.download_game_lines(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game lines data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.LinesApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_game_lines,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
                team=_to_str_list(team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
                score_state=score_state,
                level=level,
                linemates=linemates,
                opposition=opposition,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl game lines data", refresh=True)

        return df

    def download_season_lines(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        team: list[str] | str | None = None,
        opp_team: list[str] | str | None = None,
        strength_state: list[str] | str | None = None,
        score_state: bool = False,
        linemates: bool = False,
        opposition: bool = False,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download season-level line stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            opp_team (list[str] | str | None):
                Opponents to download. Defaults to all available.
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
            score_state (bool):
                Include score state breakdown if True. Defaults to False.
            linemates (bool):
                Include linemate breakdown if True. Defaults to False.
            opposition (bool):
                Include opposition breakdown if True. Defaults to False.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download all 5v5 season line stats for the Nashville Predators
            >>> cs_instance = ChickenStats()
            >>> nsh_season_lines = cs_instance.download_season_lines(
            ...     season=[20242025, 20232024, 20222023, 20212022, 20202021], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl season lines data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.LinesApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_season_lines,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                team=_to_str_list(team),
                opp_team=_to_str_list(opp_team),
                strength_state=_to_str_list(strength_state),
                score_state=score_state,
                linemates=linemates,
                opposition=opposition,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl season lines data", refresh=True)

        return df

    def download_rapm(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        api_id: list[int] | int | None = None,
        name: list[str] | str | None = None,
        team: list[str] | str | None = None,
        situation: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download RAPM scores from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available.
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            api_id (list[int] | int | None):
                API ID for players to download. Defaults to all available.
            name (list[str] | str | None):
                Player names to download. Defaults to all available.
            team (list[str] | str | None):
                Teams to download. Defaults to all available.
            situation (list[str] | str | None):
                Situations (e.g., "5v5") to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download RAPM scores for Filip Forsberg in 5v5 situations
            >>> cs_instance = ChickenStats()
            >>> forsberg_rapm = cs_instance.download_rapm(
            ...     season=[20242025, 20232024, 20222023], name=["FILIP FORSBERG"], situation=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading RAPM scores..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.RapmApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_rapm,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                api_id=_to_int_list(api_id),
                player=_to_str_list(name),
                team=_to_str_list(team),
                situation=_to_str_list(situation),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded RAPM scores", refresh=True)

        return df

    def download_pred_goal(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download pre-computed pred_goal values from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available.
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download pred_goal values for the 2024 season
            >>> cs_instance = ChickenStats()
            >>> pred_goals = cs_instance.download_pred_goal(season=[20242025])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading pred_goal data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or PRED_GOAL_MAX_LIMIT

            api_instance = chickenstats_api.InferenceApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_pred_goal,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded pred_goal data", refresh=True)

        return df

    def get_live_games(self, disable_progress_bar: bool = True) -> FrameT:
        """Get currently live games from the chickenstats API.

        Parameters:
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Get all currently live games
            >>> cs_instance = ChickenStats()
            >>> live_games = cs_instance.get_live_games()

        """
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Fetching live games..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.LiveApi(self.user.api_client)

            data = self._call(api_instance.read_live_games)

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Fetched live games", completed=True, advance=True, refresh=True)

        return df

    def download_live_pbp(
        self, game_id: list[str | int] | str | int | None = None, disable_progress_bar: bool = False
    ) -> FrameT:
        """Download live play-by-play data from the chickenstats API.

        Parameters:
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download live play-by-play for a specific game
            >>> cs_instance = ChickenStats()
            >>> live_pbp = cs_instance.download_live_pbp(game_id=[2024021000])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading live play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or STATS_MAX_LIMIT

            api_instance = chickenstats_api.LiveApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_live_pbp,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                game_id=_to_int_list(game_id),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded live play-by-play data", refresh=True)

        return df

    def check_roster_game_ids(self, disable_progress_bar: bool = True) -> list:
        """Check what game IDs are already available from the rosters endpoint.

        Parameters:
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            >>> cs_instance = ChickenStats()
            >>> game_ids = cs_instance.check_roster_game_ids()

        """
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading roster game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.RostersApi(self.user.api_client)

            response = self._fetch_ids(api_instance.read_roster_game_ids)

            progress.update(
                progress_task, description="Downloaded roster game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def download_rosters(
        self,
        game_id: list[str | int] | str | int | None = None,
        api_id: list[str | int] | str | int | None = None,
        team: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download game rosters from the chickenstats API.

        The API equivalent of ``Scraper.rosters`` -- pre-computed, so it avoids
        re-scraping the NHL for historical games. Note there's no ``season``
        filter on this endpoint; use ``check_roster_game_ids`` to find game IDs.

        Parameters:
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            api_id (list[str | int] | None):
                NHL API player IDs to download. Defaults to all available.
            team (list[str] | None):
                Teams to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download rosters for a single game
            >>> cs_instance = ChickenStats()
            >>> rosters = cs_instance.download_rosters(game_id=[2023020001])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading rosters data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or RAW_MAX_LIMIT

            api_instance = chickenstats_api.RostersApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_rosters,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                game_id=_to_int_list(game_id),
                api_id=_to_int_list(api_id),
                team=_to_str_list(team),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded rosters data", refresh=True)

        return df

    def download_shifts(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        api_id: list[str | int] | str | int | None = None,
        team: list[str] | str | None = None,
        period: list[str | int] | str | int | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download shifts data from the chickenstats API.

        The API equivalent of ``Scraper.shifts`` -- pre-computed, so it avoids
        re-scraping the NHL for historical games.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available.
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            api_id (list[str | int] | None):
                NHL API player IDs to download. Defaults to all available.
            team (list[str] | None):
                Teams to download. Defaults to all available.
            period (list[str | int] | None):
                Periods to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download shifts for a single game
            >>> cs_instance = ChickenStats()
            >>> shifts = cs_instance.download_shifts(game_id=[2023020001])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading shifts data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or RAW_MAX_LIMIT

            api_instance = chickenstats_api.ShiftsApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_shifts,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
                api_id=_to_int_list(api_id),
                team=_to_str_list(team),
                period=_to_int_list(period),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded shifts data", refresh=True)

        return df

    def download_changes(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        game_id: list[str | int] | str | int | None = None,
        event_team: list[str] | str | None = None,
        period: list[str | int] | str | int | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download line changes from the chickenstats API.

        The API equivalent of ``Scraper.changes`` -- pre-computed, so it avoids
        re-scraping the NHL for historical games.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available.
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            game_id (list[str | int] | None):
                Game IDs to download. Defaults to all available.
            event_team (list[str] | None):
                Event teams to download. Defaults to all available.
            period (list[str | int] | None):
                Periods to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download changes for a single game
            >>> cs_instance = ChickenStats()
            >>> changes = cs_instance.download_changes(game_id=[2023020001])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading changes data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or RAW_MAX_LIMIT

            api_instance = chickenstats_api.ChangesApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_changes,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                game_id=_to_int_list(game_id),
                event_team=_to_str_list(event_team),
                period=_to_int_list(period),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded changes data", refresh=True)

        return df

    def download_games(
        self,
        season: list[str | int] | str | int | None = None,
        sessions: list[str] | str | None = None,
        team: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download game metadata (dates, scores, outcomes) from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download, as 8-digit IDs (e.g., 20232024).
                Defaults to all seasons available.
            sessions (list[str] | None):
                Sessions (i.e., regular season or playoffs) to download.
                Defaults to all available.
            team (list[str] | None):
                Teams to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download Nashville's 2023-24 games
            >>> cs_instance = ChickenStats()
            >>> games = cs_instance.download_games(season=[20232024], team=["NSH"])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading games data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or RAW_MAX_LIMIT

            api_instance = chickenstats_api.GamesApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_games,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=_to_int_list(season),
                sessions=_to_str_list(sessions),
                team=_to_str_list(team),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded games data", refresh=True)

        return df

    def download_players(
        self,
        name: list[str] | str | None = None,
        api_id: list[str | int] | str | int | None = None,
        eh_id: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> FrameT:
        """Download player biographical data from the chickenstats API.

        Includes birth date/city/country, height, weight, shoots/catches --
        none of which the scraper produces.

        Parameters:
            name (list[str] | None):
                Player names to download, matched as substrings -- "FORSBERG"
                returns every Forsberg. Defaults to all available.
            api_id (list[str | int] | None):
                NHL API player IDs to download. Defaults to all available.
            eh_id (list[str] | None):
                Evolving Hockey IDs to download. Defaults to all available.
            disable_progress_bar (bool):
                Disables the progress bar if True.

        Examples:
            Download biographical data for several players at once
            >>> cs_instance = ChickenStats()
            >>> players = cs_instance.download_players(name=["FILIP FORSBERG", "ROMAN JOSI"])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading players data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or RAW_MAX_LIMIT

            api_instance = chickenstats_api.PlayersApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_players,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                name=_to_str_list(name),
                api_id=_to_int_list(api_id),
                eh_id=_to_str_list(eh_id),
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded players data", refresh=True)

        return df


# no cover: stop
