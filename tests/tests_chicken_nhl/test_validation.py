import typing

import pandera.pandas as pa_pd
import pandera.polars as pa_pl
import polars as pl
import pytest

from chickenstats.chicken_nhl._validation_utils import _get_base_type_and_nullable, pydantic_to_pandera
from chickenstats.exceptions import UnsupportedBackendError
from chickenstats.chicken_nhl.validation_pandas import reorder_columns
from chickenstats.chicken_nhl.validation_polars import convert_pandas_pandera_to_polars, pydantic_to_native_polars
from chickenstats.chicken_nhl.validation_pydantic import APIEvent, ChangeEvent, PBPEvent

# ---------------------------------------------------------------------------
# _get_base_type_and_nullable
# ---------------------------------------------------------------------------


class TestGetBaseTypeAndNullable:
    # ------------------------------------------------------------------
    # String annotation path (lines 19–32 in _schema_utils.py)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Union / Optional types
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Typing.Optional (legacy form)
    # ------------------------------------------------------------------

    def test_typing_optional_float(self) -> None:
        base_type, is_nullable = _get_base_type_and_nullable(typing.Optional[float])  # noqa: UP045
        assert base_type is float
        assert is_nullable is True


# ---------------------------------------------------------------------------
# pydantic_to_pandera — pandas engine path (lines 78–88 in _schema_utils.py)
# ---------------------------------------------------------------------------


class TestPydanticToPandera:
    def test_polars_engine_returns_polars_schema(self) -> None:
        schema = pydantic_to_pandera(PBPEvent, engine="polars")
        assert isinstance(schema, pa_pl.DataFrameSchema)

    def test_pandas_engine_returns_pandas_schema(self) -> None:
        schema = pydantic_to_pandera(PBPEvent, engine="pandas")
        assert isinstance(schema, pa_pd.DataFrameSchema)

    def test_pandas_engine_columns_non_empty(self) -> None:
        schema = pydantic_to_pandera(PBPEvent, engine="pandas")
        assert len(schema.columns) > 0

    def test_invalid_engine_raises(self) -> None:
        with pytest.raises(UnsupportedBackendError):
            pydantic_to_pandera(PBPEvent, engine="duckdb")  # type: ignore[arg-type, ty:invalid-argument-type]

    def test_pandas_engine_api_event(self) -> None:
        schema = pydantic_to_pandera(APIEvent, engine="pandas")
        assert isinstance(schema, pa_pd.DataFrameSchema)
        assert len(schema.columns) > 0


# ---------------------------------------------------------------------------
# pydantic_to_native_polars
# ---------------------------------------------------------------------------


class TestPydanticToNativePolars:
    def test_returns_dict(self) -> None:
        schema = pydantic_to_native_polars(PBPEvent)
        assert isinstance(schema, dict)

    def test_all_values_are_polars_dtypes(self) -> None:
        schema = pydantic_to_native_polars(PBPEvent)
        for dtype in schema.values():
            assert isinstance(dtype, type | pl.DataType)


# ---------------------------------------------------------------------------
# convert_pandas_pandera_to_polars (lines 73–136 in validation_polars.py)
# ---------------------------------------------------------------------------


class TestConvertPandasPanderaToPolars:
    @pytest.fixture
    def simple_pandas_schema(self):
        return pa_pd.DataFrameSchema(
            {
                "game_id": pa_pd.Column(pa_pd.Int64, nullable=False),
                "player_name": pa_pd.Column(pa_pd.String, nullable=True),
                "toi": pa_pd.Column(pa_pd.Float64, nullable=True),
                "is_home": pa_pd.Column(pa_pd.Bool, nullable=False),
            },
            coerce=True,
        )

    def test_pandera_output_returns_polars_schema(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="pandera")
        assert isinstance(result, pa_pl.DataFrameSchema)

    def test_pandera_output_column_count(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="pandera")
        assert len(result.columns) == 4  # type: ignore[arg-type, ty:unresolved-attribute]

    def test_native_output_returns_dict(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="native")
        assert isinstance(result, dict)

    def test_native_output_column_count(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="native")
        assert len(result) == 4  # type: ignore[arg-type, ty:invalid-argument-type]

    def test_native_output_int_dtype(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="native")
        assert result["game_id"] == pl.Int64  # ty: ignore[not-subscriptable]

    def test_native_output_string_dtype(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="native")
        assert result["player_name"] == pl.String  # ty: ignore[not-subscriptable]

    def test_native_output_float_dtype(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="native")
        assert result["toi"] == pl.Float64  # ty: ignore[not-subscriptable]

    def test_native_output_bool_dtype(self, simple_pandas_schema) -> None:
        result = convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="native")
        assert result["is_home"] == pl.Boolean  # ty: ignore[not-subscriptable]

    def test_invalid_output_format_raises(self, simple_pandas_schema) -> None:
        with pytest.raises(UnsupportedBackendError):
            convert_pandas_pandera_to_polars(simple_pandas_schema, output_format="arrow")  # type: ignore[arg-type, ty:invalid-argument-type]

    def test_int8_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column("Int8")})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Int8  # ty: ignore[not-subscriptable]

    def test_int16_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column("Int16")})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Int16  # ty: ignore[not-subscriptable]

    def test_int32_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column("Int32")})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Int32  # ty: ignore[not-subscriptable]

    def test_float32_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column("Float32")})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Float32  # ty: ignore[not-subscriptable]

    def test_datetime_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column(pa_pd.DateTime)})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Datetime  # ty: ignore[not-subscriptable]

    def test_unknown_dtype_falls_back_to_string(self) -> None:
        # object dtype maps to String fallback
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column(object, nullable=True)})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.String  # ty: ignore[not-subscriptable]

    def test_date_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column(pa_pd.Date)})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Date  # ty: ignore[not-subscriptable]

    def test_timedelta_dtype_mapping(self) -> None:
        schema = pa_pd.DataFrameSchema({"col": pa_pd.Column(pa_pd.Timedelta)})
        result = convert_pandas_pandera_to_polars(schema, output_format="native")
        assert result["col"] == pl.Duration  # ty: ignore[not-subscriptable]


# ---------------------------------------------------------------------------
# _get_base_type_and_nullable — string annotation, non-list branch (arc 50->53)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# reorder_columns — explicit ordered_columns arg (branch 344->347)
# ---------------------------------------------------------------------------


class TestReorderColumns:
    def test_default_ordered_columns(self) -> None:
        """Without explicit ordered_columns, column_order is used."""
        cols = {"season": pa_pd.Column(pa_pd.String), "game_id": pa_pd.Column(pa_pd.Int64)}
        result = reorder_columns(cols)
        assert isinstance(result, dict)

    def test_explicit_ordered_columns(self) -> None:
        """Passing ordered_columns reorders to that explicit list."""
        cols = {"a": pa_pd.Column(pa_pd.String), "b": pa_pd.Column(pa_pd.Int64), "c": pa_pd.Column(pa_pd.Float64)}
        result = reorder_columns(cols, ordered_columns=["c", "a"])
        assert list(result.keys()) == ["c", "a"]

    def test_explicit_ordered_columns_skips_absent(self) -> None:
        """Keys in ordered_columns that don't exist in pandera_columns are skipped."""
        cols = {"a": pa_pd.Column(pa_pd.String)}
        result = reorder_columns(cols, ordered_columns=["a", "z"])
        assert list(result.keys()) == ["a"]


# ---------------------------------------------------------------------------
# ChangeEvent / PBPEvent fix_lists — non-dict branch (lines 162 / 485)
# ---------------------------------------------------------------------------


class TestFixListsNonDict:
    def test_change_event_non_dict_passthrough(self) -> None:
        """fix_lists returns non-dict input unchanged, triggering ValidationError downstream."""
        with pytest.raises(Exception):
            ChangeEvent.model_validate("not_a_dict")

    def test_pbp_event_non_dict_passthrough(self) -> None:
        """fix_lists returns non-dict input unchanged, triggering ValidationError downstream."""
        with pytest.raises(Exception):
            PBPEvent.model_validate("not_a_dict")
