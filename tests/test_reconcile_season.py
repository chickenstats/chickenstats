"""What reconcile_season.py reports, on saved boxscores and made-up season totals."""

import gzip
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest

from chickenstats.chicken_nhl import Scraper

ROOT = Path(__file__).resolve().parents[1]
SAVED_DIR = ROOT / "tests" / "tests_chicken_nhl" / "mock_data" / "saved"
# The script is not in a package, so it is run from its path, not imported
recon = SimpleNamespace(**runpy.run_path(str(ROOT / "scripts" / "reconcile_season.py")))


def saved_boxscore(game_id: int) -> dict:
    with gzip.open(SAVED_DIR / f"gamecenter_{game_id}_boxscore.gz", "rb") as f:
        return json.load(f)


def test_toi_seconds():
    assert recon.toi_seconds("20:37") == 1237
    assert recon.toi_seconds("65:00") == 3900


def test_boxscore_rows_take_the_shootout_goal_out_of_the_winner():
    """VGK won 4-3 at LAK in a shootout; the boxscore's 4 includes the shootout goal."""
    team, goalies, skaters = recon.boxscore_rows(saved_boxscore(2023020125), "VGK")

    assert team == {
        "game_id": 2023020125,
        "game_date": "2023-10-28",
        "opponent": "LAK",
        "shootout_win": 1,
        "shootout_loss": 0,
        "gf": 3,
        "ga": 3,
        "sf": 30,
        "sa": 40,
    }
    # The backup who did not play is left out
    assert [(g["name"], g["games"], g["toi"], g["shots_against"], g["goals_against"]) for g in goalies] == [
        ("L. Thompson", 1, 3900, 40, 3)
    ]
    assert len(skaters) == 18
    assert {"name": "J. Eichel", "games": 1, "toi": 1379, "goals": 0, "assists": 0, "points": 0}.items() <= skaters[
        0
    ].items()


def test_boxscore_rows_for_the_shootout_loser():
    team, _, _ = recon.boxscore_rows(saved_boxscore(2023020125), "LAK")

    assert (team["shootout_win"], team["shootout_loss"], team["gf"], team["ga"]) == (0, 1, 3, 3)


def test_club_rows_turn_average_toi_into_a_season_total():
    club = {
        "goalies": [
            {
                "playerId": 1,
                "firstName": {"default": "Juuse"},
                "lastName": {"default": "Saros"},
                "gamesPlayed": 2,
                "timeOnIce": 7150,
                "shotsAgainst": 60,
                "goalsAgainst": 5,
                "saves": 55,
            }
        ],
        "skaters": [
            {
                "playerId": 2,
                "firstName": {"default": "Filip"},
                "lastName": {"default": "Forsberg"},
                "gamesPlayed": 3,
                "avgTimeOnIcePerGame": 1079.6667,
                "goals": 1,
                "assists": 2,
                "points": 3,
            }
        ],
    }
    goalies, skaters = recon.club_rows(club)

    assert goalies.to_dicts() == [
        {
            "api_id": 1,
            "name": "Juuse Saros",
            "games": 2,
            "toi": 7150,
            "shots_against": 60,
            "goals_against": 5,
            "saves": 55,
        }
    ]
    assert skaters.to_dicts() == [
        {"api_id": 2, "name": "Filip Forsberg", "games": 3, "toi": 3239, "goals": 1, "assists": 2, "points": 3}
    ]


def skater_frame(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=["game_id", "api_id", "games", "toi", "goals", "assists", "points"], orient="row")


def test_game_differences_name_each_stat_that_differs():
    official = skater_frame([(1, 10, 1, 600, 1, 0, 1), (1, 11, 1, 700, 0, 1, 1)])
    scraped = skater_frame([(1, 10, 1, 601, 1, 0, 1), (1, 11, 1, 700, 0, 2, 2)])

    differences = recon.game_differences(official, scraped, ["game_id", "api_id"], recon.SKATER_STATS)

    assert [(row["api_id"], row["stat"], row["difference"]) for row in differences] == [
        (10, "toi", 1),
        (11, "assists", 1),
        (11, "points", 1),
    ]


def test_game_differences_accept_toi_within_the_tolerance_only():
    official = skater_frame([(1, 10, 1, 600, 1, 0, 1)])
    scraped = skater_frame([(1, 10, 1, 602, 2, 0, 2)])

    differences = recon.game_differences(official, scraped, ["game_id", "api_id"], recon.SKATER_STATS, 2)

    assert [row["stat"] for row in differences] == ["goals", "points"]


def test_game_differences_count_a_missing_player_as_zero():
    official = skater_frame([(1, 10, 1, 600, 1, 0, 1), (1, 11, 1, 30, 0, 0, 0)])
    scraped = skater_frame([(1, 10, 1, 600, 1, 0, 1)])

    differences = recon.game_differences(official, scraped, ["game_id", "api_id"], recon.SKATER_STATS)

    assert [(row["api_id"], row["stat"], row["scraped"]) for row in differences] == [(11, "games", 0), (11, "toi", 0)]


def test_player_lines_take_failed_games_out_of_the_published_total():
    published = pl.DataFrame(
        [{"api_id": 10, "name": "A", "games": 2, "toi": 1300, "goals": 2, "assists": 0, "points": 2}]
    )
    official = skater_frame([(1, 10, 1, 600, 1, 0, 1), (2, 10, 1, 700, 1, 0, 1)])
    scraped = skater_frame([(1, 10, 1, 600, 1, 0, 1)])

    assert recon.player_lines(published, official, scraped, [2], recon.SKATER_STATS) == []
    # Without the failed game the scraped total is a game short
    assert [
        (row["stat"], row["difference"])
        for row in recon.player_lines(published, official, scraped, [], recon.SKATER_STATS)
    ] == [("games", -1), ("toi", -700), ("goals", -1), ("points", -1)]


def test_player_lines_report_a_player_missing_from_the_club_stats():
    published = pl.DataFrame(
        [{"api_id": 10, "name": "A", "games": 1, "toi": 600, "goals": 1, "assists": 0, "points": 1}]
    )
    official = skater_frame([(1, 10, 1, 600, 1, 0, 1)])
    scraped = skater_frame([(1, 10, 1, 600, 1, 0, 1), (1, 12, 1, 45, 0, 0, 0)])

    lines = recon.player_lines(published, official, scraped, [], recon.SKATER_STATS)

    assert [(row["player"], row["api_id"], row["stat"], row["scraped"]) for row in lines] == [
        ("not in the club stats", 12, "games", 1),
        ("not in the club stats", 12, "toi", 45),
    ]


def test_season_lines_add_shootout_wins_for_the_standings():
    official = pl.DataFrame(
        [
            {"game_id": 1, "shootout_win": 1, "shootout_loss": 0, "gf": 2, "ga": 2, "sf": 30, "sa": 25},
            {"game_id": 2, "shootout_win": 0, "shootout_loss": 0, "gf": 1, "ga": 4, "sf": 20, "sa": 35},
        ]
    )
    scraped = official.select("game_id", *recon.TEAM_STATS)
    standing = {"games_played": 2, "goals_for": 4, "goals_against": 6}
    summary = {"goalsFor": 3, "goalsAgainst": 6, "shotsForPerGame": 25.0, "shotsAgainstPerGame": 30.0}

    lines = recon.season_lines(official, scraped, [], standing, summary)

    assert len(lines) == 11
    assert [line for line in lines if line["difference"]] == []


def test_season_lines_take_a_failed_game_out():
    official = pl.DataFrame(
        [
            {"game_id": 1, "shootout_win": 1, "shootout_loss": 0, "gf": 2, "ga": 2, "sf": 30, "sa": 25},
            {"game_id": 2, "shootout_win": 0, "shootout_loss": 0, "gf": 1, "ga": 4, "sf": 20, "sa": 35},
        ]
    )
    scraped = official.filter(pl.col("game_id") == 2).select("game_id", *recon.TEAM_STATS)
    standing = {"games_played": 2, "goals_for": 4, "goals_against": 6}
    summary = {"goalsFor": 3, "goalsAgainst": 6, "shotsForPerGame": 25.0, "shotsAgainstPerGame": 30.0}

    lines = recon.season_lines(official, scraped, [1], standing, summary)

    assert [line for line in lines if line["difference"]] == []
    assert lines[1] == {
        "source": "standings",
        "stat": "goals for + SO wins",
        "published": 4,
        "in_failed_games": 3,
        "expected": 1,
        "scraped": 1,
        "difference": 0,
    }


@pytest.mark.parametrize("team", ["NSH", "TBL"])
def test_the_saved_game_agrees_with_its_boxscore(team):
    """Game 2023020001 scraped from the saved responses matches its boxscore for every team, goalie and skater."""
    scraper = Scraper([2023020001], disable_progress_bar=True)
    team_row, goalies, skaters = recon.boxscore_rows(saved_boxscore(2023020001), team)
    scraped_teams, scraped_goalies, scraped_skaters = recon.scraped_rows(
        scraper.play_by_play, scraper.play_by_play_ext, team
    )
    key = ["game_id", "api_id"]

    team_frame = pl.DataFrame([team_row])
    assert recon.game_differences(team_frame, scraped_teams, ["game_id"], recon.TEAM_STATS) == []
    goalie_frame = pl.DataFrame(goalies)
    assert recon.game_differences(goalie_frame, scraped_goalies, key, recon.GOALIE_STATS) == []
    skater_frame = pl.DataFrame(skaters)
    assert recon.game_differences(skater_frame, scraped_skaters, key, recon.SKATER_STATS) == []
