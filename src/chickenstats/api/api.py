import os
import requests


def get_access_token(
    api_url: str | None = None, username: str | None = None, password: str | None = None
) -> str:
    """Docstring."""
    if not username:
        username = os.environ.get("API_USERNAME")

    if not password:
        password = os.environ.get("API_PASSWORD")

    if not api_url:
        token_url = "http://localhost/api/v1/login/access-token"
    else:
        token_url = f"{api_url}/api/v1/login/access-token"

    data = {"username": username, "password": password}

    response = requests.post(token_url, data=data).json()

    access_token = f"Bearer {response["access_token"]}"

    return access_token
