"""What check_dist.py lets through to a release, on made-up file lists."""

import runpy
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
# The script is not in a package, so it is run from its path, not imported
dist = SimpleNamespace(**runpy.run_path(str(ROOT / "scripts" / "check_dist.py")))

SDIST = ["chickenstats-1.9.0", "chickenstats-1.9.0/PKG-INFO", "chickenstats-1.9.0/src/chickenstats/__init__.py"]
WHEEL = [*dist.WHEEL_REQUIRED, "chickenstats/__init__.py", "chickenstats-1.9.0.dist-info/METADATA"]


def test_clean_sdist_passes():
    assert dist.sdist_problems(SDIST) == []


def test_sdist_with_local_or_test_files_fails():
    names = [*SDIST, "chickenstats-1.9.0/.claude/settings.local.json", "chickenstats-1.9.0/tests/data.csv"]

    assert dist.sdist_problems(names) == [
        "sdist has an unexpected path: .claude",
        "sdist has an unexpected path: tests",
    ]


def test_clean_wheel_passes():
    assert dist.wheel_problems(WHEEL) == []


def test_wheel_with_a_stray_package_fails():
    assert dist.wheel_problems([*WHEEL, "tests/conftest.py"]) == ["wheel has an unexpected path: tests"]


def test_wheel_without_a_data_file_fails():
    names = [name for name in WHEEL if name != "chickenstats/py.typed"]

    assert dist.wheel_problems(names) == ["wheel is missing: chickenstats/py.typed"]
