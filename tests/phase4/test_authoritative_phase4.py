from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from pc_external.hashing import byte_hash, canonical_json_hash
from pc_external_audit.claims_audit import validate_claim_ledger
from scripts.phase4_generate_claims import verify_final_seal
from scripts.phase4_independent_audit import build_audit, public_core

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = os.environ.get("PC_RUN_ID")
PHASE = os.environ.get("PC_PHASE")

pytestmark = [
    pytest.mark.authoritative,
    pytest.mark.skipif(
        not RUN_ID or PHASE != "4",
        reason="PC_RUN_ID and PC_PHASE=4 are required for authoritative Phase-4 checks",
    ),
]


def run_root() -> Path:
    assert RUN_ID
    return ROOT / "results" / "external_validation_v01" / RUN_ID


def load(path: str) -> dict:
    return json.loads((run_root() / path).read_text(encoding="utf-8"))


def test_final_audit_and_seal_bind_every_phase4_gate() -> None:
    seal = verify_final_seal(ROOT, run_root())
    audit = load("audit/audit.json")
    assert audit["overall_pass"]
    assert audit["final_verdict"] == "PASS — POSITIVE EXTERNAL"
    assert audit["supported_claim_findings"] == 0
    assert not audit["findings"]
    for name, gate in audit.items():
        if name.endswith("_audit"):
            assert gate["passed"], name
            assert gate["checked"] == gate["matched"], name
    assert seal["all_twenty_clauses_passed"]
    assert seal["artifact_count"] == len(seal["artifact_hashes"])
    for relative, expected in seal["artifact_hashes"].items():
        assert byte_hash(ROOT / relative) == expected
    payload = {key: value for key, value in seal.items() if key != "seal_hash"}
    assert seal["seal_hash"] == canonical_json_hash(payload)


def test_live_independent_recomputation_matches_every_scientific_row() -> None:
    assert RUN_ID
    live = build_audit(ROOT, RUN_ID)
    assert public_core(live) == load("audit/independent_audit.json")
    assert live["touch"]["checked"] == live["touch"]["matched"] == 1
    assert live["planner"]["checked"] == live["planner"]["matched"] == 64
    assert live["aggregation"]["checked"] == live["aggregation"]["matched"] == 8
    assert live["controls"]["checked"] == live["controls"]["matched"] == 10
    assert pq.read_table(run_root() / "audit" / "independent_touch.parquet").num_rows == 1
    independent = pq.read_table(run_root() / "audit" / "independent_results.parquet").to_pylist()
    assert len(independent) == 8
    assert {row["delta_R_relation"] for row in independent} == {"STRUCTURAL_POSITIVE"}


def test_all_attacks_claim_locks_clauses_and_graph_are_complete() -> None:
    corruptions = load("audit/corruption_report.json")
    assert corruptions["attack_count"] == corruptions["detected_count"] == 12
    assert len({row["attack_id"] for row in corruptions["attacks"]}) == 12
    assert all(row["detected"] for row in corruptions["attacks"])
    clauses = load("audit/clause_audit.json")
    assert clauses["check_count"] == clauses["passed_count"] == 20
    assert clauses["all_passed"] and all(row["passed"] for row in clauses["checks"])
    graph = load("audit/artifact_graph.json")
    assert not graph["unindexed_scientific_files"]
    assert graph["scientific_file_count"] == graph["indexed_scientific_file_count"]
    assert graph["backward_traversal_passed"] and graph["forward_traversal_passed"]
    assert graph["paper_value_count"] == 8
    ledger = load("reports/claim_ledger.json")
    assert not validate_claim_ledger(ledger)
    assert ledger["external_operational_validation"]
    assert ledger["result_sign"] == "POSITIVE"
    assert all(value is False for value in ledger["locked_flags"].values())
    assert "SINGLE_ACTION" in (run_root() / "reports" / "external_case_report.md").read_text()


def test_sealed_run_refuses_cleaner() -> None:
    assert RUN_ID
    process = subprocess.run(
        [
            str(ROOT / ".venv" / "Scripts" / "python.exe"),
            str(ROOT / "scripts" / "clean_named_run.py"),
            "--run-id",
            RUN_ID,
            "--repo-root",
            str(ROOT),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode != 0
    assert "sealed" in (process.stdout + process.stderr).lower()
