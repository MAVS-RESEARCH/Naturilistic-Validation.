#!/usr/bin/env python3
"""Execute all sealed Phase-3 case/completion/cost/freeze allocations exactly."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import yaml


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.freeze import (  # noqa: E402
    condition_manifest,
    derive_action_mask,
    exact_freeze_lattice,
    freeze_result_id,
    scientific_instance,
)
from pc_external.hashing import (  # noqa: E402
    byte_hash,
    canonical_json_hash,
    write_json_atomic,
    write_jsonl_atomic,
)
from pc_external.planner import exact_minimax_plan, exhaustive_policy_optimum  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_contract_seal(contract_root: Path) -> dict[str, Any]:
    seal = read_json(contract_root / "CONTRACT_SEALED")
    payload = {key: value for key, value in seal.items() if key != "contract_seal_hash"}
    if canonical_json_hash(payload) != seal["contract_seal_hash"]:
        raise RuntimeError("Phase-2 contract seal self-hash mismatch")
    if not seal.get("phase3_authorized") or seal["status"] not in {
        "IDENTIFIED",
        "PARTIALLY_IDENTIFIED",
    }:
        raise RuntimeError("sealed contract does not authorize Phase 3")
    for name, expected in seal["artifact_hashes"].items():
        if byte_hash(contract_root / name) != expected:
            raise RuntimeError(f"sealed Phase-2 artifact mutated: {name}")
    return seal


def touch_map(contract_root: Path) -> dict[str, dict[str, bool]]:
    table = pq.read_table(contract_root / "touch_records.parquet")
    result: dict[str, dict[str, bool]] = {}
    for row in table.to_pylist():
        action_id = row["action_id"]
        touches = {"E": row["touch_E"], "R": row["touch_R"], "A": row["touch_A"]}
        if action_id in result and result[action_id] != touches:
            raise RuntimeError(
                f"completion-dependent touch is unsupported in this contract: {action_id}"
            )
        result[action_id] = touches
    return result


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    contract_root = run_root / "contract"
    raw_root = run_root / "raw"
    processed_root = run_root / "processed"
    controls_root = run_root / "controls"

    # console.log: external.phase3.run_freezes.start
    console.log("external.phase3.run_freezes.start", run_id=args.run_id)

    # console.log: external.phase3.run_freezes.inventory_prior_results
    console.log("external.phase3.run_freezes.inventory_prior_results", run_id=args.run_id)
    phase3_paths = [raw_root, processed_root, controls_root]
    prior_files = sorted(
        path.relative_to(run_root).as_posix()
        for directory in phase3_paths
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file()
    )
    if prior_files:
        raise RuntimeError("Phase-3 namespace is not clean; run the named-run cleaner first")
    inventory_value = {
        "run_id": args.run_id,
        "inspected_namespaces": [path.relative_to(run_root).as_posix() for path in phase3_paths],
        "prior_phase3_file_count": 0,
        "prior_phase3_files": [],
        "clean_start": True,
    }
    inventory_value["inventory_hash"] = canonical_json_hash(inventory_value)
    write_json_atomic(run_root / "manifests" / "phase3_pre_run_inventory.json", inventory_value)

    # console.log: external.phase3.run_freezes.verify_sealed_contract
    console.log("external.phase3.run_freezes.verify_sealed_contract", run_id=args.run_id)
    seal = verify_contract_seal(contract_root)
    contract = read_json(contract_root / "extensional_contract.json")
    completion_set = read_json(contract_root / "completion_set.json")
    if contract["contract_hash"] != seal["contract_hash"]:
        raise RuntimeError("contract is not bound to CONTRACT_SEALED")
    touches = touch_map(contract_root)
    experiment = yaml.safe_load((root / "configs" / "experiment.yaml").read_text(encoding="utf-8"))
    lattice = exact_freeze_lattice(experiment["freeze_sets"])
    cost_contracts = [{"cost_contract_id": "unit_intervention_cost", "cost_key": "unit"}]
    if contract["c"]["native_secondary"]:
        raise RuntimeError("native secondary costs require an explicit source-grounded adapter")

    # console.log: external.phase3.run_freezes.allocate_lattice
    console.log(
        "external.phase3.run_freezes.allocate_lattice",
        run_id=args.run_id,
        cases=len(contract["Terminal"]),
        completions=completion_set["completion_count"],
        freezes=len(lattice),
        cost_contracts=len(cost_contracts),
    )
    manifests: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    crosschecks: list[dict[str, Any]] = []
    for completion in sorted(completion_set["completions"], key=lambda item: item["completion_id"]):
        if completion["contract_hash"] != contract["contract_hash"]:
            raise RuntimeError("completion contract hash differs from sealed contract")
        for case_id in sorted(contract["Terminal"]):
            terminal_states = sorted(
                state["state_id"]
                for state in contract["states"]
                if state["terminal_certificates"][case_id]
            )
            for cost_contract in cost_contracts:
                instance = scientific_instance(contract, case_id, cost_contract["cost_contract_id"])
                for freeze in lattice:
                    mask = derive_action_mask(contract["Q"], touches, freeze["forbidden_resources"])
                    manifest = condition_manifest(
                        run_id=args.run_id,
                        instance=instance,
                        freeze_id=freeze["freeze_id"],
                        forbidden_resources=freeze["forbidden_resources"],
                        action_mask=mask,
                        contract_seal_hash=seal["contract_seal_hash"],
                    )
                    identity = {
                        "case_id": case_id,
                        "completion_id": completion["completion_id"],
                        "cost_contract_id": cost_contract["cost_contract_id"],
                        "freeze_id": freeze["freeze_id"],
                    }
                    result_id = freeze_result_id(identity)
                    solved = exact_minimax_plan(
                        states=contract["S"],
                        actions=contract["Q"],
                        initial_state=contract["s0"],
                        terminal_states=terminal_states,
                        allowed_action_ids=mask["retained_action_ids"],
                        cost_key=cost_contract["cost_key"],
                    )
                    alternate = exhaustive_policy_optimum(
                        states=contract["S"],
                        actions=contract["Q"],
                        initial_state=contract["s0"],
                        terminal_states=terminal_states,
                        allowed_action_ids=mask["retained_action_ids"],
                        cost_key=cost_contract["cost_key"],
                    )
                    exact_match = (
                        solved["value"] == alternate["value"]
                        and solved["optimal_action_ids"] == alternate["optimal_action_ids"]
                    )
                    if not exact_match:
                        raise RuntimeError(f"alternate exact planner mismatch: {result_id}")
                    certificate = {
                        "result_id": result_id,
                        "case_id": case_id,
                        "completion_id": completion["completion_id"],
                        "freeze_id": freeze["freeze_id"],
                        "condition_manifest_hash": manifest["condition_manifest_hash"],
                        **solved["certificate"],
                    }
                    certificate_payload = {
                        key: value
                        for key, value in certificate.items()
                        if key != "certificate_hash"
                    }
                    certificate["certificate_hash"] = canonical_json_hash(certificate_payload)
                    result = {
                        "result_id": result_id,
                        "run_id": args.run_id,
                        **identity,
                        "forbidden_resources": freeze["forbidden_resources"],
                        "retained_action_ids": mask["retained_action_ids"],
                        "blocked_action_ids": mask["blocked_action_ids"],
                        "action_mask_hash": mask["action_mask_hash"],
                        "condition_manifest_hash": manifest["condition_manifest_hash"],
                        "contract_hash": contract["contract_hash"],
                        "contract_seal_hash": seal["contract_seal_hash"],
                        "value": solved["value"],
                        "optimal_action_ids": solved["optimal_action_ids"],
                        "certificate_hash": certificate["certificate_hash"],
                        "planner_algorithm": "EXACT_AND_OR_MINIMAX",
                    }
                    manifests.append(manifest)
                    results.append(result)
                    crosschecks.append(
                        {
                            "result_id": result_id,
                            "production_value": solved["value"],
                            "alternate_value": alternate["value"],
                            "production_actions": solved["optimal_action_ids"],
                            "alternate_actions": alternate["optimal_action_ids"],
                            "policies_enumerated": alternate["policies_enumerated"],
                            "passed": exact_match,
                        }
                    )
                    for state_id, state_value in certificate["state_values"].items():
                        trace_rows.append(
                            {
                                "result_id": result_id,
                                "case_id": case_id,
                                "completion_id": completion["completion_id"],
                                "cost_contract_id": cost_contract["cost_contract_id"],
                                "freeze_id": freeze["freeze_id"],
                                "state_id": state_id,
                                "value_kind": state_value["kind"],
                                "value": state_value.get("value"),
                                "optimal_action_ids_json": json.dumps(
                                    certificate["optimal_actions_by_state"][state_id],
                                    separators=(",", ":"),
                                ),
                                "certificate_hash": certificate["certificate_hash"],
                            }
                        )
                    stem = result_id.replace(":", "_")
                    write_json_atomic(raw_root / "condition_manifests" / f"{stem}.json", manifest)
                    write_json_atomic(
                        raw_root / "planner_certificates" / f"{stem}.json", certificate
                    )

    # console.log: external.phase3.run_freezes.write_raw_outputs
    console.log(
        "external.phase3.run_freezes.write_raw_outputs",
        run_id=args.run_id,
        result_rows=len(results),
        trace_rows=len(trace_rows),
    )
    results.sort(key=lambda row: row["result_id"])
    crosschecks.sort(key=lambda row: row["result_id"])
    trace_rows.sort(key=lambda row: (row["result_id"], row["state_id"]))
    write_jsonl_atomic(raw_root / "freeze_results.jsonl", results)
    write_json_atomic(
        raw_root / "planner_crosscheck.json",
        {
            "checked_results": len(crosschecks),
            "passed_results": sum(item["passed"] for item in crosschecks),
            "all_passed": all(item["passed"] for item in crosschecks),
            "checks": crosschecks,
        },
    )
    trace_schema = pa.schema(
        [
            ("result_id", pa.string()),
            ("case_id", pa.string()),
            ("completion_id", pa.string()),
            ("cost_contract_id", pa.string()),
            ("freeze_id", pa.string()),
            ("state_id", pa.string()),
            ("value_kind", pa.string()),
            ("value", pa.int64()),
            ("optimal_action_ids_json", pa.string()),
            ("certificate_hash", pa.string()),
        ]
    )
    raw_root.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(trace_rows, schema=trace_schema),
        raw_root / "freeze_policy_traces.parquet",
        compression="zstd",
        use_dictionary=False,
        write_statistics=False,
    )

    # console.log: external.phase3.run_freezes.complete
    console.log(
        "external.phase3.run_freezes.complete",
        run_id=args.run_id,
        allocated=len(results),
        alternate_exact_passed=len(crosschecks),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
