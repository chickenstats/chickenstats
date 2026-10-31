import polars as pl
import pytest

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl._agg_constants import build_group_list, STINT_LINEUP_COLS
from chickenstats.chicken_nhl._aggregation import (
    _prep_oi_percent,
    _prep_p60,
    prep_ind,
    prep_lines,
    prep_oi,
    prep_rolling_stats,
    prep_stints,
    prep_team_stats,
)
from chickenstats.chicken_nhl import Scraper, prep_stats
from chickenstats.chicken_nhl.identity import identity_columns
from chickenstats.exceptions import InvalidInputError

_skip_no_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")


# -----------------------------------------------------------------------------
# prep_oi
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def game_pbp():
    scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
    return scraper.play_by_play, scraper.play_by_play_ext


class TestPrepOi:
    """prep_oi combines "for" (event_on), "against" (opp_on), and zone-start (change_on)
    perspectives across 21 lineup-slot columns into one row per player. These tests cover
    the deferred-aggregation rewrite (concat-then-single-group_by per category instead of
    a redundant per-slot group_by) added to reduce ~24 full-frame group_by calls to ~6.
    """

    @pytest.mark.parametrize(
        "level,strength_state,score,teammates,opposition",
        [
            ("game", True, False, False, False),
            ("period", True, True, False, False),
            ("session", False, False, True, False),
            ("season", True, False, False, True),
        ],
    )
    def test_runs_without_error_and_has_expected_columns(
        self, game_pbp, level, strength_state, score, teammates, opposition
    ):
        pbp, pbp_ext = game_pbp
        result = prep_oi(
            pbp,
            pbp_ext,
            level=level,
            strength_state=strength_state,
            score=score,
            teammates=teammates,
            opposition=opposition,
        )
        assert len(result) > 0
        for col in ("player", "eh_id", "team", "toi", "gf", "ga", "sf", "sa", "cf", "ca", "give", "take"):
            assert col in result.columns

    def test_toi_and_counts_are_non_negative(self, game_pbp):
        pbp, pbp_ext = game_pbp
        result = prep_oi(pbp, pbp_ext, level="game")
        for col in ("toi", "gf", "ga", "sf", "sa", "cf", "ca", "give", "take"):
            assert (result[col] >= 0).all()


# -----------------------------------------------------------------------------
# _prep_p60
# -----------------------------------------------------------------------------


class TestPrepP60:
    def test_polars_adds_p60_column(self):
        df = pl.DataFrame({"toi": [60.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal"])
        assert "goal_p60" in result.columns

    def test_polars_p60_value(self):
        df = pl.DataFrame({"toi": [60.0], "goal": [2.0]})
        result = _prep_p60(df, stats=["goal"])
        assert result["goal_p60"][0] == pytest.approx(2.0)  # (2/60)*60 = 2

    def test_no_ice_time_gives_null(self):
        """A row with an event but no ice time has a null rate, not an infinite one."""
        df = pl.DataFrame({"toi": [0.0, 0.0], "goal": [1.0, 0.0]})
        result = _prep_p60(df, stats=["goal"])
        assert result["goal_p60"].to_list() == [None, None]

    @_skip_no_pandas
    def test_pandas_adds_p60_column(self):
        df = pd.DataFrame({"toi": [60.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal"])
        assert "goal_p60" in result.columns

    @_skip_no_pandas
    def test_pandas_p60_value(self):
        df = pd.DataFrame({"toi": [30.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal"])
        assert result["goal_p60"].iloc[0] == pytest.approx(2.0)  # (1/30)*60 = 2

    def test_missing_stat_column_skipped(self):
        """Stats not present in the DataFrame should be silently skipped."""
        df = pl.DataFrame({"toi": [60.0]})
        result = _prep_p60(df, stats=["goal"])
        assert "goal_p60" not in result.columns

    def test_multiple_stats(self):
        df = pl.DataFrame({"toi": [60.0], "goal": [1.0], "shot": [5.0]})
        result = _prep_p60(df, stats=["goal", "shot"])
        assert "goal_p60" in result.columns
        assert "shot_p60" in result.columns

    def test_partial_stats_present(self):
        """Only stats that exist in the DataFrame get a _p60 column."""
        df = pl.DataFrame({"toi": [60.0], "goal": [1.0]})
        result = _prep_p60(df, stats=["goal", "shot"])
        assert "goal_p60" in result.columns
        assert "shot_p60" not in result.columns


# -----------------------------------------------------------------------------
# _prep_oi_percent
# -----------------------------------------------------------------------------


class TestPrepOiPercent:
    def test_polars_computes_percent(self):
        df = pl.DataFrame({"xgf": [2.0], "xga": [2.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"][0] == pytest.approx(0.5)

    @_skip_no_pandas
    def test_pandas_computes_percent(self):
        df = pd.DataFrame({"xgf": [3.0], "xga": [1.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert "xgf_percent" in result.columns
        assert result["xgf_percent"].iloc[0] == pytest.approx(0.75)

    @pytest.mark.parametrize("present", ["xgf", "xga"])
    def test_missing_column_gives_no_percent(self, present):
        """When either side is absent from the DataFrame there is no percent column."""
        df = pl.DataFrame({present: [2.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert result.columns == [present]

    def test_multiple_stats(self):
        df = pl.DataFrame({"xgf": [1.0], "xga": [1.0], "cf": [3.0], "ca": [1.0]})
        result = _prep_oi_percent(df, stats_for=["xgf", "cf"], stats_against=["xga", "ca"])
        assert "xgf_percent" in result.columns
        assert "cf_percent" in result.columns
        assert result["cf_percent"][0] == pytest.approx(0.75)

    def test_zero_for_zero_gives_null(self):
        """When both sides are zero the percent is null, not 0.0 or NaN."""
        df = pl.DataFrame({"xgf": [0.0, 0.0], "xga": [0.0, 1.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert result["xgf_percent"].to_list() == [None, 0.0]

    @_skip_no_pandas
    def test_zero_for_zero_gives_null_pandas(self):
        df = pd.DataFrame({"xgf": [0.0], "xga": [0.0]})
        result = _prep_oi_percent(df, stats_for=["xgf"], stats_against=["xga"])
        assert pd.isna(result["xgf_percent"].iloc[0])


# -----------------------------------------------------------------------------
# prep_rolling_stats
# -----------------------------------------------------------------------------


class TestPrepRollingStats:
    def test_rates_and_percentages_come_from_rolling_sums(self):
        """A rate is total count over total ice time, so a short game counts for less."""
        df = pl.DataFrame(
            {
                "team": ["A", "A", "A"],
                "game_id": [1, 2, 3],
                "toi": [60.0, 0.0, 6.0],
                "gf": [2, 0, 1],
                "ga": [1, 0, 0],
                "gf_p60": [2.0, None, 10.0],
                "gf_percent": [2 / 3, None, 1.0],
            }
        )
        result = prep_rolling_stats(df, window=3)

        assert result["rolling_gf_p60"].to_list() == pytest.approx([2.0, 2.0, 3 / 66 * 60])
        assert result["rolling_gf_percent"].to_list() == pytest.approx([2 / 3, 2 / 3, 3 / 4])

    def test_nothing_to_divide_by_gives_null(self):
        df = pl.DataFrame(
            {"team": ["A"], "game_id": [1], "toi": [0.0], "gf": [0], "ga": [0], "gf_p60": [None], "gf_percent": [None]},
            schema_overrides={"gf_p60": pl.Float64, "gf_percent": pl.Float64},
        )
        result = prep_rolling_stats(df, window=3)

        assert result.select("rolling_gf_p60", "rolling_gf_percent").row(0) == (None, None)

    def test_defaults_to_p60_and_percent_columns(self):
        df = pl.DataFrame(
            {
                "player": ["A", "A", "A"],
                "eh_id": ["A.A", "A.A", "A.A"],
                "game_id": [1, 2, 3],
                "cf_p60": [10.0, 20.0, 30.0],
                "cf_percent": [0.4, 0.5, 0.6],
                "toi": [15.0, 16.0, 17.0],
            }
        )
        result = prep_rolling_stats(df, window=2)
        assert "rolling_cf_p60" in result.columns
        assert "rolling_cf_percent" in result.columns
        assert "rolling_toi" not in result.columns

    def test_explicit_stats_list(self):
        df = pl.DataFrame({"team": ["NSH", "NSH", "NSH"], "game_id": [1, 2, 3], "toi": [60.0, 61.0, 59.0]})
        result = prep_rolling_stats(df, window=2, stats=["toi"], group_cols=["team"])
        assert "rolling_toi" in result.columns

    def test_rolling_mean_value(self):
        """A trailing 2-game window's mean matches a manual computation, sorted by game_id."""
        df = pl.DataFrame({"team": ["NSH", "NSH", "NSH"], "game_id": [3, 1, 2], "cf_p60": [30.0, 10.0, 20.0]})
        result = prep_rolling_stats(df, window=2, stats=["cf_p60"], group_cols=["team"], min_periods=1)
        result = result.sort("game_id")
        assert result["rolling_cf_p60"].to_list() == pytest.approx([10.0, 15.0, 25.0])

    def test_groups_are_independent(self):
        """Rolling windows don't leak across different group_cols entities."""
        df = pl.DataFrame(
            {"team": ["NSH", "NSH", "TBL", "TBL"], "game_id": [1, 2, 1, 2], "cf_p60": [10.0, 20.0, 100.0, 200.0]}
        )
        result = prep_rolling_stats(df, window=2, stats=["cf_p60"], group_cols=["team"])
        result = result.sort(["team", "game_id"])
        assert result.filter(pl.col("team") == "NSH")["rolling_cf_p60"].to_list() == pytest.approx([10.0, 15.0])
        assert result.filter(pl.col("team") == "TBL")["rolling_cf_p60"].to_list() == pytest.approx([100.0, 150.0])

    def test_min_periods_respected(self):
        """With min_periods above the available history, early rows are null."""
        df = pl.DataFrame({"team": ["NSH", "NSH", "NSH"], "game_id": [1, 2, 3], "cf_p60": [10.0, 20.0, 30.0]})
        result = prep_rolling_stats(df, window=3, stats=["cf_p60"], group_cols=["team"], min_periods=3)
        result = result.sort("game_id")
        assert result["rolling_cf_p60"][0] is None
        assert result["rolling_cf_p60"][1] is None
        assert result["rolling_cf_p60"][2] == pytest.approx(20.0)

    def test_missing_stat_column_skipped(self):
        df = pl.DataFrame({"team": ["NSH"], "game_id": [1], "cf_p60": [10.0]})
        result = prep_rolling_stats(df, stats=["cf_p60", "xgf_p60"], group_cols=["team"])
        assert "rolling_cf_p60" in result.columns
        assert "rolling_xgf_p60" not in result.columns

    def test_no_matching_stats_returns_unchanged(self):
        df = pl.DataFrame({"team": ["NSH"], "game_id": [1], "toi": [60.0]})
        result = prep_rolling_stats(df, stats=["xgf_p60"], group_cols=["team"])
        assert result.columns == df.columns

    def test_defaults_to_player_eh_id_grouping_when_present(self):
        df = pl.DataFrame({"player": ["A", "B"], "eh_id": ["A.A", "B.B"], "game_id": [1, 1], "cf_p60": [10.0, 20.0]})
        result = prep_rolling_stats(df, stats=["cf_p60"])
        assert result["rolling_cf_p60"].to_list() == pytest.approx([10.0, 20.0])

    def test_raises_without_game_id_or_game_date(self):
        """level='session'/'season' output has no per-game granularity to roll over."""
        df = pl.DataFrame({"team": ["NSH"], "cf_p60": [10.0]})
        with pytest.raises(InvalidInputError):
            prep_rolling_stats(df, group_cols=["team"])

    def test_two_games_on_one_date_are_two_games(self):
        """A split-squad preseason day has two games for one team on one date (bB-06)."""
        df = pl.DataFrame(
            {
                "team": ["NSH", "NSH", "NSH"],
                "game_date": ["2023-09-25", "2023-09-25", "2023-09-23"],
                "game_id": [2023010012, 2023010011, 2023010003],
                "cf_p60": [30.0, 20.0, 10.0],
            }
        )
        result = prep_rolling_stats(df, window=2, stats=["cf_p60"], group_cols=["team"])

        assert result["game_id"].to_list() == [2023010003, 2023010011, 2023010012]
        assert result["rolling_cf_p60"].to_list() == pytest.approx([10.0, 15.0, 25.0])

    def test_raises_with_duplicate_period_rows(self):
        """level='period' output has multiple rows per game, not meaningful to roll."""
        df = pl.DataFrame({"team": ["NSH", "NSH"], "game_id": [1, 1], "period": [1, 2], "cf_p60": [10.0, 5.0]})
        with pytest.raises(InvalidInputError):
            prep_rolling_stats(df, group_cols=["team"])

    def test_raises_with_unfiltered_strength_state_splits(self):
        """Default prep_stats(level='game') output splits by strength_state, producing
        multiple rows per game per player — must raise rather than silently mix them."""
        df = pl.DataFrame(
            {
                "player": ["A", "A"],
                "eh_id": ["A.A", "A.A"],
                "game_id": [1, 1],
                "strength_state": ["5v5", "5v4"],
                "cf_p60": [10.0, 20.0],
            }
        )
        with pytest.raises(InvalidInputError):
            prep_rolling_stats(df)


# -----------------------------------------------------------------------------
# build_group_list
# -----------------------------------------------------------------------------


class TestBuildGroupList:
    def test_returns_list(self):
        result = build_group_list(["season", "game_id"])
        assert isinstance(result, list)

    def test_deduplicates(self):
        """Columns added more than once appear only once in the output."""
        result = build_group_list(["season", "season", "game_id"])
        assert result.count("season") == 1

    def test_canonical_order(self):
        """Columns present in _CANONICAL_ORDER are sorted into canonical order."""
        result = build_group_list(["game_id", "season"])
        assert result.index("season") < result.index("game_id")

    def test_level_game_adds_columns(self):
        result = build_group_list(["season"], level="game")
        assert "game_id" in result
        assert "opp_team" in result

    def test_level_period_adds_period(self):
        result = build_group_list(["season"], level="period")
        assert "period" in result

    def test_strength_state(self):
        result = build_group_list(["season"], strength_state=True)
        assert "strength_state" in result

    def test_opp_strength_state(self):
        result = build_group_list(["season"], opp_strength_state=True)
        assert "opp_strength_state" in result

    def test_filter_to_drops_absent_columns(self):
        df = pl.DataFrame({"season": [1], "game_id": [1]})
        result = [c for c in build_group_list(["season", "game_id", "opp_team"]) if c in df.columns]
        assert "season" in result
        assert "game_id" in result
        assert "opp_team" not in result

    def test_filter_to_only_returns_present_columns(self):
        df = pl.DataFrame({"season": [1]})
        result = [c for c in build_group_list(["season", "game_id"]) if c in df.columns]
        assert all(c in df.columns for c in result)


# -----------------------------------------------------------------------------
# prep_stints
# -----------------------------------------------------------------------------


_HOME_5 = ["1", "2", "3", "4", "99"]
_AWAY_5 = ["6", "7", "8", "9", "88"]
_HOME_6 = ["1", "2", "3", "4", "5", "99"]
_AWAY_4 = ["6", "7", "8", "88"]


def _stint_event(**overrides) -> dict:
    """Return a fresh play-by-play row shaped the way prep_stints expects."""
    row = {
        "season": 20222023,
        "session": "R",
        "game_id": 2022020001,
        "game_date": "2022-10-15",
        "period": 1,
        "event_idx": 1,
        "home_team": "TOR",
        "away_team": "MTL",
        "home_score_diff": 0,
        "shootout_attempt": 0,
        "home_goalie_api_id": ["99"],
        "away_goalie_api_id": ["88"],
        "home_on_api_id": _HOME_5,
        "away_on_api_id": _AWAY_5,
        "event": "SHOT",
        "event_team": "TOR",
        "event_length": 5,
        "zone_start": "OTF",
        "strength_state": "5v5",
        "shot": 0,
        "fenwick": 0,
        "block": 0,
        "teammate_block": 0,
        "goal": 0,
    }
    row.update(overrides)

    # Mirrors the flag columns _game_pbp.py builds.
    event = row["event"]
    if event in ("SHOT", "GOAL"):
        row["shot"], row["fenwick"] = 1, 1
    if event == "GOAL":
        row["goal"] = 1
    if event == "MISS":
        row["fenwick"] = 1
    if event == "BLOCK":
        row["block"] = 1
    return row


@pytest.fixture
def stint_pbp():
    """One game: an even-strength stint and a 5v4 with home on the power play."""
    rows = [
        _stint_event(event_idx=1, event="FAC", event_length=2, zone_start="NEU", pred_goal=None),
        _stint_event(event_idx=2, event_length=3, zone_start="OFF", pred_goal=0.06, base_xg=0.05),
        # MTL blocked a TOR attempt -- event_team is the blocking team.
        _stint_event(event_idx=3, event="BLOCK", event_team="MTL", event_length=1, pred_goal=None, base_xg=None),
        _stint_event(
            event_idx=4, event="GOAL", event_team="MTL", event_length=4, zone_start="DEF", pred_goal=0.12, base_xg=0.09
        ),
        _stint_event(
            event_idx=5,
            home_on_api_id=_HOME_6,
            away_on_api_id=_AWAY_4,
            zone_start="OFF",
            strength_state="5v4",
            pred_goal=0.08,
            base_xg=0.06,
        ),
    ]
    return pl.DataFrame(rows)


class TestPrepStints:
    """prep_stints collapses play-by-play into stints -- contiguous runs where neither
    team's on-ice group changed."""

    def test_splits_even_strength_and_power_play_stints(self, stint_pbp):
        stints = prep_stints(stint_pbp)

        assert stints.height == 2

        ev = stints.filter(pl.col("strength_state") == "5v5")
        pp = stints.filter(pl.col("strength_state") == "5v4")

        assert ev.height == 1
        assert pp.height == 1
        assert ev["home_skater_count"].item() == 4
        assert ev["away_skater_count"].item() == 4
        assert pp["home_skater_count"].item() == 5
        assert pp["away_skater_count"].item() == 3

        assert ev["toi"].item() == 10
        assert pp["toi"].item() == 5

    def test_goalies_split_out_of_skaters(self, stint_pbp):
        stints = prep_stints(stint_pbp)
        ev = stints.filter(pl.col("strength_state") == "5v5")

        assert ev["home_goalies"].item().to_list() == ["99"]
        assert ev["away_goalies"].item().to_list() == ["88"]
        assert "99" not in ev["home_skaters"].item().to_list()
        assert "88" not in ev["away_skaters"].item().to_list()

    def test_block_credits_the_shooting_team(self, stint_pbp):
        """MTL blocking a TOR attempt is Corsi *for* TOR, not for MTL."""
        ev = prep_stints(stint_pbp).filter(pl.col("strength_state") == "5v5")

        # TOR: one SHOT (fenwick) + one attempt MTL blocked.
        assert ev["home_ff"].item() == 1
        assert ev["home_cf"].item() == 2
        # MTL: one GOAL, and nothing of theirs was blocked.
        assert ev["away_ff"].item() == 1
        assert ev["away_cf"].item() == 1

    def test_counting_stats_nest(self, stint_pbp):
        stints = prep_stints(stint_pbp)
        for venue in ("home", "away"):
            assert (stints[f"{venue}_sf"] <= stints[f"{venue}_ff"]).all()
            assert (stints[f"{venue}_ff"] <= stints[f"{venue}_cf"]).all()
            assert (stints[f"{venue}_gf"] <= stints[f"{venue}_sf"]).all()

    def test_reconciles_with_prep_team_stats(self, game_pbp):
        """Stint totals must match team_stats over the same events.

        Penalty shots and shootout attempts (1v0) are excluded from the comparison: they
        have one skater on ice, so prep_stints leaves them out while prep_team_stats counts
        penalty shots.
        """
        pbp, pbp_ext = game_pbp
        pbp = pbp.filter(pl.col("strength_state") != "1v0")
        stints = prep_stints(pbp)
        team_stats = prep_team_stats(pbp, pbp_ext, level="game", strength_state=False)

        home, away = pbp["home_team"][0], pbp["away_team"][0]
        for team, venue in ((home, "home"), (away, "away")):
            row = team_stats.filter(pl.col("team") == team)
            for stat in ("sf", "ff", "cf", "gf"):
                assert stints[f"{venue}_{stat}"].sum() == row[stat].item(), f"{team} {stat} mismatch"

        # TOI is seconds in stints, minutes in team_stats.
        assert stints["toi"].sum() / 60 == pytest.approx(team_stats.filter(pl.col("team") == home)["toi"].item())

    def test_for_and_against_are_the_same_rows(self, game_pbp):
        """The schema is keyed on venue, so home_sa is away_sf -- no separate columns."""
        pbp, _ = game_pbp
        pbp = pbp.filter(pl.col("period") < 5)
        stints = prep_stints(pbp)
        team_stats = prep_team_stats(pbp, level="game", strength_state=False)

        home = pbp["home_team"][0]
        row = team_stats.filter(pl.col("team") == home)
        for against, venue_for in (("sa", "away_sf"), ("fa", "away_ff"), ("ca", "away_cf"), ("ga", "away_gf")):
            assert stints[venue_for].sum() == row[against].item(), f"{against} mismatch"

    def test_xg_columns_are_conditional(self, stint_pbp):
        with_xg = prep_stints(stint_pbp)
        assert "home_xgf" in with_xg.columns
        assert "home_base_xgf" in with_xg.columns
        # delta needs both base and context; only base is present here.
        assert "home_delta_xgf" not in with_xg.columns

        without_xg = prep_stints(stint_pbp.drop(["pred_goal", "base_xg"]))
        assert not [col for col in without_xg.columns if col.endswith("xgf")]
        assert without_xg.height == with_xg.height

    def test_delta_xg_derived_from_context_and_base(self, stint_pbp):
        pbp = stint_pbp.with_columns(context_xg=pl.col("pred_goal") * 1.1)
        stints = prep_stints(pbp)

        for row in stints.iter_rows(named=True):
            assert row["home_delta_xgf"] == pytest.approx(row["home_context_xgf"] - row["home_base_xgf"])
            assert row["away_delta_xgf"] == pytest.approx(row["away_context_xgf"] - row["away_base_xgf"])

    def test_xg_sums_split_by_event_team(self, stint_pbp):
        ev = prep_stints(stint_pbp).filter(pl.col("strength_state") == "5v5")
        assert ev["home_xgf"].item() == pytest.approx(0.06)
        assert ev["away_xgf"].item() == pytest.approx(0.12)

    def test_string_lineup_columns_match_list_columns(self, stint_pbp):
        """A parquet round-trip collapses List[String] lineups to comma-space String."""
        as_strings = stint_pbp.with_columns(
            [pl.col(col).list.join(", ") for col in ("home_on_api_id", "away_on_api_id")]
        )
        assert as_strings.schema["home_on_api_id"] == pl.String

        assert prep_stints(as_strings).equals(prep_stints(stint_pbp))

    def test_unsorted_input_produces_the_same_stints(self, stint_pbp):
        shuffled = stint_pbp.sort("event_length", descending=True)
        assert prep_stints(shuffled).equals(prep_stints(stint_pbp))

    def test_min_skaters_filter(self, stint_pbp):
        """A 2-skater side is dropped at the default and kept at min_skaters=2."""
        short_handed = [
            _stint_event(
                event_idx=6,
                home_on_api_id=["1", "2", "99"],
                away_on_api_id=["6", "7", "88"],
                event_length=6,
                strength_state="2v2",
            )
        ]
        pbp = pl.concat([stint_pbp, pl.DataFrame(short_handed)], how="diagonal_relaxed")

        assert prep_stints(pbp).height == 2
        assert prep_stints(pbp, min_skaters=2).height == 3

    def test_back_to_back_flags_follow_game_dates(self):
        """b2b is derived from each team's own schedule within the input."""
        rows = [
            _stint_event(event_idx=idx + 1, game_id=game_id, game_date=game_date)
            for idx, (game_id, game_date) in enumerate([(2022020001, "2022-10-15"), (2022020002, "2022-10-16")])
        ]
        stints = prep_stints(pl.DataFrame(rows))

        first = stints.filter(pl.col("game_id") == 2022020001)
        second = stints.filter(pl.col("game_id") == 2022020002)
        assert first["home_b2b"].item() is False
        assert first["away_b2b"].item() is False
        # Both teams played the day before.
        assert second["home_b2b"].item() is True
        assert second["away_b2b"].item() is True

    def test_no_back_to_back_when_games_are_days_apart(self):
        rows = [
            _stint_event(event_idx=1, game_id=2022020001, game_date="2022-10-15"),
            _stint_event(event_idx=2, game_id=2022020002, game_date="2022-10-18"),
        ]
        stints = prep_stints(pl.DataFrame(rows))
        assert not stints["home_b2b"].any()
        assert not stints["away_b2b"].any()

    def test_ordering_follows_game_date_not_game_id(self):
        """A postponed game keeps its original ID, so IDs aren't reliably chronological."""
        rows = [
            # The LOWER game_id happens LATER.
            _stint_event(event_idx=1, game_id=2022020001, game_date="2022-10-20"),
            _stint_event(event_idx=2, game_id=2022020009, game_date="2022-10-19"),
        ]
        stints = prep_stints(pl.DataFrame(rows))

        assert stints["game_date"].to_list() == ["2022-10-19", "2022-10-20"]
        assert stints["game_id"].to_list() == [2022020009, 2022020001]
        # b2b follows the dates: the 10-20 game is the back-to-back, not the lower ID.
        assert stints.filter(pl.col("game_date") == "2022-10-20")["home_b2b"].item() is True
        assert stints.filter(pl.col("game_date") == "2022-10-19")["home_b2b"].item() is False

    def test_zero_length_stints_dropped(self, stint_pbp):
        zero = pl.DataFrame([_stint_event(event_idx=9, event="STOP", event_length=0, strength_state="4v4")])
        pbp = pl.concat([stint_pbp, zero], how="diagonal_relaxed")
        assert "4v4" not in prep_stints(pbp)["strength_state"].to_list()

    def test_score_state_buckets(self, stint_pbp):
        pbp = stint_pbp.with_columns(home_score_diff=pl.lit(4, dtype=pl.Int64))
        stints = prep_stints(pbp)

        assert stints["home_score_7"].unique().to_list() == [3]
        assert stints["home_score_3"].unique().to_list() == [1]
        assert stints["away_score_7"].unique().to_list() == [-3]
        assert stints["away_score_3"].unique().to_list() == [-1]

    def test_missing_columns_raise(self, stint_pbp):
        with pytest.raises(InvalidInputError, match="missing required play-by-play columns"):
            prep_stints(stint_pbp.drop("strength_state"))

    def test_shootout_attempts_are_excluded(self):
        """Shootout events carry no on-ice lineup, so they can't be attributed to one."""
        shootout = _stint_event(
            event_idx=9,
            period=5,
            event_length=0,
            strength_state="1v0",
            home_on_api_id=None,
            away_on_api_id=None,
            home_goalie_api_id=None,
            away_goalie_api_id=None,
        )
        # Real play-by-play carries these as String, null on non-play events.
        pbp = pl.DataFrame([shootout], schema_overrides={col: pl.String for col in STINT_LINEUP_COLS})
        assert prep_stints(pbp).height == 0

    def test_runs_on_real_play_by_play(self, game_pbp):
        pbp, _ = game_pbp
        stints = prep_stints(pbp)

        assert stints.height > 0
        assert (stints["toi"] > 0).all()
        assert (stints["home_skater_count"] >= 3).all()
        assert (stints["away_skater_count"] >= 3).all()
        assert (stints["stint_id"] >= 1).all()


# -----------------------------------------------------------------------------
# Corsi for/against symmetry across prep_oi, prep_lines, prep_team_stats
# -----------------------------------------------------------------------------


class TestCorsiSymmetry:
    """A team's Corsi against must equal its opponent's Corsi for. Corsi is assembled
    from three flags -- ``fenwick``, ``block`` (credited to the blocking team), and
    ``teammate_block`` (credited to the shooting team) -- which is what previously made
    prep_oi, prep_lines, and prep_team_stats disagree with each other.
    """

    def test_team_stats_ca_equals_opponent_cf(self, game_pbp):
        pbp, pbp_ext = game_pbp
        team_stats = prep_team_stats(pbp, pbp_ext, level="game", strength_state=False)

        home, away = pbp["home_team"][0], pbp["away_team"][0]
        home_row = team_stats.filter(pl.col("team") == home)
        away_row = team_stats.filter(pl.col("team") == away)

        assert home_row["ca"].item() == away_row["cf"].item()
        assert away_row["ca"].item() == home_row["cf"].item()
        assert home_row["ca_adj"].item() == pytest.approx(away_row["cf_adj"].item())
        assert away_row["ca_adj"].item() == pytest.approx(home_row["cf_adj"].item())

    def test_team_stats_blocked_shots_are_mirrored(self, game_pbp):
        """bsf is attempts this team had blocked; bsa is attempts it blocked."""
        pbp, pbp_ext = game_pbp
        team_stats = prep_team_stats(pbp, pbp_ext, level="game", strength_state=False)

        home, away = pbp["home_team"][0], pbp["away_team"][0]
        home_row = team_stats.filter(pl.col("team") == home)
        away_row = team_stats.filter(pl.col("team") == away)

        assert home_row["bsf"].item() == away_row["bsa"].item()
        assert away_row["bsf"].item() == home_row["bsa"].item()

    def test_lines_agree_with_team_stats_orientation(self, game_pbp):
        """prep_lines used to map a line's own BLOCK events to bsf, inverting cf/ca."""
        pbp, pbp_ext = game_pbp
        lines = prep_lines(pbp, pbp_ext, position="f", level="game", strength_state=False)
        team_stats = prep_team_stats(pbp, pbp_ext, level="game", strength_state=False)

        line_totals = lines.group_by("team").agg(pl.col("bsf").sum(), pl.col("bsa").sum())
        for team in (pbp["home_team"][0], pbp["away_team"][0]):
            line_row = line_totals.filter(pl.col("team") == team)
            team_row = team_stats.filter(pl.col("team") == team)
            assert line_row["bsf"].item() == team_row["bsf"].item(), f"{team} bsf orientation"
            assert line_row["bsa"].item() == team_row["bsa"].item(), f"{team} bsa orientation"

    def test_oi_cf_includes_blocked_attempts(self, game_pbp):
        """cf used to read bsf in the with_columns that redefined it, dropping the
        opponent-blocked component."""
        pbp, pbp_ext = game_pbp
        oi = prep_oi(pbp, pbp_ext, level="game", strength_state=False)

        skaters = oi.filter(pl.col("position") != "G")
        assert (skaters["cf"] >= skaters["ff"]).all()
        # At least one skater was on for a blocked attempt, so cf must exceed ff.
        assert (skaters["cf"] > skaters["ff"]).any()

    def test_oi_matches_hand_computed_corsi(self, game_pbp):
        """Independent recomputation straight from the play-by-play flags."""
        pbp, _pbp_ext = game_pbp
        oi = prep_oi(pbp, _pbp_ext, level="game", strength_state=False)

        home = pbp["home_team"][0]
        own = (pl.col("event_team") == home).cast(pl.Int64)
        opp = (pl.col("event_team") != home).cast(pl.Int64)

        skaters = oi.filter((pl.col("team") == home) & (pl.col("position") != "G"))
        assert skaters.height > 0

        for api_id in skaters["api_id"].to_list():
            row = oi.filter(pl.col("api_id") == api_id)
            on_ice = pbp.filter(pl.col("home_on_api_id").str.contains(str(api_id)))
            expected_cf = on_ice.select(
                (pl.col("fenwick") * own + pl.col("block") * opp + pl.col("teammate_block") * own).sum()
            ).item()
            expected_ca = on_ice.select(
                (pl.col("fenwick") * opp + pl.col("block") * own + pl.col("teammate_block") * opp).sum()
            ).item()

            assert row["cf"].item() == expected_cf, f"{row['player'].item()} cf"
            assert row["ca"].item() == expected_ca, f"{row['player'].item()} ca"


# -----------------------------------------------------------------------------
# Required play-by-play columns
# -----------------------------------------------------------------------------

PREP_FUNCTIONS = [prep_ind, prep_oi, prep_lines, prep_team_stats]


class TestRequiredColumns:
    """A missing count column gave plausible zeros, such as sf 342 becoming 0, with no warning (bB-01)."""

    @pytest.mark.parametrize("prep", PREP_FUNCTIONS, ids=lambda f: f.__name__)
    def test_a_missing_count_column_raises(self, game_pbp, prep):
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match=f"{prep.__name__} is missing required play-by-play columns"):
            prep(pbp.drop("shot"))

    @pytest.mark.parametrize("prep", PREP_FUNCTIONS, ids=lambda f: f.__name__)
    def test_play_by_play_from_1_8_raises(self, game_pbp, prep):
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match=f"{prep.__name__} needs play-by-play from chickenstats 1.9"):
            prep(pbp.drop("shootout_attempt"))

    @pytest.mark.parametrize("prep", PREP_FUNCTIONS, ids=lambda f: f.__name__)
    def test_play_by_play_mixed_with_1_8_rows_raises(self, game_pbp, prep):
        pbp, _ = game_pbp
        mixed = pbp.with_columns(
            pl.when(pl.col("event_idx") > 1).then(pl.col("shootout_attempt")).alias("shootout_attempt")
        )
        with pytest.raises(InvalidInputError, match=f"{prep.__name__} needs play-by-play from chickenstats 1.9"):
            prep(mixed)

    def test_the_output_of_a_prep_function_gets_the_missing_columns_error(self, game_pbp):
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match="is missing required play-by-play columns"):
            prep_ind(pbp.select("season", "game_id"))

    def test_the_error_names_every_missing_column(self, game_pbp):
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match=r"\['shot', 'hit'\]"):
            prep_ind(pbp.drop("shot", "hit"))

    @pytest.mark.parametrize(
        "prep,column",
        [(prep_ind, "forwards"), (prep_oi, "forwards"), (prep_lines, "defense")],
        ids=["ind", "oi", "lines"],
    )
    def test_lineup_columns_are_required_only_for_their_split(self, game_pbp, prep, column):
        pbp, _ = game_pbp
        prep(pbp.drop(column))
        with pytest.raises(InvalidInputError, match=f"'{column}'"):
            prep(pbp.drop(column), teammates=True)

    def test_a_line_needs_its_own_lineup_columns(self, game_pbp):
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match="'forwards'"):
            prep_lines(pbp.drop("forwards"), position="f")

    @pytest.mark.parametrize("prep", [prep_oi, prep_lines, prep_team_stats], ids=lambda f: f.__name__)
    def test_lineup_lists_are_not_required_with_df_ext(self, game_pbp, prep):
        pbp, ext = game_pbp
        prep(pbp.drop("teammates", "opp_team_on", "change_on"), df_ext=ext)


# -----------------------------------------------------------------------------
# Argument checks
# -----------------------------------------------------------------------------


class TestArguments:
    def test_an_unknown_position_raises(self, game_pbp):
        """position='F' raised UnboundLocalError from inside prep_lines (R18, pa-03)."""
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match="position must be 'f' or 'd', got 'F'"):
            prep_lines(pbp, position="F")  # ty: ignore[invalid-argument-type]

    @pytest.mark.parametrize("prep", PREP_FUNCTIONS, ids=lambda f: f.__name__)
    def test_a_flag_that_is_not_a_bool_raises(self, game_pbp, prep):
        """strength_state='no' is truthy, so it split by strength state instead of raising (as-11)."""
        pbp, _ = game_pbp
        with pytest.raises(InvalidInputError, match="strength_state must be True or False, got 'no'"):
            prep(pbp, strength_state="no")


def test_an_all_null_supplied_xg_adjustment_is_filled_from_the_raw_xg(game_pbp):
    """Hosted play-by-play carries base_xg_adj as nulls, and base_xgf_adj summed them to 0.0 (ds-1)."""
    pbp, ext = game_pbp
    with_xg = pbp.with_columns(pred_goal=pl.lit(0.1), base_xg=pl.lit(0.08))
    null_adj = with_xg.with_columns(base_xg_adj=pl.lit(None, dtype=pl.Float64))

    filled = prep_team_stats(null_adj, ext).sort("team", "strength_state")
    computed = prep_team_stats(with_xg, ext).sort("team", "strength_state")

    assert filled["base_xgf_adj"].sum() > 0
    assert filled.equals(computed)


@pytest.mark.parametrize(
    "prep,frame",
    [(prep_stats, "stats"), (prep_lines, "lines"), (prep_team_stats, "team_stats")],
    ids=["stats", "lines", "team_stats"],
)
def test_season_level_combines_the_regular_season_and_playoffs(game_pbp, prep, frame):
    """level='season' gave a regular-season row and a playoff row; it is now one row with both, and no session."""
    pbp, _ = game_pbp
    playoffs = pbp.with_columns(session=pl.lit("P"), game_id=pl.col("game_id") + 10000, id=pl.col("id") + 100_000_000)
    both = pl.concat([pbp, playoffs])

    season = prep(both, level="season")
    by_session = prep(both, level="session")
    key = identity_columns(frame, level="season")
    counts = [c for c in ("toi", "g", "gf", "cf", "ca") if c in season.columns]
    summed = by_session.group_by(key).agg(pl.sum(c) for c in counts).sort(key)

    assert "session" not in season.columns and "session" not in key
    assert season.height == by_session.filter(pl.col("session") == "R").height
    for column in counts:
        assert season.sort(key)[column].to_list() == pytest.approx(summed[column].to_list()), column


class TestPartlyCoveredXg:
    """A season the xG model does not cover has unknown xG, not 0.0, while a covered season keeps its 0s (ds-1)."""

    COVERED, UNCOVERED = 20232024, 20242025

    @pytest.fixture
    def two_seasons(self, game_pbp):
        pbp, _ = game_pbp
        covered = pbp.with_columns(pred_goal=pl.lit(0.1), base_xg=pl.lit(0.08))
        uncovered = pbp.with_columns(
            season=pl.lit(self.UNCOVERED).cast(pbp.schema["season"]),
            game_id=pl.col("game_id") + 1_0000_0000,
            id=pl.col("id") + 1_0000_0000_0000,
            pred_goal=pl.lit(None, dtype=pl.Float64),
            base_xg=pl.lit(None, dtype=pl.Float64),
        )
        return pl.concat([covered, uncovered], how="vertical_relaxed")

    @pytest.mark.parametrize(
        "prep,column",
        [
            (prep_ind, "ixg"),
            (prep_oi, "xgf"),
            (prep_stats, "xgf_p60"),
            (prep_stats, "xgf_percent"),
            (prep_lines, "xgf"),
            (prep_team_stats, "xgf_adj"),
            (prep_team_stats, "base_xgf"),
        ],
    )
    def test_an_uncovered_season_is_null(self, two_seasons, prep, column):
        result = prep(two_seasons).filter(pl.col("season") == self.UNCOVERED)
        assert result.height > 0
        assert result[column].null_count() == result.height

    @pytest.mark.parametrize("prep,column", [(prep_ind, "ixg"), (prep_stats, "ixg"), (prep_stats, "a1_xg")])
    def test_a_covered_season_keeps_its_zeros(self, two_seasons, prep, column):
        covered = prep(two_seasons).filter(pl.col("season") == self.COVERED)

        assert covered[column].null_count() == 0
        assert (covered[column] == 0).any()

    def test_a_shootout_zero_does_not_count_as_coverage(self, two_seasons):
        shootout = two_seasons.with_columns(
            pl.when(pl.col("season") == self.UNCOVERED, pl.col("event_idx") == 1)
            .then(1)
            .otherwise(pl.col("shootout_attempt"))
            .alias("shootout_attempt")
        )
        result = prep_ind(shootout).filter(pl.col("season") == self.UNCOVERED)
        assert result["ixg"].null_count() == result.height

    def test_a_frame_with_full_coverage_has_no_nulls(self, game_pbp):
        pbp, ext = game_pbp
        result = prep_team_stats(pbp.with_columns(pred_goal=pl.lit(0.1)), ext)
        assert result["xgf"].null_count() == 0

    def test_stints_in_an_uncovered_season_are_null(self):
        rows = [
            _stint_event(event_idx=1, event_length=5, pred_goal=0.1, base_xg=0.05, context_xg=0.09),
            _stint_event(
                event_idx=1,
                season=20232024,
                game_id=2023020001,
                event_length=5,
                pred_goal=None,
                base_xg=None,
                context_xg=None,
            ),
        ]
        stints = prep_stints(pl.DataFrame(rows))
        delta = {row["season"]: row["home_delta_xgf"] for row in stints.iter_rows(named=True)}

        assert delta[20232024] is None
        assert delta[20222023] is not None
