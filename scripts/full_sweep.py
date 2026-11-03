"""Scrape every completed game from 2007-08, one at a time, saving each game's frames and their hashes.

    full_sweep.py list               build games.json and one schedule per season
    full_sweep.py run [--limit N]    work through games.json, skipping games already in results.jsonl
    full_sweep.py manifest SEASON    write a season's manifest
    full_sweep.py upload SEASON      copy a finished season to the bucket, verify it, then remove the local copy
    full_sweep.py audit              list names with several api_ids, and api_ids with several names, by season
    full_sweep.py swaps              list events whose description names a player the event was not credited to

Each game is one line of results.jsonl and one parquet per frame under frames/<season>/<game_id>/, written
to a temporary directory and renamed, so a resumed run cannot leave a partial game.
"""

import hashlib
import importlib.metadata
import io
import json
import os
import pathlib
import re
import shutil
import sys
import time
import traceback

import chickenstats
import polars as pl
from chickenstats.chicken_nhl import Scraper, Season, prep_stats, prep_stints, prep_team_stats

HERE = pathlib.Path(__file__).parent
GAMES, RESULTS, ROOT = HERE / "games.json", HERE / "results.jsonl", HERE / "frames"
FRAMES = ("api_events", "html_events", "shifts", "changes", "rosters", "play_by_play", "play_by_play_ext", "xg_fields")
HASHED = FRAMES
FIRST_YEAR, LAST_YEAR = 2007, 2026
GAP, PAUSE, MAX_STREAK = 2, 600, 20
BUCKET, PREFIX = os.environ["SWEEP_BUCKET"], "xg_working/sweep_frames"
COMMIT = os.environ["SWEEP_COMMIT"]

# A player in a description, as "TOR #3 MURRAY", up to the words that follow a name
MENTION = re.compile(r"([A-Z.]{2,3}) #(\d+) ([A-Z][A-Z'. -]*?)(?=,| HIT | BLOCKED | VS | WON |\(| DRAWN| SERVED|$)")
SHOTS = {"SHOT", "MISS", "GOAL", "BLOCK"}


def season_of(game_id):
    """Return the eight-digit season of game_id."""
    year = game_id // 1_000_000
    return year * 10_000 + year + 1


def build_list():
    """Write each season's schedule and the list of completed games."""
    games = []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        schedule = Season(year, backend="polars").schedule(sessions=["R", "P"], disable_progress_bar=True)
        folder = ROOT / str(year * 10_000 + year + 1)
        folder.mkdir(parents=True, exist_ok=True)
        schedule.write_parquet(folder / "schedule.parquet", compression="zstd")
        done = schedule.filter(pl.col("game_state").is_in(["OFF", "FINAL"]))
        games += done.sort("game_date", "game_id")["game_id"].to_list()
        print(year, schedule.height, done.height, flush=True)
    GAMES.write_text(json.dumps(sorted(set(games))))
    print("games", len(set(games)))


def digest(frame):
    """Return a short hash of frame, leaving out the package version."""
    frame = frame.drop("cs_version", strict=False)
    return hashlib.sha256(frame.write_ndjson().encode()).hexdigest()[:16]


def save(game_id, frames):
    """Write one game's frames to a temporary directory, then rename it into place."""
    target = ROOT / str(season_of(game_id)) / str(game_id)
    partial = target.with_name(f".{game_id}.tmp")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    for name, frame in frames.items():
        frame.write_parquet(partial / f"{name}.parquet", compression="zstd")
    shutil.rmtree(target, ignore_errors=True)
    partial.rename(target)


def one(game_id):
    """Scrape and save one game, and return its row for results.jsonl."""
    row = {"game_id": game_id, "version": chickenstats.__version__, "commit": COMMIT}
    started = time.monotonic()
    try:
        scraper = Scraper(game_id, disable_progress_bar=True)
        frames = {name: getattr(scraper, name) for name in FRAMES}
        row["rows"] = {name: frame.height for name, frame in frames.items()}
        row["hash"] = {name: digest(frames[name]) for name in HASHED}
        row["failed"] = [str(x) for x in scraper.failed_games]
        row["reasons"] = {str(k): v for k, v in scraper.failure_reasons.items()}
        pbp = frames["play_by_play"]
        row["prep"] = {
            "stats": prep_stats(pbp).height,
            "team": prep_team_stats(pbp).height,
            "stints": prep_stints(pbp).height,
        }
        row["ok"] = not row["failed"] and pbp.height > 0
        if row["ok"]:
            save(game_id, frames)
    except Exception as error:
        row.update(ok=False, error=f"{type(error).__name__}: {error}"[:400], trace=traceback.format_exc()[-1200:])
    row["seconds"] = round(time.monotonic() - started, 1)
    return row


def results():
    """Return every row of results.jsonl."""
    if not RESULTS.exists():
        return []
    return [json.loads(line) for line in RESULTS.read_text().splitlines() if line]


def check_commit():
    """Refuse to run unless the installed chickenstats is SWEEP_COMMIT, so the manifest names the code that ran."""
    installed = importlib.metadata.distribution("chickenstats").read_text("direct_url.json") or "{}"
    commit = json.loads(installed).get("vcs_info", {}).get("commit_id", "")
    if not commit.startswith(COMMIT):
        raise SystemExit(f"chickenstats is installed from {commit or 'no commit'}, not {COMMIT}")


def run(limit):
    """Work through the games not yet in results.jsonl, uploading each season as it ends."""
    check_commit()
    done = {row["game_id"] for row in results()}
    todo = [g for g in json.loads(GAMES.read_text()) if g not in done]
    print("todo", len(todo), "done", len(done), "commit", COMMIT, flush=True)
    streak, season = 0, None
    for game_id in todo[:limit] if limit else todo:
        if season not in (None, season_of(game_id)):
            finish(season)
        season = season_of(game_id)
        row = one(game_id)
        streak = 0 if row["ok"] else streak + 1
        if streak >= MAX_STREAK:
            # Probably an outage, so this game is not recorded and comes back on the next pass
            print("pausing after", streak, "failures:", row.get("error") or row.get("reasons"), flush=True)
            streak = 0
            time.sleep(PAUSE)
            continue
        with RESULTS.open("a") as out:
            out.write(json.dumps(row) + "\n")
        time.sleep(GAP)
    if season is not None:
        finish(season)
    print("finished", flush=True)


def finish(season):
    """Upload a season that has run, so the disk never holds more than one season of frames."""
    try:
        upload(season)
    except SystemExit as reason:
        print("not uploaded:", reason, flush=True)


def manifest(season):
    """Write and return a season's manifest, refusing results from another commit."""
    rows = [row for row in results() if season_of(row["game_id"]) == season]
    commits = sorted({row.get("commit") for row in rows})
    if len(commits) != 1 or commits[0] != COMMIT:
        raise SystemExit(f"{season}: results come from {commits}, not only {COMMIT}")
    expected = {g for g in json.loads(GAMES.read_text()) if season_of(g) == season}
    seen = {row["game_id"] for row in rows}
    body = {
        "season": season,
        "commit": COMMIT,
        "version": chickenstats.__version__,
        "game_ids": sorted(row["game_id"] for row in rows if row.get("ok")),
        "failed": {str(row["game_id"]): row.get("error") or row.get("reasons") for row in rows if not row.get("ok")},
        "missing": sorted(expected - seen),
    }
    (ROOT / str(season) / "manifest.json").write_text(json.dumps(body, indent=1))
    print(season, len(body["game_ids"]), "ok", len(body["failed"]), "failed", len(body["missing"]), "missing")
    return body


def names(season):
    """Write each name, eh_id and api_id a season's rosters gave, with its game count."""
    folder = ROOT / str(season)
    (
        pl.scan_parquet(folder / "*" / "rosters.parquet")
        .with_columns(season=pl.lit(season))
        .group_by("season", "player_name", "eh_id", "api_id")
        .agg(games=pl.col("game_id").n_unique())
        .sort("player_name", "api_id")
        .collect()
        .write_parquet(folder / "names.parquet", compression="zstd")
    )


def audit():
    """Print the names and api_ids that disagree, within a season and across seasons."""
    from google.cloud import storage

    client = storage.Client()
    blobs = client.list_blobs(BUCKET, prefix=f"{PREFIX}/{COMMIT}/")
    frames = [pl.read_parquet(blob.download_as_bytes()) for blob in blobs if blob.name.endswith("/names.parquet")]
    seen = pl.concat(frames).filter(pl.col("api_id").is_not_null())
    for key, value in (("player_name", "api_id"), ("api_id", "player_name")):
        for scope, by in (("within a season", ["season", key]), ("across seasons", [key])):
            found = seen.group_by(by).agg(pl.col(value).unique().sort()).filter(pl.col(value).list.len() > 1)
            print(f"{key} with several {value} values {scope}: {found.height}")
            with pl.Config(tbl_rows=-1, fmt_table_cell_list_len=-1, fmt_str_lengths=60):
                print(found.sort(by))


def letters(text):
    """Keep only a name's letters, so MARC-ANDRE and O'REILLY compare the same way in both sources."""
    return re.sub(r"[^A-Z]", "", text.upper())


def unnamed(play_by_play):
    """Yield each player a description names whose surname is in none of the event's players."""
    rows = play_by_play.sort("event_idx").to_dicts()
    for row, after in zip(rows, [*rows[1:], {}], strict=True):
        players = [letters(row[f"player_{n}"]) for n in (1, 2, 3) if row.get(f"player_{n}")]
        for team, jersey, surname in MENTION.findall((row.get("description") or "").upper()):
            word = letters(surname.split()[0])
            if not any(word in player for player in players):
                yield {
                    "season": row["season"],
                    "game_id": row["game_id"],
                    "event_idx": row["event_idx"],
                    "event": row["event"],
                    "event_team": row.get("event_team"),
                    "named": f"{team} #{jersey} {surname.strip()}",
                    "players": ", ".join(row.get(f"player_{n}") or "" for n in (1, 2, 3)),
                    "next_event": after.get("event"),
                    "next_team": after.get("event_team"),
                    "shot_next": after.get("event") in SHOTS and after.get("period") == row.get("period"),
                    "description": row.get("description"),
                }


def swaps():
    """Write every unmatched player in a description to the bucket and print the count by season."""
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(BUCKET)
    blobs = client.list_blobs(BUCKET, prefix=f"{PREFIX}/{COMMIT}/")
    found = [
        row
        for blob in blobs
        if blob.name.endswith("/play_by_play.parquet")
        for row in unnamed(pl.read_parquet(blob.download_as_bytes()))
    ]
    if not found:
        print("no unmatched players")
        return
    frame = pl.DataFrame(found, infer_schema_length=None)
    out = io.BytesIO()
    frame.write_parquet(out, compression="zstd")
    bucket.blob(f"{PREFIX}/{COMMIT}/swaps.parquet").upload_from_string(out.getvalue())
    with pl.Config(tbl_rows=-1):
        print(
            frame.group_by("season")
            .agg(
                events=pl.struct("game_id", "event_idx").n_unique(),
                games=pl.col("game_id").n_unique(),
                shot_next=pl.col("shot_next").sum(),
            )
            .sort("season")
        )


def upload(season):
    """Copy a season to the bucket, check every file arrived, then remove the local copy."""
    from google.cloud import storage

    body = manifest(season)
    if body["missing"]:
        raise SystemExit(f"{season}: {len(body['missing'])} games have not run")
    names(season)
    folder = ROOT / str(season)
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    prefix = f"{PREFIX}/{COMMIT}/{season}"
    files = [path for path in sorted(folder.rglob("*")) if path.is_file() and not path.name.startswith(".")]
    for path in files:
        bucket.blob(f"{prefix}/{path.relative_to(folder)}").upload_from_filename(path)
    remote = {blob.name: blob.size for blob in client.list_blobs(bucket, prefix=f"{prefix}/")}
    wrong = [p for p in files if remote.get(f"{prefix}/{p.relative_to(folder)}") != p.stat().st_size]
    if wrong:
        raise SystemExit(f"{season}: {len(wrong)} files did not arrive intact, local copy kept: {wrong[:3]}")
    shutil.rmtree(folder)
    print(season, "uploaded", len(files), "files, local copy removed")


if __name__ == "__main__":
    if sys.argv[1] == "list":
        build_list()
    elif sys.argv[1] == "manifest":
        manifest(int(sys.argv[2]))
    elif sys.argv[1] == "upload":
        upload(int(sys.argv[2]))
    elif sys.argv[1] == "audit":
        audit()
    elif sys.argv[1] == "swaps":
        swaps()
    else:
        run(int(sys.argv[3]) if len(sys.argv) > 3 else None)
