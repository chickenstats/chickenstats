import os
import requests


class ChickenToken:
    """Docstring."""

    def __init__(self,
                 api_url: str | None = None,
                 username: str | None = None,
                 password: str | None = None):
        """Docstring."""

        self.username = username
        self.password = password
        self.api_url = api_url

        if not username:
            self.username = os.environ.get("API_USERNAME")

        if not password:
            self.password = os.environ.get("API_PASSWORD")

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
