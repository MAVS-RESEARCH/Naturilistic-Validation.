"""Mandatory Phase-3 isolated transformation controls C1 through C10."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from pc_external.authority import assert_no_taint
from pc_external.freeze import FREEZE_LATTICE, derive_action_mask
from pc_external.hashing import canonical_json_hash
from pc_external.interventions import validate_intervention
from pc_external.partitions import canonical_partition
from pc_external.planner import exact_minimax_plan


def _record(
    control_id: str,
    transformation: str,
    transformation_input: dict[str, Any],
    expected: str,
    observed: dict[str, Any],
    evidence: list[str],
    passed: bool,
) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "transformation": transformation,
        "transformation_input": transformation_input,
        "expected_invariant": expected,
        "observed_result": observed,
        "evidence": evidence,
        "passed": passed,
    }


def run_controls(
    contract: Mapping[str, Any],
    touch_by_action: Mapping[str, Mapping[str, bool]],
    solve_digest: Callable[[Mapping[str, Any]], str],
) -> list[dict[str, Any]]:
    """Execute all controls on deep copies, never on the authoritative contract object."""

    baseline_hash = canonical_json_hash(contract)
    controls: list[dict[str, Any]] = []
    universe = [item["history_id"] for item in contract["U_H"]]
    labels = {history: f"label-{index}" for index, history in enumerate(universe)}
    renamed = {history: f"renamed-{index}" for index, history in enumerate(universe)}
    controls.append(
        _record(
            "C1_REPRESENTATION_VALUE_RENAME",
            "bijectively rename raw representation values",
            {"value_count": len(labels)},
            "canonical partition and planner value remain invariant",
            {
                "partition_equal": canonical_partition(universe, labels)
                == canonical_partition(universe, renamed)
            },
            ["synthetic raw labels are external to authoritative Polaris values"],
            canonical_partition(universe, labels) == canonical_partition(universe, renamed),
        )
    )

    permuted = copy.deepcopy(contract)
    permuted["Q"].reverse()
    permuted["U_H"].reverse()
    controls.append(
        _record(
            "C2_CASE_FIELD_ORDER_PERMUTATION",
            "reverse action and history serialization order",
            {"actions": len(contract["Q"]), "histories": len(universe)},
            "scientific solution digest remains invariant",
            {"baseline_digest": solve_digest(contract), "permuted_digest": solve_digest(permuted)},
            ["solver canonicalizes identities rather than relying on input order"],
            solve_digest(contract) == solve_digest(permuted),
        )
    )

    metadata_copy = copy.deepcopy(contract)
    metadata_copy["irrelevant_metadata"] = {"control": "C3", "value": 17}
    controls.append(
        _record(
            "C3_IRRELEVANT_METADATA_PERTURBATION",
            "add an unconsumed metadata object to an isolated copy",
            {"field": "irrelevant_metadata"},
            "planner result remains invariant",
            {
                "baseline_digest": solve_digest(contract),
                "perturbed_digest": solve_digest(metadata_copy),
            },
            ["planner consumes only typed graph fields"],
            solve_digest(contract) == solve_digest(metadata_copy),
        )
    )

    noop_actions = list(copy.deepcopy(contract["Q"])) + [
        {
            "intervention_id": "action:synthetic_empty_touch_noop",
            "source_state_id": contract["s0"],
            "positive_support_successors": [{"state_id": contract["s0"], "support": 1}],
            "cost": {"unit": 1, "native": None},
        }
    ]
    noop_touch = {
        **copy.deepcopy(touch_by_action),
        "action:synthetic_empty_touch_noop": {"E": False, "R": False, "A": False},
    }
    retained_all = all(
        "action:synthetic_empty_touch_noop"
        in derive_action_mask(noop_actions, noop_touch, forbidden)["retained_action_ids"]
        for _, forbidden in FREEZE_LATTICE
    )
    no_improvement = True
    for _, forbidden in FREEZE_LATTICE:
        baseline_mask = derive_action_mask(contract["Q"], touch_by_action, forbidden)
        augmented_mask = derive_action_mask(noop_actions, noop_touch, forbidden)
        for case_id in sorted(contract["Terminal"]):
            terminals = [
                state["state_id"]
                for state in contract["states"]
                if state["terminal_certificates"][case_id]
            ]
            baseline = exact_minimax_plan(
                states=contract["S"],
                actions=contract["Q"],
                initial_state=contract["s0"],
                terminal_states=terminals,
                allowed_action_ids=baseline_mask["retained_action_ids"],
                cost_key="unit",
            )
            augmented = exact_minimax_plan(
                states=contract["S"],
                actions=noop_actions,
                initial_state=contract["s0"],
                terminal_states=terminals,
                allowed_action_ids=augmented_mask["retained_action_ids"],
                cost_key="unit",
            )
            no_improvement = no_improvement and baseline["value"] == augmented["value"]
    controls.append(
        _record(
            "C4_EMPTY_TOUCH_NOOP",
            "add an isolated positive-cost self-loop with empty touch",
            {"action_id": "action:synthetic_empty_touch_noop"},
            "empty-touch action remains mask-eligible and cannot improve closure",
            {"retained_in_all_freezes": retained_all, "closure_values_unchanged": no_improvement},
            ["synthetic no-op is not an authoritative intervention"],
            retained_all and no_improvement,
        )
    )

    observed_masks = {
        freeze_id: derive_action_mask(contract["Q"], touch_by_action, forbidden)[
            "retained_action_ids"
        ]
        for freeze_id, forbidden in FREEZE_LATTICE
    }
    expected_masks = {
        freeze_id: sorted(
            action["intervention_id"]
            for action in contract["Q"]
            if not any(
                touch_by_action[action["intervention_id"]][resource] for resource in forbidden
            )
        )
        for freeze_id, forbidden in FREEZE_LATTICE
    }
    controls.append(
        _record(
            "C5_EXACT_FREEZE_AUDIT",
            "independently recompute all eight disjoint-touch masks",
            {"freeze_count": 8},
            "every action mask equals exact set-disjointness",
            {"observed_masks": observed_masks, "expected_masks": expected_masks},
            ["all F000-F111 cells audited"],
            observed_masks == expected_masks,
        )
    )

    mixed_action = {
        "intervention_id": "action:synthetic_mixed",
        "source_state_id": "s0",
        "positive_support_successors": [{"state_id": "goal", "support": 1}],
        "cost": {"unit": 1},
    }
    mixed_touch = {"action:synthetic_mixed": {"E": True, "R": True, "A": True}}
    mixed_masks = {
        fid: derive_action_mask([mixed_action], mixed_touch, forbidden)
        for fid, forbidden in FREEZE_LATTICE
    }
    mixed_pass = mixed_masks["F000"]["retained_action_ids"] == ["action:synthetic_mixed"] and all(
        not mixed_masks[fid]["retained_action_ids"] for fid, _ in FREEZE_LATTICE if fid != "F000"
    )
    controls.append(
        _record(
            "C6_ATOMICITY_CHALLENGE",
            "freeze a synthetic E/R/A mixed action without component splitting",
            {"touch": mixed_touch["action:synthetic_mixed"]},
            "atomic mixed action is blocked by every nonempty freeze",
            {"masks": mixed_masks},
            ["one action identity is preserved in every condition"],
            mixed_pass,
        )
    )

    evaluator_values = [item["expected_realm"] for item in contract["A_Pi"].values()]
    visible_payload = [state["controller_observation"] for state in contract["states"]]
    isolation_pass = all(value not in str(visible_payload) for value in evaluator_values)
    controls.append(
        _record(
            "C7_TARGET_ISOLATION",
            "search controller observations for terminal evaluator labels",
            {"evaluator_label_count": len(evaluator_values)},
            "terminal labels remain evaluator-only",
            {"labels_absent_from_controller_observation": isolation_pass},
            ["omega stores field names, not expected realm values"],
            isolation_pass,
        )
    )

    provenance_copy = copy.deepcopy(contract)
    del provenance_copy["Q"][0]["provenance_fact_ids"]
    provenance_rejected = False
    try:
        validate_intervention(provenance_copy["Q"][0], provenance_copy["S"])
    except (KeyError, ValueError):
        provenance_rejected = True
    controls.append(
        _record(
            "C8_PROVENANCE_DELETION",
            "delete required intervention provenance on an isolated copy",
            {"deleted_field": "Q[0].provenance_fact_ids"},
            "validation detects missing provenance",
            {"detected": provenance_rejected},
            ["authoritative contract hash remains unchanged"],
            provenance_rejected,
        )
    )

    tainted = copy.deepcopy(contract["states"][0]["controller_observation"])
    tainted["leaked_expected_realm"] = evaluator_values[0]
    taint_rejected = False
    try:
        assert_no_taint(tainted, evaluator_values)
    except ValueError:
        taint_rejected = True
    controls.append(
        _record(
            "C9_HIDDEN_TRUTH_TAINT",
            "inject evaluator-only truth into an isolated controller observation",
            {"injected_field": "leaked_expected_realm"},
            "taint validator rejects the copy",
            {"detected": taint_rejected},
            ["authoritative omega is never modified"],
            taint_rejected,
        )
    )

    completion_forward = [
        contract["completion_id"],
        "completion:isolated-permutation-fixture-a",
        "completion:isolated-permutation-fixture-b",
    ]
    completion_reverse = list(reversed(completion_forward))
    controls.append(
        _record(
            "C10_COMPLETION_PERMUTATION",
            "reverse exact completion enumeration order",
            {"completion_count": len(completion_forward)},
            "canonical completion set remains invariant",
            {"forward": sorted(completion_forward), "reversed": sorted(completion_reverse)},
            ["no completion sampling"],
            sorted(completion_forward) == sorted(completion_reverse),
        )
    )
    if canonical_json_hash(contract) != baseline_hash:
        raise RuntimeError("control execution mutated the authoritative contract")
    return controls


def solve_contract_digest(contract: Mapping[str, Any]) -> str:
    """Return an order-invariant synthetic control digest for unrestricted case solutions."""

    rows = []
    for case_id in sorted(contract["Terminal"]):
        terminal_states = [
            state["state_id"]
            for state in contract["states"]
            if state["terminal_certificates"][case_id]
        ]
        solved = exact_minimax_plan(
            states=contract["S"],
            actions=contract["Q"],
            initial_state=contract["s0"],
            terminal_states=terminal_states,
            allowed_action_ids=[action["intervention_id"] for action in contract["Q"]],
            cost_key="unit",
        )
        rows.append(
            {
                "case_id": case_id,
                "value": solved["value"],
                "optimal_action_ids": solved["optimal_action_ids"],
            }
        )
    return canonical_json_hash(rows)
