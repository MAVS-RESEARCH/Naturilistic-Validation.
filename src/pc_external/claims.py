"""Mechanically derive constrained claim language from audited gates and processed results."""

from __future__ import annotations

from typing import Any

from pc_external.hashing import canonical_json_hash


class ClaimError(ValueError):
    """Raised when audited evidence does not authorize a claim ledger."""


LOCKED_FLAGS = {
    "prevalence": False,
    "superiority": False,
    "deployment_readiness": False,
}
PROHIBITED = sorted(LOCKED_FLAGS)


def _claim(
    claim_id: str,
    predicate: str,
    supported: bool,
    evidence_paths: list[str],
    generated_text: str,
) -> dict[str, Any]:
    value = {
        "claim_id": claim_id,
        "predicate": predicate,
        "supported": supported,
        "evidence_paths": sorted(evidence_paths),
        "prohibited_dependencies": PROHIBITED,
        "generated_text": generated_text,
    }
    return {**value, "claim_hash": canonical_json_hash(value)}


def derive_claim_ledger(
    run_id: str,
    independent_core: dict[str, Any],
    corruption_report: dict[str, Any],
    case_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    core_pass = independent_core.get("overall_pass") is True
    corruptions_pass = (
        corruption_report.get("all_detected") is True
        and corruption_report.get("detected_count") == 12
    )
    external_valid = core_pass and corruptions_pass and bool(case_rows)
    classes = {row["result_class"] for row in case_rows}
    routes = {row["route_class"] for row in case_rows}
    all_audit_eligible = all(row["audit_eligible"] for row in case_rows)
    if not external_valid or not all_audit_eligible:
        sign = "INVALID"
    elif classes <= {"POSITIVE_FINITE", "STRUCTURAL_R"}:
        sign = "POSITIVE"
    elif classes == {"ZERO_GAP"}:
        sign = "NULL"
    elif "PARTIAL_SIGN" in classes or len(classes) > 1:
        sign = "PARTIAL"
    elif classes == {"INSUFFICIENT"}:
        sign = "FEASIBILITY_NEGATIVE"
    else:
        sign = "THEORY_CONFLICT"
    evidence = [
        "audit/independent_audit.json",
        "audit/corruption_report.json",
        "processed/case_results.parquet",
    ]
    claims = [
        _claim(
            "CLM-EXT-001",
            "independent core audit passes and all twelve corruptions are detected",
            external_valid,
            evidence,
            (
                "The Apache Polaris OPA certificate-target experiment is a valid external "
                "operational measurement under the preregistered finite contract."
            ),
        ),
        _claim(
            "CLM-RESULT-001",
            "every retained native case is audit-eligible and has a positive Delta_R relation",
            external_valid and sign == "POSITIVE",
            evidence,
            (
                "In this independently engineered Apache Polaris instance, unrestricted closure "
                "costs one unit intervention and R-frozen closure is unreachable for all eight "
                "source-selected certificate cases."
            ),
        ),
        _claim(
            "CLM-QUAL-001",
            "every measured case carries the preregistered SINGLE_ACTION route qualifier",
            routes == {"SINGLE_ACTION"},
            ["contract/route_classification.json", "processed/case_results.parquet"],
            (
                "The result is qualified as SINGLE_ACTION because the frozen source establishes "
                "one admitted historical repair action and no competing repair route."
            ),
        ),
        _claim(
            "CLM-NONCLAIM-001",
            "the preregistered prevalence flag remains false",
            LOCKED_FLAGS["prevalence"] is False,
            ["preregistration/preregistration.json", "reports/claim_ledger.json"],
            "This experiment does not estimate how prevalent positive resource dependence is.",
        ),
        _claim(
            "CLM-NONCLAIM-002",
            "the preregistered superiority flag remains false",
            LOCKED_FLAGS["superiority"] is False,
            ["preregistration/preregistration.json", "reports/claim_ledger.json"],
            (
                "This experiment does not establish superiority over another authorization "
                "architecture."
            ),
        ),
        _claim(
            "CLM-NONCLAIM-003",
            "the preregistered deployment-readiness flag remains false",
            LOCKED_FLAGS["deployment_readiness"] is False,
            ["preregistration/preregistration.json", "reports/claim_ledger.json"],
            "This experiment does not establish deployment readiness or universal correctness.",
        ),
    ]
    value = {
        "run_id": run_id,
        "external_operational_validation": external_valid,
        "result_sign": sign,
        "locked_flags": LOCKED_FLAGS,
        "claims": claims,
    }
    return {**value, "ledger_hash": canonical_json_hash(value)}


def final_verdict(ledger: dict[str, Any]) -> str:
    if not ledger["external_operational_validation"]:
        return "FAIL — INVALID EXPERIMENT"
    return {
        "POSITIVE": "PASS — POSITIVE EXTERNAL",
        "NULL": "PASS — NULL EXTERNAL",
        "PARTIAL": "PASS — PARTIAL EXTERNAL",
        "FEASIBILITY_NEGATIVE": "PASS — FEASIBILITY NEGATIVE",
        "INVALID": "FAIL — INVALID EXPERIMENT",
        "THEORY_CONFLICT": "STOP — THEORY CONFLICT",
    }[ledger["result_sign"]]
