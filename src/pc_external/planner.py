"""Exact closure planners for finite deterministic and positive-support graphs."""

from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from pc_external.hashing import canonical_json_hash


class PlannerError(ValueError):
    """Raised when a graph violates the exact planner contract."""


def finite(value: int) -> dict[str, Any]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PlannerError("finite extended-real values must be nonnegative integers")
    return {"kind": "FINITE", "value": value}


def infinity() -> dict[str, str]:
    return {"kind": "INFINITE"}


def _validate_graph(
    states: Iterable[str], actions: Iterable[Mapping[str, Any]], allowed: set[str], cost_key: str
) -> tuple[list[str], list[dict[str, Any]]]:
    state_ids = sorted(states)
    if not state_ids or len(state_ids) != len(set(state_ids)):
        raise PlannerError("states must be a nonempty unique collection")
    action_rows = sorted(
        (dict(action) for action in actions), key=lambda item: item["intervention_id"]
    )
    action_ids = [action["intervention_id"] for action in action_rows]
    if len(action_ids) != len(set(action_ids)) or not allowed <= set(action_ids):
        raise PlannerError("action IDs must be unique and the mask must reference known actions")
    known = set(state_ids)
    for action in action_rows:
        if action["source_state_id"] not in known:
            raise PlannerError("action source is outside S")
        successors = [item["state_id"] for item in action["positive_support_successors"]]
        if not successors or not set(successors) <= known:
            raise PlannerError("positive-support successors must be nonempty members of S")
        cost = action["cost"].get(cost_key)
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            raise PlannerError("planner costs must be nonnegative integers")
    return state_ids, action_rows


def exact_minimax_plan(
    *,
    states: Iterable[str],
    actions: Iterable[Mapping[str, Any]],
    initial_state: str,
    terminal_states: Iterable[str],
    allowed_action_ids: Iterable[str],
    cost_key: str,
) -> dict[str, Any]:
    """Solve the minimum worst-supported cost over proper observation-class policies.

    The fixed-point recurrence is V(s)=min_a[c(a)+max_{s' in Succ+(a)} V(s')].
    Actions enter the solved set only when every positive-support successor is solved, so
    unsupported optimism and improper cycles cannot receive a finite value.
    """

    allowed = set(allowed_action_ids)
    state_ids, action_rows = _validate_graph(states, actions, allowed, cost_key)
    terminals = set(terminal_states)
    if initial_state not in state_ids or not terminals <= set(state_ids):
        raise PlannerError("initial and terminal states must belong to S")
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in action_rows:
        if action["intervention_id"] in allowed:
            by_source[action["source_state_id"]].append(action)
    values: dict[str, int] = {state: 0 for state in terminals}
    optimal: dict[str, list[str]] = {state: [] for state in terminals}
    changed = True
    while changed:
        changed = False
        for state in state_ids:
            if state in terminals:
                continue
            candidates: list[tuple[int, str]] = []
            for action in by_source[state]:
                successors = [item["state_id"] for item in action["positive_support_successors"]]
                if all(successor in values for successor in successors):
                    candidates.append(
                        (
                            action["cost"][cost_key] + max(values[item] for item in successors),
                            action["intervention_id"],
                        )
                    )
            if not candidates:
                continue
            best = min(value for value, _ in candidates)
            best_actions = sorted(action_id for value, action_id in candidates if value == best)
            if state not in values or best < values[state] or optimal[state] != best_actions:
                values[state] = best
                optimal[state] = best_actions
                changed = True
    unresolved = sorted(set(state_ids) - set(values))
    cycle_edges = []
    for state in unresolved:
        for action in by_source[state]:
            successors = sorted(item["state_id"] for item in action["positive_support_successors"])
            if any(successor in unresolved for successor in successors):
                cycle_edges.append(
                    {
                        "state_id": state,
                        "action_id": action["intervention_id"],
                        "successor_ids": successors,
                    }
                )
    result_value = finite(values[initial_state]) if initial_state in values else infinity()
    certificate_without_hash = {
        "algorithm": "EXACT_AND_OR_MINIMAX",
        "recurrence": "min_action(cost + max_positive_support_successor_value)",
        "initial_state": initial_state,
        "terminal_states": sorted(terminals),
        "allowed_action_ids": sorted(allowed),
        "state_values": {
            state: finite(values[state]) if state in values else infinity() for state in state_ids
        },
        "optimal_actions_by_state": {state: optimal.get(state, []) for state in state_ids},
        "unreachable_states": unresolved,
        "improper_cycle_edges": cycle_edges,
        "value": result_value,
    }
    certificate = {
        **certificate_without_hash,
        "certificate_hash": canonical_json_hash(certificate_without_hash),
    }
    return {
        "value": result_value,
        "optimal_action_ids": optimal.get(initial_state, []),
        "certificate": certificate,
    }


def exhaustive_policy_optimum(
    *,
    states: Iterable[str],
    actions: Iterable[Mapping[str, Any]],
    initial_state: str,
    terminal_states: Iterable[str],
    allowed_action_ids: Iterable[str],
    cost_key: str,
) -> dict[str, Any]:
    """Independently enumerate stationary policies and reject cyclic policy branches."""

    allowed = set(allowed_action_ids)
    state_ids, action_rows = _validate_graph(states, actions, allowed, cost_key)
    terminals = set(terminal_states)
    choices: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in action_rows:
        if action["intervention_id"] in allowed:
            choices[action["source_state_id"]].append(action)
    decision_states = [state for state in state_ids if state not in terminals]
    option_lists = [choices[state] or [None] for state in decision_states]
    best: int | None = None
    best_initial_actions: set[str] = set()
    enumerated = 0

    def evaluate(state: str, policy: Mapping[str, Any], visiting: frozenset[str]) -> int | None:
        if state in terminals:
            return 0
        if state in visiting or policy[state] is None:
            return None
        action = policy[state]
        child_values = [
            evaluate(item["state_id"], policy, visiting | {state})
            for item in action["positive_support_successors"]
        ]
        if any(value is None for value in child_values):
            return None
        return action["cost"][cost_key] + max(value for value in child_values if value is not None)

    for selected in itertools.product(*option_lists):
        enumerated += 1
        policy = dict(zip(decision_states, selected, strict=True))
        value = evaluate(initial_state, policy, frozenset())
        if value is None:
            continue
        initial_action = policy.get(initial_state)
        if best is None or value < best:
            best = value
            best_initial_actions = {initial_action["intervention_id"]} if initial_action else set()
        elif value == best and initial_action:
            best_initial_actions.add(initial_action["intervention_id"])
    return {
        "value": finite(best) if best is not None else infinity(),
        "optimal_action_ids": sorted(best_initial_actions),
        "policies_enumerated": enumerated,
        "algorithm": "EXHAUSTIVE_STATIONARY_POLICY_ENUMERATION",
    }
