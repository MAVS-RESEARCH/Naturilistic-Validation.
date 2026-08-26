"""Authority and controller-observation normalization with taint rejection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pc_external.hashing import canonical_json_hash


class AuthorityError(ValueError):
    """Raised when authority or observation data is not admissible."""


def canonical_authority(entries: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Normalize admitted authority independently of whether fields exist in a state."""
    normalized = []
    for entry in entries:
        normalized.append(
            {
                "kind": str(entry["kind"]),
                "identifier": str(entry["identifier"]),
                "admissible": bool(entry["admissible"]),
                "provenance_fact_ids": sorted(set(entry["provenance_fact_ids"])),
            }
        )
    normalized.sort(key=lambda item: (item["kind"], item["identifier"]))
    value = {"entries": normalized}
    return {**value, "authority_hash": canonical_json_hash(value)}


def authority_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "changed": before["authority_hash"] != after["authority_hash"],
        "before_authority_hash": before["authority_hash"],
        "after_authority_hash": after["authority_hash"],
    }


def controller_observation(
    visible_fields: Iterable[str], *, evaluator_only_values: Iterable[str]
) -> dict[str, Any]:
    """Create a value-free observation schema and reject evaluator-truth leakage."""
    fields = sorted(set(visible_fields))
    forbidden = {value for value in evaluator_only_values if value}
    leaked = sorted(forbidden.intersection(fields))
    if leaked:
        raise AuthorityError(f"evaluator-only truth leaked into controller observation: {leaked}")
    value = {"visible_fields": fields, "contains_evaluator_truth": False}
    return {**value, "observation_hash": canonical_json_hash(value)}


def assert_no_taint(value: Any, evaluator_only_values: Iterable[str]) -> None:
    forbidden = {item for item in evaluator_only_values if item}

    def visit(node: Any) -> None:
        if isinstance(node, str) and node in forbidden:
            raise AuthorityError("evaluator-only truth present in controller-visible value")
        if isinstance(node, Mapping):
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
