from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from pc_external.authority import canonical_authority
from pc_external.hashing import canonical_json_bytes
from pc_external.partitions import canonical_partition


@given(st.permutations(["history:a", "history:b", "history:c", "history:d"]))
def test_u_h_and_serialization_permutation_invariance(order: list[str]) -> None:
    keys = {item: item[-1] for item in order}
    forward = canonical_partition(order, keys)
    reverse = canonical_partition(reversed(order), keys)
    assert canonical_json_bytes(forward) == canonical_json_bytes(reverse)


@given(st.permutations(["a", "b", "c"]))
def test_artifact_and_action_provenance_permutation_invariance(order: list[str]) -> None:
    entry = {
        "kind": "SOURCE",
        "identifier": "opa",
        "admissible": True,
        "provenance_fact_ids": order,
    }
    assert canonical_authority([entry]) == canonical_authority(
        [{**entry, "provenance_fact_ids": list(reversed(order))}]
    )
