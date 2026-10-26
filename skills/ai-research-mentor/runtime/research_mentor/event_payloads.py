"""Admission rules for the ``data`` object of every registered ledger event.

``Ledger.verify`` reports and ``Ledger.append`` refuses a payload that a consumer
of the runtime would dereference unconditionally, so a structurally valid hash
chain can no longer hide a missing ``candidate.upsert.id`` (or any other payload
shape that used to crash ``status``/``assess`` later).

The rules below are deliberately weak admission checks, not scientific gates:
presence plus primitive type for fields the runtime reads, extra keys allowed for
forward compatibility, and no enum invented beyond what an existing validator
already enforces.  ``result.record``, ``result.invalidate`` and
``reading.retract`` delegate to :func:`results.validate_result_payload` and
:func:`readings.validate_retraction_payload` so each payload has exactly one rule.

Table (required fields; optional/nullable fields in parentheses)::

    project.init             project_id, core_version
    project.update           id, question, research_type, constraints, assumptions
    search.result            id, query, provider, family, limit, result_paper_ids,
                             papers, limitations, executed, status
    paper.resolve            id, identifiers, title, version, provider, source_url
    source.fetch             id, paper_id, source_identity, source_url, media_type,
                             receipt, raw_sha256, text_sha256, ir_sha256, ir_path,
                             extractor, normalization, block_count, read_scope,
                             needs_host_review, needs_host_extraction, limitations
                             (paper_id and source_url may be null)
    evidence.anchor          id, source, source_event, source_ir_sha256, locator,
                             start, end, quote, quote_normalized, quote_sha256,
                             source_sha256, match, anchor_version, read_scope,
                             block_id, section, lossy
                             (block_id may be null)
    source.identity.confirm  source_id, source_event, paper_id, version,
                             resolve_event, statement, source_snapshot, status
    candidate.upsert         id, version, title, question, hypothesis,
                             contribution, research_type, search_ids, nearest_work,
                             novelty, feasibility, validation
    claim.add                text, candidate_id, candidate_version, kind,
                             load_bearing
    claim.link               claim_id, evidence_id, relation, target,
                             decision_relevant
    reading.confirm          evidence_id, scope, context, visual_checked
    reading.retract          target, reason (delegated to the readings validator)
    review.record            candidate_id, candidate_version, snapshot,
                             policy_version, machine_recommendation, stage, scope
                             (kill_type and human_decision may be null)
    decision.record          candidate_id, candidate_version, review_id, snapshot,
                             machine_recommendation, human_decision, statement,
                             override_reason, stage, scope
    decision.revoke          candidate_id, statement
    result.record            delegated to the results validator (record fields)
    result.invalidate        delegated to the results validator (invalidation fields)

Every error message starts with the event type and names the field, for example
``candidate.upsert: version must be a positive integer``.
"""
from __future__ import annotations

from typing import Any

from .readings import validate_retraction_payload
from .results import INVALIDATION_FIELDS, RECORD_FIELDS, validate_result_payload

# Primitive field kinds.  "text" is a nonempty string, "text?" additionally
# admits null for fields the producers legitimately leave unset, and "string"
# admits an empty string for fields where "" is a declared producer default.
TEXT = "text"
STRING = "string"
NULLABLE_TEXT = "text?"
INTEGER = "int"
POSITIVE_INTEGER = "positive_int"
BOOLEAN = "bool"
ARRAY = "list"
OBJECT = "dict"

_DESCRIPTIONS = {
    TEXT: "nonempty text",
    STRING: "text",
    NULLABLE_TEXT: "text or null",
    INTEGER: "an integer",
    POSITIVE_INTEGER: "a positive integer",
    BOOLEAN: "a boolean",
    ARRAY: "an array",
    OBJECT: "an object",
}

# Event type -> ordered (field, kind) pairs.  Only fields the runtime reads
# unconditionally belong here; optional producer keys are intentionally absent.
_CONCRETE_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "project.init": (("project_id", TEXT), ("core_version", TEXT)),
    "project.update": (("id", TEXT), ("question", TEXT), ("research_type", TEXT),
                       ("constraints", OBJECT), ("assumptions", ARRAY)),
    "search.result": (("id", TEXT), ("query", TEXT), ("provider", TEXT), ("family", TEXT),
                      ("limit", INTEGER), ("result_paper_ids", ARRAY), ("papers", ARRAY),
                      ("limitations", ARRAY), ("executed", BOOLEAN), ("status", TEXT)),
    "paper.resolve": (("id", TEXT), ("identifiers", OBJECT), ("title", TEXT),
                      ("version", TEXT), ("provider", TEXT), ("source_url", TEXT)),
    "source.fetch": (("id", TEXT), ("paper_id", NULLABLE_TEXT), ("source_identity", OBJECT),
                     ("source_url", NULLABLE_TEXT), ("media_type", TEXT), ("receipt", OBJECT),
                     ("raw_sha256", TEXT), ("text_sha256", TEXT), ("ir_sha256", TEXT),
                     ("ir_path", TEXT), ("extractor", TEXT), ("normalization", TEXT),
                     ("block_count", INTEGER), ("read_scope", TEXT),
                     ("needs_host_review", BOOLEAN), ("needs_host_extraction", BOOLEAN),
                     ("limitations", ARRAY)),
    "evidence.anchor": (("id", TEXT), ("source", TEXT), ("source_event", TEXT),
                        ("source_ir_sha256", TEXT), ("locator", TEXT), ("start", INTEGER),
                        ("end", INTEGER), ("quote", TEXT), ("quote_normalized", TEXT),
                        ("quote_sha256", TEXT), ("source_sha256", TEXT), ("match", TEXT),
                        ("anchor_version", TEXT), ("read_scope", TEXT),
                        ("block_id", NULLABLE_TEXT), ("section", TEXT), ("lossy", BOOLEAN)),
    "source.identity.confirm": (("source_id", TEXT), ("source_event", TEXT), ("paper_id", TEXT),
                                ("version", TEXT), ("resolve_event", TEXT), ("statement", TEXT),
                                ("source_snapshot", TEXT), ("status", TEXT)),
    "candidate.upsert": (("id", TEXT), ("version", POSITIVE_INTEGER), ("title", TEXT),
                         ("question", TEXT), ("hypothesis", TEXT), ("contribution", TEXT),
                         ("research_type", TEXT), ("search_ids", ARRAY),
                         ("nearest_work", ARRAY), ("novelty", OBJECT),
                         ("feasibility", OBJECT), ("validation", OBJECT)),
    "claim.add": (("text", TEXT), ("candidate_id", TEXT), ("candidate_version", POSITIVE_INTEGER),
                  ("kind", TEXT), ("load_bearing", BOOLEAN)),
    "claim.link": (("claim_id", TEXT), ("evidence_id", TEXT), ("relation", TEXT),
                   ("target", TEXT), ("decision_relevant", BOOLEAN)),
    "reading.confirm": (("evidence_id", TEXT), ("scope", TEXT), ("context", TEXT),
                        ("visual_checked", BOOLEAN)),
    "review.record": (("candidate_id", TEXT), ("candidate_version", POSITIVE_INTEGER),
                      ("snapshot", TEXT), ("policy_version", TEXT),
                      ("machine_recommendation", TEXT), ("stage", TEXT), ("scope", TEXT),
                      ("kill_type", NULLABLE_TEXT), ("human_decision", NULLABLE_TEXT)),
    "decision.record": (("candidate_id", TEXT), ("candidate_version", POSITIVE_INTEGER),
                        ("review_id", TEXT), ("snapshot", TEXT),
                        ("machine_recommendation", TEXT), ("human_decision", TEXT),
                        ("statement", TEXT), ("override_reason", STRING),
                        ("stage", TEXT), ("scope", TEXT)),
    "decision.revoke": (("candidate_id", TEXT), ("statement", TEXT)),
}

# Documented required fields, including the delegated event types whose single
# rule lives in results.py/readings.py.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    event_type: tuple(field for field, _ in fields) for event_type, fields in _CONCRETE_RULES.items()
}
REQUIRED_FIELDS["result.record"] = tuple(sorted(RECORD_FIELDS))
REQUIRED_FIELDS["result.invalidate"] = tuple(sorted(INVALIDATION_FIELDS))
REQUIRED_FIELDS["reading.retract"] = ("target", "reason")

_RESULT_TYPES = {"result.record", "result.invalidate"}


def _check(event_type: str, field: str, value: Any, kind: str) -> None:
    if kind == TEXT:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == STRING:
        if not isinstance(value, str):
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == NULLABLE_TEXT:
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == POSITIVE_INTEGER:
        if type(value) is not int or value < 1:
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == INTEGER:
        if type(value) is not int:
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == BOOLEAN:
        if type(value) is not bool:
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == ARRAY:
        if not isinstance(value, list):
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    elif kind == OBJECT:
        if not isinstance(value, dict):
            raise ValueError(f"{event_type}: {field} must be {_DESCRIPTIONS[kind]}")
    else:  # pragma: no cover - a programming error in the table above
        raise ValueError(f"{event_type}: unknown admission kind for {field!r}")


def validate_payload(event_type: str, data: Any) -> None:
    """Raise ``ValueError`` when ``data`` is not an admissible payload.

    Unknown event types are rejected here too; callers that already enforce the
    registered vocabulary (``Ledger.append``/``Ledger.verify``) keep their own
    messages and only call this for registered types.
    """
    if not isinstance(event_type, str) or event_type not in REQUIRED_FIELDS:
        raise ValueError(f"unregistered event type: {event_type!r}")
    if not isinstance(data, dict):
        raise ValueError(f"{event_type}: payload must be an object")
    if event_type in _RESULT_TYPES or event_type == "reading.retract":
        # One payload, one rule: reuse the results/readings validators verbatim.
        try:
            if event_type in _RESULT_TYPES:
                validate_result_payload(event_type, data)
            else:
                validate_retraction_payload(event_type, data)
        except ValueError as exc:
            raise ValueError(f"{event_type}: {exc}") from exc
        return
    for field, kind in _CONCRETE_RULES[event_type]:
        if field not in data:
            raise ValueError(f"{event_type}: missing required field {field!r}")
        _check(event_type, field, data[field], kind)
