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


def test_rows_match_chickenstats_xg(history):
    golden = _golden("rows")
    out = _in_row_set(prep_rolling_gax(history)).select(golden.columns)
    assert_frame_equal(out, golden, check_exact=True)


def test_games_match_chickenstats_xg(history):
    shooters, goalies = prep_rolling_gax_games(history)
    assert_frame_equal(shooters, _golden("shooter_games"), check_exact=True)
    assert_frame_equal(goalies, _golden("goalie_games"), check_exact=True)


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


def test_a_missing_xg_stays_null_and_the_ewma_skips_it():
    shots = pl.concat(
        [
            _shots([(1, "2024-10-08", 0)]).with_columns(event_idx=pl.lit(i), goal=pl.lit(g))
            for i, g in enumerate([1, 0, 0])
        ]
    ).with_columns(context_xg=pl.Series([0.2, None, 0.4]))
    out = prep_rolling_gax(shots).sort("event_idx")
    # The shot after the missing xG has no EWMA, since the mean is shifted from a null.
    assert out["shooter_gax_ewma"].to_list()[:2] == [None, pytest.approx(0.8)]
    assert out["shooter_gax_ewma"][2] is None


def test_xg_col_names_the_expected_goals_column(history):
    renamed = history.rename({"context_xg": "base_xg"})
    assert_frame_equal(
        prep_rolling_gax(renamed, xg_col="base_xg").drop("base_xg"),
        prep_rolling_gax(history).drop("context_xg"),
        check_exact=True,
    )


# ── the live path equals the batch, ported from chickenstats-xg ─────────────────────────


def test_live_form_carried_from_the_stored_state_equals_the_batch(history):
    past, live = _live_split(history)
    batch = _in_row_set(prep_rolling_gax(history).filter(pl.col("game_id") == LIVE_GAME))
    shooters, goalies = prep_rolling_gax_games(past)
    served = _in_row_set(
        continue_rolling_gax(
            live, latest_rolling_state(shooters, SHOOTER_ID_COL), latest_rolling_state(goalies, GOALIE_ID_COL)
        )
    )

    both = batch.select("event_idx", SHOOTER_ID_COL, GOALIE_ID_COL, *FEATURES).join(
        served.select("event_idx", *FEATURES), on="event_idx", suffix="_live"
    )
    assert both.height == batch.height == served.height

    # chickenstats-xg's behavior, kept: when a player's last stored shot has no xG, the
    # batch EWMA of his next shot is the shift of a null mean, so null, while the stored
    # state carries the mean through the shots before it. Only that first live shot differs.
    for id_col, prefix in ((SHOOTER_ID_COL, "shooter_gax"), (GOALIE_ID_COL, "goalie_gsax")):
        last_null = (
            _in_row_set(past)
            .filter(pl.col(id_col).is_not_null())
            .sort("season", "game_date", "game_id", "event_idx")
            .group_by(id_col, maintain_order=True)
            .last()
            .filter(pl.col("context_xg").is_null())[id_col]
        )
        first_live = pl.col("event_idx") == pl.col("event_idx").min().over(id_col)
        differs = both.filter(pl.col(id_col).is_in(last_null.implode()) & first_live)
        assert differs[f"{prefix}_ewma"].is_null().all()
        assert differs[f"{prefix}_ewma_live"].is_not_null().all()
        both = both.with_columns(
            pl.when(pl.col("event_idx").is_in(differs["event_idx"].implode()))
            .then(None)
            .otherwise(pl.col(f"{prefix}_ewma_live"))
            .alias(f"{prefix}_ewma_live")
        )
        if prefix == "shooter_gax":
            assert differs.height > 0  # the fixture has the case

    for f in FEATURES:
        a, b = both[f].to_numpy().astype(float), both[f"{f}_live"].to_numpy().astype(float)
        assert np.array_equal(np.isnan(a), np.isnan(b)), f
        np.testing.assert_allclose(b[~np.isnan(b)], a[~np.isnan(a)], rtol=0, atol=1e-12, err_msg=f)
    assert both["shooter_gax_ewma"].drop_nulls().n_unique() > 8  # form moves within the game


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
