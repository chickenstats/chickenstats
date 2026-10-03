import pytest

from chickenstats.chicken_nhl._agg_constants import build_group_list
from chickenstats.chicken_nhl.identity import identity_columns


# -----------------------------------------------------------------------------
# identity_columns
# -----------------------------------------------------------------------------


class TestFrames:
    def test_stats_identifies_a_player_in_a_game_state(self):
        cols = identity_columns("stats", level="period")
        for expected in ("season", "game_id", "api_id", "team", "opp_team", "period"):
            assert expected in cols

    def test_lines_is_stats_without_the_player(self):
        stats = identity_columns("stats")
        lines = identity_columns("lines")
        assert "api_id" in stats
        assert "api_id" not in lines
        assert set(lines) < set(stats)

    def test_team_stats_has_no_lineup_detail(self):
        cols = identity_columns("team_stats")
        assert not [c for c in cols if "forwards" in c or "defense" in c]
        # ...but must still separate the two teams in a game.
        assert "team" in cols and "opp_team" in cols

    def test_unknown_frame_is_rejected(self):
        with pytest.raises(ValueError, match="frame must be one of"):
            identity_columns("skaters")  # ty: ignore[invalid-argument-type]


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
            ["season", "session", "team", "api_id"],
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
        cols = identity_columns("stats", lineup_ids=flavour)
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
