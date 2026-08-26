from __future__ import annotations

import json
from pathlib import Path

import pytest

from pc_external.completions import CompletionError, enumerate_completions

ROOT = Path(__file__).resolve().parents[2]


def compiler(base: dict, choices: dict) -> dict:
    return {**base, "choices": choices}


def test_exact_completion_enumeration_and_dimension_permutation_invariance() -> None:
    fixture = json.loads((ROOT / "tests" / "fixtures" / "phase2_completions.json").read_text())
    forward = enumerate_completions({"base": True}, fixture["dimensions"], compiler, cap=128)
    reverse = enumerate_completions(
        {"base": True}, reversed(fixture["dimensions"]), compiler, cap=128
    )
    assert forward == reverse
    assert forward["enumerated_choice_vectors"] == fixture["expected_choice_vectors"]
    assert forward["completion_count"] == 4
    assert forward["sampled"] is False


def test_completion_deduplication_cap_and_author_prior_rejection() -> None:
    dimension = {"dimension_id": "d", "source_grounded": True, "choices": [1, 2]}
    deduplicated = enumerate_completions(
        {"base": True}, [dimension], lambda base, choices: dict(base), cap=128
    )
    assert deduplicated["completion_count"] == 1
    assert deduplicated["deduplicated_count"] == 1
    with pytest.raises(CompletionError, match="exceeds cap"):
        enumerate_completions({"base": True}, [dimension], compiler, cap=1)
    with pytest.raises(CompletionError, match="author-prior"):
        enumerate_completions(
            {"base": True}, [{**dimension, "source_grounded": False}], compiler, cap=128
        )
