"""evolving_hockey against chicken_nhl on the same games.

The exports here come from chicken_nhl, so the two modules start from the same events and any difference is in the
aggregation. These differences are listed on purpose:

- Names: the exports shorten some first names, so chicken_nhl's names go through the same rule before comparing.
- Line keys: chicken_nhl orders a lineup by NHL API id, which the exports do not have, so both sides are sorted here.
- Expected goals: the saved games have none, so the xG columns are left out.
"""

import polars as pl
import pytest

import chickenstats.chicken_nhl as chicken_nhl
import chickenstats.evolving_hockey as evolving_hockey

from .eh_converter import SHORTENED_NAMES

COUNTS = [
    "gf",
    "ga",
    "sf",
    "sa",
    "msf",
    "msa",
    "ff",
    "fa",
    "cf",
    "ca",
    "bsf",
    "bsa",
    "hf",
    "ht",
    "give",
    "take",
    "fow",
    "fol",
    "ozfw",
    "ozfl",
    "nzfw",
    "nzfl",
    "dzfw",
    "dzfl",
    "pent2",
    "pend2",
    "hdgf",
    "hdga",
    "hdsf",
    "hdsa",
    "teammate_block",
    "opp_teammate_block",
]
ADJUSTED = ["gf_adj", "ga_adj", "sf_adj", "sa_adj", "msf_adj", "msa_adj", "ff_adj", "fa_adj", "bsf_adj", "bsa_adj"]
INDIVIDUAL = [
    "g",
    "a1",
    "a2",
    "isf",
    "imsf",
    "iff",
    "icf",
    "isb",
    "isb_adj",
    "ibs",
    "ibs_adj",
    "imsf_adj",
    "ihf",
    "iht",
    "igive",
    "itake",
    "ifow",
    "ifol",
    "iozfw",
    "iozfl",
    "inzfw",
    "inzfl",
    "idzfw",
    "idzfl",
    "ipent2",
    "ipend2",
]
ZONE_STARTS = ["ozs", "nzs", "dzs", "otf"]


def export_names(frame: pl.DataFrame) -> pl.DataFrame:
    """Write chicken_nhl's names the way the exports do."""
    names = [c for c in frame.columns if c == "eh_id" or c.endswith("_eh_id")]
    return frame.with_columns(pl.col(names).str.replace_many(list(SHORTENED_NAMES), list(SHORTENED_NAMES.values())))


def sorted_lineups(frame: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    """Sort each comma-separated lineup, so the two orders compare."""
    return frame.with_columns(pl.col(columns).str.split(", ").list.sort().list.join(", "))


def assert_same_rows(ours: pl.DataFrame, theirs: pl.DataFrame, keys: list[str], columns: list[str]) -> None:
    """Both frames hold the same rows under the keys and the same numbers in the columns."""
    ours, theirs = ours.select(*keys, *columns), theirs.select(*keys, *columns)
    joined = ours.join(theirs, on=keys, how="full", coalesce=True, nulls_equal=True, suffix="_nhl")

    missing = joined.filter(pl.col(columns[0]).is_null() | pl.col(f"{columns[0]}_nhl").is_null())
    assert missing.is_empty(), missing.select(keys)

    for column in columns:
        different = joined.filter((pl.col(column) - pl.col(f"{column}_nhl")).abs() > 1e-6)
        assert different.is_empty(), (column, different.select(*keys, column, f"{column}_nhl").head())


@pytest.fixture(scope="module")
def nhl_splits(chicken):
    """A function that runs a chicken_nhl aggregation on the saved games, with the names of the exports."""

    def run(function: str, **options) -> pl.DataFrame:
        frame = getattr(chicken_nhl, function)(chicken.play_by_play, chicken.play_by_play_ext, **options)
        return export_names(frame)

    return run


@pytest.mark.parametrize("level", ["game", "period", "session", "season"])
def test_player_rows_match_chicken_nhl(pbp_polars, nhl_splits, level):
    ours = evolving_hockey.prep_stats(pbp_polars, level=level, disable_progress_bar=True)
    theirs = nhl_splits("prep_stats", level=level)

    keys = [
        c for c in ["season", "session", "game_id", "period", "team", "eh_id", "strength_state"] if c in ours.columns
    ]
    assert_same_rows(ours, theirs, keys, [*COUNTS, *INDIVIDUAL, *ZONE_STARTS, *ADJUSTED, "toi"])


@pytest.mark.parametrize(
    "flags", [{"score": True}, {"teammates": True}, {"opposition": True}], ids=["score", "teammates", "opposition"]
)
def test_split_player_rows_match_chicken_nhl(pbp_polars, nhl_splits, flags):
    ours = evolving_hockey.prep_stats(pbp_polars, level="game", disable_progress_bar=True, **flags)
    theirs = nhl_splits("prep_stats", level="game", **flags)

    lineups = [c for c in ours.columns if c.endswith("_eh_id") and c != "eh_id"]
    keys = [
        "game_id",
        "team",
        "eh_id",
        "strength_state",
        *([c for c in ["score_state"] if c in ours.columns]),
        *lineups,
    ]

    assert_same_rows(
        sorted_lineups(ours, lineups),
        sorted_lineups(theirs, lineups),
        keys,
        [*COUNTS, *INDIVIDUAL, *ZONE_STARTS, "toi"],
    )


@pytest.mark.parametrize("position", ["f", "d"])
@pytest.mark.parametrize("level", ["game", "season"])
def test_line_rows_match_chicken_nhl(pbp_polars, nhl_splits, level, position):
    ours = evolving_hockey.prep_lines(pbp_polars, position=position, level=level, disable_progress_bar=True)
    theirs = nhl_splits("prep_lines", position=position, level=level)

    line = "forwards_eh_id" if position == "f" else "defense_eh_id"
    keys = [c for c in ["season", "game_id", "team", line, "strength_state"] if c in ours.columns]

    assert_same_rows(sorted_lineups(ours, [line]), sorted_lineups(theirs, [line]), keys, [*COUNTS, *ZONE_STARTS, "toi"])


@pytest.mark.parametrize("level", ["game", "period", "session", "season"])
def test_team_rows_match_chicken_nhl(pbp_polars, nhl_splits, level):
    ours = evolving_hockey.prep_team_stats(pbp_polars, level=level, disable_progress_bar=True)
    theirs = nhl_splits("prep_team_stats", level=level)

    keys = [c for c in ["season", "session", "game_id", "period", "team", "strength_state"] if c in ours.columns]
    assert_same_rows(ours, theirs, keys, [*COUNTS, *ZONE_STARTS, *ADJUSTED, "toi"])


def test_names_match_chicken_nhl(pbp_polars, chicken):
    """Every player has the name chicken_nhl gives him, after the names the exports shorten."""
    ours = set(pbp_polars.filter(pl.col("event_type") == "GOAL")["event_player_1"])
    theirs = chicken.play_by_play.filter(pl.col("event") == "GOAL")["player_1"]
    shortened = theirs.str.replace_many(list(SHORTENED_NAMES), list(SHORTENED_NAMES.values()))

    assert ours == set(shortened)


def test_every_eh_id_joins_to_gar(pbp_polars, raw_gar_skater_polars, raw_gar_goalie_polars):
    """prep_stats and prep_gar agree on the id of every player, so the two join on it."""
    stats = evolving_hockey.prep_stats(pbp_polars, level="session", disable_progress_bar=True)
    gar = evolving_hockey.prep_gar(raw_gar_skater_polars, raw_gar_goalie_polars)

    unmatched = stats.join(gar, on=["season", "eh_id"], how="anti")

    assert unmatched.is_empty(), unmatched.select("season", "eh_id")


def test_shootouts_count_only_in_the_shootout_columns(pbp_polars, chicken):
    """A shootout goal is not a goal, a shot or an attempt for the team, and its xG is cleared."""
    columns = ["goal", "shot", "miss", "fenwick", "corsi", "shootout_attempt", "shootout_goal"]
    ours = pbp_polars.select(pl.col(columns).sum()).row(0)
    theirs = chicken.play_by_play.select(pl.col(columns).sum()).row(0)

    assert ours == theirs
    assert pbp_polars.filter(pl.col("shootout_attempt") == 1)["pred_goal"].is_null().all()


def test_a_penalty_shot_has_no_goalie_for_the_shooting_team(pbp_polars):
    penalty_shot = pbp_polars.filter(pl.col("strength_state") == "1v0", pl.col("goal") == 1).row(0, named=True)

    assert penalty_shot["own_goalie"] is None
    assert penalty_shot["opp_goalie_eh_id"] == "JUUSE.SAROS"
