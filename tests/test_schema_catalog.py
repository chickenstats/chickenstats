"""The schema reference pages and the schema snapshot match the package's schemas.

scripts/schema_catalog.py writes both from the schema dictionaries the package validates its
output with. A change to a column fails here until the script rewrites them, so the change
shows up in the diff of the commit that makes it.
"""

import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The script is not in a package, so it is run from its path, not imported
catalog = runpy.run_path(str(ROOT / "scripts" / "schema_catalog.py"))
FRAMES = catalog["FRAMES"]
FIX = "run `python scripts/schema_catalog.py --write` and commit the result"


def test_snapshot_matches_the_schemas():
    assert catalog["SNAPSHOT"].read_text() == catalog["snapshot"](), f"the schema snapshot is out of date; {FIX}"


@pytest.mark.parametrize("path", sorted(catalog["pages"]()), ids=lambda path: path.name)
def test_reference_page_matches_the_schema(path):
    assert path.exists(), f"{path.name} is missing; {FIX}"
    assert path.read_text() == catalog["pages"]()[path], f"{path.name} is out of date; {FIX}"


def test_no_page_for_a_frame_that_is_gone():
    pages = {path.name for path in catalog["PAGES_DIR"].glob("*.md")}
    assert pages == {path.name for path in catalog["pages"]()}


def test_every_page_is_in_the_nav():
    nav = (ROOT / "zensical.toml").read_text()
    missing = [path.name for path in catalog["pages"]() if f'"reference/schemas/{path.name}"' not in nav]
    assert not missing, "add these pages to the nav in zensical.toml"


def test_every_frame_has_one_key():
    keys = [frame.key for frame in FRAMES]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("name", "unit"),
    [
        ("toi", "minutes"),
        ("toi_seconds", "seconds"),
        ("seconds_since_stoppage", "seconds"),
        ("event_length", "seconds"),
        ("cf_p60", "per 60 minutes"),
        ("xgf_percent", "share, 0 to 1"),
        ("event_angle", "degrees"),
        ("goals", ""),
    ],
)
def test_unit_from_column_name(name, unit):
    assert catalog["unit"](name) == unit
