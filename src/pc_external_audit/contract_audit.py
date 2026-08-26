"""Independent reconstruction of the finite extensional semantic components."""

from __future__ import annotations

import hashlib
import itertools
import json
from typing import Any

from pc_external_audit.source_audit import object_hash


def stable_id(namespace: str, value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return f"{namespace}:{hashlib.sha256(payload).hexdigest()[:20]}"


def canonical_partition(domain: list[str], labels: dict[str, str]) -> dict[str, Any]:
    groups: dict[str, list[str]] = {}
    for item in domain:
        groups.setdefault(labels[item], []).append(item)
    blocks = sorted((sorted(block) for block in groups.values()), key=lambda block: tuple(block))
    value = {"history_domain": domain, "blocks": blocks}
    return {**value, "partition_hash": object_hash(value)}


def validate_partition(partition: dict[str, Any], universe: list[str]) -> bool:
    flattened = list(itertools.chain.from_iterable(partition["blocks"]))
    value = {"history_domain": partition["history_domain"], "blocks": partition["blocks"]}
    return (
        partition["history_domain"] == universe
        and sorted(flattened) == sorted(universe)
        and len(flattened) == len(set(flattened))
        and partition["partition_hash"] == object_hash(value)
    )


def reconstruct_contract_components(
    native_index: dict[str, Any], manifest: dict[str, Any], facts: list[dict[str, Any]]
) -> dict[str, Any]:
    histories = []
    for case in native_index["cases"]:
        identity = {"case_id": case["case_id"], "source_case_ids": case["source_case_ids"]}
        histories.append(
            {
                "history_id": stable_id("history", identity),
                "case_id": case["case_id"],
                "source_case_ids": case["source_case_ids"],
                "provenance": {
                    "artifact_id": case["source_artifact_id"],
                    "locator": case["source_locator"],
                },
            }
        )
    histories.sort(key=lambda item: item["history_id"])
    universe = [item["history_id"] for item in histories]
    realm_by_case = {case["case_id"]: case["expected_realm"] for case in native_index["cases"]}
    realm_by_history = {item["history_id"]: realm_by_case[item["case_id"]] for item in histories}
    pre = canonical_partition(universe, {history: "absent" for history in universe})
    post = canonical_partition(universe, realm_by_history)
    authority_fact_ids = sorted(
        fact["fact_id"]
        for fact in facts
        if fact["statement"]["predicate"]
        in {"policy_endpoint_is_application_configuration", "default_deny_predicate_exists"}
    )
    authority_entries = sorted(
        [
            {
                "kind": kind,
                "identifier": identifier,
                "admissible": True,
                "provenance_fact_ids": authority_fact_ids,
            }
            for kind, identifier in (
                ("SOURCE", "configured_opa_policy_endpoint"),
                ("FIELD", "all_fields_presented_in_opa_input"),
                ("PREDICATE", "rego_allow_over_presented_input"),
                ("ATTESTATION", "opa_boolean_decision_response"),
                ("CHECK", "default_deny_then_explicit_allow"),
            )
        ],
        key=lambda item: (item["kind"], item["identifier"]),
    )
    authority_value = {"entries": authority_entries}
    authority = {**authority_value, "authority_hash": object_hash(authority_value)}
    existing = sorted(item["artifact_id"] for item in manifest["artifacts"])
    admitted = sorted(
        item["artifact_id"] for item in manifest["artifacts"] if item["role"] != "EXCLUDED"
    )
    return {
        "U_H": histories,
        "H": {
            "existing_artifact_ids": existing,
            "admitted_artifact_ids": admitted,
            "normalization": "stable artifact identity; existence and admission are separate",
        },
        "pre_partition": pre,
        "post_partition": post,
        "Lambda": authority,
        "omega": {
            "pre": {"visible_fields": ["request_id"], "contains_evaluator_truth": False},
            "post": {
                "visible_fields": ["realm", "request_id"],
                "contains_evaluator_truth": False,
            },
        },
    }


def audit_contract(
    contract: dict[str, Any], reconstructed: dict[str, Any], facts: list[dict[str, Any]]
) -> dict[str, Any]:
    mismatches: list[dict[str, str]] = []
    states = {state["state_id"]: state for state in contract["states"]}
    pre_id = contract["s0"]
    successor_ids = contract["Succ_plus"][contract["Q"][0]["intervention_id"]]
    post_id = successor_ids[0]
    comparisons = {
        "U_H": contract["U_H"] == reconstructed["U_H"],
        "H": contract["H"] == reconstructed["H"],
        "P_R_pre": contract["P_R"][pre_id] == reconstructed["pre_partition"],
        "P_R_post": contract["P_R"][post_id] == reconstructed["post_partition"],
        "Lambda_pre": contract["Lambda"][pre_id] == reconstructed["Lambda"],
        "Lambda_post": contract["Lambda"][post_id] == reconstructed["Lambda"],
        "omega_pre": all(
            states[pre_id]["controller_observation"][key] == value
            for key, value in reconstructed["omega"]["pre"].items()
        ),
        "omega_post": all(
            states[post_id]["controller_observation"][key] == value
            for key, value in reconstructed["omega"]["post"].items()
        ),
        "contract_self_hash": contract["contract_hash"]
        == object_hash({key: value for key, value in contract.items() if key != "contract_hash"}),
        "fact_references": set(contract["source_fact_ids"]) <= {fact["fact_id"] for fact in facts},
        "unit_cost": contract["c"] == {"primary": "unit", "unit_cost": 1, "native_secondary": []},
        "initial_state": pre_id in contract["S"],
    }
    for component, passed in comparisons.items():
        if not passed:
            mismatches.append(
                {"component": component, "reason": "INDEPENDENT_RECONSTRUCTION_MISMATCH"}
            )
    if not all(
        validate_partition(value, [item["history_id"] for item in contract["U_H"]])
        for value in contract["P_R"].values()
    ):
        mismatches.append({"component": "P_R", "reason": "INVALID_PARTITION"})
    return {"passed": not mismatches, "comparisons": comparisons, "mismatches": mismatches}
