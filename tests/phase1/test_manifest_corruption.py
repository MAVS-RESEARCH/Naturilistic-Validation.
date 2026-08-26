from __future__ import annotations

import copy

import pytest

from pc_external.evidence import EvidenceError, artifact_lookup
from scripts.phase1_validate import verify_self_hash


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
