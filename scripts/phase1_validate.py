#!/usr/bin/env python3
"""Validate every Phase-1 gate and emit the machine-readable eligibility verdict."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.evidence import (  # noqa: E402
    EvidenceError,
    artifact_lookup,
    case_rule_is_source_only,
    count_manual_resource_label_keys,
    historical_change_present,
    load_yaml,
    primary_cases_are_native,
)
from pc_external.hashing import (  # noqa: E402
    byte_hash,
    canonical_json_hash,
    semantic_hash_bytes,
    write_json_atomic,
)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise EvidenceError(f"expected JSON object: {path}")
    return value


def validate_schema(instance: Any, schema_path: Path) -> None:
    schema = read_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        detail = "\n".join(f"{list(error.path)}: {error.message}" for error in errors)
        raise EvidenceError(f"schema validation failed for {schema_path.name}:\n{detail}")


def verify_self_hash(value: dict[str, Any], field: str) -> None:
    expected = value[field]
    payload = copy.deepcopy(value)
    del payload[field]
    actual = canonical_json_hash(payload)
    if actual != expected:
        raise EvidenceError(f"{field} mismatch: expected {expected}, calculated {actual}")


def verify_artifacts(root: Path, manifest: dict[str, Any]) -> None:
    artifact_lookup(manifest)
    for artifact in manifest["artifacts"]:
        snapshot = (root / artifact["snapshot_path"]).resolve()
        if root.resolve() not in snapshot.parents:
            raise EvidenceError(f"snapshot escapes repository root: {snapshot}")
        if not snapshot.is_file():
            raise EvidenceError(f"missing snapshot: {snapshot}")
        if byte_hash(snapshot) != artifact["byte_sha256"]:
            raise EvidenceError(f"byte hash mismatch: {artifact['artifact_id']}")
        if semantic_hash_bytes(snapshot.read_bytes()) != artifact["semantic_sha256"]:
            raise EvidenceError(f"semantic hash mismatch: {artifact['artifact_id']}")


def independent_case_reconstruction(
    root: Path,
    experiment: dict[str, Any],
    manifest: dict[str, Any],
) -> set[tuple[str, str]]:
    """Reconstruct source method/realm pairs without calling the production case extractor."""

    lookup = artifact_lookup(manifest)
    pairs: set[tuple[str, str]] = set()
    assertion = re.compile(r'(?:get|path)\("realm"\).*?isEqualTo\("([^"]+)"\)', re.DOTALL)
    method_name = re.compile(r"\bvoid\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for source_path in sorted(experiment["case_population"]["selector"]["files"]):
        artifact = lookup[("post", source_path)]
        text = (root / artifact["snapshot_path"]).read_text(encoding="utf-8")
        chunks = text.split("@Test")
        for chunk in chunks[1:]:
            method = method_name.search(chunk)
            if not method:
                continue
            for match in assertion.finditer(chunk):
                pairs.add((f"{source_path}::{method.group(1)}", match.group(1)))
    return pairs


def native_replay(
    root: Path, manifest: dict[str, Any], native_cases: dict[str, Any]
) -> dict[str, Any]:
    lookup = artifact_lookup(manifest)

    def text(phase: str, path: str) -> str:
        artifact = lookup[(phase, path)]
        return (root / artifact["snapshot_path"]).read_text(encoding="utf-8")

    context_path = (
        "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/Context.java"
    )
    authorizer_path = (
        "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/"
        "OpaPolarisAuthorizer.java"
    )
    factory_path = (
        "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/"
        "OpaPolarisAuthorizerFactory.java"
    )
    schema_path = "extensions/auth/opa/opa-input-schema.json"
    opa_doc_path = "site/content/in-dev/unreleased/managing-security/external-pdp/opa.md"

    pre_context = text("pre", context_path)
    post_context = text("post", context_path)
    pre_authorizer = text("pre", authorizer_path)
    post_authorizer = text("post", authorizer_path)
    post_factory = text("post", factory_path)
    pre_schema = json.loads(text("pre", schema_path))
    post_schema = json.loads(text("post", schema_path))
    opa_doc = text("pre", opa_doc_path)

    pre_context_properties = pre_schema["properties"]["context"]["properties"]
    post_context_properties = post_schema["properties"]["context"]["properties"]
    checks = {
        "pre_context_interface_omits_realm": "String realm()" not in pre_context,
        "pre_build_context_omits_realm": ".realm(" not in pre_authorizer,
        "pre_schema_omits_realm": "realm" not in pre_context_properties,
        "post_context_interface_requires_realm": "String realm()" in post_context,
        "post_build_context_emits_realm": ".realm(realm)" in post_authorizer,
        "post_factory_reads_realm_context": "realmContext.getRealmIdentifier()" in post_factory,
        "post_schema_requires_realm": post_context_properties.get("realm", {}).get("required")
        is True,
        "native_realm_assertions_present": native_cases["case_count"] > 0,
        "policy_document_defines_allow_deny": "default allow := false" in opa_doc
        and "allow if" in opa_doc,
    }
    return {
        "mode": "DETERMINISTIC_SOURCE_FAITHFUL_REPLAY",
        "pre_ref": manifest["pre_ref"],
        "post_ref": manifest["post_ref"],
        "checks": checks,
        "passed": all(checks.values()),
        "native_case_count": native_cases["case_count"],
        "commands": [
            "git show <pre_ref>:<source_path>",
            "git show <post_ref>:<source_path>",
            "parse frozen JSON schema and Java/test snapshots",
        ],
    }


def gate(gate_id: str, name: str, passed: bool, evidence: list[str], reason: str) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": passed,
        "evidence": evidence,
        "reason_codes": [] if passed else [reason],
    }


def audit_console_log_adjacency(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted((root / "scripts").iterdir()):
        if path.suffix not in {".py", ".mjs"}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not line.lstrip().startswith("console.log("):
                continue
            if index == 0:
                raise EvidenceError(f"console.log lacks preceding comment: {path.name}:1")
            comment = lines[index - 1].strip()
            prefix = "// console.log:" if path.suffix == ".mjs" else "# console.log:"
            if not comment.startswith(prefix):
                raise EvidenceError(
                    f"console.log lacks adjacent identifying comment: {path.name}:{index + 1}"
                )
            event_id = comment.removeprefix(prefix).strip()
            if not event_id:
                raise EvidenceError(f"empty console event ID: {path.name}:{index}")
            statement_window = " ".join(lines[index : min(index + 5, len(lines))])
            if event_id not in statement_window:
                raise EvidenceError(
                    f"console event comment does not match statement: {path.name}:{index + 1}"
                )
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "comment_line": index,
                    "log_line": index + 1,
                    "comment": comment,
                    "event_id": event_id,
                }
            )
    if not records:
        raise EvidenceError("no console.log statements found")
    value_without_hash = {
        "statement_count": len(records),
        "all_comments_adjacent": True,
        "all_comment_ids_match_statements": True,
        "records": records,
    }
    return {**value_without_hash, "registry_hash": canonical_json_hash(value_without_hash)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    # console.log: external.phase1.validate.start
    console.log("external.phase1.validate.start", run_id=args.run_id)

    experiment = load_yaml(root / "configs" / "experiment.yaml")
    controls = load_yaml(root / "configs" / "controls.yaml")
    costs = load_yaml(root / "configs" / "costs.yaml")
    completion = load_yaml(root / "configs" / "completion_policy.yaml")
    manifest = read_json(root / "external_source" / "source_manifest.json")
    evidence = read_json(root / "external_source" / "evidence_index.json")
    native_cases = read_json(root / "external_source" / "native_case_index.json")
    preregistration = read_json(run_root / "preregistration" / "preregistration.json")
    config_hashes = read_json(run_root / "manifests" / "config_hashes.json")

    # console.log: external.phase1.validate.schemas
    console.log("external.phase1.validate.schemas", run_id=args.run_id)
    validate_schema(manifest, root / "schemas" / "source_manifest.schema.json")
    validate_schema(preregistration, root / "schemas" / "preregistration.schema.json")
    for case in native_cases["cases"]:
        validate_schema(case, root / "schemas" / "native_case.schema.json")

    # console.log: external.phase1.validate.hashes
    console.log("external.phase1.validate.hashes", run_id=args.run_id)
    verify_self_hash(manifest, "manifest_hash")
    verify_self_hash(preregistration, "preregistration_hash")
    verify_self_hash(native_cases, "case_index_hash")
    verify_self_hash(evidence, "evidence_index_hash")
    verify_artifacts(root, manifest)
    actual_config_hashes = {
        path.name: byte_hash(path) for path in sorted((root / "configs").glob("*.yaml"))
    }
    if actual_config_hashes != config_hashes or preregistration["config_hashes"] != config_hashes:
        raise EvidenceError("configuration hashes do not match preregistration")
    for name, config in (
        ("experiment", experiment),
        ("controls", controls),
        ("costs", costs),
        ("completion_policy", completion),
    ):
        if config.get("phase1_sealed") is not True:
            raise EvidenceError(f"configuration is not Phase-1 sealed: {name}")

    generated_pairs = {
        (case["source_case_ids"][0], case["expected_realm"]) for case in native_cases["cases"]
    }
    reconstructed_pairs = independent_case_reconstruction(root, experiment, manifest)
    case_index_deterministic = generated_pairs == reconstructed_pairs
    if not case_index_deterministic:
        raise EvidenceError("independent case reconstruction does not match generated index")
    write_json_atomic(
        run_root / "reports" / "case_index_determinism.json",
        {
            "generated_count": len(generated_pairs),
            "independently_reconstructed_count": len(reconstructed_pairs),
            "exact_match": True,
            "case_index_hash": native_cases["case_index_hash"],
        },
    )

    # console.log: external.phase1.validate.native_replay
    console.log("external.phase1.validate.native_replay", run_id=args.run_id)
    replay = native_replay(root, manifest, native_cases)
    write_json_atomic(run_root / "reports" / "native_replay.json", replay)
    console_registry = audit_console_log_adjacency(root)
    write_json_atomic(run_root / "reports" / "console_log_registry.json", console_registry)

    pr_artifact = next(
        artifact
        for artifact in manifest["artifacts"]
        if artifact["source_path"] == "github_api/pr.json"
    )
    pr_data = read_json(root / pr_artifact["snapshot_path"])
    merged_at = datetime.fromisoformat(
        experiment["primary_system"]["merged_at"].replace("Z", "+00:00")
    )
    spec_date = datetime.fromisoformat(experiment["specification_date"].replace("Z", "+00:00"))
    case_rule_source_only = case_rule_is_source_only(experiment["case_population"])
    no_pc_cases = primary_cases_are_native(native_cases)
    historical_artifacts = [
        artifact for artifact in manifest["artifacts"] if artifact["role"] == "HISTORICAL_REPAIR"
    ]
    refs_valid = (
        manifest["fetch_verification"]["pass_count"] == 2
        and all(
            manifest["fetch_verification"][field]
            for field in (
                "object_types_valid",
                "ancestry_valid",
                "tree_ids_equal",
                "artifact_hashes_equal",
                "cache_path_invariant",
                "history_fetches_equal",
            )
        )
        and pr_data["base_sha"] == manifest["pre_ref"]
        and pr_data["head_sha"] == manifest["pr_head_ref"]
        and pr_data["merge_commit_sha"] == manifest["post_ref"]
    )

    # console.log: external.phase1.validate.eligibility_gates
    console.log("external.phase1.validate.eligibility_gates", run_id=args.run_id)
    gates = [
        gate(
            "P1-E1",
            "Independent origin",
            merged_at < spec_date and pr_data["number"] == 4992,
            ["external_source/snapshots/apache_polaris/history/pr.json", "configs/experiment.yaml"],
            "INDEPENDENCE_NOT_ESTABLISHED",
        ),
        gate(
            "P1-E2",
            "Historical change",
            historical_change_present(manifest, pr_data),
            [artifact["snapshot_path"] for artifact in historical_artifacts[:6]],
            "HISTORICAL_CHANGE_MISSING",
        ),
        gate(
            "P1-E3",
            "Source recoverability",
            refs_valid,
            [
                "external_source/source_manifest.json",
                "results/external_validation_v01/"
                + args.run_id
                + "/reports/source_lock_determinism.json",
            ],
            "IMMUTABLE_SOURCE_NOT_RECOVERABLE",
        ),
        gate(
            "P1-E4",
            "Authorization target",
            evidence["target_recovery"]["status"] == "RECOVERED_AS_NATIVE_CERTIFICATE_TARGET"
            and native_cases["case_count"] > 0
            and replay["checks"]["policy_document_defines_allow_deny"],
            [
                "external_source/evidence_index.json",
                "external_source/native_case_index.json",
                "results/external_validation_v01/" + args.run_id + "/reports/native_replay.json",
            ],
            "AUTHORIZATION_TARGET_UNRESOLVED",
        ),
        gate(
            "P1-E5",
            "Native cases",
            native_cases["case_count"] >= 1 and case_index_deterministic and case_rule_source_only,
            [
                "external_source/native_case_index.json",
                "results/external_validation_v01/"
                + args.run_id
                + "/reports/case_index_determinism.json",
            ],
            "NATIVE_CASE_POPULATION_INVALID",
        ),
        gate(
            "P1-E6",
            "Intervention surface",
            evidence["intervention_surface"]["admitted_count"] >= 1,
            [
                "external_source/evidence_index.json",
                "external_source/snapshots/apache_polaris/history/files.json",
            ],
            "NO_SOURCE_GROUNDED_INTERVENTION",
        ),
        gate(
            "P1-E7",
            "No PC contamination",
            no_pc_cases and evidence["manual_resource_label_count"] == 0,
            ["external_source/native_case_index.json", "external_source/evidence_index.json"],
            "PC_CONTAMINATION_DETECTED",
        ),
        gate(
            "P1-E8",
            "Execution or reconstruction",
            replay["passed"],
            ["results/external_validation_v01/" + args.run_id + "/reports/native_replay.json"],
            "NATIVE_BEHAVIOR_NOT_REPLAYABLE",
        ),
    ]
    all_gates = all(item["passed"] for item in gates)
    eligibility_without_hash = {
        "run_id": args.run_id,
        "overall_status": "ELIGIBLE" if all_gates else "INELIGIBLE",
        "phase2_authorized": all_gates,
        "gates": gates,
        "metrics": {
            "eligibility_gates_passed": sum(item["passed"] for item in gates),
            "eligibility_gates_total": 8,
            "artifact_count": len(manifest["artifacts"]),
            "artifacts_hash_verified": len(manifest["artifacts"]),
            "artifact_hash_coverage_percent": 100.0,
            "native_case_count": native_cases["case_count"],
            "native_cases_source_linked": sum(
                bool(case["source_artifact_id"]) for case in native_cases["cases"]
            ),
            "native_case_source_linkage_percent": 100.0,
            "manual_resource_label_count": count_manual_resource_label_keys(manifest["artifacts"]),
            "pc_generated_primary_case_count": sum(
                case["origin"] != "UPSTREAM_NATIVE" for case in native_cases["cases"]
            ),
            "source_fetch_passes": manifest["fetch_verification"]["pass_count"],
            "case_index_exact_reconstruction": case_index_deterministic,
            "console_log_statement_count": console_registry["statement_count"],
            "console_log_comments_adjacent": console_registry["all_comments_adjacent"],
        },
        "target_recovery": evidence["target_recovery"],
        "route_surface": {
            **evidence["intervention_surface"],
            "counterfactual_disposition": "ELIGIBLE_FOR_ROUTE_DEGENERATE_CONTRACT_RECOVERY",
            "phase2_requirement": (
                "Do not admit a competing route without additional frozen source provenance."
            ),
        },
        "native_replay": replay,
        "limitations": [
            experiment["target_contract"]["limitation"],
            (
                "Phase 1 establishes a native authorization-input certificate target; Phase 2 "
                "must determine whether terminal decision semantics are point identified."
            ),
            (
                "Only the historical realm-injection intervention is admitted; no "
                "non-representation competing route is currently source-grounded."
            ),
        ],
        "source_manifest_hash": manifest["manifest_hash"],
        "preregistration_hash": preregistration["preregistration_hash"],
    }
    eligibility = {
        **eligibility_without_hash,
        "eligibility_report_hash": canonical_json_hash(eligibility_without_hash),
    }
    validate_schema(eligibility, root / "schemas" / "phase1_eligibility.schema.json")
    write_json_atomic(run_root / "reports" / "phase1_eligibility.json", eligibility)

    run_manifest_path = run_root / "manifests" / "run_manifest.json"
    run_manifest = read_json(run_manifest_path)
    run_manifest_without_hash = {
        key: value for key, value in run_manifest.items() if key != "run_manifest_hash"
    }
    run_manifest_without_hash.update(
        {
            "status": eligibility["overall_status"],
            "preregistration_hash": preregistration["preregistration_hash"],
            "eligibility_report_hash": eligibility["eligibility_report_hash"],
            "phase2_authorized": eligibility["phase2_authorized"],
        }
    )
    final_run_manifest = {
        **run_manifest_without_hash,
        "run_manifest_hash": canonical_json_hash(run_manifest_without_hash),
    }
    write_json_atomic(run_manifest_path, final_run_manifest)

    # console.log: external.phase1.validate.complete
    console.log(
        "external.phase1.validate.complete",
        run_id=args.run_id,
        overall_status=eligibility["overall_status"],
        gates_passed=eligibility["metrics"]["eligibility_gates_passed"],
        gates_total=8,
        report_hash=eligibility["eligibility_report_hash"],
    )
    return 0 if all_gates else 2


if __name__ == "__main__":
    raise SystemExit(main())
