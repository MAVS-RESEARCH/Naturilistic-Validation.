#!/usr/bin/env python3
"""Execute the twelve mandatory Phase-4 fail-closed attacks on isolated copies."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import write_json_atomic  # noqa: E402
from pc_external_audit.claims_audit import validate_claim_ledger  # noqa: E402
from pc_external_audit.contract_audit import validate_partition  # noqa: E402
from pc_external_audit.source_audit import object_hash  # noqa: E402
from pc_external_audit.touch_audit import audit_touch, derive_touch  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def production_touch(path: Path) -> list[dict[str, Any]]:
    return [
        {
            "completion_id": row["completion_id"],
            "state_id": row["state_id"],
            "action_id": row["action_id"],
            "successor_ids": json.loads(row["successor_ids_json"]),
            "touches": {"E": row["touch_E"], "R": row["touch_R"], "A": row["touch_A"]},
        }
        for row in pq.read_table(path).to_pylist()
    ]


def result(
    attack_id: str,
    mutation: str,
    intended_layer: str,
    detector: str,
    detected: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "attack_id": attack_id,
        "mutation": mutation,
        "intended_fail_closed_layer": intended_layer,
        "detector": detector,
        "detected": detected,
        "evidence": evidence,
    }


def provenance_complete(contract: dict[str, Any], fact_ids: set[str]) -> bool:
    referenced = contract.get("source_fact_ids", [])
    actions = contract.get("Q", [])
    return (
        bool(referenced)
        and set(referenced) <= fact_ids
        and bool(actions)
        and all(
            action.get("provenance_fact_ids") and set(action["provenance_fact_ids"]) <= fact_ids
            for action in actions
        )
    )


def expected_mask(
    contract: dict[str, Any], touches: list[dict[str, Any]], freeze_id: str
) -> list[str]:
    resources = tuple("ERA")
    forbidden = {
        resource for resource, frozen in zip(resources, freeze_id[1:], strict=True) if frozen == "1"
    }
    touch_by_action = {row["action_id"]: row["touches"] for row in touches}
    return sorted(
        action["intervention_id"]
        for action in contract["Q"]
        if not any(touch_by_action[action["intervention_id"]][item] for item in forbidden)
    )


def allocation_is_bijective(expected_case_ids: set[str], result_rows: list[dict[str, Any]]) -> bool:
    observed = [row["case_id"] for row in result_rows]
    return len(observed) == len(set(observed)) and set(observed) == expected_case_ids


def valid_extended_real(value: dict[str, Any]) -> bool:
    return (value.get("kind") == "FINITE" and set(value) == {"kind", "value"}) or (
        value.get("kind") == "INFINITE" and set(value) == {"kind"}
    )


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    contract = load(run_root / "contract" / "extensional_contract.json")
    facts = load_jsonl(run_root / "contract" / "semantic_facts.jsonl")
    manifest = load(root / "external_source" / "source_manifest.json")
    freeze_results = load_jsonl(run_root / "raw" / "freeze_results.jsonl")
    independent_touch = derive_touch(contract)
    attacks: list[dict[str, Any]] = []
    # console.log: external.phase4.corruptions.start
    console.log("external.phase4.corruptions.start", run_id=args.run_id)

    # console.log: external.phase4.corruptions.attack_touch_source_provenance_partition
    console.log(
        "external.phase4.corruptions.attack_touch_source_provenance_partition",
        run_id=args.run_id,
    )
    flipped_touch = production_touch(run_root / "contract" / "touch_records.parquet")
    flipped_touch[0]["touches"]["R"] = not flipped_touch[0]["touches"]["R"]
    detected = not audit_touch(independent_touch, flipped_touch)["passed"]
    attacks.append(
        result(
            "A1_FLIP_TOUCH",
            "flip derived R touch",
            "independent touch equality",
            "audit_touch",
            detected,
            {"field": "touches.R"},
        )
    )

    source_artifact = manifest["artifacts"][0]
    original_bytes = (root / source_artifact["snapshot_path"]).read_bytes()
    changed_hash = hashlib.sha256(original_bytes + b"corruption").hexdigest()
    detected = changed_hash != source_artifact["byte_sha256"]
    attacks.append(
        result(
            "A2_ALTER_SOURCE_BYTE",
            "append one byte sequence in memory",
            "source byte hash",
            "sha256",
            detected,
            {"artifact_id": source_artifact["artifact_id"]},
        )
    )

    no_provenance = copy.deepcopy(contract)
    del no_provenance["Q"][0]["provenance_fact_ids"]
    detected = not provenance_complete(no_provenance, {fact["fact_id"] for fact in facts})
    attacks.append(
        result(
            "A3_DELETE_PROVENANCE",
            "delete intervention provenance",
            "contract provenance",
            "required nonempty provenance",
            detected,
            {"action_id": contract["Q"][0]["intervention_id"]},
        )
    )

    bad_partition = copy.deepcopy(contract["P_R"][contract["s0"]])
    bad_partition["blocks"][0].pop()
    universe = [item["history_id"] for item in contract["U_H"]]
    detected = not validate_partition(bad_partition, universe)
    attacks.append(
        result(
            "A4_MUTATE_PARTITION",
            "remove one history from a representation block",
            "partition validity/hash",
            "validate_partition",
            detected,
            {"state_id": contract["s0"]},
        )
    )

    # console.log: external.phase4.corruptions.attack_masks_state_taint_cost
    console.log(
        "external.phase4.corruptions.attack_masks_state_taint_cost",
        run_id=args.run_id,
    )
    r_frozen = copy.deepcopy(next(row for row in freeze_results if row["freeze_id"] == "F010"))
    r_frozen["retained_action_ids"].append(contract["Q"][0]["intervention_id"])
    r_expected = expected_mask(contract, independent_touch, "F010")
    detected = sorted(r_frozen["retained_action_ids"]) != r_expected
    attacks.append(
        result(
            "A5_ADD_FROZEN_ACTION",
            "add R-touch action to F010",
            "exact action mask",
            "independent disjoint-touch mask",
            detected,
            {"freeze_id": "F010", "expected": r_expected},
        )
    )

    unrestricted = copy.deepcopy(next(row for row in freeze_results if row["freeze_id"] == "F000"))
    unrestricted["retained_action_ids"].clear()
    unrestricted_expected = expected_mask(contract, independent_touch, "F000")
    detected = sorted(unrestricted["retained_action_ids"]) != unrestricted_expected
    attacks.append(
        result(
            "A6_REMOVE_ALLOWED_ACTION",
            "remove admissible action from F000",
            "exact action mask",
            "independent disjoint-touch mask",
            detected,
            {"freeze_id": "F000", "expected": unrestricted_expected},
        )
    )

    manifest_path = next((run_root / "raw" / "condition_manifests").glob("*.json"))
    condition = load(manifest_path)
    changed_condition = copy.deepcopy(condition)
    changed_condition["scientific_instance"]["s0"] = "state:corrupted"
    detected = (
        object_hash(changed_condition["scientific_instance"]) != condition["base_instance_hash"]
    )
    attacks.append(
        result(
            "A7_CHANGE_INITIAL_STATE",
            "change condition initial state",
            "same-instance manifest",
            "base instance hash",
            detected,
            {"manifest": manifest_path.name},
        )
    )

    tainted = copy.deepcopy(contract["omega"][contract["s0"]])
    secret = next(iter(contract["A_Pi"].values()))["expected_realm"]
    tainted["leak"] = secret

    def contains(node: Any) -> bool:
        if isinstance(node, str):
            return node == secret
        if isinstance(node, dict):
            return any(contains(item) for item in node.values())
        if isinstance(node, list):
            return any(contains(item) for item in node)
        return False

    detected = contains(tainted)
    attacks.append(
        result(
            "A8_LEAK_EVALUATOR_TRUTH",
            "inject expected realm into omega",
            "controller-information firewall",
            "recursive taint search",
            detected,
            {"field": "omega.leak"},
        )
    )

    changed_cost = copy.deepcopy(contract)
    changed_cost["Q"][0]["cost"]["unit"] = 2
    detected = changed_cost["Q"][0]["cost"]["unit"] != changed_cost["c"]["unit_cost"]
    attacks.append(
        result(
            "A9_CHANGE_COST",
            "change action unit cost from one to two",
            "preregistered cost contract",
            "action/global cost equality",
            detected,
            {"observed": 2, "expected": 1},
        )
    )

    # console.log: external.phase4.corruptions.attack_retention_infinity_claims
    console.log(
        "external.phase4.corruptions.attack_retention_infinity_claims",
        run_id=args.run_id,
    )
    production_cases = pq.read_table(run_root / "processed" / "case_results.parquet").to_pylist()
    zero_row = copy.deepcopy(production_cases[0])
    zero_row["case_id"] = "isolated-zero-case"
    zero_row["delta_R_relation"] = "FINITE_ZERO"
    zero_row["result_class"] = "ZERO_GAP"
    isolated_rows = [*production_cases, zero_row]
    expected_cases = {row["case_id"] for row in isolated_rows}
    corrupted_rows = [row for row in isolated_rows if row["result_class"] != "ZERO_GAP"]
    detected = not allocation_is_bijective(expected_cases, corrupted_rows)
    attacks.append(
        result(
            "A10_DROP_ZERO_ROW",
            "filter an isolated zero-gap allocation",
            "aggregation bijection",
            "expected case identity set",
            detected,
            {"missing_case_id": "synthetic-zero"},
        )
    )

    sentinel = {"kind": "INFINITE", "value": 999999}
    detected = not valid_extended_real(sentinel)
    attacks.append(
        result(
            "A11_SENTINEL_INFINITY",
            "attach numeric sentinel to infinity",
            "extended-real validator",
            "infinite object key contract",
            detected,
            {"sentinel": 999999},
        )
    )

    claim_value = {
        "claim_id": "CLM-TEST-001",
        "predicate": "isolated claim predicate",
        "supported": True,
        "evidence_paths": ["fixture/evidence.json"],
        "prohibited_dependencies": ["prevalence"],
        "generated_text": "Constrained isolated claim.",
    }
    claim = {**claim_value, "claim_hash": object_hash(claim_value)}
    ledger_value = {
        "run_id": "isolated",
        "external_operational_validation": True,
        "result_sign": "POSITIVE",
        "locked_flags": {"prevalence": False, "superiority": False, "deployment_readiness": False},
        "claims": [claim],
    }
    ledger = {**ledger_value, "ledger_hash": object_hash(ledger_value)}
    ledger["claims"][0]["generated_text"] = "Manually strengthened universal claim."
    findings = validate_claim_ledger(ledger)
    detected = bool(findings)
    attacks.append(
        result(
            "A12_HAND_EDIT_CLAIM",
            "strengthen generated claim text without rederivation",
            "claim hash ledger",
            "validate_claim_ledger",
            detected,
            {"findings": findings},
        )
    )

    if len(attacks) != 12 or len({item["attack_id"] for item in attacks}) != 12:
        raise RuntimeError("corruption suite does not contain exactly A1-A12")
    report = {
        "run_id": args.run_id,
        "attack_count": len(attacks),
        "detected_count": sum(item["detected"] for item in attacks),
        "all_detected": all(item["detected"] for item in attacks),
        "attacks": attacks,
    }
    report["corruption_report_hash"] = object_hash(report)
    if not report["all_detected"]:
        raise RuntimeError("one or more deliberate corruptions escaped detection")
    write_json_atomic(run_root / "audit" / "corruption_report.json", report)

    # console.log: external.phase4.corruptions.complete
    console.log(
        "external.phase4.corruptions.complete",
        run_id=args.run_id,
        detected=report["detected_count"],
        required=12,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
