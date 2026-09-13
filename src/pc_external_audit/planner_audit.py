"""Independent exhaustive policy-tree result and aggregation audit."""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any

FREEZES = (
    ("F000", ()),
    ("F100", ("E",)),
    ("F010", ("R",)),
    ("F001", ("A",)),
    ("F110", ("E", "R")),
    ("F101", ("E", "A")),
    ("F011", ("R", "A")),
    ("F111", ("E", "R", "A")),
)


def finite(value: int) -> dict[str, Any]:
    return {"kind": "FINITE", "value": value}


def infinite() -> dict[str, str]:
    return {"kind": "INFINITE"}


def exhaustive_value(
    contract: dict[str, Any], case_id: str, allowed_action_ids: set[str]
) -> tuple[dict[str, Any], list[str], int]:
    states = sorted(contract["S"])
    terminal = {
        state["state_id"] for state in contract["states"] if state["terminal_certificates"][case_id]
    }
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in sorted(contract["Q"], key=lambda item: item["intervention_id"]):
        if action["intervention_id"] in allowed_action_ids:
            by_source[action["source_state_id"]].append(action)
    decisions = [state for state in states if state not in terminal]
    options = [by_source[state] or [None] for state in decisions]
    best: int | None = None
    initial_actions: set[str] = set()
    count = 0

    def walk(state: str, policy: dict[str, Any], stack: frozenset[str]) -> int | None:
        if state in terminal:
            return 0
        if state in stack or policy[state] is None:
            return None
        action = policy[state]
        costs = [
            walk(successor["state_id"], policy, stack | {state})
            for successor in action["positive_support_successors"]
        ]
        if any(cost is None for cost in costs):
            return None
        return action["cost"]["unit"] + max(cost for cost in costs if cost is not None)

    for selected in itertools.product(*options):
        count += 1
        policy = dict(zip(decisions, selected, strict=True))
        value = walk(contract["s0"], policy, frozenset())
        if value is None:
            continue
        action = policy.get(contract["s0"])
        action_id = action["intervention_id"] if action else None
        if best is None or value < best:
            best = value
            initial_actions = {action_id} if action_id else set()
        elif value == best and action_id:
            initial_actions.add(action_id)
    return (finite(best) if best is not None else infinite(), sorted(initial_actions), count)


def relation(restricted: dict[str, Any], unrestricted: dict[str, Any]) -> str:
    if restricted["kind"] == unrestricted["kind"] == "INFINITE":
        return "BOTH_INFINITE"
    if restricted["kind"] == "INFINITE":
        return "STRUCTURAL_POSITIVE"
    if unrestricted["kind"] == "INFINITE" or restricted["value"] < unrestricted["value"]:
        return "INVALID_NEGATIVE"
    return "FINITE_POSITIVE" if restricted["value"] > unrestricted["value"] else "FINITE_ZERO"


def classification(delta_relation: str) -> str:
    return {
        "FINITE_POSITIVE": "POSITIVE_FINITE",
        "FINITE_ZERO": "ZERO_GAP",
        "STRUCTURAL_POSITIVE": "STRUCTURAL_R",
        "BOTH_INFINITE": "BOTH_INFINITE",
    }.get(delta_relation, "INVALID")


def recompute_results(
    contract: dict[str, Any], touches: list[dict[str, Any]], route_by_case: dict[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    touch_by_action = {row["action_id"]: row["touches"] for row in touches}
    detailed: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for case_id in sorted(contract["Terminal"]):
        values: dict[str, dict[str, Any]] = {}
        result_ids: dict[str, str] = {}
        for freeze_id, forbidden in FREEZES:
            allowed = {
                action["intervention_id"]
                for action in contract["Q"]
                if not any(
                    touch_by_action[action["intervention_id"]][resource] for resource in forbidden
                )
            }
            value, actions, policies = exhaustive_value(contract, case_id, allowed)
            values[freeze_id] = value
            detailed.append(
                {
                    "case_id": case_id,
                    "completion_id": contract["completion_id"],
                    "cost_contract_id": "unit_intervention_cost",
                    "freeze_id": freeze_id,
                    "forbidden_resources": list(forbidden),
                    "retained_action_ids": sorted(allowed),
                    "value": value,
                    "optimal_action_ids": actions,
                    "policies_enumerated": policies,
                }
            )
        delta = relation(values["F010"], values["F000"])
        row: dict[str, Any] = {
            "case_id": case_id,
            "completion_id": contract["completion_id"],
            "cost_contract_id": "unit_intervention_cost",
            "delta_R_relation": delta,
            "result_class": classification(delta),
            "route_class": route_by_case[case_id],
            "identification_status": "IDENTIFIED",
            "audit_eligible": delta != "INVALID_NEGATIVE",
            "contract_hash": contract["contract_hash"],
        }
        for freeze_id, _ in FREEZES:
            row[f"K_{freeze_id}_kind"] = values[freeze_id]["kind"]
            row[f"K_{freeze_id}_value"] = values[freeze_id].get("value")
            row[f"{freeze_id}_result_id"] = result_ids.get(freeze_id)
        cases.append(row)
    return detailed, cases


def compare_production_results(
    independent_detailed: list[dict[str, Any]], production_detailed: list[dict[str, Any]]
) -> list[dict[str, str]]:
    keys = ("case_id", "completion_id", "cost_contract_id", "freeze_id")
    production = {tuple(row[key] for key in keys): row for row in production_detailed}
    mismatches: list[dict[str, str]] = []
    for row in independent_detailed:
        key = tuple(row[field] for field in keys)
        observed = production.get(key)
        if observed is None:
            mismatches.append({"key": repr(key), "reason": "MISSING_PRODUCTION_RESULT"})
            continue
        for field in ("forbidden_resources", "retained_action_ids", "value", "optimal_action_ids"):
            if row[field] != observed[field]:
                mismatches.append({"key": repr(key), "reason": f"FIELD_MISMATCH:{field}"})
    if len(independent_detailed) != len(production_detailed):
        mismatches.append({"key": "results", "reason": "COUNT_MISMATCH"})
    return mismatches


def compare_case_rows(
    independent_cases: list[dict[str, Any]], production_cases: list[dict[str, Any]]
) -> list[dict[str, str]]:
    production = {row["case_id"]: row for row in production_cases}
    fields = [
        "completion_id",
        "cost_contract_id",
        "delta_R_relation",
        "result_class",
        "route_class",
        "identification_status",
        "audit_eligible",
        "contract_hash",
    ]
    for freeze_id, _ in FREEZES:
        fields.extend([f"K_{freeze_id}_kind", f"K_{freeze_id}_value"])
    mismatches: list[dict[str, str]] = []
    for row in independent_cases:
        observed = production.get(row["case_id"])
        if observed is None:
            mismatches.append({"key": row["case_id"], "reason": "MISSING_CASE_ROW"})
            continue
        for field in fields:
            if row[field] != observed[field]:
                mismatches.append({"key": row["case_id"], "reason": f"FIELD_MISMATCH:{field}"})
    if len(independent_cases) != len(production_cases):
        mismatches.append({"key": "case_results", "reason": "COUNT_MISMATCH"})
    return mismatches
