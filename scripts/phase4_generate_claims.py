#!/usr/bin/env python3
"""Generate constrained claims, provenance graph, final audit, reports, and seal."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.claims import derive_claim_ledger, final_verdict  # noqa: E402
from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import (  # noqa: E402
    byte_hash,
    canonical_json_hash,
    write_json_atomic,
    write_jsonl_atomic,
)
from pc_external_audit.claims_audit import (  # noqa: E402
    validate_claim_ledger,
    verify_report_sentences,
)
from scripts.phase2_validate_contract import validate_schema  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    parser.add_argument("--verify-seal", action="store_true")
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def claim_lines(ledger: dict[str, Any], supported_only: bool = False) -> list[str]:
    return [
        f"[{claim['claim_id']}] {claim['generated_text']}"
        for claim in ledger["claims"]
        if not supported_only or claim["supported"]
    ]


def update_run_manifest(run_root: Path, verdict: str) -> None:
    manifest = load(run_root / "manifests" / "run_manifest.json")
    manifest.update({"phase": 4, "status": verdict, "phase4_complete": True})
    manifest.pop("run_manifest_hash", None)
    manifest["run_manifest_hash"] = canonical_json_hash(manifest)
    write_json_atomic(run_root / "manifests" / "run_manifest.json", manifest)


def scientific_file_paths(root: Path, run_root: Path) -> list[Path]:
    paths = [path for path in sorted((root / "configs").glob("*.yaml")) if path.is_file()]
    paths.extend(
        path
        for path in sorted((root / "external_source").rglob("*"))
        if path.is_file() and "/cache/" not in path.as_posix()
    )
    paths.extend(
        path
        for path in sorted(run_root.rglob("*"))
        if path.is_file()
        and path.name not in {"SEALED", "artifact_graph.json", "audit.json", "clause_audit.json"}
    )
    return paths


def build_artifact_graph(
    root: Path, run_root: Path, case_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    files = scientific_file_paths(root, run_root)
    file_nodes = []
    indexed_paths: list[str] = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        indexed_paths.append(relative)
        file_nodes.append(
            {
                "node_id": f"file:{relative}",
                "kind": "FILE",
                "path": relative,
                "sha256": byte_hash(path),
            }
        )
    entities: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    facts = load_jsonl(run_root / "contract" / "semantic_facts.jsonl")
    source_manifest = load(root / "external_source" / "source_manifest.json")
    artifact_paths = {
        item["artifact_id"]: f"file:{item['snapshot_path']}"
        for item in source_manifest["artifacts"]
    }
    facts_file = (
        f"file:{(run_root / 'contract' / 'semantic_facts.jsonl').relative_to(root).as_posix()}"
    )
    contract_file = (
        f"file:{(run_root / 'contract' / 'extensional_contract.json').relative_to(root).as_posix()}"
    )
    touch_file = (
        f"file:{(run_root / 'contract' / 'touch_records.parquet').relative_to(root).as_posix()}"
    )
    case_file = (
        f"file:{(run_root / 'processed' / 'case_results.parquet').relative_to(root).as_posix()}"
    )
    freeze_file = f"file:{(run_root / 'raw' / 'freeze_results.jsonl').relative_to(root).as_posix()}"
    paper_file = (
        f"file:{(run_root / 'reports' / 'audited_paper_table.csv').relative_to(root).as_posix()}"
    )
    for fact in facts:
        fact_node = f"fact:{fact['fact_id']}"
        entities.append(
            {"node_id": fact_node, "kind": "SEMANTIC_FACT", "identity": fact["fact_id"]}
        )
        edges.append({"from": facts_file, "to": fact_node, "relation": "CONTAINS"})
        edges.append(
            {"from": fact_node, "to": artifact_paths[fact["artifact_id"]], "relation": "PROVEN_BY"}
        )
    edges.append({"from": contract_file, "to": facts_file, "relation": "COMPILED_FROM"})
    edges.append({"from": touch_file, "to": contract_file, "relation": "DERIVED_FROM"})
    production_results = load_jsonl(run_root / "raw" / "freeze_results.jsonl")
    result_by_key = {(row["case_id"], row["freeze_id"]): row for row in production_results}
    paper_nodes: list[str] = []
    source_nodes = set(artifact_paths.values())
    for row in case_rows:
        case_id = row["case_id"]
        paper_node = f"paper_row:{case_id}"
        paper_nodes.append(paper_node)
        entities.append({"node_id": paper_node, "kind": "PAPER_VALUE", "identity": case_id})
        edges.extend(
            [
                {"from": paper_file, "to": paper_node, "relation": "CONTAINS"},
                {"from": paper_node, "to": case_file, "relation": "READS_CASE_ROW"},
            ]
        )
        for freeze_id in ("F000", "F010"):
            result = result_by_key[(case_id, freeze_id)]
            result_node = f"result:{result['result_id']}"
            entities.append(
                {"node_id": result_node, "kind": "FREEZE_RESULT", "identity": result["result_id"]}
            )
            stem = result["result_id"].replace(":", "_") + ".json"
            certificate_path = run_root / "raw" / "planner_certificates" / stem
            condition_path = run_root / "raw" / "condition_manifests" / stem
            certificate = f"file:{certificate_path.relative_to(root).as_posix()}"
            condition = f"file:{condition_path.relative_to(root).as_posix()}"
            edges.extend(
                [
                    {"from": paper_node, "to": result_node, "relation": f"READS_{freeze_id}"},
                    {"from": result_node, "to": freeze_file, "relation": "STORED_IN"},
                    {"from": result_node, "to": certificate, "relation": "CERTIFIED_BY"},
                    {"from": certificate, "to": condition, "relation": "BOUND_TO"},
                    {"from": condition, "to": touch_file, "relation": "MASK_DERIVED_FROM"},
                ]
            )
    all_nodes = {node["node_id"] for node in file_nodes + entities}
    adjacency: dict[str, set[str]] = {node: set() for node in all_nodes}
    reverse: dict[str, set[str]] = {node: set() for node in all_nodes}
    for edge in edges:
        adjacency[edge["from"]].add(edge["to"])
        reverse[edge["to"]].add(edge["from"])

    def reaches(start: str, targets: set[str], graph: dict[str, set[str]]) -> bool:
        queue = deque([start])
        seen = {start}
        while queue:
            current = queue.popleft()
            if current in targets:
                return True
            for neighbor in graph[current] - seen:
                seen.add(neighbor)
                queue.append(neighbor)
        return False

    backward_pass = all(reaches(node, source_nodes, adjacency) for node in paper_nodes)
    forward_pass = all(
        reaches(source, set(paper_nodes), reverse) for source in source_nodes if reverse[source]
    )
    value = {
        "run_id": run_root.name,
        "nodes": sorted(file_nodes + entities, key=lambda item: item["node_id"]),
        "edges": sorted(edges, key=lambda item: (item["from"], item["to"], item["relation"])),
        "indexed_scientific_paths": sorted(indexed_paths),
        "scientific_file_count": len(files),
        "indexed_scientific_file_count": len(indexed_paths),
        "unindexed_scientific_files": [],
        "excluded_self_referential_metadata": [
            "audit/artifact_graph.json",
            "audit/audit.json",
            "audit/clause_audit.json",
            "SEALED",
        ],
        "paper_value_count": len(paper_nodes),
        "backward_traversal_passed": backward_pass,
        "forward_traversal_passed": forward_pass,
    }
    if not backward_pass or not forward_pass or len(indexed_paths) != len(set(indexed_paths)):
        raise RuntimeError("artifact graph traversal or indexing failed")
    return {**value, "artifact_graph_hash": canonical_json_hash(value)}


def gate(passed: bool, checked: int, matched: int, evidence: list[str]) -> dict[str, Any]:
    return {"passed": passed, "checked": checked, "matched": matched, "evidence": evidence}


def verify_final_seal(root: Path, run_root: Path) -> dict[str, Any]:
    seal = load(run_root / "SEALED")
    payload = {key: value for key, value in seal.items() if key != "seal_hash"}
    if seal["seal_hash"] != canonical_json_hash(payload):
        raise RuntimeError("final seal self-hash mismatch")
    for relative, expected in seal["artifact_hashes"].items():
        if byte_hash(root / relative) != expected:
            raise RuntimeError(f"post-seal artifact mutation: {relative}")
    audit = load(run_root / "audit" / "audit.json")
    validate_schema(root, audit, "audit.schema.json")
    audit_payload = {key: value for key, value in audit.items() if key != "audit_hash"}
    if audit["audit_hash"] != canonical_json_hash(audit_payload) or not audit["overall_pass"]:
        raise RuntimeError("final audit hash or pass state is invalid")
    ledger = load(run_root / "reports" / "claim_ledger.json")
    validate_schema(root, ledger, "claim_ledger.schema.json")
    findings = validate_claim_ledger(ledger)
    findings.extend(
        verify_report_sentences(
            (run_root / "reports" / "CLAIMS.md").read_text(encoding="utf-8"), ledger
        )
    )
    findings.extend(
        verify_report_sentences(
            (run_root / "reports" / "external_case_report.md").read_text(encoding="utf-8"),
            ledger,
            supported_only=True,
        )
    )
    if findings:
        raise RuntimeError(f"post-seal claims mismatch: {findings}")
    graph = load(run_root / "audit" / "artifact_graph.json")
    graph_payload = {key: value for key, value in graph.items() if key != "artifact_graph_hash"}
    if graph["artifact_graph_hash"] != canonical_json_hash(graph_payload):
        raise RuntimeError("artifact graph self-hash mismatch")
    if (
        graph["unindexed_scientific_files"]
        or not graph["backward_traversal_passed"]
        or not graph["forward_traversal_passed"]
    ):
        raise RuntimeError("artifact graph completeness failed")
    return seal


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    audit_root = run_root / "audit"
    reports_root = run_root / "reports"
    # console.log: external.phase4.claims.start
    console.log("external.phase4.claims.start", run_id=args.run_id)
    if args.verify_seal:
        # console.log: external.phase4.claims.verify_seal_read_only
        console.log("external.phase4.claims.verify_seal_read_only", run_id=args.run_id)
        seal = verify_final_seal(root, run_root)
        # console.log: external.phase4.claims.verify_seal_complete
        console.log(
            "external.phase4.claims.verify_seal_complete",
            run_id=args.run_id,
            seal_hash=seal["seal_hash"],
        )
        return 0
    core = load(audit_root / "independent_audit.json")
    corruption = load(audit_root / "corruption_report.json")
    case_rows = pq.read_table(run_root / "processed" / "case_results.parquet").to_pylist()
    if not core["overall_pass"] or not corruption["all_detected"]:
        raise RuntimeError("claims require passing independent and corruption audits")

    # console.log: external.phase4.claims.derive_ledger
    console.log("external.phase4.claims.derive_ledger", run_id=args.run_id)
    ledger = derive_claim_ledger(args.run_id, core, corruption, case_rows)
    validate_schema(root, ledger, "claim_ledger.schema.json")
    claim_findings = validate_claim_ledger(ledger)
    if claim_findings:
        raise RuntimeError(f"claim ledger validation failed: {claim_findings}")
    write_json_atomic(reports_root / "claim_ledger.json", ledger)
    verdict = final_verdict(ledger)

    # console.log: external.phase4.claims.generate_reports
    console.log("external.phase4.claims.generate_reports", run_id=args.run_id)
    claims_markdown = (
        "\n".join(
            [
                "# Audited Claims",
                "",
                f"Final verdict: **{verdict}**",
                "",
                *claim_lines(ledger),
                "",
                "Only the claim-ID-prefixed sentences above are authorized paper-facing language.",
            ]
        )
        + "\n"
    )
    (reports_root / "CLAIMS.md").write_text(claims_markdown, encoding="utf-8", newline="\n")
    reproduce = (
        "\n".join(
            [
                "# Reproduce the External Validation",
                "",
                "From the repository root with the locked Python environment available:",
                "",
                "```text",
                "npm run phase4",
                "```",
                "",
                (
                    "The command safely removes only the explicitly named unsealed run, "
                    "regenerates Phases 1-4, executes the full test suite, seals the run, "
                    "proves cleaner refusal, "
                    "and reruns the independent audit read-only."
                ),
                "",
                f"Expected run ID: `{args.run_id}`.",
                f"Expected verdict: `{verdict}`.",
            ]
        )
        + "\n"
    )
    (reports_root / "REPRODUCE.md").write_text(reproduce, encoding="utf-8", newline="\n")
    supported = claim_lines(ledger, supported_only=True)
    case_report = (
        "\n".join(
            [
                "# External Case Report",
                "",
                f"Verdict: **{verdict}**",
                "",
                *supported,
                "",
                "## Retained native cases",
                "",
                "| Case | F000 | F010 | Delta relation | Result | Route |",
                "|---|---:|---|---|---|---|",
                *[
                    (
                        f"| `{row['case_id']}` | {row['K_F000_value']} | "
                        f"{row['K_F010_kind']} | {row['delta_R_relation']} | "
                        f"{row['result_class']} | {row['route_class']} |"
                    )
                    for row in case_rows
                ],
            ]
        )
        + "\n"
    )
    (reports_root / "external_case_report.md").write_text(
        case_report, encoding="utf-8", newline="\n"
    )
    report_findings = verify_report_sentences(claims_markdown, ledger) + verify_report_sentences(
        case_report, ledger, supported_only=True
    )
    if report_findings:
        raise RuntimeError(f"unauthorized report sentence detected: {report_findings}")
    write_jsonl_atomic(
        reports_root / "failure_cards.jsonl",
        load_jsonl(run_root / "processed" / "failure_cards.jsonl"),
    )
    paper_fields = [
        "case_id",
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
    with (reports_root / "audited_paper_table.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=paper_fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(case_rows)
    write_json_atomic(audit_root / "claims_mismatches.json", {"count": 0, "mismatches": []})
    update_run_manifest(run_root, verdict)

    # console.log: external.phase4.claims.build_clause_audit_and_artifact_graph
    console.log(
        "external.phase4.claims.build_clause_audit_and_artifact_graph",
        run_id=args.run_id,
    )
    graph = build_artifact_graph(root, run_root, case_rows)
    phase1 = load(run_root / "reports" / "phase1_eligibility.json")
    phase3 = load(run_root / "reports" / "phase3_validation.json")
    fidelity = load(run_root / "contract" / "fidelity_report.json")
    contract = load(run_root / "contract" / "extensional_contract.json")
    contract_checks = core["contract"]["comparisons"]
    clause_checks = [
        ("system_and_source_frozen", phase1["overall_status"] == "ELIGIBLE"),
        ("cases_source_selected", core["source"]["case_count"] == len(case_rows)),
        ("history_universe_provenanced", contract_checks["U_H"]),
        ("evidence_provenanced", contract_checks["H"]),
        ("representation_provenanced", contract_checks["P_R_pre"] and contract_checks["P_R_post"]),
        ("authority_provenanced", contract_checks["Lambda_pre"] and contract_checks["Lambda_post"]),
        (
            "controller_observation_provenanced",
            contract_checks["omega_pre"] and contract_checks["omega_post"],
        ),
        ("targets_provenanced", bool(contract["Terminal"]) and bool(contract["A_Pi"])),
        ("actions_and_support_provenanced", bool(contract["Q"]) and bool(contract["Succ_plus"])),
        ("costs_provenanced", contract_checks["unit_cost"]),
        ("touch_mechanical", core["touch"]["passed"]),
        ("native_fidelity_complete", fidelity["fidelity_percent"] == 100),
        ("completions_exact", fidelity["all_completions_valid"]),
        ("all_eight_freezes", phase3["all_eight_conditions_per_group"]),
        ("unit_cost_complete", phase3["observed_allocations"] == 64),
        ("controls_complete", core["controls"]["checked"] == core["controls"]["matched"] == 10),
        ("independent_audit_complete", core["overall_pass"]),
        ("corruptions_fail_closed", corruption["detected_count"] == 12),
        ("all_cases_allocated", core["aggregation"]["allocation_bijection"]),
        (
            "claim_and_artifact_discipline",
            not claim_findings and not report_findings and not graph["unindexed_scientific_files"],
        ),
    ]
    clause_rows = [
        {
            "check_id": f"SCI-{index:02d}",
            "name": name,
            "passed": passed,
        }
        for index, (name, passed) in enumerate(clause_checks, start=1)
    ]
    clause_audit = {
        "check_count": len(clause_rows),
        "passed_count": sum(row["passed"] for row in clause_rows),
        "all_passed": all(row["passed"] for row in clause_rows),
        "checks": clause_rows,
    }
    if not clause_audit["all_passed"]:
        raise RuntimeError("one or more evidence-derived specification clauses failed")
    clause_audit["clause_audit_hash"] = canonical_json_hash(clause_audit)
    write_json_atomic(audit_root / "clause_audit.json", clause_audit)
    write_json_atomic(audit_root / "artifact_graph.json", graph)

    # console.log: external.phase4.claims.finalize_audit
    console.log("external.phase4.claims.finalize_audit", run_id=args.run_id)
    audit_gates = {
        "source_audit": gate(
            core["source"]["passed"],
            core["source"]["artifact_count"],
            core["source"]["artifact_count"] - len(core["source"]["mismatches"]),
            ["audit/source_mismatches.json"],
        ),
        "contract_audit": gate(
            core["contract"]["passed"],
            len(core["contract"]["comparisons"]),
            sum(core["contract"]["comparisons"].values()),
            ["audit/contract_mismatches.json"],
        ),
        "touch_audit": gate(
            core["touch"]["passed"],
            core["touch"]["checked"],
            core["touch"]["matched"],
            ["audit/independent_touch.parquet", "audit/touch_mismatches.json"],
        ),
        "planner_audit": gate(
            core["planner"]["passed"],
            core["planner"]["checked"],
            core["planner"]["matched"],
            ["audit/independent_results.parquet", "audit/planner_mismatches.json"],
        ),
        "aggregation_audit": gate(
            core["aggregation"]["passed"],
            core["aggregation"]["checked"],
            core["aggregation"]["matched"],
            ["audit/aggregation_mismatches.json"],
        ),
        "controls_audit": gate(
            core["controls"]["passed"],
            core["controls"]["checked"],
            core["controls"]["matched"],
            ["controls/control_results.jsonl"],
        ),
        "corruption_audit": gate(
            corruption["all_detected"],
            corruption["attack_count"],
            corruption["detected_count"],
            ["audit/corruption_report.json"],
        ),
        "claims_audit": gate(
            not claim_findings and not report_findings,
            len(ledger["claims"]),
            len(ledger["claims"]),
            ["reports/claim_ledger.json", "reports/CLAIMS.md"],
        ),
        "artifact_graph_audit": gate(
            graph["backward_traversal_passed"]
            and graph["forward_traversal_passed"]
            and not graph["unindexed_scientific_files"],
            graph["scientific_file_count"],
            graph["indexed_scientific_file_count"],
            ["audit/artifact_graph.json"],
        ),
    }
    failed_gates = sorted(name for name, value in audit_gates.items() if not value["passed"])
    audit_value = {
        "run_id": args.run_id,
        "phase": 4,
        **audit_gates,
        "findings": [{"component": name, "reason": "PHASE4_GATE_FAILED"} for name in failed_gates],
        "supported_claim_findings": len(claim_findings) + len(report_findings),
        "overall_pass": not failed_gates and clause_audit["all_passed"],
        "final_verdict": verdict,
    }
    if not audit_value["overall_pass"]:
        raise RuntimeError("final Phase-4 audit contains one or more failed gates")
    audit = {**audit_value, "audit_hash": canonical_json_hash(audit_value)}
    validate_schema(root, audit, "audit.schema.json")
    write_json_atomic(audit_root / "audit.json", audit)

    # console.log: external.phase4.claims.seal_all_artifacts
    console.log("external.phase4.claims.seal_all_artifacts", run_id=args.run_id)
    all_paths = scientific_file_paths(root, run_root)
    all_paths.extend(
        [
            audit_root / "artifact_graph.json",
            audit_root / "audit.json",
            audit_root / "clause_audit.json",
        ]
    )
    artifact_hashes = {
        path.relative_to(root).as_posix(): byte_hash(path) for path in sorted(set(all_paths))
    }
    environment = load(run_root / "manifests" / "environment_lock.json")
    phase3 = load(run_root / "PHASE3_COMPLETE")
    source = load(root / "external_source" / "source_manifest.json")
    preregistration = load(run_root / "preregistration" / "preregistration.json")
    contract_seal = load(run_root / "contract" / "CONTRACT_SEALED")
    seal_value = {
        "run_id": args.run_id,
        "phase": 4,
        "status": verdict,
        "source_manifest_hash": source["manifest_hash"],
        "preregistration_hash": preregistration["preregistration_hash"],
        "contract_hash": contract_seal["contract_hash"],
        "contract_seal_hash": contract_seal["contract_seal_hash"],
        "phase3_completion_hash": phase3["phase3_completion_hash"],
        "audit_hash": audit["audit_hash"],
        "claim_ledger_hash": ledger["ledger_hash"],
        "artifact_graph_hash": graph["artifact_graph_hash"],
        "implementation_git_sha": environment["implementation_git_sha"],
        "environment_hash": environment["environment_hash"],
        "artifact_hashes": artifact_hashes,
        "artifact_count": len(artifact_hashes),
        "all_twenty_clauses_passed": clause_audit["all_passed"],
        "cleaner_must_refuse": True,
    }
    seal = {**seal_value, "seal_hash": canonical_json_hash(seal_value)}
    write_json_atomic(run_root / "SEALED", seal)

    # console.log: external.phase4.claims.complete
    console.log(
        "external.phase4.claims.complete",
        run_id=args.run_id,
        verdict=verdict,
        claims=len(ledger["claims"]),
        indexed_files=graph["indexed_scientific_file_count"],
        seal_hash=seal["seal_hash"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
