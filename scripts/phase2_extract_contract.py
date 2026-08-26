#!/usr/bin/env python3
"""Extract validated Phase-2 semantic facts and the common history universe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.contract import (  # noqa: E402
    build_history_universe,
    extract_semantic_facts,
    validate_semantic_facts,
)
from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import write_json_atomic, write_jsonl_atomic  # noqa: E402
from scripts.phase1_validate import verify_artifacts, verify_self_hash  # noqa: E402


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    # console.log: external.phase2.extract_contract.start
    console.log("external.phase2.extract_contract.start", run_id=args.run_id)

    # console.log: external.phase2.extract_contract.verify_phase1_seal
    console.log("external.phase2.extract_contract.verify_phase1_seal", run_id=args.run_id)
    manifest = read_json(root / "external_source" / "source_manifest.json")
    native_cases = read_json(root / "external_source" / "native_case_index.json")
    phase1 = read_json(run_root / "reports" / "phase1_eligibility.json")
    run_manifest = read_json(run_root / "manifests" / "run_manifest.json")
    verify_self_hash(manifest, "manifest_hash")
    verify_self_hash(native_cases, "case_index_hash")
    verify_self_hash(phase1, "eligibility_report_hash")
    verify_artifacts(root, manifest)
    if phase1["overall_status"] != "ELIGIBLE" or not phase1["phase2_authorized"]:
        raise RuntimeError("Phase 1 does not authorize Phase 2")
    if run_manifest["source_manifest_hash"] != manifest["manifest_hash"]:
        raise RuntimeError("run manifest is not bound to the frozen source manifest")

    # console.log: external.phase2.extract_contract.extract_semantic_facts
    console.log("external.phase2.extract_contract.extract_semantic_facts", run_id=args.run_id)
    facts = extract_semantic_facts(root, manifest, native_cases)

    # console.log: external.phase2.extract_contract.validate_fact_lineage
    console.log("external.phase2.extract_contract.validate_fact_lineage", run_id=args.run_id)
    validate_semantic_facts(root, manifest, facts)
    history_universe = build_history_universe(args.run_id, native_cases, manifest["manifest_hash"])
    write_jsonl_atomic(contract_root / "semantic_facts.jsonl", facts)
    write_json_atomic(contract_root / "history_universe.json", history_universe)

    # console.log: external.phase2.extract_contract.complete
    console.log(
        "external.phase2.extract_contract.complete",
        run_id=args.run_id,
        fact_count=len(facts),
        history_count=history_universe["history_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
