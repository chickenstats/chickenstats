import os
from typing import Literal

import numpy as np
import pandas as pd
import polars as pl

from chickenstats.chicken_nhl._validation import LineSchema, PBPSchema, StatSchema, TeamStatSchema
from chickenstats.utilities import ChickenProgress, ChickenProgressIndeterminate

import chickenstats_api


# no cover: start


def _prep_pbp_pandas(pbp: pd.DataFrame) -> list[dict]:
    """Function to prepare a play-by-play dataframe for uploading to the chickenstats API."""
    pbp = pbp.copy()

    goalie_cols = [
        "player_1_api_id",
        "player_2_api_id",
        "player_3_api_id",
        "own_goalie_api_id",
        "opp_goalie_api_id",
        "change_on_goalie_api_id",
        "change_off_goalie_api_id",
        "home_goalie_api_id",
        "away_goalie_api_id",
    ]

    for goalie_col in goalie_cols:
        pbp[goalie_col] = pbp[goalie_col].astype(str).fillna("").astype(str).str.replace(".0", "")

    percent_cols = ["forwards_percent", "opp_forwards_percent"]
    pbp[percent_cols] = pbp[percent_cols].fillna(0.0)

    columns = [x for x in list(PBPSchema.dtypes.keys()) if x in pbp.columns]
    pbp = PBPSchema.validate(pbp[columns])

    pbp = pbp.replace(np.nan, None).replace("nan", None).replace("", None).replace(" ", None)

    api_id_cols = ["player_1_api_id", "player_2_api_id", "player_3_api_id"]
    pbp[api_id_cols] = pbp[api_id_cols].replace("BENCH", None).replace("REFEREE", None).astype("Int64")

    pbp = pbp.to_dict(orient="records")

    return pbp


def _prep_stats_pandas(stats: pd.DataFrame) -> list[dict]:
    """Function to prepare a stats dataframe for uploading to the chickenstats API."""
    stats = stats.copy()

    columns = [x for x in StatSchema.dtypes.keys() if x in stats.columns]

    stats = StatSchema.validate(stats[columns])

    stats = stats.replace(np.nan, None).replace("nan", None).replace("", None).replace(" ", None)

    stats_id = pd.Series(
        data=(
            stats.game_id.astype(str).copy()
            + "_"
            + "0"
            + stats.period.astype(str).copy()
            + "_"
            + stats.score_state
            + "_"
            + stats.strength_state
            + "_"
            + stats.team
            + "_"
            + stats.api_id.astype(str)
            + "_"
            + stats.forwards_api_id.astype(str).str.replace(", ", "_")
            + "_"
            + stats.defense_api_id.astype(str).str.replace(", ", "_")
            + "_"
            + stats.own_goalie_api_id.astype(str).str.replace(", ", "_")
            + "_"
            + stats.opp_team
            + "_"
            + stats.opp_forwards_api_id.astype(str).str.replace(", ", "_")
            + "_"
            + stats.opp_defense_api_id.astype(str).str.replace(", ", "_")
            + "_"
            + stats.opp_goalie_api_id.astype(str).str.replace(", ", "_")
        ),
        index=stats.index,
        name="id",
        copy=True,
    )

    stats = pd.concat([stats_id, stats], axis=1)

    column_order = [x for x in stats.columns if x != "id"]

    column_order.insert(0, "id")

    stats = stats[column_order]

    stats = stats.to_dict(orient="records")

    return stats


def _prep_pbp_polars(pbp: pl.DataFrame) -> list[dict]:
    """Function to prepare a play-by-play dataframe for uploading to the chickenstats API."""
    pbp = pbp.with_columns(pl.col(pl.String).replace(old=["", " ", "nan"], new=[None, None, None]))
    pbp = pbp.fill_nan(None)

    pbp = pbp.with_columns(
        forwards_percent=pl.col("forwards_percent").fill_null(0.0),
        opp_forwards_percent=pl.col("opp_forwards_percent").fill_null(0.0),
        player_1_api_id=pl.col("player_1_api_id")
        .replace(old="BENCH", new=None)
        .replace(old="REFEREE", new=None)
        .cast(pl.Int64),
        player_2_api_id=pl.col("player_2_api_id")
        .replace(old="BENCH", new=None)
        .replace(old="REFEREE", new=None)
        .cast(pl.Int64),
        player_3_api_id=pl.col("player_3_api_id")
        .replace(old="BENCH", new=None)
        .replace(old="REFEREE", new=None)
        .cast(pl.Int64),
    )

    pbp = pbp.to_dicts()

    return pbp


def _prep_stats_polars(stats: pl.DataFrame) -> list[dict]:
    """Function to prepare a stats dataframe for uploading to the chickenstats API."""
    stats = stats.with_columns(pl.col(pl.String).replace(old=["", " ", "nan"], new=[None, None, None]))
    stats = stats.fill_nan(None)

    stats = stats.with_columns(
        id=(
            stats["game_id"].cast(pl.String)
            + "_"
            + "0"
            + stats["period"].cast(pl.String)
            + "_"
            + stats["score_state"]
            + "_"
            + stats["strength_state"]
            + "_"
            + stats["team"]
            + "_"
            + stats["api_id"].cast(pl.String)
            + "_"
            + stats["forwards_api_id"].cast(pl.String).str.replace_all(", ", "_").replace(None, "")
            + "_"
            + stats["defense_api_id"].cast(pl.String).str.replace_all(", ", "_").replace(None, "")
            + "_"
            + stats["own_goalie_api_id"].cast(pl.String).str.replace_all(", ", "_").replace(None, "")
            + "_"
            + stats["opp_team"]
            + "_"
            + stats["opp_forwards_api_id"].cast(pl.String).str.replace_all(", ", "_").replace(None, "")
            + "_"
            + stats["opp_defense_api_id"].cast(pl.String).str.replace_all(", ", "_").replace(None, "")
            + "_"
            + stats["opp_goalie_api_id"].cast(pl.String).str.replace_all(", ", "_").replace(None, "")
        )
    )

    column_order = [x for x in stats.columns if x != "id"]

    column_order.insert(0, "id")

    stats = stats.select(column_order)

    stats = stats.to_dicts()

    return stats


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
            # Create an instance of the API class
            api_instance = chickenstats_api.LoginApi(api_client)

            token = api_instance.login_login_access_token(username=self.username, password=self.password)

            self.token = token
            self.access_token = token.access_token
            self.configuration.access_token = token.access_token

    def reset_password(self, new_password: str) -> None:
        """Method to reset the password for the chickenstats API."""
        self.login()

        with chickenstats_api.ApiClient(self.configuration) as api_client:
            api_instance = chickenstats_api.LoginApi(api_client)
            new_password = chickenstats_api.NewPassword(
                token=self.configuration.access_token, new_password=new_password
            )

            api_instance.login_reset_password(new_password)


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

        if self.backend == "pandas":
            response = [dict(x) for x in response]
            df = pd.DataFrame.from_records(response).dropna(how="all", axis=1)

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

            # Enter a context with an instance of the API client
            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                # Create an instance of the API class
                api_instance = chickenstats_api.ChickenNhlApi(api_client)

                response = api_instance.chicken_nhl_read_pbp_game_ids(season=season, sessions=sessions)

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
                api_instance = chickenstats_api.ChickenNhlApi(api_client)

                response = api_instance.chicken_nhl_read_pbp_play_ids(season=season, sessions=sessions, game_id=game_id)

            progress.update(progress_task, description=pbar_message, completed=True, advance=True, refresh=True)

        return response

    def upload_pbp(self, pbp: pd.DataFrame | pl.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload play-by-play data to the chickenstats API. Only available for superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            if isinstance(pbp, pd.DataFrame):
                pbp = _prep_pbp_pandas(pbp)

            if isinstance(pbp, pl.DataFrame):
                pbp = _prep_pbp_polars(pbp)

            progress.start_task(progress_task)
            progress_total = len(pbp)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.PlayByPlayApi(api_client)

                for _idx, row in enumerate(pbp):
                    api_instance.chicken_nhl_create_pbp(row)

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

                response = api_instance.chicken_nhl_read_pbp(
                    season=season,
                    sessions=sessions,
                    game_id=game_id,
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

                response = api_instance.chicken_nhl_read_stats_game_ids(season=season, sessions=sessions)

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
                stats = _prep_stats_pandas(stats)

            if isinstance(stats, pl.DataFrame):
                stats = _prep_stats_polars(stats)

            progress.start_task(progress_task)
            progress_total = len(stats)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with chickenstats_api.ApiClient(self.user.configuration) as api_client:
                api_instance = chickenstats_api.StatsApi(api_client)

                for _idx, row in enumerate(stats):
                    api_instance.chicken_nhl_create_stats(row)

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

                response = api_instance.chicken_nhl_read_game_stats(
                    season=season,
                    sessions=sessions,
                    game_id=game_id,
                    player=player,
                    api_id=api_id,
                    eh_id=eh_id,
                    team=team,
                    opp_team=opp_team,
                    strength_state=strength_state,
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


# no cover: stop
