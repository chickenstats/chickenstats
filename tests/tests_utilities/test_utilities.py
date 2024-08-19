from requests import Session
from requests.adapters import HTTPAdapter

from chickenstats.utilities.utilities import (
    ChickenProgress,
    ChickenSession,
    ChickenHTTPAdapter,
)

from rich.progress import Progress


def test_ChickenProgress():
    progress = ChickenProgress()

    assert isinstance(progress, Progress) is True


def test_ChickenSession():
    session = ChickenSession()

    assert isinstance(session, Session) is True


def test_ChickenHTTPAdapter():
    adapter = ChickenHTTPAdapter()

    assert isinstance(adapter, HTTPAdapter) is True
