"""Mechanical E/R/A touch derivation over all positive-support successors."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pc_external.authority import authority_diff
from pc_external.hashing import canonical_json_hash, content_id
from pc_external.interventions import successor_ids, validate_intervention
from pc_external.partitions import partition_diff


class TouchError(ValueError):
    """Raised when touch cannot be derived exactly."""


def derive_touch_record(
    *,
    completion_id: str,
    action: Mapping[str, Any],
    states: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    validate_intervention(action, states)
    before = states[action["source_state_id"]]
    evidence_witnesses: list[dict[str, Any]] = []
    representation_witnesses: list[dict[str, Any]] = []
    authority_witnesses: list[dict[str, Any]] = []
    for target_id in successor_ids(action):
        after = states[target_id]
        if before["normalized_evidence_hash"] != after["normalized_evidence_hash"]:
            evidence_witnesses.append(
                {
                    "successor_id": target_id,
                    "before_hash": before["normalized_evidence_hash"],
                    "after_hash": after["normalized_evidence_hash"],
                }
            )
        representation = partition_diff(
            before["representation_partition"], after["representation_partition"]
        )
        if representation["changed"]:
            representation_witnesses.append({"successor_id": target_id, **representation})
        authority = authority_diff(before["authority"], after["authority"])
        if authority["changed"]:
            authority_witnesses.append({"successor_id": target_id, **authority})
    touches = {
        "E": bool(evidence_witnesses),
        "R": bool(representation_witnesses),
        "A": bool(authority_witnesses),
    }
    payload = {
        "completion_id": completion_id,
        "state_id": action["source_state_id"],
        "action_id": action["intervention_id"],
        "successor_ids": successor_ids(action),
        "touches": touches,
        "witnesses": {
            "E": evidence_witnesses,
            "R": representation_witnesses,
            "A": authority_witnesses,
        },
        "provenance_hash": canonical_json_hash(action["provenance_fact_ids"]),
    }
    return {"touch_record_id": content_id("touch", payload), **payload}


def derive_all_touch_records(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    states = {state["state_id"]: state for state in contract["states"]}
    records = [
        derive_touch_record(completion_id=contract["completion_id"], action=action, states=states)
        for action in contract["Q"]
    ]
    expected = {
        (contract["completion_id"], action["source_state_id"], action["intervention_id"])
        for action in contract["Q"]
    }
    actual = {(item["completion_id"], item["state_id"], item["action_id"]) for item in records}
    if actual != expected or len(records) != len(expected):
        raise TouchError("reachable state-action pairs do not have exactly one touch record")
    return sorted(records, key=lambda item: item["touch_record_id"])
