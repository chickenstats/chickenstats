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
        assert pp.players != sh.players

    def test_even_strength_rows_have_equal_counts(self, stints):
        stints_df, _ = stints
        ev = build_rapm_matrix(stints_df, metric="cf", situation="EV")
        expected = stints_df.filter(pl.col("home_skater_count") == pl.col("away_skater_count")).height * 2
        assert ev.x.shape[0] == expected

    def test_goalie_columns_only_for_goals(self, stints):
        stints_df, _ = stints
        goals = build_rapm_matrix(stints_df, metric="gf", situation="EV")
        corsi = build_rapm_matrix(stints_df, metric="cf", situation="EV")

        assert goals.x.nnz > corsi.x.nnz

    def test_weights_are_toi_seconds(self, stints):
        stints_df, _ = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="all")
        assert matrix.weights.sum() == stints_df["toi"].sum() * 2

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
        with pytest.raises(InvalidInputError, match="aren't in the stints"):
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
            ozs=True,
            dzs=True,
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
        # A home offensive- or defensive-zone start is a zone start for somebody.
        assert flagged.filter(~(pl.col("ozs") | pl.col("dzs"))).is_empty()
        # A neutral-zone-only stint gives the home team neither.
        neutral = stints_df.filter(pl.col("nzs") & ~pl.col("ozs") & ~pl.col("dzs"))
        assert neutral.filter(pl.col("home_ozs") | pl.col("home_dzs")).is_empty()
        # One team's offensive-zone start is the other's defensive-zone start.
        assert stints_df["away_ozs"].equals(stints_df["home_dzs"])
        assert stints_df["away_dzs"].equals(stints_df["home_ozs"])

    def test_stints_from_an_older_prep_stints_are_refused(self, stints):
        stints_df, _ = stints
        with pytest.raises(InvalidInputError, match="home_ozs"):
            build_rapm_matrix(stints_df.drop("home_ozs", "home_dzs", "away_ozs", "away_dzs"), metric="cf")


class TestBuildPositionMap:
    def test_maps_every_on_ice_player(self, stints):
        _, pbp = stints
        position_map = build_position_map(pbp)

        assert position_map.height > 0
        assert set(position_map.columns) == {"api_id", "position", "player"}
        assert position_map["api_id"].n_unique() == position_map.height
        assert position_map["position"].is_in(["C", "L", "R", "D", "G"]).all()

    def test_covers_the_players_in_the_matrix(self, stints):
        stints_df, pbp = stints
        matrix = build_rapm_matrix(stints_df, metric="cf", situation="EV")
        known = set(build_position_map(pbp)["api_id"].to_list())

        for player_team in matrix.players:
            assert player_team.split("_")[0] in known

    def test_accepts_a_lazyframe(self, stints):
        _, pbp = stints
        assert build_position_map(pbp.lazy()).equals(build_position_map(pbp))
