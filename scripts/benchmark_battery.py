#!/usr/bin/env python3
"""Scrape the release validation set in one Scraper and record its wall time and peak memory.

    benchmark_battery.py OUTDIR

Times the scrape and the default prep_stats, prep_lines and prep_team_stats, reading this process's
peak resident memory after each step. Then runs every invariant on the frames already in memory, so
the checks make no requests of their own. Writes OUTDIR/battery.json, and exits 1 if a game failed
or an invariant did not hold.

Run it in a fresh process, since peak memory never falls.
"""

import argparse
import json
import logging
import os
import platform
import runpy
import sys
import time
import warnings
from pathlib import Path

import chickenstats
from chickenstats.chicken_nhl import Scraper

INVARIANTS_FILE = Path(__file__).resolve().parent.parent / "tests" / "tests_chicken_nhl" / "invariants.py"
MEGABYTE = 1024**2
# ru_maxrss is in bytes on macOS and in kilobytes on Linux
RSS_UNIT = 1 if sys.platform == "darwin" else 1024
FRAMES = (
    "play_by_play",
    "play_by_play_ext",
    "xg_fields",
    "rosters",
    "html_rosters",
    "api_rosters",
    "shifts",
    "changes",
    "html_events",
    "api_events",
)


def peak_rss_mb() -> float:
    """Return this process's peak resident memory, in megabytes."""
    if sys.platform == "win32":
        # Windows has no resource module; the peak working set is its peak resident memory
        import psutil

        return psutil.Process().memory_info().peak_wset / MEGABYTE

    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * RSS_UNIT / MEGABYTE


class _Collect(logging.Handler):
    """Keep every warning the package logs."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(f"{record.levelname} {record.name}: {record.getMessage()}")


def main() -> None:
    """Scrape and aggregate the validation set, check it, and write what it took."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("outdir", type=Path, help="directory for battery.json")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    invariants = runpy.run_path(str(INVARIANTS_FILE))
    game_ids = invariants["VALIDATION_GAME_IDS"]

    collect = _Collect()
    logging.getLogger().addHandler(collect)
    steps: dict[str, dict[str, float]] = {}

    def record(name: str, began: float) -> None:
        steps[name] = {"seconds": round(time.perf_counter() - began, 1), "peak_rss_mb": round(peak_rss_mb(), 1)}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        start = time.perf_counter()

        began = time.perf_counter()
        scraper = Scraper(game_ids, disable_progress_bar=True)
        for frame in FRAMES:
            getattr(scraper, frame)
        record("scrape", began)

        for method in ("prep_stats", "prep_lines", "prep_team_stats"):
            began = time.perf_counter()
            getattr(scraper, method)(disable_progress_bar=True)
            record(method, began)

        total_seconds = round(time.perf_counter() - start, 1)
        peak = round(peak_rss_mb(), 1)

        # One scrape serves every check, so a failure must not hide the checks after it
        began = time.perf_counter()
        failures = []
        for check in invariants["INVARIANTS"]:
            try:
                check(scraper)
            except AssertionError as error:
                first_line = str(error).partition("\n")[0]
                failures.append(f"{check.__name__}: {first_line}")
        record("invariants", began)

    result = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "chickenstats": chickenstats.__version__,
        "cpus": os.cpu_count(),
        "games": len(game_ids),
        "failed_games": [str(game) for game in scraper.failed_games],
        "total_seconds": total_seconds,
        "peak_rss_mb": peak,
        "steps": steps,
        "invariant_failures": failures,
        "warnings": [f"{w.category.__name__}: {w.message}" for w in caught],
        "log_warnings": collect.messages,
    }
    # Player names are not ASCII, and the default encoding on Windows is not UTF-8
    (args.outdir / "battery.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        f"### {result['os']}, Python {result['python']}, {result['cpus']} CPUs",
        "",
        f"{result['games']} games, {total_seconds} s and {peak} MB peak to scrape and aggregate; "
        f"{len(result['failed_games'])} failed games, {len(failures)} invariant failures",
        "",
        "| step | seconds | peak RSS (MB) |",
        "| --- | --- | --- |",
        *(f"| {name} | {step['seconds']} | {step['peak_rss_mb']} |" for name, step in steps.items()),
    ]
    print("\n".join(lines))
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

    if result["failed_games"] or failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
