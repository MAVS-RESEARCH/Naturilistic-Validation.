#!/usr/bin/env python3
"""Create the immutable Phase-1 preregistration and evidence index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.evidence import (  # noqa: E402
    build_evidence_index,
    build_preregistration,
    load_yaml,
)
from pc_external.hashing import write_json_atomic  # noqa: E402


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    # console.log: external.phase1.preregister.start
    console.log("external.phase1.preregister.start", run_id=args.run_id)

    experiment = load_yaml(root / "configs" / "experiment.yaml")
    costs = load_yaml(root / "configs" / "costs.yaml")
    completion = load_yaml(root / "configs" / "completion_policy.yaml")
    manifest = _read_json(root / "external_source" / "source_manifest.json")
    native_cases = _read_json(root / "external_source" / "native_case_index.json")
    config_hashes = _read_json(run_root / "manifests" / "config_hashes.json")

    # console.log: external.phase1.preregister.index_evidence
    console.log("external.phase1.preregister.index_evidence", run_id=args.run_id)
    evidence_index = build_evidence_index(
        run_id=args.run_id,
        experiment=experiment,
        manifest=manifest,
        native_case_index=native_cases,
    )
    preregistration = build_preregistration(
        run_id=args.run_id,
        experiment=experiment,
        costs=costs,
        completion_policy=completion,
        manifest=manifest,
        config_hashes=config_hashes,
    )

    write_json_atomic(root / "external_source" / "evidence_index.json", evidence_index)
    write_json_atomic(run_root / "preregistration" / "preregistration.json", preregistration)
    # console.log: external.phase1.preregister.complete
    console.log(
        "external.phase1.preregister.complete",
        run_id=args.run_id,
        preregistration_hash=preregistration["preregistration_hash"],
        evidence_index_hash=evidence_index["evidence_index_hash"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
