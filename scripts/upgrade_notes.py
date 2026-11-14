#!/usr/bin/env python3
"""Collect the Breaking: paragraphs of a release's commits for its upgrade page.

Every commit that changes a returned value, a column, a signature or a default
is a `!` commit with a Breaking: paragraph (CONTRIBUTING.md). This lists those
paragraphs, grouped by the part of the package each commit touched, with a link
to the commit, so the upgrade page can be seeded from them and checked against
them.

    upgrade_notes.py                                   print the entries for origin/main..HEAD
    upgrade_notes.py --range v1.8.3..HEAD              another range
    upgrade_notes.py --check docs/guide/upgrade_1_9.md  fail if a Breaking commit is not on the page

The printed entries are a starting point: the page is edited by hand after
that, and --check only asks that each commit's short hash appears on it.

Standard library only.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

COMMIT_URL = "https://github.com/chickenstats/chickenstats/commit/"
SHORT_HASH = 8

# The page's sections, in reading order. A commit goes in the area that matches the most of
# its changed source files.
AREAS: tuple[tuple[str, str], ...] = (
    ("Scraping and play-by-play", r"chicken_nhl/(_game_|_scraper_raw|_scraper_core|_corrections|game\.py|scraper\.py)"),
    (
        "Aggregated stats",
        r"chicken_nhl/(_aggregation|_agg_constants|identity|_scraper_stats|_validation_|score_adjustments/)",
    ),
    ("Saving and the cache", r"chicken_nhl/_scraper_persist\.py"),
    ("Season, Player and Team", r"chicken_nhl/(season|player|team|_season_constants)\.py"),
    ("Network and utilities", r"chickenstats/(utilities/|exceptions)"),
    ("Charts", r"chicken_nhl/viz/"),
    ("RAPM", r"chicken_nhl/rapm\.py"),
    ("The chickenstats.com API client", r"chickenstats/api/"),
    ("evolving_hockey", r"evolving_hockey/"),
)
OTHER_AREA = "Other"

# Ties go to the more specific area, so a cache change that also touches the scraper is filed
# under the cache, and a change to both modules under the module most users have
TIE_ORDER = (
    "Charts",
    "RAPM",
    "Saving and the cache",
    "Season, Player and Team",
    "The chickenstats.com API client",
    "Network and utilities",
    "Aggregated stats",
    "Scraping and play-by-play",
    "evolving_hockey",
)


@dataclass
class Entry:
    """One Breaking commit: its hash, summary, Breaking: paragraph and changed files."""

    sha: str
    summary: str
    breaking: str
    files: list[str] = field(default_factory=list)

    @property
    def area(self) -> str:
        """The upgrade-page section this commit belongs in."""
        source = [path for path in self.files if path.startswith("src/")]
        counts = {name: sum(bool(re.search(pattern, path)) for path in source) for name, pattern in AREAS}
        best = max(counts.values())
        return next(name for name in TIE_ORDER if counts[name] == best) if best else OTHER_AREA


def breaking_paragraph(body: str) -> str | None:
    """The text of the paragraph that starts with "Breaking:", joined onto one line."""
    for paragraph in re.split(r"\n\s*\n", body):
        if paragraph.startswith("Breaking:"):
            return " ".join(paragraph.removeprefix("Breaking:").split())
    return None


def git(*args: str) -> str:
    """Run a git command and return its output."""
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def entries(commit_range: str) -> list[Entry]:
    """Every commit in the range with a Breaking: paragraph, oldest first."""
    found = []
    for sha in git("rev-list", "--reverse", "--no-merges", commit_range).split():
        summary, _, body = git("show", "-s", "--format=%s%n%b", sha).partition("\n")
        paragraph = breaking_paragraph(body)
        if paragraph is None:
            continue
        files = git("show", "--name-only", "--format=", sha).split()
        found.append(Entry(sha[:SHORT_HASH], summary, paragraph, files))
    return found


def capitalize(text: str) -> str:
    """Capitalize a sentence, unless it starts with a name from the code, such as prep_stats."""
    first = text.split(" ", 1)[0]
    return text[0].upper() + text[1:] if first.isalpha() else text


def render(found: list[Entry]) -> str:
    """Markdown sections, one per area in AREAS order, each entry linked to its commit."""
    sections = []
    for name in [*(area for area, _ in AREAS), OTHER_AREA]:
        in_area = [e for e in found if e.area == name]
        if not in_area:
            continue
        lines = [f"## {name}", ""]
        for e in in_area:
            subject = re.sub(r"^[a-z]+(\([^)]*\))?!?: ", "", e.summary)
            lines += [f"- **{capitalize(subject)}** ([`{e.sha}`]({COMMIT_URL}{e.sha}))", ""]
            lines += [f"    {capitalize(e.breaking)}", ""]
        sections.append("\n".join(lines))
    return "\n".join(sections)


def missing(found: list[Entry], page: str) -> list[Entry]:
    """The entries whose short hash does not appear on the page."""
    return [e for e in found if e.sha not in page]


def main(argv: list[str] | None = None) -> int:
    """Print the entries, or check a page against them."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--range", default="origin/main..HEAD", help="git revision range (default origin/main..HEAD)")
    parser.add_argument("--check", type=Path, help="fail if a Breaking commit's hash is not on this page")
    args = parser.parse_args(argv)

    found = entries(args.range)
    if args.check is None:
        print(render(found))
        return 0

    absent = missing(found, args.check.read_text())
    for e in absent:
        print(f"{e.sha} {e.summary}", file=sys.stderr)
    if absent:
        print(f"{len(absent)} of {len(found)} Breaking commits are not on {args.check}", file=sys.stderr)
        return 1
    print(f"All {len(found)} Breaking commits are on {args.check}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
