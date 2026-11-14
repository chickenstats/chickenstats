"""How upgrade_notes.py finds Breaking: paragraphs and files them on the upgrade page.

The upgrade page is seeded from these entries and checked against them before a release, so
a paragraph it fails to find, or a commit it files nowhere, would leave a change off the page.
These run on made-up commits, without git.
"""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
# The script is not in a package, so it is run from its path, not imported
notes = SimpleNamespace(**runpy.run_path(str(ROOT / "scripts" / "upgrade_notes.py")))


def entry(files, sha="abcdef12", summary="fix!: change something", breaking="Something changes."):
    return notes.Entry(sha, summary, breaking, files)


def test_the_breaking_paragraph_is_joined_onto_one_line():
    body = "Why it changed.\n\nBreaking: prep_stats returns\nnull rates.\n\nMore detail."
    assert notes.breaking_paragraph(body) == "prep_stats returns null rates."


def test_a_commit_with_no_breaking_paragraph_has_none():
    assert notes.breaking_paragraph("Why it changed.\n\nNo Breaking here.") is None


@pytest.mark.parametrize(
    ("files", "area"),
    [
        (["src/chickenstats/chicken_nhl/_game_pbp.py"], "Scraping and play-by-play"),
        (
            ["src/chickenstats/chicken_nhl/_aggregation.py", "tests/tests_chicken_nhl/test_aggregation.py"],
            "Aggregated stats",
        ),
        # A tie goes to the more specific area
        (
            ["src/chickenstats/chicken_nhl/_scraper_core.py", "src/chickenstats/chicken_nhl/_scraper_persist.py"],
            "Saving and the cache",
        ),
        (
            ["src/chickenstats/chicken_nhl/_aggregation.py", "src/chickenstats/evolving_hockey/_aggregation.py"],
            "Aggregated stats",
        ),
        # Otherwise the area with the most changed files wins
        (
            [
                "src/chickenstats/chicken_nhl/_game_pbp.py",
                "src/chickenstats/chicken_nhl/_game_utils.py",
                "src/chickenstats/chicken_nhl/_aggregation.py",
            ],
            "Scraping and play-by-play",
        ),
        (["scripts/build_score_adjustments.py"], "Other"),
    ],
)
def test_a_commit_is_filed_under_its_area(files, area):
    assert entry(files).area == area


def test_entries_render_under_their_area_with_a_link_and_a_capital():
    page = notes.render([entry(["src/chickenstats/chicken_nhl/viz/_rink.py"], breaking="charts close their figures.")])

    assert page.startswith("## Charts\n")
    assert "- **Change something** ([`abcdef12`](https://github.com/chickenstats/chickenstats/commit/abcdef12))" in page
    assert "    Charts close their figures." in page


def test_check_lists_the_commits_missing_from_the_page():
    on_page, off_page = entry([], sha="11111111"), entry([], sha="22222222")

    assert notes.missing([on_page, off_page], "... ([`11111111`](...)) ...") == [off_page]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("charts close their figures.", "Charts close their figures."),
        ("prep_stats returns null rates.", "prep_stats returns null rates."),
        ("bsf, bsa and their adjusted columns change.", "bsf, bsa and their adjusted columns change."),
        ("Scraper.game_ids holds ints.", "Scraper.game_ids holds ints."),
    ],
)
def test_a_sentence_is_capitalized_unless_it_starts_with_a_name_from_the_code(text, expected):
    assert notes.capitalize(text) == expected
