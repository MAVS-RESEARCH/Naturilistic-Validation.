from __future__ import annotations

import copy

from pc_external.claims import derive_claim_ledger, final_verdict
from pc_external_audit.claims_audit import validate_claim_ledger, verify_report_sentences
from pc_external_audit.contract_audit import canonical_partition, validate_partition
from pc_external_audit.planner_audit import exhaustive_value, relation
from pc_external_audit.source_audit import object_hash, verify_self_hash
from pc_external_audit.touch_audit import audit_touch, derive_touch
from scripts.phase4_corruption_tests import (
    allocation_is_bijective,
    expected_mask,
    provenance_complete,
    valid_extended_real,
)


def synthetic_contract() -> dict:
    partition = canonical_partition(["h1", "h2"], {"h1": "same", "h2": "same"})
    split = canonical_partition(["h1", "h2"], {"h1": "left", "h2": "right"})
    action = {
        "intervention_id": "q1",
        "source_state_id": "s0",
        "positive_support_successors": [{"state_id": "goal", "probability_positive": True}],
        "cost": {"unit": 1},
        "provenance_fact_ids": ["fact:1"],
    }
    value = {
        "completion_id": "completion:1",
        "S": ["s0", "goal"],
        "s0": "s0",
        "Q": [action],
        "source_fact_ids": ["fact:1"],
        "Succ_plus": {"q1": ["goal"]},
        "Terminal": {"case:1": ["goal"]},
        "states": [
            {
                "state_id": "s0",
                "normalized_evidence_hash": "evidence",
                "representation_partition": partition,
                "authority": {"entries": []},
                "terminal_certificates": {"case:1": False},
            },
            {
                "state_id": "goal",
                "normalized_evidence_hash": "evidence",
                "representation_partition": split,
                "authority": {"entries": []},
                "terminal_certificates": {"case:1": True},
            },
        ],
    }
    value["contract_hash"] = object_hash(value)
    return value


def passing_core() -> dict:
    return {"overall_pass": True}


def passing_corruptions() -> dict:
    return {"all_detected": True, "detected_count": 12}


def positive_case() -> dict:
    return {
        "case_id": "case:1",
        "result_class": "STRUCTURAL_R",
        "route_class": "SINGLE_ACTION",
        "audit_eligible": True,
    }


def test_independent_hash_partition_touch_and_exact_planner() -> None:
    payload = {"field": [1, 2, 3]}
    sealed = {**payload, "hash": object_hash(payload)}
    assert verify_self_hash(sealed, "hash")
    partition = canonical_partition(["h1", "h2"], {"h1": "same", "h2": "same"})
    assert validate_partition(partition, ["h1", "h2"])
    broken = copy.deepcopy(partition)
    broken["blocks"][0].pop()
    assert not validate_partition(broken, ["h1", "h2"])

    contract = synthetic_contract()
    touches = derive_touch(contract)
    assert touches[0]["touches"] == {"E": False, "R": True, "A": False}
    assert audit_touch(touches, copy.deepcopy(touches))["passed"]
    changed = copy.deepcopy(touches)
    changed[0]["touches"]["R"] = False
    assert not audit_touch(touches, changed)["passed"]
    value, actions, policies = exhaustive_value(contract, "case:1", {"q1"})
    assert value == {"kind": "FINITE", "value": 1}
    assert actions == ["q1"]
    assert policies == 1
    assert exhaustive_value(contract, "case:1", set())[0] == {"kind": "INFINITE"}
    assert relation({"kind": "INFINITE"}, value) == "STRUCTURAL_POSITIVE"


def test_claims_are_hash_bound_complete_and_scope_locked() -> None:
    ledger = derive_claim_ledger(
        "isolated", passing_core(), passing_corruptions(), [positive_case()]
    )
    assert ledger["external_operational_validation"]
    assert ledger["result_sign"] == "POSITIVE"
    assert final_verdict(ledger) == "PASS — POSITIVE EXTERNAL"
    assert ledger["locked_flags"] == {
        "prevalence": False,
        "superiority": False,
        "deployment_readiness": False,
    }
    assert not validate_claim_ledger(ledger)
    report = "\n".join(
        f"[{claim['claim_id']}] {claim['generated_text']}" for claim in ledger["claims"]
    )
    assert not verify_report_sentences(report, ledger)
    assert verify_report_sentences("", ledger)
    edited = copy.deepcopy(ledger)
    edited["claims"][0]["generated_text"] = "Strengthened text."
    assert validate_claim_ledger(edited)


def test_corruption_detectors_use_independent_invariants() -> None:
    contract = synthetic_contract()
    touches = derive_touch(contract)
    assert provenance_complete(contract, {"fact:1"})
    missing = copy.deepcopy(contract)
    missing["Q"][0].pop("provenance_fact_ids")
    assert not provenance_complete(missing, {"fact:1"})
    assert expected_mask(contract, touches, "F000") == ["q1"]
    assert expected_mask(contract, touches, "F010") == []
    assert allocation_is_bijective({"a", "b"}, [{"case_id": "a"}, {"case_id": "b"}])
    assert not allocation_is_bijective({"a", "b"}, [{"case_id": "a"}])
    assert valid_extended_real({"kind": "FINITE", "value": 0})
    assert valid_extended_real({"kind": "INFINITE"})
    assert not valid_extended_real({"kind": "INFINITE", "value": 999999})
