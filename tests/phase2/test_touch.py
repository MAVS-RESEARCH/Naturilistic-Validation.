from __future__ import annotations

import json
from pathlib import Path

import pytest

from pc_external.authority import canonical_authority
from pc_external.interventions import InterventionError, classify_route, validate_intervention
from pc_external.partitions import canonical_partition
from pc_external.touch import derive_all_touch_records, derive_touch_record

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE = ["history:a", "history:b"]


def authority(identifier: str) -> dict:
    return canonical_authority(
        [
            {
                "kind": "SOURCE",
                "identifier": identifier,
                "admissible": True,
                "provenance_fact_ids": ["fact:a"],
            }
        ]
    )


def state(state_id: str, *, evidence: str, split: bool, authority_id: str) -> dict:
    keys = {"history:a": "x", "history:b": "y" if split else "x"}
    return {
        "state_id": state_id,
        "normalized_evidence_hash": evidence,
        "representation_partition": canonical_partition(UNIVERSE, keys),
        "authority": authority(authority_id),
    }


def action(successors: list[str]) -> dict:
    return {
        "intervention_id": "action:fixture",
        "source_state_id": "state:before",
        "preconditions": ["fixture"],
        "atomicity": {"is_atomic": True, "basis": "fixture"},
        "positive_support_successors": [
            {"state_id": successor, "support": 1} for successor in successors
        ],
        "public_effect": "fixture",
        "provenance_fact_ids": ["fact:a"],
        "cost": {"unit": 1, "native": None},
    }


@pytest.mark.parametrize(
    "fixture_case",
    json.loads((ROOT / "tests" / "fixtures" / "phase2_touch_cases.json").read_text())["cases"],
)
def test_empty_and_all_e_r_a_truth_tables(fixture_case: dict) -> None:
    before = state("state:before", evidence="same", split=False, authority_id="same")
    after = state(
        "state:after",
        evidence="changed" if fixture_case["evidence"] else "same",
        split=fixture_case["representation"],
        authority_id="changed" if fixture_case["authority"] else "same",
    )
    record = derive_touch_record(
        completion_id="completion:" + "a" * 20,
        action=action(["state:after"]),
        states={"state:before": before, "state:after": after},
    )
    assert record["touches"] == {
        "E": fixture_case["evidence"],
        "R": fixture_case["representation"],
        "A": fixture_case["authority"],
    }


def test_successor_union_touch_and_exact_pair_coverage() -> None:
    states = {
        "state:before": state("state:before", evidence="same", split=False, authority_id="same"),
        "state:e": state("state:e", evidence="changed", split=False, authority_id="same"),
        "state:r": state("state:r", evidence="same", split=True, authority_id="same"),
        "state:a": state("state:a", evidence="same", split=False, authority_id="changed"),
    }
    intervention = action(["state:e", "state:r", "state:a"])
    contract = {
        "completion_id": "completion:" + "a" * 20,
        "states": list(states.values()),
        "Q": [intervention],
    }
    records = derive_all_touch_records(contract)
    assert len(records) == 1
    assert records[0]["touches"] == {"E": True, "R": True, "A": True}


def test_action_permutation_invariance() -> None:
    states = {
        "state:before": state("state:before", evidence="same", split=False, authority_id="same"),
        "state:after": state("state:after", evidence="same", split=True, authority_id="same"),
    }
    first = action(["state:after"])
    second = {**action(["state:after"]), "intervention_id": "action:second"}
    base = {"completion_id": "completion:" + "a" * 20, "states": list(states.values())}
    assert derive_all_touch_records({**base, "Q": [first, second]}) == derive_all_touch_records(
        {**base, "Q": [second, first]}
    )


def test_manual_touch_labels_and_invalid_support_are_rejected() -> None:
    intervention = action(["state:after"])
    with pytest.raises(InterventionError, match="manual touch"):
        validate_intervention({**intervention, "touch": ["R"]}, ["state:before", "state:after"])
    invalid = action(["state:after"])
    invalid["positive_support_successors"][0]["support"] = 0
    with pytest.raises(InterventionError, match="positive support"):
        validate_intervention(invalid, ["state:before", "state:after"])


def test_all_route_classifications_are_explicit() -> None:
    one = action(["state:after"])
    two = [{**one, "intervention_id": "action:a"}, {**one, "intervention_id": "action:b"}]
    assert classify_route([]) == "NO_REPAIR_SPACE"
    assert classify_route([one]) == "SINGLE_ACTION"
    assert classify_route(two, [{"E": False, "R": True, "A": False}] * 2) == "R-ONLY_ROUTE"
    assert classify_route(two) == "NONDEGENERATE"
