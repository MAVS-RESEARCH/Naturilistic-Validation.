#!/usr/bin/env python3
"""Materialize and hash-lock the Phase-1 Apache Polaris evidence set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.source_lock import SourceLocker  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    # console.log: external.phase1.lock_source.start
    console.log("external.phase1.lock_source.start", run_id=args.run_id)
    locker = SourceLocker(repository_root=root, run_id=args.run_id)
    # console.log: external.phase1.lock_source.materialize
    console.log(
        "external.phase1.lock_source.materialize",
        repository_origin="https://github.com/apache/polaris.git",
    )
    result = locker.lock()
    # console.log: external.phase1.lock_source.complete
    console.log(
        "external.phase1.lock_source.complete",
        run_id=args.run_id,
        artifact_count=len(result["manifest"]["artifacts"]),
        case_count=result["native_case_index"]["case_count"],
        manifest_hash=result["manifest"]["manifest_hash"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
