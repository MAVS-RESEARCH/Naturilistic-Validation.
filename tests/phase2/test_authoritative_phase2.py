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
        not RUN_ID or PHASE not in {"2", "3"},
        reason="PC_RUN_ID and PC_PHASE=2 or 3 are required for authoritative checks",
    ),
]


def contract_root() -> Path:
    if not RUN_ID:
        pytest.skip("PC_RUN_ID is required")
    return ROOT / "results" / "external_validation_v01" / RUN_ID / "contract"


def load(name: str) -> dict:
    return json.loads((contract_root() / name).read_text(encoding="utf-8"))


def test_authoritative_phase2_identified_and_sealed() -> None:
    seal = load("CONTRACT_SEALED")
    completion = load("completion_set.json")
    assert seal["status"] == "IDENTIFIED"
    assert seal["phase3_authorized"] is True
    assert completion["completion_count"] == 1
    assert completion["sampled"] is False
    payload = {key: value for key, value in seal.items() if key != "contract_seal_hash"}
    assert seal["contract_seal_hash"] == canonical_json_hash(payload)
    for name, expected in seal["artifact_hashes"].items():
        assert byte_hash(contract_root() / name) == expected


def test_authoritative_touch_and_fidelity_are_complete() -> None:
    touch = load("touch_summary.json")
    fidelity = load("fidelity_report.json")
    route = load("route_classification.json")
    table = pq.read_table(contract_root() / "touch_records.parquet")
    assert touch["coverage_percent"] == 100.0
    assert touch["exactly_one_record_per_pair"] is True
    assert touch["touch_pattern_counts"] == {"E0_R1_A0": 1}
    assert table.num_rows == touch["touch_record_count"] == 1
    assert {field.name: str(field.type) for field in table.schema} == touch["column_types"]
    assert fidelity["fidelity_percent"] == 100.0
    assert fidelity["passed_pairs"] == fidelity["case_completion_pairs"] == 8
    assert route["classification_counts"] == {"SINGLE_ACTION": 8}


def test_authoritative_contract_has_complete_lineage_and_no_hidden_truth() -> None:
    contract = load("extensional_contract.json")
    provenance = load("contract_provenance.json")
    facts = [
        json.loads(line)
        for line in (contract_root() / "semantic_facts.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert provenance["all_normative_components_have_lineage"] is True
    assert provenance["fact_count"] == len(facts) == 18
    assert all(
        not state["controller_observation"]["contains_evaluator_truth"]
        for state in contract["states"]
    )
    assert not any(
        key in action
        for action in contract["Q"]
        for key in ("touch", "touches", "touch_mask", "resource_touch")
    )
