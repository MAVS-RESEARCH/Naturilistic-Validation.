#!/usr/bin/env python3
"""Validate all Phase-3 scientific gates and emit the MEASURED completion record."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import yaml


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.freeze import (  # noqa: E402
    FREEZE_LATTICE,
    assert_same_instance,
    derive_action_mask,
    exact_freeze_lattice,
    extended_relation,
)
from pc_external.hashing import byte_hash, canonical_json_hash, write_json_atomic  # noqa: E402
from scripts.phase2_validate_contract import validate_schema  # noqa: E402
from scripts.phase3_run_freezes import touch_map, verify_contract_seal  # noqa: E402

FREEZE_MAP = {freeze_id: set(resources) for freeze_id, resources in FREEZE_LATTICE}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def extended_ge(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["kind"] == "INFINITE":
        return True
    if right["kind"] == "INFINITE":
        return False
    return left["value"] >= right["value"]


def verify_no_sentinel_infinity(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        if value.get("kind") == "INFINITE" and set(value) != {"kind"}:
            raise RuntimeError(f"infinite extended-real value carries a sentinel payload at {path}")
        for key, item in value.items():
            verify_no_sentinel_infinity(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            verify_no_sentinel_infinity(item, f"{path}[{index}]")
    elif isinstance(value, str) and value.lower() in {
        "inf",
        "+inf",
        "infinity",
        "+infinity",
        "999999",
    }:
        raise RuntimeError(f"sentinel infinity detected at {path}")


def parquet_signature(path: Path) -> tuple[int, list[str], dict[str, str]]:
    table = pq.read_table(path)
    return (
        table.num_rows,
        table.column_names,
        {field.name: str(field.type) for field in table.schema},
    )


def require_parquet_contract(
    name: str,
    signature: tuple[int, list[str], dict[str, str]],
    expected_fields: list[tuple[str, str]],
) -> None:
    expected_columns = [field for field, _ in expected_fields]
    expected_types = dict(expected_fields)
    if signature[1] != expected_columns or signature[2] != expected_types:
        raise RuntimeError(
            f"{name} Parquet columns or types differ from the sealed Phase-3 contract"
        )


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    contract_root = run_root / "contract"
    raw_root = run_root / "raw"
    processed_root = run_root / "processed"
    # console.log: external.phase3.validate.start
    console.log("external.phase3.validate.start", run_id=args.run_id)

    # console.log: external.phase3.validate.verify_upstream_seal
    console.log("external.phase3.validate.verify_upstream_seal", run_id=args.run_id)
    seal = verify_contract_seal(contract_root)
    contract = load(contract_root / "extensional_contract.json")
    completions = load(contract_root / "completion_set.json")
    touches = touch_map(contract_root)
    experiment = yaml.safe_load((root / "configs" / "experiment.yaml").read_text(encoding="utf-8"))
    lattice = exact_freeze_lattice(experiment["freeze_sets"])
    inventory = load(run_root / "manifests" / "phase3_pre_run_inventory.json")
    if not inventory["clean_start"] or inventory["prior_phase3_file_count"] != 0:
        raise RuntimeError("Phase-3 results hygiene gate failed")

    # console.log: external.phase3.validate.schemas_and_allocations
    console.log("external.phase3.validate.schemas_and_allocations", run_id=args.run_id)
    results = load_jsonl(raw_root / "freeze_results.jsonl")
    controls = load_jsonl(run_root / "controls" / "control_results.jsonl")
    for result in results:
        validate_schema(root, result, "freeze_result.schema.json")
        verify_no_sentinel_infinity(result)
    for control in controls:
        validate_schema(root, control, "control_result.schema.json")
    expected_keys = {
        (case_id, completion["completion_id"], "unit_intervention_cost", freeze["freeze_id"])
        for case_id in contract["Terminal"]
        for completion in completions["completions"]
        for freeze in lattice
    }
    observed_keys = [
        (
            row["case_id"],
            row["completion_id"],
            row["cost_contract_id"],
            row["freeze_id"],
        )
        for row in results
    ]
    if set(observed_keys) != expected_keys or len(observed_keys) != len(expected_keys):
        raise RuntimeError("case/completion/cost/freeze allocation is incomplete or duplicated")
    if len(controls) != 10 or not all(item["passed"] for item in controls):
        raise RuntimeError("C1-C10 require exactly 10/10 passes")
    if {item["control_id"].split("_", 1)[0] for item in controls} != {
        f"C{index}" for index in range(1, 11)
    }:
        raise RuntimeError("control IDs do not cover C1-C10 exactly")

    # console.log: external.phase3.validate.manifests_masks_certificates
    console.log("external.phase3.validate.manifests_masks_certificates", run_id=args.run_id)
    manifests_by_group: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    result_lookup: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for result in results:
        stem = result["result_id"].replace(":", "_")
        manifest = load(raw_root / "condition_manifests" / f"{stem}.json")
        certificate = load(raw_root / "planner_certificates" / f"{stem}.json")
        manifest_payload = {
            key: value for key, value in manifest.items() if key != "condition_manifest_hash"
        }
        if canonical_json_hash(manifest_payload) != manifest["condition_manifest_hash"]:
            raise RuntimeError("condition manifest self-hash mismatch")
        if result["condition_manifest_hash"] != manifest["condition_manifest_hash"]:
            raise RuntimeError("freeze result is not bound to its condition manifest")
        certificate_payload = {
            key: value for key, value in certificate.items() if key != "certificate_hash"
        }
        if canonical_json_hash(certificate_payload) != certificate["certificate_hash"]:
            raise RuntimeError("planner certificate self-hash mismatch")
        if result["certificate_hash"] != certificate["certificate_hash"]:
            raise RuntimeError("freeze result is not bound to its planner certificate")
        expected_mask = derive_action_mask(contract["Q"], touches, result["forbidden_resources"])
        if (
            result["retained_action_ids"] != expected_mask["retained_action_ids"]
            or result["blocked_action_ids"] != expected_mask["blocked_action_ids"]
            or result["action_mask_hash"] != expected_mask["action_mask_hash"]
        ):
            raise RuntimeError("action mask differs from exact derived-touch set disjointness")
        key3 = (result["case_id"], result["completion_id"], result["cost_contract_id"])
        manifests_by_group[key3].append(manifest)
        result_lookup[(*key3, result["freeze_id"])] = result
    same_instance_checks = [assert_same_instance(rows) for rows in manifests_by_group.values()]
    if any(item["manifest_count"] != 8 for item in same_instance_checks):
        raise RuntimeError("same-instance group does not contain all eight conditions")

    # console.log: external.phase3.validate.mathematical_relations
    console.log("external.phase3.validate.mathematical_relations", run_id=args.run_id)
    monotonic_pairs = 0
    for key3 in manifests_by_group:
        unrestricted = result_lookup[(*key3, "F000")]["value"]
        r_frozen = result_lookup[(*key3, "F010")]["value"]
        relation = extended_relation(r_frozen, unrestricted)
        if relation not in {
            "FINITE_POSITIVE",
            "FINITE_ZERO",
            "STRUCTURAL_POSITIVE",
            "BOTH_INFINITE",
            "UNDEFINED",
        }:
            raise RuntimeError("invalid Delta_R relation")
        for less_id, less_forbidden in FREEZE_MAP.items():
            for more_id, more_forbidden in FREEZE_MAP.items():
                if less_forbidden < more_forbidden:
                    less = result_lookup[(*key3, less_id)]
                    more = result_lookup[(*key3, more_id)]
                    if not set(more["retained_action_ids"]) <= set(less["retained_action_ids"]):
                        raise RuntimeError("superset freeze retained an action removed earlier")
                    if not extended_ge(more["value"], less["value"]):
                        raise RuntimeError("superset-freeze monotonicity failed")
                    monotonic_pairs += 1
    crosscheck = load(raw_root / "planner_crosscheck.json")
    if not crosscheck["all_passed"] or crosscheck["checked_results"] != len(results):
        raise RuntimeError("alternate exact planner did not pass every authoritative cell")

    # console.log: external.phase3.validate.parquet_and_retention
    console.log("external.phase3.validate.parquet_and_retention", run_id=args.run_id)
    case_signature = parquet_signature(processed_root / "case_results.parquet")
    set_signature = parquet_signature(processed_root / "identified_sets.parquet")
    lattice_signature = parquet_signature(processed_root / "freeze_lattice.parquet")
    trace_signature = parquet_signature(raw_root / "freeze_policy_traces.parquet")
    case_fields = [
        ("run_id", "string"),
        ("case_id", "string"),
        ("completion_id", "string"),
        ("cost_contract_id", "string"),
        ("delta_R_relation", "string"),
        ("structural_R", "bool"),
        ("zero_gap", "bool"),
        ("route_class", "string"),
        ("identification_status", "string"),
        ("result_class", "string"),
        ("audit_eligible", "bool"),
        ("contract_hash", "string"),
    ]
    for freeze_id, _ in FREEZE_LATTICE:
        case_fields.extend(
            [
                (f"K_{freeze_id}_kind", "string"),
                (f"K_{freeze_id}_value", "int64"),
                (f"{freeze_id}_result_id", "string"),
            ]
        )
    require_parquet_contract("case_results", case_signature, case_fields)
    require_parquet_contract(
        "identified_sets",
        set_signature,
        [
            ("run_id", "string"),
            ("case_id", "string"),
            ("cost_contract_id", "string"),
            ("completion_count", "int64"),
            ("identification_status", "string"),
            ("freeze_value_sets_json", "string"),
            ("delta_R_relation_set_json", "string"),
            ("point_identified", "bool"),
            ("positive_sign_invariant", "bool"),
            ("identified_result_class", "string"),
            ("result_class_set_json", "string"),
        ],
    )
    require_parquet_contract(
        "freeze_lattice",
        lattice_signature,
        [
            ("run_id", "string"),
            ("case_id", "string"),
            ("completion_id", "string"),
            ("cost_contract_id", "string"),
            ("freeze_id", "string"),
            ("forbidden_resources_json", "string"),
            ("retained_action_ids_json", "string"),
            ("blocked_action_ids_json", "string"),
            ("value_kind", "string"),
            ("value", "int64"),
            ("result_id", "string"),
            ("certificate_hash", "string"),
            ("condition_manifest_hash", "string"),
        ],
    )
    require_parquet_contract(
        "freeze_policy_traces",
        trace_signature,
        [
            ("result_id", "string"),
            ("case_id", "string"),
            ("completion_id", "string"),
            ("cost_contract_id", "string"),
            ("freeze_id", "string"),
            ("state_id", "string"),
            ("value_kind", "string"),
            ("value", "int64"),
            ("optimal_action_ids_json", "string"),
            ("certificate_hash", "string"),
        ],
    )
    allocation = load(processed_root / "allocation_report.json")
    summary = load(processed_root / "summary.json")
    failure_cards = load_jsonl(processed_root / "failure_cards.jsonl")
    expected_case_rows = len(contract["Terminal"]) * completions["completion_count"]
    if case_signature[0] != expected_case_rows or set_signature[0] != len(contract["Terminal"]):
        raise RuntimeError("processed case or identified-set retention failed")
    if lattice_signature[0] != len(results) or trace_signature[0] != len(results) * len(
        contract["S"]
    ):
        raise RuntimeError("lattice or planner-trace row retention failed")
    if not allocation["complete"] or allocation["failure_card_count"] != len(failure_cards):
        raise RuntimeError("allocation report or failure-card accounting failed")
    if summary["status"] != "MEASURED" or summary["control_passes"] != 10:
        raise RuntimeError("summary does not meet the Phase-3 exit gate")
    infinite_rows = sum(row["value"]["kind"] == "INFINITE" for row in results)
    finite_rows = len(results) - infinite_rows

    report = {
        "run_id": args.run_id,
        "phase": 3,
        "status": "MEASURED",
        "contract_hash": contract["contract_hash"],
        "contract_seal_hash": seal["contract_seal_hash"],
        "results_hygiene_passed": True,
        "expected_allocations": len(expected_keys),
        "observed_allocations": len(results),
        "all_eight_conditions_per_group": True,
        "same_instance_group_count": len(same_instance_checks),
        "same_instance_passed": True,
        "exact_action_masks_passed": True,
        "production_alternate_exact_matches": crosscheck["passed_results"],
        "controls_passed": sum(item["passed"] for item in controls),
        "monotonicity_pairs_checked": monotonic_pairs,
        "finite_result_rows_retained": finite_rows,
        "infinite_result_rows_retained": infinite_rows,
        "failure_card_count": len(failure_cards),
        "parquet": {
            "freeze_policy_traces": {
                "rows": trace_signature[0],
                "columns": trace_signature[1],
                "types": trace_signature[2],
            },
            "case_results": {
                "rows": case_signature[0],
                "columns": case_signature[1],
                "types": case_signature[2],
            },
            "identified_sets": {
                "rows": set_signature[0],
                "columns": set_signature[1],
                "types": set_signature[2],
            },
            "freeze_lattice": {
                "rows": lattice_signature[0],
                "columns": lattice_signature[1],
                "types": lattice_signature[2],
            },
        },
        "classification_counts": summary["classification_counts"],
        "delta_R_relation_counts": summary["delta_R_relation_counts"],
        "all_scientific_gates_passed": True,
    }
    report["validation_hash"] = canonical_json_hash(report)
    write_json_atomic(run_root / "reports" / "phase3_validation.json", report)

    # console.log: external.phase3.validate.seal_phase
    console.log("external.phase3.validate.seal_phase", run_id=args.run_id)
    scientific_roots = [raw_root, processed_root, run_root / "controls"]
    artifact_hashes = {
        path.relative_to(run_root).as_posix(): byte_hash(path)
        for directory in scientific_roots
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }
    artifact_hashes["reports/phase3_validation.json"] = byte_hash(
        run_root / "reports" / "phase3_validation.json"
    )
    completion_value = {
        "run_id": args.run_id,
        "phase": 3,
        "status": "MEASURED",
        "phase4_authorized": True,
        "contract_hash": contract["contract_hash"],
        "contract_seal_hash": seal["contract_seal_hash"],
        "validation_hash": report["validation_hash"],
        "artifact_hashes": artifact_hashes,
        "raw_result_count": len(results),
        "case_result_count": case_signature[0],
        "identified_set_count": set_signature[0],
        "control_pass_count": 10,
        "failure_card_count": len(failure_cards),
    }
    completion = {
        **completion_value,
        "phase3_completion_hash": canonical_json_hash(completion_value),
    }
    write_json_atomic(run_root / "PHASE3_COMPLETE", completion)
    run_manifest = load(run_root / "manifests" / "run_manifest.json")
    run_manifest.update(
        {
            "phase": 3,
            "status": "MEASURED",
            "phase4_authorized": True,
            "phase3_completion_hash": completion["phase3_completion_hash"],
        }
    )
    run_manifest.pop("run_manifest_hash", None)
    run_manifest["run_manifest_hash"] = canonical_json_hash(run_manifest)
    write_json_atomic(run_root / "manifests" / "run_manifest.json", run_manifest)

    # console.log: external.phase3.validate.complete
    console.log(
        "external.phase3.validate.complete",
        run_id=args.run_id,
        status="MEASURED",
        allocations=len(results),
        controls=10,
        classifications=report["classification_counts"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
