from __future__ import annotations

import pytest

from pc_external.planner import (
    PlannerError,
    exact_minimax_plan,
    exhaustive_policy_optimum,
)


def action(action_id: str, source: str, successors: list[str], cost: int = 1) -> dict:
    return {
        "intervention_id": action_id,
        "source_state_id": source,
        "positive_support_successors": [
            {"state_id": successor, "support": 1} for successor in successors
        ],
        "cost": {"unit": cost},
    }


def solve(states: list[str], actions: list[dict], allowed: list[str]) -> dict:
    return exact_minimax_plan(
        states=states,
        actions=actions,
        initial_state="start",
        terminal_states=["goal"],
        allowed_action_ids=allowed,
        cost_key="unit",
    )


def alternate(states: list[str], actions: list[dict], allowed: list[str]) -> dict:
    return exhaustive_policy_optimum(
        states=states,
        actions=actions,
        initial_state="start",
        terminal_states=["goal"],
        allowed_action_ids=allowed,
        cost_key="unit",
    )


def test_exact_planner_selects_all_tied_optimal_actions() -> None:
    actions = [
        action("a_direct", "start", ["goal"], 2),
        action("a_via", "start", ["middle"], 1),
        action("a_finish", "middle", ["goal"], 1),
    ]
    result = solve(["start", "middle", "goal"], actions, [a["intervention_id"] for a in actions])
    assert result["value"] == {"kind": "FINITE", "value": 2}
    assert result["optimal_action_ids"] == ["a_direct", "a_via"]
    assert result["certificate"]["certificate_hash"]


def test_positive_support_branching_uses_worst_supported_successor() -> None:
    actions = [
        action("branch", "start", ["near", "far"], 1),
        action("near_done", "near", ["goal"], 1),
        action("far_step", "far", ["far2"], 1),
        action("far_done", "far2", ["goal"], 1),
    ]
    states = ["start", "near", "far", "far2", "goal"]
    allowed = [item["intervention_id"] for item in actions]
    production = solve(states, actions, allowed)
    independent = alternate(states, actions, allowed)
    assert production["value"] == {"kind": "FINITE", "value": 3}
    assert independent["value"] == production["value"]


def test_improper_cycle_is_explicitly_infinite() -> None:
    actions = [action("cycle_a", "start", ["loop"]), action("cycle_b", "loop", ["start"])]
    production = solve(["start", "loop", "goal"], actions, ["cycle_a", "cycle_b"])
    independent = alternate(["start", "loop", "goal"], actions, ["cycle_a", "cycle_b"])
    assert production["value"] == {"kind": "INFINITE"}
    assert production["certificate"]["improper_cycle_edges"]
    assert independent["value"] == production["value"]


def test_action_removal_can_make_target_unreachable_without_sentinel() -> None:
    actions = [action("repair", "start", ["goal"])]
    result = solve(["start", "goal"], actions, [])
    assert result["value"] == {"kind": "INFINITE"}
    assert "value" not in result["value"]


@pytest.mark.parametrize("cost", [-1, True, 1.5])
def test_invalid_costs_fail_closed(cost: object) -> None:
    with pytest.raises(PlannerError, match="nonnegative integers"):
        solve(["start", "goal"], [action("bad", "start", ["goal"], cost)], ["bad"])


def test_unknown_mask_action_fails_closed() -> None:
    with pytest.raises(PlannerError, match="known actions"):
        solve(["start", "goal"], [action("repair", "start", ["goal"])], ["unknown"])
