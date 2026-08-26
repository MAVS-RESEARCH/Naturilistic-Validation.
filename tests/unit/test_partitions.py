from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pc_external.partitions import (
    PartitionError,
    canonical_partition,
    partition_diff,
    validate_partition,
)

ROOT = Path(__file__).resolve().parents[2]


def fixture() -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "phase2_partitions.json").read_text())


def test_partition_rename_invariance_and_witness_generation() -> None:
    data = fixture()
    before = canonical_partition(data["universe"], data["before_keys"])
    renamed = canonical_partition(data["universe"], {item: "renamed" for item in data["universe"]})
    after = canonical_partition(data["universe"], data["after_keys"])
    assert before == renamed
    difference = partition_diff(before, after)
    assert difference["changed"] is True
    assert len(difference["split_witness_pairs"]) == 3
    assert difference["merge_witness_pairs"] == []


def test_common_domain_typing_rejects_missing_duplicate_and_cross_domain_members() -> None:
    data = fixture()
    with pytest.raises(PartitionError, match="exactly the common history domain"):
        canonical_partition(data["universe"], {"history:a": "x"})
    partition = canonical_partition(data["universe"], data["before_keys"])
    corrupted = {**partition, "blocks": [["history:a", "history:a", "history:b"]]}
    with pytest.raises(PartitionError, match="exactly once"):
        validate_partition(corrupted, data["universe"])
    other = canonical_partition(["history:x"], {"history:x": "x"})
    with pytest.raises(PartitionError, match="different history domains"):
        partition_diff(partition, other)


@given(st.permutations(["history:a", "history:b", "history:c"]))
def test_history_order_and_duplicate_invariance(order: list[str]) -> None:
    keys = {item: item[-1] for item in order}
    assert canonical_partition(order, keys) == canonical_partition(order + order, keys)
