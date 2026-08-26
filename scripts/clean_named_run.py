#!/usr/bin/env python3
"""Safely remove one explicitly named, unsealed external-validation run."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


sys.path.insert(0, str(_repository_root() / "src"))

from pc_external.eventlog import console  # noqa: E402
from pc_external.evidence import require_run_id  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", type=Path, default=_repository_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_run_id(args.run_id)
    root = args.repo_root.resolve()
    results_root = (root / "results" / "external_validation_v01").resolve()
    target = (results_root / args.run_id).resolve()
    # console.log: external.phase1.clean_named_run.start
    console.log("external.phase1.clean_named_run.start", run_id=args.run_id)
    if target.parent != results_root:
        raise RuntimeError("resolved run target is not a direct child of the results root")
    if not target.exists():
        # console.log: external.phase1.clean_named_run.noop
        console.log(
            "external.phase1.clean_named_run.noop", run_id=args.run_id, reason="target_absent"
        )
        return 0
    if (target / "SEALED").exists():
        # console.log: external.phase1.clean_named_run.refused
        console.log("external.phase1.clean_named_run.refused", run_id=args.run_id, reason="sealed")
        raise RuntimeError("refusing to remove a sealed run")
    shutil.rmtree(target)
    # console.log: external.phase1.clean_named_run.complete
    console.log("external.phase1.clean_named_run.complete", run_id=args.run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
