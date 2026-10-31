"""What a failed HTML report must do: record the game as failed, warn, and come back on a retry.

Each report the scraper fetches for a game (play-by-play PL, the two shift reports TH and TV, and the
rosters RO) is failed four ways through the shared network guard: a connection error, a 404, a 500, and
a report cut off before its end.
Each must record the game in failed_games with a warning that names the report, and Scraper.refresh must
recover it once the report can be read.
"""

import json
import logging
import warnings
from unittest.mock import patch

import pytest
import requests

from chickenstats.chicken_nhl import Game, Scraper

GAME_ID = 2023020001
REPORTS = ["PL", "TH", "TV", "RO"]
FAILURES = ["connection error", 404, 500, "cut off"]


def failing(report: str, failure: str | int):
    """A Session.get that fails one report of the saved game and serves every other request."""
    served_get = requests.Session.get

    def get(self, url, *args, **kwargs):
        if f"/{report}020001.HTM" in str(url):
            if failure == "connection error":
                raise requests.exceptions.ConnectionError("down")
            if failure == "cut off":
                response = served_get(self, url, *args, **kwargs)
                response._content = response.content[: int(len(response.content) * 0.6)]
                return response
            response = requests.Response()
            response.status_code = int(failure)
            response._content = b""
            response.url = str(url)
            return response
        return served_get(self, url, *args, **kwargs)

    return get


def scrape_with_a_failed_report(caplog, report: str, failure: str | int):
    """Scrape the saved game with one report failing, and return the Scraper, its play-by-play and the warnings."""
    with patch.object(requests.Session, "get", failing(report, failure)), warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with caplog.at_level(logging.WARNING, logger="chickenstats"):
            scraper = Scraper([GAME_ID], disable_progress_bar=True)
            play_by_play = scraper.play_by_play

    return scraper, play_by_play, list(w) + list(caplog.records)


@pytest.mark.parametrize("failure", FAILURES)
@pytest.mark.parametrize("report", REPORTS)
def test_a_failed_report_fails_the_game(caplog, report, failure):
    """A finished game with a report that cannot be read is recorded as failed, with a warning, not returned partial."""
    scraper, play_by_play, warned = scrape_with_a_failed_report(caplog, report, failure)

    assert scraper.failed_games == [GAME_ID]
    assert play_by_play.height == 0
    assert any(report in str(getattr(record, "message", record)) for record in warned)


@pytest.mark.parametrize("failure", FAILURES)
@pytest.mark.parametrize("report", REPORTS)
def test_a_retry_recovers_a_failed_game(caplog, report, failure):
    """Once the report can be read, refresh() fetches the game again and it leaves failed_games."""
    scraper, _, _ = scrape_with_a_failed_report(caplog, report, failure)

    scraper.refresh([GAME_ID])

    assert scraper.failed_games == []
    assert scraper.play_by_play.height == 781


def test_a_failed_report_only_warns_before_the_game_is_official(caplog):
    """At FINAL a report can still be posted, so the game is returned and fetched again rather than failed."""
    served_get = failing("PL", 404)

    def final(self, url, *args, **kwargs):
        response = served_get(self, url, *args, **kwargs)
        if "gamecenter/2023020001/play-by-play" in str(url):
            payload = response.json()
            payload["gameState"] = "FINAL"
            response._content = json.dumps(payload).encode()
        return response

    with patch.object(requests.Session, "get", final), caplog.at_level(logging.WARNING, logger="chickenstats"):
        html_events = Game(GAME_ID).html_events
        scraper = Scraper([GAME_ID], disable_progress_bar=True)
        _ = scraper.html_events

    assert html_events == []
    assert any("PL" in record.getMessage() and "FINAL" in record.getMessage() for record in caplog.records)
    assert scraper.failed_games == []
    assert not scraper._is_final(GAME_ID)


def test_a_finished_game_whose_events_stop_before_the_game_end_fails(caplog):
    """An events report with status 200 that has no game end row stopped early, so the game is not complete."""
    served_get = requests.Session.get

    def without_game_end(self, url, *args, **kwargs):
        response = served_get(self, url, *args, **kwargs)
        if "/PL020001.HTM" in str(url):
            html = response.content.decode("utf-8")
            start = html.rfind("<tr", 0, html.find(">GEND<"))
            end = html.find("</tr>", start) + len("</tr>")
            response._content = (html[:start] + html[end:]).encode()
        return response

    with patch.object(requests.Session, "get", without_game_end), warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with caplog.at_level(logging.WARNING, logger="chickenstats"):
            scraper = Scraper([GAME_ID], disable_progress_bar=True)
            _ = scraper.play_by_play

    assert scraper.failed_games == [GAME_ID]
    assert any("no game end" in record.getMessage() for record in caplog.records)


def test_a_defect_in_the_play_by_play_pipeline_reaches_the_error_log(caplog):
    """A bug while building play-by-play is not relabeled as a data mismatch: it is logged as an unexpected error."""
    from chickenstats.chicken_nhl import Game
    from chickenstats.chicken_nhl._game_pbp import _GamePBPMixin

    def broken(self, merged_events, actives):
        raise ZeroDivisionError("a defect")

    with patch.object(_GamePBPMixin, "_track_pbp_state", broken):
        with pytest.raises(ZeroDivisionError):
            _ = Game(GAME_ID).play_by_play

        with warnings.catch_warnings(), caplog.at_level(logging.ERROR, logger="chickenstats"):
            warnings.simplefilter("ignore")
            scraper = Scraper([GAME_ID], disable_progress_bar=True)
            _ = scraper.play_by_play

    assert scraper.failed_games == [GAME_ID]
    assert any("Unexpected error" in record.getMessage() for record in caplog.records)


def test_a_refresh_that_fails_again_keeps_the_earlier_rows(caplog):
    """A game whose report fails on refresh keeps the rows it had, and is listed as failed."""
    scraper = Scraper([GAME_ID], disable_progress_bar=True)
    before = scraper.play_by_play

    with patch.object(requests.Session, "get", failing("PL", 500)), pytest.warns(UserWarning, match="Failed"):
        scraper.refresh([GAME_ID])

    assert scraper.failed_games == [GAME_ID]
    assert scraper.play_by_play.equals(before)


def test_refresh_with_no_games_fetches_only_those_not_final(caplog):
    """refresh() fetches failed and provisional games, and leaves a final game alone."""
    with patch.object(requests.Session, "get", failing("PL", 404)), pytest.warns(UserWarning):
        scraper = Scraper([GAME_ID, 2023020015], disable_progress_bar=True)
        _ = scraper.play_by_play
    assert scraper.failed_games == [GAME_ID]

    served_get = requests.Session.get
    requested: list[str] = []

    def recording_get(self, url, *args, **kwargs):
        requested.append(str(url))
        return served_get(self, url, *args, **kwargs)

    with patch.object(requests.Session, "get", recording_get):
        scraper.refresh()

    assert scraper.failed_games == []
    assert requested and not any("2023020015" in url or "020015.HTM" in url for url in requested)
    assert scraper.play_by_play["game_id"].unique().sort().to_list() == [GAME_ID, 2023020015]


def test_refresh_rejects_a_game_not_in_the_scraper():
    from chickenstats.exceptions import InvalidInputError

    scraper = Scraper([GAME_ID], disable_progress_bar=True)

    with pytest.raises(InvalidInputError, match="not in this Scraper"):
        scraper.refresh([2023020015])


def test_a_failed_api_request_is_not_repeated():
    """A Game raises its failed API request again instead of retrying it on the next property (N66)."""
    from chickenstats.chicken_nhl import Game

    calls = []

    def api_down(self, url, *args, **kwargs):
        calls.append(str(url))
        raise requests.exceptions.ConnectionError("down")

    game = Game(GAME_ID)
    with patch.object(requests.Session, "get", api_down):
        for _ in range(2):
            with pytest.raises(requests.exceptions.ConnectionError):
                game._fetch_api_data()

    assert len(calls) == 1


def test_a_game_the_api_does_not_have_fails_without_counting_as_an_outage():
    """A 404 from the API is a bad game ID, so a range past the last game fails each game, not the scrape (bA-03)."""

    def not_found(self, url, *args, **kwargs):
        calls.append(str(url))
        response = requests.Response()
        response.status_code = 404
        response._content = b"<html>Not Found</html>"
        response.url = str(url)
        return response

    calls: list[str] = []
    game_ids: list[str | float | int] = list(range(2023029990, 2023029997))
    scraper = Scraper(game_ids, disable_progress_bar=True)
    with patch.object(requests.Session, "get", not_found), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        play_by_play = scraper.play_by_play

    assert play_by_play.height == 0
    assert scraper.failed_games == game_ids
    assert sum("api-web" in url for url in calls) == len(game_ids)


def test_a_scrape_stops_after_five_games_fail_on_the_network():
    """When every request fails, the Scraper stops after five games with a clear error (N66)."""
    from chickenstats.exceptions import NHLUnavailableError

    def network_down(self, url, *args, **kwargs):
        raise requests.exceptions.ConnectionError("down")

    game_ids: list[str | float | int] = list(range(2023020001, 2023020008))
    scraper = Scraper(game_ids, disable_progress_bar=True)
    with patch.object(requests.Session, "get", network_down), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(NHLUnavailableError, match="last 5 games failed with network errors") as raised:
            _ = scraper.play_by_play

    assert raised.value.game_ids == game_ids[:5]
    assert scraper.failed_games == game_ids[:5]


def test_a_game_that_fails_on_its_data_resets_the_count():
    """Only games failing in a row on the network stop the scrape; a data failure in between does not."""
    from chickenstats.chicken_nhl import _scraper_core
    from chickenstats.exceptions import DataMismatchError

    def every_fourth_on_its_data(self, game_id, scrape_types):
        return requests.exceptions.ConnectionError("down") if game_id % 4 else DataMismatchError("bad data")

    with patch.object(_scraper_core._ScraperCore, "_scrape_single_game", every_fourth_on_its_data):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            scraper = Scraper(list(range(2023020001, 2023020013)), disable_progress_bar=True)
            _ = scraper.play_by_play

    assert len(scraper.failed_games) == 12
