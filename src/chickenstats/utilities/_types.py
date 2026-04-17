"""Shared type aliases for DataFrame inputs across the package."""

from __future__ import annotations

from typing import TypeAlias

import pandas as pd
import polars as pl
import pyarrow as pa

#: Union of all supported input DataFrame types.
#: Used in public-facing function signatures that accept any backend.
DataFrameT: TypeAlias = pl.DataFrame | pl.LazyFrame | pd.DataFrame | pa.Table
