from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def cleaner(repo_root: Path, run_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "clean_named_run.py"),
            "--run-id",
            run_id,
            "--repo-root",
            str(repo_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cleaner_removes_only_named_unsealed_run(tmp_path: Path) -> None:
    results = tmp_path / "results" / "external_validation_v01"
    target = results / "run_a"
    sibling = results / "run_b"
    target.mkdir(parents=True)
    sibling.mkdir()
    (target / "x.txt").write_text("x")
    result = cleaner(tmp_path, "run_a")
    assert result.returncode == 0
    assert not target.exists()
    assert sibling.exists()


def test_cleaner_refuses_sealed_run(tmp_path: Path) -> None:
    target = tmp_path / "results" / "external_validation_v01" / "sealed_run"
    target.mkdir(parents=True)
    (target / "SEALED").write_text("sealed")
    result = cleaner(tmp_path, "sealed_run")
    assert result.returncode != 0
    assert target.exists()


def test_cleaner_rejects_path_traversal(tmp_path: Path) -> None:
    result = cleaner(tmp_path, "../escape")
    assert result.returncode != 0
    assert not (tmp_path / "results" / "escape").exists()
