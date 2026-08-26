"""Independent validation of mechanical claim ledgers and generated sentences."""

from __future__ import annotations

from typing import Any

from pc_external_audit.source_audit import object_hash


def validate_claim_ledger(ledger: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    payload = {key: value for key, value in ledger.items() if key != "ledger_hash"}
    if ledger.get("ledger_hash") != object_hash(payload):
        findings.append({"claim_id": "LEDGER", "reason": "LEDGER_HASH_MISMATCH"})
    if ledger.get("locked_flags") != {
        "prevalence": False,
        "superiority": False,
        "deployment_readiness": False,
    }:
        findings.append({"claim_id": "LOCKS", "reason": "PROHIBITED_FLAG_ENABLED"})
    seen: set[str] = set()
    for claim in ledger.get("claims", []):
        claim_id = claim.get("claim_id", "UNKNOWN")
        if claim_id in seen:
            findings.append({"claim_id": claim_id, "reason": "DUPLICATE_CLAIM_ID"})
        seen.add(claim_id)
        claim_payload = {key: value for key, value in claim.items() if key != "claim_hash"}
        if claim.get("claim_hash") != object_hash(claim_payload):
            findings.append({"claim_id": claim_id, "reason": "CLAIM_HASH_MISMATCH"})
        if not claim.get("evidence_paths"):
            findings.append({"claim_id": claim_id, "reason": "MISSING_EVIDENCE"})
        if claim.get("supported") and not claim.get("prohibited_dependencies"):
            findings.append({"claim_id": claim_id, "reason": "MISSING_PROHIBITED_DEPENDENCIES"})
    return findings


def verify_report_sentences(
    report_text: str, ledger: dict[str, Any], *, supported_only: bool = False
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    expected = {
        f"[{claim['claim_id']}] {claim['generated_text']}"
        for claim in ledger["claims"]
        if not supported_only or claim["supported"]
    }
    actual = {line for line in report_text.splitlines() if line.startswith("[CLM-")}
    unknown = actual - expected
    missing = expected - actual
    if unknown:
        findings.extend(
            {"claim_id": "REPORT", "reason": f"UNAUTHORIZED_SENTENCE:{line}"}
            for line in sorted(unknown)
        )
    if missing:
        findings.extend(
            {"claim_id": "REPORT", "reason": f"MISSING_SENTENCE:{line}"} for line in sorted(missing)
        )
    return findings
