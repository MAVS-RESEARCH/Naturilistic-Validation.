"""Resource-freeze lattice, condition manifests, and extended-real relations."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

from pc_external.hashing import canonical_json_hash, content_id


class FreezeError(ValueError):
    """Raised when a matched freeze experiment violates its preregistration."""


FREEZE_LATTICE = (
    ("F000", ()),
    ("F100", ("E",)),
    ("F010", ("R",)),
    ("F001", ("A",)),
    ("F110", ("E", "R")),
    ("F101", ("E", "A")),
    ("F011", ("R", "A")),
    ("F111", ("E", "R", "A")),
)


def exact_freeze_lattice(configured: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    actual = [(item["id"], tuple(item["forbidden"])) for item in configured]
    if actual != list(FREEZE_LATTICE):
        raise FreezeError("configured freeze lattice differs from the preregistered eight cells")
    return [
        {"freeze_id": freeze_id, "forbidden_resources": list(resources)}
        for freeze_id, resources in FREEZE_LATTICE
    ]


def derive_action_mask(
    actions: Iterable[Mapping[str, Any]],
    touch_by_action: Mapping[str, Mapping[str, bool]],
    forbidden_resources: Iterable[str],
) -> dict[str, Any]:
    forbidden = set(forbidden_resources)
    retained: list[str] = []
    blocked: list[str] = []
    for action in sorted(actions, key=lambda item: item["intervention_id"]):
        action_id = action["intervention_id"]
        touches = touch_by_action.get(action_id)
        if touches is None or set(touches) != {"E", "R", "A"}:
            raise FreezeError(f"action lacks an exact derived touch record: {action_id}")
        destination = blocked if any(touches[resource] for resource in forbidden) else retained
        destination.append(action_id)
    value = {"retained_action_ids": retained, "blocked_action_ids": blocked}
    return {**value, "action_mask_hash": canonical_json_hash(value)}


def scientific_instance(
    contract: Mapping[str, Any], case_id: str, cost_contract_id: str
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "completion_id": contract["completion_id"],
        "cost_contract_id": cost_contract_id,
        "S": copy.deepcopy(contract["S"]),
        "s0": contract["s0"],
        "U_H": copy.deepcopy(contract["U_H"]),
        "H": copy.deepcopy(contract["H"]),
        "P_R": copy.deepcopy(contract["P_R"]),
        "Lambda": copy.deepcopy(contract["Lambda"]),
        "omega": copy.deepcopy(contract["omega"]),
        "Q": copy.deepcopy(contract["Q"]),
        "Succ_plus": copy.deepcopy(contract["Succ_plus"]),
        "Terminal": copy.deepcopy(contract["Terminal"][case_id]),
        "A_Pi": copy.deepcopy(contract["A_Pi"][case_id]),
        "cost": copy.deepcopy(contract["c"]),
        "contract_hash": contract["contract_hash"],
        "source_fact_ids": copy.deepcopy(contract["source_fact_ids"]),
    }


def condition_manifest(
    *,
    run_id: str,
    instance: Mapping[str, Any],
    freeze_id: str,
    forbidden_resources: list[str],
    action_mask: Mapping[str, Any],
    contract_seal_hash: str,
) -> dict[str, Any]:
    base_hash = canonical_json_hash(instance)
    value = {
        "run_id": run_id,
        "freeze_id": freeze_id,
        "forbidden_resources": forbidden_resources,
        "action_mask": dict(action_mask),
        "base_instance_hash": base_hash,
        "scientific_instance": copy.deepcopy(instance),
        "contract_seal_hash": contract_seal_hash,
    }
    return {**value, "condition_manifest_hash": canonical_json_hash(value)}


def assert_same_instance(manifests: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(manifests)
    if not rows:
        raise FreezeError("same-instance validation requires manifests")
    base_hashes = {row["base_instance_hash"] for row in rows}
    recomputed = {canonical_json_hash(row["scientific_instance"]) for row in rows}
    if len(base_hashes) != 1 or recomputed != base_hashes:
        raise FreezeError("condition manifests differ outside allowed freeze/planner fields")
    return {
        "passed": True,
        "manifest_count": len(rows),
        "base_instance_hash": next(iter(base_hashes)),
    }


def extended_relation(
    restricted: Mapping[str, Any] | None, unrestricted: Mapping[str, Any] | None
) -> str:
    if restricted is None or unrestricted is None:
        return "UNDEFINED"
    left, right = restricted["kind"], unrestricted["kind"]
    if left == right == "INFINITE":
        return "BOTH_INFINITE"
    if left == "INFINITE" and right == "FINITE":
        return "STRUCTURAL_POSITIVE"
    if left == "FINITE" and right == "INFINITE":
        raise FreezeError("FINITE_NEGATIVE under pure action removal invalidates the run")
    difference = restricted["value"] - unrestricted["value"]
    if difference < 0:
        raise FreezeError("FINITE_NEGATIVE under pure action removal invalidates the run")
    return "FINITE_POSITIVE" if difference > 0 else "FINITE_ZERO"


def classify_result(unrestricted: Mapping[str, Any], r_frozen: Mapping[str, Any]) -> str:
    relation = extended_relation(r_frozen, unrestricted)
    return {
        "FINITE_POSITIVE": "POSITIVE_FINITE",
        "FINITE_ZERO": "ZERO_GAP",
        "STRUCTURAL_POSITIVE": "STRUCTURAL_R",
        "BOTH_INFINITE": "BOTH_INFINITE",
        "UNDEFINED": "INSUFFICIENT",
    }[relation]


def freeze_result_id(identity: Mapping[str, Any]) -> str:
    return content_id("freeze_result", identity)
