#!/usr/bin/env python3
"""Validate, hash, and seal the authoritative Phase-2 contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.contract import validate_contract, validate_semantic_facts  # noqa: E402
from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import byte_hash, canonical_json_hash, write_json_atomic  # noqa: E402
from scripts.phase1_validate import verify_self_hash  # noqa: E402
from scripts.phase2_validate_contract import read_json, validate_schema  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    contract_root = run_root / "contract"
    # console.log: external.phase2.seal.start
    console.log("external.phase2.seal.start", run_id=args.run_id)
    required = [
        "semantic_facts.jsonl",
        "history_universe.json",
        "extensional_contract.json",
        "completion_set.json",
        "contract_provenance.json",
        "touch_records.parquet",
        "touch_summary.json",
        "route_classification.json",
        "fidelity_report.json",
    ]
    if any(not (contract_root / name).is_file() for name in required):
        raise RuntimeError("required Phase-2 artifact is missing")

    # console.log: external.phase2.seal.validate_contract_touch_fidelity
    console.log("external.phase2.seal.validate_contract_touch_fidelity", run_id=args.run_id)
    contract = read_json(contract_root / "extensional_contract.json")
    completions = read_json(contract_root / "completion_set.json")
    history = read_json(contract_root / "history_universe.json")
    provenance = read_json(contract_root / "contract_provenance.json")
    touch = read_json(contract_root / "touch_summary.json")
    fidelity = read_json(contract_root / "fidelity_report.json")
    route = read_json(contract_root / "route_classification.json")
    manifest = read_json(root / "external_source" / "source_manifest.json")
    facts = [
        json.loads(line)
        for line in (contract_root / "semantic_facts.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    for fact in facts:
        validate_schema(root, fact, "semantic_fact.schema.json")
    validate_semantic_facts(root, manifest, facts)
    validate_contract(contract)
    validate_schema(root, contract, "extensional_contract.schema.json")
    validate_schema(root, completions, "completion_set.schema.json")
    verify_self_hash(history, "history_universe_hash")
    verify_self_hash(completions, "completion_set_hash")
    verify_self_hash(provenance, "provenance_hash")
    verify_self_hash(touch, "touch_summary_hash")
    verify_self_hash(fidelity, "fidelity_report_hash")
    verify_self_hash(route, "route_classification_hash")
    parquet = pq.read_table(contract_root / "touch_records.parquet")
    if (
        parquet.num_rows != touch["touch_record_count"]
        or parquet.column_names != touch["column_inventory"]
    ):
        raise RuntimeError("Parquet row count or column inventory mismatch")
    if {field.name: str(field.type) for field in parquet.schema} != touch["column_types"]:
        raise RuntimeError("Parquet column types do not match the declared schema")
    reconstructed_records = []
    for row in parquet.to_pylist():
        reconstructed_records.append(
            {
                "touch_record_id": row["touch_record_id"],
                "completion_id": row["completion_id"],
                "state_id": row["state_id"],
                "action_id": row["action_id"],
                "successor_ids": json.loads(row["successor_ids_json"]),
                "touches": {"E": row["touch_E"], "R": row["touch_R"], "A": row["touch_A"]},
                "witnesses": json.loads(row["witnesses_json"]),
                "provenance_hash": row["provenance_hash"],
            }
        )
    if canonical_json_hash(reconstructed_records) != touch["records_hash"]:
        raise RuntimeError("Parquet content does not match canonical touch records")
    if not touch["exactly_one_record_per_pair"] or touch["coverage_percent"] != 100.0:
        raise RuntimeError("touch completeness gate failed")
    if not fidelity["all_completions_valid"] or fidelity["fidelity_percent"] != 100.0:
        raise RuntimeError("native fidelity gate failed")
    if completions["status"] not in {"IDENTIFIED", "PARTIALLY_IDENTIFIED"}:
        raise RuntimeError("completion status does not authorize Phase 3")
    if len(contract["S"]) > 500:
        raise RuntimeError("contract exceeds the Phase-2 state tractability preference")
    if not route["classified_before_freeze_results"]:
        raise RuntimeError("route classification was not frozen before results")

    # console.log: external.phase2.seal.hash_artifact_graph
    console.log("external.phase2.seal.hash_artifact_graph", run_id=args.run_id)
    artifact_hashes = {name: byte_hash(contract_root / name) for name in sorted(required)}
    seal_value = {
        "run_id": args.run_id,
        "phase": 2,
        "status": completions["status"],
        "phase3_authorized": True,
        "contract_hash": contract["contract_hash"],
        "completion_set_hash": completions["completion_set_hash"],
        "touch_summary_hash": touch["touch_summary_hash"],
        "fidelity_report_hash": fidelity["fidelity_report_hash"],
        "route_classification_hash": route["route_classification_hash"],
        "artifact_hashes": artifact_hashes,
        "state_count": len(contract["S"]),
        "history_count": len(contract["U_H"]),
        "completion_count": completions["completion_count"],
        "reachable_state_action_pairs": touch["reachable_state_action_pairs"],
        "touch_record_count": touch["touch_record_count"],
        "fidelity_percent": fidelity["fidelity_percent"],
    }
    seal = {**seal_value, "contract_seal_hash": canonical_json_hash(seal_value)}
    write_json_atomic(contract_root / "CONTRACT_SEALED", seal)
    run_manifest = read_json(run_root / "manifests" / "run_manifest.json")
    run_manifest.update(
        {
            "phase": 2,
            "status": completions["status"],
            "phase2_authorized": True,
            "phase3_authorized": True,
            "contract_hash": contract["contract_hash"],
            "contract_seal_hash": seal["contract_seal_hash"],
        }
    )
    run_manifest.pop("run_manifest_hash", None)
    run_manifest["run_manifest_hash"] = canonical_json_hash(run_manifest)
    write_json_atomic(run_root / "manifests" / "run_manifest.json", run_manifest)

    # console.log: external.phase2.seal.complete
    console.log(
        "external.phase2.seal.complete",
        run_id=args.run_id,
        status=seal["status"],
        contract_seal_hash=seal["contract_seal_hash"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
