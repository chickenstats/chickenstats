import os

import numpy as np
import pandas as pd

from chickenstats.chicken_nhl.validation import LineSchema, PBPSchema, StatSchema, TeamStatSchema
from chickenstats.utilities import ChickenProgress, ChickenProgressIndeterminate, ChickenSession


# no cover: start
class ChickenToken:
    """Generate login tokens for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_PASSWORD environment variable
        api_url (str):
            The URL for the chickenstats API. Default is https://api.chickenstats.com
        api_version (str):
            The api_version for the chickenstats API. Default is v1
        session (ChickenSession):
            The requests session for the chickenstats API

    Attributes:
        username (str):
            The username given on initialization for the chickenstats API
        password (str):
            The password given on initialization for the chickenstats API
        api_url (str):
            The URL given on initialization for the chickenstats API
        api_version (str):
            The api_version given on initialization for the chickenstats API
        token_url (str):
            The login token URL generated after initialization.
            Default is https://api.chickenstats.com/api/v1/login/access-token
        response (dict):
            A dictionary containing the response from the token URL
        access_token (str):
            The bearer token generated after logging into the chickenstats API
        requests_session (ChickenSession):
            The requests session for the chickenstats API

    Examples:
        Instantiate the object and generate the token response from default values
        >>> token = ChickenToken()

        You can access the bearer token with the access_token attribute
        >>> access_token = token.access_token

        You can access usernames and passwords from the token object
        >>> username = token.username
        >>> password = token.password

    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        api_url: str | None = None,
        api_version: str | None = None,
        session: ChickenSession | None = None,
    ):
        """Instantiates the ChickenToken object with the given URL, username, and password."""
        self.username = username
        self.password = password
        self.api_url = api_url
        self.api_version = api_version
        self.requests_session = session

        if not username:
            self.username = os.environ.get("CHICKENSTATS_USERNAME")

        if not password:
            self.password = os.environ.get("CHICKENSTATS_PASSWORD")

        if not api_url:
            self.api_url = "https://api.chickenstats.com"

        if not api_version:
            self.api_version = "v1"

        self.token_url = f"{self.api_url}/api/{self.api_version}/login/access-token"

        self.response = None
        self.access_token = None

        if not session:
            self.requests_session = ChickenSession()

        if not self.access_token:
            self.get_token()

    def get_token(self) -> str:
        """Method to generate an access token for the chickenstats API.

        Returns:
            access_token (str):
                The bearer token generated after logging into the chickenstats API

        Examples:
            >>> token = ChickenToken()
            >>> access_token = token.get_token()

        """
        data = {"username": self.username, "password": self.password}

        with self.requests_session as session:
            self.response = session.post(self.token_url, data=data).json()

        _response_access_token = self.response["access_token"]

        self.access_token = f"Bearer {_response_access_token}"

        return self.access_token


class ChickenUser:
    """Generate login tokens and user information for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_PASSWORD environment variable
        api_url (str):
            The URL for the chickenstats API. Default is https://api.chickenstats.com
        api_version (str):
            The api_version for the chickenstats API. Default is v1
        session (ChickenSession):
            The requests session for the chickenstats API

    Attributes:
        username (str):
            The username given on initialization for the chickenstats API
        password (str):
            The password given on initialization for the chickenstats API
        api_url (str):
            The URL given on initialization for the chickenstats API
        api_version (str):
            The api_version given on initialization for the chickenstats API
        token (ChickenToken):
            ChickenToken object used for logging into the chickenstats API
        access_token (str):
            The bearer token generated after logging into the chickenstats API
        requests_session (ChickenSession):
            The requests session for the chickenstats API

    Examples:
        Instantiate the object and generate the user information from default values
        >>> user = ChickenUser()

        You can access the bearer token with the access_token attribute
        >>> access_token = user.access_token

        You can reset your password with the reset_password method
        >>> user.reset_password(new_password="new_password")

        You can access usernames and passwords from the user object
        >>> username = user.username
        >>> password = user.password

        You can also access the underlying ChickenToken object and its attributes
        >>> api_url = user.token.api_url

    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        api_url: str | None = None,
        api_version: str | None = None,
        session: ChickenSession | None = None,
    ):
        """Instantiates the user object for the chickenstats API."""
        self.username = username
        self.password = password
        self.api_url = api_url
        self.api_version = api_version
        self.requests_session = session

        if not username:
            self.username = os.environ.get("CHICKENSTATS_USERNAME")

        if not password:
            self.password = os.environ.get("CHICKENSTATS_PASSWORD")

        if not api_url:
            self.api_url = "https://api.chickenstats.com"

        if not api_version:
            self.api_version = "v1"

        self.token = ChickenToken(
            api_url=self.api_url, api_version=self.api_version, username=self.username, password=self.password
        )
        self.access_token = self.token.access_token

        if not session:
            self.requests_session = ChickenSession()

    def reset_password(self, new_password: str):
        """Reset password in-place."""
        headers = {"Authorization": self.access_token}
        url = f"{self.api_url}/api/{self.api_version}/reset-password/"

        data = {"token": self.access_token.replace("Bearer ", ""), "new_password": new_password}

        with self.requests_session as session:
            response = session.post(url=url, json=data, headers=headers)

        return response


class ChickenStats:
    """Generate an API instance for the chickenstats API.

    Parameters:
        username (str):
            The username for the chickenstats API.
            Default is the CHICKENSTATS_USERNAME environment variable
        password (str):
            The password for the chickenstats API.
            Default is the CHICKENSTATS_PASSWORD environment variable
        api_url (str):
            The URL for the chickenstats API. Default is https://api.chickenstats.com
        api_version (str):
            The api_version for the chickenstats API. Default is v1
        session (ChickenSession):
            The requests session for the chickenstats API

    Attributes:
        user (ChickenUser):
            A ChickenUser instance for the chickenstats API
        token (dict):
            A dictionary containing the response from the token URL
        access_token (str):
            The bearer token generated after logging into the chickenstats API
        requests_session (ChickenSession):
            The requests session for the chickenstats API

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
        api_url: str | None = None,
        api_version: str | None = None,
        session: ChickenSession | None = None,
    ):
        """Instantiates the ChickenStats object for the chickenstats API."""
        self.user = ChickenUser(api_url=api_url, api_version=api_version, username=username, password=password)
        self.token = self.user.token
        self.access_token = self.user.access_token

        if not session:
            self.requests_session = ChickenSession()

        else:
            self.requests_session = session

    def check_pbp_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Check what game IDs are already available from the play-by-play endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading play-by-play game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/play_by_play/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description="Downloaded play-by-play game IDs",
                completed=True,
                advance=True,
                refresh=True,
            )

        return response.json()

    def check_pbp_play_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        game_id: list[str | int] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Check what play IDs are already available from the play-by-play endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading play-by-play play IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/play_by_play/play_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions, "game_id": game_id}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(progress_task, description=pbar_message, completed=True, advance=True, refresh=True)

        return response.json()

    def upload_pbp(self, pbp: pd.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload play-by-play data to the chickenstats API. Only available for superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            goalie_cols = [
                "own_goalie_api_id",
                "opp_goalie_api_id",
                "change_on_goalie_api_id",
                "change_off_goalie_api_id",
                "home_goalie_api_id",
                "away_goalie_api_id",
            ]

            for goalie_col in goalie_cols:
                pbp[goalie_col] = pbp[goalie_col].astype(str).fillna("").str.replace(".0", "")

            percent_cols = ["forwards_percent", "opp_forwards_percent"]
            pbp[percent_cols] = pbp[percent_cols].fillna(0.0)

            api_id_cols = ["player_1_api_id", "player_2_api_id", "player_3_api_id"]
            pbp[api_id_cols] = pbp[api_id_cols].replace("BENCH", None).replace("REFEREE", None)

            columns = [x for x in list(PBPSchema.dtypes.keys()) if x in pbp.columns]
            pbp = PBPSchema.validate(pbp[columns])

            pbp = pbp.replace(np.nan, None).replace("nan", None).replace("", None).replace(" ", None)

            pbp = pbp.to_dict(orient="records")

            progress.start_task(progress_task)
            progress_total = len(pbp)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with self.requests_session as session:
                for _idx, row in enumerate(pbp):
                    url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/play_by_play"
                    headers = {"Authorization": self.access_token}

                    response = session.post(url=url, headers=headers, json=row)

                    if response.status_code != 200:
                        if response.status_code == 422:
                            print(response.text)
                            break

                        break

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
    ) -> pd.DataFrame:
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
            >>> api_instance = ChickenStats()
            >>> forsberg_goals = api_instance.download_pbp(
            ...     season=[2024, 2023, 2022, 2021, 2020],
            ...     event=["GOAL"],
            ...     player_1=["FILIP FORSBERG"],
            ...     strength_state=["5v5"],
            ... )

            The endpoint is pretty flexible - you can query multiple players and events
            >>> random_shots = api_instance.download_pbp(
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

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/play_by_play"
                headers = {"Authorization": self.access_token}
                params = {
                    "season": season,
                    "sessions": sessions,
                    "game_id": game_id,
                    "event": event,
                    "player_1": player_1,
                    "goalie": goalie,
                    "event_team": event_team,
                    "opp_team": opp_team,
                    "strength_state": strength_state,
                }

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description="Downloaded chicken_nhl play-by-play data",
                completed=True,
                advance=True,
                refresh=True,
            )

        return pd.json_normalize(response.json())

    def check_stats_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Check what game IDs are already available from the game stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/stats/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task, description="Downloaded stats game IDs", completed=True, advance=True, refresh=True
            )

        return response.json()

    def upload_stats(self, stats: pd.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload data for the various stats endpoints. Only available to superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            columns = [x for x in list(StatSchema.dtypes.keys()) if x in stats.columns]
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

            progress.start_task(progress_task)
            progress_total = len(stats)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with self.requests_session as session:
                for _idx, row in enumerate(stats):
                    url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/stats"
                    headers = {"Authorization": self.access_token}

                    response = session.post(url=url, headers=headers, json=row)

                    if response.status_code != 200:
                        if response.status_code == 422:
                            print(response.text)
                            break

                        break

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
        strength_state: list[str] | str | None = None,
        disable_progress_bar: bool = False,
    ) -> pd.DataFrame:
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
            >>> api_instance = ChickenStats()
            >>> forsberg_stats = api_instance.download_game_stats(
            ...     season=[2024, 2023, 2022, 2021, 2020], player=["FILIP FORSBERG"], strength_state=["5v5"]
            ... )

            The endpoint is pretty flexible - you can query multiple players
            >>> random_stats = api_instance.download_game_stats(
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

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/stats/game"
                headers = {"Authorization": self.access_token}
                params = {
                    "season": season,
                    "sessions": sessions,
                    "game_id": game_id,
                    "player": player,
                    "eh_id": eh_id,
                    "api_id": api_id,
                    "team": team,
                    "strength_state": strength_state,
                }

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description="Downloaded chicken_nhl game stats data",
                completed=True,
                advance=True,
                refresh=True,
            )

        return pd.json_normalize(response.json()).dropna(how="all", axis=1)

    def check_lines_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Check what game IDs are already available from the line stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading line stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/lines/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task, description="Downloaded lines game IDs", completed=True, advance=True, refresh=True
            )

        return response.json()

    def upload_lines(self, lines: pd.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload data for the line stats endpoints. Only available to superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl line stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            columns = [x for x in list(LineSchema.dtypes.keys()) if x in lines.columns]
            lines = LineSchema.validate(lines[columns])

            lines = (
                lines.replace(np.nan, None)
                .replace("nan", None)
                .replace("", None)
                .replace(" ", None)
                .replace("EMPTY", None)
            )

            lines_id = pd.Series(
                data=(
                    lines.game_id.astype(str).copy()
                    + "_"
                    + "0"
                    + lines.period.astype(str).copy()
                    + "_"
                    + lines.score_state
                    + "_"
                    + lines.strength_state
                    + "_"
                    + lines.team
                    + "_"
                    + lines.forwards_api_id.astype(str).str.replace(", ", "_")
                    + "_"
                    + lines.defense_api_id.astype(str).str.replace(", ", "_")
                    + "_"
                    + lines.own_goalie_api_id.astype(str).str.replace(", ", "_")
                    + "_"
                    + lines.opp_team
                    + "_"
                    + lines.opp_forwards_api_id.astype(str).str.replace(", ", "_")
                    + "_"
                    + lines.opp_defense_api_id.astype(str).str.replace(", ", "_")
                    + "_"
                    + lines.opp_goalie_api_id.astype(str).str.replace(", ", "_")
                ),
                index=lines.index,
                name="id",
                copy=True,
            )

            lines = pd.concat([lines_id, lines], axis=1)

            column_order = [x for x in lines.columns if x != "id"]

            column_order.insert(0, "id")

            lines = lines[column_order]

            lines = lines.to_dict(orient="records")

            progress.start_task(progress_task)
            progress_total = len(lines)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with self.requests_session as session:
                for _idx, row in enumerate(lines):
                    url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/lines"
                    headers = {"Authorization": self.access_token}

                    response = session.post(url=url, headers=headers, json=row)

                    if response.status_code != 200:
                        if response.status_code == 422:
                            print(response.text)
                            break

                        break

                    progress.update(progress_task, description=pbar_message, advance=1, refresh=True)

    def check_team_stats_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Check what game IDs are already available from the team stats endpoint."""
        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = "Downloading team stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(progress_task, total=1, description=pbar_message, refresh=True)

            with self.requests_session as session:
                url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/team_stats/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task, description="Downloaded team stats game IDs", completed=True, advance=True, refresh=True
            )

        return response.json()

    def upload_team_stats(self, team_stats: pd.DataFrame, disable_progress_bar: bool = False) -> None:
        """Upload data for the team stats endpoints. Only available to superusers."""
        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = "Uploading chicken_nhl team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            columns = [x for x in list(TeamStatSchema.dtypes.keys()) if x in team_stats.columns]
            team_stats = TeamStatSchema.validate(team_stats[columns])

            team_stats = (
                team_stats.replace(np.nan, 0).replace(np.inf, 0).replace("nan", 0).replace("", 0).replace(" ", 0)
            )

            team_stats_id = pd.Series(
                data=(
                    team_stats.game_id.astype(str).copy()
                    + "_"
                    + "0"
                    + team_stats.period.astype(str).copy()
                    + "_"
                    + team_stats.score_state
                    + "_"
                    + team_stats.strength_state
                    + "_"
                    + team_stats.team
                    + "_"
                    + team_stats.opp_team
                ),
                index=team_stats.index,
                name="id",
                copy=True,
            )

            team_stats = pd.concat([team_stats_id, team_stats], axis=1)

            column_order = [x for x in team_stats.columns if x != "id"]

            column_order.insert(0, "id")

            team_stats = team_stats[column_order]

            team_stats = team_stats.to_dict(orient="records")

            progress.start_task(progress_task)
            progress_total = len(team_stats)
            progress.update(progress_task, total=progress_total, description=pbar_message, refresh=True)

            with self.requests_session as session:
                for _idx, row in enumerate(team_stats):
                    url = f"{self.token.api_url}/api/{self.token.api_version}/chicken_nhl/team_stats"
                    headers = {"Authorization": self.access_token}

                    response = session.post(url=url, headers=headers, json=row)

                    if response.status_code != 200:
                        if response.status_code == 422:
                            print(response.text)
                            break

                        break

                    progress.update(progress_task, description=pbar_message, advance=1, refresh=True)


# no cover: stop
