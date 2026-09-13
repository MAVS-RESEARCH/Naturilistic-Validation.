from __future__ import annotations

import copy
from pathlib import Path

import pytest

from pc_external.evidence import EvidenceError, artifact_lookup
from scripts.phase1_validate import (
    require_phase1_configs_sealed,
    verify_artifacts,
    verify_self_hash,
)


def test_manifest_self_hash_detects_mutation() -> None:
    manifest = {
        "run_id": "run_a",
        "artifacts": [],
    }
    from pc_external.hashing import canonical_json_hash

    manifest["manifest_hash"] = canonical_json_hash({"run_id": "run_a", "artifacts": []})
    verify_self_hash(manifest, "manifest_hash")
    corrupted = copy.deepcopy(manifest)
    corrupted["run_id"] = "run_b"
    with pytest.raises(EvidenceError, match="manifest_hash mismatch"):
        verify_self_hash(corrupted, "manifest_hash")


def test_manifest_duplicate_artifact_is_rejected() -> None:
    artifact = {"artifact_id": "artifact:abc", "phase": "pre", "source_path": "x"}
    with pytest.raises(EvidenceError):
        artifact_lookup({"artifacts": [artifact, artifact]})


def test_snapshot_byte_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    snapshot = tmp_path / "external_source" / "snapshot.txt"
    snapshot.parent.mkdir()
    snapshot.write_text("corrupted", encoding="utf-8")
    manifest = {
        "artifacts": [
            {
                "artifact_id": "artifact:abc",
                "phase": "pre",
                "source_path": "snapshot.txt",
                "snapshot_path": "external_source/snapshot.txt",
                "byte_sha256": "0" * 64,
                "semantic_sha256": "0" * 64,
            }
        ]
    }
    with pytest.raises(EvidenceError, match="byte hash mismatch"):
        verify_artifacts(tmp_path, manifest)


def test_unsealed_configuration_is_rejected() -> None:
    require_phase1_configs_sealed({"experiment": {"phase1_sealed": True}})
    with pytest.raises(EvidenceError, match="configuration is not Phase-1 sealed"):
        require_phase1_configs_sealed({"experiment": {"phase1_sealed": False}})
