from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from chickenstats.chicken_nhl._game_utils import (
    _return_name_html as return_name_html,
    calculate_score_adjustment,
    load_score_adjustments,
)
from chickenstats.chicken_nhl._helpers import convert_to_list
from chickenstats.utilities.utilities import charts_directory, data_directory, norm_coords


@pytest.fixture(scope="package")
def test_pbp():
    filepath = Path("./tests/tests_chicken_nhl/data/test_pbp.csv")

    test_pbp = pd.read_csv(filepath, low_memory=False)

    return test_pbp


def test_norm_coords(test_pbp, norm_column="event_team", norm_value="NSH"):
    data = norm_coords(data=test_pbp, normalization_column=norm_column, normalization_value=norm_value)

    if "norm_coords_x" in data.columns and "norm_coords_y" in data.columns:
        assert True

    else:
        raise AssertionError()


@pytest.mark.parametrize(
    "test_list",
    [2023020001, 2023020001.0, "2023020001", (2023020001, 2023020002), pd.Series([2023020001]), np.array([2023020001])],
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


# ---------------------------------------------------------------------------
# calculate_score_adjustment
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def score_adjustments():
    return load_score_adjustments()


def _base_play(**overrides) -> dict:
    """Minimal play dict with all keys required by calculate_score_adjustment."""
    play = {
        "event": "SHOT",
        "event_team": "NSH",
        "opp_team": "CHI",
        "home_team": "NSH",
        "home_score_diff": 0,
        "strength_state": "5v5",
        "teammate_block": 0,
        "goal": 0,
        "pred_goal": 0.1,
        "shot": 1,
        "miss": 0,
        "block": 0,
        "fenwick": 1,
        "corsi": 1,
    }
    play.update(overrides)
    return play


def test_calculate_score_adjustment_shot_home(score_adjustments):
    """Home team SHOT produces adjusted columns."""
    play = _base_play()
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" in result
    assert result["shot_adj"] > 0


def test_calculate_score_adjustment_block_opponent(score_adjustments):
    """BLOCK with teammate_block=0 uses opp_team as the event_team (line 49 path)."""
    play = _base_play(event="BLOCK", event_team="NSH", opp_team="CHI", teammate_block=0, block=1, corsi=1)
    result = calculate_score_adjustment(play, score_adjustments)
    assert "block_adj" in result


def test_calculate_score_adjustment_block_teammate(score_adjustments):
    """BLOCK with teammate_block=1 uses event_team directly."""
    play = _base_play(event="BLOCK", event_team="NSH", opp_team="CHI", teammate_block=1, block=1, corsi=1)
    result = calculate_score_adjustment(play, score_adjustments)
    assert "block_adj" in result


def test_calculate_score_adjustment_miss(score_adjustments):
    """MISS event still uses fenwick weight column."""
    play = _base_play(event="MISS", shot=0, miss=1, fenwick=1)
    result = calculate_score_adjustment(play, score_adjustments)
    assert "miss_adj" in result


def test_calculate_score_adjustment_score_diff_clamped_low(score_adjustments):
    """home_score_diff below -3 is clamped to -3."""
    play = _base_play(home_score_diff=-5)
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" in result


def test_calculate_score_adjustment_score_diff_clamped_high(score_adjustments):
    """home_score_diff above +3 is clamped to +3."""
    play = _base_play(home_score_diff=5)
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" in result


def test_calculate_score_adjustment_empty_net_no_division(score_adjustments):
    """Strength state with 'E' uses identity weight (multiplied by 1)."""
    play = _base_play(strength_state="5v4E")
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" in result
    assert result["shot_adj"] == play["shot"]


def test_calculate_score_adjustment_disadvantage_flips_home(score_adjustments):
    """Strength state 4v5 swaps is_home before lookup."""
    play = _base_play(event_team="NSH", home_team="NSH", strength_state="4v5")
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" in result


def test_calculate_score_adjustment_non_shot_event_unchanged(score_adjustments):
    """Non-shot events (e.g. FACEOFF) pass through without adding _adj keys."""
    play = _base_play(event="FACEOFF")
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" not in result


# ---------------------------------------------------------------------------
# charts_directory / data_directory
# ---------------------------------------------------------------------------


def test_charts_directory_creates_folder(tmp_path):
    charts_directory(target_path=tmp_path)
    assert (tmp_path / "charts").is_dir()


def test_charts_directory_idempotent(tmp_path):
    charts_directory(target_path=tmp_path)
    charts_directory(target_path=tmp_path)  # second call should not raise
    assert (tmp_path / "charts").is_dir()


def test_data_directory_creates_folder(tmp_path):
    data_directory(target_path=tmp_path)
    assert (tmp_path / "data").is_dir()


def test_data_directory_idempotent(tmp_path):
    data_directory(target_path=tmp_path)
    data_directory(target_path=tmp_path)  # second call should not raise
    assert (tmp_path / "data").is_dir()


def test_charts_directory_default_path(tmp_path, monkeypatch):
    """charts_directory() with no argument defaults to cwd."""
    monkeypatch.chdir(tmp_path)
    charts_directory()
    assert (tmp_path / "charts").is_dir()


def test_data_directory_default_path(tmp_path, monkeypatch):
    """data_directory() with no argument defaults to cwd."""
    monkeypatch.chdir(tmp_path)
    data_directory()
    assert (tmp_path / "data").is_dir()
