#!/usr/bin/env python3
"""Aggregate every retained Phase-3 cell into case and identified-set outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.freeze import FREEZE_LATTICE, classify_result, extended_relation  # noqa: E402
from pc_external.hashing import (  # noqa: E402
    canonical_json_hash,
    write_json_atomic,
    write_jsonl_atomic,
)

FREEZE_IDS = [item[0] for item in FREEZE_LATTICE]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def parquet_write(path: Path, rows: list[dict[str, Any]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(rows, schema=schema),
        path,
        compression="zstd",
        use_dictionary=False,
        write_statistics=False,
    )


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    processed = run_root / "processed"
    # console.log: external.phase3.aggregate.start
    console.log("external.phase3.aggregate.start", run_id=args.run_id)
    results = load_jsonl(run_root / "raw" / "freeze_results.jsonl")
    controls = load_jsonl(run_root / "controls" / "control_results.jsonl")
    contract = load(run_root / "contract" / "extensional_contract.json")
    completion_set = load(run_root / "contract" / "completion_set.json")
    routes = {
        row["case_id"]: row["route_class"]
        for row in load(run_root / "contract" / "route_classification.json")["cases"]
    }
    if len(controls) != 10 or not all(row["passed"] for row in controls):
        raise RuntimeError("aggregation requires ten passing controls")

    # console.log: external.phase3.aggregate.retain_case_rows
    console.log("external.phase3.aggregate.retain_case_rows", run_id=args.run_id)
    grouped: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        key = (result["case_id"], result["completion_id"], result["cost_contract_id"])
        if result["freeze_id"] in grouped[key]:
            raise RuntimeError(f"duplicate freeze cell: {key}::{result['freeze_id']}")
        grouped[key][result["freeze_id"]] = result
    case_rows: list[dict[str, Any]] = []
    failure_cards: list[dict[str, Any]] = []
    for (case_id, completion_id, cost_id), cells in sorted(grouped.items()):
        missing = sorted(set(FREEZE_IDS) - set(cells))
        if missing:
            failure_cards.append(
                {
                    "case_id": case_id,
                    "completion_id": completion_id,
                    "cost_contract_id": cost_id,
                    "failure_type": "MISSING_FREEZE_CELLS",
                    "missing_freeze_ids": missing,
                }
            )
            continue
        unrestricted = cells["F000"]["value"]
        r_frozen = cells["F010"]["value"]
        relation = extended_relation(r_frozen, unrestricted)
        row: dict[str, Any] = {
            "run_id": args.run_id,
            "case_id": case_id,
            "completion_id": completion_id,
            "cost_contract_id": cost_id,
            "delta_R_relation": relation,
            "structural_R": relation == "STRUCTURAL_POSITIVE",
            "zero_gap": relation == "FINITE_ZERO",
            "route_class": routes[case_id],
            "identification_status": completion_set["status"],
            "result_class": classify_result(unrestricted, r_frozen),
            "audit_eligible": True,
            "contract_hash": contract["contract_hash"],
        }
        for freeze_id in FREEZE_IDS:
            value = cells[freeze_id]["value"]
            row[f"K_{freeze_id}_kind"] = value["kind"]
            row[f"K_{freeze_id}_value"] = value.get("value")
            row[f"{freeze_id}_result_id"] = cells[freeze_id]["result_id"]
        case_rows.append(row)
    if failure_cards:
        write_jsonl_atomic(processed / "failure_cards.jsonl", failure_cards)
        raise RuntimeError("incomplete native cases were retained as failure cards")
    write_jsonl_atomic(processed / "failure_cards.jsonl", [])

    case_fields: list[tuple[str, pa.DataType]] = [
        ("run_id", pa.string()),
        ("case_id", pa.string()),
        ("completion_id", pa.string()),
        ("cost_contract_id", pa.string()),
        ("delta_R_relation", pa.string()),
        ("structural_R", pa.bool_()),
        ("zero_gap", pa.bool_()),
        ("route_class", pa.string()),
        ("identification_status", pa.string()),
        ("result_class", pa.string()),
        ("audit_eligible", pa.bool_()),
        ("contract_hash", pa.string()),
    ]
    for freeze_id in FREEZE_IDS:
        case_fields.extend(
            [
                (f"K_{freeze_id}_kind", pa.string()),
                (f"K_{freeze_id}_value", pa.int64()),
                (f"{freeze_id}_result_id", pa.string()),
            ]
        )
    parquet_write(processed / "case_results.parquet", case_rows, pa.schema(case_fields))

    # console.log: external.phase3.aggregate.build_identified_sets
    console.log("external.phase3.aggregate.build_identified_sets", run_id=args.run_id)
    identified_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        identified_groups[(row["case_id"], row["cost_contract_id"])].append(row)
    identified_rows: list[dict[str, Any]] = []
    for (case_id, cost_id), rows in sorted(identified_groups.items()):
        relation_set = sorted({row["delta_R_relation"] for row in rows})
        value_sets = {
            freeze_id: sorted(
                {
                    json.dumps(
                        {
                            "kind": row[f"K_{freeze_id}_kind"],
                            **(
                                {"value": row[f"K_{freeze_id}_value"]}
                                if row[f"K_{freeze_id}_kind"] == "FINITE"
                                else {}
                            ),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    for row in rows
                }
            )
            for freeze_id in FREEZE_IDS
        }
        positive_sign_invariant = bool(relation_set) and set(relation_set) <= {
            "FINITE_POSITIVE",
            "STRUCTURAL_POSITIVE",
        }
        identified_rows.append(
            {
                "run_id": args.run_id,
                "case_id": case_id,
                "cost_contract_id": cost_id,
                "completion_count": len(rows),
                "identification_status": completion_set["status"],
                "freeze_value_sets_json": json.dumps(
                    value_sets, sort_keys=True, separators=(",", ":")
                ),
                "delta_R_relation_set_json": json.dumps(relation_set, separators=(",", ":")),
                "point_identified": all(len(values) == 1 for values in value_sets.values())
                and len(relation_set) == 1,
                "positive_sign_invariant": positive_sign_invariant,
                "identified_result_class": (
                    "PARTIAL_SIGN"
                    if len(relation_set) > 1
                    else sorted({row["result_class"] for row in rows})[0]
                ),
                "result_class_set_json": json.dumps(
                    sorted({row["result_class"] for row in rows}), separators=(",", ":")
                ),
            }
        )
    identified_schema = pa.schema(
        [
            ("run_id", pa.string()),
            ("case_id", pa.string()),
            ("cost_contract_id", pa.string()),
            ("completion_count", pa.int64()),
            ("identification_status", pa.string()),
            ("freeze_value_sets_json", pa.string()),
            ("delta_R_relation_set_json", pa.string()),
            ("point_identified", pa.bool_()),
            ("positive_sign_invariant", pa.bool_()),
            ("identified_result_class", pa.string()),
            ("result_class_set_json", pa.string()),
        ]
    )
    parquet_write(processed / "identified_sets.parquet", identified_rows, identified_schema)

    lattice_rows = [
        {
            "run_id": row["run_id"],
            "case_id": row["case_id"],
            "completion_id": row["completion_id"],
            "cost_contract_id": row["cost_contract_id"],
            "freeze_id": row["freeze_id"],
            "forbidden_resources_json": json.dumps(
                row["forbidden_resources"], separators=(",", ":")
            ),
            "retained_action_ids_json": json.dumps(
                row["retained_action_ids"], separators=(",", ":")
            ),
            "blocked_action_ids_json": json.dumps(row["blocked_action_ids"], separators=(",", ":")),
            "value_kind": row["value"]["kind"],
            "value": row["value"].get("value"),
            "result_id": row["result_id"],
            "certificate_hash": row["certificate_hash"],
            "condition_manifest_hash": row["condition_manifest_hash"],
        }
        for row in sorted(results, key=lambda item: item["result_id"])
    ]
    lattice_schema = pa.schema(
        [
            ("run_id", pa.string()),
            ("case_id", pa.string()),
            ("completion_id", pa.string()),
            ("cost_contract_id", pa.string()),
            ("freeze_id", pa.string()),
            ("forbidden_resources_json", pa.string()),
            ("retained_action_ids_json", pa.string()),
            ("blocked_action_ids_json", pa.string()),
            ("value_kind", pa.string()),
            ("value", pa.int64()),
            ("result_id", pa.string()),
            ("certificate_hash", pa.string()),
            ("condition_manifest_hash", pa.string()),
        ]
    )
    parquet_write(processed / "freeze_lattice.parquet", lattice_rows, lattice_schema)
    with (processed / "freeze_lattice.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(lattice_rows[0]))
        writer.writeheader()
        writer.writerows(lattice_rows)

    # console.log: external.phase3.aggregate.write_reports
    console.log("external.phase3.aggregate.write_reports", run_id=args.run_id)
    allocation = {
        "native_case_count": len(contract["Terminal"]),
        "completion_count": completion_set["completion_count"],
        "freeze_count": len(FREEZE_IDS),
        "cost_contract_count": 1,
        "expected_cells": len(contract["Terminal"]) * completion_set["completion_count"] * 8,
        "observed_result_cells": len(results),
        "case_result_rows": len(case_rows),
        "identified_set_rows": len(identified_rows),
        "failure_card_count": len(failure_cards),
        "complete": len(results)
        == len(contract["Terminal"]) * completion_set["completion_count"] * 8,
    }
    allocation["allocation_hash"] = canonical_json_hash(allocation)
    write_json_atomic(processed / "allocation_report.json", allocation)
    classification_counts = dict(sorted(Counter(row["result_class"] for row in case_rows).items()))
    summary = {
        "run_id": args.run_id,
        "phase": 3,
        "status": "MEASURED",
        "case_result_rows": len(case_rows),
        "raw_freeze_rows": len(results),
        "identified_set_rows": len(identified_rows),
        "control_passes": sum(row["passed"] for row in controls),
        "failure_card_count": len(failure_cards),
        "classification_counts": classification_counts,
        "delta_R_relation_counts": dict(
            sorted(Counter(row["delta_R_relation"] for row in case_rows).items())
        ),
        "all_rows_audit_eligible": all(row["audit_eligible"] for row in case_rows),
        "no_models_trained": True,
    }
    summary["summary_hash"] = canonical_json_hash(summary)
    write_json_atomic(processed / "summary.json", summary)
    paper_fields = [
        "case_id",
        "cost_contract_id",
        "K_F000_kind",
        "K_F000_value",
        "K_F010_kind",
        "K_F010_value",
        "delta_R_relation",
        "result_class",
        "route_class",
        "identification_status",
        "audit_eligible",
    ]
    with (processed / "paper_table.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=paper_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(case_rows)

    # console.log: external.phase3.aggregate.complete
    console.log(
        "external.phase3.aggregate.complete",
        run_id=args.run_id,
        case_rows=len(case_rows),
        classifications=classification_counts,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
