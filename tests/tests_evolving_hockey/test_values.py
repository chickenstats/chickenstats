"""Value tests for evolving_hockey on the saved games, converted to the shape of the exports."""

import polars as pl
import pytest

from chickenstats.chicken_nhl._game_utils import calculate_score_adjustment, load_score_adjustments
from chickenstats.evolving_hockey import prep_gar, prep_ind, prep_oi, prep_pbp, prep_stats, prep_team_stats, prep_xgar
from chickenstats.evolving_hockey._weights import get_adj_weights_lf

from .eh_converter import FIXTURE_GAME_ID, SHOOTOUT_GAME_ID

GOALS = [
    ("NIKITA.KUCHEROV", "VICTOR.HEDMAN", "BRAYDEN.POINT"),
    ("RYAN.O'REILLY", "FILIP.FORSBERG", "RYAN.MCDONAGH"),
    ("JUUSO.PARSSINEN", "FILIP.FORSBERG", "RYAN.O'REILLY"),
    ("NICK.PAUL", "BRAYDEN.POINT", "STEVEN.STAMKOS"),
    ("BRANDON.HAGEL", None, None),
    ("THOMAS.NOVAK", "PHILIP.TOMASINO", "GUSTAV.NYQUIST"),
    ("NICK.PAUL", "MIKHAIL.SERGACHEV", "BRAYDEN.POINT"),
    ("NIKITA.KUCHEROV", "NICK.PAUL", None),
]

TBL_GAME_ROW = {
    "toi": 60.0,
    "gf": 5,
    "ga": 3,
    "sf": 34,
    "sa": 31,
    "ff": 50,
    "fa": 46,
    "cf": 61,
    "ca": 65,
    "msf": 16,
    "msa": 15,
    "fow": 34,
    "fol": 26,
    "ozfw": 15,
    "ozfl": 9,
    "nzfw": 7,
    "nzfl": 10,
    "dzfw": 12,
    "dzfl": 7,
    "give": 8,
    "take": 8,
    "pent2": 4,
    "pend2": 5,
    "pend0": 1,
}

INDIVIDUALS = {
    "NIKITA.KUCHEROV": {"g": 2, "a1": 0, "a2": 0, "isf": 5, "ifow": 0, "ifol": 0},
    "NICK.PAUL": {"g": 2, "a1": 1, "a2": 0, "isf": 3, "ifow": 3, "ifol": 8},
    "BRANDON.HAGEL": {"g": 1, "a1": 0, "a2": 0, "isf": 4, "ifow": 1, "ifol": 0},
    "RYAN.O'REILLY": {"g": 1, "a1": 0, "a2": 1, "isf": 4, "ifow": 11, "ifol": 19},
    "FILIP.FORSBERG": {"g": 0, "a1": 2, "a2": 0, "isf": 6, "ifow": 0, "ifol": 0},
    "STEVEN.STAMKOS": {"g": 0, "a1": 0, "a2": 1, "isf": 2, "ifow": 12, "ifol": 5},
}

ON_ICE = {
    # Johansson is not on the ice for his own team's penalty shot
    "JONAS.JOHANSSON": {"gf": 4, "ga": 3, "cf": 60, "ca": 65},
    "JUUSE.SAROS": {"gf": 3, "ga": 4, "cf": 54, "ca": 59},
    "NIKITA.KUCHEROV": {"gf": 4, "ga": 1, "cf": 32, "ca": 24},
}


def one_game(frame: pl.DataFrame, game_id: int = FIXTURE_GAME_ID) -> pl.DataFrame:
    return frame.filter(pl.col("game_id") == game_id)


def totals(frame: pl.DataFrame, by: str, columns: list[str]) -> dict:
    """Sum columns for each value of a column, as {value: {column: total}}."""
    rows = frame.group_by(by).agg(pl.col(columns).sum()).to_dicts()
    return {row.pop(by): row for row in rows}


def test_goals_go_to_the_scorer_and_the_assisters(pbp_polars):
    goals = one_game(pbp_polars).filter(pl.col("event_type") == "GOAL").sort("event_index")

    assert goals.select("event_player_1_eh_id", "event_player_2_eh_id", "event_player_3_eh_id").rows() == GOALS


def test_faceoffs_name_the_winner_first(pbp_polars):
    faceoffs = one_game(pbp_polars).filter(pl.col("event_type") == "FAC").sort("event_index")

    assert faceoffs.select("event_team", "event_player_1_eh_id", "event_player_2_eh_id").rows()[:2] == [
        ("NSH", "RYAN.O'REILLY", "ANTHONY.CIRELLI"),
        ("TBL", "ANTHONY.CIRELLI", "COLTON.SISSONS"),
    ]


def test_every_game_has_one_code_for_each_team(pbp_polars):
    teams = pbp_polars.group_by("game_id").agg(pl.col("opp_team").drop_nulls().unique().sort())

    assert teams.filter(pl.col("game_id") == FIXTURE_GAME_ID)["opp_team"].to_list() == [["NSH", "TBL"]]
    assert teams.filter(pl.col("game_id") == SHOOTOUT_GAME_ID)["opp_team"].to_list() == [["LAK", "VGK"]]


def test_a_team_row_matches_the_game(pbp_polars):
    team_stats = prep_team_stats(pbp_polars, strengths=False, disable_progress_bar=True)
    row = one_game(team_stats).filter(pl.col("team") == "TBL").row(0, named=True)

    assert {column: row[column] for column in TBL_GAME_ROW} == pytest.approx(TBL_GAME_ROW)


def test_opposing_team_rows_mirror_each_other(pbp_polars):
    team_stats = prep_team_stats(pbp_polars, strengths=False, disable_progress_bar=True)
    pairs = {"gf": "ga", "sf": "sa", "cf": "ca", "ff": "fa", "hf": "ht", "fow": "fol", "ozfw": "dzfl", "dzfw": "ozfl"}

    mirrored = team_stats.join(team_stats, left_on=["game_id", "team"], right_on=["game_id", "opp_team"], suffix="_opp")

    assert mirrored.height == team_stats.height
    for own, opposing in pairs.items():
        assert (mirrored[own] == mirrored[f"{opposing}_opp"]).all(), own


def test_individual_stats_go_to_the_right_player(pbp_polars):
    columns = list(next(iter(INDIVIDUALS.values())))
    individuals = totals(one_game(prep_ind(pbp_polars)), "eh_id", columns)

    assert {player: individuals[player] for player in INDIVIDUALS} == INDIVIDUALS


@pytest.mark.parametrize("flags", [{}, {"score": True}, {"teammates": True}, {"opposition": True}], ids=str)
def test_prep_stats_keeps_every_individual_stat(pbp_polars, flags):
    """Each individual stat in prep_stats adds up to prep_ind, however the rows are split."""
    columns = ["g", "a1", "a2", "isf", "imsf", "icf", "isb", "ibs", "ihf", "iht", "ifow", "ifol", "ipent2", "ipend2"]

    stats = prep_stats(pbp_polars, disable_progress_bar=True, **flags)
    individual = prep_ind(pbp_polars, **flags)

    assert stats.select(pl.col(columns).sum()).row(0) == individual.select(pl.col(columns).sum()).row(0)


def test_on_ice_stats_count_every_event(pbp_polars):
    columns = list(next(iter(ON_ICE.values())))
    on_ice = totals(one_game(prep_stats(pbp_polars, disable_progress_bar=True)), "eh_id", columns)

    assert {player: on_ice[player] for player in ON_ICE} == ON_ICE


def test_ice_time_matches_the_shifts_of_every_player(pbp_polars, raw_shifts_polars):
    shift_minutes = {
        player.replace("..", "."): seconds / 60
        for player, seconds in one_game(raw_shifts_polars)
        .group_by("player")
        .agg(pl.col("seconds_duration").sum())
        .rows()
    }
    ice_time = totals(one_game(prep_stats(pbp_polars, disable_progress_bar=True)), "eh_id", ["toi"])

    assert {player: row["toi"] for player, row in ice_time.items()} == pytest.approx(shift_minutes)


def test_away_team_zone_starts_are_from_the_away_team(pbp_polars):
    """The change before the faceoff at second 35 is in Tampa Bay's defensive zone, so Nashville's offensive zone."""
    change = one_game(pbp_polars).filter(
        pl.col("event_type") == "CHANGE", pl.col("game_seconds") == 35, pl.col("event_team") == "NSH"
    )

    assert change["zone_start"].to_list() == ["OFF"]


def test_a_file_of_several_games_matches_each_game_alone(raw_pbp_polars, raw_shifts_polars, pbp_polars):
    """Reading seven games in one file gives each game the same rows as reading it alone."""
    alone = prep_pbp(one_game(raw_pbp_polars), one_game(raw_shifts_polars), disable_progress_bar=True)
    columns = ["id", "zone_start", "strength_state", "ozs", "dzs", "nzs", "otf"]

    assert one_game(pbp_polars).sort("id").select(columns).rows() == alone.sort("id").select(columns).rows()


def test_a_single_game_read_by_pandas_prepares(raw_pbp_polars, raw_shifts_polars, tmp_path):
    """pandas reads the empty seventh on-ice column of one game as numbers."""
    pd = pytest.importorskip("pandas")

    pbp_path, shifts_path = tmp_path / "pbp.csv", tmp_path / "shifts.csv"
    one_game(raw_pbp_polars).write_csv(pbp_path)
    one_game(raw_shifts_polars).write_csv(shifts_path)

    pbp = prep_pbp(pd.read_csv(pbp_path), pd.read_csv(shifts_path), disable_progress_bar=True)

    assert (pbp["event_type"] == "GOAL").sum() == 8


@pytest.mark.parametrize("level", ["game", "period", "session", "season"])
def test_opposition_splits_work_at_every_level(pbp_polars, level):
    stats = prep_stats(pbp_polars, level=level, opposition=True, disable_progress_bar=True)

    assert stats.filter(pl.col("opp_team").is_null()).is_empty()
    assert stats["toi"].sum() == pytest.approx(prep_oi(pbp_polars)["toi"].sum())


def _against(stat: str) -> str:
    """The against column a percentage divides by, from the naming rule: gf_adj to ga_adj, take to give."""
    special = {"take": "give", "hf": "ht"}
    if stat in special:
        return special[stat]
    base, adjusted = (stat[:-4], "_adj") if stat.endswith("_adj") else (stat, "")
    return f"{base[:-1]}a{adjusted}"


@pytest.mark.parametrize("level", ["game", "season"])
@pytest.mark.parametrize("prep", [prep_stats, prep_team_stats])
def test_rates_and_percentages_follow_their_counts(pbp_polars, prep, level):
    """Every per-60 rate is its count over ice time, and every percentage is for over for plus against."""
    df = prep(pbp_polars, level=level, disable_progress_bar=True)
    rates = [c for c in df.columns if c.endswith("_p60") and df[c[:-4]].sum() != 0]
    percentages = [c for c in df.columns if c.endswith("_percent") and (df[c[:-8]].sum() + df[_against(c[:-8])].sum())]
    assert rates and percentages

    expected = df.select(
        *(pl.when(pl.col("toi") > 0).then(pl.col(c[:-4]) / pl.col("toi") * 60).alias(c) for c in rates),
        *(
            pl.when(pl.col(c[:-8]) + pl.col(_against(c[:-8])) > 0)
            .then(pl.col(c[:-8]) / (pl.col(c[:-8]) + pl.col(_against(c[:-8]))))
            .alias(c)
            for c in percentages
        ),
    )

    for column in expected.columns:
        assert df[column].is_null().to_list() == expected[column].is_null().to_list(), column
        assert df[column].drop_nulls().to_list() == pytest.approx(expected[column].drop_nulls().to_list(), abs=1e-9)


def test_individual_faceoff_zones_are_inside_the_on_ice_zones(pbp_polars):
    """A player cannot lose more faceoffs in a zone than he was on the ice for there."""
    stats = prep_stats(pbp_polars, level="game", disable_progress_bar=True)

    assert (stats["iozfl"] <= stats["ozfl"]).all()
    assert (stats["idzfl"] <= stats["dzfl"]).all()
    assert (stats["iozfw"] <= stats["ozfw"]).all()


@pytest.mark.parametrize("season", ["23-24", "99-00", "09-10"])
def test_gar_seasons_are_integers_like_the_play_by_play(
    raw_gar_skater_polars, raw_gar_goalie_polars, raw_xgar_polars, season
):
    expected = {"23-24": 20232024, "99-00": 19992000, "09-10": 20092010}[season]
    skaters = raw_gar_skater_polars.with_columns(pl.lit(season).alias("Season"))
    goalies = raw_gar_goalie_polars.with_columns(pl.lit(season).alias("Season"))
    xgar = raw_xgar_polars.with_columns(pl.lit(season).alias("Season"))

    assert prep_gar(skaters, goalies)["season"].unique().to_list() == [expected]
    assert prep_xgar(xgar)["season"].unique().to_list() == [expected]


def test_the_weights_table_matches_chicken_nhl_everywhere():
    """Every strength state, venue and score difference gives the same weights in both modules."""
    weights = get_adj_weights_lf().collect()
    columns = {"goal": "goal_w", "shot": "shot_w", "fenwick": "fenwick_w", "corsi": "corsi_w"}

    assert weights.height == 9 * 2 * 7
    for row in weights.iter_rows(named=True):
        play = calculate_score_adjustment(
            {
                "event": "SHOT",
                "event_team": "HOME" if row["is_home"] else "AWAY",
                "home_team": "HOME",
                "strength_state": row["strength_state"],
                "home_score_diff": row["score_bucket"],
                "teammate_block": 0,
                **dict.fromkeys(["goal", "shot", "miss", "block", "teammate_block", "fenwick", "corsi"], 1),
            },
            load_score_adjustments(),
        )
        for stat, weight in columns.items():
            assert row[weight] == pytest.approx(play[f"{stat}_adj"]), (row, stat)
