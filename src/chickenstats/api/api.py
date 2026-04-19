import os
from typing import Literal, cast

import chickenstats_api
import pandas as pd
import polars as pl

from chickenstats.api._api_utils import _player_stats_id, _team_stats_id, _to_int_list, _to_str_list
from chickenstats.utilities import ChickenProgress, ChickenProgressIndeterminate


# no cover: start


def _prep_pbp_polars(pbp: pl.DataFrame) -> list[dict]:
    """Prepare a play-by-play DataFrame for uploading to the chickenstats API."""
    return pbp.to_dicts()


def _prep_stats_polars(stats: pl.DataFrame) -> list[dict]:
    """Prepare a stats DataFrame for uploading to the chickenstats API."""
    stats = stats.with_columns(id=_player_stats_id())
    column_order = [x for x in stats.columns if x != "id"]
    column_order.insert(0, "id")
    return stats.select(column_order).to_dicts()


def _prep_team_stats_polars(team_stats: pl.DataFrame) -> list[dict]:
    """Prepare a stats DataFrame for uploading to the chickenstats API."""
    team_stats = team_stats.with_columns(id=_team_stats_id())
    column_order = [x for x in team_stats.columns if x != "id"]
    column_order.insert(0, "id")
    return team_stats.select(column_order).to_dicts()


class ChickenUser:
    """Generate login tokens and user information for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_PASSWORD environment variable
        host (str):
            The URL for the chickenstats API. Default is https://api.chickenstats.com

    Attributes:
        username (str):
            The username given on initialization for the chickenstats API
        password (str):
            The password given on initialization for the chickenstats API
        host (str):
            The URL given on initialization for the chickenstats API
        token (ChickenToken):
            Token object used for logging into the chickenstats API
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

    def __init__(self, username: str | None = None, password: str | None = None, host: str | None = None):
        """Instantiates the user object for the chickenstats API."""
        self.username = username
        self.password = password
        self.host = host

        if not username:
            self.username = os.environ.get("CHICKENSTATS_API_USERNAME")

        if not password:
            self.password = os.environ.get("CHICKENSTATS_API_PASSWORD")

        if not host:
            self.host = os.environ.get("CHICKENSTATS_API_HOST")

            if not self.host:
                self.host = "https://api.chickenstats.com"

        self.configuration = chickenstats_api.Configuration(
            username=self.username, password=self.password, host=self.host
        )

        self.token = None
        self.access_token = None
        self.login()

    def login(self) -> None:
        """Method to log the user into the chickenstats API."""
        with chickenstats_api.ApiClient(self.configuration) as api_client:
            api_instance = chickenstats_api.LoginApi(api_client)

            token = api_instance.login_access_token(username=self.username or "", password=self.password or "")

            self.token = token
            self.access_token = token.access_token
            self.configuration.access_token = token.access_token

    def reset_password(self, new_password: str) -> None:
        """Method to reset the password for the chickenstats API."""
        self.login()

        with chickenstats_api.ApiClient(self.configuration) as api_client:
            api_instance = chickenstats_api.LoginApi(api_client)
            new_password_body = chickenstats_api.NewPassword(
                token=self.configuration.access_token or "", new_password=new_password
            )

            api_instance.reset_password(new_password_body)


class ChickenStats:
    """Generate an API instance for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_PASSWORD environment variable
        host (str):
            The URL for the chickenstats API. Default is https://api.chickenstats.com

    Attributes:
        user (ChickenUser):
            A ChickenUser instance for the chickenstats API
        token (dict):
            A dictionary containing the response from the token URL
        access_token (str):
            The bearer token generated after logging into the chickenstats API

    Examples:
        Instantiate the object and generate the user information from default values
        >>> api_instance = ChickenStats()

        You can access the ChickenUser object underlying the instance
        >>> user = api_instance.user
        >>> username = user.username
        >>> user.reset_password(new_password="new_password")

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
    ):
        """Instantiates the ChickenStats object for the chickenstats API."""
        self.user = ChickenUser(username=username, password=password, host=host)
        self.token = self.user.token
        self.access_token = self.user.access_token
        self.backend = backend

    def _finalize_dataframe(self, response) -> pl.DataFrame | pd.DataFrame:
        """Internal method to finalize dataframes when returning stats."""
        if self.backend == "polars":
            df = pl.DataFrame(response)
            df = df.select(col for col in df if col.is_not_null().any())
        elif self.backend == "pandas":
            response = [dict(x) for x in response]
            df = pd.DataFrame.from_records(response).dropna(how="all", axis=1)
        else:
            raise ValueError(f"Unsupported backend: {self.backend!r}")
        return df

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

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.PlayByPlayApi(api_client)

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

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.PlayByPlayApi(api_client)

                response = api_instance.read_pbp_play_ids(
                    season=[int(x) for x in season] if season is not None else None,
                    sessions=sessions,
                    game_id=[int(x) for x in game_id] if game_id is not None else None,
                )

            progress.update(progress_task, description=pbar_message, completed=True, advance=True, refresh=True)

        return response

    def upload_pbp(self, pbp: pd.DataFrame | pl.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload play-by-play data to the chickenstats API. Only available for superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            if isinstance(pbp, pd.DataFrame):
                pbp = pl.from_pandas(pbp)
            pbp_records: list[dict] = _prep_pbp_polars(pbp)

            progress.start_task(progress_task)
            progress_total = len(pbp_records)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.AdminApi(api_client)

                for _idx, row in enumerate(pbp_records):
                    api_instance.create_pbp(cast(chickenstats_api.PbpPublic, row))

                    progress.update(progress_task, description=pbar_message, advance=1, refresh=True)

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

        Be mindful of your queries, it may fail if the table to return is too large :)

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
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.PlayByPlayApi(api_client)

                response = api_instance.read_pbp(
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

            df = self._finalize_dataframe(response)

            progress.update(
                progress_task,
                description="Downloaded chicken_nhl play-by-play data",
                completed=True,
                advance=True,
                refresh=True,
            )

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

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.StatsApi(api_client)

                response = api_instance.read_stats_game_ids(
                    season=[int(x) for x in season] if season is not None else None, sessions=sessions
                )

            progress.update(
                progress_task, description="Downloaded stats game IDs", completed=True, advance=True, refresh=True
            )

        return response

    def upload_stats(self, stats: pd.DataFrame | pl.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload data for the various stats endpoints. Only available to superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            if isinstance(stats, pd.DataFrame):
                stats = pl.from_pandas(stats)
            stats_records: list[dict] = _prep_stats_polars(stats)

            progress.start_task(progress_task)
            progress_total = len(stats_records)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.AdminApi(api_client)

                for _idx, row in enumerate(stats_records):
                    api_instance.create_stats(cast(chickenstats_api.StatsCreate, row))

                    progress.update(progress_task, description=pbar_message, advance=1, refresh=True)

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
        disable_progress_bar: bool = False,
    ) -> pl.DataFrame | pd.DataFrame:
        """Download individual game stats data from the chickenstats API.

        Be mindful of your queries, it may fail if the table to return is too large :)

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
            strength_state (list[str] | None):
                Strength states to download. Defaults to all available.
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
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading chicken_nhl game stats data..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.StatsApi(api_client)

                _season = _to_int_list(season)
                _sessions = _to_str_list(sessions)
                _game_id = _to_int_list(game_id)
                _player = _to_str_list(player)
                _api_id = _to_int_list(api_id)
                _eh_id = _to_str_list(eh_id)
                _team = _to_str_list(team)
                _opp_team = _to_str_list(opp_team)
                _strength_state = _to_str_list(strength_state)

                response = api_instance.read_game_stats(
                    season=_season,
                    sessions=_sessions,
                    game_id=_game_id,
                    player=_player,
                    api_id=_api_id,
                    eh_id=_eh_id,
                    team=_team,
                    opp_team=_opp_team,
                    strength_state=_strength_state,
                    score_state=score_state,
                    teammates=teammates,
                    opposition=opposition,
                )

            df = self._finalize_dataframe(response)

            progress.update(
                progress_task,
                description="Downloaded chicken_nhl game stats data",
                completed=True,
                advance=True,
                refresh=True,
            )

        return df

    def upload_team_stats(self, team_stats: pd.DataFrame | pl.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload data for the various stats endpoints. Only available to superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            if isinstance(team_stats, pd.DataFrame):
                team_stats = pl.from_pandas(team_stats)
            team_stats_records: list[dict] = _prep_team_stats_polars(team_stats)

            progress.start_task(progress_task)
            progress_total = len(team_stats_records)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.AdminApi(api_client)

                for _idx, row in enumerate(team_stats_records):
                    api_instance.create_team_stats(cast(chickenstats_api.TeamStatsCreate, row))

                    progress.update(progress_task, description=pbar_message, advance=1, refresh=True)


# no cover: stop
