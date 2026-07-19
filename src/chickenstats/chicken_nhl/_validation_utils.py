"""Utility functions used in validation.py.

Includes:
    * _get_base_type_and_nullable
    * pydantic_to_pandera
    * convert_pydantic_models
    * build_pandera_schema
    * pydantic_to_native_polars
"""

from __future__ import annotations

import typing
import types
import pandera.polars as pa_pl

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandera.pandas as pa_pd
from pydantic import BaseModel
import polars as pl

from chickenstats.exceptions import UnsupportedBackendError


def _get_base_type_and_nullable(annotation: typing.Any) -> tuple[typing.Any, bool]:
    """Extract the concrete base type and nullability flag from a Pydantic field annotation.

    Parameters:
        annotation (typing.Any):
            A Pydantic field annotation, as returned by ``model.model_fields[name].annotation``.

    Returns:
        tuple[type, bool]:
            ``(base_type, is_nullable)`` where ``base_type`` is a plain Python type (e.g.
            ``int``, ``str``) and ``is_nullable`` is ``True`` when the original annotation
            included ``None`` as a valid value.
    """
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


@typing.overload
def pydantic_to_pandera(
    model: type[BaseModel], dtype_map: dict, pandera_options: dict, engine: typing.Literal["polars"]
) -> pa_pl.DataFrameSchema: ...


@typing.overload
def pydantic_to_pandera(
    model: type[BaseModel], dtype_map: dict, pandera_options: dict, engine: typing.Literal["pandas"]
) -> pa_pd.DataFrameSchema: ...


def pydantic_to_pandera(
    model: type[BaseModel], dtype_map: dict, pandera_options: dict, engine: typing.Literal["polars", "pandas"]
) -> pa_pd.DataFrameSchema | pa_pl.DataFrameSchema:
    """Convert a Pydantic v2 model to a pandera DataFrameSchema.

    Parameters:
        model (type[BaseModel]):
            The Pydantic model whose fields define the schema columns.
        dtype_map (dict):
            Mapping from a plain Python type (e.g. ``int``, ``str``) to the
            corresponding pandera dtype for the chosen engine.
        pandera_options (dict):
            Keyword arguments forwarded to the ``DataFrameSchema`` constructor
            (e.g. ``{"coerce": True, "ordered": True}``).
        engine (str):
            Backend to build for — ``"polars"`` or ``"pandas"``.

    Returns:
        pa_pd.DataFrameSchema | pa_pl.DataFrameSchema:
            A pandera schema ready to validate DataFrames of the given engine type.
    """
    if engine not in ("pandas", "polars"):
        raise UnsupportedBackendError("Engine must be 'pandas' or 'polars'")

    columns = {}

    for field_name, field_info in model.model_fields.items():
        base_type, is_nullable = _get_base_type_and_nullable(field_info.annotation)
        pandera_dtype = dtype_map.get(base_type, base_type)

        if engine == "pandas":
            try:
                import pandera.pandas as pa_pd
            except ImportError as exc:
                raise ImportError(
                    "pandas is required for pandas schema validation. Install with: pip install chickenstats[pandas]"
                ) from exc
            columns[field_name] = pa_pd.Column(pandera_dtype, nullable=is_nullable)

        elif engine == "polars":
            columns[field_name] = pa_pl.Column(pandera_dtype, nullable=is_nullable)

    if engine == "pandas":
        import pandera.pandas as pa_pd

        return pa_pd.DataFrameSchema(columns, **pandera_options)
    else:
        return pa_pl.DataFrameSchema(columns, **pandera_options)


# Wrapper to convert multiple pydantic models at once
def convert_pydantic_models(pydantic_models: typing.Sequence[type[BaseModel]], dtype_map: dict) -> tuple:
    """Convert a sequence of Pydantic v2 models to native Polars schema dicts.

    Parameters:
        pydantic_models (Sequence[type[BaseModel]]):
            Pydantic models to convert, in the desired unpack order.
        dtype_map (dict):
            Mapping from plain Python types to ``pl.DataType`` instances
            (e.g. ``{int: pl.Int64, str: pl.String}``).

    Returns:
        tuple[dict[str, pl.DataType], ...]:
            One native Polars schema dict per input model, in input order.
    """
    polars_schemas = []

    for pydantic_model in pydantic_models:
        polars_schemas.append(pydantic_to_native_polars(pydantic_model, dtype_map))

    return tuple(polars_schemas)


@typing.overload
def build_pandera_schema(
    schema_dict: dict, dtype_map: dict, pandera_options: dict, engine: typing.Literal["polars"]
) -> pa_pl.DataFrameSchema: ...


@typing.overload
def build_pandera_schema(
    schema_dict: dict, dtype_map: dict, pandera_options: dict, engine: typing.Literal["pandas"]
) -> pa_pd.DataFrameSchema: ...


def build_pandera_schema(
    schema_dict: dict, dtype_map: dict, pandera_options: dict, engine: typing.Literal["polars", "pandas"]
) -> pa_pl.DataFrameSchema | pa_pd.DataFrameSchema:
    """Builds a pandera DataFrameSchema from a schema dictionary.

    Parameters:
        schema_dict (dict):
            A dictionary of column names and column options (e.g., nullable, default) to build the pandera DataFrameSchema.
        dtype_map (dict):
            A mapping of base datatypes to pandera datatypes.
        pandera_options (dict):
            A dictionary of options to build the pandera DataFrameSchema.
        engine (str):
            The backend engine to build the pandera DataFrameSchema. Either 'polars' or 'pandas'
    """
    if engine not in ("pandas", "polars"):
        raise UnsupportedBackendError("Engine must be 'pandas' or 'polars'")

    columns = {}

    for column_name, column_schema in schema_dict.items():
        base_dtype = column_schema["dtype"]
        pandera_dtype = dtype_map.get(base_dtype, base_dtype)

        is_nullable = column_schema["nullable"]
        is_required = column_schema["required"]
        default_value = column_schema["default"]

        column_kwargs: dict = {"nullable": is_nullable, "required": is_required}

        # False is the sentinel for "no default"; 0 and other falsy values are real defaults.
        if default_value is not False:
            column_kwargs["default"] = default_value

        if engine == "polars":
            columns[column_name] = pa_pl.Column(pandera_dtype, **column_kwargs)

        elif engine == "pandas":
            try:
                import pandera.pandas as pa_pd
            except ImportError as exc:
                raise ImportError(
                    "pandas is required for pandas schema validation. Install with: pip install chickenstats[pandas]"
                ) from exc
            columns[column_name] = pa_pd.Column(pandera_dtype, **column_kwargs)

    if engine == "polars":
        dataframe_schema = pa_pl.DataFrameSchema(columns, **pandera_options)

    elif engine == "pandas":
        import pandera.pandas as pa_pd

        dataframe_schema = pa_pd.DataFrameSchema(columns, **pandera_options)

    return dataframe_schema


def prepare_for_validation(df: pl.DataFrame, schema: pa_pl.DataFrameSchema) -> pl.DataFrame:
    """Select schema columns, then fill any missing required columns with their defaults.

    Selects df down to schema columns in schema order, then adds any required columns
    still absent using their schema defaults (optional columns are left absent). A
    second select after filling restores schema column order when new columns are added.
    """
    df_cols = set(df.columns)  # O(1) membership checks below

    present_cols = [c for c in schema.columns if c in df_cols]
    df = df.select(present_cols)
    df_cols = set(df.columns)  # refresh after select (drops non-schema cols)

    # Fill NaN→null for Float64 columns the schema expects as Int64.
    nan_to_null_cols = [
        c
        for c, col_obj in schema.columns.items()
        if c in df_cols and df.schema[c] == pl.Float64 and col_obj.dtype.type == pl.Int64  # type: ignore[union-attr]
    ]
    if nan_to_null_cols:
        df = df.with_columns([pl.col(c).fill_nan(None) for c in nan_to_null_cols])
        df_cols -= set(nan_to_null_cols)

    exprs = []
    for col_name, col_obj in schema.columns.items():
        if col_obj.required and col_name not in df_cols:
            default = col_obj.default
            if default is not None:
                exprs.append(pl.lit(default).alias(col_name))
    if exprs:
        df = df.with_columns(exprs)
        df_cols = set(df.columns)
        present_cols = [c for c in schema.columns if c in df_cols]
        df = df.select(present_cols)

    return df


def validate_dataframe(df: pl.DataFrame, schema: pa_pl.DataFrameSchema) -> pl.DataFrame:
    """Prepare and validate a Polars DataFrame against a pandera schema.

    Parameters:
        df (pl.DataFrame):
            The raw DataFrame to validate.
        schema (pa_pl.DataFrameSchema):
            The pandera Polars schema to validate against.

    Returns:
        pl.DataFrame:
            The validated (and coerced) DataFrame.
    """
    df = prepare_for_validation(df, schema)
    return schema.validate(df)


# Function to convert pydantic model to native polars dictionary-based schema
def pydantic_to_native_polars(model: type[BaseModel], dtype_map: dict) -> dict[str, pl.DataType]:
    """Convert a Pydantic v2 model to a native Polars schema dict.

    Parameters:
        model (type[BaseModel]):
            The Pydantic model whose fields define the schema columns.
        dtype_map (dict):
            Mapping from plain Python types to ``pl.DataType`` instances
            (e.g. ``{int: pl.Int64, str: pl.String}``). Unmapped types fall back to
            ``pl.String``.

    Returns:
        dict[str, pl.DataType]:
            Column-name → Polars dtype mapping ready for ``pl.from_dicts(..., schema=...)``.
    """
    polars_schema = {}

    for field_name, field_info in model.model_fields.items():
        base_type, _ = _get_base_type_and_nullable(field_info.annotation)
        polars_schema[field_name] = dtype_map.get(base_type, pl.String)

    return polars_schema
