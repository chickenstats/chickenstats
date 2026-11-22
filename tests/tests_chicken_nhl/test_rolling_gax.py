"""prep_rolling_gax and its live helpers, checked against chickenstats-xg's rolling form.

The golden files mock_data/golden/rolling_gax_*.parquet were written once by chickenstats-xg
at commit 870e7af0ab2d4b871706f23622cc4f2d04659d00 (chickenstats_xg/simple/talent.py), from
_history(fixture_game.play_by_play) below:

    rows           compute_rolling_stats(rolling_input(history))
    shooter_games  game_rolling_stats(rolling_input(history))[0]
    goalie_games   game_rolling_stats(rolling_input(history))[1]
    live           continue_rolling(rolling_input(live game), latest_state(...) of the
                   games before it)

each cut to the keys and the features. A change to _history needs the files rewritten from
the same commit.
"""

import os
from collections.abc import Sequence

import narwhals as nw
import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from chickenstats.chicken_nhl import (
    EWMA_HALF_LIFE,
    FORM_GAMES,
    GOALIE_ID_COL,
    MODELLED_STRENGTH_STATES,
    ROLLING_GAX_COLUMNS,
    SHOOTER_ID_COL,
    continue_rolling_gax,
    latest_rolling_state,
    prep_rolling_gax,
    prep_rolling_gax_games,
)
from chickenstats.chicken_nhl.contract import FENWICK_EVENTS
from chickenstats.exceptions import InvalidInputError
from conftest import MOCK_DATA_DIR

GOLDEN_DIR = os.path.join(MOCK_DATA_DIR, "golden")
FEATURES = list(ROLLING_GAX_COLUMNS)
S1 = 20232024
S2 = 20242025
BACKUP_GOALIE = 8400001

# (season, game_date) of each copy of the fixture game, in game_id order. The fourth was
# postponed to the end of the season, so its number says fourth and its date says last.
GAMES: list[tuple[int, str]] = [
    (S1, "2023-10-10"),
    (S1, "2023-10-12"),
    (S1, "2023-10-14"),
    (S1, "2024-04-10"),
    (S1, "2023-10-18"),
    (S1, "2023-10-20"),
    (S1, "2023-10-22"),
    (S1, "2023-10-24"),
    (S1, "2023-10-26"),
    (S1, "2023-10-28"),
    (S1, "2023-10-30"),
    (S2, "2024-10-08"),
    (S2, "2024-10-10"),
    (S2, "2024-10-12"),
]
LIVE_GAME = 2024020003

COLUMNS = [
    "season",
    "session",
    "game_id",
    "game_date",
    "event_idx",
    "event",
    "strength_state",
    "fenwick",
    "goal",
    SHOOTER_ID_COL,
    GOALIE_ID_COL,
]


def _history(pbp: pl.DataFrame) -> pl.DataFrame:
    """The fixture game copied into GAMES, with a synthetic context_xg.

    The xG is a fixed function of the copy and event_idx, null now and then. Odd copies
    hand one goalie's shots to a backup and some shots lose their shooter id, so players'
    games and shot counts differ.
    """
    base = pbp.select(COLUMNS)
    starter = base[GOALIE_ID_COL].drop_nulls().min()
    copies = []
    for k, (season, date) in enumerate(GAMES):
        first_id = (season // 10000) * 1000000 + 20001
        game_id = first_id + sum(1 for s, _ in GAMES[:k] if s == season)
        idx = pl.col("event_idx")
        xg = ((idx * 7919 + k * 104729) % 1000) / 2500 + 0.01
        copies.append(
            base.with_columns(
                season=pl.lit(season, dtype=base.schema["season"]),
                game_id=pl.lit(game_id, dtype=base.schema["game_id"]),
                game_date=pl.lit(date, dtype=base.schema["game_date"]),
                context_xg=pl.when((idx + k) % 23 == 0).then(None).otherwise(xg).cast(pl.Float64),
                **{
                    SHOOTER_ID_COL: pl.when((idx + k) % 31 == 0).then(None).otherwise(pl.col(SHOOTER_ID_COL)),
                    GOALIE_ID_COL: pl.when((k % 2 == 1) & (pl.col(GOALIE_ID_COL) == starter))
                    .then(pl.lit(BACKUP_GOALIE, dtype=base.schema[GOALIE_ID_COL]))
                    .otherwise(pl.col(GOALIE_ID_COL)),
                },
            )
        )
    return pl.concat(copies)


def _in_row_set(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(
        pl.col("event").is_in(sorted(FENWICK_EVENTS)),
        pl.col("fenwick") == 1,
        pl.col("strength_state").is_in(sorted(MODELLED_STRENGTH_STATES)),
    )


def _golden(name: str) -> pl.DataFrame:
    return pl.read_parquet(os.path.join(GOLDEN_DIR, f"rolling_gax_{name}.parquet"))


@pytest.fixture(scope="module")
def history(fixture_game) -> pl.DataFrame:
    return _history(fixture_game.play_by_play)


def _live_split(history: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    return history.filter(pl.col("game_id") != LIVE_GAME), history.filter(pl.col("game_id") == LIVE_GAME)


# ── an exact match with chickenstats-xg ─────────────────────────────────────────────────


_STALE_GOLDEN = pytest.mark.xfail(
    strict=True,
    reason="golden files predate the null-xG fix; regenerate from chickenstats-xg once talent.py's fix is committed",
)


@_STALE_GOLDEN
def test_rows_match_chickenstats_xg(history):
    golden = _golden("rows")
    out = _in_row_set(prep_rolling_gax(history)).select(golden.columns)
    assert_frame_equal(out, golden, check_exact=True)


@_STALE_GOLDEN
def test_games_match_chickenstats_xg(history):
    shooters, goalies = prep_rolling_gax_games(history)
    assert_frame_equal(shooters, _golden("shooter_games"), check_exact=True)
    assert_frame_equal(goalies, _golden("goalie_games"), check_exact=True)


@_STALE_GOLDEN
def test_live_rows_match_chickenstats_xg(history):
    past, live = _live_split(history)
    shooters, goalies = prep_rolling_gax_games(past)
    served = continue_rolling_gax(
        live, latest_rolling_state(shooters, SHOOTER_ID_COL), latest_rolling_state(goalies, GOALIE_ID_COL)
    )
    golden = _golden("live")
    assert_frame_equal(_in_row_set(served).select(golden.columns), golden, check_exact=True)


def test_the_fixture_exercises_the_cases_that_matter(history):
    rows = _in_row_set(history)
    assert rows["context_xg"].null_count() > 0
    assert rows[SHOOTER_ID_COL].null_count() > 0
    assert rows[GOALIE_ID_COL].null_count() > 0  # empty-net shots
    assert BACKUP_GOALIE in rows[GOALIE_ID_COL].to_list()
    assert rows["goal"].sum() > 0
    games = history.select("game_id", "game_date").unique().sort("game_id")
    assert games["game_date"].to_list() != sorted(games["game_date"].to_list())  # the postponed game
    assert history["game_id"].n_unique() > FORM_GAMES


# ── the rows the features count ─────────────────────────────────────────────────────────


def test_every_row_is_kept_and_rows_outside_the_row_set_are_null(history):
    out = prep_rolling_gax(history)
    assert out.height == history.height
    outside = out.join(_in_row_set(out).select("game_id", "event_idx"), on=["game_id", "event_idx"], how="anti")
    assert outside.height > 0
    assert outside.select(pl.col(FEATURES).is_null().all()).row(0) == (True,) * len(FEATURES)


def test_rows_outside_the_row_set_do_not_change_the_features(history):
    full = _in_row_set(prep_rolling_gax(history))
    only = prep_rolling_gax(_in_row_set(history))
    assert_frame_equal(full, only, check_exact=True)


def test_the_constants_follow_chickenstats_xg():
    assert EWMA_HALF_LIFE == 50
    assert FORM_GAMES == 10
    assert {"6v5", "EvE", "1v0", "0v1"}.isdisjoint(MODELLED_STRENGTH_STATES)
    assert len(MODELLED_STRENGTH_STATES) == 15


# ── rolling form looks only backward, ported from chickenstats-xg ───────────────────────

S = 20242025


def _shots(games: list[tuple[int, str, int]], shooter: int | None = 8, goalie: int | None = 30) -> pl.DataFrame:
    """One 5v5 shot per game: (game_id, game_date, goal), context_xg 0.1."""
    return pl.DataFrame(
        {
            "season": S,
            "session": "R",
            "game_id": [g for g, _, _ in games],
            "game_date": [d for _, d, _ in games],
            "event_idx": 0,
            "event": "SHOT",
            "fenwick": 1,
            "strength_state": "5v5",
            SHOOTER_ID_COL: pl.Series([shooter] * len(games), dtype=pl.Int64),
            GOALIE_ID_COL: pl.Series([goalie] * len(games), dtype=pl.Int64),
            "goal": [y for _, _, y in games],
            "context_xg": 0.1,
        }
    )


def test_a_rescheduled_game_does_not_feed_the_windows_of_games_played_before_it():
    # Game 3 was postponed to the end of the season and holds the only goal, so any window
    # that sees it before it was played is a leak.
    games = [
        (1, "2024-10-08", 0),
        (2, "2024-10-10", 0),
        (3, "2025-04-10", 1),
        (4, "2024-10-12", 0),
        (5, "2024-10-14", 0),
    ]
    out = prep_rolling_gax(_shots(games)).sort("game_date")

    played_before = out.filter(pl.col("game_id") != 3)
    assert played_before["game_id"].to_list() == [1, 2, 4, 5]
    assert played_before["shooter_gax_10g"].drop_nulls().to_list() == pytest.approx([-0.1, -0.2, -0.3])
    assert (played_before["shooter_gax_ewma"].drop_nulls() < 0).all()
    assert (played_before["goalie_gsax_10g"].drop_nulls() > 0).all()

    late = out.filter(pl.col("game_id") == 3).row(0, named=True)
    assert late["shooter_gax_10g"] == pytest.approx(-0.4)


def test_shots_with_no_shooter_id_get_no_form_and_do_not_pool_together():
    known = _shots([(1, "2024-10-08", 1), (2, "2024-10-10", 0)], shooter=8)
    unknown = _shots([(1, "2024-10-08", 1), (2, "2024-10-10", 1)], shooter=None).with_columns(event_idx=pl.lit(1))
    out = prep_rolling_gax(pl.concat([known, unknown])).sort("game_id", "event_idx")

    nameless = out.filter(pl.col(SHOOTER_ID_COL).is_null())
    for col in ("shooter_gax_10g", "shooter_gax_ewma", "shooter_gax_per_shot_10g"):
        assert nameless[col].null_count() == nameless.height
    named = out.filter((pl.col(SHOOTER_ID_COL) == 8) & (pl.col("game_id") == 2))
    assert named["shooter_gax_10g"].item() == pytest.approx(0.9)


def _ewma(xs: list[float]) -> float:
    """The adjusted EWMA of xs, oldest first, in plain Python."""
    d = 0.5 ** (1 / EWMA_HALF_LIFE)
    weights = [d ** (len(xs) - 1 - i) for i in range(len(xs))]
    return sum(w * x for w, x in zip(weights, xs, strict=True)) / sum(weights)


def _game_shots(games: Sequence[tuple[int, str, Sequence[tuple[int, float | None]]]]) -> pl.DataFrame:
    """Shooter 8's 5v5 shots on goalie 30: (game_id, game_date, [(goal, context_xg), ...])."""
    return pl.concat(
        [
            _shots([(game_id, date, goal)]).with_columns(event_idx=pl.lit(i), context_xg=pl.lit(xg, dtype=pl.Float64))
            for game_id, date, shots in games
            for i, (goal, xg) in enumerate(shots)
        ]
    )


def test_a_null_xg_shot_adds_nothing_to_the_ewma_and_hides_nothing_after_it():
    goals, xgs = [1, 0, 0, 0], [0.2, None, 0.4, 0.1]
    out = prep_rolling_gax(_game_shots([(1, "2024-10-08", list(zip(goals, xgs, strict=True)))])).sort("event_idx")
    gax = [g - x for g, x in zip(goals, xgs, strict=True) if x is not None]  # 0.8, -0.4, -0.1
    expected = [_ewma(gax[:1]), _ewma(gax[:1]), _ewma(gax[:2])]  # after the first shot
    shooter = out["shooter_gax_ewma"].to_list()
    assert shooter[0] is None
    assert shooter[1:] == pytest.approx(expected, rel=0, abs=1e-15)
    assert shooter[2] == pytest.approx(0.8)  # the shot right after the null xG
    goalie = out["goalie_gsax_ewma"].to_list()
    assert goalie[0] is None
    assert goalie[1:] == pytest.approx([-v for v in expected], rel=0, abs=1e-15)


def test_null_xg_shots_are_left_out_of_the_shot_counts():
    # Game 2's only shot has no xG, a goal that must not feed the total or the shot count.
    games = [
        (1, "2024-10-08", [(1, 0.2), (0, None)]),
        (2, "2024-10-10", [(1, None)]),
        (3, "2024-10-12", [(0, 0.3)]),
        (4, "2024-10-14", [(0, 0.1)]),
    ]
    out = prep_rolling_gax(_game_shots(games)).group_by("game_id", maintain_order=True).first().sort("game_id")
    assert out["shooter_gax_10g"].to_list() == [None, pytest.approx(0.8), pytest.approx(0.8), pytest.approx(0.5)]
    assert out["shooter_gax_per_shot_10g"].to_list() == [
        None,
        pytest.approx(0.8),
        pytest.approx(0.8),
        pytest.approx(0.25),
    ]

    shooters, goalies = prep_rolling_gax_games(_game_shots(games))
    assert shooters["shooter_gax_shots_after"].to_list() == [1, 1, 2, 3]
    assert shooters["shooter_gax_shots_10g_after"].to_list() == [1, 1, 2, 3]
    assert shooters["shooter_gax_10g_after"].to_list() == pytest.approx([0.8, 0.8, 0.5, 0.4])
    # The game with no xG keeps the EWMA of the game before it.
    assert shooters["shooter_gax_ewma_after"].to_list() == pytest.approx(
        [_ewma([0.8]), _ewma([0.8]), _ewma([0.8, -0.3]), _ewma([0.8, -0.3, -0.1])], rel=0, abs=1e-15
    )
    assert goalies["goalie_gsax_shots_after"].to_list() == [1, 1, 2, 3]
    assert goalies["goalie_gsax_10g_after"].to_list() == pytest.approx([-0.8, -0.8, -0.5, -0.4])


def test_a_player_whose_first_shot_has_null_xg_starts_from_his_first_shot_with_one():
    games = [(1, "2024-10-08", [(1, None)]), (2, "2024-10-10", [(0, 0.2), (1, 0.3), (0, 0.1)])]
    out = prep_rolling_gax(_game_shots(games)).sort("game_id", "event_idx")
    assert out["shooter_gax_ewma"].to_list() == [
        None,
        None,
        pytest.approx(_ewma([-0.2])),
        pytest.approx(_ewma([-0.2, 0.7])),
    ]
    # Game 1 holds a place in the window but no shot with an xG, so game 2 has no form yet.
    assert out["shooter_gax_10g"].to_list() == [None] * 4
    assert out["shooter_gax_per_shot_10g"].to_list() == [None] * 4

    shooters, _ = prep_rolling_gax_games(_game_shots(games))
    first = shooters.row(0, named=True)
    assert first["shooter_gax_ewma_after"] is None
    assert first["shooter_gax_shots_after"] is None
    assert first["shooter_gax_shots_10g_after"] == 0


def test_xg_col_names_the_expected_goals_column(history):
    renamed = history.rename({"context_xg": "base_xg"})
    assert_frame_equal(
        prep_rolling_gax(renamed, xg_col="base_xg").drop("base_xg"),
        prep_rolling_gax(history).drop("context_xg"),
        check_exact=True,
    )


# ── the live path equals the batch, ported from chickenstats-xg ─────────────────────────


def _served(past: pl.DataFrame, live: pl.DataFrame) -> pl.DataFrame:
    shooters, goalies = prep_rolling_gax_games(past)
    return continue_rolling_gax(
        live, latest_rolling_state(shooters, SHOOTER_ID_COL), latest_rolling_state(goalies, GOALIE_ID_COL)
    )


def _assert_live_equals_batch(past: pl.DataFrame, live: pl.DataFrame) -> pl.DataFrame:
    live_ids = live["game_id"].unique().implode()
    batch = _in_row_set(prep_rolling_gax(pl.concat([past, live])).filter(pl.col("game_id").is_in(live_ids)))
    served = _in_row_set(_served(past, live))
    assert served.height == batch.height
    assert_frame_equal(served.select(FEATURES), batch.select(FEATURES), rel_tol=0, abs_tol=1e-12)
    return batch


def test_live_form_carried_from_the_stored_state_equals_the_batch(history):
    past, live = _live_split(history)
    batch = _assert_live_equals_batch(past, live)
    assert batch["shooter_gax_ewma"].drop_nulls().n_unique() > 8  # form moves within the game

    # The fixture has players whose last stored shot has no xG, the case that used to differ.
    last = (
        _in_row_set(past)
        .filter(pl.col(SHOOTER_ID_COL).is_not_null())
        .sort("season", "game_date", "game_id", "event_idx")
        .group_by(SHOOTER_ID_COL, maintain_order=True)
        .last()
    )
    carried = last.filter(pl.col("context_xg").is_null())[SHOOTER_ID_COL].implode()
    assert batch.filter(pl.col(SHOOTER_ID_COL).is_in(carried))["shooter_gax_ewma"].null_count() == 0
    assert live["context_xg"].null_count() > 0


def test_live_equals_the_batch_after_a_game_with_no_xg():
    past = _game_shots([(1, "2024-10-08", [(1, 0.2), (0, None)]), (2, "2024-10-10", [(1, None)])])
    live = _game_shots([(3, "2024-10-12", [(0, None), (0, 0.3), (1, 0.1)])])
    batch = _assert_live_equals_batch(past, live)
    assert batch["shooter_gax_ewma"].to_list() == pytest.approx([0.8, 0.8, _ewma([0.8, -0.3])])
    assert batch["shooter_gax_per_shot_10g"].to_list() == pytest.approx([0.8] * 3)


def test_live_equals_the_batch_for_a_player_with_no_xg_yet():
    past = _game_shots([(1, "2024-10-08", [(1, None)])])
    live = _game_shots([(2, "2024-10-10", [(0, None), (0, 0.3), (1, 0.1)])])
    batch = _assert_live_equals_batch(past, live)
    assert batch["shooter_gax_ewma"].to_list() == [None, None, pytest.approx(-0.3)]
    assert batch["shooter_gax_10g"].null_count() == 3


def test_a_player_with_no_state_starts_as_a_first_shot_does(history):
    past, live = _live_split(history)
    shooters, goalies = prep_rolling_gax_games(past)
    empty_shooters = latest_rolling_state(shooters, SHOOTER_ID_COL).clear()
    served = _in_row_set(continue_rolling_gax(live, empty_shooters, latest_rolling_state(goalies, GOALIE_ID_COL)))
    fresh = _in_row_set(prep_rolling_gax(live))
    named = pl.col(SHOOTER_ID_COL).is_not_null()
    cols = ["shooter_gax_ewma", "shooter_gax_10g", "shooter_gax_per_shot_10g"]
    a, b = served.filter(named).select(cols), fresh.filter(named).select(cols)
    assert_frame_equal(a.select(pl.col(cols).is_null()), b.select(pl.col(cols).is_null()))
    np.testing.assert_allclose(
        a["shooter_gax_ewma"].drop_nulls().to_numpy(), b["shooter_gax_ewma"].drop_nulls().to_numpy(), atol=1e-12
    )


def test_the_stored_entering_values_are_the_first_shot_of_each_game(history):
    shooters, _ = prep_rolling_gax_games(history)
    first = (
        _in_row_set(prep_rolling_gax(history))
        .filter(pl.col(SHOOTER_ID_COL).is_not_null())
        .group_by(SHOOTER_ID_COL, "game_id", maintain_order=True)
        .first()
        .select(SHOOTER_ID_COL, "game_id", pl.col("shooter_gax_ewma").alias("first"))
    )
    joined = shooters.join(first, on=[SHOOTER_ID_COL, "game_id"])
    assert joined.height == shooters.height
    assert joined.filter(pl.col("shooter_gax_ewma").ne_missing(pl.col("first"))).is_empty()


def test_latest_state_is_the_last_game_played_not_the_highest_game_id(history):
    shooters, _ = prep_rolling_gax_games(history.filter(pl.col("season") == S1))
    state = latest_rolling_state(shooters, SHOOTER_ID_COL)
    assert state[SHOOTER_ID_COL].is_unique().all()
    postponed = 2023020004
    assert set(state["game_id"].to_list()) == {postponed}


# ── bad input raises InvalidInputError ──────────────────────────────────────────────────


def test_missing_columns_are_named_together(history):
    with pytest.raises(InvalidInputError, match=r"fenwick.*strength_state"):
        prep_rolling_gax(history.drop("fenwick", "strength_state"))
    with pytest.raises(InvalidInputError, match="base_xg"):
        prep_rolling_gax_games(history, xg_col="base_xg")


def test_a_null_game_date_raises(history):
    with pytest.raises(InvalidInputError, match="null game_date"):
        prep_rolling_gax(
            history.with_columns(game_date=pl.when(pl.col("event_idx") == 1).then(None).otherwise("game_date"))
        )


def test_a_column_of_the_wrong_type_raises_invalid_input(history):
    with pytest.raises(InvalidInputError, match="could not compute"):
        prep_rolling_gax(history.with_columns(pl.col("goal").cast(pl.String)))


def test_a_state_with_repeated_players_raises(history):
    past, live = _live_split(history)
    shooters, goalies = prep_rolling_gax_games(past)
    with pytest.raises(InvalidInputError, match="one shooter_state row per"):
        continue_rolling_gax(live, shooters, latest_rolling_state(goalies, GOALIE_ID_COL))
    with pytest.raises(InvalidInputError, match="goalie_state"):
        continue_rolling_gax(
            live, latest_rolling_state(shooters, SHOOTER_ID_COL), goalies.drop("goalie_gsax_10g_after")
        )


def test_latest_state_needs_its_columns(history):
    shooters, _ = prep_rolling_gax_games(history)
    with pytest.raises(InvalidInputError, match="game_date"):
        latest_rolling_state(shooters.drop("game_date"), SHOOTER_ID_COL)


# ── backends ────────────────────────────────────────────────────────────────────────────


def test_narwhals_input_comes_back_as_narwhals(history):
    out = prep_rolling_gax(nw.from_native(history, eager_only=True))
    assert isinstance(out, nw.DataFrame)
    assert_frame_equal(out.to_native(), prep_rolling_gax(history), check_exact=True)
    shooters, goalies = prep_rolling_gax_games(history, backend="narwhals")
    assert isinstance(shooters, nw.DataFrame) and isinstance(goalies, nw.DataFrame)


def test_pandas_input_comes_back_as_pandas(history):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    out = prep_rolling_gax(history.to_pandas())
    assert isinstance(out, pd.DataFrame)
    np.testing.assert_array_equal(
        out["shooter_gax_ewma"].to_numpy(dtype=float, na_value=np.nan),
        prep_rolling_gax(history)["shooter_gax_ewma"].to_numpy().astype(float),
    )


def test_pyarrow_backend_returns_tables(history):
    pa = pytest.importorskip("pyarrow")
    past, live = _live_split(history)
    shooters, goalies = prep_rolling_gax_games(past, backend="pyarrow")
    assert isinstance(shooters, pa.Table) and isinstance(goalies, pa.Table)
    state = latest_rolling_state(shooters, SHOOTER_ID_COL, backend="pyarrow")
    out = continue_rolling_gax(live, state, latest_rolling_state(goalies, GOALIE_ID_COL), backend="pyarrow")
    assert isinstance(out, pa.Table)
    assert set(FEATURES) <= set(out.column_names)
