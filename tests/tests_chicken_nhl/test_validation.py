import typing

import pandera.polars as pa_pl
import polars as pl
import pytest

try:
    import pandera.pandas as pa_pd

    HAS_PANDAS = True
except ImportError:
    pa_pd = None  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    HAS_PANDAS = False

from chickenstats.chicken_nhl._validation_utils import (
    _get_base_type_and_nullable,
    build_pandera_schema,
    coerce_to_schema,
    prepare_for_validation,
    pydantic_to_pandera,
    pydantic_to_native_polars,
    validate_dataframe,
)
from chickenstats.exceptions import UnsupportedBackendError
from chickenstats.chicken_nhl._validation_schema import (
    reorder_columns,
    polars_dtype_map,
    polars_pandera_options,
    pandas_pandera_options,
)

# pandas_dtype_map is built on first access and needs pandas; the tests that use it are skipped without it
if HAS_PANDAS:
    from chickenstats.chicken_nhl._validation_schema import pandas_dtype_map
else:
    pandas_dtype_map = {}
from chickenstats.chicken_nhl.validation_pydantic import APIEvent, ChangeEvent, PBPEvent
import chickenstats.chicken_nhl.validation_polars as chicken_schemas
import chickenstats.evolving_hockey.validation as eh_schemas
import pandera.errors as pa_errors

_skip_no_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")

# Minimal schema dict used by build_pandera_schema / prepare_for_validation tests
_SIMPLE_SCHEMA_DICT = {
    "name": {"dtype": str, "nullable": False, "default": False, "required": True},
    "count": {"dtype": int, "nullable": False, "default": 1, "required": True},
}

# Schema dict with an optional column and a required column that has a truthy default
_PREP_SCHEMA_DICT = {
    "a": {"dtype": int, "nullable": False, "default": False, "required": True},
    "b": {"dtype": str, "nullable": True, "default": False, "required": False},
    "c": {"dtype": int, "nullable": False, "default": 42, "required": True},
    "d": {"dtype": float, "nullable": False, "default": 0, "required": True},
}

# -----------------------------------------------------------------------------
# _get_base_type_and_nullable
# -----------------------------------------------------------------------------


class TestGetBaseTypeAndNullable:
    # -----------------------------------------------------------------------------
    # String annotation path
    # -----------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("annotation", "expected_type"),
        [
            ("list[int]", int),
            ("List[int]", int),
            ("list[float]", float),
            ("List[float]", float),
            ("list[bool]", bool),
            ("List[bool]", bool),
            ("list[str]", str),
            ("List[str]", str),
            ("list[object]", str),  # unrecognized inner type → str fallback
        ],
    )
    def test_string_annotation_list(self, annotation, expected_type) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(annotation)
        assert base_type is expected_type
        assert is_nullable is False

    @pytest.mark.parametrize("annotation", ["list", "List"])
    def test_string_annotation_bare_list(self, annotation) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(annotation)
        assert base_type is str
        assert is_nullable is False

    # -----------------------------------------------------------------------------
    # Union / Optional types
    # -----------------------------------------------------------------------------

    def test_optional_int(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(int | None)
        assert base_type is int
        assert is_nullable is True

    def test_optional_str(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(str | None)
        assert base_type is str
        assert is_nullable is True

    def test_non_nullable_int(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(int)
        assert base_type is int
        assert is_nullable is False

    def test_list_int_optional(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(list[int] | None)
        assert base_type is int
        assert is_nullable is True

    # -----------------------------------------------------------------------------
    # Typing.Optional (legacy form)
    # -----------------------------------------------------------------------------

    def test_typing_optional_float(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(typing.Optional[float])  # noqa: UP045
        assert base_type is float
        assert is_nullable is True


# -----------------------------------------------------------------------------
# pydantic_to_pandera — pandas engine path
# -----------------------------------------------------------------------------


class TestPydanticToPandera:
    def test_polars_engine_returns_polars_schema(self) -> None:
        schema = pydantic_to_pandera(
            PBPEvent, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
        )
        assert isinstance(schema, pa_pl.DataFrameSchema)

    @_skip_no_pandas
    def test_pandas_engine_returns_pandas_schema(self) -> None:
        schema = pydantic_to_pandera(
            PBPEvent, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
        )
        assert isinstance(schema, pa_pd.DataFrameSchema)

    @_skip_no_pandas
    def test_pandas_engine_columns_non_empty(self) -> None:
        schema = pydantic_to_pandera(
            PBPEvent, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
        )
        assert len(schema.columns) > 0

    def test_invalid_engine_raises(self) -> None:
        with pytest.raises(UnsupportedBackendError):
            pydantic_to_pandera(
                PBPEvent,
                dtype_map=polars_dtype_map,
                pandera_options=polars_pandera_options,
                engine=typing.cast(typing.Any, "duckdb"),
            )

    @_skip_no_pandas
    def test_pandas_engine_api_event(self) -> None:
        schema = pydantic_to_pandera(
            APIEvent, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
        )
        assert isinstance(schema, pa_pd.DataFrameSchema)
        assert len(schema.columns) > 0


# -----------------------------------------------------------------------------
# pydantic_to_native_polars
# -----------------------------------------------------------------------------


class TestPydanticToNativePolars:
    def test_returns_dict(self) -> None:
        schema = pydantic_to_native_polars(PBPEvent, dtype_map=polars_dtype_map)
        assert isinstance(schema, dict)

    def test_all_values_are_polars_dtypes(self) -> None:
        schema = pydantic_to_native_polars(PBPEvent, dtype_map=polars_dtype_map)
        for dtype in schema.values():
            assert isinstance(dtype, type | pl.DataType)

    def test_keys_match_model_fields(self) -> None:
        schema = pydantic_to_native_polars(PBPEvent, dtype_map=polars_dtype_map)
        assert set(schema.keys()) == set(PBPEvent.model_fields.keys())


# -----------------------------------------------------------------------------
# _get_base_type_and_nullable — string annotation, non-list branch (arc 50->53)
# -----------------------------------------------------------------------------


class TestGetBaseTypeNonList:
    def test_string_annotation_plain_type_passthrough(self) -> None:
        """A plain string annotation like 'int' (not a list type) falls through
        the list-matching block and returns the string itself."""
        base_type, is_nullable = _get_base_type_and_nullable("int")
        assert base_type == "int"
        assert is_nullable is False

    def test_string_annotation_plain_float_passthrough(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable("float")
        assert base_type == "float"
        assert is_nullable is False


# -----------------------------------------------------------------------------
# reorder_columns — explicit ordered_columns arg (branch 344->347)
# -----------------------------------------------------------------------------


class TestReorderColumns:
    @_skip_no_pandas
    def test_default_ordered_columns(self) -> None:
        """Without explicit ordered_columns, column_order is used."""
        cols = {"season": pa_pd.Column(pa_pd.String), "game_id": pa_pd.Column(pa_pd.Int64)}
        result = reorder_columns(cols)
        assert isinstance(result, dict)

    @_skip_no_pandas
    def test_explicit_ordered_columns(self) -> None:
        """Passing ordered_columns reorders to that explicit list."""
        cols = {"a": pa_pd.Column(pa_pd.String), "b": pa_pd.Column(pa_pd.Int64), "c": pa_pd.Column(pa_pd.Float64)}
        result = reorder_columns(cols, ordered_columns=("c", "a"))
        assert list(result.keys()) == ["c", "a"]

    @_skip_no_pandas
    def test_explicit_ordered_columns_skips_absent(self) -> None:
        """Keys in ordered_columns that don't exist in pandera_columns are skipped."""
        cols = {"a": pa_pd.Column(pa_pd.String)}
        result = reorder_columns(cols, ordered_columns=("a", "z"))
        assert list(result.keys()) == ["a"]


# -----------------------------------------------------------------------------
# ChangeEvent / PBPEvent fix_lists — non-dict branch (lines 162 / 485)
# -----------------------------------------------------------------------------


class TestFixListsNonDict:
    def test_change_event_non_dict_passthrough(self) -> None:
        """fix_lists returns non-dict input unchanged, triggering ValidationError downstream."""
        with pytest.raises(Exception):
            ChangeEvent.model_validate("not_a_dict")

    def test_pbp_event_non_dict_passthrough(self) -> None:
        """fix_lists returns non-dict input unchanged, triggering ValidationError downstream."""
        with pytest.raises(Exception):
            PBPEvent.model_validate("not_a_dict")


# -----------------------------------------------------------------------------
# build_pandera_schema
# -----------------------------------------------------------------------------


class TestBuildPanderaSchema:
    def test_polars_engine_returns_polars_schema(self) -> None:
        schema = build_pandera_schema(
            _SIMPLE_SCHEMA_DICT, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
        )
        assert isinstance(schema, pa_pl.DataFrameSchema)

    @_skip_no_pandas
    def test_pandas_engine_returns_pandas_schema(self) -> None:
        schema = build_pandera_schema(
            _SIMPLE_SCHEMA_DICT, dtype_map=pandas_dtype_map, pandera_options=pandas_pandera_options, engine="pandas"
        )
        assert isinstance(schema, pa_pd.DataFrameSchema)

    def test_invalid_engine_raises(self) -> None:
        with pytest.raises(UnsupportedBackendError):
            build_pandera_schema(
                _SIMPLE_SCHEMA_DICT,
                dtype_map=polars_dtype_map,
                pandera_options=polars_pandera_options,
                engine=typing.cast(typing.Any, "duckdb"),
            )

    def test_truthy_default_propagated_to_column(self) -> None:
        """A truthy default value (e.g. 1) is stored on the schema column object."""
        schema = build_pandera_schema(
            {"val": {"dtype": int, "nullable": False, "default": 1, "required": True}},
            dtype_map=polars_dtype_map,
            pandera_options={"coerce": True},
            engine="polars",
        )
        assert schema.columns["val"].default == 1

    def test_zero_default_propagated_to_column(self) -> None:
        """default=0 is a real default (not the False sentinel) and must be stored."""
        schema = build_pandera_schema(
            {"val": {"dtype": int, "nullable": False, "default": 0, "required": True}},
            dtype_map=polars_dtype_map,
            pandera_options={"coerce": True},
            engine="polars",
        )
        assert schema.columns["val"].default == 0

    def test_columns_non_empty(self) -> None:
        schema = build_pandera_schema(
            _SIMPLE_SCHEMA_DICT, dtype_map=polars_dtype_map, pandera_options=polars_pandera_options, engine="polars"
        )
        assert len(schema.columns) == len(_SIMPLE_SCHEMA_DICT)


# -----------------------------------------------------------------------------
# prepare_for_validation
# -----------------------------------------------------------------------------


class TestPrepareForValidation:
    @pytest.fixture
    def schema(self) -> pa_pl.DataFrameSchema:
        return build_pandera_schema(
            _PREP_SCHEMA_DICT,
            dtype_map=polars_dtype_map,
            pandera_options={"coerce": True, "ordered": True},
            engine="polars",
        )

    def test_drops_extra_columns(self, schema: pa_pl.DataFrameSchema) -> None:
        df = pl.DataFrame({"a": [1], "b": ["x"], "c": [5], "extra": [99]})
        result = prepare_for_validation(df, schema)
        assert "extra" not in result.columns
        assert "a" in result.columns

    def test_column_order_matches_schema(self, schema: pa_pl.DataFrameSchema) -> None:
        df = pl.DataFrame({"c": [5], "a": [1], "b": ["x"]})
        result = prepare_for_validation(df, schema)
        present_schema_cols = [c for c in schema.columns if c in result.columns]
        assert list(result.columns) == present_schema_cols

    def test_fills_missing_required_column_with_truthy_default(self, schema: pa_pl.DataFrameSchema) -> None:
        """'c' has default=42, required=True and is absent — should be filled."""
        df = pl.DataFrame({"a": [1], "b": ["x"]})
        result = prepare_for_validation(df, schema)
        assert "c" in result.columns
        assert result["c"][0] == 42

    def test_fills_missing_required_column_with_zero_default(self, schema: pa_pl.DataFrameSchema) -> None:
        """'d' has default=0, required=True and is absent — zero is a real default, not a sentinel."""
        df = pl.DataFrame({"a": [1]})
        result = prepare_for_validation(df, schema)
        assert "d" in result.columns
        assert result["d"][0] == 0

    def test_does_not_fill_absent_optional_column(self, schema: pa_pl.DataFrameSchema) -> None:
        """'b' is required=False — absent optional columns are left absent."""
        df = pl.DataFrame({"a": [1]})
        result = prepare_for_validation(df, schema)
        assert "b" not in result.columns

    def test_nan_to_null_float64_to_int64(self, schema: pa_pl.DataFrameSchema) -> None:
        """Float64 columns the schema declares Int64 get NaN→null before coerce."""
        df = pl.DataFrame({"a": pl.Series([1.0, float("nan")], dtype=pl.Float64)})
        result = prepare_for_validation(df, schema)
        assert result["a"].null_count() == 1


# -----------------------------------------------------------------------------
# validate_dataframe
# -----------------------------------------------------------------------------


class TestValidateDataframe:
    @pytest.fixture
    def schema(self) -> pa_pl.DataFrameSchema:
        return build_pandera_schema(
            {
                "x": {"dtype": int, "nullable": False, "default": False, "required": True},
                "y": {"dtype": str, "nullable": True, "default": False, "required": False},
            },
            dtype_map=polars_dtype_map,
            pandera_options={"coerce": True, "ordered": True},
            engine="polars",
        )

    def test_returns_validated_dataframe(self, schema: pa_pl.DataFrameSchema) -> None:
        df = pl.DataFrame({"x": [1, 2], "extra": ["a", "b"]})
        result = validate_dataframe(df, schema)
        assert isinstance(result, pl.DataFrame)
        assert "x" in result.columns
        assert "extra" not in result.columns


class TestValidateDataFrame:
    """The fast path has to agree with pandera, which still raises every error."""

    @staticmethod
    def _schema():
        return pa_pl.DataFrameSchema(
            {"count": pa_pl.Column(pl.Int64, nullable=False), "rate": pa_pl.Column(pl.Float64, nullable=True)},
            coerce=True,
        )

    def test_coerces_a_valid_frame(self):
        frame = validate_dataframe(pl.DataFrame({"count": [1.0, 2.0], "rate": [None, 0.5]}), self._schema())
        assert frame.schema == {"count": pl.Int64, "rate": pl.Float64}

    def test_a_null_in_a_required_column_raises_pandera_error(self):
        with pytest.raises(pa_errors.SchemaError):
            validate_dataframe(pl.DataFrame({"count": [1, None], "rate": [0.1, 0.5]}), self._schema())

    def test_a_missing_required_column_still_raises(self):
        with pytest.raises(pl.exceptions.ColumnNotFoundError):
            validate_dataframe(pl.DataFrame({"rate": [0.1]}), self._schema())

    def test_a_value_that_cannot_be_cast_raises(self):
        with pytest.raises((pa_errors.SchemaError, pl.exceptions.PolarsError)):
            validate_dataframe(pl.DataFrame({"count": ["x"], "rate": [0.1]}), self._schema())

    def test_coerce_to_schema_matches_pandera_on_a_valid_frame(self):
        frame = pl.DataFrame({"count": [1.0, 2.0], "rate": [None, 0.5]})
        expected = self._schema().validate(frame)
        result = coerce_to_schema(frame, self._schema())
        assert result.equals(expected)
        assert result.schema == expected.schema

    def test_coerce_to_schema_leaves_a_missing_column_to_pandera(self):
        with pytest.raises(pl.exceptions.ColumnNotFoundError, match="count"):
            coerce_to_schema(pl.DataFrame({"rate": [0.1]}), self._schema())


ZONE_STARTS = ["ozs", "nzs", "dzs", "otf"]


@pytest.mark.parametrize(
    "schema_name, required",
    [
        ("oi_stats_pandera_polars", True),
        ("stats_pandera_polars", True),
        ("line_stats_pandera_polars", True),
        ("team_stats_pandera_polars", True),
        ("eh_oi_stats_pandera_polars", False),
        ("eh_stats_pandera_polars", True),
        ("eh_line_stats_pandera_polars", True),
        ("eh_team_stats_pandera_polars", True),
    ],
)
def test_zone_starts_required_where_always_counted(schema_name, required):
    """Every prep_* that counts zone starts requires them; evolving_hockey's prep_oi leaves them to prep_stats."""
    module = eh_schemas if schema_name.startswith("eh_") else chicken_schemas
    schema = getattr(module, schema_name)

    assert [schema.columns[c].required for c in ZONE_STARTS] == [required] * 4
