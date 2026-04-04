from __future__ import annotations

import datetime as dt
import typing
import types

import pandera.pandas as pa_pd
import pandera.polars as pa_pl
from pydantic import BaseModel

import polars as pl

from chickenstats.exceptions import UnsupportedBackendError


# Shared dtype maps — defined once, consumed by all converter functions

PANDAS_DTYPE_MAP: dict = {
    int: pa_pd.Int64,  # Int64 (capital I) supports NaN/None natively
    str: pa_pd.String,
    float: pa_pd.Float64,
    bool: pa_pd.Bool,
    dt.datetime: pa_pd.DateTime,
}

POLARS_DTYPE_MAP: dict = {
    int: pl.Int64,
    str: pl.String,
    float: pl.Float64,
    bool: pl.Boolean,
    dt.datetime: pl.Datetime,
    dt.date: pl.Date,
    dt.timedelta: pl.Duration,
}


def _get_base_type_and_nullable(annotation: typing.Any) -> tuple[typing.Any, bool]:
    """Extracts the base type and nullability from a type hint."""
    is_nullable = False
    base_type = annotation

    # Pure string annotations
    if isinstance(annotation, str):
        if annotation.startswith(("list[", "List[")):
            inner_str = annotation.split("[")[1].split("]")[0].strip()
            if "int" in inner_str:
                return int, False
            elif "float" in inner_str:
                return float, False
            elif "bool" in inner_str:
                return bool, False
            else:
                return str, False
        elif annotation in ("list", "List"):
            return str, False  # Fallback for pure string lists

    origin = typing.get_origin(base_type)
    args = typing.get_args(base_type)

    # Check for Optional/Union types (e.g., list[int] | None)
    is_union = origin is typing.Union or (hasattr(types, "UnionType") and origin is types.UnionType)

    if is_union:
        if type(None) in args:
            is_nullable = True
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                # Prefer concrete non-list types over bare `list` for unions like `list | int | None`
                non_list_args = [a for a in non_none_args if a is not list and typing.get_origin(a) is not list]
                base_type = non_list_args[0] if non_list_args else non_none_args[0]
                origin = typing.get_origin(base_type)
                args = typing.get_args(base_type)

    # Flatten lists to their inner types
    if origin is list or base_type is list:
        if args:
            base_type = args[0]  # Extract the inner type from `list[type]`
        else:
            base_type = str  # Fallback to string if it's just `list`

    return base_type, is_nullable


def pydantic_to_pandera(
    model: type[BaseModel], engine: typing.Literal["polars", "pandas"] = "polars"
) -> pa_pd.DataFrameSchema | pa_pl.DataFrameSchema:
    """Converts a Pydantic V2 model to a Pandera DataFrameSchema.

    Parameters:
        model (type[BaseModel]):
            The Pydantic model to convert.
        engine (str):
            'polars' or 'pandas'
    """
    if engine not in ("pandas", "polars"):
        raise UnsupportedBackendError("Engine must be 'pandas' or 'polars'")

    columns = {}

    for field_name, field_info in model.model_fields.items():
        base_type, is_nullable = _get_base_type_and_nullable(field_info.annotation)

        if engine == "pandas":
            pa_dtype = PANDAS_DTYPE_MAP.get(base_type, base_type)
            columns[field_name] = pa_pd.Column(pa_dtype, nullable=is_nullable)

        elif engine == "polars":
            pl_dtype = POLARS_DTYPE_MAP.get(base_type, base_type)
            columns[field_name] = pa_pl.Column(pl_dtype, nullable=is_nullable)

    if engine == "pandas":
        return pa_pd.DataFrameSchema(
            columns, coerce=True, ordered=True, unique_column_names=True, add_missing_columns=True, strict="filter"
        )
    else:
        return pa_pl.DataFrameSchema(columns, coerce=True, ordered=True, add_missing_columns=True, strict="filter")


def build_pandera_schema(
    column_specs: dict[str, dict],
    engine: typing.Literal["pandas", "polars"] = "polars",
    strict: bool | typing.Literal["filter"] = "filter",
    add_missing_columns: bool = True,
    coerce: bool = True,
    ordered: bool = True,
) -> pa_pd.DataFrameSchema | pa_pl.DataFrameSchema:
    """Build a pandera pandas or polars DataFrameSchema from engine-agnostic column specs.

    Each entry in column_specs is a dict with the following keys:
        type     (required) — Python type: int, str, float, or bool
        nullable (optional) — whether the column allows nulls; default False
        required (optional) — whether the column must be present; default True
        default  (optional) — fill value when add_missing_columns=True; default None

    This is the counterpart to pydantic_to_pandera() for columns that have no pydantic
    equivalent (e.g. computed stats like g_p60, gf_percent, g_adj).

    Parameters:
        column_specs:
            Dict mapping column name to a spec dict.
        engine:
            'pandas' or 'polars'
        strict:
            Pandera strict mode; 'filter' drops unknown columns.
        add_missing_columns:
            Whether pandera should fill missing columns with their default value.
        coerce:
            Whether pandera should coerce column dtypes.
        ordered:
            Whether pandera should enforce column order.

    Examples:
        >>> SPECS = {
        ...     "season": {"type": int},
        ...     "g": {"type": int, "default": 0},
        ...     "g_adj": {"type": float, "default": 0},
        ...     "api_id": {"type": int, "nullable": True, "required": False},
        ... }
        >>> pandas_schema = build_pandera_schema(SPECS, engine="pandas")
        >>> polars_schema = build_pandera_schema(SPECS, engine="polars")
    """
    if engine not in ("pandas", "polars"):
        raise UnsupportedBackendError("Engine must be 'pandas' or 'polars'")

    columns = {}

    for col_name, spec in column_specs.items():
        base_type = spec["type"]
        is_nullable = spec.get("nullable", False)
        is_required = spec.get("required", True)
        default = spec.get("default", None)

        if engine == "pandas":
            pa_dtype = PANDAS_DTYPE_MAP.get(base_type, base_type)
            kwargs: dict = {"nullable": is_nullable, "required": is_required}
            if default is not None:
                kwargs["default"] = default
            columns[col_name] = pa_pd.Column(pa_dtype, **kwargs)

        else:
            pl_dtype = POLARS_DTYPE_MAP.get(base_type, base_type)
            kwargs = {"nullable": is_nullable, "required": is_required}
            if default is not None:
                kwargs["default"] = default
            columns[col_name] = pa_pl.Column(pl_dtype, **kwargs)

    if engine == "pandas":
        return pa_pd.DataFrameSchema(
            columns, strict=strict, add_missing_columns=add_missing_columns, coerce=coerce, ordered=ordered
        )
    else:
        return pa_pl.DataFrameSchema(
            columns, strict=strict, add_missing_columns=add_missing_columns, coerce=coerce, ordered=ordered
        )
