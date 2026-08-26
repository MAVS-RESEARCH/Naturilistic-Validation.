"""Canonical serialization and hashing primitives."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Return stable UTF-8 JSON bytes for a JSON-compatible value."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def byte_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text_bytes(data: bytes) -> bytes:
    """Normalize UTF-8 text line endings without changing other semantic content."""

    text = data.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def semantic_hash_bytes(data: bytes) -> str:
    try:
        normalized = normalize_text_bytes(data)
    except UnicodeDecodeError:
        normalized = data
    return sha256_bytes(normalized)


def write_json_atomic(path: Path, value: Any) -> None:
    """Write canonical JSON plus one newline using atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_jsonl_atomic(path: Path, values: list[Any]) -> None:
    """Write canonical JSON Lines with deterministic ordering supplied by the caller."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(canonical_json_bytes(value) + b"\n" for value in values)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def content_id(namespace: str, value: Any, length: int = 20) -> str:
    if not namespace or not namespace.replace("_", "").isalnum():
        raise ValueError("namespace must be alphanumeric with optional underscores")
    return f"{namespace}:{canonical_json_hash(value)[:length]}"
