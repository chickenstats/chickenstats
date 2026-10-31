"""Value tests against the offline fixture for game 2023020001 (NSH at TBL, TBL won 5-3).

The expected numbers come from the NHL API response and HTML reports saved in ``mock_data``.
Where a number can be read from the raw API response it is compared with that response; the
rest are pinned. A deliberate change to an output should update the number here in the same commit.
"""

import itertools
import json
import logging
import os
from unittest.mock import patch

import polars as pl
import pytest

from chickenstats.chicken_nhl import (
    Game,
    Scraper,
    prep_ind,
    prep_lines,
    prep_oi,
    prep_stats,
    prep_stints,
    prep_team_stats,
)

from chickenstats.chicken_nhl._game_utils import prepare_xg
from test_live_games import LIVE_DATA_DIR, snapshot_session_get

# How one team's strength state reads from the other bench
MIRRORED_STATE = {"5v5": "5v5", "5v4": "4v5", "4v5": "5v4", "5vE": "Ev5", "Ev5": "5vE", "1v0": "0v1", "0v1": "1v0"}


# -----------------------------------------------------------------------------
# Scraped frames
# -----------------------------------------------------------------------------


def test_frame_heights(fixture_game):
    """Each scraped frame has the number of rows the reports contain."""
    assert fixture_game.failed_games == []
    assert fixture_game.play_by_play.height == 781
    assert fixture_game.play_by_play_ext.height == 781
    assert fixture_game.rosters.height == 46
    assert fixture_game.html_rosters.height == 46
    assert fixture_game.api_rosters.height == 40
    assert fixture_game.shifts.height == 743
    assert fixture_game.changes.height == 450
    assert fixture_game.html_events.height == 331
    assert fixture_game.api_events.height == 328

    assert dict(fixture_game.rosters["status"].value_counts().rows()) == {"ACTIVE": 40, "SCRATCH": 6}
    assert dict(fixture_game.shifts["team"].value_counts().rows()) == {"TBL": 359, "NSH": 384}


def test_final_score_and_shots_match_api_box_score(fixture_game, fixture_api_response):
    """The running score and the shots on goal agree with the box score in the API response."""
    play_by_play = fixture_game.play_by_play
    home, away = fixture_api_response["homeTeam"], fixture_api_response["awayTeam"]

    assert (home["abbrev"], home["score"], home["sog"]) == ("TBL", 5, 34)
    assert (away["abbrev"], away["score"], away["sog"]) == ("NSH", 3, 31)

    last_event = play_by_play.tail(1)
    assert last_event["event"].item() == "GEND"
    assert (last_event["home_score"].item(), last_event["away_score"].item()) == (home["score"], away["score"])

    totals = {
        row["event_team"]: row
        for row in play_by_play.group_by("event_team").agg(pl.col("goal", "shot").sum()).to_dicts()
    }
    assert (totals["TBL"]["goal"], totals["TBL"]["shot"]) == (home["score"], home["sog"])
    assert (totals["NSH"]["goal"], totals["NSH"]["shot"]) == (away["score"], away["sog"])


def test_goal_scorers_and_assists_match_api(fixture_game, fixture_api_response):
    """Every goal row carries the scorer and assists the API response lists, in order."""
    goals = (
        fixture_game.play_by_play.filter(pl.col("event") == "GOAL")
        .select("player_1_api_id", "player_2_api_id", "player_3_api_id")
        .rows()
    )
    expected = [
        (
            play["details"].get("scoringPlayerId"),
            play["details"].get("assist1PlayerId"),
            play["details"].get("assist2PlayerId"),
        )
        for play in fixture_api_response["plays"]
        if play["typeDescKey"] == "goal"
    ]

    assert goals == expected
    assert goals[0] == (8476453, 8475167, 8478010)  # Kucherov from Hedman and Point
    assert goals[4] == (8479542, None, None)  # Hagel, penalty shot


def test_event_counts(fixture_game):
    """The play-by-play has the number of each event the reports list."""
    counts = dict(fixture_game.play_by_play["event"].value_counts().rows())
    expected = {
        "GOAL": 8,
        "SHOT": 57,
        "MISS": 31,
        "BLOCK": 30,
        "FAC": 60,
        "HIT": 45,
        "GIVE": 15,
        "TAKE": 18,
        "PENL": 10,
        "CHANGE": 450,
        "STOP": 44,
    }

    assert {event: counts[event] for event in expected} == expected


def test_event_lengths_cover_the_game(fixture_game):
    """Event lengths add up to 60 minutes, split across the strength states."""
    play_by_play = fixture_game.play_by_play
    seconds = dict(play_by_play.group_by("strength_state").agg(pl.col("event_length").sum()).rows())

    assert play_by_play["event_length"].sum() == 3600
    assert {state: seconds[state] for state in ("5v5", "5v4", "4v5", "Ev5", "5vE")} == {
        "5v5": 2478,
        "5v4": 529,
        "4v5": 429,
        "Ev5": 105,
        "5vE": 59,
    }


# -----------------------------------------------------------------------------
# Aggregations without a strength split
# -----------------------------------------------------------------------------


def test_player_toi_matches_shift_report(fixture_game):
    """A player's time on ice equals the sum of their shifts in the HTML shift reports."""
    stats = prep_stats(
        fixture_game.play_by_play, fixture_game.play_by_play_ext, level="game", strength_state=False
    ).select("api_id", "toi")
    shift_toi = fixture_game.shifts.group_by("api_id").agg((pl.col("duration_seconds").sum() / 60).alias("shift_toi"))
    joined = stats.join(shift_toi, on="api_id", how="full")

    assert joined.height == 38
    assert joined.null_count().sum_horizontal().item() == 0
    assert joined.select(((pl.col("toi") - pl.col("shift_toi")).abs() < 1e-9).all()).item()
    assert dict(stats.rows())[8475167] == pytest.approx(26 + 55 / 60)  # Hedman, 26:55


def test_individual_totals(fixture_game):
    """Individual stats add up to the event counts in the play-by-play."""
    ind_stats = prep_ind(fixture_game.play_by_play, level="game", strength_state=False)
    columns = ["g", "a1", "a2", "isf", "iff", "icf", "ihf", "iht", "igive", "itake", "ifow", "ifol"]

    assert ind_stats.select(pl.col(columns).sum()).row(0) == (8, 7, 6, 65, 96, 126, 45, 45, 15, 18, 60, 60)

    nick_paul = ind_stats.filter(pl.col("api_id") == 8477426).select("g", "a1", "a2", "isf", "iff", "icf").row(0)
    assert nick_paul == (2, 1, 0, 3, 5, 6)


def test_team_stats_game_rows(fixture_game):
    """Each team's game row matches the box score, and the two rows mirror each other."""
    team_stats = prep_team_stats(
        fixture_game.play_by_play, fixture_game.play_by_play_ext, level="game", strength_state=False
    )
    tbl = team_stats.filter(pl.col("team") == "TBL").to_dicts()[0]
    nsh = team_stats.filter(pl.col("team") == "NSH").to_dicts()[0]

    assert (tbl["toi"], nsh["toi"]) == (60.0, 60.0)

    for_against = ["gf", "ga", "sf", "sa", "ff", "fa", "cf", "ca"]
    assert [tbl[column] for column in for_against] == [5, 3, 34, 31, 50, 46, 61, 65]
    assert [nsh[column] for column in for_against] == [3, 5, 31, 34, 46, 50, 65, 61]

    assert [tbl[column] for column in ("bsf", "bsa", "hf", "ht", "fow", "fol")] == [11, 19, 22, 23, 34, 26]
    assert tbl["gf_percent"] == pytest.approx(5 / 8)
    assert tbl["cf_percent"] == pytest.approx(61 / 126)


def test_stints_cover_the_game(fixture_game):
    """Stints add up to 60 minutes and to the box score, less the penalty-shot goal."""
    stints = prep_stints(fixture_game.play_by_play)
    columns = ["home_gf", "away_gf", "home_sf", "away_sf", "home_cf", "away_cf"]

    assert stints.height == 385
    assert stints["toi"].sum() == 3600
    # Tampa Bay's penalty-shot goal has one skater on ice, so it is not part of any stint
    assert stints.select(pl.col(columns).sum()).row(0) == (4, 3, 33, 31, 60, 65)


# -----------------------------------------------------------------------------
# Aggregations with the default strength split
# -----------------------------------------------------------------------------


def test_team_stats_by_strength_match_play_by_play(fixture_game):
    """Each team's goals and shots in a strength state equal the play-by-play rows for that state."""
    team_stats = prep_team_stats(fixture_game.play_by_play, fixture_game.play_by_play_ext)
    direct = {
        (row["event_team"], row["strength_state"]): (row["goal"], row["shot"])
        for row in fixture_game.play_by_play.group_by("event_team", "strength_state")
        .agg(pl.col("goal", "shot").sum())
        .to_dicts()
    }

    # Includes Tampa Bay's 1v0 row and Nashville's 0v1 row from the penalty-shot goal
    assert team_stats.height == 10
    for row in team_stats.to_dicts():
        assert (row["gf"], row["sf"]) == direct.get((row["team"], row["strength_state"]), (0, 0))

    five_on_five = team_stats.filter(pl.col("team") == "TBL", pl.col("strength_state") == "5v5").to_dicts()[0]
    assert five_on_five["toi"] == pytest.approx(2478 / 60)
    assert [five_on_five[column] for column in ("gf", "ga", "sf", "sa", "cf", "ca")] == [1, 2, 22, 18, 42, 38]


def assert_rates_and_percentages_are_null_when_not_applicable(df: pl.DataFrame) -> None:
    """No float column holds an infinity or NaN; rates without ice time and empty percentages are null."""
    floats = [c for c, dtype in df.schema.items() if dtype == pl.Float64]
    assert df.select(pl.col(floats).is_infinite().any() | pl.col(floats).is_nan().any()).sum_horizontal().item() == 0

    no_toi = df.filter(pl.col("toi") == 0)
    rates = [c for c in df.columns if c.endswith("_p60")]
    assert no_toi.select(pl.col(rates).is_not_null().sum()).sum_horizontal().item() == 0

    if "cf_percent" in df.columns:
        empty = df.filter(pl.col("cf") + pl.col("ca") == 0)
        assert empty["cf_percent"].null_count() == empty.height


@pytest.mark.parametrize("prep", [prep_stats, prep_lines, prep_team_stats])
@pytest.mark.parametrize("level", ["period", "game"])
def test_rates_and_percentages_with_nothing_to_divide_by_are_null(fixture_game, prep, level):
    """Rows with no ice time have null rates, and percentages with nothing on either side are null."""
    df = prep(fixture_game.play_by_play, fixture_game.play_by_play_ext, level=level)

    assert df.filter(pl.col("toi") == 0).height > 0
    assert_rates_and_percentages_are_null_when_not_applicable(df)


@pytest.mark.parametrize("opposition", [False, True])
def test_team_and_line_counts_are_the_same_with_and_without_a_strength_split(fixture_game, opposition):
    """Splitting by strength state moves events between rows but never drops one."""
    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext
    counts = ["gf", "ga", "sf", "sa", "ff", "fa", "cf", "ca", "ozf", "nzf", "dzf", "hf", "ht"]

    for prep in (prep_team_stats, prep_lines):
        split = prep(pbp, pbp_ext, opposition=opposition)
        unsplit = prep(pbp, pbp_ext, strength_state=False, opposition=opposition)

        assert split.select(pl.col(counts).sum()).row(0) == unsplit.select(pl.col(counts).sum()).row(0), prep


def test_zone_faceoffs_mirror_between_the_teams_in_every_output(fixture_game):
    """One team's offensive-zone faceoffs are the other team's defensive-zone faceoffs."""
    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext

    def by_team(df, offensive, defensive):
        totals = df.group_by("team").agg(pl.col(offensive).sum(), pl.col(defensive).sum())
        return {row["team"]: (row[offensive], row[defensive]) for row in totals.to_dicts()}

    ind = prep_ind(pbp, level="game", strength_state=False)
    ind_totals = ind.with_columns(iozf=pl.col("iozfw") + pl.col("iozfl"), idzf=pl.col("idzfw") + pl.col("idzfl"))

    for totals in (
        by_team(prep_team_stats(pbp, pbp_ext, strength_state=False), "ozf", "dzf"),
        by_team(prep_lines(pbp, pbp_ext, strength_state=False), "ozf", "dzf"),
        by_team(ind_totals, "iozf", "idzf"),
    ):
        assert totals == {"TBL": (24, 19), "NSH": (19, 24)}

    # A win in one zone is the other team's loss in the opposite zone
    wins, losses = by_team(ind, "iozfw", "idzfw"), by_team(ind, "idzfl", "iozfl")
    assert (wins["TBL"], wins["NSH"]) == (losses["NSH"], losses["TBL"])


def test_blocked_shots_count_every_blocked_attempt(fixture_game):
    """bsf and bsa include teammate blocks, so Corsi is Fenwick plus blocked attempts in every output.

    cf_adj weights every attempt, blocked or not, by the Corsi weight, so it is not ff_adj plus bsf_adj; the
    invariants check it against the play-by-play.
    """
    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext
    outputs = [
        prep_stats(pbp, pbp_ext, level="game", strength_state=True),
        prep_lines(pbp, pbp_ext, level="game", strength_state=True),
        prep_team_stats(pbp, pbp_ext, level="game", strength_state=True),
    ]

    for df in outputs:
        assert (df["cf"] == df["ff"] + df["bsf"]).all()
        assert (df["ca"] == df["fa"] + df["bsa"]).all()

    team_stats = outputs[2].group_by("team").agg(pl.col("bsf", "bsa", "teammate_block", "opp_teammate_block").sum())
    assert dict((row[0], row[1:]) for row in team_stats.rows()) == {"NSH": (19, 11, 2, 1), "TBL": (11, 19, 1, 2)}


SPLITS = list(itertools.product([False, True], repeat=4))


def assert_individual_sums_match(game, strength_state, score, teammates, opposition):
    flags = {"level": "game", "strength_state": strength_state, "score": score}
    ind = prep_ind(game.play_by_play, teammates=teammates, opposition=opposition, **flags)
    stats = prep_stats(game.play_by_play, game.play_by_play_ext, teammates=teammates, opposition=opposition, **flags)
    counts = [
        c
        for c, dtype in ind.schema.items()
        if dtype.is_integer() and c not in ("season", "game_id") and not c.endswith("api_id")
    ]

    assert stats.select(pl.col(counts).sum()).row(0) == ind.select(pl.col(counts).sum()).row(0), counts


@pytest.mark.parametrize("strength_state, score, teammates, opposition", SPLITS)
def test_stats_keep_every_individual_event(fixture_game, strength_state, score, teammates, opposition):
    """An event credited to a player with no on-ice row in its group, such as a secondary assist, is kept."""
    assert_individual_sums_match(fixture_game, strength_state, score, teammates, opposition)


@pytest.mark.parametrize("fixture", ["shootout_game", "long_shootout_game", "playoff_overtime_game"])
def test_stats_keep_every_individual_event_in_other_games(request, fixture):
    assert_individual_sums_match(request.getfixturevalue(fixture), True, True, True, True)


@pytest.mark.parametrize("fixture", ["fixture_game", "shootout_game", "long_shootout_game", "playoff_overtime_game"])
def test_zone_starts_have_their_faceoffs_strength_state(request, fixture):
    """A zone start is filed under the state the faceoff is played at, not one team's change alone."""
    play_by_play = request.getfixturevalue(fixture).play_by_play
    zone_starts = play_by_play.filter(pl.col("event") == "CHANGE", pl.col("zone_start").is_in(["OFF", "DEF", "NEU"]))
    faceoffs = play_by_play.filter(pl.col("event") == "FAC").unique(["period", "game_seconds"], keep="first")
    joined = zone_starts.join(
        faceoffs.select("period", "game_seconds", fac_team="event_team", fac_state="strength_state"),
        on=["period", "game_seconds"],
    )
    mirrored = pl.col("fac_state").str.split("v").list.reverse().list.join("v")
    expected = pl.when(pl.col("event_team") == pl.col("fac_team")).then(pl.col("fac_state")).otherwise(mirrored)

    assert joined.height > 0
    assert joined.filter(pl.col("strength_state") != expected).is_empty()


def test_team_toi_by_strength_mirrors(fixture_game):
    """A team's ice time in a strength state equals the other team's in the mirrored state."""
    team_stats = prep_team_stats(fixture_game.play_by_play, fixture_game.play_by_play_ext)
    toi = {(row["team"], row["strength_state"]): row["toi"] for row in team_stats.to_dicts()}
    other_team = {"TBL": "NSH", "NSH": "TBL"}

    for (team, state), minutes in toi.items():
        assert minutes == pytest.approx(toi[(other_team[team], MIRRORED_STATE[state])])


def test_player_stats_by_strength(fixture_game):
    """A player's default rows split their ice time and events by strength state."""
    stats = prep_stats(fixture_game.play_by_play, fixture_game.play_by_play_ext)
    nick_paul = {
        row["strength_state"]: row
        for row in stats.filter(pl.col("api_id") == 8477426)
        .select("strength_state", "toi", "g", "isf", "gf")
        .to_dicts()
    }

    assert sorted(nick_paul) == ["4v5", "5v4", "5v5", "5vE"]
    assert nick_paul["5v4"]["toi"] == pytest.approx(6.5)
    assert (nick_paul["5v4"]["g"], nick_paul["5v4"]["isf"], nick_paul["5v4"]["gf"]) == (2, 3, 2)
    assert nick_paul["5v5"]["toi"] == pytest.approx(497 / 60)
    assert (nick_paul["5vE"]["g"], nick_paul["5vE"]["gf"]) == (0, 1)


# -----------------------------------------------------------------------------
# Row order
# -----------------------------------------------------------------------------

ORDER_CASES = [
    ("prep_ind", {}),
    ("prep_ind", {"level": "period", "score": True}),
    ("prep_ind", {"teammates": True, "opposition": True}),
    ("prep_oi", {}),
    ("prep_oi", {"level": "period", "score": True}),
    ("prep_oi", {"teammates": True, "opposition": True}),
    ("prep_stats", {}),
    ("prep_stats", {"level": "period", "score": True}),
    ("prep_stats", {"teammates": True, "opposition": True}),
    ("prep_lines", {}),
    ("prep_lines", {"level": "period", "score": True}),
    ("prep_lines", {"teammates": True, "opposition": True}),
    ("prep_team_stats", {}),
    ("prep_team_stats", {"level": "period", "score": True, "opposition": True}),
]


@pytest.mark.parametrize("function, arguments", ORDER_CASES)
def test_rows_come_back_in_the_same_order(fixture_game, function, arguments):
    """Calling an aggregation twice on the same play-by-play gives the same rows in the same order."""
    if function == "prep_ind":
        frames = [prep_ind(fixture_game.play_by_play, **arguments) for _ in range(3)]
    else:
        aggregate = {
            "prep_oi": prep_oi,
            "prep_stats": prep_stats,
            "prep_lines": prep_lines,
            "prep_team_stats": prep_team_stats,
        }[function]
        frames = [aggregate(fixture_game.play_by_play, fixture_game.play_by_play_ext, **arguments) for _ in range(3)]

    assert frames[1].equals(frames[0])
    assert frames[2].equals(frames[0])


# -----------------------------------------------------------------------------
# Overtime and shootout
# -----------------------------------------------------------------------------

EXTRA_TIME_CASES = [
    # fixture, (play-by-play rows, shifts, changes), away and home (team, score, shots), overtime seconds
    ("shootout_game", (827, 729, 477), ("VGK", 4, 30), ("LAK", 3, 40), 300),
    ("playoff_overtime_game", (884, 854, 516), ("NYR", 3, 25), ("CAR", 2, 47), 103),
]


@pytest.mark.parametrize("fixture, heights, away, home, overtime_seconds", EXTRA_TIME_CASES)
def test_extra_time_game_matches_api_box_score(
    request, saved_api_response, fixture, heights, away, home, overtime_seconds
):
    """A game that goes past regulation has the final score and the shots on goal the API reports."""
    game = request.getfixturevalue(fixture)
    api_response = saved_api_response(game.game_id)
    play_by_play = game.play_by_play

    assert game.failed_games == []
    assert (play_by_play.height, game.shifts.height, game.changes.height) == heights

    api_away, api_home = api_response["awayTeam"], api_response["homeTeam"]
    assert (api_away["abbrev"], api_away["score"], api_away["sog"]) == away
    assert (api_home["abbrev"], api_home["score"], api_home["sog"]) == home

    last_event = play_by_play.tail(1)
    assert last_event["event"].item() == "GEND"
    assert (last_event["away_score"].item(), last_event["home_score"].item()) == (away[1], home[1])

    # Shots on goal do not include shootout attempts, which are period 5
    shots = dict(
        play_by_play.filter(pl.col("period") <= 4).group_by("event_team").agg(pl.col("shot").sum()).drop_nulls().rows()
    )
    assert (shots[away[0]], shots[home[0]]) == (away[2], home[2])


@pytest.mark.parametrize("fixture, heights, away, home, overtime_seconds", EXTRA_TIME_CASES)
def test_overtime_is_timed_from_the_end_of_regulation(request, fixture, heights, away, home, overtime_seconds):
    """Overtime events and line changes run from 3600 game seconds to the end of overtime."""
    game = request.getfixturevalue(fixture)
    overtime = game.play_by_play.filter(pl.col("period") == 4)
    overtime_changes = game.changes.filter(pl.col("period") == 4)

    assert overtime["event_length"].sum() == overtime_seconds
    assert (overtime["game_seconds"].min(), overtime["game_seconds"].max()) == (3600, 3600 + overtime_seconds)

    assert overtime_changes.height > 0
    assert overtime_changes["game_seconds"].min() == 3600
    assert overtime_changes["game_seconds"].max() == 3600 + overtime_seconds

    team_stats = prep_team_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=False)
    assert team_stats["toi"].to_list() == pytest.approx([(3600 + overtime_seconds) / 60] * 2)
    assert prep_stints(game.play_by_play)["toi"].sum() == 3600 + overtime_seconds


def test_regular_season_overtime_is_three_on_three(shootout_game):
    """Regular-season overtime is played 3v3, with 4v3 after a penalty."""
    overtime = shootout_game.play_by_play.filter(pl.col("period") == 4)
    states = dict(overtime["strength_state"].value_counts().rows())

    assert states["3v3"] == 29
    assert states["4v3"] == 7


def test_playoff_overtime_is_five_on_five(playoff_overtime_game):
    """Playoff overtime is played 5v5 and ends on the goal."""
    overtime = playoff_overtime_game.play_by_play.filter(pl.col("period") == 4)

    assert dict(overtime["strength_state"].value_counts().rows())["5v5"] == 21
    assert overtime.filter(pl.col("event") == "GOAL").height == 1
    assert 5 not in playoff_overtime_game.play_by_play["period"].unique().to_list()


def test_shootout_rows(shootout_game):
    """The shootout is period 5: five attempts, one goal, no time on the clock."""
    shootout = shootout_game.play_by_play.filter(pl.col("period") == 5)
    events = dict(shootout["event"].value_counts().rows())

    assert (events["SHOT"], events["GOAL"]) == (4, 1)
    assert shootout["event_length"].sum() == 0
    assert shootout["game_seconds"].unique().to_list() == [3900]
    assert shootout["strength_state"].unique().to_list() == ["1v0"]
    assert shootout["opp_strength_state"].unique().to_list() == ["0v1"]


def test_long_shootout_game(long_shootout_game, saved_api_response):
    """A game with five shootout goals has the right shots through overtime and eight shootout attempts."""
    api_response = saved_api_response(long_shootout_game.game_id)
    play_by_play = long_shootout_game.play_by_play

    assert long_shootout_game.failed_games == []
    assert (play_by_play.height, long_shootout_game.shifts.height, long_shootout_game.changes.height) == (779, 742, 455)

    through_overtime = play_by_play.filter(pl.col("period") <= 4)
    totals = {
        row["event_team"]: row
        for row in through_overtime.group_by("event_team").agg(pl.col("goal", "shot").sum()).drop_nulls().to_dicts()
    }
    assert (totals["MTL"]["goal"], totals["BUF"]["goal"]) == (2, 2)
    assert (totals["MTL"]["shot"], totals["BUF"]["shot"]) == (
        api_response["awayTeam"]["sog"],
        api_response["homeTeam"]["sog"],
    )
    assert (totals["MTL"]["shot"], totals["BUF"]["shot"]) == (31, 48)

    shootout = dict(play_by_play.filter(pl.col("period") == 5)["event"].value_counts().rows())
    assert (shootout["GOAL"], shootout["SHOT"]) == (5, 3)

    # Buffalo had a two-man advantage in the first period
    assert through_overtime.filter(pl.col("strength_state") == "5v3").height == 3


@pytest.mark.parametrize("fixture", ["shootout_game", "long_shootout_game", "playoff_overtime_game"])
def test_shootout_attempts_are_flagged_and_not_counted(request, fixture, saved_api_response):
    """Shootout attempts have their own flags, are not shots or goals, and are not xG inputs."""
    game = request.getfixturevalue(fixture)
    api_plays = saved_api_response(game.game_id)["plays"]
    api_shootout = [play for play in api_plays if play["periodDescriptor"]["periodType"] == "SO"]
    api_goals = sum(play["typeDescKey"] == "goal" for play in api_shootout)
    api_attempts = api_goals + sum(play["typeDescKey"] in ("shot-on-goal", "missed-shot") for play in api_shootout)

    play_by_play = game.play_by_play
    attempts = play_by_play.filter(pl.col("shootout_attempt") == 1)

    assert (attempts.height, play_by_play["shootout_goal"].sum()) == (api_attempts, api_goals)
    assert attempts["event"].is_in(["GOAL", "SHOT", "MISS"]).all()
    assert attempts.select(pl.col("goal", "shot", "miss", "fenwick", "corsi").sum()).row(0) == (0, 0, 0, 0, 0)
    assert attempts.join(game.xg_fields, on=["game_id", "event_idx"]).height == 0


# The finest and coarsest levels, always split by score; each case takes about two seconds
@pytest.mark.parametrize("level", ["period", "season"])
@pytest.mark.parametrize("strength_state", [True, False])
@pytest.mark.parametrize("with_others", [True, False])
def test_shootout_game_totals_at_every_level(long_shootout_game, level, strength_state, with_others):
    """Goals and shots through overtime are the same for every aggregation and argument combination."""
    pbp, pbp_ext = long_shootout_game.play_by_play, long_shootout_game.play_by_play_ext
    goals, shots = {"MTL": 2, "BUF": 2}, {"MTL": 31, "BUF": 48}
    split = {"level": level, "strength_state": strength_state, "score": True}

    stats = prep_stats(pbp, pbp_ext, teammates=with_others, opposition=with_others, **split)
    team_stats = prep_team_stats(pbp, pbp_ext, opposition=with_others, **split)
    lines = prep_lines(
        pbp,
        pbp_ext,
        position="f",
        level=level,
        strength_state=strength_state,
        score=True,
        teammates=with_others,
        opposition=with_others,
    )

    assert stats.select(pl.col("g", "isf").sum()).row(0) == (sum(goals.values()), sum(shots.values()))
    assert dict(team_stats.group_by("team").agg(pl.col("gf").sum()).rows()) == goals
    assert dict(team_stats.group_by("team").agg(pl.col("sf").sum()).rows()) == shots
    assert dict(lines.group_by("team").agg(pl.col("gf").sum()).rows()) == goals
    assert dict(lines.group_by("team").agg(pl.col("sf").sum()).rows()) == shots


def with_known_xg(play_by_play: pl.DataFrame) -> pl.DataFrame:
    """Give every row a different known xG value, blocked shots and shootout attempts included, and one shot NaN."""
    first_shot = (pl.col("event") == "SHOT").arg_true().first()
    return play_by_play.with_columns(
        pred_goal=pl.when(pl.int_range(pl.len()) == first_shot)
        .then(float("nan"))
        .otherwise((pl.int_range(pl.len()) % 7 + 1) / 100)
    )


def counted_xg(play_by_play: pl.DataFrame) -> pl.DataFrame:
    """The rows whose xG counts: goals, shots and misses outside the shootout, with a number for xG."""
    return play_by_play.filter(
        pl.col("event").is_in(["GOAL", "SHOT", "MISS"]), pl.col("shootout_attempt") == 0, ~pl.col("pred_goal").is_nan()
    )


def sums_by(df: pl.DataFrame, key: str, column: str) -> dict:
    return {team: pytest.approx(total) for team, total in df.group_by(key).agg(pl.col(column).sum()).rows()}


def test_xg_totals_equal_a_direct_sum_in_every_output(fixture_game):
    """Supplied xG, raw and score-adjusted, adds up the same in individual, on-ice, team and stint output."""
    pbp = with_known_xg(fixture_game.play_by_play)
    pbp_ext = fixture_game.play_by_play_ext
    direct = prepare_xg(pbp)

    # xG on blocked shots, penalties and other rows, and the NaN, count nowhere
    assert direct.filter(pl.col("pred_goal").is_not_null())["pred_goal"].sum() == pytest.approx(
        counted_xg(pbp)["pred_goal"].sum()
    )

    ind = prep_ind(pbp, level="game", strength_state=False)
    assert sums_by(ind, "team", "ixg") == sums_by(counted_xg(pbp), "event_team", "pred_goal")
    assert sums_by(ind, "team", "ixg_adj") == sums_by(direct, "event_team", "pred_goal_adj")
    assists = counted_xg(pbp).filter(pl.col("event") == "GOAL", pl.col("player_2").is_not_null())
    assert ind["a1_xg"].sum() == pytest.approx(assists["pred_goal"].sum())

    team_stats = prep_team_stats(pbp, pbp_ext, level="game", strength_state=False)
    for raw, adjusted in (("xgf", "pred_goal"), ("xgf_adj", "pred_goal_adj")):
        assert sums_by(team_stats, "team", raw) == sums_by(direct, "event_team", adjusted)
    assert sums_by(team_stats, "team", "xga") == sums_by(direct, "opp_team", "pred_goal")

    with_base = prep_team_stats(pbp.with_columns(base_xg="pred_goal"), pbp_ext, level="game", strength_state=False)
    assert sums_by(with_base, "team", "base_xgf_adj") == sums_by(direct, "event_team", "pred_goal_adj")

    oi = prep_oi(pbp, pbp_ext, level="game", strength_state=False).filter(pl.col("position") == "G")
    with_goalie = direct.filter(pl.col("own_goalie").is_not_null())
    assert sums_by(oi, "team", "xgf") == sums_by(with_goalie, "event_team", "pred_goal")
    assert sums_by(oi, "team", "xgf_adj") == sums_by(with_goalie, "event_team", "pred_goal_adj")

    stints = prep_stints(pbp)
    in_stints = direct.filter(pl.col("strength_state") != "1v0")
    home = in_stints.filter(pl.col("event_team") == pl.col("home_team"))["pred_goal"].sum()
    away = in_stints.filter(pl.col("event_team") == pl.col("away_team"))["pred_goal"].sum()
    assert (stints["home_xgf"].sum(), stints["away_xgf"].sum()) == (pytest.approx(home), pytest.approx(away))


@pytest.mark.parametrize("fixture", ["shootout_game", "long_shootout_game"])
def test_shootout_attempts_carry_no_xg(request, fixture):
    """In a game decided by a shootout, shootout attempts add no xG, and goalies are charged with the rest."""
    game = request.getfixturevalue(fixture)
    pbp = with_known_xg(game.play_by_play)
    stats = prep_stats(pbp, game.play_by_play_ext, level="game", strength_state=False)
    team_stats = prep_team_stats(pbp, game.play_by_play_ext, level="game", strength_state=False)
    goalies = stats.filter(pl.col("position") == "G")
    outside_shootout = prepare_xg(pbp).filter(pl.col("shootout_attempt") == 0)
    # An attempt at an empty net counts for the team but not against a goalie
    on_a_goalie = outside_shootout.filter(pl.col("opp_goalie").is_not_null())

    assert pbp.filter(pl.col("shootout_attempt") == 1)["pred_goal"].sum() > 0
    assert sums_by(team_stats, "team", "xgf") == sums_by(outside_shootout, "event_team", "pred_goal")
    assert sums_by(team_stats, "team", "xga_adj") == sums_by(outside_shootout, "opp_team", "pred_goal_adj")
    assert sums_by(goalies, "team", "xga") == sums_by(on_a_goalie, "opp_team", "pred_goal")
    assert sums_by(goalies, "team", "xga_adj") == sums_by(on_a_goalie, "opp_team", "pred_goal_adj")


@pytest.mark.parametrize("fixture", ["shootout_game", "long_shootout_game"])
def test_goalie_goals_against_equal_team_goals_against(request, fixture):
    """In a game decided by a shootout, each team's goalies allowed the goals the team allowed."""
    game = request.getfixturevalue(fixture)
    stats = prep_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=False)
    team_stats = prep_team_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=False)

    goalies = stats.filter(pl.col("position") == "G").group_by("team").agg(pl.col("ga").sum())

    assert dict(goalies.rows()) == dict(team_stats.select("team", "ga").rows())


@pytest.mark.parametrize("fixture", ["shootout_game", "playoff_overtime_game"])
def test_penalties_drawn_are_credited_to_the_other_team(request, fixture):
    """The teammate serving a bench minor is not credited with drawing it, so every drawn penalty is the opponent's."""
    game = request.getfixturevalue(fixture)
    bench_minors = game.play_by_play.filter(pl.col("event") == "PENL", pl.col("player_1") == "BENCH")
    ind_stats = prep_ind(game.play_by_play, level="game", strength_state=False)
    drawn = ind_stats.filter(pl.sum_horizontal(pl.col("^ipend.*$")) > 0)
    rosters = game.rosters.select("team", "api_id")

    assert bench_minors.height == 1
    assert drawn.join(rosters, on=["team", "api_id"], how="anti").is_empty()


def test_bench_minor_with_a_drawer_credits_the_drawer():
    """A TEAM penalty with SERVED BY and DRAWN BY keeps the drawer in player_2 and the server in player_3."""
    game = Game(2023020125)
    raw = next(e for e in game._fetch_html_events() if e["event"] == "PENL" and "TEAM" in e["description"])
    lak = next(p for p in game.rosters if p["team"] == "LAK" and p["status"] == "ACTIVE" and p["position"] != "G")
    raw = {**raw, "description": f"{raw['description']} DRAWN BY: LAK #{lak['jersey']} {lak['player_name']}"}
    actives = {p["team_jersey"]: p for p in game.rosters if p.get("team_jersey") and p.get("status") == "ACTIVE"}

    event = game._munge_html_events([raw], actives, {})[0]

    assert (event["player_1"], event["player_2"], event["player_3"]) == ("BENCH", lak["player_name"], "PAUL COTTER")


@pytest.mark.parametrize(
    ("fixture", "server", "server_api_id"),
    [("shootout_game", "PAUL COTTER", 8481032), ("playoff_overtime_game", "WILL CUYLLE", 8482157)],
)
def test_the_player_serving_a_bench_minor_is_player_3(request, fixture, server, server_api_id):
    """player_2 is only the player who drew a penalty, and the teammate serving it is player_3 (hk-04, N44)."""
    play_by_play = request.getfixturevalue(fixture).play_by_play
    bench_minor = play_by_play.filter(pl.col("event") == "PENL", pl.col("player_1") == "BENCH")

    assert bench_minor.select("player_2", "player_3", "player_3_api_id").rows() == [(None, server, server_api_id)]


def test_a_served_goalie_penalty_credits_the_drawer_and_not_the_server(long_shootout_game):
    """Primeau's penalty, served by Ylönen and drawn by Thompson, keeps all three players apart."""
    penalty = long_shootout_game.play_by_play.filter(pl.col("event") == "PENL", pl.col("player_1") == "CAYDEN PRIMEAU")

    assert penalty.select("player_1", "player_2", "player_3").rows() == [
        ("CAYDEN PRIMEAU", "TAGE THOMPSON", "JESSE YLONEN")
    ]


def test_a_goalie_penalty_served_by_a_teammate_has_no_drawer():
    """The teammate serving it was read as the player who drew it, under the other team (hk-04)."""
    game = Game(2023020001)

    events = _munged_with(game, "PENL", "NSH #74 SAROS TRIPPING(2 MIN) SERVED BY: #9 FORSBERG, DEF. ZONE")

    assert [(e["player_1"], e["player_2"], e["player_3"]) for e in events] == [("JUUSE SAROS", None, "FILIP FORSBERG")]


def test_the_api_penalty_puts_the_server_in_player_3():
    from chickenstats.chicken_nhl._game_utils import handle_penalty_details

    served = handle_penalty_details({"typeCode": "MIN", "committedByPlayerId": 1, "servedByPlayerId": 2})
    bench = handle_penalty_details({"typeCode": "BEN", "servedByPlayerId": 2})

    assert (served.get("player_2_api_id"), served["player_3_api_id"], served["player_3_type"]) == (None, 2, "SERVED BY")
    assert (bench["player_1"], bench.get("player_2_api_id"), bench["player_3_api_id"]) == ("BENCH", None, 2)


def _munged_with(game, event, description):
    """Run one raw event of the game, given a new type and description, through _munge_html_events."""
    raw = next(e for e in game._fetch_html_events() if e["event"] == "PENL")
    actives = {p["team_jersey"]: p for p in game.rosters if p.get("team_jersey") and p.get("status") == "ACTIVE"}

    return game._munge_html_events([{**raw, "event": event, "description": description}], actives, {})


def test_a_head_coach_penalty_with_no_server_is_kept_on_the_bench():
    """A head-coach misconduct with no SERVED BY was dropped; it is kept with player_1 BENCH (R100, bA-09)."""
    game = Game(2023020001)

    events = _munged_with(game, "PENL", "TBL TEAM MISCONDUCT - HEAD COACH(10 MIN), NEU. ZONE")

    assert [(e["event_team"], e["player_1"], e["player_2"], e["penalty_length"]) for e in events] == [
        ("TBL", "BENCH", None, 10)
    ]


def test_an_event_with_no_team_prefix_is_kept_with_no_team():
    """An event whose description has no team prefix was dropped; it is kept with no team (R100, bA-09)."""
    game = Game(2023020001)

    events = _munged_with(game, "SHOT", "")

    assert [(e["event"], e["event_team"]) for e in events] == [("SHOT", "")]


def test_a_final_game_warns_about_events_kept_without_a_team_or_server(caplog):
    game = Game(2023020001)

    with caplog.at_level(logging.WARNING, logger="chickenstats"):
        _munged_with(game, "PENL", "TBL TEAM MISCONDUCT - HEAD COACH(10 MIN), NEU. ZONE")

    assert any("0 event(s) with no team and 1 bench penalty(ies)" in record.getMessage() for record in caplog.records)


@pytest.mark.parametrize("fixture", ["fixture_game", "shootout_game", "long_shootout_game", "playoff_overtime_game"])
def test_only_penalty_rows_count_as_penalties(request, fixture):
    """A delayed penalty is only a call, so penalty counts come from PENL rows alone."""
    play_by_play = request.getfixturevalue(fixture).play_by_play
    pen_columns = ["pen0", "pen2", "pen4", "pen5", "pen10"]
    by_event = play_by_play.group_by(pl.col("event") == "PENL").agg(pl.sum_horizontal(pen_columns).sum())

    assert dict(by_event.rows()).get(False, 0) == 0
    assert (
        play_by_play.select(pl.sum_horizontal(pen_columns).sum()).item()
        == play_by_play.filter(pl.col("event") == "PENL", pl.col("penalty_length").is_in([0, 2, 4, 5, 10])).height
    )


@pytest.mark.parametrize(
    "fixture, garbled, name",
    [("long_shootout_game", "LINDSTRAM", "LINDSTROM"), ("playoff_overtime_game", "LAFRENIARE", "LAFRENIERE")],
)
def test_accented_names_are_read_correctly(request, fixture, garbled, name):
    """The event and roster reports are UTF-8, so accented names come through instead of garbled."""
    game = request.getfixturevalue(fixture)
    descriptions = game.play_by_play["description"].drop_nulls()

    assert not descriptions.str.contains(garbled).any()
    assert descriptions.str.contains(name).any()
    assert game.html_rosters["player_name"].str.contains(name).any()


@pytest.mark.parametrize("fixture", ["fixture_game", "shootout_game", "long_shootout_game"])
def test_one_on_one_rows_have_only_the_shooter_and_the_goalie(request, fixture):
    """A penalty shot or shootout attempt has the shooter on one side and the goalie in net on the other."""
    game = request.getfixturevalue(fixture)
    one_on_one = game.play_by_play.filter(
        pl.col("strength_state") == "1v0", pl.col("event").is_in(["GOAL", "SHOT", "MISS"])
    )

    assert one_on_one.height > 0
    for row in one_on_one.to_dicts():
        assert (row["event_team_skaters"], row["opp_team_skaters"]) == (1, 0)
        assert (row["teammates"], row["own_goalie"]) == (row["player_1"], None)
        assert row["opp_goalie"] is not None
        assert row["opp_team_on"] == row["opp_goalie"]


@pytest.mark.parametrize(
    "game_id, period, period_type", [(2023020001, 3, "REG"), (2023020125, 5, "SO"), (2023030223, 4, "OT")]
)
def test_current_period_of_a_finished_game(game_id, period, period_type):
    """Once the API response is loaded, a finished game reports its last period."""
    game = Game(game_id)
    _ = game.api_events

    assert game.game_state == "OFF"
    assert (game.current_period, game.current_period_type) == (period, period_type)


# -----------------------------------------------------------------------------
# Game in progress
# -----------------------------------------------------------------------------


def test_live_snapshot_values():
    """A snapshot taken in the third period matches the score, shots and clock in its API response."""
    snapshot = "2026020052_LIVE_P3"
    with open(os.path.join(LIVE_DATA_DIR, snapshot, "play_by_play.json")) as f:
        api_response = json.load(f)

    with patch("requests.Session.get", snapshot_session_get(snapshot)):
        scraper = Scraper([2026020052], disable_progress_bar=True)
        play_by_play = scraper.play_by_play

    assert scraper.failed_games == []
    assert play_by_play.height == 638

    last_event = play_by_play.tail(1)
    assert api_response["clock"]["secondsRemaining"] == 803
    assert (last_event["period"].item(), last_event["period_seconds"].item()) == (3, 1200 - 803)
    assert (last_event["home_score"].item(), last_event["away_score"].item()) == (1, 1)
    assert (api_response["homeTeam"]["score"], api_response["awayTeam"]["score"]) == (1, 1)

    shots = dict(play_by_play.group_by("event_team").agg(pl.col("shot").sum()).drop_nulls().rows())
    assert (shots["LAK"], shots["FLA"]) == (api_response["homeTeam"]["sog"], api_response["awayTeam"]["sog"])
    assert (shots["LAK"], shots["FLA"]) == (18, 24)
    assert play_by_play["event_length"].sum() == 2797


# -----------------------------------------------------------------------------
# Every saved game against its boxscore, and a season across two games
# -----------------------------------------------------------------------------

SAVED_GAMES = [
    "fixture_game",
    "shootout_game",
    "long_shootout_game",
    "playoff_overtime_game",
    "second_nashville_game",
    "old_regular_season_game",
    "old_playoff_game",
]
# The package names the Coyotes ARI in every season
BOXSCORE_CODES = {"PHX": "ARI"}


@pytest.mark.parametrize("fixture", SAVED_GAMES)
def test_final_score_and_shots_match_the_boxscore(request, saved_boxscore, fixture):
    """The last play-by-play row has the final score, and each team's shots on goal match the boxscore."""
    game = request.getfixturevalue(fixture)
    box = saved_boxscore(game.game_id)
    team_stats = prep_team_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=False)
    teams = {
        BOXSCORE_CODES.get(box[side]["abbrev"], box[side]["abbrev"]): box[side] for side in ("homeTeam", "awayTeam")
    }

    assert game.failed_games == []
    assert game.play_by_play.select("home_score", "away_score").row(-1) == (
        box["homeTeam"]["score"],
        box["awayTeam"]["score"],
    )
    assert dict(team_stats.select("team", "sf").rows()) == {team: side["sog"] for team, side in teams.items()}


@pytest.mark.parametrize(
    "fixture, heights",
    [
        ("second_nashville_game", (792, 695, 463)),
        ("old_regular_season_game", (620, 785, 287)),
        ("old_playoff_game", (697, 862, 330)),
    ],
)
def test_new_saved_game_heights(request, fixture, heights):
    game = request.getfixturevalue(fixture)

    assert (game.play_by_play.height, game.shifts.height, game.changes.height) == heights


def test_a_season_across_two_games_is_the_sum_of_the_games():
    """Nashville's first two games, scraped together, give season totals equal to the two game rows."""
    scraper = Scraper([2023020001, 2023020015], disable_progress_bar=True)
    pbp, ext = scraper.play_by_play, scraper.play_by_play_ext
    counts = ["gf", "ga", "sf", "sa", "cf", "ca", "toi"]

    by_game = prep_team_stats(pbp, ext, level="game", strength_state=False).filter(pl.col("team") == "NSH")
    season = prep_team_stats(pbp, ext, level="season", strength_state=False).filter(pl.col("team") == "NSH")
    assert by_game.height == 2
    assert season.select(counts).row(0) == pytest.approx(by_game.select(pl.col(counts).sum()).row(0))

    player_counts = ["g", "a1", "isf", "icf", "gf", "cf", "toi"]
    games = prep_stats(pbp, ext, level="game", strength_state=False).filter(pl.col("team") == "NSH")
    seasons = prep_stats(pbp, ext, level="season", strength_state=False).filter(pl.col("team") == "NSH")
    summed = games.group_by("api_id").agg(pl.col(player_counts).sum(), pl.len().alias("games"))
    joined = seasons.join(summed, on="api_id", suffix="_games")
    assert joined.filter(pl.col("games") == 2).height >= 18
    for column in player_counts:
        assert ((joined[column] - joined[f"{column}_games"]).abs() < 1e-9).all(), column
