#!/usr/bin/env python3
"""Derive complete E/R/A touch records and write deterministic Parquet."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import (  # noqa: E402
    canonical_json_bytes,
    canonical_json_hash,
    write_json_atomic,
)
from pc_external.touch import derive_all_touch_records  # noqa: E402
from scripts.phase2_validate_contract import read_json, validate_schema  # noqa: E402

PARQUET_COLUMNS = [
    "touch_record_id",
    "completion_id",
    "state_id",
    "action_id",
    "successor_ids_json",
    "touch_E",
    "touch_R",
    "touch_A",
    "witnesses_json",
    "provenance_hash",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    contract_root = root / "results" / "external_validation_v01" / args.run_id / "contract"
    # console.log: external.phase2.extract_touch.start
    console.log("external.phase2.extract_touch.start", run_id=args.run_id)
    contract = read_json(contract_root / "extensional_contract.json")

    # console.log: external.phase2.extract_touch.derive_successor_union
    console.log("external.phase2.extract_touch.derive_successor_union", run_id=args.run_id)
    records = derive_all_touch_records(contract)
    for record in records:
        validate_schema(root, record, "touch_record.schema.json")

    # console.log: external.phase2.extract_touch.write_parquet
    console.log("external.phase2.extract_touch.write_parquet", run_id=args.run_id)
    rows = [
        {
            "touch_record_id": item["touch_record_id"],
            "completion_id": item["completion_id"],
            "state_id": item["state_id"],
            "action_id": item["action_id"],
            "successor_ids_json": canonical_json_bytes(item["successor_ids"]).decode(),
            "touch_E": item["touches"]["E"],
            "touch_R": item["touches"]["R"],
            "touch_A": item["touches"]["A"],
            "witnesses_json": canonical_json_bytes(item["witnesses"]).decode(),
            "provenance_hash": item["provenance_hash"],
        }
        for item in records
    ]
    schema = pa.schema(
        [
            ("touch_record_id", pa.string()),
            ("completion_id", pa.string()),
            ("state_id", pa.string()),
            ("action_id", pa.string()),
            ("successor_ids_json", pa.string()),
            ("touch_E", pa.bool_()),
            ("touch_R", pa.bool_()),
            ("touch_A", pa.bool_()),
            ("witnesses_json", pa.string()),
            ("provenance_hash", pa.string()),
        ],
        metadata={b"pc_schema": b"touch_record_v1"},
    )
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(
        table,
        contract_root / "touch_records.parquet",
        compression="NONE",
        version="2.6",
        write_statistics=True,
    )
    expected_pairs = len(contract["Q"])
    summary = {
        "run_id": args.run_id,
        "completion_count": 1,
        "reachable_state_action_pairs": expected_pairs,
        "touch_record_count": len(records),
        "coverage_percent": 100.0 if len(records) == expected_pairs else 0.0,
        "exactly_one_record_per_pair": len(records) == expected_pairs,
        "column_inventory": PARQUET_COLUMNS,
        "column_types": {field.name: str(field.type) for field in schema},
        "touch_pattern_counts": {
            "E0_R1_A0": sum(
                not item["touches"]["E"] and item["touches"]["R"] and not item["touches"]["A"]
                for item in records
            )
        },
        "records_hash": canonical_json_hash(records),
    }
    summary["touch_summary_hash"] = canonical_json_hash(summary)
    if not summary["exactly_one_record_per_pair"]:
        raise RuntimeError("touch coverage is incomplete")
    write_json_atomic(contract_root / "touch_summary.json", summary)

    # console.log: external.phase2.extract_touch.complete
    console.log(
        "external.phase2.extract_touch.complete",
        run_id=args.run_id,
        touch_records=len(records),
        coverage_percent=summary["coverage_percent"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
