from chickenstats.chicken_nhl._validation_utils import build_pandera_schema
from chickenstats.chicken_nhl._validation_schema import polars_dtype_map, polars_pandera_options
from chickenstats.evolving_hockey._validation_schema import (
    pbp_fields,
    ind_stats_fields,
    oi_stats_fields,
    stats_fields,
    line_stats_fields,
    team_stats_fields,
)

# PBPSchema stays local — EH PBP format is unique to this module.
PBPSchema = build_pandera_schema(
    schema_dict=pbp_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)

# ---------------------------------------------------------------------------
# EH-specific stat schemas (polars only; no api_id — EH data is eh_id only)
# ---------------------------------------------------------------------------

eh_ind_stats_pandera_polars = build_pandera_schema(
    schema_dict=ind_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)
eh_oi_stats_pandera_polars = build_pandera_schema(
    schema_dict=oi_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)
eh_stats_pandera_polars = build_pandera_schema(
    schema_dict=stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)
eh_line_stats_pandera_polars = build_pandera_schema(
    schema_dict=line_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)
eh_team_stats_pandera_polars = build_pandera_schema(
    schema_dict=team_stats_fields, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
)
