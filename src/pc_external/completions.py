"""Exact finite semantic-completion enumeration."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from itertools import product
from typing import Any

from pc_external.hashing import canonical_json_hash, content_id


class CompletionError(ValueError):
    """Raised when exact semantic completion is impossible under the sealed policy."""


def enumerate_completions(
    base_contract: Mapping[str, Any],
    dimensions: Iterable[Mapping[str, Any]],
    compiler: Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]],
    *,
    cap: int,
) -> dict[str, Any]:
    """Enumerate, deduplicate, and hash all source-grounded completion choices."""
    ordered = sorted(dimensions, key=lambda item: item["dimension_id"])
    if any(item.get("source_grounded") is not True for item in ordered):
        raise CompletionError("author-prior completion dimension is prohibited")
    choice_vectors = product(*(item["choices"] for item in ordered)) if ordered else [()]
    candidates: dict[str, dict[str, Any]] = {}
    enumerated = 0
    for vector in choice_vectors:
        enumerated += 1
        if enumerated > cap:
            raise CompletionError("exact completion count exceeds cap")
        choices = {
            dimension["dimension_id"]: choice
            for dimension, choice in zip(ordered, vector, strict=True)
        }
        contract = compiler(base_contract, choices)
        contract_hash = contract.get("contract_hash", canonical_json_hash(contract))
        candidates.setdefault(
            contract_hash,
            {
                "completion_id": contract.get(
                    "completion_id", content_id("completion", {"contract_hash": contract_hash})
                ),
                "contract_hash": contract_hash,
                "choices": choices,
            },
        )
    completions = sorted(candidates.values(), key=lambda item: item["completion_id"])
    status = "IDENTIFIED" if len(completions) == 1 else "PARTIALLY_IDENTIFIED"
    value = {
        "mode": "EXACT_ENUMERATION",
        "cap": cap,
        "dimension_count": len(ordered),
        "enumerated_choice_vectors": enumerated,
        "completion_count": len(completions),
        "deduplicated_count": enumerated - len(completions),
        "sampled": False,
        "status": status,
        "completions": completions,
    }
    return {**value, "completion_set_hash": canonical_json_hash(value)}
