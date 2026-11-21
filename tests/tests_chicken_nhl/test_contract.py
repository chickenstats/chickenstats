"""Tests for chickenstats.chicken_nhl.contract against the saved games."""

import polars as pl
import pytest

from chickenstats.chicken_nhl.contract import (
    EVENT_SORT_ORDER,
    FENWICK_EVENTS,
    PBP_ORDER_COLUMNS,
    STRENGTH_STATES,
    assert_chronological,
    assert_unique_events,
    assert_xg_fields_match,
    build_pandera_schema,
    sort_chronological,
)
from chickenstats.exceptions import InvalidInputError


def test_play_by_play_is_already_in_contract_order(fixture_game):
    """Sorting on the order columns changes nothing."""
    pbp = fixture_game.play_by_play

    assert pbp.equals(pbp.sort(PBP_ORDER_COLUMNS, maintain_order=True))


def test_a_shot_ranks_before_a_change_and_a_change_before_a_faceoff():
    """The rule the on-ice columns depend on."""
    assert EVENT_SORT_ORDER["SHOT"] < EVENT_SORT_ORDER["CHANGE"] < EVENT_SORT_ORDER["FAC"]


def test_saved_games_stay_inside_the_strength_states(shootout_game, playoff_overtime_game):
    """A sound game produces no state outside the vocabulary."""
    for game in (shootout_game, playoff_overtime_game):
        states = set(game.play_by_play.filter(pl.col("event") != "CHANGE")["strength_state"].drop_nulls())

        assert states <= set(STRENGTH_STATES)


def _rows() -> pl.DataFrame:
    """Two games, with the later game_id played first."""
    return pl.DataFrame(
        {
            "season": [20242025] * 3,
            "game_date": ["2024-10-09", "2024-10-08", "2024-10-08"],
            "game_id": [2024020001, 2024020002, 2024020002],
            "event_idx": [1, 2, 1],
        }
    )


def test_rows_sort_by_the_date_played_not_the_game_id():
    assert sort_chronological(_rows())["game_id"].to_list() == [2024020002, 2024020002, 2024020001]


def test_pandas_rows_sort_the_same_way():
    pytest.importorskip("pandas")

    assert sort_chronological(_rows().to_pandas())["event_idx"].tolist() == [1, 2, 1]


def test_rows_without_a_date_are_refused():
    with pytest.raises(InvalidInputError, match="game_date"):
        sort_chronological(_rows().drop("game_date"))


def test_rows_that_step_back_in_time_raise():
    with pytest.raises(ValueError, match="1 steps back"):
        assert_chronological(_rows(), what="rows")


def test_a_split_game_raises():
    rows = sort_chronological(_rows()).with_columns(game_id=pl.Series([1, 2, 1]), game_date=pl.lit("2024-10-08"))

    with pytest.raises(ValueError, match="split"):
        assert_chronological(rows, what="rows")


def test_sorted_rows_pass():
    assert_chronological(sort_chronological(_rows()), what="rows")


def test_a_repeated_event_raises():
    with pytest.raises(ValueError, match="1 "):
        assert_unique_events(pl.concat([_rows(), _rows().head(1)]), what="rows")


@pytest.mark.parametrize(
    "call",
    [
        lambda: assert_chronological(_rows(), "rows"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: assert_unique_events(_rows(), "rows"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: assert_xg_fields_match(_rows(), _rows(), "rows"),  # ty: ignore[missing-argument, too-many-positional-arguments]
        lambda: build_pandera_schema({}, {}, {}, "polars"),  # ty: ignore[no-matching-overload]
    ],
    ids=["assert_chronological", "assert_unique_events", "assert_xg_fields_match", "build_pandera_schema"],
)
def test_options_are_keyword_only(call):
    with pytest.raises(TypeError):
        call()


def test_fenwick_events_are_goals_shots_and_misses():
    """The public set is the one the package counts with, and it can't be changed."""
    from chickenstats.chicken_nhl._game_utils import FENWICK_EVENTS as internal

    assert FENWICK_EVENTS == internal == {"GOAL", "SHOT", "MISS"}
    assert isinstance(FENWICK_EVENTS, frozenset)


def test_scraped_xg_fields_match_the_play_by_play(fixture_game, shootout_game):
    """One xg_fields row per Fenwick attempt, with the shootout attempts left out."""
    for game in (fixture_game, shootout_game):
        assert_xg_fields_match(game.play_by_play, game.xg_fields, what="saved game")
    assert_xg_fields_match(fixture_game.play_by_play.to_pandas(), fixture_game.xg_fields.to_pandas(), what="saved game")
    attempts = shootout_game.play_by_play.filter(pl.col("shootout_attempt") == 1)
    assert attempts.height and attempts.join(shootout_game.xg_fields, on=["game_id", "event_idx"]).is_empty()


def test_a_missing_xg_fields_row_raises(fixture_game):
    with pytest.raises(InvalidInputError, match="1 Fenwick attempts without an xg_fields row"):
        assert_xg_fields_match(fixture_game.play_by_play, fixture_game.xg_fields.slice(1), what="rows")


def test_an_xg_fields_row_for_a_shootout_attempt_raises(fixture_game, shootout_game):
    """A row for an event with fenwick 0 is an extra row."""
    attempt = shootout_game.play_by_play.filter(pl.col("shootout_attempt") == 1).head(1).select("game_id", "event_idx")
    xg = pl.concat([shootout_game.xg_fields.select("game_id", "event_idx"), attempt])

    with pytest.raises(InvalidInputError, match="1 xg_fields rows without a Fenwick attempt"):
        assert_xg_fields_match(shootout_game.play_by_play, xg, what="rows")


def test_a_repeated_xg_fields_row_raises(fixture_game):
    xg = pl.concat([fixture_game.xg_fields, fixture_game.xg_fields.head(1)])

    with pytest.raises(InvalidInputError, match="appear more than once"):
        assert_xg_fields_match(fixture_game.play_by_play, xg, what="rows")
