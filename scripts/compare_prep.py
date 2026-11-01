#!/usr/bin/env python3
"""Compare every prep_* output between two git revisions, column by column.

Builds every level and flag combination at both revisions from the same saved frames,
then reports each output that differs, allowing floats a rounding error of 1e-9. Use it to
prove a rewrite changes nothing:

    compare_prep.py pbp.parquet ext.parquet --base HEAD

The play-by-play must carry the cs_version of both revisions. Exits 1 if anything differs.
"""

import argparse
import itertools
import os
import pathlib
import subprocess
import sys
import tempfile

import polars as pl

LEVELS = ("period", "game", "session", "season")
FLAGS = ("strength_state", "score", "teammates", "opposition")
NO_EXT = ("prep_ind", "prep_stints")
TOLERANCE = 1e-9


def combinations() -> list[tuple[str, dict]]:
    """Return one (function name, arguments) pair per output to build."""
    calls = []
    for level, values in itertools.product(LEVELS, itertools.product((False, True), repeat=len(FLAGS))):
        flags = dict(zip(FLAGS, values, strict=True))
        calls += [(name, {"level": level, **flags}) for name in ("prep_ind", "prep_oi", "prep_stats")]
        calls += [("prep_lines", {"level": level, "position": p, **flags}) for p in ("f", "d")]
        if not flags["teammates"]:
            team_flags = {k: v for k, v in flags.items() if k != "teammates"}
            calls.append(("prep_team_stats", {"level": level, **team_flags}))
    calls.append(("prep_stints", {}))
    return calls


def key(name: str, arguments: dict) -> str:
    """Name an output's file after its function and arguments."""
    return "__".join([name, *(f"{k}={v}" for k, v in sorted(arguments.items()))])


def dump(pbp_path: str, ext_path: str, out: pathlib.Path) -> None:
    """Build every output with the installed chickenstats and write it to ``out``."""
    import chickenstats.chicken_nhl as nhl

    pbp, ext = pl.read_parquet(pbp_path), pl.read_parquet(ext_path)
    for name, arguments in combinations():
        path = out / f"{key(name, arguments)}.parquet"
        function = getattr(nhl, name)
        try:
            frame = function(pbp, **arguments) if name in NO_EXT else function(pbp, ext, **arguments)
        except Exception as error:  # An error is an output too, and has to match
            path.with_suffix(".error").write_text(f"{type(error).__name__}: {error}")
            continue
        frame.write_parquet(path)


def differences(base: pathlib.Path, head: pathlib.Path) -> list[str]:
    """Return one line per output or column that differs."""
    lines = []
    names = sorted({path.name for folder in (base, head) for path in folder.iterdir()})
    for name in names:
        old, new = base / name, head / name
        if not old.exists() or not new.exists():
            lines.append(f"{name}: only at one revision")
        elif name.endswith(".error"):
            if old.read_text() != new.read_text():
                lines.append(f"{name}: different error")
        else:
            lines += [f"{name}: {line}" for line in frame_differences(pl.read_parquet(old), pl.read_parquet(new))]
    return lines


def frame_differences(old: pl.DataFrame, new: pl.DataFrame) -> list[str]:
    """Compare two frames exactly, order included."""
    if old.schema != new.schema:
        changed = set(old.schema.items()) ^ set(new.schema.items())
        return [f"schema differs: {sorted(str(item) for item in changed)}"]
    if old.height != new.height:
        return [f"{old.height} rows, then {new.height}"]
    lines = []
    for column in old.columns:
        if old[column].equals(new[column], null_equal=True):
            continue
        if old[column].dtype.is_float() and old[column].is_null().equals(new[column].is_null()):
            gap = (old[column] - new[column]).abs()
            if (gap <= TOLERANCE).all():
                continue  # Float sums depend on the order of their terms
            lines.append(f"{column} differs by up to {gap.max()}")
        else:
            lines.append(column)
    return lines


def main() -> None:
    """Dump both revisions and report what differs."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pbp", help="parquet file of play_by_play")
    parser.add_argument("ext", help="parquet file of play_by_play_ext")
    parser.add_argument("--base", default="HEAD~1", help="revision to compare against")
    parser.add_argument("--head", help="revision to check (default the working tree)")
    parser.add_argument("--dump", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.dump:
        dump(args.pbp, args.ext, pathlib.Path(args.dump))
        return

    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary)
        for side, revision in (("base", args.base), ("head", args.head)):
            out = root / side
            out.mkdir()
            command = [sys.executable, __file__, args.pbp, args.ext, "--dump", str(out)]
            if revision is None:
                source = pathlib.Path(__file__).parent.parent / "src"
                subprocess.run(command, check=True, env={**os.environ, "PYTHONPATH": str(source)})
                continue
            tree = root / f"{side}_tree"
            subprocess.run(["git", "worktree", "add", "--detach", "--quiet", str(tree), revision], check=True)
            try:
                subprocess.run(command, check=True, env={**os.environ, "PYTHONPATH": str(tree / "src")})
            finally:
                subprocess.run(["git", "worktree", "remove", "--force", str(tree)], check=True)

        lines = differences(root / "base", root / "head")
        count = sum(1 for _ in (root / "head").iterdir())

    print("\n".join(lines) if lines else f"All {count} outputs match")
    sys.exit(1 if lines else 0)


if __name__ == "__main__":
    main()
