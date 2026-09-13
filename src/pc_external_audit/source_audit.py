"""Independent source, case-population, and semantic-locator audit primitives."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def object_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def semantic_hash(path: Path) -> str:
    data = path.read_bytes()
    try:
        data = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode()
    except UnicodeDecodeError:
        pass
    return hashlib.sha256(data).hexdigest()


def verify_self_hash(value: dict[str, Any], field: str) -> bool:
    payload = {key: item for key, item in value.items() if key != field}
    return value.get(field) == object_hash(payload)


def reconstruct_native_cases(
    root: Path, manifest: dict[str, Any], preregistration: dict[str, Any]
) -> list[dict[str, str]]:
    selector = preregistration["native_case_rule"]["selector"]
    assertion = re.compile(selector["assertion_regex"], re.DOTALL)
    method_name = re.compile(r"\bvoid\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    artifacts = {(item["phase"], item["source_path"]): item for item in manifest["artifacts"]}
    rows: list[dict[str, str]] = []
    for source_path in sorted(selector["files"]):
        artifact = artifacts[("post", source_path)]
        text = (root / artifact["snapshot_path"]).read_text(encoding="utf-8")
        for chunk in text.split("@Test")[1:]:
            method = method_name.search(chunk)
            if not method:
                continue
            for match in assertion.finditer(chunk):
                rows.append(
                    {
                        "source_case_id": f"{source_path}::{method.group(1)}",
                        "expected_realm": match.group(1),
                    }
                )
    return sorted(rows, key=lambda item: (item["source_case_id"], item["expected_realm"]))


def verify_locators(root: Path, facts: list[dict[str, Any]]) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []
    for fact in facts:
        locator = fact["locator"]
        path = root / locator["path"]
        if not path.is_file():
            mismatches.append({"fact_id": fact["fact_id"], "reason": "MISSING_LOCATOR_FILE"})
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        start, end = locator["start_line"], locator["end_line"]
        if start < 1 or end < start or end > len(lines):
            mismatches.append({"fact_id": fact["fact_id"], "reason": "INVALID_LINE_RANGE"})
            continue
        quote = "\n".join(lines[start - 1 : end]).encode()
        if hashlib.sha256(quote).hexdigest() != locator["quote_sha256"]:
            mismatches.append({"fact_id": fact["fact_id"], "reason": "QUOTE_HASH_MISMATCH"})
    return mismatches


def audit_source(
    root: Path,
    manifest: dict[str, Any],
    preregistration: dict[str, Any],
    native_index: dict[str, Any],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    mismatches: list[dict[str, str]] = []
    if not verify_self_hash(manifest, "manifest_hash"):
        mismatches.append({"path": "external_source/source_manifest.json", "reason": "SELF_HASH"})
    for artifact in manifest["artifacts"]:
        path = root / artifact["snapshot_path"]
        if not path.is_file():
            mismatches.append({"path": artifact["snapshot_path"], "reason": "MISSING"})
            continue
        if file_hash(path) != artifact["byte_sha256"]:
            mismatches.append({"path": artifact["snapshot_path"], "reason": "BYTE_HASH"})
        if semantic_hash(path) != artifact["semantic_sha256"]:
            mismatches.append({"path": artifact["snapshot_path"], "reason": "SEMANTIC_HASH"})
    reconstructed = reconstruct_native_cases(root, manifest, preregistration)
    recorded = sorted(
        (
            {
                "source_case_id": case["source_case_ids"][0],
                "expected_realm": case["expected_realm"],
            }
            for case in native_index["cases"]
        ),
        key=lambda item: (item["source_case_id"], item["expected_realm"]),
    )
    if reconstructed != recorded:
        mismatches.append({"path": "native_case_index.json", "reason": "CASE_RECONSTRUCTION"})
    mismatches.extend(verify_locators(root, facts))
    return {
        "passed": not mismatches,
        "artifact_count": len(manifest["artifacts"]),
        "case_count": len(reconstructed),
        "semantic_locator_count": len(facts),
        "mismatches": mismatches,
    }
