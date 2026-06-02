from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

import chickenstats_api
import polars as pl

if TYPE_CHECKING:
    import pandas as pd

from chickenstats.api._api_utils import _to_int_list, _to_str_list
from chickenstats.utilities import ChickenProgress, ChickenProgressIndeterminate


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
            The URL for the chickenstats API. Default is https://api.chickenstats.com
        cf_client_id (str):
            Cloudflare Access service token client ID for programmatic access.
            Default is the CHICKENSTATS_API_CF_CLIENT_ID environment variable
        cf_client_secret (str):
            Cloudflare Access service token client secret for programmatic access.
            Default is the CHICKENSTATS_API_CF_CLIENT_SECRET environment variable

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
    ):
        """Instantiates the user object for the chickenstats API."""
        self.username = username or os.environ.get("CHICKENSTATS_API_USERNAME")
        self.password = password or os.environ.get("CHICKENSTATS_API_PASSWORD")
        self.host = host or os.environ.get("CHICKENSTATS_API_HOST") or "https://api.chickenstats.com"
        self.cf_client_id = cf_client_id or os.environ.get("CHICKENSTATS_API_CF_CLIENT_ID")
        self.cf_client_secret = cf_client_secret or os.environ.get("CHICKENSTATS_API_CF_CLIENT_SECRET")

        self.configuration = chickenstats_api.Configuration(host=self.host)
        self.api_client = chickenstats_api.ApiClient(self.configuration)
        if self.cf_client_id:
            self.api_client.set_default_header("CF-Access-Client-Id", self.cf_client_id)
        if self.cf_client_secret:
            self.api_client.set_default_header("CF-Access-Client-Secret", self.cf_client_secret)

        self.access_token = None
        self.login()

    def login(self) -> None:
        """Method to log the user into the chickenstats API."""
        api_instance = chickenstats_api.LoginApi(self.api_client)
        token = api_instance.login_auth0_token(username=self.username or "", password=self.password or "")
        self.access_token = token.access_token
        self.configuration.access_token = token.access_token

    def test_token(self):
        """Validate the current access token and return the user's profile.

        Returns:
            UserPublic: The current user's profile, including email, tier, and is_superuser.
        """
        api_instance = chickenstats_api.LoginApi(self.api_client)
        return api_instance.test_token()

    def reset_password(self, current_password: str, new_password: str) -> None:
        """Method to update the password for the chickenstats API.

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

        api_instance.update_password_me(update_password_body)


class ChickenStats:
    """Generate an API instance for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_API_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_API_PASSWORD environment variable
        host (str):
            The URL for the chickenstats API. Default is https://api.chickenstats.com
        limit (int | None):
            Batch size for paginated requests. When None, uses the maximum allowed per
            endpoint (100,000 for play-by-play, 50,000 for all other endpoints).
        cf_client_id (str):
            Cloudflare Access service token client ID for programmatic access.
            Default is the CHICKENSTATS_API_CF_CLIENT_ID environment variable
        cf_client_secret (str):
            Cloudflare Access service token client secret for programmatic access.
            Default is the CHICKENSTATS_API_CF_CLIENT_SECRET environment variable

    Attributes:
        user (ChickenUser):
            A ChickenUser instance for the chickenstats API
        access_token (str):
            The bearer token generated after logging into the chickenstats API
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

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        host: str | None = None,
        backend: Literal["polars", "pandas"] = "polars",
        limit: int | None = None,
        cf_client_id: str | None = None,
        cf_client_secret: str | None = None,
    ):
        """Instantiates the ChickenStats object for the chickenstats API."""
        self.user = ChickenUser(
            username=username,
            password=password,
            host=host,
            cf_client_id=cf_client_id,
            cf_client_secret=cf_client_secret,
        )
        self.access_token = self.user.access_token
        self.backend = backend
        self.limit = limit

    def _finalize_dataframe(self, response) -> pl.DataFrame | pd.DataFrame:
        """Internal method to finalize dataframes when returning stats."""
        if self.backend == "polars":
            df = pl.DataFrame(response)
            df = df.select(col for col in df if col.is_not_null().any())
        elif self.backend == "pandas":
            import pandas as pd

            response = [dict(x) for x in response]
            df = pd.DataFrame.from_records(response).dropna(how="all", axis=1)
        else:
            raise ValueError(f"Unsupported backend: {self.backend!r}")
        return df

    def _fetch_paginated(self, api_method, limit, progress, progress_task, pbar_message, **kwargs) -> list:
        """Internal method to paginate through all results from an API endpoint."""
        all_data = []
        offset = 0

        while True:
            response = api_method(limit=limit, offset=offset, **kwargs)
            all_data.extend(response.data)

            if offset == 0:
                progress.update(progress_task, total=response.total, description=pbar_message, refresh=True)

            progress.update(progress_task, advance=response.count, refresh=True)

            if not response.has_next:
                break

            offset += response.count

        return all_data

    def check_pbp_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the play-by-play endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading play-by-play game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.PlayByPlayApi(self.user.api_client)

            response = api_instance.read_pbp_game_ids(
                season=[int(x) for x in season] if season is not None else None, sessions=sessions
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
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        game_id: list[str | int] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what play IDs are already available from the play-by-play endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading play-by-play play IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.PlayByPlayApi(self.user.api_client)

            response = api_instance.read_pbp_play_ids(
                season=[int(x) for x in season] if season is not None else None,
                sessions=sessions,
                game_id=[int(x) for x in game_id] if game_id is not None else None,
            )

            progress.update(progress_task, description=pbar_message, completed=True, advance=True, refresh=True)

        return response

    def download_pbp(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        game_id: list[str | int] | None = None,
        event: list[str] | None = None,
        player_1: list[str] | None = None,
        goalie: list[str] | None = None,
        event_team: list[str] | None = None,
        opp_team: list[str] | None = None,
        strength_state: list[str] | None = None,
        disable_progress_bar: bool = False,
    ) -> pl.DataFrame | pd.DataFrame:
        """Download play-by-play data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020],
            ...     event=["GOAL"],
            ...     player_1=["FILIP FORSBERG"],
            ...     strength_state=["5v5"],
            ... )

            The endpoint is pretty flexible - you can query multiple players and events
            >>> random_shots = cs_instance.download_pbp(
            ...     season=[2024, 2023, 2022, 2021, 2020],
            ...     event=["GOAL", "SHOT", "MISS"],
            ...     player_1=["FILIP FORSBERG", "STEVEN STAMKOS", "MATT DUCHENE"],
            ...     strength_state=["5v5", "4v4", "3v3"],
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 100_000

            api_instance = chickenstats_api.PlayByPlayApi(self.user.api_client)

            data = self._fetch_paginated(
                api_instance.read_pbp,
                limit=limit,
                progress=progress,
                progress_task=progress_task,
                pbar_message=pbar_message,
                season=[int(x) for x in season] if season is not None else None,
                sessions=sessions,
                game_id=[int(x) for x in game_id] if game_id is not None else None,
                event=event,
                player_1=player_1,
                goalie=goalie,
                event_team=event_team,
                opp_team=opp_team,
                strength_state=strength_state,
            )

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Downloaded chicken_nhl play-by-play data", refresh=True)

        return df

    def check_stats_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the game stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.StatsApi(self.user.api_client)

            response = api_instance.read_stats_game_ids(
                season=[int(x) for x in season] if season is not None else None, sessions=sessions
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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download individual game stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020], player=["FILIP FORSBERG"], strength_state=["5v5"]
            ... )

            The endpoint is pretty flexible - you can query multiple players
            >>> random_stats = cs_instance.download_game_stats(
            ...     season=[2024, 2023, 2022, 2021, 2020],
            ...     player=["FILIP FORSBERG", "STEVEN STAMKOS", "MATT DUCHENE"],
            ...     strength_state=["5v5", "4v4", "3v3"],
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download season-level aggregated stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020], player=["FILIP FORSBERG"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl season stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download game-level team stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download season-level team stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl season team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the team stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading team stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.TeamStatsApi(self.user.api_client)

            response = api_instance.read_team_stats_game_ids(
                season=[int(x) for x in season] if season is not None else None, sessions=sessions
            )

            progress.update(
                progress_task, description="Downloaded team stats game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def check_team_stats_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what row IDs are already available from the team stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading team stats IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.TeamStatsApi(self.user.api_client)

            response = api_instance.read_team_stats_ids(
                season=[int(x) for x in season] if season is not None else None, sessions=sessions
            )

            progress.update(
                progress_task, description="Downloaded team stats IDs", completed=True, advance=True, refresh=True
            )

        return response

    def check_lines_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what game IDs are already available from the lines endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading lines game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.LinesApi(self.user.api_client)

            response = api_instance.read_lines_game_ids(
                season=[int(x) for x in season] if season is not None else None, sessions=sessions
            )

            progress.update(
                progress_task, description="Downloaded lines game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def check_line_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ) -> list:
        """Check what row IDs are already available from the lines endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading line IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            api_instance = chickenstats_api.LinesApi(self.user.api_client)

            response = api_instance.read_line_ids(
                season=[int(x) for x in season] if season is not None else None, sessions=sessions
            )

            progress.update(
                progress_task, description="Downloaded line IDs", completed=True, advance=True, refresh=True
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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download game-level line stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game lines data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download season-level line stats data from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available
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
            ...     season=[2024, 2023, 2022, 2021, 2020], team=["NSH"], strength_state=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl season lines data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download RAPM scores from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available.
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
            ...     season=[2024, 2023, 2022], name=["FILIP FORSBERG"], situation=["5v5"]
            ... )

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading RAPM scores..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 50_000

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
                name=_to_str_list(name),
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
    ) -> pl.DataFrame | pd.DataFrame:
        """Download pre-computed pred_goal values from the chickenstats API.

        Parameters:
            season (list[str | int] | None):
                Seasons to download. Defaults to all seasons available.
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
            >>> pred_goals = cs_instance.download_pred_goal(season=[2024])

        """
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading pred_goal data..."
            progress_task = progress.add_task(pbar_message, total=None)

            progress.start_task(progress_task)

            limit = self.limit or 100_000

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

    def get_live_games(self, disable_progress_bar: bool = True) -> pl.DataFrame | pd.DataFrame:
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

            data = api_instance.read_live_games()

            df = self._finalize_dataframe(data)

            progress.update(progress_task, description="Fetched live games", completed=True, advance=True, refresh=True)

        return df

    def download_live_pbp(
        self, game_id: list[str | int] | str | int | None = None, disable_progress_bar: bool = False
    ) -> pl.DataFrame | pd.DataFrame:
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

            limit = self.limit or 50_000

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


# no cover: stop
