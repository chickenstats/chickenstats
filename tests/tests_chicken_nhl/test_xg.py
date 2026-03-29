from pathlib import Path

import pandas as pd
import polars as pl
import pytest

from chickenstats.chicken_nhl.xg import prep_data_pandas, prep_data_polars


@pytest.fixture(scope="package")
def raw_pbp():
    filepath = Path("./tests/tests_chicken_nhl/data/test_pbp.csv")

    raw_pbp = pd.read_csv(filepath, low_memory=False)

    return raw_pbp


@pytest.fixture(scope="package")
def raw_pbp_polars():
    filepath = Path("./tests/tests_chicken_nhl/data/test_pbp.csv")

    return pl.read_csv(filepath, infer_schema_length=10000)


@pytest.mark.parametrize("strengths", ["even", "powerplay", "shorthanded", "empty_for", "empty_against"])
def test_prep_data_pandas(strengths, raw_pbp):
    """Tests the xG prep data function."""

    df = prep_data_pandas(data=raw_pbp, strengths=strengths)

    assert isinstance(df, pd.DataFrame) is True


@pytest.mark.parametrize("strengths", ["even", "powerplay", "shorthanded", "empty_for", "empty_against"])
def test_prep_data_polars(strengths, raw_pbp_polars):
    """Tests the polars xG prep data function."""

    df = prep_data_polars(df=raw_pbp_polars, strengths=strengths)

    assert isinstance(df, pl.DataFrame)
    assert len(df) > 0
