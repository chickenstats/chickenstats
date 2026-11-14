"""Every chickenstats name that chickenstats-api and chickenstats-xg import, so a rename fails here first (ds-11)."""

import importlib

import pytest

DOWNSTREAM_IMPORTS: dict[str, list[str]] = {
    "chickenstats.chicken_nhl": [
        "Player",
        "Scraper",
        "Season",
        "prep_lines",
        "prep_stats",
        "prep_stints",
        "prep_team_stats",
    ],
    "chickenstats.chicken_nhl._validation_schema": [
        "pandas_dtype_map",
        "pandas_pandera_options",
        "polars_dtype_map",
        "polars_pandera_options",
    ],
    "chickenstats.chicken_nhl._validation_utils": ["build_pandera_schema"],
    "chickenstats.chicken_nhl.contract": [
        "CHRONOLOGICAL_COLUMNS",
        "EVENT_SORT_ORDER",
        "PBP_ORDER_COLUMNS",
        "STRENGTH_STATES",
        "assert_chronological",
        "assert_unique_events",
        "build_pandera_schema",
        "polars_dtype_map",
        "polars_pandera_options",
        "sort_chronological",
    ],
    "chickenstats.chicken_nhl.rapm": ["build_position_map", "build_rapm_matrix"],
    "chickenstats.chicken_nhl.team": ["TEAM_COLORS"],
    "chickenstats.utilities": ["ChickenProgress", "ChickenProgressIndeterminate", "track"],
    "chickenstats.utilities.enums": ["FORWARDS", "Zone"],
}

# Names that only exist with an optional package installed
OPTIONAL_PACKAGES: dict[str, str] = {
    "build_position_map": "scipy",
    "build_rapm_matrix": "scipy",
    "pandas_dtype_map": "pandas",
}


@pytest.mark.parametrize(
    ("module", "name"), [(module, name) for module, names in DOWNSTREAM_IMPORTS.items() for name in names]
)
def test_a_downstream_import_still_resolves(module, name):
    if name in OPTIONAL_PACKAGES:
        pytest.importorskip(OPTIONAL_PACKAGES[name])

    assert hasattr(importlib.import_module(module), name)
