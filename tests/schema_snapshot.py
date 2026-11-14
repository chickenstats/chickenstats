"""Compare an output frame with its entry in tests/data/schema_snapshot.json."""

import json
from pathlib import Path

import polars as pl

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "schema_snapshot.json"
SNAPSHOT: dict[str, list[tuple[str, str, bool]]] = {
    key: [(name, dtype, nullable) for name, dtype, nullable in rows]
    for key, rows in json.loads(SNAPSHOT_PATH.read_text()).items()
}


def assert_matches_snapshot(df: pl.DataFrame, key: str, *, every_column: bool = False) -> None:
    """Raise unless df's columns come in the snapshot's order with its dtypes, and its non-nullable columns have no nulls.

    A frame returns only the columns its options ask for, so by default df may leave some out;
    every_column=True also requires all of them.
    """
    snapshot = SNAPSHOT[key]
    declared = [name for name, _, _ in snapshot]

    unknown = [name for name in df.columns if name not in declared]
    assert not unknown, f"{key}: columns not in the snapshot: {unknown}"
    assert df.columns == [name for name in declared if name in df.columns], f"{key}: columns out of order"
    if every_column:
        assert df.columns == declared, f"{key}: missing columns {[n for n in declared if n not in df.columns]}"

    dtypes = {name: dtype for name, dtype, _ in snapshot}
    changed = {name: (dtypes[name], str(dtype)) for name, dtype in df.schema.items() if str(dtype) != dtypes[name]}
    assert not changed, f"{key}: dtypes differ from the snapshot (snapshot, output): {changed}"

    never_null = [name for name, _, nullable in snapshot if not nullable and name in df.columns]
    nulls = {name: count for name, count in df.select(never_null).null_count().row(0, named=True).items() if count}
    assert not nulls, f"{key}: null values in columns the snapshot says are never null: {nulls}"
