"""Atomic intervention and positive-support transition validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class InterventionError(ValueError):
    """Raised when an intervention is incomplete or stores manual touch labels."""


FORBIDDEN_TOUCH_FIELDS = {"touch", "touches", "resource_touch", "touch_mask"}


def validate_intervention(action: Mapping[str, Any], state_ids: Iterable[str]) -> None:
    if FORBIDDEN_TOUCH_FIELDS.intersection(action):
        raise InterventionError("interventions may not store manual touch labels")
    states = set(state_ids)
    if action["source_state_id"] not in states:
        raise InterventionError("intervention source state is outside S")
    if not action["atomicity"]["is_atomic"]:
        raise InterventionError("non-atomic intervention is not admitted")
    successors = action["positive_support_successors"]
    if not successors:
        raise InterventionError("intervention must have positive-support successors")
    if any(item["state_id"] not in states or item["support"] <= 0 for item in successors):
        raise InterventionError("successor is outside S or lacks positive support")
    if action["cost"]["unit"] != 1:
        raise InterventionError("primary intervention cost must be one")
    if not action["provenance_fact_ids"]:
        raise InterventionError("intervention requires source provenance")


def successor_ids(action: Mapping[str, Any]) -> list[str]:
    return sorted({item["state_id"] for item in action["positive_support_successors"]})


def classify_route(
    actions: Iterable[Mapping[str, Any]], touch_masks: Iterable[Mapping[str, bool]] | None = None
) -> str:
    """Classify the source-grounded route space before freeze results exist."""
    action_list = list(actions)
    if not action_list:
        return "NO_REPAIR_SPACE"
    if len(action_list) == 1:
        return "SINGLE_ACTION"
    masks = list(touch_masks or [])
    if len(masks) == len(action_list) and all(
        mask == {"E": False, "R": True, "A": False} for mask in masks
    ):
        return "R-ONLY_ROUTE"
    return "NONDEGENERATE"
