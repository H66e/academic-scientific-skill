"""Causal result classifications and run-level eligibility.

These are declared observations, not authenticated execution receipts. Locators
and structure do not establish control validity, faithful analysis or truth.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
import re
from typing import Any
from urllib.parse import urlsplit

KINDS = {"smoke", "scientific"}
OUTCOMES = {"not_run", "execution_failed", "inconclusive", "supported", "contradicted"}
RECORD_FIELDS = {"id", "run_id", "candidate_id", "candidate_version", "kind",
                 "outcome", "artifacts", "summary", "limitations", "affected_claims"}
INVALIDATION_FIELDS = {"id", "run_id", "candidate_id", "candidate_version",
                       "result_id", "reason", "recorded_at"}


def text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


def artifact_locator(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip() or re.search(r"[\x00-\x1f]", value):
        return False
    if re.match(r"^[a-z][a-z\d+.-]*:", value, re.I) and not re.match(r"^[a-z]:[\\/]", value, re.I):
        if re.search(r"[\x00-\x20]", value) or not re.match(r"^(https?://|file://)", value, re.I):
            return False
        try:
            parsed = urlsplit(value)
            parsed.port  # Reject malformed ports without following the locator.
            if parsed.username or parsed.password:
                return False
            return len(parsed.path) > 1 if parsed.scheme == "file" else bool(parsed.hostname)
        except ValueError:
            return False
    return True


def result_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?(?:Z|[+-][0-9]{2}:?[0-9]{2})", value):
        return False
    zone = re.search(r"([+-])([0-9]{2}):?([0-9]{2})$", value)
    if zone and (int(zone[2]) > 23 or int(zone[3]) > 59):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def validate_result_payload(event_type: str, data: dict) -> None:
    """Validate complete payload shape; causal references are resolved below."""
    if event_type not in {"result.record", "result.invalidate"}:
        return
    if not isinstance(data, dict):
        raise ValueError("result data must be an object")
    required = RECORD_FIELDS if event_type == "result.record" else INVALIDATION_FIELDS
    optional = {"supersedes", "reason"} if event_type == "result.record" else set()
    if not required <= data.keys() or not data.keys() <= required | optional:
        raise ValueError(f"{event_type} payload fields mismatch")
    for key in ("id", "run_id", "candidate_id"):
        text(data[key], key)
    if type(data["candidate_version"]) is not int or data["candidate_version"] < 1:
        raise ValueError("candidate_version must be a positive integer")
    if event_type == "result.invalidate":
        for key in ("result_id", "reason", "recorded_at"):
            text(data[key], key)
        if not result_timestamp(data["recorded_at"]):
            raise ValueError("recorded_at must be a timezone-aware ISO timestamp")
        return
    if not isinstance(data["kind"], str) or data["kind"] not in KINDS:
        raise ValueError("unsupported result kind")
    if not isinstance(data["outcome"], str) or data["outcome"] not in OUTCOMES:
        raise ValueError("unsupported result outcome")
    text(data["summary"], "summary")
    for key in ("artifacts", "limitations"):
        if not isinstance(data[key], list):
            raise ValueError(f"{key} must be an array")
        for value in data[key]:
            text(value, key)
            if key == "artifacts" and not artifact_locator(value):
                raise ValueError("artifact must be a locatable path or HTTP(S)/file URL")
    if data["outcome"] != "not_run" and not data["artifacts"]:
        raise ValueError("reported executed results require locatable artifacts")
    if not isinstance(data["affected_claims"], list):
        raise ValueError("affected_claims must be an array")
    for claim in data["affected_claims"]:
        if not isinstance(claim, dict) or set(claim) != {"claim_id", "reason"}:
            raise ValueError("affected_claims requires claim_id and reason objects")
        text(claim["claim_id"], "affected_claims.claim_id")
        text(claim["reason"], "affected_claims.reason")
    if "supersedes" in data:
        text(data["supersedes"], "supersedes")
        text(data.get("reason"), "reclassification reason")
    elif "reason" in data:
        raise ValueError("a correction reason requires supersedes")


def _scope(data: dict) -> tuple[str, int]:
    return data["candidate_id"], data["candidate_version"]


def _history(events: list[dict]) -> tuple[dict[str, dict], list[dict], dict]:
    """Resolve identity and causality over the full supplied event history."""
    candidates = {(e["data"].get("id"), e["data"].get("version")) for e in events
                  if e["type"] == "candidate.upsert" and isinstance(e["data"].get("id"), str)
                  and type(e["data"].get("version")) is int and e["data"]["version"] > 0}
    claims = {e["id"]: e["data"] for e in events if e["type"] == "claim.add"}
    records: dict[str, dict] = {}
    invalidations = []
    ids = set()
    for event in events:
        if event["type"] not in {"result.record", "result.invalidate"}:
            continue
        data = event["data"]
        validate_result_payload(event["type"], data)
        expected = {("model", "T2"), ("user", "T1")} if event["type"] == "result.record" else {("user", "T1")}
        if not isinstance(event.get("actor"), str) or not isinstance(event.get("trust"), str) or (event["actor"], event["trust"]) not in expected:
            raise ValueError("invalid result actor/trust")
        if not result_timestamp(event.get("ts")):
            raise ValueError("result event timestamp must be timezone-aware ISO")
        if data["id"] in ids:
            raise ValueError(f"duplicate result lifecycle ID: {data['id']}")
        ids.add(data["id"])
        if _scope(data) not in candidates:
            raise ValueError("result refers to a missing candidate/version")
        item = {**deepcopy(data), "actor": event["actor"], "trust": event["trust"],
                "recorded_at": data.get("recorded_at", event["ts"])}
        if event["type"] == "result.record":
            records[data["id"]] = item
        else:
            invalidations.append(item)
    # Run IDs cannot silently transfer between candidates or candidate versions.
    scopes = {}
    for item in records.values():
        previous = scopes.setdefault(item["run_id"], _scope(item))
        if previous != _scope(item):
            raise ValueError("run_id belongs to a different candidate/version")
        if "supersedes" in item:
            target = records.get(item["supersedes"])
            if not target:
                raise ValueError("supersedes target is missing")
            if item["id"] == target["id"]:
                raise ValueError("a result cannot supersede itself")
            if item["run_id"] != target["run_id"] or _scope(item) != _scope(target):
                raise ValueError("supersedes crosses run/candidate/version")
    # No chronological assumption: a cycle is invalid even in a supplied snapshot.
    done = set()
    for record_id in records:
        cursor, path = record_id, set()
        while cursor not in done:
            if cursor in path:
                raise ValueError("result supersession cycle")
            path.add(cursor)
            parent = records[cursor].get("supersedes")
            if parent is None:
                break
            cursor = parent
        done.update(path)
    for item in invalidations:
        target = records.get(item["result_id"])
        if not target or target["run_id"] != item["run_id"] or _scope(target) != _scope(item):
            raise ValueError("invalidation target is absent or mismatched")
    return records, invalidations, claims


def validate_result_history(events: list[dict]) -> None:
    _history(events)


def candidate_result_state(events: list[dict], candidate_id: str, candidate_version: int) -> dict:
    records, invalidations, claims = _history(events)
    scope = (candidate_id, candidate_version)
    retired_runs = {r["run_id"] for r in invalidations if _scope(r) == scope}
    grouped = defaultdict(list)
    for item in records.values():
        if _scope(item) == scope:
            grouped[item["run_id"]].append(item)
    runs, warnings, refutations = [], [], []
    contradiction = ambiguity = degraded = False
    for run_id, history in sorted(grouped.items()):
        superseded = {r["supersedes"] for r in history if "supersedes" in r}
        heads = sorted((r for r in history if r["id"] not in superseded), key=lambda r: r["id"])
        invalidated = run_id in retired_runs
        ambiguous = len(heads) > 1 and not invalidated
        runs.append({"run_id": run_id, "invalidated": invalidated,
                     "heads": heads, "ambiguous": ambiguous})
        if ambiguous:
            warnings.append(f"Run {run_id} has multiple effective classifications; HOLD required")
            ambiguity = True
        for item in history:
            for ref in item["affected_claims"]:
                claim = claims.get(ref["claim_id"])
                if not claim or (claim.get("candidate_id"), claim.get("candidate_version")) != scope:
                    degraded = True
                    warnings.append(f"Result {item['id']} affected claim {ref['claim_id']} is unresolved")
        if not invalidated:
            heads_contradicted = [h for h in heads if h["kind"] == "scientific" and h["outcome"] == "contradicted"]
            contradiction = contradiction or bool(heads_contradicted)
            if not ambiguous:
                refutations.extend(heads_contradicted)
    return {"candidate_id": candidate_id, "candidate_version": candidate_version,
            "runs": runs, "contradiction_blocker": contradiction,
            "ambiguity_blocker": ambiguity, "requires_hold": contradiction or ambiguity,
            "scientific_refutation_basis": refutations, "warnings": list(dict.fromkeys(warnings)),
            "affected_claims_degraded": degraded}
