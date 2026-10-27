"""Payload admission for all 17 registered ledger event types.

These are SYNTHETIC structural checks, not scientific or provenance tests.  They
prove that a realistic producer payload is admitted, that a missing key or a
mistyped load-bearing field is refused by ``Ledger.append`` and reported by
``Ledger.verify``, and that the pre-existing legacy result/retraction payload
rules and their reported vocabulary are unchanged.  Every event type listed in
``ledger.EVENT_ACTORS`` must have exactly one admission rule; the result types
stay in the vocabulary only so old ledgers keep verifying.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills" / "ai-research-mentor" / "runtime"))

from research_mentor.contracts import PACKAGE_VERSION
from research_mentor.event_payloads import REQUIRED_FIELDS, validate_payload
from research_mentor.ledger import (
    ANCHOR_PROTOCOL, EVENT_ACTORS, PROTOCOL, Ledger, LedgerError, canonical_json, digest,
)

STAMP = "2026-10-10T00:00:00Z"
HASH = "0" * 64

# Realistic producer shapes (core.py, judgment.py, cli.py) plus the readings
# payload; legacy result payloads are kept for old-ledger admission coverage.
# Extra producer-only keys are included where they are useful for realism; the
# admission rule ignores keys it does not need.
REALISTIC = {
    "project.init": {
        "project_id": "PROJECT-0123456789abcdef", "core_version": PACKAGE_VERSION,
    },
    "project.update": {
        "id": "SYNTHETIC-project", "question": "SYNTHETIC question",
        "research_type": "empirical", "constraints": {}, "assumptions": [],
    },
    "search.result": {
        "id": "S-0123456789abcdef", "query": "SYNTHETIC query", "provider": "crossref",
        "family": "problem", "requested_params": {"limit": 10, "start": 0}, "limit": 10,
        "result_paper_ids": [], "papers": [], "limitations": [], "executed": True,
        "status": "complete", "stop_reason": "provider_results_exhausted",
    },
    "paper.resolve": {
        "id": "P-0123456789abcdef", "identifiers": {"doi": "10.5555/synthetic"},
        "title": "SYNTHETIC paper", "authors": [], "year": 2026, "version": "unknown",
        "abstract": "", "provider": "crossref", "source_url": "https://doi.org/10.5555/synthetic",
        "read_scope": "not_read", "status": "resolved", "receipt": {"artifact": "sources/synthetic.bin"},
    },
    "source.fetch": {
        "id": "SRC-0123456789abcdef", "paper_id": None,
        "source_identity": {"status": "unconfirmed", "paper_id": None, "version": "unknown"},
        "source_url": None, "media_type": "text/plain",
        "receipt": {"artifact": "sources/synthetic.bin", "raw_sha256": HASH, "bytes": 12,
                    "provider": "local", "generated_by": "research-mentor-python-acquisition-v1",
                    "request": {}},
        "raw_sha256": HASH, "text_sha256": "1" * 64, "ir_sha256": "2" * 64,
        "ir_path": "sources/synthetic.ir.json", "extractor": "text-utf8-v1",
        "normalization": "NFC-whitespace-v1", "block_count": 1, "read_scope": "not_read",
        "needs_host_review": True, "needs_host_extraction": False, "limitations": [],
    },
    "evidence.anchor": {
        "id": "E-0123456789abcdef", "source": "SRC-0123456789abcdef", "source_event": "EV-000003",
        "source_ir_sha256": "2" * 64, "locator": "text", "start": 0, "end": 20,
        "quote": "SYNTHETIC quote text", "quote_normalized": "SYNTHETIC quote text",
        "quote_sha256": "3" * 64, "source_sha256": "1" * 64, "match": "exact",
        "anchor_version": "text-normalized-v1", "read_scope": "not_read", "block_id": None,
        "section": "unknown", "lossy": False,
    },
    "source.identity.confirm": {
        "source_id": "SRC-0123456789abcdef", "source_event": "EV-000003",
        "paper_id": "P-0123456789abcdef", "version": "unknown", "resolve_event": "EV-000002",
        "statement": "SYNTHETIC human checked the fixture identity",
        "source_snapshot": "4" * 64, "status": "human_confirmed",
    },
    "candidate.upsert": {
        "id": "C-SYNTHETIC", "version": 1, "title": "SYNTHETIC candidate",
        "question": "SYNTHETIC question?", "hypothesis": "SYNTHETIC hypothesis",
        "contribution": "SYNTHETIC contribution", "research_type": "empirical",
        "search_ids": [], "nearest_work": [],
        "novelty": {"status": "unclear", "reason": "Unassessed"},
        "feasibility": {"status": "unknown", "reason": "Unconfirmed", "dependencies": []},
        "validation": {"status": "missing"},
    },
    "claim.add": {
        "text": "SYNTHETIC claim", "candidate_id": "C-SYNTHETIC", "candidate_version": 1,
        "kind": "hypothesis", "load_bearing": True,
    },
    "claim.link": {
        "claim_id": "EV-000008", "evidence_id": "E-0123456789abcdef", "relation": "supports",
        "target": "hypothesis", "decision_relevant": True,
    },
    "reading.confirm": {
        "evidence_id": "E-0123456789abcdef", "scope": "section",
        "context": "SYNTHETIC fixture section actually inspected", "visual_checked": False,
    },
    "reading.retract": {"target": "EV-000012", "reason": "SYNTHETIC honest withdrawal"},
    "review.record": {
        "candidate_id": "C-SYNTHETIC", "candidate_version": 1, "snapshot": "5" * 64,
        "policy_version": "python-credibility-v5", "machine_recommendation": "HOLD",
        "requested_recommendation": "GO", "stage": "pilot", "scope": "scientific_framing",
        "kill_type": None, "reason": "SYNTHETIC review", "missing": ["SYNTHETIC missing input"],
        "coverage": {}, "legacy_result_events_ignored": 0, "warnings": [],
        "artifact_verification": {"valid": True, "receipts_verified": 0},
        "human_decision": None, "approval_status": "pending_human", "notice": "SYNTHETIC notice",
    },
    "decision.record": {
        "candidate_id": "C-SYNTHETIC", "candidate_version": 1, "review_id": "EV-000014",
        "snapshot": "5" * 64, "machine_recommendation": "HOLD", "human_decision": "HOLD",
        "statement": "SYNTHETIC actual user statement", "override_reason": "",
        "stage": "pilot", "scope": "scientific_framing",
    },
    "decision.revoke": {"candidate_id": "C-SYNTHETIC", "statement": "SYNTHETIC user revocation"},
    "result.record": {
        "id": "R-000001", "run_id": "RUN-SYNTHETIC", "candidate_id": "C-SYNTHETIC",
        "candidate_version": 1, "kind": "scientific", "outcome": "not_run", "artifacts": [],
        "summary": "SYNTHETIC declared result", "limitations": [], "affected_claims": [],
    },
    "result.invalidate": {
        "id": "RI-000001", "run_id": "RUN-SYNTHETIC", "candidate_id": "C-SYNTHETIC",
        "candidate_version": 1, "result_id": "R-000001", "reason": "SYNTHETIC invalidation",
        "recorded_at": STAMP,
    },
}

# One load-bearing field per type and a value that has the wrong primitive type.
BREAKABLE = {
    "project.init": ("project_id", 7),
    "project.update": ("constraints", []),
    "search.result": ("limit", "10"),
    "paper.resolve": ("identifiers", []),
    "source.fetch": ("receipt", []),
    "evidence.anchor": ("start", "0"),
    "source.identity.confirm": ("statement", 5),
    "candidate.upsert": ("version", "1"),
    "claim.add": ("load_bearing", "false"),
    "claim.link": ("decision_relevant", 0),
    "reading.confirm": ("visual_checked", "false"),
    "reading.retract": ("reason", 0),
    "review.record": ("candidate_version", "1"),
    "decision.record": ("human_decision", 3),
    "decision.revoke": ("statement", 0),
    "result.record": ("candidate_version", "1"),
    "result.invalidate": ("recorded_at", "2026-10-10"),
}


def make_event(event_type, data, *, seq=1, prev=None):
    actor, trust = sorted(EVENT_ACTORS[event_type])[0]
    event = {"seq": seq, "id": f"EV-{seq:06d}", "ts": STAMP, "type": event_type,
             "actor": actor, "trust": trust, "data": data, "prev": prev, "protocol": PROTOCOL}
    event["sha256"] = digest(event)
    return event


def write_ledger(project, events):
    """Write JSONL and a matching anchor directly, as a tampering writer would."""
    root = Path(project)
    root.mkdir(parents=True, exist_ok=True)
    (root / "ledger.jsonl").write_text(
        "".join(canonical_json(event) + "\n" for event in events), encoding="utf-8")
    head = events[-1]["sha256"] if events else ""
    (root / "ledger.anchor.json").write_text(
        canonical_json({"protocol": ANCHOR_PROTOCOL, "event_count": len(events), "head": head}) + "\n",
        encoding="utf-8")


class LedgerPayloadAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mentor-ledger-payloads-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def ledger(self, name):
        return Ledger(self.root / name)

    def test_every_registered_type_has_exactly_one_admission_rule(self):
        self.assertEqual(set(REQUIRED_FIELDS), set(EVENT_ACTORS))
        self.assertEqual(set(REALISTIC), set(EVENT_ACTORS))
        self.assertEqual(set(BREAKABLE), set(EVENT_ACTORS))

    def test_realistic_payload_is_admitted_and_verifies_for_all_17_types(self):
        for event_type in sorted(EVENT_ACTORS):
            with self.subTest(event_type=event_type):
                ledger = self.ledger(event_type.replace(".", "_"))
                actor, trust = sorted(EVENT_ACTORS[event_type])[0]
                appended = ledger.append(event_type, deepcopy(REALISTIC[event_type]),
                                         actor=actor, trust=trust)
                self.assertEqual(appended["data"], REALISTIC[event_type])
                report = ledger.verify()
                self.assertTrue(report["valid"], report["errors"])
                self.assertEqual(report["event_count"], 1)
                self.assertEqual(report["anchor"], "matched")

    def test_missing_key_and_wrong_type_are_refused_by_append_and_reported_by_verify(self):
        for event_type in sorted(EVENT_ACTORS):
            field, wrong = BREAKABLE[event_type]
            cases = {
                "missing": {key: value for key, value in REALISTIC[event_type].items() if key != field},
                "wrong_type": {**deepcopy(REALISTIC[event_type]), field: wrong},
            }
            for case, broken in cases.items():
                with self.subTest(event_type=event_type, case=case):
                    self.assertNotEqual(broken, REALISTIC[event_type])
                    ledger = self.ledger(f"{event_type.replace('.', '_')}-{case}")
                    actor, trust = sorted(EVENT_ACTORS[event_type])[0]
                    with self.assertRaises(LedgerError) as caught:
                        ledger.append(event_type, deepcopy(broken), actor=actor, trust=trust)
                    message = str(caught.exception)
                    self.assertTrue(message.startswith(event_type + ":"), message)
                    if event_type not in {"result.record", "result.invalidate", "reading.retract"}:
                        # Delegated validators keep their own established wording.
                        self.assertIn(field, message)
                    self.assertFalse(ledger.path.exists(), "a rejected payload must not write")
                    # A directly written chain with a correctly recomputed hash must
                    # still be reported invalid, otherwise verify would accept it.
                    directory = self.root / f"verify-{event_type.replace('.', '_')}-{case}"
                    first = make_event(event_type, deepcopy(REALISTIC[event_type]))
                    second = make_event(event_type, broken, seq=2, prev=first["sha256"])
                    write_ledger(directory, [first, second])
                    report = Ledger(directory).verify()
                    self.assertFalse(report["valid"])
                    self.assertEqual(report["anchor"], "matched", "only the payload may be invalid")
                    self.assertTrue(any("line 2" in error and "payload" in error for error in report["errors"]),
                                    report["errors"])

    def test_tampered_candidate_upsert_without_id_invalidates_the_ledger(self):
        directory = self.root / "tampered"
        payload = deepcopy(REALISTIC["candidate.upsert"])
        payload.pop("id")
        write_ledger(directory, [make_event("candidate.upsert", payload)])
        report = Ledger(directory).verify()
        self.assertFalse(report["valid"])
        self.assertEqual(report["event_count"], 1)
        self.assertEqual(report["anchor"], "matched")
        self.assertTrue(any("invalid event payload at line 1: candidate.upsert:" in error
                            for error in report["errors"]), report["errors"])
        with self.assertRaisesRegex(LedgerError, "refusing append to invalid ledger"):
            Ledger(directory).append("candidate.upsert", deepcopy(REALISTIC["candidate.upsert"]),
                                     actor="model", trust="T2")

    def test_direct_append_of_candidate_upsert_without_id_is_rejected(self):
        ledger = self.ledger("candidate-missing-id")
        payload = deepcopy(REALISTIC["candidate.upsert"])
        payload.pop("id")
        with self.assertRaisesRegex(LedgerError, r"candidate\.upsert: missing required field 'id'"):
            ledger.append("candidate.upsert", payload, actor="model", trust="T2")
        self.assertEqual(ledger.read(), [])
        self.assertFalse((self.root / "candidate-missing-id" / "ledger.lock").exists())

    def test_legacy_result_and_reading_retraction_rules_keep_their_single_rule_and_vocabulary(self):
        result_payload = {**deepcopy(REALISTIC["result.record"]), "outcome": "invented"}
        write_ledger(self.root / "result-rule", [make_event("result.record", result_payload)])
        result_report = Ledger(self.root / "result-rule").verify()
        self.assertFalse(result_report["valid"])
        self.assertTrue(any(error.startswith("invalid result payload at line 1: result.record:")
                            for error in result_report["errors"]), result_report["errors"])
        retraction_payload = {"target": "EV-000012"}
        write_ledger(self.root / "retraction-rule",
                     [make_event("reading.retract", retraction_payload)])
        retraction_report = Ledger(self.root / "retraction-rule").verify()
        self.assertFalse(retraction_report["valid"])
        self.assertTrue(any(error.startswith("invalid reading retraction payload at line 1: reading.retract:")
                            for error in retraction_report["errors"]), retraction_report["errors"])

    def test_extra_keys_remain_forward_compatible(self):
        ledger = self.ledger("extra-keys")
        payload = {**deepcopy(REALISTIC["project.init"]),
                   "future_field": {"nested": [1, True, None]}}
        event = ledger.append("project.init", payload)
        self.assertEqual(event["data"], payload)
        self.assertTrue(ledger.verify()["valid"])

    def test_validator_rejects_unknown_event_type_directly(self):
        with self.assertRaisesRegex(ValueError, "unregistered event type"):
            validate_payload("project.innit", {})


if __name__ == "__main__":
    unittest.main()
