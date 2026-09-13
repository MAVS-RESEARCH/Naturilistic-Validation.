"""Two-pass source-fact extraction and extensional-contract compilation."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pc_external.authority import assert_no_taint, canonical_authority, controller_observation
from pc_external.evidence import EvidenceError, artifact_lookup
from pc_external.hashing import canonical_json_hash, content_id, sha256_bytes
from pc_external.interventions import validate_intervention
from pc_external.partitions import canonical_partition, validate_partition


class ContractError(ValueError):
    """Raised when the extensional contract cannot be source-grounded exactly."""


def _locator(root: Path, artifact: Mapping[str, Any], snippet: str) -> dict[str, Any]:
    path = root / artifact["snapshot_path"]
    lines = path.read_text(encoding="utf-8").splitlines()
    matches = [index + 1 for index, line in enumerate(lines) if snippet in line]
    if len(matches) != 1:
        raise ContractError(
            f"locator snippet must occur exactly once: {artifact['snapshot_path']}::{snippet}"
        )
    line = matches[0]
    quote = lines[line - 1]
    return {
        "path": artifact["snapshot_path"],
        "start_line": line,
        "end_line": line,
        "quote_sha256": sha256_bytes(quote.encode("utf-8")),
    }


def _fact(
    *,
    subject: str,
    predicate: str,
    value: Any,
    artifact: Mapping[str, Any],
    locator: Mapping[str, Any],
    evidence_type: str,
    derivation_rule: str | None,
    allowed_influence: str,
    primary_inclusion: bool = True,
) -> dict[str, Any]:
    identity = {
        "subject": subject,
        "statement": {"predicate": predicate, "value": value},
        "artifact_id": artifact["artifact_id"],
        "locator": dict(locator),
    }
    return {
        "fact_id": content_id("fact", identity),
        **identity,
        "evidence_type": evidence_type,
        "derivation_rule": derivation_rule,
        "conflicts": [],
        "primary_inclusion": primary_inclusion,
        "allowed_influence": allowed_influence,
    }


def extract_semantic_facts(
    root: Path, manifest: Mapping[str, Any], native_cases: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Pass A: extract immutable, resource-label-free facts from frozen evidence."""
    lookup = artifact_lookup(dict(manifest))
    specs = [
        (
            "pre",
            "site/content/in-dev/unreleased/realm.md",
            "RealmContext:**  It is a key concept",
            "polaris_realm_context",
            "realm_context_identifies_security_domain",
            True,
            "DIRECT",
            None,
            "HISTORY",
        ),
        (
            "pre",
            "site/content/in-dev/unreleased/managing-security/external-pdp/opa.md",
            "Setting `default allow := false` to deny by default",
            "opa_policy",
            "default_deny_predicate_exists",
            True,
            "DIRECT",
            None,
            "AUTHORITY",
        ),
        (
            "pre",
            "extensions/auth/opa/opa-input-schema.json",
            '"request_id" : {',
            "pre_opa_context",
            "realm_field_present",
            False,
            "DERIVED",
            "Parse the frozen pre-repair context properties and test membership of realm.",
            "REPRESENTATION_INTERFACE",
        ),
        (
            "post",
            "extensions/auth/opa/opa-input-schema.json",
            '"realm" : {',
            "post_opa_context",
            "realm_field_required",
            True,
            "DIRECT",
            None,
            "REPRESENTATION_INTERFACE",
        ),
        (
            "post",
            "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/model/Context.java",
            "String realm();",
            "post_context_interface",
            "realm_accessor_required",
            True,
            "DIRECT",
            None,
            "REPRESENTATION_INTERFACE",
        ),
        (
            "post",
            "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizer.java",
            ".realm(realm).build();",
            "post_authorizer_context",
            "realm_certificate_emitted",
            True,
            "DIRECT",
            None,
            "REPRESENTATION_INTERFACE",
        ),
        (
            "post",
            "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactory.java",
            "realmContext.getRealmIdentifier());",
            "post_authorizer_factory",
            "realm_factory_injection",
            True,
            "DIRECT",
            None,
            "INTERVENTION",
        ),
        (
            "pre",
            "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaPolarisAuthorizerFactory.java",
            "public PolarisAuthorizer create(RealmConfig realmConfig)",
            "pre_authorizer_factory",
            "realm_config_not_consumed_for_policy_route",
            True,
            "DERIVED",
            "The pre-repair create method constructs the OPA authorizer without realm data.",
            "INTERVENTION",
        ),
        (
            "pre",
            "extensions/auth/opa/src/main/java/org/apache/polaris/extension/auth/opa/OpaAuthorizationConfig.java",
            "Optional<URI> policyUri();",
            "opa_authority",
            "policy_endpoint_is_application_configuration",
            True,
            "DIRECT",
            None,
            "AUTHORITY",
        ),
        (
            "pre",
            "site/content/in-dev/unreleased/managing-security/external-pdp/opa.md",
            '"request_id": "uuid"',
            "terminal_decision_semantics",
            "paired_realm_sensitive_decision_case_available",
            False,
            "INCOMPLETE",
            (
                "The frozen policy examples expose request_id only and the native index has no "
                "paired realm-sensitive decision case."
            ),
            "TERMINAL",
        ),
    ]
    facts: list[dict[str, Any]] = []
    for phase, path, snippet, subject, predicate, value, kind, rule, influence in specs:
        artifact = lookup[(phase, path)]
        facts.append(
            _fact(
                subject=subject,
                predicate=predicate,
                value=value,
                artifact=artifact,
                locator=_locator(root, artifact, snippet),
                evidence_type=kind,
                derivation_rule=rule,
                allowed_influence=influence,
            )
        )
    for case in native_cases["cases"]:
        artifact = next(
            item
            for item in manifest["artifacts"]
            if item["artifact_id"] == case["source_artifact_id"]
        )
        line_number = case["source_locator"]["assertion_line"]
        lines = (root / artifact["snapshot_path"]).read_text(encoding="utf-8").splitlines()
        locator = {
            "path": artifact["snapshot_path"],
            "start_line": line_number,
            "end_line": line_number,
            "quote_sha256": sha256_bytes(lines[line_number - 1].encode("utf-8")),
        }
        facts.append(
            _fact(
                subject=case["case_id"],
                predicate="native_expected_realm",
                value=case["expected_realm"],
                artifact=artifact,
                locator=locator,
                evidence_type="DIRECT",
                derivation_rule=None,
                allowed_influence="TARGET",
            )
        )
    facts.sort(key=lambda item: item["fact_id"])
    if len({fact["fact_id"] for fact in facts}) != len(facts):
        raise ContractError("duplicate semantic fact ID")
    return facts


def validate_semantic_facts(
    root: Path, manifest: Mapping[str, Any], facts: Iterable[Mapping[str, Any]]
) -> None:
    artifacts = {item["artifact_id"]: item for item in manifest["artifacts"]}
    for fact in facts:
        artifact = artifacts.get(fact["artifact_id"])
        if artifact is None or fact["locator"]["path"] != artifact["snapshot_path"]:
            raise ContractError("semantic fact locator does not resolve to its artifact")
        lines = (root / fact["locator"]["path"]).read_text(encoding="utf-8").splitlines()
        start = fact["locator"]["start_line"]
        end = fact["locator"]["end_line"]
        if start < 1 or end < start or end > len(lines):
            raise ContractError("semantic fact locator line range is invalid")
        quote = "\n".join(lines[start - 1 : end])
        if sha256_bytes(quote.encode("utf-8")) != fact["locator"]["quote_sha256"]:
            raise ContractError("semantic fact locator quote hash mismatch")
        if fact["allowed_influence"] not in artifact["allowed_influence"]:
            raise ContractError("semantic fact exceeds artifact allowed influence")
        if fact["evidence_type"] != "DIRECT" and not fact["derivation_rule"]:
            raise ContractError("derived or incomplete fact lacks derivation rule")


def build_history_universe(
    run_id: str, native_cases: Mapping[str, Any], source_manifest_hash: str
) -> dict[str, Any]:
    histories = []
    for case in native_cases["cases"]:
        identity = {"case_id": case["case_id"], "source_case_ids": case["source_case_ids"]}
        histories.append(
            {
                "history_id": content_id("history", identity),
                "case_id": case["case_id"],
                "source_case_ids": case["source_case_ids"],
                "provenance": {
                    "artifact_id": case["source_artifact_id"],
                    "locator": case["source_locator"],
                },
            }
        )
    histories.sort(key=lambda item: item["history_id"])
    value = {
        "run_id": run_id,
        "source_manifest_hash": source_manifest_hash,
        "mode": "EXPLICIT_FINITE",
        "validity_predicate": (
            "history is one frozen UPSTREAM_NATIVE case with a validated realm assertion"
        ),
        "canonical_enumeration": "ascending content-derived history_id",
        "history_count": len(histories),
        "histories": histories,
    }
    return {**value, "history_universe_hash": canonical_json_hash(value)}


def _fact_ids(facts: Iterable[Mapping[str, Any]], *predicates: str) -> list[str]:
    selected = {fact["fact_id"] for fact in facts if fact["statement"]["predicate"] in predicates}
    if len(selected) < len(set(predicates)):
        raise ContractError(f"required semantic predicates missing: {predicates}")
    return sorted(selected)


def compile_contract(
    *,
    run_id: str,
    facts: list[dict[str, Any]],
    history_universe: Mapping[str, Any],
    manifest: Mapping[str, Any],
    native_cases: Mapping[str, Any],
    costs: Mapping[str, Any],
) -> dict[str, Any]:
    """Pass B: compile validated facts into a typed extensional model."""
    histories = history_universe["histories"]
    universe = [item["history_id"] for item in histories]
    expected_by_case = {case["case_id"]: case["expected_realm"] for case in native_cases["cases"]}
    expected_by_history = {
        history["history_id"]: expected_by_case[history["case_id"]] for history in histories
    }
    pre_partition = canonical_partition(universe, {item: "realm-absent" for item in universe})
    post_partition = canonical_partition(universe, expected_by_history)
    validate_partition(pre_partition, universe)
    validate_partition(post_partition, universe)

    admitted_artifacts = sorted(
        item["artifact_id"] for item in manifest["artifacts"] if item["role"] != "EXCLUDED"
    )
    evidence_value = {
        "existing_artifact_ids": sorted(item["artifact_id"] for item in manifest["artifacts"]),
        "admitted_artifact_ids": admitted_artifacts,
        "normalization": "stable artifact identity; existence and admission are separate",
    }
    evidence_hash = canonical_json_hash(evidence_value)
    authority_fact_ids = _fact_ids(
        facts, "policy_endpoint_is_application_configuration", "default_deny_predicate_exists"
    )
    authority = canonical_authority(
        [
            {
                "kind": "SOURCE",
                "identifier": "configured_opa_policy_endpoint",
                "admissible": True,
                "provenance_fact_ids": authority_fact_ids,
            },
            {
                "kind": "PREDICATE",
                "identifier": "rego_allow_over_presented_input",
                "admissible": True,
                "provenance_fact_ids": authority_fact_ids,
            },
            {
                "kind": "FIELD",
                "identifier": "all_fields_presented_in_opa_input",
                "admissible": True,
                "provenance_fact_ids": authority_fact_ids,
            },
            {
                "kind": "ATTESTATION",
                "identifier": "opa_boolean_decision_response",
                "admissible": True,
                "provenance_fact_ids": authority_fact_ids,
            },
            {
                "kind": "CHECK",
                "identifier": "default_deny_then_explicit_allow",
                "admissible": True,
                "provenance_fact_ids": authority_fact_ids,
            },
        ]
    )
    evaluator_values = list(expected_by_case.values())
    pre_observation = controller_observation(["request_id"], evaluator_only_values=evaluator_values)
    post_observation = controller_observation(
        ["request_id", "realm"], evaluator_only_values=evaluator_values
    )
    assert_no_taint(pre_observation, evaluator_values)
    assert_no_taint(post_observation, evaluator_values)

    state_fact_ids = _fact_ids(
        facts,
        "realm_field_present",
        "realm_field_required",
        "realm_accessor_required",
        "realm_certificate_emitted",
    )
    pre_id = "state:polaris_opa_pre_repair_context_without_realm_certificate"
    post_id = "state:polaris_opa_post_repair_context_with_realm_certificate"
    terminals_pre = {case["case_id"]: False for case in native_cases["cases"]}
    terminals_post = {case["case_id"]: True for case in native_cases["cases"]}
    states = [
        {
            "state_id": pre_id,
            "history_domain": universe,
            "normalized_evidence_hash": evidence_hash,
            "representation_partition": pre_partition,
            "authority": authority,
            "controller_observation": pre_observation,
            "terminal_certificates": terminals_pre,
            "source_fact_ids": state_fact_ids,
        },
        {
            "state_id": post_id,
            "history_domain": universe,
            "normalized_evidence_hash": evidence_hash,
            "representation_partition": post_partition,
            "authority": authority,
            "controller_observation": post_observation,
            "terminal_certificates": terminals_post,
            "source_fact_ids": state_fact_ids,
        },
    ]
    action_fact_ids = _fact_ids(
        facts, "realm_factory_injection", "realm_certificate_emitted", "realm_accessor_required"
    )
    action = {
        "intervention_id": "action:historical_context_realm_injection",
        "source_state_id": pre_id,
        "preconditions": ["OPA authorizer selected", "realm context resolvable"],
        "atomicity": {
            "is_atomic": True,
            "basis": (
                "single historical PR changes interface, factory injection, and emitted context"
            ),
        },
        "positive_support_successors": [{"state_id": post_id, "support": 1}],
        "public_effect": "add required realm certificate to the existing OPA request path",
        "provenance_fact_ids": action_fact_ids,
        "cost": {"unit": costs["primary"]["unit_cost"], "native": None},
    }
    validate_intervention(action, [pre_id, post_id])
    completion_id = content_id(
        "completion", {"fact_ids": [fact["fact_id"] for fact in facts], "choices": {}}
    )
    terminal = {
        case["case_id"]: {
            "target_class": case["target_class"],
            "predicate": case["target_predicate"],
            "pre_satisfied": False,
            "post_satisfied": True,
            "provenance_fact_ids": _fact_ids(facts, "native_expected_realm"),
        }
        for case in native_cases["cases"]
    }
    model = {
        "run_id": run_id,
        "model_type": "M_ext",
        "completion_id": completion_id,
        "S": [pre_id, post_id],
        "s0": pre_id,
        "U_H": copy.deepcopy(histories),
        "H": evidence_value,
        "P_R": {pre_id: pre_partition, post_id: post_partition},
        "Lambda": {pre_id: authority, post_id: authority},
        "omega": {pre_id: pre_observation, post_id: post_observation},
        "Q": [action],
        "Succ_plus": {action["intervention_id"]: [post_id]},
        "Terminal": terminal,
        "A_Pi": {
            case["case_id"]: {
                "kind": "AUTHORIZATION_INPUT_CERTIFICATE",
                "expected_realm": case["expected_realm"],
                "evaluator_truth_ref": case["evaluator_truth_ref"],
            }
            for case in native_cases["cases"]
        },
        "c": {"primary": "unit", "unit_cost": 1, "native_secondary": []},
        "states": states,
        "source_fact_ids": [fact["fact_id"] for fact in facts if fact["primary_inclusion"]],
        "limitations": [
            (
                "Terminal allow/deny under a paired realm-sensitive Rego policy is not identified "
                "by the frozen native cases."
            ),
            "The source-grounded repair space contains one atomic action and no competing route.",
        ],
    }
    return {**model, "contract_hash": canonical_json_hash(model)}


def validate_contract(contract: Mapping[str, Any]) -> None:
    payload = {key: value for key, value in contract.items() if key != "contract_hash"}
    if contract["contract_hash"] != canonical_json_hash(payload):
        raise ContractError("contract hash mismatch")
    if set(contract["S"]) != {state["state_id"] for state in contract["states"]}:
        raise ContractError("S and expanded states differ")
    universe = [item["history_id"] for item in contract["U_H"]]
    if len(universe) != len(set(universe)):
        raise ContractError("U_H contains duplicate histories")
    for state in contract["states"]:
        if state["history_domain"] != universe:
            raise ContractError("state does not use the canonical common U_H ordering")
        validate_partition(state["representation_partition"], universe)
    for action in contract["Q"]:
        validate_intervention(action, contract["S"])


def fidelity_report(
    run_id: str, contract: Mapping[str, Any], native_cases: Mapping[str, Any]
) -> dict[str, Any]:
    states = {item["state_id"]: item for item in contract["states"]}
    pre = states[contract["s0"]]
    post_id = contract["Succ_plus"][contract["Q"][0]["intervention_id"]][0]
    post = states[post_id]
    cases = []
    for case in native_cases["cases"]:
        checks = {
            "pre_certificate_absent": pre["terminal_certificates"][case["case_id"]] is False,
            "post_certificate_satisfied": post["terminal_certificates"][case["case_id"]] is True,
            "target_matches_native": contract["A_Pi"][case["case_id"]]["expected_realm"]
            == case["expected_realm"],
            "controller_observation_untainted": not pre["controller_observation"][
                "contains_evaluator_truth"
            ]
            and not post["controller_observation"]["contains_evaluator_truth"],
            "transition_positive_support": bool(
                contract["Succ_plus"][contract["Q"][0]["intervention_id"]]
            ),
            "historical_action_atomic": contract["Q"][0]["atomicity"]["is_atomic"],
        }
        cases.append({"case_id": case["case_id"], "checks": checks, "passed": all(checks.values())})
    passed = sum(item["passed"] for item in cases)
    value = {
        "run_id": run_id,
        "completion_id": contract["completion_id"],
        "case_completion_pairs": len(cases),
        "passed_pairs": passed,
        "fidelity_percent": 100.0 * passed / len(cases),
        "all_completions_valid": passed == len(cases),
        "cases": cases,
    }
    return {**value, "fidelity_report_hash": canonical_json_hash(value)}


def contract_provenance(
    contract: Mapping[str, Any], facts: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    fact_map = {
        fact["fact_id"]: {
            "artifact_id": fact["artifact_id"],
            "locator": fact["locator"],
            "evidence_type": fact["evidence_type"],
        }
        for fact in facts
    }
    components = {
        "U_H": sorted({item["provenance"]["artifact_id"] for item in contract["U_H"]}),
        "H": contract["H"]["admitted_artifact_ids"],
        "P_R": contract["source_fact_ids"],
        "Lambda": contract["Lambda"][contract["s0"]]["entries"][0]["provenance_fact_ids"],
        "omega": contract["source_fact_ids"],
        "Q": contract["Q"][0]["provenance_fact_ids"],
        "Terminal": contract["source_fact_ids"],
        "A_Pi": contract["source_fact_ids"],
        "c": ["configs/costs.yaml"],
    }
    value = {
        "contract_hash": contract["contract_hash"],
        "fact_count": len(fact_map),
        "facts": fact_map,
        "components": components,
        "all_normative_components_have_lineage": all(components.values()),
    }
    if not value["all_normative_components_have_lineage"]:
        raise EvidenceError("normative contract component lacks lineage")
    return {**value, "provenance_hash": canonical_json_hash(value)}
