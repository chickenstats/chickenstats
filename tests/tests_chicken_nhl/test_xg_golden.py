"""The xG inputs of every saved game, pinned to golden files.

Each file holds a game's xg_fields, one row per Fenwick attempt with its danger flags, as
scripts/update_xg_golden.py wrote them. A change to any input fails here until that script
rewrites the file, so the change shows up in the diff of the commit that makes it.
"""

import os

import polars as pl
import polars.selectors as cs
import pytest
from polars.testing import assert_frame_equal

from conftest import MOCK_DATA_DIR
from test_invariants import SAVED_GAMES


@pytest.mark.parametrize("fixture", SAVED_GAMES)
def test_xg_inputs_match_the_golden_file(request, fixture):
    game = request.getfixturevalue(fixture)
    xg_fields = game.xg_fields

    golden = pl.read_csv(os.path.join(MOCK_DATA_DIR, "golden", f"xg_inputs_{game.game_id}.csv"), infer_schema=False)
    golden = golden.with_columns(pl.col(c).cast(xg_fields.schema[c]) for c in golden.columns if c in xg_fields.schema)

    # Trigonometry rounds differently in the last bits across platforms, and the files come from one of them
    floats = cs.float().round(9)
    assert_frame_equal(xg_fields.with_columns(floats), golden.with_columns(floats), check_exact=True)
