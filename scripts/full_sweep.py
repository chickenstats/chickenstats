"""Scrape every completed game from 2007-08, one at a time, saving each game's frames and their hashes.

    full_sweep.py list               build games.json and one schedule per season
    full_sweep.py run [--limit N]    work through games.json, skipping games already in results.jsonl
    full_sweep.py manifest SEASON    write a season's manifest
    full_sweep.py upload SEASON      copy a finished season to the bucket, verify it, then remove the local copy
    full_sweep.py audit              list names with several api_ids, and api_ids with several names, by season
    full_sweep.py swaps              list events whose description names a player the event was not credited to
    full_sweep.py overlay API_ID...  scrape again the base sweep's failed games and the games of these players,
                                     then upload them with each season's overlay.json
    full_sweep.py diff [SEASON...]   compare uploaded seasons with SWEEP_BASE's, after its overlay, column by column,
                                     and upload each season's summary to diffs/; with no season, every new one

Each game is one line of results.jsonl and one parquet per frame under frames/<season>/<game_id>/, written
to a temporary directory and renamed, so a resumed run cannot leave a partial game.

Every NHL and ESPN response a game fetches is kept as gzipped JSON under frames/<season>/responses/<game_id>/
and uploaded with the season. Set SWEEP_REPLAY to a folder holding downloaded <season>/responses/ folders to
run or overlay from them instead of the network; a response that was never saved fails the game with a 504.
"""

import gzip
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
from chickenstats.utilities import ChickenSession
from requests_cache import CacheMixin
from requests_cache.serializers import SerializerPipeline, Stage, json_serializer

HERE = pathlib.Path(__file__).parent
GAMES, RESULTS, ROOT = HERE / "games.json", HERE / "results.jsonl", HERE / "frames"
FRAMES = ("api_events", "html_events", "shifts", "changes", "rosters", "play_by_play", "play_by_play_ext", "xg_fields")
HASHED = FRAMES
FIRST_YEAR, LAST_YEAR = 2007, 2026
BUCKET, PREFIX = os.environ["SWEEP_BUCKET"], "xg_working/sweep_frames"
COMMIT = os.environ["SWEEP_COMMIT"]
BASE = os.environ.get("SWEEP_BASE")
REPLAY = os.environ.get("SWEEP_REPLAY")
# A replay makes no requests, so it has nothing to space out or wait for
GAP, PAUSE, MAX_STREAK = (0, 0, 20) if REPLAY else (2, 600, 20)
OVERLAY, OVERLAY_ROOT = HERE / "overlay.jsonl", HERE / "overlay_frames"

# Gzip shrinks a game's responses about thirtyfold, mostly the HTML reports
GZIP_JSON = SerializerPipeline(
    [
        *json_serializer.stages,
        Stage(dumps=str.encode, loads=bytes.decode),
        Stage(dumps=gzip.compress, loads=gzip.decompress),
    ],
    name="json.gz",
    is_binary=True,
)


class SavingSession(CacheMixin, ChickenSession):
    """A ChickenSession that keeps every response it receives, or with only_if_cached answers only from them."""


def responses_session(game_id, root):
    """Return a session that saves game_id's responses under root, or replays them when SWEEP_REPLAY is set."""
    folder = pathlib.Path(REPLAY or root) / str(season_of(game_id)) / "responses" / str(game_id)
    if not REPLAY:
        # A rerun downloads afresh, so a failed attempt's responses are not reused
        shutil.rmtree(folder, ignore_errors=True)
    session = SavingSession(
        cache_name=str(folder),
        backend="filesystem",
        serializer=GZIP_JSON,
        expire_after=-1,
        allowable_codes=(200, 404),
        only_if_cached=bool(REPLAY),
    )
    return session, folder


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


def save(game_id, frames, root):
    """Write one game's frames to a temporary directory under root, then rename it into place."""
    target = root / str(season_of(game_id)) / str(game_id)
    partial = target.with_name(f".{game_id}.tmp")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    for name, frame in frames.items():
        frame.write_parquet(partial / f"{name}.parquet", compression="zstd")
    shutil.rmtree(target, ignore_errors=True)
    partial.rename(target)


def one(game_id, root=ROOT):
    """Scrape and save one game under root, and return its row for results.jsonl."""
    row = {"game_id": game_id, "version": chickenstats.__version__, "commit": COMMIT, "replay": REPLAY}
    started = time.monotonic()
    session, folder = responses_session(game_id, root)
    try:
        scraper = Scraper(game_id, requests_session=session, disable_progress_bar=True)
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
            save(game_id, frames, root)
    except Exception as error:
        row.update(ok=False, error=f"{type(error).__name__}: {error}"[:400], trace=traceback.format_exc()[-1200:])
    finally:
        session.close()
        # The responses are stored under the URLs that were asked for, so the redirect index is not needed
        (folder / "redirects.sqlite").unlink(missing_ok=True)
    row["seconds"] = round(time.monotonic() - started, 1)
    return row


def results(path=RESULTS):
    """Return every row of results.jsonl, or of the file at path."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


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


def copy(folder, prefix):
    """Copy folder to the bucket under prefix, check every file arrived, remove the local copy and return the count."""
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(BUCKET)
    files = [path for path in sorted(folder.rglob("*")) if path.is_file() and not path.name.startswith(".")]
    for path in files:
        bucket.blob(f"{prefix}/{path.relative_to(folder)}").upload_from_filename(path)
    remote = {blob.name: blob.size for blob in client.list_blobs(bucket, prefix=f"{prefix}/")}
    wrong = [p for p in files if remote.get(f"{prefix}/{p.relative_to(folder)}") != p.stat().st_size]
    if wrong:
        raise SystemExit(f"{prefix}: {len(wrong)} files did not arrive intact, local copy kept: {wrong[:3]}")
    shutil.rmtree(folder)
    return len(files)


def upload(season):
    """Copy a season to the bucket, check every file arrived, then remove the local copy."""
    body = manifest(season)
    if body["missing"]:
        raise SystemExit(f"{season}: {len(body['missing'])} games have not run")
    names(season)
    count = copy(ROOT / str(season), f"{PREFIX}/{COMMIT}/{season}")
    print(season, "uploaded", count, "files, local copy removed")


def overlay_games(players):
    """Return, by season, the base sweep's failed games and the games whose rosters list one of players."""
    from google.cloud import storage

    client = storage.Client()
    games, seasons = {}, set()
    for blob in client.list_blobs(BUCKET, prefix=f"{PREFIX}/{BASE}/", match_glob="**/manifest.json"):
        body = json.loads(blob.download_as_bytes())
        games.setdefault(body["season"], set()).update(map(int, body["failed"]))
    for blob in client.list_blobs(BUCKET, prefix=f"{PREFIX}/{BASE}/", match_glob="**/names.parquet"):
        found = pl.read_parquet(blob.download_as_bytes()).filter(pl.col("api_id").is_in(players))
        seasons.update(found["season"].to_list())
    for season in sorted(seasons):
        for blob in client.list_blobs(BUCKET, prefix=f"{PREFIX}/{BASE}/{season}/", match_glob="**/rosters.parquet"):
            rosters = pl.read_parquet(blob.download_as_bytes(), columns=["game_id", "api_id"])
            games.setdefault(season, set()).update(rosters.filter(pl.col("api_id").is_in(players))["game_id"])
    return {season: ids for season, ids in games.items() if ids}


def compare(old, new):
    """Return how frame new differs from old: columns added, dropped or retyped, and the changed cells per column."""
    out = {"added": sorted(set(new.columns) - set(old.columns)), "dropped": sorted(set(old.columns) - set(new.columns))}
    common = [c for c in new.columns if c in old.columns and c != "cs_version"]
    out["retyped"] = {c: [str(old.schema[c]), str(new.schema[c])] for c in common if old.schema[c] != new.schema[c]}
    if old.height != new.height:
        out["rows"] = [old.height, new.height]
        return out
    out["cells"], out["float_noise"], out["empty_to_null"] = {}, {}, {}
    for c in common:
        a, b = old[c], new[c]
        if c in out["retyped"]:
            a, b = a.cast(pl.String, strict=False), b.cast(pl.String, strict=False)
        changed = a.ne_missing(b)
        if not changed.any():
            continue
        if a.dtype.is_float():
            # A change in the last bits is arithmetic order, not data, so it is counted apart
            noise = changed & ((a - b).abs() <= 1e-9 * a.abs().clip(lower_bound=1))
            out["float_noise"][c] = int(noise.sum())
            changed = changed & ~noise
        elif a.dtype == pl.String:
            # 1.9.0 writes null where earlier builds wrote an empty string
            emptied = changed & (a == "").fill_null(False) & b.is_null()
            out["empty_to_null"][c] = int(emptied.sum())
            changed = changed & ~emptied
        if changed.any():
            out["cells"][c] = int(changed.sum())
    out["float_noise"] = {c: n for c, n in out["float_noise"].items() if n}
    out["empty_to_null"] = {c: n for c, n in out["empty_to_null"].items() if n}
    return out


def diff_season(bucket, season):
    """Compare one season's frames with SWEEP_BASE's, reading overlay games from the overlay commit, as xG does."""
    from concurrent.futures import ThreadPoolExecutor

    def read(path):
        return json.loads(bucket.blob(path).download_as_bytes())

    new, base = read(f"{PREFIX}/{COMMIT}/{season}/manifest.json"), read(f"{PREFIX}/{BASE}/{season}/manifest.json")
    overlay_blob = bucket.blob(f"{PREFIX}/{BASE}/{season}/overlay.json")
    overlay = json.loads(overlay_blob.download_as_bytes()) if overlay_blob.exists() else None
    corrected = set(overlay["game_ids"]) if overlay else set()
    overlay_commit = overlay["overlay_commit"] if overlay else BASE
    base_games = set(base["game_ids"]) | corrected
    games = sorted(set(new["game_ids"]) & base_games)

    def frames(commit, game_id):
        return {
            name: pl.read_parquet(
                bucket.blob(f"{PREFIX}/{commit}/{season}/{game_id}/{name}.parquet").download_as_bytes()
            )
            for name in FRAMES
        }

    def one_game(game_id):
        old = frames(overlay_commit if game_id in corrected else BASE, game_id)
        now = frames(COMMIT, game_id)
        return game_id, {name: compare(old[name], now[name]) for name in FRAMES}

    per_frame: dict[str, dict] = {
        name: {
            "added": [],
            "dropped": [],
            "retyped": {},
            "rows": {},
            "columns": {},
            "float_noise": {},
            "empty_to_null": {},
        }
        for name in FRAMES
    }
    summary = {
        "season": season,
        "base": BASE,
        "commit": COMMIT,
        "games": len(games),
        "only_in_base": sorted(base_games - set(new["game_ids"])),
        "only_in_commit": sorted(set(new["game_ids"]) - base_games),
        "frames": per_frame,
    }
    with ThreadPoolExecutor(16) as pool:
        for game_id, result in pool.map(one_game, games):
            for name, found in result.items():
                frame = per_frame[name]
                frame["added"] = sorted(set(frame["added"]) | set(found["added"]))
                frame["dropped"] = sorted(set(frame["dropped"]) | set(found["dropped"]))
                frame["retyped"].update(found["retyped"])
                if "rows" in found:
                    frame["rows"][str(game_id)] = found["rows"]
                for column, cells in found.get("cells", {}).items():
                    entry = frame["columns"].setdefault(column, {"games": 0, "cells": 0, "first_games": []})
                    entry["games"] += 1
                    entry["cells"] += cells
                    if len(entry["first_games"]) < 20:
                        entry["first_games"].append(game_id)
                for kind in ("float_noise", "empty_to_null"):
                    for column, cells in found.get(kind, {}).items():
                        frame[kind][column] = frame[kind].get(column, 0) + cells
    return summary


def diff(seasons):
    """Compare uploaded seasons with SWEEP_BASE's and upload each summary, skipping seasons already compared."""
    from google.cloud import storage

    if not BASE or BASE == COMMIT:
        raise SystemExit("set SWEEP_BASE to the full commit to compare against, which must differ from SWEEP_COMMIT")
    bucket = storage.Client().bucket(BUCKET)
    if not seasons:
        manifests = bucket.list_blobs(prefix=f"{PREFIX}/{COMMIT}/", match_glob=f"{PREFIX}/{COMMIT}/*/manifest.json")
        seasons = sorted(int(blob.name.split("/")[-2]) for blob in manifests)
    for season in seasons:
        target = bucket.blob(f"{PREFIX}/{COMMIT}/diffs/{season}_vs_{BASE}.json")
        if target.exists():
            continue
        summary = diff_season(bucket, season)
        target.upload_from_string(json.dumps(summary, indent=1))
        changed = {name: len(frame["columns"]) + len(frame["rows"]) for name, frame in summary["frames"].items()}
        print(season, summary["games"], "games compared; changed columns or row counts by frame:", changed, flush=True)


def overlay(players):
    """Scrape again the base sweep's failed games and the games of players, then upload each season's overlay."""
    from google.cloud import storage

    check_commit()
    if not BASE or len(COMMIT) != 40 or COMMIT == BASE:
        raise SystemExit("set SWEEP_BASE, and SWEEP_COMMIT to the overlay's full commit, which must differ from it")
    bucket = storage.Client().bucket(BUCKET)
    games = overlay_games(players)
    print({season: len(ids) for season, ids in sorted(games.items())}, flush=True)
    rows = {row["game_id"]: row for row in results(OVERLAY)}
    for season, ids in sorted(games.items()):
        for game_id in sorted(ids - rows.keys()):
            rows[game_id] = one(game_id, OVERLAY_ROOT)
            with OVERLAY.open("a") as out:
                out.write(json.dumps(rows[game_id]) + "\n")
            time.sleep(GAP)
        season_rows = [rows[game_id] for game_id in sorted(ids)]
        body = {
            "season": season,
            "base_commit": BASE,
            "overlay_commit": COMMIT,
            "overlay_version": chickenstats.__version__,
            "game_ids": [row["game_id"] for row in season_rows if row.get("ok")],
            "failed": {
                str(row["game_id"]): row.get("error") or row.get("reasons") for row in season_rows if not row.get("ok")
            },
        }
        folder = OVERLAY_ROOT / str(season)
        count = copy(folder, f"{PREFIX}/{COMMIT}/{season}") if folder.exists() else 0
        bucket.blob(f"{PREFIX}/{BASE}/{season}/overlay.json").upload_from_string(json.dumps(body, indent=1))
        print(season, len(body["game_ids"]), "ok", len(body["failed"]), "failed", count, "files", flush=True)


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
    elif sys.argv[1] == "diff":
        diff([int(season) for season in sys.argv[2:]])
    elif sys.argv[1] == "overlay":
        overlay([int(player) for player in sys.argv[2:]])
    else:
        run(int(sys.argv[3]) if len(sys.argv) > 3 else None)
