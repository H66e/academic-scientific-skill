"""Cumulative reading declarations with explicit, irreversible withdrawal.

Declarations remain visible historical facts; this module neither reads a paper
nor authenticates who made a declaration. Only explicit retraction lowers the
derived reading qualification.
"""
from __future__ import annotations

from typing import Any


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def validate_retraction_payload(event_type: str, data: dict) -> None:
    if event_type != "reading.retract":
        return
    if not isinstance(data, dict) or set(data) != {"target", "reason"}:
        raise ValueError("reading.retract payload requires exactly target and reason")
    _text(data["target"], "reading target")
    _text(data["reason"], "reading retraction reason")


def effective_readings(events: list[dict], evidence_id: str | None = None) -> list[dict]:
    """Resolve all withdrawals before returning effective confirmations.

    Event identity and explicit targets govern the set, never time or position.
    The writer separately requires its target to exist before an append. This
    fold also accepts an unordered event view for deterministic verification.
    """
    anchors: dict[str, set[str]] = {}
    for event in events:
        if event["type"] == "evidence.anchor":
            key = _text(event["data"].get("id", event["id"]), "anchor identity")
            for alias in (event["id"], key):
                if isinstance(alias, str):
                    anchors.setdefault(alias, set()).add(key)

    def anchor_key(alias: str) -> str:
        choices = anchors.get(alias, set())
        if len(choices) != 1:
            raise ValueError("reading evidence must resolve to an immutable anchor")
        return next(iter(choices))

    confirmations = {}
    bound_anchors = {}
    for event in events:
        if event["type"] != "reading.confirm":
            continue
        if event["id"] in confirmations:
            raise ValueError("duplicate reading confirmation event ID")
        if (not isinstance(event.get("actor"), str) or not isinstance(event.get("trust"), str)
                or (event["actor"], event["trust"]) not in {("model", "T2"), ("user", "T1")}):
            raise ValueError("invalid reading confirmation actor/trust")
        data = event["data"]
        if not isinstance(data.get("scope"), str) or data["scope"] not in {"abstract", "section", "full_text"}:
            raise ValueError("invalid reading confirmation scope")
        _text(data.get("context"), "reader context")
        if type(data.get("visual_checked")) is not bool or (data["visual_checked"] and event["actor"] != "user"):
            raise ValueError("visual confirmation requires declared user/T1 provenance")
        alias = _text(data.get("evidence_id"), "reading evidence ID")
        bound_anchors[event["id"]] = anchor_key(alias)
        confirmations[event["id"]] = event
    retired = set()
    for event in events:
        if event["type"] != "reading.retract":
            continue
        validate_retraction_payload(event["type"], event["data"])
        if (not isinstance(event.get("actor"), str) or not isinstance(event.get("trust"), str)
                or (event["actor"], event["trust"]) not in {("model", "T2"), ("user", "T1")}):
            raise ValueError("invalid reading retraction actor/trust")
        target_id = event["data"]["target"]
        target = confirmations.get(target_id)
        if target is None:
            raise ValueError("reading retraction target must be an existing reading.confirm")
        if target_id in retired:
            raise ValueError("reading confirmation is already retracted")
        if event["actor"] == "model" and (target["actor"], target["trust"]) != ("model", "T2"):
            raise ValueError("model cannot retract a user/T1 reading confirmation")
        retired.add(target_id)
    key = anchor_key(evidence_id) if evidence_id is not None else None
    return [confirmations[event_id] for event_id in sorted(confirmations)
            if event_id not in retired and (key is None or bound_anchors[event_id] == key)]
