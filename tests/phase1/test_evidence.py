from __future__ import annotations

import json
from pathlib import Path

import pytest

from pc_external.evidence import (
    EvidenceError,
    artifact_lookup,
    build_evidence_index,
    build_preregistration,
    count_manual_resource_label_keys,
    extract_native_cases,
    require_immutable_ref,
    require_run_id,
)
from pc_external.hashing import canonical_json_hash, content_id, semantic_hash_bytes

ROOT = Path(__file__).resolve().parents[2]


def test_immutable_ref_fixture() -> None:
    fixture = json.loads((ROOT / "tests" / "fixtures" / "immutable_refs.json").read_text())
    for value in fixture["valid"]:
        require_immutable_ref(value, "test_ref")
    for value in fixture["invalid"]:
        with pytest.raises(EvidenceError):
            require_immutable_ref(value, "test_ref")


@pytest.mark.parametrize("run_id", ["external_v01", "run.2026-08-26", "a_b-c"])
def test_run_id_accepts_explicit_safe_names(run_id: str) -> None:
    require_run_id(run_id)


@pytest.mark.parametrize("run_id", ["../escape", "a/b", "ab", "", " space"])
def test_run_id_rejects_unsafe_names(run_id: str) -> None:
    with pytest.raises(EvidenceError):
        require_run_id(run_id)


def test_artifact_lookup_rejects_duplicate_ids_and_paths() -> None:
    base = {
        "artifact_id": "artifact:123",
        "phase": "post",
        "source_path": "a.java",
    }
    with pytest.raises(EvidenceError, match="duplicate artifact_id"):
        artifact_lookup({"artifacts": [base, {**base, "source_path": "b.java"}]})
    with pytest.raises(EvidenceError, match="duplicate phase/source_path"):
        artifact_lookup({"artifacts": [base, {**base, "artifact_id": "artifact:456"}]})


def test_manual_resource_label_scan_checks_keys_not_text_values() -> None:
    assert count_manual_resource_label_keys({"description": "E R A", "P_R": "partition"}) == 0
    assert count_manual_resource_label_keys({"resource_touch": ["R"]}) == 1


def test_source_only_case_extractor_is_deterministic(tmp_path: Path) -> None:
    source_path = "tests/NativeCaseFixture.java"
    snapshot = tmp_path / "external_source" / "snapshots" / "apache_polaris" / "post" / source_path
    snapshot.parent.mkdir(parents=True)
    data = (ROOT / "tests" / "fixtures" / "native_case_java.txt").read_bytes()
    snapshot.write_bytes(data)
    identity = {
        "phase": "post",
        "source_ref": "d" * 40,
        "source_path": source_path,
        "byte_sha256": "0" * 64,
    }
    artifact = {
        "artifact_id": content_id("artifact", identity),
        "phase": "post",
        "source_path": source_path,
        "snapshot_path": snapshot.relative_to(tmp_path).as_posix(),
    }
    manifest_without_hash = {"artifacts": [artifact]}
    manifest = {
        **manifest_without_hash,
        "manifest_hash": canonical_json_hash(manifest_without_hash),
    }
    experiment = {
        "case_population": {
            "rule_id": "fixture_rule",
            "description": "fixture",
            "selector": {
                "files": [source_path],
                "assertion_regex": r'(?:get|path)\("realm"\).*?isEqualTo\("([^"]+)"\)',
            },
        }
    }
    first = extract_native_cases(
        run_id="fixture_run",
        experiment=experiment,
        manifest=manifest,
        repository_root=tmp_path,
    )
    second = extract_native_cases(
        run_id="fixture_run",
        experiment=experiment,
        manifest=manifest,
        repository_root=tmp_path,
    )
    assert first == second
    assert first["case_count"] == 2
    assert first["distinct_expected_realms"] == ["realm-a", "realm-b"]
    assert all(case["origin"] == "UPSTREAM_NATIVE" for case in first["cases"])
    assert semantic_hash_bytes(data)


def test_evidence_index_and_preregistration_lock_nonclaims() -> None:
    manifest = {
        "manifest_hash": "a" * 64,
        "artifacts": [
            {
                "artifact_id": "artifact:source",
                "role": "SOURCE_SEMANTICS",
                "phase": "pre",
                "source_path": "Context.java",
            }
        ],
    }
    experiment = {
        "case_population": {"rule_id": "rule", "description": "source-only"},
        "target_contract": {
            "kind": "AUTHORIZATION_INPUT_CERTIFICATE",
            "predicate": "realm equality",
            "terminal_evidence": "native assertion",
            "limitation": "paired decision absent",
        },
        "intervention_surface": {
            "admitted": [{"id": "historical_repair"}],
            "excluded_candidates": [{"id": "invented_route", "reason": "unsupported"}],
        },
        "primary_system": {
            "id": "system",
            "pre_repair_ref": "a" * 40,
            "post_repair_ref": "b" * 40,
            "historical_change_id": "change#1",
        },
        "freeze_sets": [{"id": f"F{i}", "forbidden": []} for i in range(8)],
        "claims": {
            "prevalence": False,
            "superiority": False,
            "deployment_readiness": False,
            "universal_zero_error": False,
        },
        "stop_conditions": ["STOP"],
    }
    native = {
        "case_count": 1,
        "distinct_expected_realms": ["realm-a"],
    }
    evidence = build_evidence_index(
        run_id="fixture_run",
        experiment=experiment,
        manifest=manifest,
        native_case_index=native,
    )
    preregistration = build_preregistration(
        run_id="fixture_run",
        experiment=experiment,
        costs={"primary": {"type": "unit"}, "secondary": []},
        completion_policy={"route_degeneracy_rule": {"classify_before_results": True}},
        manifest=manifest,
        config_hashes={"experiment.yaml": "c" * 64},
    )
    assert evidence["manual_resource_label_count"] == 0
    assert evidence["intervention_surface"]["admitted_count"] == 1
    assert preregistration["sealed_before_phase2"] is True
    assert all(value is False for value in preregistration["nonclaims"].values())
