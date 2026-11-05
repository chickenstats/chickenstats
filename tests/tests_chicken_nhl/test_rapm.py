import polars as pl
import pytest

from chickenstats.chicken_nhl import Scraper, prep_stints
from chickenstats.exceptions import InvalidInputError

pytest.importorskip("scipy", reason="requires the 'rapm' extra")

from chickenstats.chicken_nhl.rapm import build_position_map, build_rapm_matrix


@pytest.fixture(scope="module")
def stints():
    scraper = Scraper(game_ids=[2023020001], disable_progress_bar=True)
    return prep_stints(scraper.play_by_play), scraper.play_by_play


class TestBuildRapmMatrix:
    @pytest.mark.parametrize("situation", ["ev", "5v5", ""])
    def test_rejects_an_unknown_situation(self, stints, situation):
        """A misspelled situation used to mean no filter at all."""
        stints_df, _ = stints

        with pytest.raises(InvalidInputError, match="Unknown situation"):
            build_rapm_matrix(stints_df, metric="cf", situation=situation)

    def test_shapes_line_up(self, stints):
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="EV")

        assert matrix.x.shape[0] > 0
        assert matrix.x.shape[0] == len(matrix.y) == len(matrix.weights)
        assert matrix.dates is not None
        assert len(matrix.dates) == len(matrix.y)
        assert matrix.x.shape[1] > len(matrix.players) * 2

    def test_column_count_matches_feature_groups(self, stints):
        """Skaters x2, strength states, five scalar flags, then score-state levels."""
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="EV")

        ev = stints_df.filter(pl.col("home_skater_count") == pl.col("away_skater_count"))
        # Strength state is each row's own skater counts, so at even strength one per count.
        strengths = ev["home_skater_count"].n_unique()
        # metric="cf" is a shot-volume metric, so score state uses six buckets.
        assert matrix.x.shape[1] == len(matrix.players) * 2 + strengths + 5 + 6

    def test_xg_score_state_uses_three_buckets(self, stints):
        stints_df, _ = stints
        volume = build_rapm_matrix(stints_df, metric="cf", situation="EV")
        goals = build_rapm_matrix(stints_df, metric="gf", situation="EV")

        # Same skaters and strengths, but cf gets six score buckets and gf only two --
        # gf's extra columns are its goalies.
        assert volume.x.shape[1] - 6 + 2 < goals.x.shape[1]

    def test_two_rows_per_stint_when_unfiltered(self, stints):
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="all")
        assert matrix.x.shape[0] == stints_df.height * 2

    def test_stints_with_no_xg_are_left_out(self, stints):
        stints_df, _ = stints
        half = stints_df.height // 2
        known = pl.int_range(pl.len()) < half
        partial = stints_df.with_columns(home_xgf=pl.when(known).then(0.1), away_xgf=pl.when(known).then(0.1))

        matrix = build_rapm_matrix(partial, metric="xgf", situation="all")

        assert matrix.x.shape[0] == half * 2

    def test_power_play_and_shorthanded_differ(self, stints):
        """Filtering pre-stack would make PP and SH resolve to the same rows."""
        stints_df, _ = stints
        pp = build_rapm_matrix(stints_df, metric="cf", situation="PP")
        sh = build_rapm_matrix(stints_df, metric="cf", situation="SH")

        assert pp.x.shape[0] > 0
        assert sh.x.shape[0] > 0
        assert pp.player_metrics.sort("api_id")["toi_seconds"].to_list() != (
            sh.player_metrics.sort("api_id")["toi_seconds"].to_list()
        )

    def test_power_play_matrix_has_defensive_columns_for_the_penalty_killers(self, stints):
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="PP")
        count = len(matrix.players)
        x = matrix.x.toarray()
        offense, defense = x[:, :count].sum(axis=0), x[:, count : count * 2].sum(axis=0)

        assert (defense > 0).sum() >= 8
        penalty_killers = matrix.player_metrics.filter(pl.col("toi_seconds") == 0)
        assert penalty_killers.height > 0
        for key in penalty_killers["player_team"]:
            index = matrix.players.index(key)
            assert offense[index] == 0
            assert defense[index] > 0

    @pytest.mark.parametrize("situation", ["EV", "PP", "SH"])
    def test_empty_net_stints_are_in_no_situation(self, stints, situation):
        stints_df, _ = stints
        pulled = stints_df.with_columns(home_goalie_ids=pl.lit([], dtype=pl.List(pl.String)))

        assert build_rapm_matrix(pulled, metric="cf", situation=situation, min_toi=0).x.shape[0] == 0

    def test_empty_net_stints_stay_in_all(self, stints):
        stints_df, _ = stints
        pulled = stints_df.with_columns(home_goalie_ids=pl.lit([], dtype=pl.List(pl.String)))

        assert build_rapm_matrix(pulled, metric="cf", situation="all").x.shape[0] == stints_df.height * 2

    def test_player_metrics_splits_the_key(self, stints):
        stints_df, _ = stints
        metrics = build_rapm_matrix(stints_df, metric="cf", situation="EV").player_metrics

        assert metrics.schema["api_id"] == pl.Int64
        assert metrics.select(pl.format("{}_{}", "api_id", "team").eq(pl.col("player_team")).all()).item()

    def test_even_strength_rows_have_equal_counts(self, stints):
        stints_df, _ = stints
        ev = build_rapm_matrix(stints_df, metric="cf", situation="EV")
        expected = (
            stints_df.filter(
                pl.col("home_skater_count") == pl.col("away_skater_count"),
                pl.col("home_goalie_ids").list.len() > 0,
                pl.col("away_goalie_ids").list.len() > 0,
            ).height
            * 2
        )
        assert ev.x.shape[0] == expected

    def test_goalie_columns_only_for_goals(self, stints):
        stints_df, _ = stints
        goals = build_rapm_matrix(stints_df, metric="gf", situation="EV")
        corsi = build_rapm_matrix(stints_df, metric="cf", situation="EV")

        assert goals.x.nnz > corsi.x.nnz

    def test_weights_are_toi_seconds(self, stints):
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="all")
        assert matrix.weights.sum() == stints_df["toi_seconds"].sum() * 2

    def test_stints_with_no_time_are_left_out(self, stints):
        stints_df, _ = stints
        zero = stints_df.head(1).with_columns(toi_seconds=pl.lit(0, dtype=stints_df.schema["toi_seconds"]))
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="all")
        padded = build_rapm_matrix(pl.concat([stints_df, zero]), metric="cf", situation="all")
        assert padded.x.shape == matrix.x.shape

    def test_min_toi_filters_players(self, stints):
        stints_df, _ = stints
        loose = build_rapm_matrix(stints_df, metric="cf", situation="EV", min_toi=1)
        strict = build_rapm_matrix(stints_df, metric="cf", situation="EV", min_toi=30)
        assert len(strict.players) < len(loose.players)

    def test_matrix_is_binary(self, stints):
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="EV")
        assert set(matrix.x.data.tolist()) == {1.0}

    def test_unpacks_positionally(self, stints):
        stints_df, _ = stints
        x, y, weights, dates, players, player_metrics = build_rapm_matrix(stints_df, metric="cf")
        assert dates is not None
        assert x.shape[0] == len(y) == len(weights) == len(dates)
        assert isinstance(players, list)
        assert isinstance(player_metrics, pl.DataFrame)

    def test_unknown_metric_raises(self, stints):
        stints_df, _ = stints
        with pytest.raises(InvalidInputError, match="Unknown metric"):
            build_rapm_matrix(stints_df, metric="corsi")

    def test_absent_xg_metric_raises(self, stints):
        """xG metrics only exist when the source column was in the play-by-play."""
        stints_df, _ = stints
        with pytest.raises(InvalidInputError, match="pred_goal, base_xg or context_xg"):
            build_rapm_matrix(stints_df, metric="context_xgf")


class TestPerspectives:
    """Each team's rows carry its own zone starts and its own strength state."""

    @staticmethod
    def _one(stints_df: pl.DataFrame, **values) -> pl.DataFrame:
        row = stints_df.head(1)
        return row.with_columns(**{k: pl.lit(v) for k, v in values.items()})

    @staticmethod
    def _flag_columns(matrix) -> tuple[int, int, int]:
        """Indices of OZS, NZS, DZS: after the skaters and the strength dummies."""
        strengths = 2  # one row per perspective, each with its own strength state
        start = len(matrix.players) * 2 + strengths
        return start, start + 1, start + 2

    def test_an_offensive_zone_start_gives_the_teams_opposite_flags(self, stints):
        stints_df, _ = stints
        one = self._one(
            stints_df,
            home_ozs=True,
            home_dzs=False,
            away_ozs=False,
            away_dzs=True,
            home_skater_count=5,
            away_skater_count=4,
        )
        matrix = build_rapm_matrix(one, metric="cf", situation="all", min_toi=0)
        ozs, _, dzs = self._flag_columns(matrix)
        home, away = matrix.x.toarray()
        assert (home[ozs], home[dzs]) == (1.0, 0.0)
        assert (away[ozs], away[dzs]) == (0.0, 1.0)

    def test_power_play_and_shorthanded_rows_get_their_own_strength(self, stints):
        stints_df, _ = stints
        one = self._one(stints_df, home_skater_count=5, away_skater_count=4, strength_state="5v4")
        matrix = build_rapm_matrix(one, metric="cf", situation="all", min_toi=0)
        home, away = matrix.x.toarray()
        start = len(matrix.players) * 2
        # Two strength dummies, sorted: "4v5" then "5v4". The home team had the extra skater.
        assert (home[start], home[start + 1]) == (0.0, 1.0)
        assert (away[start], away[start + 1]) == (1.0, 0.0)

    def test_prep_stints_zone_starts_follow_the_home_team(self, stints):
        stints_df, _ = stints
        flagged = stints_df.filter(pl.col("home_ozs") | pl.col("home_dzs"))
        assert flagged.height > 0
        # One team's offensive-zone start is the other's defensive-zone start.
        assert stints_df["away_ozs"].equals(stints_df["home_dzs"])
        assert stints_df["away_dzs"].equals(stints_df["home_ozs"])

    def test_stints_from_an_older_prep_stints_are_refused(self, stints):
        stints_df, _ = stints
        with pytest.raises(InvalidInputError, match="home_ozs"):
            build_rapm_matrix(stints_df.drop("home_ozs", "home_dzs", "away_ozs", "away_dzs"), metric="cf")


class TestDesignMatrixFeatures:
    """One stint's two rows, read column by column: a wrong feature still fits a plausible model."""

    @pytest.fixture
    def stint(self, stints):
        stints_df, _ = stints
        return stints_df.head(1).with_columns(
            home_skater_count=pl.lit(5),
            away_skater_count=pl.lit(4),
            toi_seconds=pl.lit(120),
            home_cf=pl.lit(3),
            away_cf=pl.lit(1),
            home_gf=pl.lit(1),
            away_gf=pl.lit(0),
            home_b2b=pl.lit(True),
            away_b2b=pl.lit(False),
            home_score_7=pl.lit(2),
            away_score_7=pl.lit(-2),
            home_score_3=pl.lit(1),
            away_score_3=pl.lit(-1),
        )

    @staticmethod
    def _columns(matrix) -> dict[str, int]:
        """Indices of the scalar flags and the first score column, for one row per strength."""
        start = len(matrix.players) * 2 + 2
        return {"home_adv": start + 3, "b2b": start + 4, "score": start + 5}

    def test_skaters_are_on_offense_for_their_team_and_defense_against_it(self, stint):
        matrix = build_rapm_matrix(stint, metric="cf", situation="all", min_toi=0)
        home_row, away_row = matrix.x.toarray()
        count = len(matrix.players)
        home_keys = {f"{player}_{stint['home_team'].item()}" for player in stint["home_skater_ids"].item()}
        away_keys = {f"{player}_{stint['away_team'].item()}" for player in stint["away_skater_ids"].item()}

        assert {matrix.players[i] for i in home_row[:count].nonzero()[0]} == home_keys
        assert {matrix.players[i] for i in home_row[count : count * 2].nonzero()[0]} == away_keys
        assert {matrix.players[i] for i in away_row[:count].nonzero()[0]} == away_keys
        assert {matrix.players[i] for i in away_row[count : count * 2].nonzero()[0]} == home_keys

    def test_home_advantage_is_only_on_the_home_row(self, stint):
        matrix = build_rapm_matrix(stint, metric="cf", situation="all", min_toi=0)
        home_row, away_row = matrix.x.toarray()
        column = self._columns(matrix)["home_adv"]

        assert (home_row[column], away_row[column]) == (1.0, 0.0)

    def test_back_to_back_comes_from_the_rows_own_team(self, stint):
        matrix = build_rapm_matrix(stint, metric="cf", situation="all", min_toi=0)
        home_row, away_row = matrix.x.toarray()
        column = self._columns(matrix)["b2b"]

        assert (home_row[column], away_row[column]) == (1.0, 0.0)

    def test_score_state_is_signed_for_each_row(self, stint):
        matrix = build_rapm_matrix(stint, metric="cf", situation="all", min_toi=0)
        home_row, away_row = matrix.x.toarray()
        first = self._columns(matrix)["score"]
        levels = [-3, -2, -1, 1, 2, 3]

        assert home_row[first + levels.index(2)] == 1.0
        assert home_row[first:].sum() == 1.0
        assert away_row[first + levels.index(-2)] == 1.0
        assert away_row[first:].sum() == 1.0

    def test_target_is_a_per_hour_rate(self, stint):
        for metric, expected in (("cf", [90.0, 30.0]), ("gf", [30.0, 0.0])):
            matrix = build_rapm_matrix(stint, metric=metric, situation="all", min_toi=0)
            assert matrix.y.tolist() == expected


class TestBuildPositionMap:
    def test_maps_every_on_ice_player(self, stints):
        _, pbp = stints
        position_map = build_position_map(pbp)

        assert position_map.height > 0
        assert set(position_map.columns) == {"api_id", "position", "player"}
        assert position_map["api_id"].n_unique() == position_map.height
        assert position_map.schema["api_id"] == pl.Int64
        assert position_map["position"].is_in(["C", "L", "R", "D", "G"]).all()

    def test_covers_the_players_in_the_matrix(self, stints):
        stints_df, pbp = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="EV")
        known = set(build_position_map(pbp)["api_id"].to_list())

        for player_team in matrix.players:
            assert int(player_team.split("_")[0]) in known

    def test_accepts_a_lazyframe(self, stints):
        _, pbp = stints
        assert build_position_map(pbp.lazy()).equals(build_position_map(pbp))


def _lineup_rows(positions: list[str]) -> pl.DataFrame:
    """Play-by-play rows putting player 1 on the ice at each of the positions given."""
    return pl.DataFrame(
        {
            "home_on_api_id": ["1"] * len(positions),
            "home_on_positions": positions,
            "home_on": ["A"] * len(positions),
            "away_on_api_id": ["2"] * len(positions),
            "away_on_positions": ["G"] * len(positions),
            "away_on": ["B"] * len(positions),
        }
    )


class TestBuildPositionMapChoice:
    def test_a_player_gets_their_most_common_position(self):
        position_map = build_position_map(_lineup_rows(["D", "C", "C"]))

        assert position_map.filter(pl.col("api_id") == 1)["position"].item() == "C"

    def test_row_order_does_not_change_the_position(self):
        frame = _lineup_rows(["D", "C", "L", "C", "D"])

        for seed in range(5):
            position_map = build_position_map(frame.sample(fraction=1, shuffle=True, seed=seed))

            assert position_map.filter(pl.col("api_id") == 1)["position"].item() == "C"
