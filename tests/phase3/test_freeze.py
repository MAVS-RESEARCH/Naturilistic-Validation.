from __future__ import annotations

import copy

import pytest

from pc_external.freeze import (
    FREEZE_LATTICE,
    FreezeError,
    assert_same_instance,
    condition_manifest,
    derive_action_mask,
    exact_freeze_lattice,
    extended_relation,
)

ACTIONS = [
    {"intervention_id": "a_e", "source_state_id": "s"},
    {"intervention_id": "a_r", "source_state_id": "s"},
    {"intervention_id": "a_a", "source_state_id": "s"},
    {"intervention_id": "a_mixed", "source_state_id": "s"},
    {"intervention_id": "a_empty", "source_state_id": "s"},
]
TOUCHES = {
    "a_e": {"E": True, "R": False, "A": False},
    "a_r": {"E": False, "R": True, "A": False},
    "a_a": {"E": False, "R": False, "A": True},
    "a_mixed": {"E": True, "R": True, "A": True},
    "a_empty": {"E": False, "R": False, "A": False},
}


def test_exact_eight_freezes_and_action_masks() -> None:
    configured = [
        {"id": freeze_id, "forbidden": list(resources)} for freeze_id, resources in FREEZE_LATTICE
    ]
    assert len(exact_freeze_lattice(configured)) == 8
    masks = {
        freeze_id: derive_action_mask(ACTIONS, TOUCHES, forbidden)["retained_action_ids"]
        for freeze_id, forbidden in FREEZE_LATTICE
    }
    assert masks["F000"] == ["a_a", "a_e", "a_empty", "a_mixed", "a_r"]
    assert masks["F100"] == ["a_a", "a_empty", "a_r"]
    assert masks["F010"] == ["a_a", "a_e", "a_empty"]
    assert masks["F001"] == ["a_e", "a_empty", "a_r"]
    assert masks["F111"] == ["a_empty"]


def test_lattice_order_or_touch_omission_fails_closed() -> None:
    configured = [
        {"id": freeze_id, "forbidden": list(resources)}
        for freeze_id, resources in reversed(FREEZE_LATTICE)
    ]
    with pytest.raises(FreezeError, match="lattice"):
        exact_freeze_lattice(configured)
    with pytest.raises(FreezeError, match="touch record"):
        derive_action_mask(ACTIONS, {"a_e": TOUCHES["a_e"]}, [])


def test_same_instance_detects_only_scientific_mutation() -> None:
    instance = {"case_id": "case:x", "s0": "s", "S": ["s", "goal"]}
    manifests = [
        condition_manifest(
            run_id="run",
            instance=instance,
            freeze_id=freeze_id,
            forbidden_resources=list(forbidden),
            action_mask={
                "retained_action_ids": [],
                "blocked_action_ids": [],
                "action_mask_hash": "0" * 64,
            },
            contract_seal_hash="1" * 64,
        )
        for freeze_id, forbidden in FREEZE_LATTICE
    ]
    assert assert_same_instance(manifests)["manifest_count"] == 8
    corrupted = copy.deepcopy(manifests)
    corrupted[-1]["scientific_instance"]["s0"] = "different"
    with pytest.raises(FreezeError, match="differ"):
        assert_same_instance(corrupted)


def test_extended_real_relation_vocabulary_and_negative_detector() -> None:
    one = {"kind": "FINITE", "value": 1}
    two = {"kind": "FINITE", "value": 2}
    inf = {"kind": "INFINITE"}
    assert extended_relation(two, one) == "FINITE_POSITIVE"
    assert extended_relation(one, one) == "FINITE_ZERO"
    assert extended_relation(inf, one) == "STRUCTURAL_POSITIVE"
    assert extended_relation(inf, inf) == "BOTH_INFINITE"
    assert extended_relation(None, one) == "UNDEFINED"
    with pytest.raises(FreezeError, match="FINITE_NEGATIVE"):
        extended_relation(one, two)
