"""Tests for behavior that is known to be wrong today.

Each test states what the correct result is and is marked as an expected failure, with the
exception the bug causes. The marks are strict: when a bug is fixed its test passes, pytest
reports that as a failure, and the test moves to test_fixed_bugs.py in the same commit as the
fix. A test that fails with any other exception is reported, so it cannot pass as expected
for the wrong reason.

All of them run on the saved games, with no network access.
"""

import warnings
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl import Game, Scraper, Season, prep_ind, prep_lines, prep_stats, prep_team_stats
from chickenstats.chicken_nhl.identity import identity_columns
from chickenstats.exceptions import InvalidInputError

GAME_ID = 2023020001


def known_bug(reason: str, raises: type[BaseException] | tuple[type[BaseException], ...] = AssertionError):
    """Mark a test as failing today because of a known bug, with the exception that bug causes."""
    return pytest.mark.xfail(strict=True, reason=reason, raises=raises)


# -----------------------------------------------------------------------------
# Other aggregation
# -----------------------------------------------------------------------------


@known_bug("the standalone aggregation functions fail on a pandas frame", raises=AttributeError)
def test_standalone_aggregation_accepts_pandas(fixture_game):
    pytest.importorskip("pandas")

    team_stats = prep_team_stats(fixture_game.play_by_play.to_pandas(), level="game", strength_state=False)

    assert len(team_stats) == 2
