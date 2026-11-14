"""Save NHL responses so tests can replay them with the network blocked.

Each command runs the package against the live NHL and records every response it
downloads under tests/tests_chicken_nhl/mock_data/saved/, gzipped and byte-for-byte as
received. index.json maps each URL to its file; tests/conftest.py serves them from there.

    uv run python scripts/capture_test_fixture.py game 2023020125
    uv run python scripts/capture_test_fixture.py boxscore 2023020125
    uv run python scripts/capture_test_fixture.py schedule NSH 2023
    uv run python scripts/capture_test_fixture.py standings 2023
    uv run python scripts/capture_test_fixture.py player 8476887
    uv run python scripts/capture_test_fixture.py search forsberg
"""

import gzip
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import requests

from chickenstats.chicken_nhl import Player, Scraper, Season, search_players

SAVED_DIR = Path(__file__).resolve().parents[1] / "tests" / "tests_chicken_nhl" / "mock_data" / "saved"
INDEX_PATH = SAVED_DIR / "index.json"

_real_get = requests.Session.get


def full_url(url: str, params: dict | None = None) -> str:
    """Return the URL with its query string, the form the index is keyed on."""
    return str(requests.Request("GET", url, params=params).prepare().url)


def file_name(url: str) -> str:
    """Build a readable file name from a URL, e.g. gamecenter_2023020125_play-by-play.gz."""
    path = re.sub(r"^https?://[^/]+/", "", url)
    path = re.sub(r"^(v1|api/v1|scores)/", "", path)
    return re.sub(r"[^A-Za-z0-9.-]+", "_", path).strip("_") + ".gz"


def record(run) -> list[str]:
    """Call run() and save every response it downloads; return the URLs saved."""
    SAVED_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX_PATH.read_text()) if INDEX_PATH.exists() else {}
    saved = []

    def recording_get(self, url, *args, **kwargs):
        response = _real_get(self, url, *args, **kwargs)
        if response.status_code == 200:
            key = full_url(str(url), kwargs.get("params"))
            name = file_name(key)
            (SAVED_DIR / name).write_bytes(gzip.compress(response.content, mtime=0))
            index[key] = name
            saved.append(key)
        return response

    with patch.object(requests.Session, "get", recording_get):
        run()

    INDEX_PATH.write_text(json.dumps(dict(sorted(index.items())), indent=2) + "\n")

    return saved


def main(argv: list[str]) -> int:
    """Run one capture command."""
    match argv:
        case ["game", game_id]:
            saved = record(lambda: Scraper([int(game_id)], disable_progress_bar=True).play_by_play)
        case ["boxscore", game_id]:
            url = f"https://api-web.nhle.com/v1/gamecenter/{int(game_id)}/boxscore"
            saved = record(lambda: requests.Session().get(url, timeout=30))
        case ["schedule", team, year]:
            saved = record(lambda: Season(int(year)).schedule(team))
        case ["standings", year]:
            saved = record(lambda: Season(int(year)).standings)
        case ["player", player_id]:

            def run_player():
                player = Player(player_id=int(player_id))
                player.prefetch()
                _ = player.player_info
                _ = player._game_logs

            saved = record(run_player)
        case ["search", query]:
            saved = record(lambda: search_players(query))
        case _:
            print(__doc__)
            return 2

    for url in saved:
        print(url)
    print(f"{len(saved)} response(s) saved under {SAVED_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
