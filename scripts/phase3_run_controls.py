#!/usr/bin/env python3
"""Execute the ten mandatory Phase-3 controls on isolated contract copies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root()))
sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.controls import run_controls, solve_contract_digest  # noqa: E402
from pc_external.eventlog import console  # noqa: E402
from pc_external.hashing import byte_hash, canonical_json_hash, write_jsonl_atomic  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    run_root = root / "results" / "external_validation_v01" / args.run_id
    contract_root = run_root / "contract"
    # console.log: external.phase3.run_controls.start
    console.log("external.phase3.run_controls.start", run_id=args.run_id)

    # console.log: external.phase3.run_controls.verify_isolation_boundary
    console.log("external.phase3.run_controls.verify_isolation_boundary", run_id=args.run_id)
    seal = load(contract_root / "CONTRACT_SEALED")
    for name, expected in seal["artifact_hashes"].items():
        if byte_hash(contract_root / name) != expected:
            raise RuntimeError(f"control boundary found upstream mutation: {name}")
    contract = load(contract_root / "extensional_contract.json")
    before_hash = canonical_json_hash(contract)
    touches = {
        row["action_id"]: {"E": row["touch_E"], "R": row["touch_R"], "A": row["touch_A"]}
        for row in pq.read_table(contract_root / "touch_records.parquet").to_pylist()
    }

    # console.log: external.phase3.run_controls.execute_c1_c10
    console.log("external.phase3.run_controls.execute_c1_c10", run_id=args.run_id)
    results = run_controls(contract, touches, solve_contract_digest)
    if len(results) != 10 or len({item["control_id"] for item in results}) != 10:
        raise RuntimeError("mandatory control allocation is not exactly C1-C10")
    if not all(item["passed"] for item in results):
        raise RuntimeError("one or more mandatory controls failed")
    if canonical_json_hash(contract) != before_hash:
        raise RuntimeError("isolated controls mutated the loaded authoritative contract")
    write_jsonl_atomic(run_root / "controls" / "control_results.jsonl", results)

    # console.log: external.phase3.run_controls.complete
    console.log(
        "external.phase3.run_controls.complete",
        run_id=args.run_id,
        passed=sum(item["passed"] for item in results),
        required=10,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
