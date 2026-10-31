"""CACHE_FORMAT changes whenever the frames a cache stores change (C1).

A cache only records its format number, its schema hash and the version that wrote each game. During
development the version stays the same, so a change to a cached frame's values that does not bump
CACHE_FORMAT would load stale frames from a cache written by an earlier commit. This test hashes every
cached frame of the saved games and ties the hash to the format number, so that change fails here.
"""

import hashlib
import json

import polars as pl
import polars.selectors as cs

from chickenstats.chicken_nhl._scraper_core import _SCRAPE_REGISTRY
from chickenstats.chicken_nhl._scraper_persist import CACHE_FORMAT

# One entry per format. Add a new one with each bump and never change an old one
FINGERPRINTS = {3: "700643130b6f5933"}


def fingerprint(frames: dict[str, pl.DataFrame]) -> str:
    """A hash of each frame's columns, types and values, with floats rounded so platforms agree."""
    digest = hashlib.sha256()
    for key in sorted(frames):
        frame = frames[key].with_columns(cs.float().round(9))
        digest.update(key.encode())
        digest.update(json.dumps({name: str(dtype) for name, dtype in frame.schema.items()}).encode())
        digest.update(json.dumps(frame.to_dicts(), default=str).encode())
    return digest.hexdigest()[:16]


def test_the_cached_frames_match_the_cache_format(all_saved_games):
    """A change to a cached frame bumps CACHE_FORMAT in the same commit, so older caches are refused."""
    found = fingerprint({key: getattr(all_saved_games, key) for key in _SCRAPE_REGISTRY})

    assert FINGERPRINTS.get(CACHE_FORMAT) == found, (
        f"The cached frames changed. Bump CACHE_FORMAT in _scraper_persist.py to {CACHE_FORMAT + 1} and add "
        f'{CACHE_FORMAT + 1}: "{found}" to FINGERPRINTS.'
        if found not in FINGERPRINTS.values()
        else f"These frames match format {next(k for k, v in FINGERPRINTS.items() if v == found)}."
    )
    assert len(set(FINGERPRINTS.values())) == len(FINGERPRINTS)
