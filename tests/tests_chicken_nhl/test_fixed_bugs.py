"""Tests for bugs fixed in the 1.9.0 release.

Each one started in test_known_bugs.py as an expected failure, and moved here when its fix
removed the mark. They keep the fixes from coming undone. All of them run on the saved games,
with no network access.
"""

import warnings
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl import (
    Game,
    Scraper,
    Season,
    prep_ind,
    prep_lines,
    prep_stats,
    prep_stints,
    prep_team_stats,
)
from chickenstats.chicken_nhl.identity import identity_columns
from chickenstats.exceptions import InvalidInputError

GAME_ID = 2023020001


# -----------------------------------------------------------------------------
# Shootouts
# -----------------------------------------------------------------------------


def test_team_shots_leave_out_shootout_attempts(shootout_game, saved_api_response):
    api_response = saved_api_response(shootout_game.game_id)
    team_stats = prep_team_stats(
        shootout_game.play_by_play, shootout_game.play_by_play_ext, level="game", strength_state=False
    )
    shots = dict(team_stats.select("team", "sf").rows())

    assert shots == {"LAK": api_response["homeTeam"]["sog"], "VGK": api_response["awayTeam"]["sog"]}


def test_individual_shots_leave_out_shootout_attempts(shootout_game):
    play_by_play = shootout_game.play_by_play
    ind_stats = prep_ind(play_by_play, level="game", strength_state=False)

    assert ind_stats["isf"].sum() == play_by_play.filter(pl.col("period") <= 4)["shot"].sum()


def test_team_shots_are_the_same_with_and_without_a_strength_split(shootout_game):
    play_by_play, play_by_play_ext = shootout_game.play_by_play, shootout_game.play_by_play_ext
    unsplit = prep_team_stats(play_by_play, play_by_play_ext, level="game", strength_state=False)
    split = prep_team_stats(play_by_play, play_by_play_ext, level="game")

    assert dict(split.group_by("team").agg(pl.col("sf").sum()).rows()) == dict(unsplit.select("team", "sf").rows())


def test_final_score_of_a_shootout_with_several_goals(long_shootout_game, saved_api_response):
    api_response = saved_api_response(long_shootout_game.game_id)
    last_event = long_shootout_game.play_by_play.tail(1)

    assert (api_response["awayTeam"]["score"], api_response["homeTeam"]["score"]) == (3, 2)
    assert (last_event["away_score"].item(), last_event["home_score"].item()) == (3, 2)


def test_team_goals_leave_out_shootout_goals(long_shootout_game):
    team_stats = prep_team_stats(
        long_shootout_game.play_by_play, long_shootout_game.play_by_play_ext, level="game", strength_state=False
    )

    # Two goals each through overtime; the shootout is left out of team goals
    assert dict(team_stats.select("team", "gf").rows()) == {"MTL": 2, "BUF": 2}


def test_individual_goals_leave_out_shootout_goals(long_shootout_game):
    ind_stats = prep_ind(long_shootout_game.play_by_play, level="game", strength_state=False)

    assert ind_stats["g"].sum() == 4


# -----------------------------------------------------------------------------
# Events lost or misplaced by a strength split
# -----------------------------------------------------------------------------


@pytest.mark.parametrize("teammates", [False, True])
def test_prep_stats_keeps_every_individual_event(fixture_game, teammates):
    stats = prep_stats(fixture_game.play_by_play, fixture_game.play_by_play_ext, level="game", teammates=teammates)

    assert stats.select(pl.col("g", "a1", "isf", "iff", "icf").sum()).row(0) == (8, 7, 65, 96, 126)


def test_team_goals_by_strength_add_up_to_the_final_score(fixture_game):
    team_stats = prep_team_stats(fixture_game.play_by_play, fixture_game.play_by_play_ext)

    assert dict(team_stats.group_by("team").agg(pl.col("gf").sum()).rows()) == {"TBL": 5, "NSH": 3}


def test_penalty_shot_has_the_mirrored_state_for_the_other_team(fixture_game):
    penalty_shot = fixture_game.play_by_play.filter(pl.col("strength_state") == "1v0")

    assert penalty_shot["opp_strength_state"].to_list() == ["0v1"]


def test_team_for_and_against_mirror_by_strength_state(fixture_game):
    team_stats = prep_team_stats(fixture_game.play_by_play, fixture_game.play_by_play_ext)
    rows = {(row["team"], row["strength_state"]): row for row in team_stats.to_dicts()}
    mirrored_state = {"5v5": "5v5", "5v4": "4v5", "4v5": "5v4", "5vE": "Ev5", "Ev5": "5vE", "1v0": "0v1", "0v1": "1v0"}
    other_team = {"TBL": "NSH", "NSH": "TBL"}

    for (team, state), row in rows.items():
        mirrored = rows[(other_team[team], mirrored_state[state])]
        for stat in ("g", "s", "f", "c"):
            assert row[f"{stat}f"] == mirrored[f"{stat}a"], (team, state, stat)


def test_zone_starts_are_all_counted(fixture_game):
    play_by_play, play_by_play_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext
    changes = play_by_play.filter(pl.col("event") == "CHANGE")
    expected = dict(changes.group_by("zone_start").agg(pl.col("change_on_count").sum()).rows())

    toi = {}
    for strength_state in (False, True):
        stats = prep_stats(play_by_play, play_by_play_ext, level="game", strength_state=strength_state)
        totals = stats.select(pl.col("ozs", "nzs", "dzs", "otf").sum()).row(0)
        assert totals == (expected["OFF"], expected["NEU"], expected["DEF"], expected["OTF"]), strength_state
        toi[strength_state] = stats["toi"].sum()

    assert toi[True] == pytest.approx(toi[False])


# -----------------------------------------------------------------------------
# Faceoff zones
# -----------------------------------------------------------------------------


def test_zone_faceoffs_mirror_between_the_teams(fixture_game):
    team_stats = prep_team_stats(
        fixture_game.play_by_play, fixture_game.play_by_play_ext, level="game", strength_state=False
    )
    tbl = team_stats.filter(pl.col("team") == "TBL").to_dicts()[0]
    nsh = team_stats.filter(pl.col("team") == "NSH").to_dicts()[0]

    assert (tbl["ozf"], tbl["dzf"]) == (nsh["dzf"], nsh["ozf"])
    assert (tbl["ozf"], tbl["dzf"]) == (24, 19)


def test_individual_zone_faceoff_losses(fixture_game):
    ind_stats = prep_ind(fixture_game.play_by_play, level="game", strength_state=False)

    # NSH lost 12 draws in its offensive zone, which are TBL's 12 defensive-zone wins; TBL lost 9
    assert dict(ind_stats.group_by("team").agg(pl.col("iozfl").sum()).rows()) == {"NSH": 12, "TBL": 9}


# -----------------------------------------------------------------------------
# Names and identity
# -----------------------------------------------------------------------------


def test_a_player_has_one_name_across_sources(fixture_game):
    alex_carrier = 8478851
    names = set(fixture_game.rosters.filter(pl.col("api_id") == alex_carrier)["player_name"]) | set(
        fixture_game.shifts.filter(pl.col("api_id") == alex_carrier)["player_name"]
    )

    assert names == {"ALEXANDRE CARRIER"}

    names_by_id = pl.concat(
        [fixture_game.rosters.select("api_id", "player_name"), fixture_game.shifts.select("api_id", "player_name")]
    ).drop_nulls("api_id")
    assert (
        names_by_id.group_by("api_id")
        .agg(pl.col("player_name").n_unique())
        .filter(pl.col("player_name") > 1)
        .is_empty()
    )


def test_identity_columns_is_a_key_of_lines(fixture_game):
    lines = prep_lines(
        fixture_game.play_by_play,
        fixture_game.play_by_play_ext,
        level="game",
        strength_state=True,
        score=False,
        teammates=False,
        opposition=False,
    )
    key = identity_columns("lines", level="game", strength_state=True, score=False, teammates=False, opposition=False)

    assert set(key) <= set(lines.columns)
    assert lines.select(key).n_unique() == lines.height


def test_identity_columns_is_a_key_of_season_team_stats(fixture_game):
    team_stats = prep_team_stats(
        fixture_game.play_by_play,
        fixture_game.play_by_play_ext,
        level="season",
        strength_state=True,
        score=False,
        opposition=False,
    )
    key = identity_columns("team_stats", level="season", strength_state=True, score=False, opposition=False)

    assert set(key) <= set(team_stats.columns)
    assert team_stats.select(key).n_unique() == team_stats.height


# -----------------------------------------------------------------------------
# Other aggregation
# -----------------------------------------------------------------------------


def test_no_xg_columns_without_predicted_goals(fixture_game):
    assert "pred_goal" not in fixture_game.play_by_play.columns

    pbp, pbp_ext = fixture_game.play_by_play, fixture_game.play_by_play_ext

    for df in (prep_stats(pbp, pbp_ext), prep_lines(pbp, pbp_ext), prep_team_stats(pbp, pbp_ext)):
        assert [column for column in df.columns if "xg" in column] == []


def test_blocked_power_play_shot_uses_the_shooting_teams_weight(fixture_game):
    play_by_play = fixture_game.play_by_play.filter(pl.col("home_score_diff") == 1)
    shot = play_by_play.filter(
        (pl.col("event_team") == "TBL") & (pl.col("strength_state") == "5v4") & (pl.col("event") == "SHOT")
    )["corsi_adj"][0]
    block = play_by_play.filter(
        (pl.col("event_team") == "NSH") & (pl.col("strength_state") == "4v5") & (pl.col("event") == "BLOCK")
    )["corsi_adj"][0]

    assert block == pytest.approx(shot)


def test_float_count_columns_give_the_same_totals(fixture_game):
    play_by_play = fixture_game.play_by_play.with_columns(pl.col("goal", "shot", "fenwick", "hit").cast(pl.Float64))
    ind_stats = prep_ind(play_by_play, level="game", strength_state=False)

    assert ind_stats.select(pl.col("g", "isf", "iff", "ihf").sum()).row(0) == (8, 65, 96, 45)


def test_shots_without_a_description_are_counted(fixture_game):
    play_by_play = fixture_game.play_by_play.with_columns(
        pl.when(pl.col("event") == "SHOT").then(None).otherwise(pl.col("description")).alias("description")
    )

    assert prep_ind(play_by_play, level="game", strength_state=False)["isf"].sum() == 65


def test_events_without_a_description_are_counted(fixture_game):
    """Blanking every description that is not a teammate block leaves every individual count unchanged."""
    play_by_play = fixture_game.play_by_play
    blanked = play_by_play.with_columns(
        pl.when(pl.col("teammate_block") == 0).then(None).otherwise(pl.col("description")).alias("description")
    )
    before = prep_ind(play_by_play, level="game", strength_state=False)
    after = prep_ind(blanked, level="game", strength_state=False)
    counts = [
        c for c, dtype in before.schema.items() if dtype.is_integer() and c not in ("season", "game_id", "api_id")
    ]

    assert after.select(pl.col(counts).sum()).row(0) == before.select(pl.col(counts).sum()).row(0)


# -----------------------------------------------------------------------------
# Scraper state
# -----------------------------------------------------------------------------


def test_access_order_does_not_duplicate_rows():
    scraper = Scraper([GAME_ID], disable_progress_bar=True)
    _ = scraper.rosters
    _ = scraper.html_events
    _ = scraper.shifts
    _ = scraper.play_by_play

    heights = (scraper.rosters.height, scraper.html_events.height, scraper.shifts.height, scraper.changes.height)
    assert heights == (46, 331, 743, 450)


def test_repeated_and_string_game_ids_are_scraped_once():
    scraper = Scraper([GAME_ID, GAME_ID, str(GAME_ID)], disable_progress_bar=True)

    assert scraper.game_ids == [GAME_ID]
    assert scraper.play_by_play.height == 781


def test_add_games_clears_the_aggregated_stats():
    scraper = Scraper([GAME_ID], disable_progress_bar=True)
    scraper.prep_stats(level="game", disable_progress_bar=True)
    assert scraper.stats["game_id"].unique().to_list() == [GAME_ID]

    scraper.add_games([2023020125])

    assert sorted(scraper.stats["game_id"].unique().to_list()) == [GAME_ID, 2023020125]


def test_changes_are_the_same_before_and_after_play_by_play():
    game = Game(GAME_ID)
    keys_before = len(game.changes[0])
    _ = game.play_by_play

    assert len(game.changes[0]) == keys_before


UNKNOWN_LEVEL_CALLS = {
    "Scraper.prep_stats": lambda scraper, level: scraper.prep_stats(level=level, disable_progress_bar=True),
    "Scraper.prep_lines": lambda scraper, level: scraper.prep_lines(level=level, disable_progress_bar=True),
    "Scraper.prep_team_stats": lambda scraper, level: scraper.prep_team_stats(level=level, disable_progress_bar=True),
    "prep_ind": lambda scraper, level: prep_ind(scraper.play_by_play, level=level),
    "prep_stats": lambda scraper, level: prep_stats(scraper.play_by_play, scraper.play_by_play_ext, level=level),
    "prep_lines": lambda scraper, level: prep_lines(scraper.play_by_play, scraper.play_by_play_ext, level=level),
    "prep_team_stats": lambda scraper, level: prep_team_stats(
        scraper.play_by_play, scraper.play_by_play_ext, level=level
    ),
}


@pytest.mark.parametrize("level", ["Game", "seasons", None])
@pytest.mark.parametrize("call", UNKNOWN_LEVEL_CALLS)
def test_unknown_level_raises(call, level):
    scraper = Scraper([GAME_ID], disable_progress_bar=True)

    with pytest.raises(InvalidInputError):
        UNKNOWN_LEVEL_CALLS[call](scraper, level)


# -----------------------------------------------------------------------------
# Season
# -----------------------------------------------------------------------------


def test_schedule_second_call_with_other_sessions():
    season = Season(2023)
    regular_season = season.schedule("NSH", sessions="R", disable_progress_bar=True)
    playoffs = season.schedule("NSH", sessions="P", disable_progress_bar=True)

    assert regular_season.height == 82
    assert playoffs.height == 6


# -----------------------------------------------------------------------------
# Charts
# -----------------------------------------------------------------------------


def rolling_stats_for_two_teams() -> pl.DataFrame:
    """Three games of a rolling stat for each of two teams."""
    return pl.DataFrame(
        {
            "team": ["NSH", "NSH", "NSH", "TBL", "TBL", "TBL"],
            "game_id": [1, 2, 3, 1, 2, 3],
            "rolling_cf_p60": [50.0, 55.0, 60.0, 40.0, 42.0, 44.0],
        }
    )


def test_rolling_chart_draws_one_line_per_team():
    pytest.importorskip("matplotlib")
    pytest.importorskip("seaborn")
    from chickenstats.chicken_nhl.viz import plot_rolling_stats

    ax = plot_rolling_stats(rolling_stats_for_two_teams(), stat="cf_p60")

    assert sorted(np.asarray(line.get_ydata()).tolist() for line in ax.lines) == [
        [40.0, 42.0, 44.0],
        [50.0, 55.0, 60.0],
    ]


def test_rolling_chart_rejects_a_filter_it_cannot_apply():
    pytest.importorskip("matplotlib")
    pytest.importorskip("seaborn")
    from chickenstats.chicken_nhl.viz import plot_rolling_stats

    with pytest.raises(InvalidInputError):
        plot_rolling_stats(rolling_stats_for_two_teams(), stat="cf_p60", player="FILIP FORSBERG")


def test_stint_strength_state_is_relative_to_the_home_team(fixture_game):
    stints = prep_stints(fixture_game.play_by_play)
    labels = stints.group_by("home_skater_count", "away_skater_count").agg(pl.col("strength_state").n_unique())

    assert labels["strength_state"].max() == 1
    power_play = stints.filter(pl.col("home_skater_count") == 5, pl.col("away_skater_count") == 4)
    assert set(power_play["strength_state"]) == {"5v4"}


def test_long_tip_is_measured_to_the_far_net():
    """A tip reported 173 feet out is not a high-danger chance at the near net."""
    game = Game(2023020001)
    shot = next(
        e
        for e in game.html_events
        if e["event"] == "SHOT" and e.get("zone") == "OFF" and (e.get("pbp_distance") or 0) < 20
    )
    shot.update(shot_type="TIP-IN", pbp_distance=173, zone="DEF")

    row = next(e for e in game.play_by_play if e["event"] == "SHOT" and e.get("pbp_distance") == 173)

    assert row["event_distance"] > 150
    assert row["zone"] == "DEF"
    assert row["high_danger"] == 0
