from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from pc_external.source_lock import SourceLocker


def git(path: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return process.stdout.strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_source_locker_uses_two_independent_materializations(tmp_path: Path) -> None:
    source = tmp_path / "upstream"
    source.mkdir()
    git(source, "init", "--quiet")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@example.test")
    (source / "Context.java").write_text(
        "interface Context { String requestId(); }\n", encoding="utf-8"
    )
    (source / "NativeTest.java").write_text("class NativeTest {}\n", encoding="utf-8")
    pre = commit(source, "pre")
    (source / "Context.java").write_text(
        "interface Context { String requestId(); String realm(); }\n", encoding="utf-8"
    )
    head = commit(source, "head")
    (source / "NativeTest.java").write_text(
        '@Test void realmCase() { assertThat(context.path("realm").asText())'
        '.isEqualTo("fixture-realm"); }\n',
        encoding="utf-8",
    )
    post = commit(source, "post")

    project = tmp_path / "project"
    project.mkdir()
    git(project, "init", "--quiet")
    git(project, "config", "user.name", "Fixture")
    git(project, "config", "user.email", "fixture@example.test")
    (project / "configs").mkdir()
    experiment = {
        "experiment_version": "fixture_v01",
        "generated_at": "2026-08-26T00:00:00Z",
        "primary_system": {
            "id": "fixture_system",
            "repository_origin": source.as_uri(),
            "pre_repair_ref": pre,
            "pr_head_ref": head,
            "post_repair_ref": post,
            "historical_change_id": "fixture#1",
            "source_artifacts": [
                {
                    "phase": "pre",
                    "path": "Context.java",
                    "role": "SOURCE_SEMANTICS",
                    "allowed_influence": ["TEST"],
                },
                {
                    "phase": "post",
                    "path": "Context.java",
                    "role": "HISTORICAL_REPAIR",
                    "allowed_influence": ["TEST"],
                },
                {
                    "phase": "post",
                    "path": "NativeTest.java",
                    "role": "NATIVE_TEST",
                    "allowed_influence": ["NATIVE_CASE"],
                },
            ],
        },
        "case_population": {
            "rule_id": "fixture_rule",
            "description": "fixture",
            "selector": {
                "files": ["NativeTest.java"],
                "assertion_regex": r'(?:get|path)\("realm"\).*?isEqualTo\("([^"]+)"\)',
            },
        },
    }
    (project / "configs" / "experiment.yaml").write_text(
        yaml.safe_dump(experiment), encoding="utf-8"
    )
    (project / "uv.lock").write_text("fixture\n", encoding="utf-8")
    (project / "README.md").write_text("fixture\n", encoding="utf-8")
    commit(project, "project")

    history = {
        "pr.json": {"number": 1, "state": "closed"},
        "commits.json": [],
        "files.json": [],
        "reviews.json": [],
        "review_comments.json": [],
        "issue_comments.json": [],
    }
    locker = SourceLocker(
        repository_root=project,
        run_id="fixture_run",
        history_provider=lambda: history,
    )
    result = locker.lock()
    assert result["manifest"]["fetch_verification"]["pass_count"] == 2
    assert result["manifest"]["fetch_verification"]["artifact_hashes_equal"] is True
    assert result["manifest"]["fetch_verification"]["cache_path_invariant"] is True
    assert result["native_case_index"]["case_count"] == 1
    assert (project / "external_source" / "source_manifest.json").is_file()
