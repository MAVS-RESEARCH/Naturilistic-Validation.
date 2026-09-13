from __future__ import annotations

import json
from pathlib import Path

import pytest

from pc_external.authority import (
    AuthorityError,
    assert_no_taint,
    authority_diff,
    canonical_authority,
    controller_observation,
)

ROOT = Path(__file__).resolve().parents[2]


def test_authority_is_distinct_from_field_existence_and_metadata() -> None:
    entry = {
        "kind": "PREDICATE",
        "identifier": "rego_allow_over_presented_input",
        "admissible": True,
        "provenance_fact_ids": ["fact:a"],
    }
    before = canonical_authority([entry])
    after = canonical_authority([entry])
    assert authority_diff(before, after)["changed"] is False
    assert (
        controller_observation(["request_id"], evaluator_only_values=[])["observation_hash"]
        != (
            controller_observation(["request_id", "realm"], evaluator_only_values=[])[
                "observation_hash"
            ]
        )
    )


def test_authority_normalization_is_permutation_invariant() -> None:
    entries = [
        {
            "kind": "SOURCE",
            "identifier": "opa",
            "admissible": True,
            "provenance_fact_ids": ["b", "a"],
        },
        {"kind": "CHECK", "identifier": "deny", "admissible": True, "provenance_fact_ids": ["c"]},
    ]
    assert canonical_authority(entries) == canonical_authority(reversed(entries))


def test_hidden_truth_taint_is_rejected() -> None:
    fixture = json.loads((ROOT / "tests" / "fixtures" / "phase2_taint.json").read_text())
    observation = controller_observation(
        fixture["visible_fields"], evaluator_only_values=fixture["evaluator_only_values"]
    )
    assert observation["contains_evaluator_truth"] is False
    with pytest.raises(AuthorityError, match="evaluator-only truth"):
        assert_no_taint(fixture["leaking_observation"], fixture["evaluator_only_values"])
    with pytest.raises(AuthorityError, match="leaked"):
        controller_observation(["realm-secret"], evaluator_only_values=["realm-secret"])
