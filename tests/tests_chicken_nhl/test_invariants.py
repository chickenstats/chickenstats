"""The invariant battery, run over every saved game, and over the regression games under the nhl marker."""

import pytest

from conftest import scrape_saved_game
from invariants import INVARIANTS, REGRESSION_GAME_IDS

SAVED_GAMES = [
    "fixture_game",
    "shootout_game",
    "long_shootout_game",
    "playoff_overtime_game",
    "second_nashville_game",
    "old_regular_season_game",
    "old_playoff_game",
]


@pytest.mark.parametrize("check", INVARIANTS, ids=lambda check: check.__name__)
@pytest.mark.parametrize("fixture", SAVED_GAMES)
def test_saved_games_pass_every_invariant(request, fixture, check):
    check(request.getfixturevalue(fixture))


@pytest.mark.parametrize("check", INVARIANTS, ids=lambda check: check.__name__)
def test_all_saved_games_together_pass_every_invariant(all_saved_games, check):
    check(all_saved_games)


@pytest.mark.nhl
@pytest.mark.regression
@pytest.mark.parametrize("game_id", REGRESSION_GAME_IDS)
def test_regression_games_pass_every_invariant(game_id):
    game = scrape_saved_game(game_id)
    for check in INVARIANTS:
        check(game)
