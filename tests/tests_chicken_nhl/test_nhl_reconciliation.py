"""Per-player output checked against the NHL's own published numbers for every saved game.

Ice time, in total and at even strength, on the power play and short-handed, comes from the summary at
the end of each player's section of the TH and TV shift reports. Goals, assists, shots on goal, hits,
blocked shots, giveaways, takeaways, ice time, penalty minutes, faceoff percentage and goalie shots and
goals against come from the NHL API boxscore. All of it is read from the saved responses.
"""

import re

import polars as pl
import pytest
import requests

from chickenstats.chicken_nhl import prep_stats
from chickenstats.chicken_nhl._game_utils import parse_report

SAVED_GAMES = [
    "fixture_game",
    "shootout_game",
    "long_shootout_game",
    "playoff_overtime_game",
    "second_nashville_game",
    "old_regular_season_game",
    "old_playoff_game",
]

# A player's section ends with a summary whose TOT row reads shifts, average, then TOI, EV, PP and SH
SUMMARY_RE = re.compile(r"\|(\d{1,2}) [^|]+\|Shift #.*?\|TOT\|\d+\|[\d:]+\|([\d:]+)\|([\d:]+)\|([\d:]+)\|([\d:]+)")


def seconds(clock: str) -> int:
    minutes, secs = clock.split(":")
    return int(minutes) * 60 + int(secs)


def shift_summaries(game_id: int, season: int, venue: str) -> dict[int, tuple[int, ...]]:
    """Each jersey's total, even-strength, power-play and short-handed seconds from a saved shift report."""
    report = f"{'TH' if venue == 'home' else 'TV'}{str(game_id)[4:]}"
    response = requests.Session().get(f"https://www.nhl.com/scores/htmlreports/{season}/{report}.HTM")
    # Script and style text is skipped so only the report's visible text is matched
    root = parse_report(response.content)
    assert root is not None
    pieces = root.xpath("//text()[not(ancestor::script or ancestor::style)]")
    text = "|".join(stripped for piece in pieces if (stripped := piece.strip()))

    return {int(m.group(1)): tuple(seconds(x) for x in m.group(2, 3, 4, 5)) for m in SUMMARY_RE.finditer(text)}


def situation_seconds(play_by_play: pl.DataFrame) -> dict[tuple[int, str], int]:
    """Each player's seconds by the NHL's situation: an extra attacker for a pulled goalie does not count."""
    frames = []
    for side, other in (("home", "away"), ("away", "home")):

        def skaters(venue: str) -> pl.Expr:
            no_goalie = pl.col(f"{venue}_goalie").is_null() | (pl.col(f"{venue}_goalie") == "")
            return pl.col(f"{venue}_skaters") - pl.when(no_goalie).then(1).otherwise(0)

        own, opp = skaters(side), skaters(other)
        frames.append(
            play_by_play.select(
                api_id=pl.col(f"{side}_on_api_id").str.split(", "),
                event_length=pl.col("event_length"),
                situation=pl.when(own == opp)
                .then(pl.lit("EV"))
                .when(own > opp)
                .then(pl.lit("PP"))
                .otherwise(pl.lit("SH")),
            ).explode("api_id", empty_as_null=True)
        )

    totals = (
        pl.concat(frames)
        .filter(pl.col("api_id").is_not_null(), pl.col("api_id") != "")
        .group_by(pl.col("api_id").cast(pl.Int64), "situation")
        .agg(pl.col("event_length").sum())
    )
    return {(api_id, situation): seconds for api_id, situation, seconds in totals.rows()}


@pytest.mark.parametrize("fixture", SAVED_GAMES)
def test_ice_time_matches_the_shift_report_summaries(request, fixture):
    game = request.getfixturevalue(fixture)
    play_by_play = game.play_by_play
    ours = situation_seconds(play_by_play)
    checked = 0

    for venue in ("home", "away"):
        team = play_by_play[f"{venue}_team"][0]
        jerseys = dict(game.rosters.filter(pl.col("team") == team).select("jersey", "api_id").rows())
        for jersey, nhl in shift_summaries(game.game_id, play_by_play["season"][0], venue).items():
            api_id = jerseys[jersey]
            by_situation = tuple(ours.get((api_id, situation), 0) for situation in ("EV", "PP", "SH"))
            assert (sum(by_situation), *by_situation) == nhl, (team, jersey)
            checked += 1

    assert checked >= 36


@pytest.mark.parametrize("fixture", SAVED_GAMES)
def test_player_totals_match_the_boxscore(request, saved_boxscore, fixture):
    game = request.getfixturevalue(fixture)
    stats = prep_stats(game.play_by_play, game.play_by_play_ext, level="game", strength_state=False)
    ours = {row["api_id"]: row for row in stats.to_dicts()}
    box = saved_boxscore(game.game_id)["playerByGameStats"]

    for side in ("awayTeam", "homeTeam"):
        for skater in box[side]["forwards"] + box[side]["defense"]:
            row = ours[skater["playerId"]]
            pim = 2 * row["ipent2"] + 4 * row["ipent4"] + 5 * row["ipent5"] + 10 * row["ipent10"]
            expected = (
                skater["goals"],
                skater["assists"],
                skater["sog"],
                skater["hits"],
                skater["blockedShots"],
                skater["giveaways"],
                skater["takeaways"],
                seconds(skater["toi"]),
                skater["pim"],
            )
            actual = (
                row["g"],
                row["a1"] + row["a2"],
                row["isf"],
                row["ihf"],
                row["ibs"],
                row["igive"],
                row["itake"],
                round(row["toi"] * 60),
                pim,
            )
            assert actual == expected, skater["name"]["default"]
            if row["ifow"] + row["ifol"]:
                assert row["ifow"] / (row["ifow"] + row["ifol"]) == pytest.approx(
                    skater["faceoffWinningPctg"], abs=1e-4
                )

        for goalie in box[side]["goalies"]:
            if seconds(goalie["toi"]) == 0:
                continue
            row = ours[goalie["playerId"]]
            assert (row["sa"], row["ga"]) == (goalie["shotsAgainst"], goalie["goalsAgainst"]), goalie["name"]["default"]
