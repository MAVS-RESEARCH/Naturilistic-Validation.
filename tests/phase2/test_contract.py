from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError

from pc_external.contract import (
    ContractError,
    build_history_universe,
    compile_contract,
    contract_provenance,
    extract_semantic_facts,
    fidelity_report,
    validate_contract,
    validate_semantic_facts,
)

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "external_v01_polaris_pr4992"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compile_frozen_contract() -> tuple[dict, list[dict], dict]:
    manifest = load(ROOT / "external_source" / "source_manifest.json")
    native = load(ROOT / "external_source" / "native_case_index.json")
    facts = extract_semantic_facts(ROOT, manifest, native)
    validate_semantic_facts(ROOT, manifest, facts)
    history = build_history_universe(RUN_ID, native, manifest["manifest_hash"])
    costs = yaml.safe_load((ROOT / "configs" / "costs.yaml").read_text(encoding="utf-8"))
    contract = compile_contract(
        run_id=RUN_ID,
        facts=facts,
        history_universe=history,
        manifest=manifest,
        native_cases=native,
        costs=costs,
    )
    return contract, facts, native


def test_two_pass_contract_compilation_has_complete_m_ext_and_native_fidelity() -> None:
    contract, facts, native = compile_frozen_contract()
    validate_contract(contract)
    assert set(
        ("S", "s0", "U_H", "H", "P_R", "Lambda", "omega", "Q", "Succ_plus", "Terminal", "A_Pi", "c")
    ).issubset(contract)
    assert len(contract["S"]) == 2
    assert len(contract["U_H"]) == 8
    assert len(contract["Q"]) == 1
    assert contract["Lambda"][contract["S"][0]] == contract["Lambda"][contract["S"][1]]
    fidelity = fidelity_report(RUN_ID, contract, native)
    assert fidelity["case_completion_pairs"] == 8
    assert fidelity["fidelity_percent"] == 100.0
    assert fidelity["all_completions_valid"] is True
    provenance = contract_provenance(contract, facts)
    assert provenance["all_normative_components_have_lineage"] is True
    assert provenance["fact_count"] == 18


def test_every_fact_locator_is_exact_and_corruption_fails_closed() -> None:
    manifest = load(ROOT / "external_source" / "source_manifest.json")
    native = load(ROOT / "external_source" / "native_case_index.json")
    facts = extract_semantic_facts(ROOT, manifest, native)
    validate_semantic_facts(ROOT, manifest, facts)
    corrupted = copy.deepcopy(facts)
    corrupted[0]["locator"]["quote_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="quote hash mismatch"):
        validate_semantic_facts(ROOT, manifest, corrupted)


def test_contract_hash_and_common_domain_corruption_fail_closed() -> None:
    contract, _, _ = compile_frozen_contract()
    corrupted_hash = copy.deepcopy(contract)
    corrupted_hash["s0"] = contract["S"][1]
    with pytest.raises(ContractError, match="contract hash mismatch"):
        validate_contract(corrupted_hash)
    corrupted_domain = copy.deepcopy(contract)
    corrupted_domain["states"][0]["history_domain"] = corrupted_domain["states"][0][
        "history_domain"
    ][:-1]
    payload = {key: value for key, value in corrupted_domain.items() if key != "contract_hash"}
    from pc_external.hashing import canonical_json_hash

    corrupted_domain["contract_hash"] = canonical_json_hash(payload)
    with pytest.raises(ContractError, match="common U_H"):
        validate_contract(corrupted_domain)


def test_artifact_case_and_serialization_permutation_invariance() -> None:
    manifest = load(ROOT / "external_source" / "source_manifest.json")
    native = load(ROOT / "external_source" / "native_case_index.json")
    reversed_manifest = {**manifest, "artifacts": list(reversed(manifest["artifacts"]))}
    reversed_native = {**native, "cases": list(reversed(native["cases"]))}
    first_facts = extract_semantic_facts(ROOT, manifest, native)
    second_facts = extract_semantic_facts(ROOT, reversed_manifest, reversed_native)
    assert first_facts == second_facts
    first_history = build_history_universe(RUN_ID, native, manifest["manifest_hash"])
    second_history = build_history_universe(RUN_ID, reversed_native, manifest["manifest_hash"])
    assert first_history == second_history


def test_strict_contract_schema_rejects_unknown_normative_field() -> None:
    from scripts.phase2_validate_contract import validate_schema

    contract, _, _ = compile_frozen_contract()
    validate_schema(ROOT, contract, "extensional_contract.schema.json")
    contract["states"][0]["manual_touch"] = ["R"]
    with pytest.raises(ValidationError):
        validate_schema(ROOT, contract, "extensional_contract.schema.json")
