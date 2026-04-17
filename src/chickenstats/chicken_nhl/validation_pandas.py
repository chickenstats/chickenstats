"""pandera schema used for pandas validation.

Includes:
    * pbp_pandera_pandas - schema for play-by-play validation
    * xg_pandera_pandas - schema for xg training validation
    * stats_pandera_pandas - schema for combined individual stats (used by API upload)
"""

from __future__ import annotations

from chickenstats.chicken_nhl._validation_utils import pydantic_to_pandera, build_pandera_schema
from chickenstats.chicken_nhl._validation_schema import (
    pandas_dtype_map,
    pandas_pandera_options,
    xg_fields,
    stats_fields,
)
from chickenstats.chicken_nhl.validation_pydantic import PBPEvent

# ------------------------------
# Building pandas pandera schemas
# ------------------------------

# Play-by-play pandera schema for pandas validation
pbp_pandera_pandas = pydantic_to_pandera(
    PBPEvent, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
)

# xG pandera schema for pandas validation
xg_pandera_pandas = build_pandera_schema(
    xg_fields, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
)

# stats pandera schema for pandas validation (used by API upload in api.py)
stats_pandera_pandas = build_pandera_schema(
    stats_fields, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
)
