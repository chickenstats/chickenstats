#!/usr/bin/env python3
"""Reconcile one team's regular season with the NHL's official numbers.

Scrapes every finished regular-season game of a team through Scraper, then compares team
goals, shots and games, each goalie's games, TOI, shots against, goals against and saves,
and each skater's games, TOI, goals, assists and points with what the NHL publishes. Each
game is checked against its boxscore, and the season against the standings, the stats
summary and the club stats.

    uv run --frozen python scripts/reconcile_season.py NSH 20242025
    uv run --frozen python scripts/reconcile_season.py LAK 2015 --save-dir /tmp/lak --json lak.json
    uv run --frozen python scripts/reconcile_season.py NSH 2024 --save-dir /tmp/nsh --toi-tolerance 1

The standings and the boxscore count a shootout win as one goal for the winner, and Scraper
and the stats summary do not, so that goal is added to the scraped total compared with the
standings and taken out of each boxscore. TOI is compared in whole seconds; the club stats
give a skater's average per game, so the season total is that average times games played.
The script exits 1 if any number differs or any game failed, and 0 if everything agrees.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import polars as pl

from chickenstats.chicken_nhl import Scraper, Season, prep_stats, prep_team_stats
from chickenstats.utilities import ChickenSession

BOXSCORE_URL = "https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
CLUB_STATS_URL = "https://api-web.nhle.com/v1/club-stats/{team}/{season}/2"
TEAM_SUMMARY_URL = "https://api.nhle.com/stats/rest/en/team/summary?cayenneExp=seasonId={season}%20and%20gameTypeId=2"

FINISHED_STATES = ("OFF", "FINAL")
GIGABYTE = 1024**3
# ru_maxrss is in bytes on macOS and in kilobytes on Linux
RSS_UNIT = 1 if sys.platform == "darwin" else 1024

TEAM_STATS = ["gf", "ga", "sf", "sa"]
# TOI is in seconds; games is 1 on each game row, so a player missing from one side shows up
GOALIE_STATS = ["games", "toi", "shots_against", "goals_against", "saves"]
SKATER_STATS = ["games", "toi", "goals", "assists", "points"]


def peak_rss() -> float:
    """Return this process's peak resident memory, in gigabytes."""
    if sys.platform == "win32":
        import psutil

        return psutil.Process().memory_info().peak_wset / GIGABYTE

    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * RSS_UNIT / GIGABYTE


def season_id(season: str) -> int:
    """Return the 8-digit season for a 4-digit or 8-digit argument."""
    return int(season) if len(season) == 8 else int(f"{season}{int(season) + 1}")


def toi_seconds(toi: str) -> int:
    """Return the seconds in a boxscore TOI such as 20:37."""
    minutes, seconds = toi.split(":")
    return int(minutes) * 60 + int(seconds)


def get_json(session: ChickenSession, url: str) -> dict:
    """Return the JSON at a URL, raising on an HTTP error."""
    response = session.get(url)
    response.raise_for_status()
    return response.json()


def boxscore_rows(box: dict, team: str) -> tuple[dict, list[dict], list[dict]]:
    """Return one team's official row, goalie rows and skater rows from a game's boxscore.

    A goalie who dressed and did not play is left out. Every skater listed is counted as
    having played, as the NHL counts a dressed skater.
    """
    side = "homeTeam" if box["homeTeam"]["abbrev"] == team else "awayTeam"
    other = "awayTeam" if side == "homeTeam" else "homeTeam"
    own, opp = box[side], box[other]

    shootout = (box.get("gameOutcome") or {}).get("lastPeriodType") == "SO"
    won = shootout and own["score"] > opp["score"]
    lost = shootout and own["score"] < opp["score"]

    team_row = {
        "game_id": box["id"],
        "game_date": box["gameDate"],
        "opponent": opp["abbrev"],
        "shootout_win": int(won),
        "shootout_loss": int(lost),
        "gf": own["score"] - int(won),
        "ga": opp["score"] - int(lost),
        "sf": own["sog"],
        "sa": opp["sog"],
    }
    goalies = [
        {
            "game_id": box["id"],
            "api_id": goalie["playerId"],
            "name": goalie["name"]["default"],
            "games": 1,
            "toi": toi_seconds(goalie.get("toi", "00:00")),
            "shots_against": goalie["shotsAgainst"],
            "goals_against": goalie["goalsAgainst"],
            "saves": goalie["saves"],
        }
        for goalie in box["playerByGameStats"][side]["goalies"]
        # Boxscores before 2009-10 give a backup who did not play no stats at all
        if goalie.get("toi", "00:00") != "00:00" or goalie.get("shotsAgainst")
    ]
    players = box["playerByGameStats"][side]
    skaters = [
        {
            "game_id": box["id"],
            "api_id": skater["playerId"],
            "name": skater["name"]["default"],
            "games": 1,
            "toi": toi_seconds(skater.get("toi", "00:00")),
            "goals": skater["goals"],
            "assists": skater["assists"],
            "points": skater["points"],
        }
        for skater in players["forwards"] + players["defense"]
    ]
    return team_row, goalies, skaters


def official_games(
    session: ChickenSession, game_ids: list[int], team: str
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Return the official team, goalie and skater rows for each game."""
    team_rows, goalie_rows, skater_rows = [], [], []
    for game_id in game_ids:
        team_row, goalies, skaters = boxscore_rows(get_json(session, BOXSCORE_URL.format(game_id=game_id)), team)
        team_rows.append(team_row)
        goalie_rows.extend(goalies)
        skater_rows.extend(skaters)
    return pl.DataFrame(team_rows), pl.DataFrame(goalie_rows), pl.DataFrame(skater_rows)


def club_rows(club: dict) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Return the club stats season totals for each goalie and each skater, TOI in seconds."""

    def name(player: dict) -> str:
        return f"{player['firstName']['default']} {player['lastName']['default']}"

    goalies = [
        {
            "api_id": goalie["playerId"],
            "name": name(goalie),
            "games": goalie["gamesPlayed"],
            "toi": goalie["timeOnIce"],
            "shots_against": goalie["shotsAgainst"],
            "goals_against": goalie["goalsAgainst"],
            "saves": goalie["saves"],
        }
        for goalie in club["goalies"]
    ]
    skaters = [
        {
            "api_id": skater["playerId"],
            "name": name(skater),
            "games": skater["gamesPlayed"],
            "toi": round(skater["avgTimeOnIcePerGame"] * skater["gamesPlayed"]),
            "goals": skater["goals"],
            "assists": skater["assists"],
            "points": skater["points"],
        }
        for skater in club["skaters"]
    ]
    return pl.DataFrame(goalies), pl.DataFrame(skaters)


def scrape(game_ids: list[int], session: ChickenSession, save_dir: Path | None, quiet: bool) -> Scraper:
    """Scrape the games, or load them from an earlier run's save directory."""
    if save_dir is not None and (save_dir / "_meta.json").exists():
        return Scraper.load(save_dir, game_ids=game_ids, disable_progress_bar=quiet, requests_session=session)

    scraper = Scraper(game_ids, disable_progress_bar=quiet, requests_session=session)
    _ = scraper.play_by_play
    if save_dir is not None:
        scraper.save(save_dir)
    return scraper


def scraped_rows(pbp: pl.DataFrame, ext: pl.DataFrame, team: str) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Return the team's game rows, its goalies' and its skaters' game rows from the scraped play-by-play."""
    teams = prep_team_stats(pbp, ext, level="game", strength_state=False)
    teams = teams.filter(pl.col("team") == team).select("game_id", *TEAM_STATS)

    players = prep_stats(pbp, ext, level="game", strength_state=False).filter(pl.col("team") == team, pl.col("toi") > 0)
    common = {"games": pl.lit(1, pl.Int64), "toi": (pl.col("toi") * 60).round().cast(pl.Int64)}
    # An own goal counts against the goalie but is not a shot, so saves are not shots less goals
    saves = (
        pbp.filter(pl.col("shot") == 1, pl.col("goal") == 0, pl.col("opp_goalie_api_id").is_not_null())
        .group_by("game_id", "opp_goalie_api_id")
        .agg(saves=pl.len().cast(pl.Int64))
        .rename({"opp_goalie_api_id": "api_id"})
    )
    goalies = (
        players.filter(pl.col("position") == "G")
        .select("game_id", "api_id", **common, shots_against="sa", goals_against="ga")
        .join(saves, on=["game_id", "api_id"], how="left")
        .with_columns(pl.col("saves").fill_null(0))
    )
    assists = pl.col("a1") + pl.col("a2")
    skaters = players.filter(pl.col("position") != "G").select(
        "game_id", "api_id", **common, goals="g", assists=assists, points=pl.col("g") + assists
    )
    return teams, goalies, skaters


def differs(stat: str, official: int, scraped: int, toi_tolerance: int) -> bool:
    """Return whether two numbers disagree, allowing TOI to be off by the tolerance in seconds."""
    allowed = toi_tolerance if stat == "toi" else 0
    return abs(scraped - official) > allowed


def game_differences(
    official: pl.DataFrame, scraped: pl.DataFrame, key: list[str], stats: list[str], toi_tolerance: int = 0
) -> list[dict]:
    """Return one row for each stat of each game row where the scraped number differs from the official one.

    A row that is on one side only counts as zero on the other, so a player missing from either shows up.
    """
    joined = official.join(scraped, on=key, how="full", coalesce=True, suffix="_scraped")
    return [
        {
            **{column: row[column] for column in key},
            "stat": stat,
            "official": row[stat] or 0,
            "scraped": row[f"{stat}_scraped"] or 0,
            "difference": (row[f"{stat}_scraped"] or 0) - (row[stat] or 0),
        }
        for row in joined.sort(key).to_dicts()
        for stat in stats
        if differs(stat, row[stat] or 0, row[f"{stat}_scraped"] or 0, toi_tolerance)
    ]


def season_lines(
    official_teams: pl.DataFrame, scraped_teams: pl.DataFrame, failed: list[int], standing: dict, summary: dict
) -> list[dict]:
    """Return one line per team total: published, less any failed games, against scraped.

    A failed game is taken out of the published total at its boxscore value, so the line
    still shows whether the games that did scrape agree.
    """
    games = official_teams.height
    gone = official_teams.filter(pl.col("game_id").is_in(failed))
    so_wins, so_losses = int(official_teams["shootout_win"].sum()), int(official_teams["shootout_loss"].sum())
    gone_wins, gone_losses = int(gone["shootout_win"].sum()), int(gone["shootout_loss"].sum())

    def line(source: str, stat: str, published: int, in_failed: int, scraped: int) -> dict:
        """One total, with the number left once the failed games are taken out."""
        expected = published - in_failed
        return {
            "source": source,
            "stat": stat,
            "published": published,
            "in_failed_games": in_failed,
            "expected": expected,
            "scraped": scraped,
            "difference": scraped - expected,
        }

    gf, ga = int(scraped_teams["gf"].sum()), int(scraped_teams["ga"].sum())
    sf, sa = int(scraped_teams["sf"].sum()), int(scraped_teams["sa"].sum())
    return [
        line("standings", "games", standing["games_played"], len(failed), scraped_teams.height),
        line(
            "standings",
            "goals for + SO wins",
            standing["goals_for"],
            int(gone["gf"].sum()) + gone_wins,
            gf + so_wins - gone_wins,
        ),
        line(
            "standings",
            "goals against + SO losses",
            standing["goals_against"],
            int(gone["ga"].sum()) + gone_losses,
            ga + so_losses - gone_losses,
        ),
        line("stats summary", "goals for", summary["goalsFor"], int(gone["gf"].sum()), gf),
        line("stats summary", "goals against", summary["goalsAgainst"], int(gone["ga"].sum()), ga),
        line("stats summary", "shots for", round(summary["shotsForPerGame"] * games), int(gone["sf"].sum()), sf),
        line(
            "stats summary", "shots against", round(summary["shotsAgainstPerGame"] * games), int(gone["sa"].sum()), sa
        ),
        line("boxscores", "goals for", int(official_teams["gf"].sum()), int(gone["gf"].sum()), gf),
        line("boxscores", "goals against", int(official_teams["ga"].sum()), int(gone["ga"].sum()), ga),
        line("boxscores", "shots for", int(official_teams["sf"].sum()), int(gone["sf"].sum()), sf),
        line("boxscores", "shots against", int(official_teams["sa"].sum()), int(gone["sa"].sum()), sa),
    ]


def player_lines(
    published: pl.DataFrame,
    official: pl.DataFrame,
    scraped: pl.DataFrame,
    failed: list[int],
    stats: list[str],
    toi_tolerance: int = 0,
) -> list[dict]:
    """Return one line per player and stat where the club stats total and the scraped one differ.

    A failed game is taken out of the club total at its boxscore value. A player scraped for
    the team but missing from the club stats gets a line for each stat he has.
    """
    gone = official.filter(pl.col("game_id").is_in(failed))

    def totals(frame: pl.DataFrame) -> dict[int, dict]:
        if frame.is_empty():
            return {}
        return {row["api_id"]: row for row in frame.group_by("api_id").agg(pl.col(stats).sum()).to_dicts()}

    gone_totals, scraped_totals = totals(gone), totals(scraped)
    published_totals = {row["api_id"]: row for row in published.to_dicts()}

    lines = []
    for api_id in sorted(set(published_totals) | set(scraped_totals)):
        player = published_totals.get(api_id, {})
        for stat in stats:
            value = player.get(stat, 0)
            in_failed = gone_totals.get(api_id, {}).get(stat, 0)
            total = scraped_totals.get(api_id, {}).get(stat, 0)
            if differs(stat, value - in_failed, total, toi_tolerance):
                lines.append(
                    {
                        "player": player.get("name", "not in the club stats"),
                        "api_id": api_id,
                        "stat": stat,
                        "published": value,
                        "in_failed_games": in_failed,
                        "expected": value - in_failed,
                        "scraped": total,
                        "difference": total - (value - in_failed),
                    }
                )
    return lines


def add_names(rows: list[dict], official: pl.DataFrame) -> None:
    """Add each row's player name from the boxscore rows, in place."""
    names = dict(official.unique("api_id").select("api_id", "name").iter_rows()) if official.height else {}
    for row in rows:
        row["name"] = names.get(row["api_id"], "unknown")


def print_rows(title: str, rows: list[dict]) -> None:
    """Print rows of dictionaries as an aligned table, or say there are none."""
    print(f"\n{title}")
    if not rows:
        print("  none")
        return
    columns = list(rows[0])
    widths = {c: max(len(c), *(len(str(row[c])) for row in rows)) for c in columns}
    print("  " + "  ".join(c.ljust(widths[c]) for c in columns))
    for row in rows:
        print("  " + "  ".join(str(row[c]).ljust(widths[c]) for c in columns))


def main() -> int:
    """Run the reconciliation and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("team", help="three-letter team code, e.g., NSH")
    parser.add_argument("season", help="season, as 2024 or 20242025")
    parser.add_argument("--rate", type=float, default=2.0, help="most NHL requests per second (default 2)")
    parser.add_argument("--save-dir", type=Path, help="save the scrape here, and load it from here on a rerun")
    parser.add_argument("--json", type=Path, help="also write the report to this file")
    parser.add_argument(
        "--toi-tolerance", type=int, default=0, help="seconds of TOI difference to accept per row (default 0)"
    )
    parser.add_argument("--quiet", action="store_true", help="hide the progress bars")
    args = parser.parse_args()

    start = time.perf_counter()
    team, season = args.team.upper(), season_id(args.season)
    session = ChickenSession(max_requests_per_second=args.rate)

    nhl_season = Season(season, requests_session=session)
    schedule = nhl_season.schedule(team, sessions="R", disable_progress_bar=args.quiet)
    finished = schedule.filter(pl.col("game_state").is_in(FINISHED_STATES)).sort("game_id")
    game_ids = finished["game_id"].to_list()
    first = finished.row(0, named=True)
    team_id = first["home_team_id"] if first["home_team"] == team else first["away_team_id"]

    standing = nhl_season.standings.filter(pl.col("team") == team).row(0, named=True)
    summaries = get_json(session, TEAM_SUMMARY_URL.format(season=season))["data"]
    summary = next(row for row in summaries if row["teamId"] == team_id)
    club_goalies, club_skaters = club_rows(get_json(session, CLUB_STATS_URL.format(team=team, season=season)))
    official_teams, official_goalies, official_skaters = official_games(session, game_ids, team)

    scraper = scrape(game_ids, session, args.save_dir, args.quiet)
    failed = sorted(scraper.failed_games)
    scraped_teams, scraped_goalies, scraped_skaters = scraped_rows(scraper.play_by_play, scraper.play_by_play_ext, team)
    seconds = time.perf_counter() - start
    tolerance = args.toi_tolerance

    def kept(frame: pl.DataFrame) -> pl.DataFrame:
        return frame.filter(~pl.col("game_id").is_in(failed))

    team_differences = game_differences(kept(official_teams), scraped_teams, ["game_id"], TEAM_STATS)
    goalie_differences = game_differences(
        kept(official_goalies), scraped_goalies, ["game_id", "api_id"], GOALIE_STATS, tolerance
    )
    skater_differences = game_differences(
        kept(official_skaters), scraped_skaters, ["game_id", "api_id"], SKATER_STATS, tolerance
    )
    add_names(goalie_differences, official_goalies)
    add_names(skater_differences, official_skaters)

    lines = season_lines(official_teams, scraped_teams, failed, standing, summary)
    goalies = player_lines(club_goalies, official_goalies, scraped_goalies, failed, GOALIE_STATS, tolerance)
    skaters = player_lines(club_skaters, official_skaters, scraped_skaters, failed, SKATER_STATS, tolerance)
    season_off = [line for line in lines if line["difference"]] + goalies + skaters

    failures = [{"game_id": game_id, "reason": str(scraper.failure_reasons.get(game_id))} for game_id in failed]
    report = {
        "team": team,
        "season": season,
        "games_finished": len(game_ids),
        "games_scraped": scraped_teams.height,
        "failed_games": failures,
        "shootout_wins": int(official_teams["shootout_win"].sum()),
        "shootout_losses": int(official_teams["shootout_loss"].sum()),
        "season_totals": lines,
        "goalie_season_differences": goalies,
        "skater_season_differences": skaters,
        "team_game_differences": team_differences,
        "goalie_game_differences": goalie_differences,
        "skater_game_differences": skater_differences,
        "wall_seconds": round(seconds, 1),
        "peak_rss_gb": round(peak_rss(), 2),
    }

    print(f"\n{team} {season}: {report['games_scraped']} of {report['games_finished']} finished games scraped")
    print(f"Shootouts: {report['shootout_wins']} won, {report['shootout_losses']} lost")
    print_rows("Failed games", failures)
    print_rows("Season totals", lines)
    print_rows("Goalie season differences", goalies)
    print_rows("Skater season differences", skaters)
    print_rows("Team differences by game", team_differences)
    print_rows("Goalie differences by game", goalie_differences)
    print_rows("Skater differences by game", skater_differences)
    print(f"\n{seconds:.1f} s, peak {report['peak_rss_gb']:.2f} GB")

    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=2))

    return 1 if failed or season_off or team_differences or goalie_differences or skater_differences else 0


if __name__ == "__main__":
    sys.exit(main())
