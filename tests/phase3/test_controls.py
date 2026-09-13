from __future__ import annotations

from pc_external.controls import run_controls, solve_contract_digest
from pc_external.hashing import canonical_json_hash


def synthetic_contract() -> dict:
    histories = [
        {"history_id": "h1", "case_id": "case:synthetic", "source_case_ids": ["native::one"]},
        {"history_id": "h2", "case_id": "case:synthetic", "source_case_ids": ["native::two"]},
    ]
    action = {
        "intervention_id": "action:repair",
        "source_state_id": "start",
        "preconditions": ["synthetic precondition"],
        "atomicity": {"is_atomic": True, "basis": "synthetic atomic fixture"},
        "positive_support_successors": [{"state_id": "goal", "support": 1}],
        "public_effect": "reach synthetic terminal",
        "cost": {"unit": 1},
        "provenance_fact_ids": ["fact:source"],
    }
    states = [
        {
            "state_id": "start",
            "terminal_certificates": {"case:synthetic": False},
            "controller_observation": {
                "visible_fields": ["request_id"],
                "contains_evaluator_truth": False,
            },
        },
        {
            "state_id": "goal",
            "terminal_certificates": {"case:synthetic": True},
            "controller_observation": {
                "visible_fields": ["request_id", "realm"],
                "contains_evaluator_truth": False,
            },
        },
    ]
    return {
        "completion_id": "completion:synthetic",
        "S": ["start", "goal"],
        "s0": "start",
        "U_H": histories,
        "Q": [action],
        "Terminal": {"case:synthetic": {"predicate": "certificate"}},
        "A_Pi": {"case:synthetic": {"expected_realm": "evaluator-secret"}},
        "states": states,
    }


def test_c1_through_c10_pass_on_out_of_sample_synthetic_contract() -> None:
    contract = synthetic_contract()
    before = canonical_json_hash(contract)
    results = run_controls(
        contract,
        {"action:repair": {"E": False, "R": True, "A": False}},
        solve_contract_digest,
    )
    assert [row["control_id"].split("_", 1)[0] for row in results] == [
        f"C{index}" for index in range(1, 11)
    ]
    assert all(row["passed"] for row in results)
    assert canonical_json_hash(contract) == before
    assert all(row["transformation_input"] for row in results)
    assert all(row["expected_invariant"] and row["evidence"] for row in results)
