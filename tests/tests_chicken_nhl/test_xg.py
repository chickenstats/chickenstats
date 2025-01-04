import pandas as pd

from pathlib import Path

from chickenstats.chicken_nhl.xg import prep_data
import pytest


@pytest.fixture(scope="package")
def raw_pbp():
    filepath = Path("./tests/tests_chicken_nhl/data/test_pbp.csv")

    raw_pbp = pd.read_csv(filepath, low_memory=False)

    return raw_pbp


@pytest.mark.parametrize(
    "strengths", ["even", "powerplay", "shorthanded", "empty_for", "empty_against"]
)
def test_prep_data(strengths, raw_pbp):
    """Tests the xG prep data function."""

    df = prep_data(data=raw_pbp, strengths=strengths)

    assert isinstance(df, pd.DataFrame) is True
