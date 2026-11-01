"""Tests for chickenstats.chicken_nhl.contract against the saved games."""

import polars as pl

from chickenstats.chicken_nhl.contract import EVENT_SORT_ORDER, PBP_ORDER_COLUMNS, STRENGTH_STATES


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
