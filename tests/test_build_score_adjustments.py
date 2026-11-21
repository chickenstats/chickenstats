"""How build_score_adjustments.py turns play-by-play into weights, and whether the shipped table follows its rules.

The build runs on made-up play-by-play, without the network. The expected weights assume a 600-minute minimum.
"""

import json
from importlib import resources
import runpy
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest

from chickenstats.chicken_nhl._game_utils import load_score_adjustments

ROOT = Path(__file__).resolve().parents[1]
# The script is not in a package, so it is run from its path, not imported
build = SimpleNamespace(**runpy.run_path(str(ROOT / "scripts" / "build_score_adjustments.py")))


def test_power_play_weights_compare_rates_and_shrink_a_small_bucket():
    """Each bucket's rate is set against the state's, and a bucket under the minimum moves toward its side's weight."""
    events = {(0, True): 1500, (0, False): 600, (1, True): 300}
    minutes = {(0, True): 600, (0, False): 600, (1, True): 300}

    weights = build.state_weights(events, minutes, rate_based=True)

    # 2,400 events in 1,500 minutes is 1.6 a minute; the home side's is 1,800 in 900, so its venue weight is 0.8
    assert weights[(0, True)] == pytest.approx(1.6 / 2.5)
    assert weights[(0, False)] == pytest.approx(1.6)
    # 300 of the 600 minutes, so halfway from the venue weight (0.8) to its own (1.6)
    assert weights[(1, True)] == pytest.approx(1.2)


def test_even_strength_weights_split_each_score_state_and_shrink_toward_one():
    """At even strength both sides share a score state's ice time, so the weight is the mean count over its own."""
    events = {(0, True): 900, (0, False): 1100}

    full = build.state_weights(events, dict.fromkeys(events, 600), rate_based=False)
    assert full == {(0, True): pytest.approx(1000 / 900), (0, False): pytest.approx(1000 / 1100)}

    # With half the minimum, the venue weight moves halfway to 1.0 and the bucket halfway to the venue weight
    half = build.state_weights(events, dict.fromkeys(events, 300), rate_based=False)
    venue = 1 + (1000 / 900 - 1) / 2
    assert half[(0, True)] == pytest.approx(venue + (1000 / 900 - venue) / 2)


def _rows(n: int, **row) -> list[dict]:
    base = {
        "event": "SHOT",
        "is_home": 0,
        "is_away": 0,
        "home_score_diff": 0,
        "strength_state": "5v5",
        "opp_strength_state": "5v5",
        "teammate_block": 0,
        "event_length": 0,
        "goal": 0,
        "pred_goal": 0.1,
        "shot": 1,
        "miss": 0,
        "block": 0,
        "fenwick": 1,
        "corsi": 1,
    }
    return [base | row] * n


def _ice(minutes: int, home_state: str, home_score_diff: int = 0) -> list[dict]:
    """A stoppage, which has no team and is seen from the home side, holding the given minutes."""
    return _rows(
        1,
        event="STOP",
        strength_state=home_state,
        event_length=minutes * 60,
        shot=0,
        fenwick=0,
        corsi=0,
        home_score_diff=home_score_diff,
    )


@pytest.fixture(scope="module")
def power_play_table():
    """5v4 only: home on the power play tied and leading, and away on the power play tied."""
    home_pp = {"is_home": 1, "strength_state": "5v4", "opp_strength_state": "4v5"}
    away_sh = {"is_away": 1, "strength_state": "4v5", "opp_strength_state": "5v4"}
    away_pp = {"is_away": 1, "strength_state": "5v4", "opp_strength_state": "4v5"}
    rows = [
        *_ice(600, "5v4"),
        *_rows(1200, **home_pp),
        # The short-handed team's shots belong to the power-play team's bucket
        *_rows(300, **away_sh),
        *_ice(600, "4v5"),
        *_rows(600, **away_pp),
        *_ice(300, "5v4", home_score_diff=1),
        *_rows(300, **home_pp, home_score_diff=1),
    ]
    return build.build(pl.DataFrame(rows))


def test_build_weights_the_power_play_by_rate(power_play_table):
    """The same weights as the rate test above, reached from play-by-play."""
    tied, leading = power_play_table["5v4"][0], power_play_table["5v4"][2]

    assert (tied["home_corsi"], tied["home_toi"]) == (1500, 600)
    assert leading["home_toi"] == 300
    assert tied["home_corsi_weight"] == pytest.approx(0.64)
    assert tied["away_corsi_weight"] == pytest.approx(1.6)
    assert leading["home_corsi_weight"] == pytest.approx(1.2)


def test_build_gives_goals_the_fenwick_weight(power_play_table):
    for by_diff in power_play_table.values():
        for row in by_diff.values():
            assert row["home_goal_weight"] == row["home_fenwick_weight"]
            assert row["away_goal_weight"] == row["away_fenwick_weight"]


def test_the_shipped_file_is_what_write_table_writes(tmp_path):
    """The bundled JSON reads back to the same table and is written in the build script's format."""
    # Read from the installed package, since the wheel tests run without src/
    shipped = resources.files("chickenstats.chicken_nhl.score_adjustments") / "score_adjustments.json"
    build.write_table(load_score_adjustments(), tmp_path / "table.json")

    assert (tmp_path / "table.json").read_text(encoding="utf-8") == shipped.read_text(encoding="utf-8")
    assert json.loads(shipped.read_text(encoding="utf-8")).keys() == load_score_adjustments().keys()


def test_every_shipped_weight_is_near_one_or_has_the_minimum_sample():
    """A weight outside 0.85 to 1.15 needs MIN_TOI_MINUTES of ice time behind it."""
    outliers = [
        (state, diff, name)
        for state, by_diff in load_score_adjustments().items()
        for diff, row in by_diff.items()
        for name, weight in row.items()
        if name.endswith("_weight")
        and not 0.85 <= weight <= 1.15
        and row.get(f"{name.split('_')[0]}_toi", 0) < build.MIN_TOI_MINUTES
    ]
    assert outliers == []


def test_shipped_goals_take_the_fenwick_weight():
    for by_diff in load_score_adjustments().values():
        for row in by_diff.values():
            assert (row["home_goal_weight"], row["away_goal_weight"]) == (
                row["home_fenwick_weight"],
                row["away_fenwick_weight"],
            )
