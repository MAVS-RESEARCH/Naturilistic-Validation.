from __future__ import annotations

import pyarrow as pa


def test_nullable_extended_real_columns_retain_zero_and_infinite_rows() -> None:
    """Use a non-Polaris fixture to prove Arrow retains zero and structural infinity."""

    schema = pa.schema(
        [
            ("case_id", pa.string()),
            ("value_kind", pa.string()),
            ("value", pa.int64()),
        ]
    )
    rows = [
        {"case_id": "synthetic-zero", "value_kind": "FINITE", "value": 0},
        {"case_id": "synthetic-infinite", "value_kind": "INFINITE", "value": None},
    ]
    restored = pa.Table.from_pylist(rows, schema=schema).to_pylist()
    assert restored == rows
    assert len(restored) == 2


def test_failure_allocation_fixture_retains_explicit_missing_cell_identity() -> None:
    expected = {"F000", "F100", "F010", "F001", "F110", "F101", "F011", "F111"}
    observed = expected - {"F111"}
    failure_card = {
        "case_id": "case:synthetic",
        "failure_type": "MISSING_FREEZE_CELLS",
        "missing_freeze_ids": sorted(expected - observed),
    }
    assert failure_card["missing_freeze_ids"] == ["F111"]
