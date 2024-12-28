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
                    + stats.api_id
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

    def check_lines_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading line stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/lines/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description=f"Downloaded lines game IDs",
                completed=True,
                advance=True,
                refresh=True,
            )

        return response.json()

    def upload_lines(
        self, lines: pd.DataFrame, disable_progress_bar: bool = False
    ) -> None:
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = f"Uploading chicken_nhl line stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            lines = (
                lines.replace(np.nan, None)
                .replace("nan", None)
                .replace("", None)
                .replace(" ", None)
            )

            lines.own_goalie_api_id = np.where(
                lines.own_goalie_api_id == "EMPTY",
                None,
                lines.own_goalie_api_id,
            )

            lines.opp_goalie_api_id = np.where(
                lines.opp_goalie_api_id == "EMPTY",
                None,
                lines.opp_goalie_api_id,
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
            progress.update(
                progress_task,
                total=progress_total,
                description=pbar_message,
                refresh=True,
            )

            with self.requests_session as session:
                for idx, row in enumerate(lines):
                    url = f"{api_url}/api/v1/chicken_nhl/lines"
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

    def check_team_stats_game_ids(
        self,
        season: list[str | int] | None = None,
        sessions: list[str] | None = None,
        disable_progress_bar: bool = True,
    ):
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgressIndeterminate(disable=disable_progress_bar) as progress:
            pbar_message = f"Downloading team stats game IDs..."
            progress_task = progress.add_task(pbar_message, total=None, refresh=True)

            progress.start_task(progress_task)
            progress.update(
                progress_task, total=1, description=pbar_message, refresh=True
            )

            with self.requests_session as session:
                url = f"{api_url}/api/v1/chicken_nhl/team_stats/game_ids"
                headers = {"Authorization": self.access_token}
                params = {"season": season, "sessions": sessions}

                response = session.get(url=url, params=params, headers=headers)

            progress.update(
                progress_task,
                description=f"Downloaded team stats game IDs",
                completed=True,
                advance=True,
                refresh=True,
            )

        return response.json()

    def upload_team_stats(
        self, team_stats: pd.DataFrame, disable_progress_bar: bool = False
    ) -> None:
        """Docstring."""
        api_url = self.token.api_url

        with ChickenProgress(disable=disable_progress_bar) as progress:
            pbar_message = f"Uploading chicken_nhl team stats data..."
            progress_task = progress.add_task(pbar_message, total=None)

            team_stats = (
                team_stats.replace(np.nan, None)
                .replace("nan", None)
                .replace("", None)
                .replace(" ", None)
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
            progress.update(
                progress_task,
                total=progress_total,
                description=pbar_message,
                refresh=True,
            )

            with self.requests_session as session:
                for idx, row in enumerate(team_stats):
                    url = f"{api_url}/api/v1/chicken_nhl/team_stats"
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
