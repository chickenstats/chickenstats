"""Native Polars schemas and Polars-engine pandera DataFrameSchemas.

Native schemas (``dict[str, pl.DataType]``) are generated from Pydantic models via
``convert_pydantic_models`` and used to type-coerce raw data on ingest (passed as the
``schema`` argument to ``pl.from_dicts``).

Pandera schemas (``pa_pl.DataFrameSchema``) are built from Pydantic models or field-dict
registries and used for post-aggregation validation of cleaned DataFrames.

Native schemas:
    api_events_polars_schema, api_rosters_polars_schema, changes_polars_schema,
    html_events_polars_schema, html_rosters_polars_schema, rosters_polars_schema,
    shifts_polars_schema, pbp_polars_schema, pbp_ext_polars_schema,
    xg_polars_schema, standings_polars_schema, schedule_polars_schema

Pandera schemas:
    pbp_pandera_polars, ind_stats_pandera_polars,
    oi_stats_pandera_polars, stats_pandera_polars, line_stats_pandera_polars,
    team_stats_pandera_polars
"""

from __future__ import annotations

import polars as pl

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
    StandingsTeam,
)
from chickenstats.chicken_nhl._validation_utils import (
    pydantic_to_pandera,
    convert_pydantic_models,
    build_pandera_schema,
)
from chickenstats.chicken_nhl._validation_schema import (
    polars_dtype_map,
    polars_pandera_options,
    ind_stats_fields,
    oi_stats_fields,
    stats_fields,
    line_stats_fields,
    team_stats_fields,
)

# ------------------------------
# Building polars native schemas
# ------------------------------

pydantic_models = [
    APIEvent,  # api_events_polars_schema
    APIRosterPlayer,  # api_rosters_polars_schema
    ChangeEvent,  # changes_polars_schema
    HTMLEvent,  # html_events_polars_schema
    HTMLRosterPlayer,  # html_rosters_polars_schema
    RosterPlayer,  # rosters_polars_schema
    PlayerShift,  # shifts_polars_schema
    PBPEvent,  # pbp_polars_schema
    PBPEventExt,  # pbp_ext_polars_schema
    XGFields,  # xg_polars_schema
    StandingsTeam,  # standings_polars_schema
]

# Unpack in the same order as pydantic_models above; tuple unpacking is position-safe
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
) = convert_pydantic_models(pydantic_models, dtype_map=polars_dtype_map)

# Special polars schema for schedule
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

# ------------------------------
# Building polars pandera schemas
# ------------------------------

# Play-by-play pandera schema for polars validation
pbp_pandera_polars = pydantic_to_pandera(
    PBPEvent, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)

# pandera schema for individual stats, excluding the on-ice statistics
ind_stats_pandera_polars = build_pandera_schema(
    ind_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)

# pandera schema for on-ice stats, excluding the individual statistics
oi_stats_pandera_polars = build_pandera_schema(
    oi_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)

# pandera schema for individual stats, combining individual, on-ice, per 60, and percent for / against stats
stats_pandera_polars = build_pandera_schema(
    stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)

# pandera schema for line stats
line_stats_pandera_polars = build_pandera_schema(
    line_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)

# pandera schema for team stats
team_stats_pandera_polars = build_pandera_schema(
    team_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)
