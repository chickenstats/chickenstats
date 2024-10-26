import os
import requests


class ChickenToken:
    """Docstring."""

    def __init__(
        self,
        api_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
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

        if not self.access_token:
            self.get_token()

    def get_token(self) -> str:
        """Docstring."""
        data = {"username": self.username, "password": self.password}

        self.response = requests.post(self.token_url, data=data).json()

        self.access_token = f"Bearer {self.response["access_token"]}"

        return self.access_token


class ChickenUser:
    """Docstring."""

    def __init__(
        self,
        api_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
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

    def reset_password(self, new_password: str):
        """Reset password in-place."""
        headers = {"Authorization": self.access_token}
        url = f"{self.api_url}/api/v1/reset-password/"

        data = {
            "token": self.access_token.replace("Bearer ", ""),
            "new_password": new_password,
        }

        response = requests.post(url=url, json=data, headers=headers)

        return response
