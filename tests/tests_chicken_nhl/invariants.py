"""Checks that every scraped game must pass, shared by the offline tests and the network-marked regression run.

Each check takes the frames for one or more games, as ``scrape_saved_games`` returns them, and asserts one invariant:
totals that agree however the output is split, for and against that mirror, Corsi that is Fenwick plus blocked
attempts, ice time equal to the shift reports, and identity columns that are a key.

The oracles below rebuild values from the play-by-play rows on their own, with no call to the package's
aggregation, and compare them with what the package returns: score-adjusted counts from the weight table, and
team and on-ice totals from the plays each team and player was on the ice for.
"""

import polars as pl
import pytest

from chickenstats.chicken_nhl import prep_ind, prep_lines, prep_stats, prep_team_stats
from chickenstats.chicken_nhl._game_utils import load_score_adjustments
from chickenstats.chicken_nhl.identity import identity_columns

# Games with a known data problem, scraped from the NHL under the regression marker
REGRESSION_GAME_IDS = [
    2022020194,
    2022020673,
    2016020001,
    2018021187,
    2010021176,
    2011020069,
    2012020095,
    2012020341,
    2012020627,
    2012020660,
    2012020671,
    2012030224,
    2013020305,
    2013030142,
    2013030155,
    2013020445,
    2014020120,
    2014020356,
    2014020417,
    2014020506,
    2014020939,
    2014020945,
    2014021127,
    2014021128,
    2014021203,
    2014030311,
    2014030315,
    2015020193,
    2015020401,
    2015020839,
    2015020917,
    2015021092,
    2016020049,
    2016020177,
    2016020256,
    2016020326,
    2016020433,
    2016020519,
    2016020625,
    2016020883,
    2016020963,
    2016021111,
    2016021165,
    2016030216,
    2017020033,
    2017020096,
    2017020209,
    2017020233,
    2017020548,
    2017020601,
    2017020615,
    2017020796,
    2017020835,
    2017020836,
    2017021136,
    2017021161,
    2018020006,
    2018020009,
    2018020049,
    2018020115,
    2018020122,
    2018020153,
    2018020211,
    2018020309,
    2018020363,
    2018020519,
    2018020561,
    2018020752,
    2018020794,
    2018020795,
    2018020841,
    2018020969,
    2018021087,
    2018021124,
    2018021171,
    2019020006,
    2019020136,
    2019020147,
    2019020179,
    2019020239,
    2019020316,
    2019020682,
    2020020456,
    2020020846,
    2020020860,
    2021020482,
    2023020838,
    2023021279,
]

TEAM_KEY = ["game_id", "team"]
TEAM_COUNTS = ["gf", "ga", "sf", "sa", "ff", "fa", "cf", "ca", "bsf", "bsa", "pent2", "pend2", "fow", "fol"]


def _mirrored(state: str) -> str:
    return "v".join(reversed(state.split("v"))) if "v" in state else state


# Each split to compare with the unsplit output; team stats have no teammates split
SPLITS = [
    {"strength_state": True},
    {"score": True},
    {"teammates": True},
    {"opposition": True},
    {"strength_state": True, "score": True, "teammates": True, "opposition": True},
]
TEAM_SPLITS = [
    {"strength_state": True},
    {"score": True},
    {"opposition": True},
    {"strength_state": True, "score": True, "opposition": True},
]
UNSPLIT = {"strength_state": False, "score": False, "teammates": False, "opposition": False}
TEAM_UNSPLIT = {"strength_state": False, "score": False, "opposition": False}


def _totals(df: pl.DataFrame, key: list[str], columns: list[str]) -> pl.DataFrame:
    return df.group_by(key).agg(pl.col(columns).sum()).sort(key)


def totals_agree_however_split(game) -> None:
    """Team, line, player and individual totals are the same with and without every split."""
    pbp, ext = game.play_by_play, game.play_by_play_ext
    whole = prep_team_stats(pbp, ext, level="game", **TEAM_UNSPLIT)
    expected = _totals(whole, TEAM_KEY, TEAM_COUNTS + ["toi"])

    for split in TEAM_SPLITS:
        totals = _totals(
            prep_team_stats(pbp, ext, level="game", **TEAM_UNSPLIT | split), TEAM_KEY, TEAM_COUNTS + ["toi"]
        )
        assert totals.select(TEAM_COUNTS).equals(expected.select(TEAM_COUNTS)), split
        assert totals["toi"].to_list() == pytest.approx(expected["toi"].to_list()), split

    player_key = ["game_id", "api_id"]
    stats_whole = prep_stats(pbp, ext, level="game", **UNSPLIT)
    counts = [c for c, dtype in stats_whole.schema.items() if dtype.is_integer() and c not in ("season", "game_id")]
    counts = [c for c in counts if not c.endswith("api_id")]
    expected = _totals(stats_whole, player_key, counts + ["toi"])
    for split in SPLITS:
        totals = _totals(prep_stats(pbp, ext, level="game", **UNSPLIT | split), player_key, counts + ["toi"])
        assert totals.select(counts).equals(expected.select(counts)), split
        assert totals["toi"].to_list() == pytest.approx(expected["toi"].to_list()), split

    ind_whole = prep_ind(pbp, level="game", strength_state=False)
    ind_split = prep_ind(pbp, level="game", strength_state=True, score=True, teammates=True, opposition=True)
    counts = [c for c, dtype in ind_whole.schema.items() if dtype.is_integer() and c not in ("season", "game_id")]
    counts = [c for c in counts if not c.endswith("api_id")]
    assert ind_split.select(pl.col(counts).sum()).row(0) == ind_whole.select(pl.col(counts).sum()).row(0)

    for position in ("f", "d"):
        lines_whole = prep_lines(pbp, ext, position=position, level="game", **UNSPLIT)
        expected = _totals(lines_whole, TEAM_KEY, TEAM_COUNTS + ["toi"])
        for split in SPLITS:
            lines = prep_lines(pbp, ext, position=position, level="game", **UNSPLIT | split)
            totals = _totals(lines, TEAM_KEY, TEAM_COUNTS + ["toi"])
            assert totals.select(TEAM_COUNTS).equals(expected.select(TEAM_COUNTS)), (position, split)
            assert totals["toi"].to_list() == pytest.approx(expected["toi"].to_list()), (position, split)

    lines = prep_lines(pbp, ext, level="game", strength_state=True)
    assert _totals(lines, TEAM_KEY, ["gf"]).equals(whole.select(TEAM_KEY + ["gf"]).sort(TEAM_KEY))


def for_and_against_mirror(game) -> None:
    """What one team has for in a strength state, the other has against in the mirrored state."""
    team_stats = prep_team_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=True)
    rows = {(row["game_id"], row["team"], row["strength_state"]): row for row in team_stats.to_dicts()}

    for (game_id, team, state), row in rows.items():
        mirror = rows.get((game_id, row["opp_team"], _mirrored(state)))
        assert mirror is not None, (game_id, team, state)
        for stat in ("g", "s", "f", "c", "bs"):
            assert row[f"{stat}f"] == mirror[f"{stat}a"], (game_id, team, state, stat)
        assert row["toi"] == pytest.approx(mirror["toi"]), (game_id, team, state)


def corsi_is_fenwick_plus_blocked(game) -> None:
    """Corsi is Fenwick plus blocked attempts, for and against, in every output."""
    pbp, ext = game.play_by_play, game.play_by_play_ext
    for df in (
        prep_stats(pbp, ext, level="game", strength_state=True),
        prep_lines(pbp, ext, level="game", strength_state=True),
        prep_team_stats(pbp, ext, level="game", strength_state=True),
    ):
        assert (df["cf"] == df["ff"] + df["bsf"]).all()
        assert (df["ca"] == df["fa"] + df["bsa"]).all()


def ice_time_matches_the_shift_reports(game) -> None:
    """Each player's ice time equals the sum of their shifts."""
    stats = prep_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=False)
    shift_toi = game.shifts.group_by("game_id", "api_id").agg(shift_toi=pl.col("duration_seconds").sum() / 60)
    joined = stats.select("game_id", "api_id", "toi").join(
        shift_toi, on=["game_id", "api_id"], how="full", coalesce=True
    )

    assert joined.null_count().sum_horizontal().item() == 0
    assert joined.select(((pl.col("toi") - pl.col("shift_toi")).abs() < 1e-9).all()).item()


def identity_columns_are_a_key(game) -> None:
    """identity_columns names a key of stats, both kinds of lines and team stats, with every split on."""
    pbp, ext = game.play_by_play, game.play_by_play_ext
    stats = prep_stats(pbp, ext, level="game", strength_state=True, score=True, teammates=True, opposition=True)
    key = identity_columns("stats", level="game", strength_state=True, score=True, teammates=True, opposition=True)
    assert stats.select(key).n_unique() == stats.height

    for position in ("f", "d"):
        lines = prep_lines(
            pbp, ext, position=position, level="game", strength_state=True, score=True, teammates=True, opposition=True
        )
        key = identity_columns(
            "lines", position=position, level="game", strength_state=True, score=True, teammates=True, opposition=True
        )
        assert lines.select(key).n_unique() == lines.height, position

    team_stats = prep_team_stats(pbp, ext, level="game", strength_state=True, score=True, opposition=True)
    key = identity_columns("team_stats", level="game", strength_state=True, score=True, opposition=True)
    assert team_stats.select(key).n_unique() == team_stats.height


def season_totals_equal_the_sum_of_games(game) -> None:
    """Season and session rows equal the sum of the game rows, split by strength and score, for every count.

    Their rates and percentages then follow the summed counts, not the mean of the game rates.
    """
    pbp, ext = game.play_by_play, game.play_by_play_ext
    outputs = {
        "stats": (
            lambda level: prep_stats(pbp, ext, level=level, strength_state=True, score=True),
            lambda level: identity_columns("stats", level=level, strength_state=True, score=True),
        ),
        "forward lines": (
            lambda level: prep_lines(pbp, ext, position="f", level=level, strength_state=True, score=True),
            lambda level: identity_columns("lines", position="f", level=level, strength_state=True, score=True),
        ),
        "defense pairs": (
            lambda level: prep_lines(pbp, ext, position="d", level=level, strength_state=True, score=True),
            lambda level: identity_columns("lines", position="d", level=level, strength_state=True, score=True),
        ),
        "team_stats": (
            lambda level: prep_team_stats(pbp, ext, level=level, strength_state=True, score=True),
            lambda level: identity_columns("team_stats", level=level, strength_state=True, score=True),
        ),
    }
    for name, (prep, identity) in outputs.items():
        by_game = prep("game")
        for level in ("season", "session"):
            key = identity(level)
            rolled = prep(level).sort(key)
            counts = [
                c
                for c, dtype in rolled.schema.items()
                if dtype.is_numeric() and c not in key and not c.endswith(("_p60", "_percent"))
            ]
            expected = _totals(by_game, key, counts)
            assert rolled.select(key).equals(expected.select(key)), (name, level)
            for column in counts:
                assert rolled[column].to_list() == pytest.approx(expected[column].to_list(), abs=1e-9), (
                    name,
                    level,
                    column,
                )
            _check_rates(f"{name} {level}", rolled)


# -----------------------------------------------------------------------------
# Oracles: values rebuilt from play-by-play rows without the package's own aggregation
# -----------------------------------------------------------------------------

ATTEMPTS = ["GOAL", "SHOT", "MISS", "BLOCK"]

# Each score-adjusted play-by-play column and the table weight it uses
ADJUSTED_WEIGHT = {
    "goal": "goal",
    "shot": "shot",
    "miss": "fenwick",
    "block": "corsi",
    "teammate_block": "corsi",
    "fenwick": "fenwick",
    "corsi": "corsi",
}

# Disadvantage states are looked up through their mirror, from the other side's weights
MIRRORED_STATES = {"4v5": "5v4", "3v5": "5v3", "3v4": "4v3"}
TABLE_STATES = ("5v5", "4v4", "3v3", "5v4", "5v3", "4v3")


def _weight_table() -> pl.DataFrame:
    """One row per table state, clamped home score difference, side and weight column."""
    table = load_score_adjustments()
    rows = [
        (state, diff, side, base, weights[f"{side}_{base}_weight"])
        for state in TABLE_STATES
        for diff, weights in table[state].items()
        for side in ("home", "away")
        for base in ("goal", "shot", "fenwick", "corsi")
    ]
    return pl.DataFrame(rows, schema=["_state", "_diff", "_side", "_base", "_weight"], orient="row")


def _attempts(pbp: pl.DataFrame) -> pl.DataFrame:
    """Shot attempts outside a shootout, with the shooting team and its strength state.

    A blocked shot's event team is the blocking team, unless a teammate blocked it.
    """
    blocked = (pl.col("event") == "BLOCK") & (pl.col("teammate_block") == 0)
    return pbp.filter(pl.col("event").is_in(ATTEMPTS), pl.col("shootout_attempt") != 1).with_columns(
        _shooter=pl.when(blocked).then(pl.col("opp_team")).otherwise(pl.col("event_team")),
        _shooter_state=pl.when(blocked).then(pl.col("opp_strength_state")).otherwise(pl.col("strength_state")),
    )


def _expected_adjusted(pbp: pl.DataFrame) -> pl.DataFrame:
    """Shot attempts with ``_expected_<column>_adj``: the raw value times its weight from the table, or 1.0 off it."""
    rows = _attempts(pbp).with_columns(
        _state=pl.col("_shooter_state").replace(MIRRORED_STATES),
        _diff=pl.col("home_score_diff").clip(-3, 3),
        _side=pl.when(
            (pl.col("_shooter") == pl.col("home_team")) != pl.col("_shooter_state").is_in(list(MIRRORED_STATES))
        )
        .then(pl.lit("home"))
        .otherwise(pl.lit("away")),
    )
    weights = _weight_table()
    for column, base in ADJUSTED_WEIGHT.items():
        weight = weights.filter(pl.col("_base") == base).drop("_base").rename({"_weight": f"_weight_{column}"})
        rows = rows.join(weight, on=["_state", "_diff", "_side"], how="left", maintain_order="left")
        rows = rows.with_columns(
            (pl.col(column) * pl.col(f"_weight_{column}").fill_null(1.0)).alias(f"_expected_{column}_adj")
        )
    return rows


def score_adjusted_counts_use_the_table_weights(game) -> None:
    """Every shot attempt's adjusted columns are its raw values times the table weight for its score and strength."""
    rows = _expected_adjusted(game.play_by_play)
    for column in ADJUSTED_WEIGHT:
        expected = rows[f"_expected_{column}_adj"].to_list()
        assert rows[f"{column}_adj"].to_list() == pytest.approx(expected, abs=1e-12), column

    others = game.play_by_play.filter(~pl.col("event").is_in(ATTEMPTS))
    assert (
        others.select(pl.col([f"{c}_adj" for c in ADJUSTED_WEIGHT]).fill_null(0).abs().max()).max_horizontal().item()
        == 0
    )


# Team adjusted columns and the play-by-play column they sum; blocked attempts include teammate blocks
TEAM_ADJUSTED = {
    "gf_adj": "_expected_goal_adj",
    "sf_adj": "_expected_shot_adj",
    "ff_adj": "_expected_fenwick_adj",
    "msf_adj": "_expected_miss_adj",
    "bsf_adj": "_expected_blocked_adj",
    "cf_adj": "_expected_corsi_adj",
}


def team_adjusted_counts_add_up_from_the_rows(game) -> None:
    """A team's adjusted counts in each strength state are the sums of its own attempts' oracle values."""
    rows = _expected_adjusted(game.play_by_play).with_columns(
        _expected_blocked_adj=pl.col("_expected_block_adj") + pl.col("_expected_teammate_block_adj")
    )
    expected = rows.group_by("game_id", team="_shooter", strength_state="_shooter_state").agg(
        pl.col(source).sum().alias(f"_expected_{stat}") for stat, source in TEAM_ADJUSTED.items()
    )
    team_stats = prep_team_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=True)
    joined = team_stats.join(expected, on=["game_id", "team", "strength_state"], how="full", coalesce=True).fill_null(0)

    for stat in TEAM_ADJUSTED:
        assert joined[stat].to_list() == pytest.approx(joined[f"_expected_{stat}"].to_list(), abs=1e-9), stat


# On-ice for columns and the play-by-play column each sums; the against column is the same count from the other side
ON_ICE = {
    "gf": ("ga", "goal"),
    "sf": ("sa", "shot"),
    "ff": ("fa", "fenwick"),
    "msf": ("msa", "miss"),
    "bsf": ("bsa", "_blocked"),
    "cf": ("ca", "corsi"),
    "gf_adj": ("ga_adj", "goal_adj"),
    "sf_adj": ("sa_adj", "shot_adj"),
    "ff_adj": ("fa_adj", "fenwick_adj"),
    "msf_adj": ("msa_adj", "miss_adj"),
    "bsf_adj": ("bsa_adj", "_blocked_adj"),
    "cf_adj": ("ca_adj", "corsi_adj"),
}


def _on_ice_rows(rows: pl.DataFrame) -> pl.DataFrame:
    """One row per player on the ice for each play, with the player's team, strength state and ``_for`` side."""
    away_team = (
        pl.when(pl.col("event_team") == pl.col("home_team")).then(pl.col("opp_team")).otherwise(pl.col("event_team"))
    )
    sides = [
        rows.with_columns(_team=team, api_id=pl.col(column).str.split(", ")).explode("api_id", empty_as_null=True)
        for column, team in (("home_on_api_id", pl.col("home_team")), ("away_on_api_id", away_team))
    ]
    return (
        pl.concat(sides)
        .filter(pl.col("api_id").is_not_null(), pl.col("api_id") != "")
        .with_columns(
            api_id=pl.col("api_id").cast(pl.Int64),
            strength_state=pl.when(pl.col("_team") == pl.col("event_team"))
            .then(pl.col("strength_state"))
            .otherwise(pl.col("opp_strength_state")),
        )
    )


def on_ice_counts_add_up_from_the_rows(game) -> None:
    """Each player's on-ice counts, raw and adjusted, for and against, are sums over the plays they were on for."""
    rows = _attempts(game.play_by_play).with_columns(
        _blocked=pl.col("block") + pl.col("teammate_block"),
        _blocked_adj=pl.col("block_adj") + pl.col("teammate_block_adj"),
    )
    players = _on_ice_rows(rows).with_columns(_for=pl.col("_team") == pl.col("_shooter"))
    aggregations = []
    for stat, (against, source) in ON_ICE.items():
        aggregations.append(pl.col(source).filter(pl.col("_for")).sum().alias(f"_expected_{stat}"))
        aggregations.append(pl.col(source).filter(~pl.col("_for")).sum().alias(f"_expected_{against}"))
    expected = players.group_by("api_id", "strength_state").agg(aggregations)

    columns = [name for stat, (against, _) in ON_ICE.items() for name in (stat, against)]
    stats = prep_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=True)
    stats = stats.group_by("api_id", "strength_state").agg(pl.col(columns).sum())
    joined = stats.join(expected, on=["api_id", "strength_state"], how="full", coalesce=True).fill_null(0)

    for column in columns:
        assert joined[column].to_list() == pytest.approx(joined[f"_expected_{column}"].to_list(), abs=1e-9), column


def individual_corsi_adds_up_from_the_rows(game) -> None:
    """Each player's individual Corsi, raw and adjusted, is the sum over the attempts they took.

    A blocked shot's shooter is ``player_2``; every other attempt's is ``player_1``.
    """
    rows = _attempts(game.play_by_play).with_columns(
        api_id=pl.when(pl.col("event") == "BLOCK").then(pl.col("player_2_api_id")).otherwise(pl.col("player_1_api_id"))
    )
    expected = rows.group_by("api_id").agg(
        _expected_icf=pl.col("corsi").sum(), _expected_icf_adj=pl.col("corsi_adj").sum()
    )
    ind = prep_ind(game.play_by_play, level="game").group_by("api_id").agg(pl.col("icf", "icf_adj").sum())
    joined = ind.join(expected, on="api_id", how="full", coalesce=True).fill_null(0)

    for column in ("icf", "icf_adj"):
        assert joined[column].to_list() == pytest.approx(joined[f"_expected_{column}"].to_list(), abs=1e-9), column


# High-danger columns and the raw column each one flags
HIGH_DANGER = {"hd_goal": "goal", "hd_shot": "shot", "hd_fenwick": "fenwick", "hd_miss": "miss"}

# On-ice high-danger columns and the play-by-play column each sums, for and against
ON_ICE_HIGH_DANGER = {
    "hdgf": ("hdga", "hd_goal"),
    "hdsf": ("hdsa", "hd_shot"),
    "hdff": ("hdfa", "hd_fenwick"),
    "hdmsf": ("hdmsa", "hd_miss"),
}


def danger_flags_follow_the_shot_location(game) -> None:
    """Only Fenwick attempts from the offensive zone carry a danger flag, and high danger is exactly the slot box.

    The box runs from 69 to 89 feet out on either end and 9 feet either side of center. danger marks the
    surrounding area and never overlaps high_danger. Each hd_* column is its raw column where high_danger is set.
    """
    pbp = game.play_by_play
    fenwick_from_the_zone = pl.col("event").is_in(["GOAL", "SHOT", "MISS"]) & (pl.col("zone") == "OFF")
    in_the_box = pl.col("coords_x").abs().is_between(69, 89) & pl.col("coords_y").is_between(-9, 9)

    flagged = pbp.filter((pl.col("danger") == 1) | (pl.col("high_danger") == 1))
    assert flagged.filter(~fenwick_from_the_zone.fill_null(False)).is_empty()
    assert pbp.filter((pl.col("danger") == 1) & (pl.col("high_danger") == 1)).is_empty()

    expected = (fenwick_from_the_zone & in_the_box).fill_null(False).cast(pl.Int64)
    assert pbp["high_danger"].to_list() == pbp.select(expected)[:, 0].to_list()

    for column, raw in HIGH_DANGER.items():
        assert pbp[column].to_list() == (pbp[raw] * pbp["high_danger"]).to_list(), column

    rows = _attempts(pbp)
    players = _on_ice_rows(rows).with_columns(_for=pl.col("_team") == pl.col("_shooter"))
    aggregations = []
    for stat, (against, source) in ON_ICE_HIGH_DANGER.items():
        aggregations.append(pl.col(source).filter(pl.col("_for")).sum().alias(f"_expected_{stat}"))
        aggregations.append(pl.col(source).filter(~pl.col("_for")).sum().alias(f"_expected_{against}"))
    expected_on_ice = players.group_by("api_id", "strength_state").agg(aggregations)

    columns = [name for stat, (against, _) in ON_ICE_HIGH_DANGER.items() for name in (stat, against)]
    stats = prep_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=True)
    stats = stats.group_by("api_id", "strength_state").agg(pl.col(columns).sum())
    joined = stats.join(expected_on_ice, on=["api_id", "strength_state"], how="full", coalesce=True).fill_null(0)
    for column in columns:
        assert joined[column].to_list() == joined[f"_expected_{column}"].to_list(), column

    team = rows.group_by(team="_shooter").agg(
        pl.col(source).sum().alias(stat) for stat, (_, source) in ON_ICE_HIGH_DANGER.items()
    )
    team_stats = prep_team_stats(game.play_by_play, game.play_by_play_ext, level="game")
    team_stats = team_stats.group_by("team").agg(pl.col(list(ON_ICE_HIGH_DANGER)).sum())
    joined = team_stats.join(team, on="team", how="full", coalesce=True, suffix="_expected").fill_null(0)
    for stat in ON_ICE_HIGH_DANGER:
        assert joined[stat].to_list() == joined[f"{stat}_expected"].to_list(), stat


# Play-by-play counts and the on-ice and team columns they become, for the event team and against it
EVENT_COUNTS = {
    "hit": ("hf", "ht"),
    "give": ("give", None),
    "take": ("take", None),
    "fac": ("fow", "fol"),
    # The zone is the winner's, so the loser's offensive zone is the winner's defensive zone
    "ozf": ("ozfw", "dzfl"),
    "nzf": ("nzfw", "nzfl"),
    "dzf": ("dzfw", "ozfl"),
    "teammate_block": ("teammate_block", "opp_teammate_block"),
    **{f"pen{minutes}": (f"pent{minutes}", f"pend{minutes}") for minutes in (0, 2, 4, 5, 10)},
}

# Zone starts, counted for the players coming on at a change
ZONE_STARTS = {"ozc": "ozs", "nzc": "nzs", "dzc": "dzs", "otf": "otf"}


def _expected_event_counts(rows: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Sum each event count for the event team's side and the other side, grouped by ``keys``."""
    aggregations = []
    for source, (stat, against) in EVENT_COUNTS.items():
        aggregations.append(pl.col(source).filter(pl.col("_for")).sum().alias(stat))
        if against is not None:
            aggregations.append(pl.col(source).filter(~pl.col("_for")).sum().alias(against))
    return rows.group_by(keys).agg(aggregations)


def _compare(actual: pl.DataFrame, expected: pl.DataFrame, keys: list[str], columns: list[str]) -> None:
    """Assert that ``actual`` summed by ``keys`` equals ``expected`` in every column, a missing group counting 0."""
    actual = actual.group_by(keys).agg(pl.col(columns).sum())
    joined = actual.join(expected, on=keys, how="full", coalesce=True, suffix="_expected").fill_null(0)
    for column in columns:
        assert joined[column].to_list() == joined[f"{column}_expected"].to_list(), column


def event_counts_add_up_on_ice_and_by_team(game) -> None:
    """Hits, giveaways, takeaways, faceoffs, teammate blocks, penalties and zone starts add up from the rows.

    Each count goes to the players on the ice and the team, for the event team and against the other, and the
    zone starts to the players coming on at a change.
    """
    pbp, ext = game.play_by_play, game.play_by_play_ext
    rows = pbp.filter(pl.col("event_team").is_not_null())
    players = _on_ice_rows(rows).with_columns(_for=pl.col("_team") == pl.col("event_team"))
    columns = [c for pair in EVENT_COUNTS.values() for c in pair if c is not None]

    stats = prep_stats(pbp, ext, level="game", strength_state=True)
    keys = ["api_id", "strength_state"]
    _compare(stats, _expected_event_counts(players, keys), keys, columns)

    changes = (
        pbp.filter(pl.col("event") == "CHANGE")
        .with_columns(api_id=pl.col("change_on_api_id").str.split(", "))
        .explode("api_id", empty_as_null=True)
        .filter(pl.col("api_id").is_not_null(), pl.col("api_id") != "")
        .with_columns(api_id=pl.col("api_id").cast(pl.Int64))
        .group_by(keys)
        .agg(pl.col(source).sum().alias(stat) for source, stat in ZONE_STARTS.items())
    )
    _compare(stats, changes, keys, list(ZONE_STARTS.values()))

    teams = pl.concat(
        [
            rows.select(pl.all(), team=pl.col("event_team"), _for=pl.lit(True)),
            rows.select(
                pl.exclude("strength_state"),
                team=pl.col("opp_team"),
                strength_state=pl.col("opp_strength_state"),
                _for=pl.lit(False),
            ),
        ],
        how="diagonal",
    )
    keys = ["team", "strength_state"]
    expected = _expected_event_counts(teams, keys)
    _compare(prep_team_stats(pbp, ext, level="game", strength_state=True), expected, keys, columns)
    for position in ("f", "d"):
        lines = prep_lines(pbp, ext, position=position, level="game", strength_state=True)
        _compare(lines, expected, keys, columns)


def score_state_follows_the_goals(game) -> None:
    """Each row's score is the goals each team scored before it, outside the shootout, from the event team's side.

    From the end of a shootout on, the winner has one more goal, as in the final score. Team goals for and against
    in each score state are the goals scored in it, so a swapped label fails.
    """
    pbp = game.play_by_play.sort("game_id", "event_idx")
    goal = (pl.col("event") == "GOAL") & (pl.col("shootout_attempt") != 1)
    shootout_goal = (pl.col("event") == "GOAL") & (pl.col("shootout_attempt") == 1)

    def scored(team: str) -> pl.Expr:
        """Goals by the home or away team before each row of its game, with one for winning the shootout."""
        own, other = pl.col(f"{team}_team"), pl.col("away_team" if team == "home" else "home_team")
        before = (goal & (pl.col("event_team") == own)).cast(pl.Int64).cum_sum().shift(1, fill_value=0)
        won_shootout = (shootout_goal & (pl.col("event_team") == own)).sum() > (
            shootout_goal & (pl.col("event_team") == other)
        ).sum()
        after_shootout = (pl.col("event") == "SOC").cum_sum() > 0
        return (before + (after_shootout & won_shootout).cast(pl.Int64)).over("game_id")

    before = pbp.with_columns(_home=scored("home"), _away=scored("away"))
    assert before["home_score"].to_list() == before["_home"].to_list()
    assert before["away_score"].to_list() == before["_away"].to_list()

    with_team = before.filter(pl.col("event_team").is_not_null())
    at_home = pl.col("event_team") == pl.col("home_team")
    own = pl.when(at_home).then(pl.col("_home")).otherwise(pl.col("_away"))
    other = pl.when(at_home).then(pl.col("_away")).otherwise(pl.col("_home"))
    expected = with_team.select(
        score_state=pl.format("{}v{}", own, other),
        opp_score_state=pl.format("{}v{}", other, own),
        score_diff=own - other,
    )
    assert with_team.select(expected.columns).equals(expected)

    pbp, ext = game.play_by_play, game.play_by_play_ext
    goals = pbp.filter(goal)
    expected = (
        pl.concat(
            [
                goals.select("game_id", team="event_team", score_state="score_state", gf=pl.lit(1), ga=pl.lit(0)),
                goals.select("game_id", team="opp_team", score_state="opp_score_state", gf=pl.lit(0), ga=pl.lit(1)),
            ]
        )
        .group_by("game_id", "team", "score_state")
        .agg(pl.col("gf", "ga").sum())
    )
    team_stats = prep_team_stats(pbp, ext, level="game", score=True)
    _compare(team_stats, expected, ["game_id", "team", "score_state"], ["gf", "ga"])


def _against(stat: str) -> str:
    """The against column a percentage divides by, from the test's own naming rule: gf_adj to ga_adj, take to give."""
    special = {"take": "give", "hf": "ht"}
    if stat in special:
        return special[stat]
    base, adjusted = (stat[:-4], "_adj") if stat.endswith("_adj") else (stat, "")
    assert base.endswith("f"), stat
    return f"{base[:-1]}a{adjusted}"


def _check_rates(name: str, df: pl.DataFrame) -> None:
    """Assert that every per-60 rate and percentage in a frame follows the counts in the same row."""
    rates = [c for c in df.columns if c.endswith("_p60")]
    percentages = [c for c in df.columns if c.endswith("_percent")]
    assert rates and percentages, name

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
        actual, wanted = df[column], expected[column]
        assert actual.is_null().to_list() == wanted.is_null().to_list(), (name, column)
        assert actual.drop_nulls().to_list() == pytest.approx(wanted.drop_nulls().to_list(), abs=1e-12), (name, column)


def rates_and_percentages_follow_their_counts(game) -> None:
    """Every per-60 rate is its count over ice time, and every percentage is for over for plus against.

    A rate with no ice time and a percentage with nothing on either side are null.
    """
    pbp, ext = game.play_by_play, game.play_by_play_ext
    _check_rates("stats", prep_stats(pbp, ext, level="game", strength_state=True))
    _check_rates("lines", prep_lines(pbp, ext, level="game", strength_state=True))
    _check_rates("team_stats", prep_team_stats(pbp, ext, level="game", strength_state=True))


def lineup_columns_hold_null_not_empty(game) -> None:
    """An empty lineup or a pulled goalie is null in every output, never '' (bB-03)."""
    pbp, ext = game.play_by_play, game.play_by_play_ext
    splits = {"level": "game", "strength_state": True, "score": True, "teammates": True, "opposition": True}
    outputs = {
        "stats": prep_stats(pbp, ext, **splits),
        "lines_f": prep_lines(pbp, ext, position="f", **splits),
        "lines_d": prep_lines(pbp, ext, position="d", **splits),
    }
    for name, df in outputs.items():
        strings = [c for c, dtype in df.schema.items() if dtype == pl.String]
        assert not [c for c in strings if (df[c] == "").any()], name


INVARIANTS = [
    totals_agree_however_split,
    for_and_against_mirror,
    corsi_is_fenwick_plus_blocked,
    ice_time_matches_the_shift_reports,
    identity_columns_are_a_key,
    season_totals_equal_the_sum_of_games,
    score_adjusted_counts_use_the_table_weights,
    team_adjusted_counts_add_up_from_the_rows,
    on_ice_counts_add_up_from_the_rows,
    individual_corsi_adds_up_from_the_rows,
    danger_flags_follow_the_shot_location,
    event_counts_add_up_on_ice_and_by_team,
    score_state_follows_the_goals,
    rates_and_percentages_follow_their_counts,
    lineup_columns_hold_null_not_empty,
]
