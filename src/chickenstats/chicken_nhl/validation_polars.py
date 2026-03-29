from __future__ import annotations

import typing
from collections.abc import Sequence
from pydantic import BaseModel
import polars as pl

import pandera.pandas as pa_pd
import pandera.polars as pa_pl

from chickenstats.exceptions import UnsupportedBackendError
from chickenstats.chicken_nhl.validation_pydantic import (
    APIEvent,
    APIRosterPlayer,
    ChangeEvent,
    HTMLEvent,
    HTMLRosterPlayer,
    RosterPlayer,
    PlayerShift,
    PBPEvent,
    PBPEventExt,
    XGFields,
    ScheduleGame,
    StandingsTeam,
)
from chickenstats.chicken_nhl._validation_utils import (
    POLARS_DTYPE_MAP,
    _get_base_type_and_nullable,
    pydantic_to_pandera,
)


# Function to convert pydantic model to native polars dictionary-based schema
def pydantic_to_native_polars(model: type[BaseModel]) -> dict[str, pl.DataType]:
    """Converts a Pydantic V2 model directly to a native Polars schema dictionary."""
    polars_schema = {}

    for field_name, field_info in model.model_fields.items():
        base_type, _ = _get_base_type_and_nullable(field_info.annotation)
        polars_schema[field_name] = POLARS_DTYPE_MAP.get(base_type, pl.String)

    return polars_schema


def convert_pydantic_models(pydantic_models: Sequence[type[BaseModel]]) -> tuple:
    """Convert list of pydantic models to native polars dictionary-based schemas."""
    polars_schemas = []

    for pydantic_model in pydantic_models:
        polars_schemas.append(pydantic_to_native_polars(pydantic_model))

    return tuple(polars_schemas)


# Function to convert pandera pandas schema to pandera polars schema, or native polars dictionary-based schema
def convert_pandas_pandera_to_polars(
    pandas_schema: pa_pd.DataFrameSchema, output_format: typing.Literal["pandera", "native"] = "pandera"
) -> pa_pl.DataFrameSchema | dict[str, pl.DataType]:
    """Converts a Pandas-based Pandera schema to a Polars-based Pandera schema or a native Polars dictionary schema.

    Parameters:
        pandas_schema (pa_pd.DataFrameSchema):
            The source Pandas Pandera DataFrameSchema.
        output_format (typing.Literal["pandera", "native"]):
            'pandera' (retains checks/metadata) or 'native' (raw pl.DataType dict).
    """
    if output_format not in ("pandera", "native"):
        raise UnsupportedBackendError("output_format must be either 'pandera' or 'native'")

    native_schema = {}
    pandera_columns = {}

    for col_name, column in pandas_schema.columns.items():
        # Map the Pandas dtype string to a Polars DataType
        dtype_str = str(column.dtype).lower()

        if "int" in dtype_str:
            if "8" in dtype_str:
                pl_type = pl.Int8
            elif "16" in dtype_str:
                pl_type = pl.Int16
            elif "32" in dtype_str:
                pl_type = pl.Int32
            else:
                pl_type = pl.Int64
        elif "float" in dtype_str:
            if "32" in dtype_str:
                pl_type = pl.Float32
            else:
                pl_type = pl.Float64
        elif "bool" in dtype_str:
            pl_type = pl.Boolean
        elif "str" in dtype_str or "string" in dtype_str:
            pl_type = pl.String
        elif "datetime" in dtype_str:
            pl_type = pl.Datetime
        elif "date" in dtype_str:
            pl_type = pl.Date
        elif "timedelta" in dtype_str or "duration" in dtype_str:
            pl_type = pl.Duration
        else:
            pl_type = pl.String  # Fallback for objects/unrecognized

        # Store the column based on the requested output format
        if output_format == "native":
            native_schema[col_name] = pl_type
        else:
            # Rebuild the Pandera column, transferring all metadata and checks
            pandera_columns[col_name] = pa_pl.Column(
                dtype=pl_type,
                checks=column.checks,
                nullable=column.nullable,
                unique=column.unique,
                title=column.title,
                description=column.description,
                default=column.default,
            )

    # Return the requested object type
    if output_format == "native":
        return native_schema

    return pa_pl.DataFrameSchema(
        columns=pandera_columns,
        coerce=pandas_schema.coerce,
        strict=pandas_schema.strict,  # ty: ignore[invalid-argument-type]
        name=pandas_schema.name,
        title=pandas_schema.title,
        description=pandas_schema.description,
    )


pydantic_models = [
    APIEvent,
    APIRosterPlayer,
    ChangeEvent,
    HTMLEvent,
    HTMLRosterPlayer,
    RosterPlayer,
    PlayerShift,
    PBPEvent,
    PBPEventExt,
    XGFields,
    StandingsTeam,
]

(
    api_events_polars_schema,
    api_rosters_polars_schema,
    changes_polars_schema,
    html_events_polars_schema,
    html_rosters_polars_schema,
    rosters_polars_schema,
    shifts_polars_schema,
    pbp_polars_schema,
    pbp_ext_polars_schema,
    xg_polars_schema,
    standings_polars_schema,
) = convert_pydantic_models(pydantic_models)

schedule_polars_schema = {
    "season": pl.Int64,
    "session": pl.Int64,
    "game_id": pl.Int64,
    "game_date": pl.String,
    "start_time": pl.String,
    "game_state": pl.String,
    "home_team": pl.String,
    "home_team_id": pl.Int64,
    "home_score": pl.Int64,
    "away_team": pl.String,
    "away_team_id": pl.Int64,
    "away_score": pl.Int64,
    "venue": pl.String,
    "venue_timezone": pl.String,
    "neutral_site": pl.Int64,
    "game_date_dt_utc": pl.Datetime(time_unit="us", time_zone="UTC"),
    "tv_broadcasts": pl.List(
        pl.Struct(
            {
                "id": pl.Int64,
                "market": pl.String,
                "countryCode": pl.String,
                "network": pl.String,
                "sequenceNumber": pl.Int64,
            }
        )
    ),
    "home_logo": pl.String,
    "home_logo_dark": pl.String,
    "away_logo": pl.String,
    "away_logo_dark": pl.String,
}
