"""Tests that chickenstats errors still match the errors they replace."""

import pickle
from unittest.mock import patch

import pandera.errors
import pandera.polars as pa_pl
import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl import Game, Player, Season, Team, search_players
from chickenstats.chicken_nhl._validation_utils import coerce_to_schema, validate_dataframe
from chickenstats.chicken_nhl.contract import assert_chronological, assert_unique_events
from chickenstats.exceptions import ChickenstatsError, InvalidInputError, NetworkError, SchemaValidationError


@pytest.mark.parametrize(
    ("error", "replaced"),
    [
        (NetworkError, requests.HTTPError),
        (SchemaValidationError, pandera.errors.SchemaError),
        (InvalidInputError, ValueError),
    ],
)
def test_each_error_is_also_the_error_it_replaces(error, replaced):
    assert issubclass(error, ChickenstatsError)
    assert issubclass(error, replaced)


def _error_status(status: int):
    """A Session.get that answers every request with an empty response of this status."""

    def get(self, url, *args, **kwargs):
        response = requests.Response()
        response.status_code, response.url, response._content = status, str(url), b""
        response.request = requests.Request("GET", str(url)).prepare()
        return response

    return get


_CALLS = {
    "schedule": lambda: Season(2023).schedule("NSH", disable_progress_bar=True),
    "standings": lambda: Season(2023).standings,
    "search_players": lambda: search_players("mcdavid"),
    "landing": lambda: Player(8478402)._landing_info,
    "game_logs": lambda: Player(8478402)._current_game_logs,
    "logo": lambda: Team(team_code="NSH").logo,
}


@pytest.mark.parametrize(
    ("call", "status"),
    [pytest.param(call, status, id=f"{name}-{status}") for name, call in _CALLS.items() for status in (404, 500)]
    # A 404 for a game means no such game, so it raises InvalidGameIDError instead
    + [pytest.param(lambda: Game(2023020001).play_by_play, 500, id="game-500")],
)
def test_an_error_status_raises_network_error(call, status):
    with patch.object(requests.Session, "get", _error_status(status)):
        with pytest.raises(NetworkError) as info:
            call()

    error = info.value
    assert isinstance(error.__cause__, requests.HTTPError)
    assert error.response is not None and error.response.status_code == status
    assert error.request is error.response.request
    assert str(status) in str(error)


def test_except_http_error_still_catches_network_error():
    caught = None
    with patch.object(requests.Session, "get", _error_status(500)):
        try:
            _ = Team(team_code="NSH").logo
        except requests.HTTPError as exc:
            caught = exc

    assert isinstance(caught, NetworkError)


def _schema():
    return pa_pl.DataFrameSchema({"count": pa_pl.Column(pl.Int64, nullable=False)}, coerce=True)


@pytest.mark.parametrize("validate", [validate_dataframe, coerce_to_schema])
def test_a_failed_schema_raises_schema_validation_error(validate):
    with pytest.raises(pandera.errors.SchemaError) as info:
        validate(pl.DataFrame({"count": [1, None]}), _schema())

    error = info.value
    assert isinstance(error, SchemaValidationError)
    assert isinstance(error.__cause__, pandera.errors.SchemaError)
    assert str(error) == str(error.__cause__)
    for name in ("schema", "data", "failure_cases", "check", "reason_code", "column_name"):
        assert getattr(error, name) is getattr(error.__cause__, name)


def test_schema_validation_error_survives_pickling():
    with pytest.raises(SchemaValidationError) as info:
        validate_dataframe(pl.DataFrame({"count": [1, None]}), _schema())

    with pytest.warns(UserWarning):
        restored = pickle.loads(pickle.dumps(info.value))

    assert isinstance(restored, SchemaValidationError)
    assert str(restored) == str(info.value)


def test_contract_checks_raise_invalid_input_error():
    backward = pl.DataFrame(
        {"season": [20232024, 20222023], "game_date": ["2023-10-10", "2022-10-10"], "game_id": [1, 2]}
    )
    repeated = pl.DataFrame({"game_id": [1, 1], "event_idx": [1, 1]})

    with pytest.raises(ValueError) as info:
        assert_chronological(backward, what="rows")
    assert isinstance(info.value, InvalidInputError)

    with pytest.raises(InvalidInputError):
        assert_unique_events(repeated, what="rows")
