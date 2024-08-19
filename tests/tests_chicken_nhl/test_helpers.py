import pytest

import pandas as pd
import numpy as np

from chickenstats.chicken_nhl.helpers import (
    convert_to_list,
    return_name_html,
    norm_coords
)

from pathlib import Path


@pytest.fixture(scope="package")
def raw_pbp():
    filepath = Path("./tests/tests_chickenstats/data/raw_pbp.csv")

    raw_pbp = pd.read_csv(filepath, low_memory=False)

    return raw_pbp


def test_norm_coords(raw_pbp, norm_team="NSH"):
    data = norm_coords(data=raw_pbp, norm_team=norm_team)

    if "norm_coords_x" in data.columns and "norm_coords_y" in data.columns:
        assert True

    else:
        assert False


@pytest.mark.parametrize(
    "test_list",
    [
        2023020001,
        2023020001.0,
        "2023020001",
        (2023020001, 2023020002),
        pd.Series([2023020001]),
        np.array([2023020001]),
    ],
)
def test_convert_to_list(test_list):
    test_list = convert_to_list(test_list, "GAME ID")

    assert isinstance(test_list, list) is True


def test_convert_to_list_fail():
    with pytest.raises(Exception):
        convert_to_list({"test_key": "test_value"}, "TEST")


def test_return_name_html():
    name = return_name_html("GOALIE - PEKKA RINNE")

    assert isinstance(name, str) is True
