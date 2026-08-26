#!/usr/bin/env python3
"""Independently recompute source, semantics, touch, planning, and aggregation."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import (  # noqa: E402
    byte_hash,
    canonical_json_hash,
    write_json_atomic,
)
from pc_external_audit.contract_audit import (  # noqa: E402
    audit_contract,
    reconstruct_contract_components,
)
from pc_external_audit.planner_audit import (  # noqa: E402
    compare_case_rows,
    compare_production_results,
    recompute_results,
)
from pc_external_audit.source_audit import audit_source  # noqa: E402
from pc_external_audit.touch_audit import audit_touch, derive_touch  # noqa: E402

FORBIDDEN_AUDIT_IMPORTS = {
    "pc_external.authority",
    "pc_external.claims",
    "pc_external.contract",
    "pc_external.controls",
    "pc_external.freeze",
    "pc_external.interventions",
    "pc_external.partitions",
    "pc_external.planner",
    "pc_external.touch",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    parser.add_argument("--read-only", action="store_true")
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def scan_import_boundary(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    files = sorted((root / "src" / "pc_external_audit").glob("*.py"))
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if module in FORBIDDEN_AUDIT_IMPORTS or any(
                    module.startswith(item + ".") for item in FORBIDDEN_AUDIT_IMPORTS
                ):
                    findings.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "line": node.lineno,
                            "module": module,
                        }
                    )
    return {
        "files_scanned": len(files),
        "forbidden_import_count": len(findings),
        "findings": findings,
        "passed": len(files) == 5 and not findings,
    }


def production_touch_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for row in pq.read_table(path).to_pylist():
        rows.append(
            {
                "completion_id": row["completion_id"],
                "state_id": row["state_id"],
                "action_id": row["action_id"],
                "successor_ids": json.loads(row["successor_ids_json"]),
                "touches": {"E": row["touch_E"], "R": row["touch_R"], "A": row["touch_A"]},
            }
        )
    return rows


def verify_phase3(run_root: Path) -> dict[str, Any]:
    phase3 = load(run_root / "PHASE3_COMPLETE")
    payload = {key: value for key, value in phase3.items() if key != "phase3_completion_hash"}
    if canonical_json_hash(payload) != phase3["phase3_completion_hash"]:
        raise RuntimeError("Phase-3 completion self-hash mismatch")
    if phase3["status"] != "MEASURED" or not phase3["phase4_authorized"]:
        raise RuntimeError("Phase 3 does not authorize independent audit")
    for name, expected in phase3["artifact_hashes"].items():
        if byte_hash(run_root / name) != expected:
            raise RuntimeError(f"Phase-3 artifact mutated before audit: {name}")
    return phase3


def build_audit(root: Path, run_id: str) -> dict[str, Any]:
    run_root = root / "results" / "external_validation_v01" / run_id
    phase3 = verify_phase3(run_root)
    manifest = load(root / "external_source" / "source_manifest.json")
    preregistration = load(run_root / "preregistration" / "preregistration.json")
    native_index = load(root / "external_source" / "native_case_index.json")
    contract = load(run_root / "contract" / "extensional_contract.json")
    facts = load_jsonl(run_root / "contract" / "semantic_facts.jsonl")
    routes = {
        row["case_id"]: row["route_class"]
        for row in load(run_root / "contract" / "route_classification.json")["cases"]
    }
    source_result = audit_source(root, manifest, preregistration, native_index, facts)
    reconstructed = reconstruct_contract_components(native_index, manifest, facts)
    contract_result = audit_contract(contract, reconstructed, facts)
    independent_touch = derive_touch(contract)
    touch_result = audit_touch(
        independent_touch, production_touch_rows(run_root / "contract" / "touch_records.parquet")
    )
    independent_detailed, independent_cases = recompute_results(contract, independent_touch, routes)
    production_detailed = load_jsonl(run_root / "raw" / "freeze_results.jsonl")
    production_cases = pq.read_table(run_root / "processed" / "case_results.parquet").to_pylist()
    planner_mismatches = compare_production_results(independent_detailed, production_detailed)
    aggregation_mismatches = compare_case_rows(independent_cases, production_cases)
    expected_cases = set(contract["Terminal"])
    allocated = {row["case_id"] for row in production_cases}
    failure_cases = {
        row["case_id"] for row in load_jsonl(run_root / "processed" / "failure_cards.jsonl")
    }
    allocation_bijection = (
        allocated.isdisjoint(failure_cases) and allocated | failure_cases == expected_cases
    )
    controls = load_jsonl(run_root / "controls" / "control_results.jsonl")
    expected_control_ids = {
        "C1_REPRESENTATION_VALUE_RENAME",
        "C2_CASE_FIELD_ORDER_PERMUTATION",
        "C3_IRRELEVANT_METADATA_PERTURBATION",
        "C4_EMPTY_TOUCH_NOOP",
        "C5_EXACT_FREEZE_AUDIT",
        "C6_ATOMICITY_CHALLENGE",
        "C7_TARGET_ISOLATION",
        "C8_PROVENANCE_DELETION",
        "C9_HIDDEN_TRUTH_TAINT",
        "C10_COMPLETION_PERMUTATION",
    }
    control_ids = {row["control_id"] for row in controls}
    controls_pass = (
        len(controls) == 10
        and control_ids == expected_control_ids
        and all(row["passed"] and row["evidence"] and row["expected_invariant"] for row in controls)
    )
    import_scan = scan_import_boundary(root)
    components = {
        "source": source_result["passed"],
        "contract": contract_result["passed"],
        "touch": touch_result["passed"],
        "planner": not planner_mismatches,
        "aggregation": not aggregation_mismatches and allocation_bijection,
        "controls": controls_pass,
        "import_boundary": import_scan["passed"],
    }
    return {
        "run_id": run_id,
        "phase3_completion_hash": phase3["phase3_completion_hash"],
        "source": source_result,
        "contract": contract_result,
        "touch": touch_result,
        "planner": {
            "passed": not planner_mismatches,
            "checked": len(independent_detailed),
            "matched": len(independent_detailed) - len(planner_mismatches),
            "mismatches": planner_mismatches,
        },
        "aggregation": {
            "passed": not aggregation_mismatches and allocation_bijection,
            "checked": len(independent_cases),
            "matched": len(independent_cases) - len(aggregation_mismatches),
            "allocation_bijection": allocation_bijection,
            "production_case_count": len(production_cases),
            "production_failure_count": len(failure_cases),
            "finite_cells": sum(row["value"]["kind"] == "FINITE" for row in production_detailed),
            "infinite_cells": sum(
                row["value"]["kind"] == "INFINITE" for row in production_detailed
            ),
            "mismatches": aggregation_mismatches,
        },
        "controls": {
            "passed": controls_pass,
            "checked": len(controls),
            "matched": sum(row["passed"] for row in controls),
            "control_ids": sorted(control_ids),
            "mismatches": [] if controls_pass else [{"reason": "CONTROL_LEDGER_MISMATCH"}],
        },
        "import_boundary": import_scan,
        "components": components,
        "overall_pass": all(components.values()),
        "independent_touch_rows": independent_touch,
        "independent_detailed_rows": independent_detailed,
        "independent_case_rows": independent_cases,
    }


def independent_touch_table(audit: dict[str, Any]) -> pa.Table:
    rows = [
        {
            "independent_touch_id": row["independent_touch_id"],
            "completion_id": row["completion_id"],
            "state_id": row["state_id"],
            "action_id": row["action_id"],
            "successor_ids_json": json.dumps(row["successor_ids"], separators=(",", ":")),
            "touch_E": row["touches"]["E"],
            "touch_R": row["touches"]["R"],
            "touch_A": row["touches"]["A"],
            "witnesses_json": json.dumps(row["witnesses"], sort_keys=True, separators=(",", ":")),
            "contract_hash": row["contract_hash"],
            "provenance_hash": row["provenance_hash"],
        }
        for row in audit["independent_touch_rows"]
    ]
    schema = pa.schema(
        [
            ("independent_touch_id", pa.string()),
            ("completion_id", pa.string()),
            ("state_id", pa.string()),
            ("action_id", pa.string()),
            ("successor_ids_json", pa.string()),
            ("touch_E", pa.bool_()),
            ("touch_R", pa.bool_()),
            ("touch_A", pa.bool_()),
            ("witnesses_json", pa.string()),
            ("contract_hash", pa.string()),
            ("provenance_hash", pa.string()),
        ]
    )
    return pa.Table.from_pylist(rows, schema=schema)


def independent_result_table(run_root: Path, audit: dict[str, Any]) -> pa.Table:
    rows = []
    source_hash = load(run_root / "manifests" / "source_manifest.json")["manifest_hash"]
    for row in audit["independent_case_rows"]:
        value = {
            "run_id": audit["run_id"],
            "case_id": row["case_id"],
            "completion_id": row["completion_id"],
            "cost_contract_id": row["cost_contract_id"],
            "delta_R_relation": row["delta_R_relation"],
            "result_class": row["result_class"],
            "route_class": row["route_class"],
            "identification_status": row["identification_status"],
            "audit_eligible": row["audit_eligible"],
            "contract_hash": row["contract_hash"],
            "source_manifest_hash": source_hash,
            "phase3_completion_hash": audit["phase3_completion_hash"],
        }
        for freeze_id, _ in (
            ("F000", None),
            ("F100", None),
            ("F010", None),
            ("F001", None),
            ("F110", None),
            ("F101", None),
            ("F011", None),
            ("F111", None),
        ):
            value[f"K_{freeze_id}_kind"] = row[f"K_{freeze_id}_kind"]
            value[f"K_{freeze_id}_value"] = row[f"K_{freeze_id}_value"]
        rows.append(value)
    result_fields: list[tuple[str, pa.DataType]] = [
        ("run_id", pa.string()),
        ("case_id", pa.string()),
        ("completion_id", pa.string()),
        ("cost_contract_id", pa.string()),
        ("delta_R_relation", pa.string()),
        ("result_class", pa.string()),
        ("route_class", pa.string()),
        ("identification_status", pa.string()),
        ("audit_eligible", pa.bool_()),
        ("contract_hash", pa.string()),
        ("source_manifest_hash", pa.string()),
        ("phase3_completion_hash", pa.string()),
    ]
    for freeze_id in ("F000", "F100", "F010", "F001", "F110", "F101", "F011", "F111"):
        result_fields.extend(
            [(f"K_{freeze_id}_kind", pa.string()), (f"K_{freeze_id}_value", pa.int64())]
        )
    return pa.Table.from_pylist(rows, schema=pa.schema(result_fields))


def write_parquet_outputs(run_root: Path, audit: dict[str, Any]) -> None:
    audit_root = run_root / "audit"
    audit_root.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        independent_touch_table(audit),
        audit_root / "independent_touch.parquet",
        compression="zstd",
        use_dictionary=False,
        write_statistics=False,
    )
    pq.write_table(
        independent_result_table(run_root, audit),
        audit_root / "independent_results.parquet",
        compression="zstd",
        use_dictionary=False,
        write_statistics=False,
    )


def public_core(audit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in audit.items() if not key.startswith("independent_")}


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    # console.log: external.phase4.independent_audit.start
    console.log(
        "external.phase4.independent_audit.start",
        run_id=args.run_id,
        read_only=args.read_only,
    )

    # console.log: external.phase4.independent_audit.verify_phase3_and_import_boundary
    console.log(
        "external.phase4.independent_audit.verify_phase3_and_import_boundary",
        run_id=args.run_id,
    )
    audit = build_audit(root, args.run_id)
    core = public_core(audit)
    if not core["overall_pass"]:
        raise RuntimeError("independent core audit failed")
    if args.read_only:
        # console.log: external.phase4.independent_audit.read_only_compare
        console.log("external.phase4.independent_audit.read_only_compare", run_id=args.run_id)
        recorded = load(run_root / "audit" / "independent_audit.json")
        if recorded != core:
            raise RuntimeError("read-only independent audit differs from recorded audit")
        recorded_touch = pq.read_table(run_root / "audit" / "independent_touch.parquet")
        recorded_results = pq.read_table(run_root / "audit" / "independent_results.parquet")
        expected_touch = independent_touch_table(audit)
        expected_results = independent_result_table(run_root, audit)
        if not recorded_touch.equals(expected_touch, check_metadata=True):
            raise RuntimeError("read-only independent touch table mismatch")
        if not recorded_results.equals(expected_results, check_metadata=True):
            raise RuntimeError("read-only independent result table mismatch")
        # console.log: external.phase4.independent_audit.read_only_complete
        console.log("external.phase4.independent_audit.read_only_complete", run_id=args.run_id)
        return 0

    # console.log: external.phase4.independent_audit.recompute_source_contract_touch
    console.log(
        "external.phase4.independent_audit.recompute_source_contract_touch",
        run_id=args.run_id,
    )

    # console.log: external.phase4.independent_audit.recompute_planner_aggregation_controls
    console.log(
        "external.phase4.independent_audit.recompute_planner_aggregation_controls",
        run_id=args.run_id,
    )
    write_parquet_outputs(run_root, audit)
    write_json_atomic(run_root / "audit" / "independent_audit.json", core)
    write_json_atomic(run_root / "audit" / "import_scan_report.json", core["import_boundary"])
    mismatch_map = {
        "source_mismatches.json": core["source"]["mismatches"],
        "contract_mismatches.json": core["contract"]["mismatches"],
        "touch_mismatches.json": core["touch"]["mismatches"],
        "planner_mismatches.json": core["planner"]["mismatches"],
        "aggregation_mismatches.json": core["aggregation"]["mismatches"],
        "controls_mismatches.json": core["controls"]["mismatches"],
    }
    for name, mismatches in mismatch_map.items():
        write_json_atomic(
            run_root / "audit" / name, {"count": len(mismatches), "mismatches": mismatches}
        )

    # console.log: external.phase4.independent_audit.complete
    console.log(
        "external.phase4.independent_audit.complete",
        run_id=args.run_id,
        source_artifacts=core["source"]["artifact_count"],
        touch_matches=core["touch"]["matched"],
        planner_matches=core["planner"]["matched"],
        case_matches=core["aggregation"]["matched"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
