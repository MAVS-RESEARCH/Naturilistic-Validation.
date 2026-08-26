"""Canonical partitions over a shared history universe."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Iterable, Mapping
from itertools import combinations
from typing import Any

from pc_external.hashing import canonical_json_hash


class PartitionError(ValueError):
    """Raised when a partition violates common-domain typing."""


def canonical_partition(
    universe: Iterable[str], representation_keys: Mapping[str, Hashable]
) -> dict[str, Any]:
    """Group a common history domain by representation equivalence.

    Raw representation keys are intentionally discarded from the result.
    """
    history_ids = sorted(set(universe))
    if not history_ids:
        raise PartitionError("history universe must not be empty")
    if set(representation_keys) != set(history_ids):
        raise PartitionError("representation keys must have exactly the common history domain")
    grouped: dict[Hashable, list[str]] = defaultdict(list)
    for history_id in history_ids:
        grouped[representation_keys[history_id]].append(history_id)
    blocks = sorted((sorted(members) for members in grouped.values()), key=lambda block: block[0])
    value = {"history_domain": history_ids, "blocks": blocks}
    return {**value, "partition_hash": canonical_json_hash(value)}


def validate_partition(partition: Mapping[str, Any], universe: Iterable[str]) -> None:
    expected = sorted(set(universe))
    members = [member for block in partition["blocks"] for member in block]
    if sorted(members) != expected or len(members) != len(set(members)):
        raise PartitionError("partition must cover every history exactly once")
    if partition["history_domain"] != expected:
        raise PartitionError("partition history_domain differs from common universe")
    payload = {"history_domain": partition["history_domain"], "blocks": partition["blocks"]}
    if partition["partition_hash"] != canonical_json_hash(payload):
        raise PartitionError("partition hash mismatch")


def equivalent_pairs(partition: Mapping[str, Any]) -> set[tuple[str, str]]:
    return {tuple(sorted(pair)) for block in partition["blocks"] for pair in combinations(block, 2)}


def partition_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Compare equivalence relations and emit concrete witness pairs."""
    if before["history_domain"] != after["history_domain"]:
        raise PartitionError("cannot compare partitions over different history domains")
    before_pairs = equivalent_pairs(before)
    after_pairs = equivalent_pairs(after)
    split = sorted(before_pairs - after_pairs)
    merged = sorted(after_pairs - before_pairs)
    return {
        "changed": bool(split or merged),
        "split_witness_pairs": [list(pair) for pair in split],
        "merge_witness_pairs": [list(pair) for pair in merged],
        "before_partition_hash": before["partition_hash"],
        "after_partition_hash": after["partition_hash"],
    }
