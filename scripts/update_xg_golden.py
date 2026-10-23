"""Rebuild the xG input golden files from the saved games and show what changed.

Each saved game has a golden file of its xg_fields, one row per Fenwick attempt with the
danger flags, under tests/tests_chicken_nhl/mock_data/golden/. test_xg_golden.py fails when
the package's output differs from it, so a change to an xG input has to be made here, on
purpose. The games are scraped from the saved responses, with the network blocked.

    uv run python scripts/update_xg_golden.py          # print the differences
    uv run python scripts/update_xg_golden.py --write  # and rewrite the files
"""

import argparse
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import polars as pl
import requests
from requests.adapters import HTTPAdapter

from chickenstats.chicken_nhl import Scraper

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "tests" / "tests_chicken_nhl" / "mock_data" / "golden"
KEY = ["game_id", "event_idx"]

# The tests' network guard serves the saved responses; it is not in a package, so it is run from its path
network_guard = runpy.run_path(str(ROOT / "tests" / "conftest.py"))

SAVED_GAME_IDS = [2023020001, 2023020125, 2023020411, 2023030223, 2023020015, 2010020012, 2017030111]


def golden_path(game_id: int) -> Path:
    """Return the golden file for a game."""
    return GOLDEN_DIR / f"xg_inputs_{game_id}.csv"


def read_golden(game_id: int, schema: pl.Schema) -> pl.DataFrame | None:
    """Read a game's golden file with the package's column types, or None when there is none."""
    path = golden_path(game_id)
    if not path.exists():
        return None
    golden = pl.read_csv(path, infer_schema=False)
    return golden.with_columns(pl.col(c).cast(schema[c]) for c in golden.columns if c in schema)


def scrape_xg_fields(game_id: int) -> pl.DataFrame:
    """Scrape a saved game's xg_fields with the network blocked."""
    with (
        patch.object(requests.Session, "get", network_guard["_guarded_get"]),
        patch.object(HTTPAdapter, "send", network_guard["_guarded_send"]),
    ):
        return Scraper([game_id], disable_progress_bar=True).xg_fields


def differences(old: pl.DataFrame, new: pl.DataFrame) -> list[str]:
    """Describe the rows added or removed and, for each column, the rows whose value changed."""
    lines = []
    added = new.join(old, on=KEY, how="anti")
    removed = old.join(new, on=KEY, how="anti")
    if added.height:
        lines.append(f"  {added.height} rows added: event_idx {added['event_idx'].to_list()}")
    if removed.height:
        lines.append(f"  {removed.height} rows removed: event_idx {removed['event_idx'].to_list()}")

    both = old.join(new, on=KEY, how="inner", suffix="_new")
    for column in (c for c in new.columns if c not in KEY):
        changed = both.filter(pl.col(column).ne_missing(pl.col(f"{column}_new")))
        if changed.height:
            examples = changed.select("event_idx", column, f"{column}_new").head(5).rows()
            lines.append(f"  {column}: {changed.height} rows, e.g. (event_idx, old, new) {examples}")

    return lines


def main(argv: list[str] | None = None) -> int:
    """Print what changed for each saved game, and rewrite the golden files with --write."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rewrite the golden files")
    args = parser.parse_args(argv)

    changed = False
    for game_id in SAVED_GAME_IDS:
        new = scrape_xg_fields(game_id)
        old = read_golden(game_id, new.schema)

        if old is None:
            lines = [f"  new file, {new.height} rows"]
        elif old.columns != new.columns:
            lines = [f"  columns changed: {old.columns} -> {new.columns}"]
        else:
            lines = differences(old, new)

        if lines:
            changed = True
            print(game_id)
            print("\n".join(lines))
            if args.write:
                GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
                new.write_csv(golden_path(game_id))

    if not changed:
        print("The golden files match the package.")

    return 1 if changed and not args.write else 0


if __name__ == "__main__":
    sys.exit(main())
