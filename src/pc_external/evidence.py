"""Phase-1 evidence indexing, native-case extraction, and preregistration."""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from pc_external.hashing import canonical_json_hash, content_id, semantic_hash_bytes

IMMUTABLE_GIT_REF = re.compile(r"^[0-9a-f]{40}$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
TEST_METHOD = re.compile(
    r"@Test\s+(?:(?:public|protected|private)\s+)?void\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)[^{]*\{",
    re.MULTILINE,
)
FORBIDDEN_MANUAL_LABEL_KEYS = {"resource_touch", "resource_touches", "touch", "touch_mask"}
FORBIDDEN_CASE_SELECTION_TERMS = (
    "results/",
    "delta_r",
    "k_pi",
    "touch_records",
    "freeze_result",
)


class EvidenceError(RuntimeError):
    """Raised when Phase-1 evidence violates the frozen protocol."""


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise EvidenceError(f"configuration must be a mapping: {path}")
    return value


def require_immutable_ref(value: str, field: str) -> None:
    if not IMMUTABLE_GIT_REF.fullmatch(value):
        raise EvidenceError(f"{field} must be a full 40-character lowercase Git SHA")


def require_run_id(value: str) -> None:
    if not RUN_ID.fullmatch(value):
        raise EvidenceError("run_id contains unsupported characters")


def artifact_lookup(manifest: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    ids: set[str] = set()
    for artifact in manifest["artifacts"]:
        artifact_id = artifact["artifact_id"]
        if artifact_id in ids:
            raise EvidenceError(f"duplicate artifact_id: {artifact_id}")
        ids.add(artifact_id)
        key = (artifact["phase"], artifact["source_path"])
        if key in lookup:
            raise EvidenceError(f"duplicate phase/source_path: {key}")
        lookup[key] = artifact
    return lookup


def _assertion_matches(method_text: str, assertion_regex: str) -> Iterable[re.Match[str]]:
    return re.finditer(assertion_regex, method_text, re.DOTALL)


def extract_native_cases(
    *,
    run_id: str,
    experiment: dict[str, Any],
    manifest: dict[str, Any],
    repository_root: Path,
) -> dict[str, Any]:
    """Apply the preregistered source-only selector to byte-exact post-repair snapshots."""

    require_run_id(run_id)
    selector = experiment["case_population"]["selector"]
    assertion_regex = selector["assertion_regex"]
    lookup = artifact_lookup(manifest)
    cases: list[dict[str, Any]] = []

    for source_path in sorted(selector["files"]):
        artifact = lookup.get(("post", source_path))
        if artifact is None:
            raise EvidenceError(f"selector path is not a post-repair artifact: {source_path}")
        snapshot = repository_root / artifact["snapshot_path"]
        text = snapshot.read_text(encoding="utf-8")
        methods = list(TEST_METHOD.finditer(text))
        for index, method in enumerate(methods):
            segment_end = methods[index + 1].start() if index + 1 < len(methods) else len(text)
            segment = text[method.start() : segment_end]
            for assertion in _assertion_matches(segment, assertion_regex):
                expected_realm = assertion.group(1)
                method_name = method.group("name")
                method_line = text.count("\n", 0, method.start()) + 1
                assertion_offset = method.start() + assertion.start()
                assertion_line = text.count("\n", 0, assertion_offset) + 1
                identity = {
                    "source_path": source_path,
                    "method": method_name,
                    "expected_realm": expected_realm,
                    "assertion_line": assertion_line,
                }
                cases.append(
                    {
                        "case_id": content_id("case", identity),
                        "source_case_ids": [f"{source_path}::{method_name}"],
                        "source_artifact_id": artifact["artifact_id"],
                        "source_locator": {
                            "path": source_path,
                            "method": method_name,
                            "method_line": method_line,
                            "assertion_line": assertion_line,
                        },
                        "origin": "UPSTREAM_NATIVE",
                        "initial_state_id": (
                            "polaris_opa_pre_repair_context_without_realm_certificate"
                        ),
                        "target_class": "AUTHORIZATION_INPUT_CERTIFICATE",
                        "target_predicate": (
                            "input.context.realm == injected RealmContext identifier"
                        ),
                        "expected_realm": expected_realm,
                        "relevance_proof": (
                            "The upstream test directly asserts equality on input.context.realm "
                            "in a file changed by apache/polaris#4992."
                        ),
                        "route_class": "UNCLASSIFIED_PHASE2",
                        "evaluator_truth_ref": (f"{artifact['artifact_id']}#L{assertion_line}"),
                    }
                )

    cases.sort(key=lambda item: item["case_id"])
    if not cases:
        raise EvidenceError("native case rule selected zero source cases")
    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise EvidenceError("native case selector produced duplicate case IDs")

    index_without_hash = {
        "run_id": run_id,
        "rule_id": experiment["case_population"]["rule_id"],
        "rule_description": experiment["case_population"]["description"],
        "source_manifest_hash": manifest["manifest_hash"],
        "case_count": len(cases),
        "distinct_expected_realms": sorted({case["expected_realm"] for case in cases}),
        "cases": cases,
    }
    return {**index_without_hash, "case_index_hash": canonical_json_hash(index_without_hash)}


def build_evidence_index(
    *,
    run_id: str,
    experiment: dict[str, Any],
    manifest: dict[str, Any],
    native_case_index: dict[str, Any],
) -> dict[str, Any]:
    role_counts = Counter(artifact["role"] for artifact in manifest["artifacts"])
    admitted = copy.deepcopy(experiment["intervention_surface"]["admitted"])
    excluded = copy.deepcopy(experiment["intervention_surface"]["excluded_candidates"])
    value_without_hash = {
        "run_id": run_id,
        "source_manifest_hash": manifest["manifest_hash"],
        "artifact_role_counts": dict(sorted(role_counts.items())),
        "artifact_ids": sorted(artifact["artifact_id"] for artifact in manifest["artifacts"]),
        "target_recovery": {
            "status": "RECOVERED_AS_NATIVE_CERTIFICATE_TARGET",
            "kind": experiment["target_contract"]["kind"],
            "predicate": experiment["target_contract"]["predicate"],
            "terminal_evidence": experiment["target_contract"]["terminal_evidence"],
            "limitation": experiment["target_contract"]["limitation"],
            "native_case_count": native_case_index["case_count"],
            "distinct_expected_realms": native_case_index["distinct_expected_realms"],
        },
        "intervention_surface": {
            "admitted": admitted,
            "excluded_candidates": excluded,
            "admitted_count": len(admitted),
            "competing_route_count": 0,
            "planning_classification": "ROUTE_DEGENERATE_PENDING_PHASE2",
        },
        "manual_resource_label_count": count_manual_resource_label_keys(manifest["artifacts"]),
    }
    return {**value_without_hash, "evidence_index_hash": canonical_json_hash(value_without_hash)}


def count_manual_resource_label_keys(value: Any) -> int:
    count = 0
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_MANUAL_LABEL_KEYS:
                count += 1
            count += count_manual_resource_label_keys(child)
    elif isinstance(value, list):
        count += sum(count_manual_resource_label_keys(child) for child in value)
    return count


def case_rule_is_source_only(case_population: dict[str, Any]) -> bool:
    """Reject case-selection rules that depend on downstream result information."""
    serialized = json.dumps(case_population, sort_keys=True).lower()
    return not any(term in serialized for term in FORBIDDEN_CASE_SELECTION_TERMS)


def historical_change_present(
    manifest: dict[str, Any], pr_data: dict[str, Any], minimum_artifacts: int = 6
) -> bool:
    """Require a merged historical change and its minimum frozen evidence set."""
    historical = [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("role") == "HISTORICAL_REPAIR"
    ]
    return (
        len(historical) >= minimum_artifacts
        and pr_data.get("state") == "closed"
        and pr_data.get("merged_at") is not None
    )


def primary_cases_are_native(native_case_index: dict[str, Any]) -> bool:
    """Reject any Phase-1 primary case synthesized by the PC implementation."""
    return all(
        case.get("origin") == "UPSTREAM_NATIVE" for case in native_case_index.get("cases", [])
    )


def build_preregistration(
    *,
    run_id: str,
    experiment: dict[str, Any],
    costs: dict[str, Any],
    completion_policy: dict[str, Any],
    manifest: dict[str, Any],
    config_hashes: dict[str, str],
) -> dict[str, Any]:
    value_without_hash = {
        "run_id": run_id,
        "primary_system_id": experiment["primary_system"]["id"],
        "pre_repair_ref": experiment["primary_system"]["pre_repair_ref"],
        "post_repair_ref": experiment["primary_system"]["post_repair_ref"],
        "historical_change_id": experiment["primary_system"]["historical_change_id"],
        "native_case_rule": copy.deepcopy(experiment["case_population"]),
        "resource_question": (
            "Compute K_Pi over all eight E/R/A freeze sets with Delta_R as the primary coordinate."
        ),
        "freeze_sets": copy.deepcopy(experiment["freeze_sets"]),
        "primary_cost": copy.deepcopy(costs["primary"]),
        "secondary_costs": copy.deepcopy(costs["secondary"]),
        "completion_policy": copy.deepcopy(completion_policy),
        "positive_claim_rule": (
            "Positive only if point identified or sign-positive for every admissible completion."
        ),
        "route_degeneracy_rule": copy.deepcopy(completion_policy["route_degeneracy_rule"]),
        "nonclaims": copy.deepcopy(experiment["claims"]),
        "stop_conditions": copy.deepcopy(experiment["stop_conditions"]),
        "source_manifest_hash": manifest["manifest_hash"],
        "config_hashes": dict(sorted(config_hashes.items())),
        "sealed_before_phase2": True,
    }
    return {
        **value_without_hash,
        "preregistration_hash": canonical_json_hash(value_without_hash),
    }


def artifact_semantic_hash(path: Path) -> str:
    return semantic_hash_bytes(path.read_bytes())
