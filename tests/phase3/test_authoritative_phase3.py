from __future__ import annotations

import json
import os
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from pc_external.hashing import byte_hash, canonical_json_hash

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = os.environ.get("PC_RUN_ID")
PHASE = os.environ.get("PC_PHASE")

pytestmark = [
    pytest.mark.authoritative,
    pytest.mark.skipif(
        not RUN_ID or PHASE not in {"3", "4"},
        reason="PC_RUN_ID and PC_PHASE=3 or 4 are required for authoritative checks",
    ),
]


def run_root() -> Path:
    assert RUN_ID
    return ROOT / "results" / "external_validation_v01" / RUN_ID


def load(path: str) -> dict:
    return json.loads((run_root() / path).read_text(encoding="utf-8"))


def load_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (run_root() / path).read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_phase3_is_measured_hash_bound_and_complete() -> None:
    completion = load("PHASE3_COMPLETE")
    payload = {key: value for key, value in completion.items() if key != "phase3_completion_hash"}
    assert completion["phase3_completion_hash"] == canonical_json_hash(payload)
    assert completion["status"] == "MEASURED"
    assert completion["phase4_authorized"] is True
    assert completion["raw_result_count"] == 64
    assert completion["case_result_count"] == completion["identified_set_count"] == 8
    assert completion["control_pass_count"] == 10
    assert completion["failure_card_count"] == 0
    for name, expected in completion["artifact_hashes"].items():
        assert byte_hash(run_root() / name) == expected


def test_all_freezes_infinities_and_structural_classifications_are_retained() -> None:
    results = load_jsonl("raw/freeze_results.jsonl")
    assert len(results) == len({row["result_id"] for row in results}) == 64
    assert {row["freeze_id"] for row in results} == {
        "F000",
        "F100",
        "F010",
        "F001",
        "F110",
        "F101",
        "F011",
        "F111",
    }
    assert sum(row["value"]["kind"] == "FINITE" for row in results) == 32
    assert sum(row["value"]["kind"] == "INFINITE" for row in results) == 32
    assert all("value" not in row["value"] for row in results if row["value"]["kind"] == "INFINITE")
    case_table = pq.read_table(run_root() / "processed" / "case_results.parquet")
    rows = case_table.to_pylist()
    assert len(rows) == 8
    assert {row["result_class"] for row in rows} == {"STRUCTURAL_R"}
    assert {row["delta_R_relation"] for row in rows} == {"STRUCTURAL_POSITIVE"}
    assert {row["route_class"] for row in rows} == {"SINGLE_ACTION"}
    assert all(row["audit_eligible"] for row in rows)


def test_same_instance_exact_masks_crosscheck_and_controls_pass() -> None:
    report = load("reports/phase3_validation.json")
    crosscheck = load("raw/planner_crosscheck.json")
    controls = load_jsonl("controls/control_results.jsonl")
    assert report["all_scientific_gates_passed"] is True
    assert report["results_hygiene_passed"] is True
    assert report["same_instance_passed"] is True
    assert report["exact_action_masks_passed"] is True
    assert report["observed_allocations"] == report["expected_allocations"] == 64
    assert report["finite_result_rows_retained"] == report["infinite_result_rows_retained"] == 32
    assert crosscheck["checked_results"] == crosscheck["passed_results"] == 64
    assert crosscheck["all_passed"] is True
    assert len(controls) == 10
    assert all(row["passed"] for row in controls)


def test_parquet_shapes_and_full_lattice_columns_are_explicit() -> None:
    report = load("reports/phase3_validation.json")
    assert report["parquet"]["freeze_policy_traces"]["rows"] == 128
    assert report["parquet"]["freeze_lattice"]["rows"] == 64
    assert report["parquet"]["case_results"]["rows"] == 8
    assert report["parquet"]["identified_sets"]["rows"] == 8
    columns = report["parquet"]["case_results"]["columns"]
    for freeze_id in ("F000", "F100", "F010", "F001", "F110", "F101", "F011", "F111"):
        assert f"K_{freeze_id}_kind" in columns
        assert f"K_{freeze_id}_value" in columns
        assert f"{freeze_id}_result_id" in columns
