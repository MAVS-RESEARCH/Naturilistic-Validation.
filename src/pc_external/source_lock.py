"""Immutable external-source acquisition and Phase-1 manifest generation."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

from pc_external.evidence import (
    extract_native_cases,
    load_yaml,
    require_immutable_ref,
    require_run_id,
)
from pc_external.hashing import (
    byte_hash,
    canonical_json_bytes,
    canonical_json_hash,
    content_id,
    semantic_hash_bytes,
    sha256_bytes,
    write_json_atomic,
)


class SourceLockError(RuntimeError):
    """Raised when immutable source material cannot be verified."""


def _run(command: list[str], *, cwd: Path | None = None, text: bool = True) -> str | bytes:
    process = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=text,
    )
    if process.returncode != 0:
        stderr = process.stderr if text else process.stderr.decode("utf-8", errors="replace")
        raise SourceLockError(
            f"command failed ({process.returncode}): {' '.join(command)}\n{stderr}"
        )
    return process.stdout


def _safe_snapshot_path(root: Path, phase: str, source_path: str) -> Path:
    pure = PurePosixPath(source_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise SourceLockError(f"unsafe source path: {source_path}")
    target = root / phase / Path(*pure.parts)
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    if resolved_root not in resolved_target.parents:
        raise SourceLockError(f"snapshot escaped root: {source_path}")
    return target


class GitHubHistoryProvider:
    """Fetch the public PR evidence required by the Phase-1 historical lock."""

    API_ROOT = "https://api.github.com/repos/apache/polaris"

    def _get(self, url: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "pc-external-validation-v0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    def __call__(self) -> dict[str, Any]:
        pull = self._get(f"{self.API_ROOT}/pulls/4992")
        commits = self._get(f"{self.API_ROOT}/pulls/4992/commits?per_page=100")
        files = self._get(f"{self.API_ROOT}/pulls/4992/files?per_page=100")
        reviews = self._get(f"{self.API_ROOT}/pulls/4992/reviews?per_page=100")
        review_comments = self._get(f"{self.API_ROOT}/pulls/4992/comments?per_page=100")
        issue_comments = self._get(f"{self.API_ROOT}/issues/4992/comments?per_page=100")
        return {
            "pr.json": {
                key: pull.get(key)
                for key in (
                    "number",
                    "state",
                    "title",
                    "body",
                    "created_at",
                    "updated_at",
                    "closed_at",
                    "merged_at",
                    "merge_commit_sha",
                )
            }
            | {
                "base_sha": pull["base"]["sha"],
                "head_sha": pull["head"]["sha"],
                "html_url": pull["html_url"],
                "user": pull["user"]["login"],
            },
            "commits.json": [
                {
                    "sha": item["sha"],
                    "message": item["commit"]["message"],
                    "author_date": item["commit"]["author"]["date"],
                    "committer_date": item["commit"]["committer"]["date"],
                }
                for item in commits
            ],
            "files.json": [
                {
                    "filename": item["filename"],
                    "status": item["status"],
                    "additions": item["additions"],
                    "deletions": item["deletions"],
                    "changes": item["changes"],
                    "sha": item["sha"],
                }
                for item in files
            ],
            "reviews.json": [
                {
                    "id": item["id"],
                    "user": item["user"]["login"],
                    "state": item["state"],
                    "body": item["body"],
                    "submitted_at": item["submitted_at"],
                    "commit_id": item["commit_id"],
                }
                for item in reviews
            ],
            "review_comments.json": [
                {
                    "id": item["id"],
                    "user": item["user"]["login"],
                    "path": item["path"],
                    "line": item["line"],
                    "original_line": item["original_line"],
                    "body": item["body"],
                    "created_at": item["created_at"],
                    "commit_id": item["commit_id"],
                }
                for item in review_comments
            ],
            "issue_comments.json": [
                {
                    "id": item["id"],
                    "user": item["user"]["login"],
                    "body": item["body"],
                    "created_at": item["created_at"],
                }
                for item in issue_comments
            ],
        }


class SourceLocker:
    """Perform two independent Git materializations and create canonical Phase-1 evidence."""

    def __init__(
        self,
        *,
        repository_root: Path,
        run_id: str,
        history_provider: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.run_id = run_id
        self.history_provider = history_provider or GitHubHistoryProvider()
        require_run_id(run_id)

    @property
    def run_root(self) -> Path:
        return self.repository_root / "results" / "external_validation_v01" / self.run_id

    def _materialize_pass(
        self,
        *,
        experiment: dict[str, Any],
        destination: Path | None,
        pass_name: str,
    ) -> dict[str, Any]:
        system = experiment["primary_system"]
        refs = {
            "pre": system["pre_repair_ref"],
            "head": system["pr_head_ref"],
            "post": system["post_repair_ref"],
        }
        for field, value in refs.items():
            require_immutable_ref(value, f"{field}_ref")

        with tempfile.TemporaryDirectory(prefix=f"pc_ext_{pass_name}_") as temp_name:
            checkout = Path(temp_name) / "source"
            checkout.mkdir()
            _run(["git", "init", "--quiet"], cwd=checkout)
            _run(["git", "remote", "add", "origin", system["repository_origin"]], cwd=checkout)
            _run(
                [
                    "git",
                    "fetch",
                    "--quiet",
                    "--filter=blob:none",
                    "--no-tags",
                    "origin",
                    refs["pre"],
                    refs["head"],
                    refs["post"],
                ],
                cwd=checkout,
            )

            object_types = {
                name: str(_run(["git", "cat-file", "-t", ref], cwd=checkout)).strip()
                for name, ref in refs.items()
            }
            if set(object_types.values()) != {"commit"}:
                raise SourceLockError(f"one or more refs are not commits: {object_types}")
            trees = {
                name: str(_run(["git", "show", "-s", "--format=%T", ref], cwd=checkout)).strip()
                for name, ref in refs.items()
            }
            ancestry = subprocess.run(
                ["git", "merge-base", "--is-ancestor", refs["pre"], refs["post"]],
                cwd=checkout,
                check=False,
                capture_output=True,
            )
            if ancestry.returncode != 0:
                raise SourceLockError("pre-repair ref is not an ancestor of post-repair ref")

            records: list[dict[str, Any]] = []
            for spec in experiment["primary_system"]["source_artifacts"]:
                phase = spec["phase"]
                ref = refs[phase]
                source_path = spec["path"]
                data = _run(["git", "show", f"{ref}:{source_path}"], cwd=checkout, text=False)
                assert isinstance(data, bytes)
                identity = {
                    "phase": phase,
                    "source_ref": ref,
                    "source_path": source_path,
                    "byte_sha256": sha256_bytes(data),
                }
                snapshot_relative = (
                    Path("external_source")
                    / "snapshots"
                    / "apache_polaris"
                    / phase
                    / Path(*PurePosixPath(source_path).parts)
                )
                if destination is not None:
                    snapshot = _safe_snapshot_path(destination, phase, source_path)
                    snapshot.parent.mkdir(parents=True, exist_ok=True)
                    snapshot.write_bytes(data)
                records.append(
                    {
                        "artifact_id": content_id("artifact", identity),
                        "phase": phase,
                        "source_ref": ref,
                        "source_path": source_path,
                        "snapshot_path": snapshot_relative.as_posix(),
                        "role": spec["role"],
                        "allowed_influence": sorted(spec["allowed_influence"]),
                        "byte_sha256": sha256_bytes(data),
                        "semantic_sha256": semantic_hash_bytes(data),
                        "size_bytes": len(data),
                    }
                )

            return {
                "pass_name": pass_name,
                "cache_leaf": Path(temp_name).name,
                "object_types": object_types,
                "trees": trees,
                "records": sorted(records, key=lambda item: item["artifact_id"]),
            }

    def _history_records(
        self,
        history_root: Path,
        experiment: dict[str, Any],
        payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for filename, payload in sorted(payloads.items()):
            target = history_root / filename
            data = canonical_json_bytes(payload) + b"\n"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            identity = {
                "phase": "history",
                "source_ref": experiment["primary_system"]["historical_change_id"],
                "source_path": f"github_api/{filename}",
                "byte_sha256": sha256_bytes(data),
            }
            records.append(
                {
                    "artifact_id": content_id("artifact", identity),
                    "phase": "history",
                    "source_ref": experiment["primary_system"]["historical_change_id"],
                    "source_path": f"github_api/{filename}",
                    "snapshot_path": (
                        Path("external_source")
                        / "snapshots"
                        / "apache_polaris"
                        / "history"
                        / filename
                    ).as_posix(),
                    "role": "HISTORICAL_REPAIR",
                    "allowed_influence": ["INTERVENTION", "TARGET"],
                    "byte_sha256": sha256_bytes(data),
                    "semantic_sha256": semantic_hash_bytes(data),
                    "size_bytes": len(data),
                }
            )
        return records

    def _environment_lock(self, config_hashes: dict[str, str]) -> dict[str, Any]:
        git_version = str(_run(["git", "--version"])).strip()
        node_version = str(_run(["node", "--version"])).strip()
        python_version = platform.python_version()
        implementation_sha = str(
            _run(["git", "rev-parse", "HEAD"], cwd=self.repository_root)
        ).strip()
        lock_path = self.repository_root / "uv.lock"
        return {
            "python_version": python_version,
            "python_implementation": platform.python_implementation(),
            "node_version": node_version,
            "git_version": git_version,
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_machine": platform.machine(),
            "implementation_git_sha": implementation_sha,
            "uv_lock_sha256": byte_hash(lock_path) if lock_path.exists() else None,
            "config_hashes": dict(sorted(config_hashes.items())),
            "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
        }

    def lock(self) -> dict[str, Any]:
        experiment_path = self.repository_root / "configs" / "experiment.yaml"
        experiment = load_yaml(experiment_path)
        config_paths = sorted((self.repository_root / "configs").glob("*.yaml"))
        config_hashes = {path.name: byte_hash(path) for path in config_paths}

        snapshots_root = self.repository_root / "external_source" / "snapshots" / "apache_polaris"
        first = self._materialize_pass(
            experiment=experiment,
            destination=snapshots_root,
            pass_name="verification_a",
        )
        second = self._materialize_pass(
            experiment=experiment,
            destination=None,
            pass_name="verification_b",
        )

        if first["trees"] != second["trees"]:
            raise SourceLockError("independent fetches produced different tree IDs")
        first_projection = [
            {
                key: record[key]
                for key in ("artifact_id", "byte_sha256", "semantic_sha256", "size_bytes")
            }
            for record in first["records"]
        ]
        second_projection = [
            {
                key: record[key]
                for key in ("artifact_id", "byte_sha256", "semantic_sha256", "size_bytes")
            }
            for record in second["records"]
        ]
        if first_projection != second_projection:
            raise SourceLockError("independent fetches produced different artifact hashes")
        if first["cache_leaf"] == second["cache_leaf"]:
            raise SourceLockError("independent source caches unexpectedly share a path")

        history_first = self.history_provider()
        history_second = self.history_provider()
        if canonical_json_hash(history_first) != canonical_json_hash(history_second):
            raise SourceLockError("independent history fetches produced different content")
        history_records = self._history_records(
            snapshots_root / "history",
            experiment,
            history_first,
        )
        artifacts = sorted(first["records"] + history_records, key=lambda item: item["artifact_id"])
        source_tree_hash = canonical_json_hash(
            {
                "refs": {
                    "pre": experiment["primary_system"]["pre_repair_ref"],
                    "head": experiment["primary_system"]["pr_head_ref"],
                    "post": experiment["primary_system"]["post_repair_ref"],
                },
                "trees": first["trees"],
            }
        )
        manifest_without_hash = {
            "run_id": self.run_id,
            "external_system_id": experiment["primary_system"]["id"],
            "repository_origin": experiment["primary_system"]["repository_origin"],
            "pre_ref": experiment["primary_system"]["pre_repair_ref"],
            "post_ref": experiment["primary_system"]["post_repair_ref"],
            "pr_head_ref": experiment["primary_system"]["pr_head_ref"],
            "historical_change_id": experiment["primary_system"]["historical_change_id"],
            "artifacts": artifacts,
            "source_tree_hash": source_tree_hash,
            "environment_ref": (
                Path("results")
                / "external_validation_v01"
                / self.run_id
                / "manifests"
                / "environment_lock.json"
            ).as_posix(),
            "created_at": experiment["generated_at"],
            "fetch_verification": {
                "pass_count": 2,
                "object_types_valid": True,
                "ancestry_valid": True,
                "tree_ids_equal": True,
                "artifact_hashes_equal": True,
                "cache_path_invariant": True,
                "history_fetches_equal": True,
            },
        }
        manifest = {
            **manifest_without_hash,
            "manifest_hash": canonical_json_hash(manifest_without_hash),
        }
        native_case_index = extract_native_cases(
            run_id=self.run_id,
            experiment=experiment,
            manifest=manifest,
            repository_root=self.repository_root,
        )
        environment_lock = self._environment_lock(config_hashes)
        environment_lock["environment_hash"] = canonical_json_hash(environment_lock)
        run_manifest_without_hash = {
            "run_id": self.run_id,
            "experiment_version": experiment["experiment_version"],
            "phase": 1,
            "status": "SOURCE_LOCKED",
            "created_at": experiment["generated_at"],
            "source_manifest_hash": manifest["manifest_hash"],
            "native_case_index_hash": native_case_index["case_index_hash"],
            "implementation_git_sha": environment_lock["implementation_git_sha"],
            "environment_hash": environment_lock["environment_hash"],
            "config_hashes": config_hashes,
        }
        run_manifest = {
            **run_manifest_without_hash,
            "run_manifest_hash": canonical_json_hash(run_manifest_without_hash),
        }

        write_json_atomic(
            self.repository_root / "external_source" / "source_manifest.json", manifest
        )
        write_json_atomic(
            self.repository_root / "external_source" / "native_case_index.json", native_case_index
        )
        write_json_atomic(self.run_root / "manifests" / "source_manifest.json", manifest)
        write_json_atomic(self.run_root / "manifests" / "environment_lock.json", environment_lock)
        write_json_atomic(self.run_root / "manifests" / "config_hashes.json", config_hashes)
        write_json_atomic(self.run_root / "manifests" / "run_manifest.json", run_manifest)
        write_json_atomic(
            self.run_root / "preregistration" / "native_case_index.json", native_case_index
        )
        write_json_atomic(
            self.run_root / "reports" / "source_lock_determinism.json",
            {
                "pass_count": 2,
                "tree_ids_equal": True,
                "artifact_hashes_equal": True,
                "cache_path_invariant": True,
                "history_fetches_equal": True,
                "first_cache_leaf_sha256": sha256_bytes(first["cache_leaf"].encode("utf-8")),
                "second_cache_leaf_sha256": sha256_bytes(second["cache_leaf"].encode("utf-8")),
                "source_manifest_hash": manifest["manifest_hash"],
            },
        )
        return {
            "manifest": manifest,
            "native_case_index": native_case_index,
            "environment_lock": environment_lock,
            "config_hashes": config_hashes,
            "run_manifest": run_manifest,
        }


def copy_json(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
