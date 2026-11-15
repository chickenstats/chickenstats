"""Shared type aliases, type variables and backend literals for DataFrame inputs and outputs.

``DataFrameT`` is what a function accepts. ``FrameT`` is what a class returns: ``Scraper``, ``Season``, ``Game`` and
``ChickenStats`` are generic over it, and the ``backend`` overloads on each class choose it. It defaults to a polars
DataFrame, the default backend at runtime.

pandas and pyarrow are optional, so they are named only for type checkers.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import polars as pl
from typing_extensions import TypeVar

from chickenstats.utilities.enums import Backend

if TYPE_CHECKING:
    import narwhals as nw
    import pandas as pd
    import pyarrow as pa

    # An eager frame given to a function whose backend defaults to the backend of its input
    InputFrameT = TypeVar("InputFrameT", pl.DataFrame, pd.DataFrame, pa.Table, nw.DataFrame[Any])

    # Type checkers see a property; runtime gets cached_property
    frame_property = property
else:
    frame_property = cached_property

DataFrameT: TypeAlias = "pl.DataFrame | pl.LazyFrame | pd.DataFrame | pa.Table | nw.DataFrame[Any]"

NarwhalsFrame: TypeAlias = "nw.DataFrame[pl.DataFrame]"

FrameT = TypeVar("FrameT", default=pl.DataFrame)

PolarsBackend: TypeAlias = Literal["polars", Backend.POLARS]
PandasBackend: TypeAlias = Literal["pandas", Backend.PANDAS]
PyarrowBackend: TypeAlias = Literal["pyarrow", Backend.PYARROW]
NarwhalsBackend: TypeAlias = Literal["narwhals", Backend.NARWHALS]
AnyBackend: TypeAlias = Backend | Literal["polars", "pandas", "pyarrow", "narwhals"]
