from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = os.environ.get("PC_RUN_ID")


pytestmark = [
    pytest.mark.authoritative,
    pytest.mark.skipif(
        not RUN_ID, reason="PC_RUN_ID is required for authoritative artifact checks"
    ),
]


def authoritative_path(*parts: str) -> Path:
    if not RUN_ID:
        pytest.skip("PC_RUN_ID is required for authoritative artifact checks")
    return ROOT / "results" / "external_validation_v01" / RUN_ID / Path(*parts)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_authoritative_phase1_gate_is_complete() -> None:
    report = read_json(authoritative_path("reports", "phase1_eligibility.json"))
    assert report["overall_status"] == "ELIGIBLE"
    assert report["phase2_authorized"] is True
    assert len(report["gates"]) == 8
    assert all(gate["passed"] for gate in report["gates"])
    assert report["metrics"]["artifact_hash_coverage_percent"] == 100.0
    assert report["metrics"]["native_case_source_linkage_percent"] == 100.0
    assert report["metrics"]["manual_resource_label_count"] == 0
    assert report["metrics"]["pc_generated_primary_case_count"] == 0


def test_authoritative_native_case_population_is_source_derived() -> None:
    index = read_json(ROOT / "external_source" / "native_case_index.json")
    assert index["case_count"] == 8
    assert len(index["distinct_expected_realms"]) >= 5
    assert all(case["origin"] == "UPSTREAM_NATIVE" for case in index["cases"])
    assert all(case["target_class"] == "AUTHORIZATION_INPUT_CERTIFICATE" for case in index["cases"])


def test_authoritative_determinism_and_replay_reports_pass() -> None:
    source = read_json(authoritative_path("reports", "source_lock_determinism.json"))
    cases = read_json(authoritative_path("reports", "case_index_determinism.json"))
    replay = read_json(authoritative_path("reports", "native_replay.json"))
    console_registry = read_json(authoritative_path("reports", "console_log_registry.json"))
    assert source["pass_count"] == 2
    assert source["artifact_hashes_equal"] is True
    assert source["history_fetches_equal"] is True
    assert source["independent_cache_paths_distinct"] is True
    assert cases["exact_match"] is True
    assert replay["passed"] is True
    assert all(replay["checks"].values())
    assert console_registry["statement_count"] >= 20
    assert console_registry["all_comments_adjacent"] is True
