from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

import polars as pl

from chickenstats.chicken_nhl._game_utils import (
    aggregate_players,
    _return_name_html as return_name_html,
    prepare_xg,
    calculate_score_adjustment,
    handle_penalty_details,
    load_score_adjustments,
)
from chickenstats.utilities.utilities import convert_to_list
from chickenstats.exceptions import InvalidInputError
from chickenstats.utilities.utilities import charts_directory, data_directory, norm_coords


@pytest.fixture(scope="package")
def test_pbp():
    filepath = Path("./tests/tests_chicken_nhl/data/test_pbp.csv")

    if not HAS_PANDAS:
        pytest.skip("pandas not installed")

    test_pbp = pd.read_csv(filepath, low_memory=False)

    return test_pbp


def test_norm_coords(test_pbp, norm_column="event_team", norm_value="NSH"):
    data = norm_coords(data=test_pbp, normalization_column=norm_column, normalization_value=norm_value)

    assert {"norm_coords_x", "norm_coords_y"} <= set(data.columns)
    assert data["norm_coords_x"].notna().any()
    assert data["norm_coords_y"].notna().any()


@pytest.mark.parametrize(
    "test_list",
    [
        2023020001,
        2023020001.0,
        "2023020001",
        (2023020001, 2023020002),
        np.array([2023020001]),
        *([pd.Series([2023020001])] if HAS_PANDAS else []),
    ],
)
def test_convert_to_list(test_list):
    test_list = convert_to_list(test_list, "GAME ID")

    assert isinstance(test_list, list) is True


def test_convert_to_list_fail():
    with pytest.raises(InvalidInputError):
        convert_to_list(cast(Any, {"test_key": "test_value"}), "TEST")


def test_return_name_html():
    name = return_name_html("GOALIE - PEKKA RINNE")

    assert name == "PEKKA RINNE"


def test_return_name_html_no_hyphen_no_crash():
    """Malformed HTML title text with no hyphen must not raise ValueError.

    Regression test: `.index("-")` used to raise uncaught ValueError for such input,
    which propagated past the caller's `except KeyError` in hs_strip_html and aborted
    parsing of the entire game's roster instead of degrading one player's name.
    """
    name = return_name_html("PEKKA RINNE")
    assert name == "PEKKA RINNE"


# -----------------------------------------------------------------------------
# calculate_score_adjustment
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def score_adjustments():
    return load_score_adjustments()


@pytest.mark.parametrize("stat", ["goal", "pred_goal", "shot", "fenwick", "corsi"])
def test_score_adjustments_keep_the_total_weight_of_events(score_adjustments, stat):
    """In each strength and score state, the weighted home and away events add up to the raw total (McCurdy)."""
    assert sorted(score_adjustments) == ["3v3", "4v3", "4v4", "5v3", "5v4", "5v5"]
    for state, by_diff in score_adjustments.items():
        assert sorted(by_diff) == [-3, -2, -1, 0, 1, 2, 3], state
        for diff, row in by_diff.items():
            home, away = row[f"home_{stat}"], row[f"away_{stat}"]
            weighted = row[f"home_{stat}_weight"] * home + row[f"away_{stat}_weight"] * away
            assert weighted == pytest.approx(home + away), (state, diff)


def _base_play(**overrides) -> dict:
    """Minimal play dict with all keys required by calculate_score_adjustment."""
    play = {
        "event": "SHOT",
        "event_team": "NSH",
        "opp_team": "CHI",
        "home_team": "NSH",
        "home_score_diff": 0,
        "strength_state": "5v5",
        "opp_strength_state": "5v5",
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
    """A home shot gets the home weights at its score difference: shot, Fenwick and Corsi each their own."""
    weights = score_adjustments["5v5"][0]
    result = calculate_score_adjustment(_base_play(), score_adjustments)

    assert result["shot_adj"] == pytest.approx(weights["home_shot_weight"])
    assert result["fenwick_adj"] == pytest.approx(weights["home_fenwick_weight"])
    assert result["corsi_adj"] == pytest.approx(weights["home_corsi_weight"])
    assert result["goal_adj"] == 0


def test_calculate_score_adjustment_block_opponent(score_adjustments):
    """A shot NSH blocks is weighted for CHI, the away team that shot it."""
    play = _base_play(event="BLOCK", event_team="NSH", opp_team="CHI", teammate_block=0, shot=0, fenwick=0, block=1)
    result = calculate_score_adjustment(play, score_adjustments)

    assert result["block_adj"] == pytest.approx(score_adjustments["5v5"][0]["away_corsi_weight"])


def test_calculate_score_adjustment_blocked_power_play_shot(score_adjustments):
    """A blocked power-play shot gets the shooting team's power-play weight, like the same shot unblocked."""
    shot = _base_play(event="SHOT", event_team="NSH", opp_team="CHI", strength_state="5v4", opp_strength_state="4v5")
    block = _base_play(
        event="BLOCK",
        event_team="CHI",
        opp_team="NSH",
        strength_state="4v5",
        opp_strength_state="5v4",
        shot=0,
        fenwick=0,
        block=1,
    )

    shot_adj = calculate_score_adjustment(shot, score_adjustments)["corsi_adj"]
    block_adj = calculate_score_adjustment(block, score_adjustments)["corsi_adj"]

    assert block_adj == pytest.approx(shot_adj)


def _xg_rows(*rows: dict) -> pl.DataFrame:
    """Shot rows for prepare_xg, NSH at home against CHI, overriding the columns each case needs."""
    base = {
        "event": "SHOT",
        "event_team": "NSH",
        "opp_team": "CHI",
        "home_team": "NSH",
        "home_score_diff": 0,
        "strength_state": "5v5",
        "opp_strength_state": "5v5",
        "teammate_block": 0,
        "shootout_attempt": 0,
        "pred_goal": 0.2,
    }
    return pl.DataFrame([{**base, **row} for row in rows])


def test_prepare_xg_uses_the_score_adjustment_rules(score_adjustments):
    """The pred_goal weight is the shooting team's, mirrored on the penalty kill, and 1.0 outside the table."""
    df = _xg_rows(
        {},
        {"event_team": "CHI", "opp_team": "NSH", "home_score_diff": 5},
        {"strength_state": "4v5", "opp_strength_state": "5v4", "home_score_diff": -1},
        {"event": "GOAL", "strength_state": "1v0", "opp_strength_state": "0v1"},
    )
    expected = [
        score_adjustments["5v5"][0]["home_pred_goal_weight"],
        score_adjustments["5v5"][3]["away_pred_goal_weight"],
        score_adjustments["5v4"][-1]["away_pred_goal_weight"],
        1.0,
    ]

    result = prepare_xg(df)

    assert result["pred_goal_adj"].to_list() == pytest.approx([0.2 * weight for weight in expected])


def test_prepare_xg_adjusts_every_xg_column(score_adjustments):
    """base_xg and context_xg get adjusted columns with the same weight as pred_goal."""
    df = _xg_rows({"event_team": "CHI", "opp_team": "NSH"}).with_columns(base_xg=pl.lit(0.3), context_xg=pl.lit(0.4))
    weight = score_adjustments["5v5"][0]["away_pred_goal_weight"]

    result = prepare_xg(df)

    assert result.select("pred_goal_adj", "base_xg_adj", "context_xg_adj").row(0) == pytest.approx(
        (0.2 * weight, 0.3 * weight, 0.4 * weight)
    )


def test_prepare_xg_counts_xg_only_on_goals_shots_and_misses():
    """xG on a blocked shot or any other event is null, and so is a NaN."""
    df = _xg_rows({"event": "BLOCK"}, {"event": "PENL"}, {"pred_goal": float("nan")}, {"event": "MISS"})

    result = prepare_xg(df)

    assert result["pred_goal"].to_list() == [None, None, None, 0.2]
    assert result["pred_goal_adj"].to_list()[:3] == [None, None, None]


def test_prepare_xg_gives_shootout_attempts_no_xg():
    result = prepare_xg(_xg_rows({"shootout_attempt": 1, "strength_state": "1v0"}))

    assert result.select("pred_goal", "pred_goal_adj").row(0) == (0.0, 0.0)


def test_prepare_xg_keeps_a_supplied_adjustment():
    result = prepare_xg(_xg_rows({}).with_columns(pred_goal_adj=pl.lit(0.5)))

    assert result["pred_goal_adj"].to_list() == [0.5]


def test_prepare_xg_does_nothing_without_pred_goal():
    df = _xg_rows({}).drop("pred_goal")

    assert prepare_xg(df).columns == df.columns


def test_calculate_score_adjustment_block_teammate(score_adjustments):
    """A shot a teammate blocked is weighted for its event team, NSH at home, which shot it."""
    play = _base_play(event="BLOCK", event_team="NSH", opp_team="CHI", teammate_block=1, shot=0, fenwick=0, block=0)
    result = calculate_score_adjustment(play, score_adjustments)

    assert result["teammate_block_adj"] == pytest.approx(score_adjustments["5v5"][0]["home_corsi_weight"])


def test_calculate_score_adjustment_miss(score_adjustments):
    """A miss is weighted with the Fenwick weight."""
    play = _base_play(event="MISS", shot=0, miss=1, fenwick=1)
    result = calculate_score_adjustment(play, score_adjustments)

    assert result["miss_adj"] == pytest.approx(score_adjustments["5v5"][0]["home_fenwick_weight"])


@pytest.mark.parametrize(("home_score_diff", "table_diff"), [(-5, -3), (-1, -1), (2, 2), (5, 3)])
def test_calculate_score_adjustment_uses_the_home_score_difference(score_adjustments, home_score_diff, table_diff):
    """The weight is looked up at the home score difference, clamped to -3 and +3, for each side."""
    weights = score_adjustments["5v5"][table_diff]
    home = calculate_score_adjustment(_base_play(home_score_diff=home_score_diff), score_adjustments)
    away = calculate_score_adjustment(
        _base_play(home_score_diff=home_score_diff, event_team="CHI", opp_team="NSH"), score_adjustments
    )

    assert home["shot_adj"] == pytest.approx(weights["home_shot_weight"])
    assert away["shot_adj"] == pytest.approx(weights["away_shot_weight"])


def test_calculate_score_adjustment_empty_net_no_division(score_adjustments):
    """Strength state with 'E' uses identity weight (multiplied by 1)."""
    play = _base_play(strength_state="5v4E")
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" in result
    assert result["shot_adj"] == play["shot"]


def test_calculate_score_adjustment_disadvantage_flips_home(score_adjustments):
    """Strength state 4v5 swaps is_home before lookup, consistently across every adjusted column.

    Regression test: the flip used to be re-toggled once per column inside the adjusted-columns
    loop instead of decided once per play, so only every other column (goal/miss/teammate_block/
    corsi) got the flipped weight while the rest (shot/block/fenwick) silently kept the unflipped
    one. All seven columns must use the same (flipped) perspective.
    """
    play = _base_play(
        event_team="NSH",
        home_team="NSH",
        strength_state="4v5",
        home_score_diff=0,
        goal=1,
        shot=1,
        miss=1,
        block=1,
        teammate_block=1,
        fenwick=1,
        corsi=1,
    )
    result = calculate_score_adjustment(play, score_adjustments)

    # Home team ("NSH") is shorthanded (4v5), so is_home flips to the away perspective and
    # the strength state reverses to "5v4" for the weight-table lookup.
    away_weights = score_adjustments["5v4"][0]

    expected = {
        "goal_adj": away_weights["away_goal_weight"] * play["goal"],
        "shot_adj": away_weights["away_shot_weight"] * play["shot"],
        "miss_adj": away_weights["away_fenwick_weight"] * play["miss"],
        "block_adj": away_weights["away_corsi_weight"] * play["block"],
        "teammate_block_adj": away_weights["away_corsi_weight"] * play["teammate_block"],
        "fenwick_adj": away_weights["away_fenwick_weight"] * play["fenwick"],
        "corsi_adj": away_weights["away_corsi_weight"] * play["corsi"],
    }

    for key, value in expected.items():
        assert result[key] == pytest.approx(value), f"{key} did not use the flipped (away) weight"


def test_calculate_score_adjustment_non_shot_event_unchanged(score_adjustments):
    """Non-shot events (e.g. FACEOFF) pass through without adding _adj keys."""
    play = _base_play(event="FACEOFF")
    result = calculate_score_adjustment(play, score_adjustments)
    assert "shot_adj" not in result


# -----------------------------------------------------------------------------
# charts_directory / data_directory
# -----------------------------------------------------------------------------


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


# -----------------------------------------------------------------------------
# handle_penalty_details
# -----------------------------------------------------------------------------


def _penalty(**details) -> dict:
    return {"typeCode": "BEN", "descKey": "too-many-men-on-the-ice", "duration": 2, **details}


def test_bench_minor_with_a_drawer_puts_the_drawer_in_player_2():
    """As for any penalty, player_2 drew it and player_3 serves it."""
    info = handle_penalty_details(_penalty(drawnByPlayerId=1, servedByPlayerId=2))

    assert (info["player_1"], info["player_2_api_id"], info["player_3_api_id"]) == ("BENCH", 1, 2)
    assert (info["player_2_type"], info["player_3_type"]) == ("DRAWN BY", "SERVED BY")


def test_bench_minor_with_no_drawer_keeps_the_server_in_player_3():
    """With no drawer, player_2 stays empty instead of taking the server (hk-04)."""
    info = handle_penalty_details(_penalty(servedByPlayerId=2))

    assert (info["player_1"], info["player_3_api_id"], info["player_3_type"]) == ("BENCH", 2, "SERVED BY")
    assert info.get("player_2_api_id") is None


# -----------------------------------------------------------------------------
# aggregate_players
# -----------------------------------------------------------------------------


def _player(api_id, position: str, name: str) -> dict:
    return {"team_jersey": f"NSH{name}", "player_name": name, "eh_id": name, "api_id": api_id, "position": position}


def test_aggregate_players_sorts_by_position_then_api_id():
    """Forwards (C, L and R alike), then defense, then goalies, each by API ID."""
    players = [_player(3, "C", "C3"), _player(1, "D", "D1"), _player(2, "G", "G2"), _player(4, "L", "L4")]

    agg = aggregate_players(players)

    assert agg["ALL"]["names"] == ["C3", "L4", "D1", "G2"]
    assert (agg["F"]["count"], agg["D"]["count"], agg["G"]["count"]) == (2, 1, 1)


def test_aggregate_players_keeps_a_player_with_no_api_id():
    """A player with no API ID sorts after the others in their bucket instead of raising (R17)."""
    players = [_player(None, "C", "NOID"), _player(5, "C", "C5"), _player(2, "D", "D2")]

    agg = aggregate_players(players)

    assert agg["ALL"]["names"] == ["C5", "NOID", "D2"]
    assert agg["F"]["names"] == ["C5", "NOID"]
