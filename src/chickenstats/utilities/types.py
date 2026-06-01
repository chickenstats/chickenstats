"""Shared type aliases for DataFrame inputs across the package."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

    DataFrameT = pl.DataFrame | pl.LazyFrame | pd.DataFrame | pa.Table
else:
    DataFrameT = pl.DataFrame  # runtime placeholder; only polars is guaranteed
