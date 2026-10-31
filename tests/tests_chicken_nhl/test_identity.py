import itertools

import pytest

from chickenstats.chicken_nhl import prep_lines, prep_stats, prep_team_stats
from chickenstats.chicken_nhl._agg_constants import build_group_list
from chickenstats.chicken_nhl.identity import identity_columns
from chickenstats.exceptions import InvalidInputError


# -----------------------------------------------------------------------------
# identity_columns
# -----------------------------------------------------------------------------


class TestFrames:
    def test_stats_identifies_a_player_in_a_game_state(self):
        cols = identity_columns("stats", level="period")
        for expected in ("season", "game_id", "api_id", "team", "opp_team", "period"):
            assert expected in cols

    def test_lines_is_stats_without_the_player(self):
        stats = identity_columns("stats", teammates=True)
        lines = identity_columns("lines", teammates=True)
        assert "api_id" in stats
        assert "api_id" not in lines
        assert set(lines) < set(stats)

    def test_team_stats_has_no_lineup_detail(self):
        cols = identity_columns("team_stats")
        assert not [c for c in cols if "forwards" in c or "defense" in c]
        # ...but must still separate the two teams in a game.
        assert "team" in cols and "opp_team" in cols

    def test_unknown_frame_is_rejected(self):
        with pytest.raises(InvalidInputError, match="frame must be one of"):
            identity_columns("skaters")  # ty: ignore[invalid-argument-type]

    @pytest.mark.parametrize(
        "kwargs,message",
        [
            ({"lineup_ids": "id"}, "lineup_ids must be"),
            ({"position": "F"}, "position must be 'f' or 'd'"),
            ({"score": "yes"}, "score must be True or False"),
        ],
    )
    def test_unknown_arguments_are_rejected(self, kwargs, message):
        """A bad lineup_ids or position gave a key with no lineup or the wrong one, and a string flag split by it."""
        with pytest.raises(InvalidInputError, match=message):
            identity_columns("lines", **kwargs)


class TestTracksTheAggregation:
    """The identity has to describe the frame it was aggregated with."""

    def test_no_lineup_split_means_no_lineup_columns(self):
        cols = identity_columns("stats", teammates=False, opposition=False)
        assert not [c for c in cols if "forwards" in c]

    def test_period_level_adds_period_over_game_level(self):
        game = identity_columns("stats", level="game")
        period = identity_columns("stats", level="period")
        assert "period" not in game
        assert "period" in period

    def test_state_splits_are_reflected(self):
        cols = identity_columns("stats", strength_state=False, score=False)
        assert "strength_state" not in cols and "score_state" not in cols

    def test_derived_from_build_group_list(self):
        """Guards the point of the module: this must not drift from grouping.

        Everything identity_columns returns must be something the aggregation
        actually groups by -- otherwise the identity describes a frame that
        prep_stats never produces.
        """
        grouped = build_group_list(
            ["season", "session", "team", "api_id", "position"],
            level="period",
            strength_state=True,
            score=True,
            teammates=True,
            opposition=True,
        )
        assert set(identity_columns("stats", level="period")) <= set(grouped)


class TestLineupIds:
    @pytest.mark.parametrize(
        "flavour,expected", [("api_id", "forwards_api_id"), ("eh_id", "forwards_eh_id"), ("name", "forwards")]
    )
    def test_one_flavour_at_a_time(self, flavour, expected):
        cols = identity_columns("stats", teammates=True, lineup_ids=flavour)
        forwards = [c for c in cols if c.startswith("forwards")]
        assert forwards == [expected], (
            "the three lineup flavours name the same skaters, so an identity using more than one is redundant"
        )

    def test_api_id_is_the_default(self):
        assert identity_columns("stats") == identity_columns("stats", lineup_ids="api_id")


class TestDeterminism:
    def test_stable_across_calls(self):
        assert identity_columns("stats") == identity_columns("stats")

    def test_no_duplicates(self):
        cols = identity_columns("stats", level="period")
        assert len(cols) == len(set(cols))

    def test_game_date_excluded_as_functionally_dependent(self):
        """game_date is grouped on but adds nothing game_id has not already."""
        assert "game_date" not in identity_columns("stats", level="period")
        assert "game_id" in identity_columns("stats", level="period")


# -----------------------------------------------------------------------------
# Against real output
# -----------------------------------------------------------------------------

FLAGS = list(itertools.product(["season", "game", "period"], [False, True], [False, True]))


@pytest.mark.parametrize("level, strength_state, score", FLAGS)
def test_is_a_key_of_team_stats(fixture_game, level, strength_state, score):
    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext
    for opposition in (False, True):
        df = prep_team_stats(
            pbp, pbp_ext, level=level, strength_state=strength_state, score=score, opposition=opposition
        )
        key = identity_columns(
            "team_stats", level=level, strength_state=strength_state, score=score, opposition=opposition
        )

        assert set(key) <= set(df.columns), (opposition, key)
        assert df.select(key).n_unique() == df.height, opposition


# Each case builds stats and both kinds of lines four times, so only the coarsest and the finest splits are run
@pytest.mark.parametrize("level, strength_state, score", [("season", True, False), ("period", True, True)])
def test_is_a_key_of_lines_and_stats(fixture_game, level, strength_state, score):
    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext
    for teammates, opposition in itertools.product((False, True), (False, True)):
        flags = (level, strength_state, score, teammates, opposition)
        stats = prep_stats(
            pbp,
            pbp_ext,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )
        key = identity_columns(
            "stats", level=level, strength_state=strength_state, score=score, teammates=teammates, opposition=opposition
        )
        assert set(key) <= set(stats.columns), ("stats", flags)
        assert stats.select(key).n_unique() == stats.height, ("stats", flags)

        for position in ("f", "d"):
            lines = prep_lines(
                pbp,
                pbp_ext,
                position=position,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )
            key = identity_columns(
                "lines",
                position=position,
                level=level,
                strength_state=strength_state,
                score=score,
                teammates=teammates,
                opposition=opposition,
            )
            assert set(key) <= set(lines.columns), ("lines", position, flags)
            assert lines.select(key).n_unique() == lines.height, ("lines", position, flags)


def test_the_defaults_name_a_key_of_each_default_output(fixture_game):
    """With no flags, identity_columns describes what prep_stats, prep_lines and prep_team_stats return by default (R90)."""
    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext
    outputs = [
        (prep_stats(pbp, pbp_ext), identity_columns("stats")),
        (prep_lines(pbp, pbp_ext), identity_columns("lines")),
        (prep_team_stats(pbp, pbp_ext), identity_columns("team_stats")),
    ]

    for df, key in outputs:
        assert set(key) <= set(df.columns), key
        assert df.select(key).n_unique() == df.height, key
