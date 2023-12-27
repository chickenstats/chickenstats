import requests

import pytest

import pandas as pd
import numpy as np

from chickenstats.chickenstats.chicken_nhl.helpers import s_session, convert_to_list


def test_s_session():
    session = s_session()

    assert isinstance(session, requests.Session) is True


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
