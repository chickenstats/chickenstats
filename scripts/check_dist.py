#!/usr/bin/env python3
"""Check what a built sdist and wheel contain before they are published.

    check_dist.py dist/chickenstats-1.9.0.tar.gz dist/chickenstats-1.9.0-py3-none-any.whl

The sdist's allow-list in pyproject.toml decides what goes in; this catches the allow-list
being widened by mistake, and a wheel missing the data files the package reads at runtime.

Standard library only.
"""

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path

SDIST_TOP_LEVEL = {
    ".gitignore",
    "CHANGELOG.md",
    "CITATION.cff",
    "LICENSE",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
    "src",
}
# Read at runtime through importlib.resources, so an import alone would not show one is missing
WHEEL_REQUIRED = (
    "chickenstats/py.typed",
    "chickenstats/chicken_nhl/score_adjustments/score_adjustments.pkl.gz",
    "chickenstats/utilities/styles/chickenstats.mplstyle",
    "chickenstats/utilities/styles/chickenstats_dark.mplstyle",
)


def sdist_problems(names: list[str]) -> list[str]:
    """Return a line for each path in an sdist outside the allow-list."""
    # Every path starts with the chickenstats-<version>/ folder
    top_level = {name.split("/")[1] for name in names if "/" in name}
    return [f"sdist has an unexpected path: {path}" for path in sorted(top_level - SDIST_TOP_LEVEL)]


def wheel_problems(names: list[str]) -> list[str]:
    """Return a line for each unexpected top-level path in a wheel and each missing data file."""
    top_level = {name.split("/")[0] for name in names}
    unexpected = [path for path in sorted(top_level) if path != "chickenstats" and not path.endswith(".dist-info")]
    missing = [path for path in WHEEL_REQUIRED if path not in names]
    return [f"wheel has an unexpected path: {path}" for path in unexpected] + [
        f"wheel is missing: {path}" for path in missing
    ]


def main() -> int:
    """Check each file named on the command line, printing what is wrong with it."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dists", nargs="+", type=Path, help="sdist and wheel files to check")
    args = parser.parse_args()

    problems = []
    for dist in args.dists:
        if dist.name.endswith(".tar.gz"):
            with tarfile.open(dist) as sdist:
                problems += sdist_problems(sdist.getnames())
        elif dist.suffix == ".whl":
            with zipfile.ZipFile(dist) as wheel:
                problems += wheel_problems(wheel.namelist())
        else:
            problems.append(f"not an sdist or a wheel: {dist}")

    print("\n".join(problems) or f"{len(args.dists)} file(s) checked, nothing unexpected")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
