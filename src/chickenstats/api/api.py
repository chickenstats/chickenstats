import os

import pandas as pd
import numpy as np

from chickenstats.utilities import (
    ChickenProgress,
    ChickenProgressIndeterminate,
    ChickenSession,
)


class ChickenToken:
    """Docstring."""

    def __init__(
        self,
        api_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        session: ChickenSession | None = None,
    ):
        """Docstring."""
        self.username = username
        self.password = password
        self.api_url = api_url

        if not username:
            self.username = os.environ.get("CHICKENSTATS_USERNAME")

        if not password:
            self.password = os.environ.get("CHICKENSTATS_PASSWORD")

        if not api_url:
            self.api_url = "https://api.chickenstats.com"

        self.token_url = f"{self.api_url}/api/v1/login/access-token"

        self.response = None
        self.access_token = None

        if not session:
            self.requests_session = ChickenSession()

        else:
            self.requests_session = session

        if not self.access_token:
            self.get_token()

    def get_token(self) -> str:
        """Docstring."""
        data = {"username": self.username, "password": self.password}

        with self.requests_session as session:
            self.response = session.post(self.token_url, data=data).json()

        self.access_token = f"Bearer {self.response['access_token']}"

        return self.access_token


class ChickenUser:
    """Docstring."""

    def __init__(
        self,
        api_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        session: ChickenSession | None = None,
    ):
        """Docstring."""
        self.username = username

        if not username:
            self.username = os.environ.get("CHICKENSTATS_USERNAME")

        self.password = password

        if not password:
            self.password = os.environ.get("CHICKENSTATS_PASSWORD")

        self.api_url = api_url

        if not api_url:
            self.api_url = "https://api.chickenstats.com"

        self.token = ChickenToken(self.api_url, self.username, self.password)
        self.access_token = self.token.access_token

        if not session:
            self.requests_session = ChickenSession()
        else:
            self.requests_session = session

    def reset_password(self, new_password: str):
        """Reset password in-place."""
        headers = {"Authorization": self.access_token}
        url = f"{self.api_url}/api/v1/reset-password/"

        data = {
            "token": self.access_token.replace("Bearer ", ""),
            "new_password": new_password,
        }

        with self.requests_session as session:
            response = session.post(url=url, json=data, headers=headers)

        return response


class ChickenStats:
    """Docstring."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        api_url: str | None = None,
        session: ChickenSession | None = None,
    ):
        """Docstring."""
        self.user = ChickenUser(api_url, username, password)
        self.token = self.user.token
        self.access_token = self.user.access_token

        if not session:
            self.requests_session = ChickenSession()

        else:
            self.requests_session = session

    def upload_pbp(self, pbp: pd.DataFrame, disable_progress_bar: bool = False) -> None:
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = f"Uploading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None)

            pbp = (
                pbp.replace(np.nan, None)
                .replace("nan", None)
                .replace("", None)
                .replace(" ", None)
            )

            pbp = pbp.to_dict(orient="records")

            progress.start_task(progress_task)
            progress_total = len(pbp)
            progress.update(
                progress_task,
                total=progress_total,
                description=pbar_message,
                refresh=True,
            )

            with self.requests_session as session:
                for idx, row in enumerate(pbp):
                    url = f"{api_url}/api/v1/chicken_nhl/play_by_play"
                    headers = {"Authorization": self.access_token}

                    response = session.post(url=url, headers=headers, json=row)

                    if response.status_code != 200:
                        if response.status_code == 422:
                            print(response.text)
                            break

                        break

                    progress.update(
                        progress_task, description=pbar_message, advance=1, refresh=True
                    )

    def upload_stats(
        self, stats: pd.DataFrame, disable_progress_bar: bool = False
    ) -> None:
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = f"Uploading chicken_nhl stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            stats = (
                stats.replace(np.nan, None)
                .replace("nan", None)
                .replace("", None)
                .replace(" ", None)
            )

            group_list = [
                "game_id",
                "period",
                "score_state",
                "strength_state",
                "forwards_eh_id",
            ]
            forward_cumcount = (
                stats.groupby(group_list).ngroup().astype(str).str.zfill(2).copy()
            )

            group_list = [
                "game_id",
                "period",
                "score_state",
                "strength_state",
                "defense_eh_id",
            ]
            defense_cumcount = (
                stats.groupby(group_list).ngroup().astype(str).str.zfill(2).copy()
            )

            group_list = [
                "game_id",
                "period",
                "score_state",
                "strength_state",
                "own_goalie_eh_id",
            ]
            own_goalie_cumcount = (
                stats.groupby(group_list).ngroup().astype(str).str.zfill(2).copy()
            )

            group_list = [
                "game_id",
                "period",
                "score_state",
                "strength_state",
                "opp_forwards_eh_id",
            ]
            opp_forward_cumcount = (
                stats.groupby(group_list).ngroup().astype(str).str.zfill(2).copy()
            )

            group_list = [
                "game_id",
                "period",
                "score_state",
                "strength_state",
                "opp_defense_eh_id",
            ]
            opp_defense_cumcount = (
                stats.groupby(group_list).ngroup().astype(str).str.zfill(2).copy()
            )

            group_list = [
                "game_id",
                "period",
                "score_state",
                "strength_state",
                "opp_goalie_eh_id",
            ]
            opp_goalie_cumcount = (
                stats.groupby(group_list).ngroup().astype(str).str.zfill(2).copy()
            )

            stats_id = pd.Series(
                data=(
                    stats.api_id.astype(str).copy()
                    + "_"
                    + stats.game_id.astype(str).copy()
                    + "_"
                    + "0"
                    + stats.period.astype(str).copy()
                    + "_"
                    + stats.score_state
                    + "_"
                    + stats.strength_state
                    + "_"
                    + forward_cumcount
                    + "_"
                    + defense_cumcount
                    + "_"
                    + own_goalie_cumcount
                    + "_"
                    + opp_forward_cumcount
                    + "_"
                    + opp_defense_cumcount
                    + "_"
                    + opp_goalie_cumcount
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
            progress.update(
                progress_task,
                total=progress_total,
                description=pbar_message,
                refresh=True,
            )

            with self.requests_session as session:
                for idx, row in enumerate(stats):
                    url = f"{api_url}/api/v1/chicken_nhl/stats"
                    headers = {"Authorization": self.access_token}

                    response = session.post(url=url, headers=headers, json=row)

                    if response.status_code != 200:
                        if response.status_code == 422:
                            print(response.text)
                            break

                        break

                    progress.update(
                        progress_task, description=pbar_message, advance=1, refresh=True
                    )

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
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading chicken_nhl play-by-play data..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/play_by_play"
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
                description=f"Downloaded chicken_nhl play-by-play data",
                completed=True,
                advance=True,
                refresh=True,
            )

        return pd.json_normalize(response.json())

    def check_pbp_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading play-by-play game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/play_by_play/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description=f"Downloaded play-by-play game IDs",
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
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading play-by-play play IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/play_by_play/play_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions, "game_id": game_id}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description=pbar_message,
                completed=True,
                advance=True,
                refresh=True,
            )

        return response.json()

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
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading chicken_nhl game stats data..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/stats/game"
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
                description=f"Downloaded chicken_nhl game stats data",
                completed=True,
                advance=True,
                refresh=True,
            )

        return pd.json_normalize(response.json()).dropna(how="all", axis=1)

    def check_stats_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/stats/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description=f"Downloaded stats game IDs",
                completed=True,
                advance=True,
                refresh=True,
            )

        return response.json()
