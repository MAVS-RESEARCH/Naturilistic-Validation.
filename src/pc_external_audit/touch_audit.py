"""Independent state-difference and successor-union touch reconstruction."""

from __future__ import annotations

import itertools
from typing import Any

from pc_external_audit.source_audit import object_hash


def partition_pairs(partition: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for block in partition["blocks"]:
        pairs.update(itertools.combinations(sorted(block), 2))
    return pairs


def derive_touch(contract: dict[str, Any]) -> list[dict[str, Any]]:
    states = {state["state_id"]: state for state in contract["states"]}
    rows: list[dict[str, Any]] = []
    for action in sorted(contract["Q"], key=lambda item: item["intervention_id"]):
        source = states[action["source_state_id"]]
        touches = {"E": False, "R": False, "A": False}
        witnesses: dict[str, list[dict[str, Any]]] = {"E": [], "R": [], "A": []}
        successor_ids: list[str] = []
        for successor_spec in action["positive_support_successors"]:
            successor = states[successor_spec["state_id"]]
            successor_ids.append(successor["state_id"])
            evidence_changed = (
                source["normalized_evidence_hash"] != successor["normalized_evidence_hash"]
            )
            before_pairs = partition_pairs(source["representation_partition"])
            after_pairs = partition_pairs(successor["representation_partition"])
            representation_changed = before_pairs != after_pairs
            authority_changed = source["authority"]["entries"] != successor["authority"]["entries"]
            touches["E"] = touches["E"] or evidence_changed
            touches["R"] = touches["R"] or representation_changed
            touches["A"] = touches["A"] or authority_changed
            if evidence_changed:
                witnesses["E"].append(
                    {
                        "successor_id": successor["state_id"],
                        "before_hash": source["normalized_evidence_hash"],
                        "after_hash": successor["normalized_evidence_hash"],
                    }
                )
            if representation_changed:
                witnesses["R"].append(
                    {
                        "successor_id": successor["state_id"],
                        "split_witness_pairs": [
                            list(pair) for pair in sorted(before_pairs - after_pairs)
                        ],
                        "merge_witness_pairs": [
                            list(pair) for pair in sorted(after_pairs - before_pairs)
                        ],
                    }
                )
            if authority_changed:
                witnesses["A"].append(
                    {
                        "successor_id": successor["state_id"],
                        "before_hash": object_hash(source["authority"]["entries"]),
                        "after_hash": object_hash(successor["authority"]["entries"]),
                    }
                )
        identity = {
            "completion_id": contract["completion_id"],
            "state_id": source["state_id"],
            "action_id": action["intervention_id"],
            "successor_ids": sorted(successor_ids),
            "touches": touches,
        }
        rows.append(
            {
                "independent_touch_id": f"independent_touch:{object_hash(identity)[:20]}",
                **identity,
                "witnesses": witnesses,
                "contract_hash": contract["contract_hash"],
                "provenance_hash": object_hash(action["provenance_fact_ids"]),
            }
        )
    return rows


def audit_touch(
    independent: list[dict[str, Any]], production: list[dict[str, Any]]
) -> dict[str, Any]:
    production_by_key = {
        (row["completion_id"], row["state_id"], row["action_id"]): row for row in production
    }
    mismatches: list[dict[str, str]] = []
    for row in independent:
        key = (row["completion_id"], row["state_id"], row["action_id"])
        observed = production_by_key.get(key)
        if observed is None:
            mismatches.append({"key": repr(key), "reason": "MISSING_PRODUCTION_TOUCH"})
        elif (
            row["touches"] != observed["touches"]
            or row["successor_ids"] != observed["successor_ids"]
        ):
            mismatches.append({"key": repr(key), "reason": "TOUCH_MISMATCH"})
    if len(independent) != len(production):
        mismatches.append({"key": "touch_records", "reason": "COUNT_MISMATCH"})
    return {
        "passed": not mismatches,
        "checked": len(production),
        "matched": len(production) - len(mismatches),
        "mismatches": mismatches,
    }
