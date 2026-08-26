#!/usr/bin/env python3
"""Compile and validate the exact Phase-2 extensional contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.completions import enumerate_completions  # noqa: E402
from pc_external.contract import (  # noqa: E402
    compile_contract,
    contract_provenance,
    fidelity_report,
    validate_contract,
    validate_semantic_facts,
)
from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import canonical_json_hash, write_json_atomic  # noqa: E402
from pc_external.interventions import classify_route  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def schema_registry(root: Path) -> Registry:
    resources = []
    for path in sorted((root / "schemas").glob("*.schema.json")):
        schema = read_json(path)
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def validate_schema(root: Path, value: Any, name: str) -> None:
    schema = read_json(root / "schemas" / name)
    Draft202012Validator(schema, registry=schema_registry(root)).validate(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    contract_root = root / "results" / "external_validation_v01" / args.run_id / "contract"
    # console.log: external.phase2.validate_contract.start
    console.log("external.phase2.validate_contract.start", run_id=args.run_id)
    manifest = read_json(root / "external_source" / "source_manifest.json")
    native_cases = read_json(root / "external_source" / "native_case_index.json")
    history = read_json(contract_root / "history_universe.json")
    facts = read_jsonl(contract_root / "semantic_facts.jsonl")
    costs = yaml.safe_load((root / "configs" / "costs.yaml").read_text(encoding="utf-8"))
    completion_policy = yaml.safe_load(
        (root / "configs" / "completion_policy.yaml").read_text(encoding="utf-8")
    )

    # console.log: external.phase2.validate_contract.validate_facts
    console.log("external.phase2.validate_contract.validate_facts", run_id=args.run_id)
    for fact in facts:
        validate_schema(root, fact, "semantic_fact.schema.json")
    validate_semantic_facts(root, manifest, facts)
    if history["history_count"] != native_cases["case_count"]:
        raise RuntimeError("common history universe does not cover every frozen native case")

    # console.log: external.phase2.validate_contract.compile_m_ext
    console.log("external.phase2.validate_contract.compile_m_ext", run_id=args.run_id)
    contract = compile_contract(
        run_id=args.run_id,
        facts=facts,
        history_universe=history,
        manifest=manifest,
        native_cases=native_cases,
        costs=costs,
    )
    validate_contract(contract)
    validate_schema(root, contract, "extensional_contract.schema.json")
    for state in contract["states"]:
        validate_schema(root, state, "state.schema.json")
    for action in contract["Q"]:
        validate_schema(root, action, "intervention.schema.json")

    # console.log: external.phase2.validate_contract.enumerate_completions
    console.log("external.phase2.validate_contract.enumerate_completions", run_id=args.run_id)
    completion_set = enumerate_completions(
        contract,
        [],
        lambda base, choices: dict(base),
        cap=completion_policy["exact_enumeration_cap"],
    )
    if completion_set["completions"][0]["contract_hash"] != contract["contract_hash"]:
        raise RuntimeError("completion set is not bound to the compiled contract")
    validate_schema(root, completion_set, "completion_set.schema.json")

    # console.log: external.phase2.validate_contract.fidelity_and_route
    console.log("external.phase2.validate_contract.fidelity_and_route", run_id=args.run_id)
    fidelity = fidelity_report(args.run_id, contract, native_cases)
    if not fidelity["all_completions_valid"]:
        raise RuntimeError("native fidelity failed")
    route_class = classify_route(contract["Q"])
    route = {
        "run_id": args.run_id,
        "classified_before_freeze_results": True,
        "case_count": native_cases["case_count"],
        "classification_counts": {route_class: native_cases["case_count"]},
        "cases": [
            {
                "case_id": case["case_id"],
                "route_class": route_class,
                "admitted_action_ids": [action["intervention_id"] for action in contract["Q"]],
                "basis": "exactly one source-grounded historical action",
            }
            for case in native_cases["cases"]
        ],
    }
    route["route_classification_hash"] = canonical_json_hash(route)
    provenance = contract_provenance(contract, facts)
    provenance["completion_analysis"] = {
        "source_grounded_dimensions": [],
        "excluded_incomplete_facts": [
            {
                "fact_id": fact["fact_id"],
                "reason": (
                    "outside the declared certificate target; retained as terminal-decision "
                    "limitation"
                ),
            }
            for fact in facts
            if fact["evidence_type"] == "INCOMPLETE"
        ],
        "author_priors_used": False,
    }
    provenance_without_hash = {
        key: value for key, value in provenance.items() if key != "provenance_hash"
    }
    provenance["provenance_hash"] = canonical_json_hash(provenance_without_hash)
    write_json_atomic(contract_root / "extensional_contract.json", contract)
    write_json_atomic(contract_root / "completion_set.json", completion_set)
    write_json_atomic(contract_root / "contract_provenance.json", provenance)
    write_json_atomic(contract_root / "route_classification.json", route)
    write_json_atomic(contract_root / "fidelity_report.json", fidelity)

    # console.log: external.phase2.validate_contract.complete
    console.log(
        "external.phase2.validate_contract.complete",
        run_id=args.run_id,
        status=completion_set["status"],
        state_count=len(contract["S"]),
        completion_count=completion_set["completion_count"],
        fidelity_percent=fidelity["fidelity_percent"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
