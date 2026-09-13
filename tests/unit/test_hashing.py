from __future__ import annotations

import json

from hypothesis import given
from hypothesis import strategies as st

from pc_external.hashing import (
    canonical_json_bytes,
    canonical_json_hash,
    content_id,
    normalize_text_bytes,
    semantic_hash_bytes,
)


def test_canonical_json_ignores_mapping_insertion_order() -> None:
    left = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
    right = {"nested": {"x": 1, "y": 2}, "a": 1, "b": 2}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_hash(left) == canonical_json_hash(right)


def test_semantic_hash_normalizes_line_endings_only() -> None:
    assert semantic_hash_bytes(b"a\r\nb\r\n") == semantic_hash_bytes(b"a\nb\n")
    assert normalize_text_bytes(b"a\rb") == b"a\nb"
    assert semantic_hash_bytes(b"a\nb") != semantic_hash_bytes(b"a\nc")


def test_content_id_is_stable_and_namespaced() -> None:
    assert content_id("case", {"x": 1}) == content_id("case", {"x": 1})
    assert content_id("case", {"x": 1}).startswith("case:")


@given(st.dictionaries(st.text(min_size=1, max_size=12), st.integers(), max_size=20))
def test_json_round_trip_preserves_canonical_hash(value: dict[str, int]) -> None:
    encoded = canonical_json_bytes(value)
    decoded = json.loads(encoded)
    assert canonical_json_hash(decoded) == canonical_json_hash(value)
