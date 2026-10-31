import gzip
import json
import os
from unittest.mock import patch

import pytest
import requests
from requests.adapters import HTTPAdapter

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import pyarrow  # noqa: F401

    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

try:
    import matplotlib  # noqa: F401

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from PIL import Image  # noqa: F401

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

requires_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
requires_pyarrow = pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
requires_matplotlib = pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
requires_pil = pytest.mark.skipif(not HAS_PIL, reason="pillow not installed")


# -----------------------------------------------------------------------------
# Network guard
# -----------------------------------------------------------------------------

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__), "tests_chicken_nhl", "mock_data")
FIXTURE_GAME_ID = 2023020001
REPORT_FILES = {"PL": "events.html", "RO": "rosters.html", "TH": "shifts_home.html", "TV": "shifts_away.html"}
SAVED_DIR = os.path.join(MOCK_DATA_DIR, "saved")

# Tests with one of these markers are allowed to reach the network
NETWORK_MARKERS = ("nhl", "live")

_network = {"allowed": False}
_blocked_urls: list[str] = []
_saved_urls: dict[str, str] = {}
_real_send = HTTPAdapter.send
_real_get = requests.Session.get


def _saved_index() -> dict[str, str]:
    """Map each saved URL to its file under mock_data/saved (see scripts/capture_test_fixture.py)."""
    if not _saved_urls:
        with open(os.path.join(SAVED_DIR, "index.json")) as f:
            _saved_urls.update(json.load(f))

    return _saved_urls


def saved_response(url: str, params: dict | None = None) -> requests.Response | None:
    """Return the saved NHL response for a URL, or None when nothing is saved for it."""
    full_url = str(requests.Request("GET", url, params=params).prepare().url)
    content = filename = None

    if full_url in _saved_index():
        with gzip.open(os.path.join(SAVED_DIR, _saved_index()[full_url]), "rb") as f:
            content = f.read()

    # Game 2023020001 predates the saved folder and is kept as plain files
    elif f"gamecenter/{FIXTURE_GAME_ID}/play-by-play" in url:
        filename = "play_by_play.json"
    else:
        for report, report_file in REPORT_FILES.items():
            if f"/{report}{str(FIXTURE_GAME_ID)[4:]}.HTM" in url:
                filename = report_file

    if content is None:
        if filename is None:
            return None
        with open(os.path.join(MOCK_DATA_DIR, filename), "rb") as f:
            content = f.read()

    response = requests.Response()
    response.url = full_url
    response.status_code = 200
    response._content = content

    return response


def _guarded_get(self, url, *args, **kwargs):
    """Serve a saved response from disk; pass every other request on."""
    if not _network["allowed"]:
        response = saved_response(str(url), kwargs.get("params"))
        if response is not None:
            return response

    return _real_get(self, url, *args, **kwargs)


def _guarded_send(self, request, *args, **kwargs):
    """Refuse a request that reaches the network, and remember it so the test fails."""
    if _network["allowed"]:
        return _real_send(self, request, *args, **kwargs)

    _blocked_urls.append(request.url)
    raise requests.exceptions.ConnectionError(f"network access is blocked in tests: {request.url}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Set whether the test about to run may reach the network, before its fixtures are built."""
    _network["allowed"] = any(item.get_closest_marker(marker) for marker in NETWORK_MARKERS)
    _blocked_urls.clear()
    yield


@pytest.fixture(scope="session", autouse=True)
def _network_guard():
    """Install the guard for the whole session."""
    with patch.object(requests.Session, "get", _guarded_get), patch.object(HTTPAdapter, "send", _guarded_send):
        yield


@pytest.fixture(autouse=True)
def _fail_on_network_access():
    """Fail a test that tried to reach the network without being marked for it."""
    yield
    if _blocked_urls:
        urls = sorted(set(_blocked_urls))
        pytest.fail(
            f"the test tried to reach the network ({len(urls)} URL(s), first: {urls[0]}). "
            "Use the saved game 2023020001, or mark the test with pytest.mark.nhl.",
            pytrace=False,
        )
