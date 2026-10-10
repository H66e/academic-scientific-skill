"""Python workflow and conservative v0.3 projection regression tests.

All provider responses are explicitly synthetic protocol fixtures. Passing these
checks proves compatibility and failure handling, never search recall or novelty.
"""
from __future__ import annotations

import http.client
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills" / "ai-research-mentor" / "runtime"))

from research_mentor.ledger import Ledger, LedgerError, EVENT_ACTORS
from research_mentor.judgment import Judgment
from research_mentor.core import ResearchCore
from research_mentor.transport import Response, Transport, TransportError


class FixtureTransport:
    """Injected synthetic provider protocol; never opens a network connection."""
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def get(self, url, **kwargs):
        self.calls.append(url)
        if self.fail:
            raise TransportError("SYNTHETIC provider connection failed")
        item = {"DOI": "10.5555/synthetic-contract", "title": ["SYNTHETIC SOURCE — NOT A REAL PAPER"],
                "published": {"date-parts": [[2026]]}}
        metadata = {"message": item if "/works/" in url else {"total-results": 1, "items": [item]}}
        return Response(url, 200, {"content-type": "application/json"},
                        json.dumps(metadata, ensure_ascii=False).encode("utf-8"), "synthetic_protocol")


def candidate(**changes):
    value = {
        "id": "C-SYNTHETIC", "title": "SYNTHETIC candidate; no research finding",
        "question": "Can an invented bounded intervention be tested?",
        "research_type": "empirical", "hypothesis": "SYNTHETIC untested hypothesis",
        "contribution": "SYNTHETIC protocol demonstration", "search_ids": [],
        "nearest_work": [],
    }
    value.update(changes)
    return value


class ProjectionContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mentor-contract-")
        self.addCleanup(self.temporary.cleanup)
        self.ledger = Ledger(self.temporary.name, clock=lambda: "2026-10-07T08:00:00Z")
        self.judgment = Judgment(self.ledger)

    def bounded_workflow(self, *, read=True, identity=True, nearest_paper=None,
                         relation="supports", nearest_decisive=True, nearest_empty=False,
                         prebound_paper=True):
        """A complete synthetic pilot workflow, with no scientific result claimed."""
        core = ResearchCore(self.temporary.name, transport=FixtureTransport())
        search = core.search("SYNTHETIC intervention query", provider="crossref", sensitivity="public", family="problem")
        reverse = core.search("SYNTHETIC nearest-work alternative", provider="crossref", sensitivity="public", family="reverse")
        self.assertTrue(search.ok, search.errors)
        self.assertTrue(reverse.ok, reverse.errors)
        paper_id = search.data["papers"][0]["id"]
        path = Path(self.temporary.name) / "synthetic-nearest.txt"
        path.write_text("SYNTHETIC source section: this fixture motivates a bounded intervention test; no result is observed.", encoding="utf-8")
        source = core.fetch(local_path=path, paper_id=paper_id if prebound_paper else None)
        self.assertTrue(source.ok, source.errors)
        if identity:
            resolved = core.resolve("10.5555/synthetic-contract")
            self.assertTrue(resolved.ok, resolved.errors)
            confirmed = core.confirm_source_identity(source.data["id"], paper_id, "unknown",
                "SYNTHETIC user confirms this is the fixture source; version is explicitly unknown", human=True)
            self.assertTrue(confirmed.ok, confirmed.errors)
        quote = core.quote(source.data["id"], "this fixture motivates a bounded intervention test; no result is observed.")
        self.assertTrue(quote.ok, quote.errors)
        data = candidate(
            search_ids=[search.data["id"], reverse.data["id"]],
            nearest_work=[{"paper_id": nearest_paper or paper_id, "evidence_ids": [] if nearest_empty else [quote.data["id"]],
                           "delta": "SYNTHETIC difference: planned test rather than observed result", "decisive": nearest_decisive}],
            novelty={"status": "incremental", "reason": "SYNTHETIC scoped comparison only"},
            feasibility={"status": "ready", "reason": "SYNTHETIC local fixture is available",
                         "dependencies": [{"name": "synthetic fixture", "mandatory": True, "status": "met", "basis": "local fixture exists"}]},
            validation={"status": "specified", "prediction": "SYNTHETIC response changes by the predeclared amount",
                        "falsifier": "Paired fixture results show no predeclared change",
                        "design": "Paired local fixture comparison", "metric": "Difference in an invented scalar",
                        "resource_estimate": "Two local fixture calls", "stop_rule": "Stop after both paired calls"},
        )
        self.judgment.upsert_candidate(data)
        claim = self.judgment.add_claim("SYNTHETIC hypothesis is testable by the bounded pilot", "C-SYNTHETIC")
        self.judgment.link_claim(claim["id"], quote.data["id"], relation=relation, target="validation")
        if read:
            self.judgment.confirm_read(quote.data["id"], "section", "SYNTHETIC fixture section actually inspected")
        return core, claim["id"], quote.data["id"]

    def node_contract(self, dossier):
        if shutil.which("node") is None:
            self.skipTest("Node reference runtime is unavailable")
        audit_uri = (REPO / "skills" / "ai-research-mentor" / "scripts" / "research_audit.mjs").as_uri()
        script = (
            "import fs from 'node:fs';"
            "const audit = await import(" + json.dumps(audit_uri) + ");"
            "const d = JSON.parse(fs.readFileSync(0, 'utf8'));"
            "const validation = audit.validateDossier(d);"
            "console.log(JSON.stringify({validation,ranking:validation.valid?audit.rankDossier(d):null}));"
        )
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            input=json.dumps(dossier, ensure_ascii=False).encode("utf-8"),
            capture_output=True, timeout=30, cwd=REPO,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return json.loads(result.stdout.decode("utf-8"))

    def test_empty_projection_is_valid_and_has_no_approval(self):
        dossier = self.judgment.export_dossier()
        checked = self.node_contract(dossier)
        self.assertTrue(checked["validation"]["valid"], checked["validation"]["errors"])
        self.assertEqual(checked["ranking"]["ranked"], [])
        self.assertEqual(dossier["evidence"], [])
        self.assertEqual(dossier["reviews"], [])

    def test_candidate_projection_remains_hold_and_preserves_utf8(self):
        self.judgment.upsert_candidate(candidate(title="SYNTHETIC 中文候选—未验证"))
        dossier = self.judgment.export_dossier()
        checked = self.node_contract(dossier)
        self.assertTrue(checked["validation"]["valid"], checked["validation"]["errors"])
        self.assertEqual(checked["ranking"]["ranked"], [])
        self.assertEqual(len(checked["ranking"]["held"]), 1)
        self.assertEqual(dossier["ideas"][0]["title"], "SYNTHETIC 中文候选—未验证")
        self.assertEqual(dossier["ideas"][0]["novelty"]["status"], "unclear")
        self.assertEqual(dossier["reviews"], [])

    def test_projection_does_not_upgrade_a_recorded_human_override_to_node_go(self):
        self.judgment.upsert_candidate(candidate())
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC missing-source demonstration")
        self.assertEqual(review["machine_recommendation"], "HOLD")
        self.judgment.record_decision(review["review_id"], "GO", "SYNTHETIC user override only",
                                      human=True, override_reason="SYNTHETIC accepts an information-gathering step")
        dossier = self.judgment.export_dossier()
        checked = self.node_contract(dossier)
        self.assertTrue(checked["validation"]["valid"], checked["validation"]["errors"])
        self.assertEqual(dossier["reviews"], [])
        self.assertEqual(checked["ranking"]["ranked"], [])
        self.assertEqual(len(checked["ranking"]["held"]), 1)

    def test_model_tagged_decision_is_not_a_human_approval(self):
        self.judgment.upsert_candidate(candidate())
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC unassessed candidate")
        with self.assertRaises(LedgerError):
            self.ledger.append("decision.record", {
                "candidate_id": "C-SYNTHETIC", "candidate_version": 1,
                "review_id": review["review_id"], "snapshot": review["snapshot"],
                "machine_recommendation": "HOLD", "human_decision": "GO",
                "statement": "SYNTHETIC fabricated model claim of approval",
            }, actor="model", trust="T2")
        status = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(status["approval_status"], "pending_human")
        self.assertIsNone(status["human_decision"])

    def test_actual_human_record_expires_when_candidate_changes(self):
        self.judgment.upsert_candidate(candidate())
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC HOLD demonstration")
        self.judgment.record_decision(review["review_id"], "HOLD", "SYNTHETIC actual user statement", human=True)
        before = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(before["approval_status"], "human_recorded")
        self.assertEqual(before["human_decision"], "HOLD")
        self.assertFalse(before["execution_authorized"])
        self.judgment.upsert_candidate(candidate(hypothesis="SYNTHETIC changed hypothesis"))
        after = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(after["approval_status"], "pending_human")
        self.assertIsNone(after["human_decision"])
        with self.assertRaises(ValueError):
            self.judgment.record_decision(review["review_id"], "HOLD", "stale statement", human=True)

    def test_provider_acquisition_survives_projection_without_inventing_evidence(self):
        transport = FixtureTransport()
        core = ResearchCore(self.temporary.name, transport=transport)
        result = core.search("SYNTHETIC protocol query", provider="crossref", sensitivity="public", family="problem")
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.status, "complete")
        self.assertEqual(len(result.data["papers"]), 1)
        self.assertTrue(core.verify_artifacts()["valid"])
        self.judgment.upsert_candidate(candidate(search_ids=[result.data["id"]]))
        dossier = self.judgment.export_dossier()
        self.assertEqual(len(dossier["papers"]), 1, "Projection must preserve actually acquired metadata")
        self.assertEqual(dossier["searches"][0]["result_paper_ids"], [result.data["papers"][0]["id"]])
        self.assertEqual(dossier["evidence"], [])
        checked = self.node_contract(dossier)
        self.assertTrue(checked["validation"]["valid"], checked["validation"]["errors"])
        self.assertEqual(checked["ranking"]["ranked"], [])

    def test_private_default_and_offline_never_invoke_provider(self):
        transport = FixtureTransport()
        core = ResearchCore(self.temporary.name, transport=transport)
        blocked = core.search("SYNTHETIC unpublished idea", provider="crossref")
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.status, "blocked")
        offline = core.search("SYNTHETIC unpublished idea", provider="crossref", offline=True)
        self.assertEqual(offline.status, "offline")
        self.assertEqual(transport.calls, [])
        projection = self.judgment.export_dossier()
        self.assertEqual(projection["papers"], [])
        self.assertEqual(projection["evidence"], [])
        self.assertFalse(any(search["status"] == "complete" for search in projection["searches"]))

    def test_failed_actual_search_is_retained_for_coverage_and_not_novelty(self):
        transport = FixtureTransport(fail=True)
        core = ResearchCore(self.temporary.name, transport=transport)
        result = core.search("SYNTHETIC query", provider="crossref", sensitivity="public")
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "failed")
        self.assertEqual(len(transport.calls), 1)
        searches = [event for event in self.ledger.read() if event["type"] == "search.result"]
        self.assertEqual(len(searches), 1, "An attempted failed request must remain in the coverage denominator")
        self.assertEqual(searches[0]["data"]["status"], "failed")
        self.assertEqual(searches[0]["data"]["result_paper_ids"], [])
        dossier = self.judgment.export_dossier()
        checked = self.node_contract(dossier)
        self.assertTrue(checked["validation"]["valid"], checked["validation"]["errors"])
        self.assertEqual(dossier["papers"], [])
        self.assertEqual(checked["ranking"]["ranked"], [])

    def test_quotes_do_not_create_reading_and_changed_bytes_invalidate_artifacts(self):
        core = ResearchCore(self.temporary.name)
        path = Path(self.temporary.name) / "synthetic-input.txt"
        path.write_text("SYNTHETIC source: a bounded intervention may alter an invented metric.", encoding="utf-8")
        acquired = core.fetch(local_path=path)
        self.assertTrue(acquired.ok, acquired.errors)
        self.assertEqual(acquired.data["read_scope"], "not_read")
        quote = core.quote(acquired.data["id"], "a bounded intervention may alter an invented metric")
        self.assertTrue(quote.ok, quote.errors)
        self.assertEqual(quote.data["read_scope"], "not_read")
        self.assertFalse(any(e["type"] == "reading.confirm" for e in self.ledger.read()))
        self.assertTrue(core.verify_artifacts()["valid"])
        raw_path = Path(self.temporary.name) / acquired.data["receipt"]["artifact"]
        raw_path.write_bytes(b"SYNTHETIC accidentally replaced source")
        self.assertFalse(core.verify_artifacts()["valid"])
        changed_quote = core.quote(acquired.data["id"], "a bounded intervention may alter an invented metric")
        self.assertFalse(changed_quote.ok)

    def test_new_source_bytes_invalidate_an_existing_human_decision(self):
        core = ResearchCore(self.temporary.name)
        path = Path(self.temporary.name) / "synthetic-input.txt"
        path.write_text("SYNTHETIC acquired content only", encoding="utf-8")
        acquired = core.fetch(local_path=path)
        self.assertTrue(acquired.ok, acquired.errors)
        self.judgment.upsert_candidate(candidate())
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC pending literature")
        self.judgment.record_decision(review["review_id"], "HOLD", "SYNTHETIC actual instruction", human=True)
        self.assertEqual(self.judgment.finalize("C-SYNTHETIC")["approval_status"], "human_recorded")
        artifact = Path(self.temporary.name) / acquired.data["receipt"]["artifact"]
        artifact.write_bytes(b"SYNTHETIC accidental source overwrite")
        result = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(result["approval_status"], "pending_human")
        self.assertIsNone(result["human_decision"])

    def test_invented_exact_anchor_cannot_pass_artifact_verification(self):
        core = ResearchCore(self.temporary.name)
        path = Path(self.temporary.name) / "synthetic-input.txt"
        path.write_text("SYNTHETIC actual source says the effect is unobserved.", encoding="utf-8")
        acquired = core.fetch(local_path=path)
        self.assertTrue(acquired.ok, acquired.errors)
        self.ledger.append("evidence.anchor", {
            "id": "E-SYNTHETIC-FALSE", "source": acquired.data["id"],
            "source_event": acquired.ledger_events[0], "source_ir_sha256": acquired.data["ir_sha256"],
            "locator": "text", "start": 0, "end": 16,
            "quote": "SYNTHETIC effect is proven", "quote_normalized": "SYNTHETIC effect is proven",
            "quote_sha256": "0" * 64, "source_sha256": acquired.data["text_sha256"],
            "match": "exact", "anchor_version": "text-normalized-v1", "read_scope": "not_read", "block_id": None,
        })
        report = core.verify_artifacts()
        self.assertFalse(report["valid"], "A label 'exact' is not a verified source anchor")

    def test_complete_bounded_workflow_can_recommend_a_pilot_and_still_waits_for_human(self):
        self.bounded_workflow()
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC complete bounded pilot fixture")
        self.assertEqual(result["machine_recommendation"], "GO", result["missing"])
        self.assertEqual(result["stage"], "pilot")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["approval_status"], "pending_human")
        self.assertIsNone(result["human_decision"])
        self.assertFalse(result["coverage"]["coverage_complete"])
        self.judgment.record_decision(result["review_id"], "GO", "SYNTHETIC user accepts this bounded pilot", human=True)
        final = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(final["approval_status"], "human_recorded")
        self.assertEqual(final["human_decision"], "GO")
        self.assertFalse(final["execution_authorized"])
        # A new review is a new decision basis even when scientific inputs match.
        self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC second assessment")
        self.assertEqual(self.judgment.finalize("C-SYNTHETIC")["approval_status"], "pending_human")

    def test_acquired_anchor_without_relevant_section_reading_stays_hold(self):
        self.bounded_workflow(read=False)
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC missing explicit reading")
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(any("reading" in missing for missing in result["missing"]), result["missing"])

    def test_core_contradiction_prevents_go_even_after_all_acquisition_steps(self):
        _, claim_id, evidence_id = self.bounded_workflow()
        first = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC pilot fixture before contradiction")
        self.assertEqual(first["machine_recommendation"], "GO", first["missing"])
        self.judgment.link_claim(claim_id, evidence_id, "contradicts", target="validation")
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC contradictory interpretation must stay unresolved")
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(any("contradicts" in missing for missing in result["missing"]), result["missing"])

    def test_nearest_work_cannot_borrow_another_papers_anchor(self):
        self.bounded_workflow(nearest_paper="P-SYNTHETIC-DIFFERENT")
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC wrong-paper anchor must not support nearest work")
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(any("different/unresolved paper" in missing for missing in result["missing"]), result["missing"])

    def test_caller_supplied_paper_id_does_not_verify_local_source_identity(self):
        self.bounded_workflow(identity=False)
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC paper identity was only asserted by the caller")
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(any("identity" in missing for missing in result["missing"]), result["missing"])

    def test_context_only_citation_does_not_support_a_load_bearing_claim(self):
        self.bounded_workflow(relation="context")
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC context citation provides no claim support")
        self.assertEqual(result["machine_recommendation"], "HOLD", result["missing"])
        self.assertTrue(result["missing"])

    def test_calling_a_neighbor_nondecisive_cannot_bypass_anchored_comparison(self):
        self.bounded_workflow(nearest_decisive=False, nearest_empty=True)
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC unsupported nearest-work comparison")
        self.assertEqual(result["machine_recommendation"], "HOLD", result["missing"])
        self.assertTrue(any("anchor" in missing for missing in result["missing"]), result["missing"])

    def test_cli_utf8_envelope_survives_a_gbk_pipe_without_network(self):
        launcher = REPO / "skills" / "ai-research-mentor" / "scripts" / "research_mentor.py"
        env = dict(os.environ, PYTHONIOENCODING="gbk", PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [sys.executable, "-B", str(launcher), "--project", self.temporary.name,
             "search", "SYNTHETIC 中文私有想法—离线", "--offline"],
            capture_output=True, timeout=30, cwd=REPO, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        envelope = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(set(envelope), {"ok", "status", "data", "warnings", "errors", "ledger_events", "next"})
        self.assertEqual(envelope["status"], "offline")
        self.assertEqual(envelope["data"]["query"], "SYNTHETIC 中文私有想法—离线")
        self.assertEqual(envelope["data"]["result_paper_ids"], [])
        self.assertTrue(self.ledger.verify()["valid"])

    def test_cli_default_private_query_reports_blocked_and_does_not_create_search(self):
        launcher = REPO / "skills" / "ai-research-mentor" / "scripts" / "research_mentor.py"
        result = subprocess.run(
            [sys.executable, "-B", str(launcher), "--project", self.temporary.name,
             "search", "SYNTHETIC unpublished private idea"],
            capture_output=True, timeout=30, cwd=REPO,
        )
        self.assertEqual(result.returncode, 2, result.stderr.decode("utf-8", errors="replace"))
        envelope = json.loads(result.stdout.decode("utf-8"))
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual(self.ledger.read(), [])

    def test_changed_resources_make_old_go_an_explicit_stale_recommendation(self):
        self.bounded_workflow()
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC original bounded pilot")
        self.assertEqual(review["machine_recommendation"], "GO", review["missing"])
        self.judgment.record_decision(review["review_id"], "GO", "SYNTHETIC user accepts original resources", human=True)
        self.ledger.append("project.update", {"id": "SYNTHETIC-project", "question": "SYNTHETIC question",
            "research_type": "empirical", "assumptions": [], "constraints": {"gpu": {
                "status": "confirmed", "value": 0, "source": "SYNTHETIC actual user says zero GPU available"}}},
            actor="user", trust="T1")
        final = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(final["machine_recommendation"], "HOLD")
        self.assertEqual(final["previous_recommendation"], "GO")
        self.assertTrue(final["assessment_required"])
        self.assertEqual(final["approval_status"], "pending_human")
        self.assertIsNone(final["human_decision"])

    def test_human_can_revoke_a_current_decision_without_erasing_history(self):
        self.bounded_workflow()
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC scoped recommendation")
        decision = self.judgment.record_decision(review["review_id"], "GO", "SYNTHETIC actual user accepts", human=True)
        self.assertEqual(self.judgment.finalize("C-SYNTHETIC")["approval_status"], "human_recorded")
        with self.assertRaises(ValueError):
            self.judgment.revoke_decision("C-SYNTHETIC", "SYNTHETIC model cannot revoke on user's behalf")
        revoked = self.judgment.revoke_decision("C-SYNTHETIC", "SYNTHETIC user withdraws permission", human=True)
        self.assertEqual(revoked["actor"], "user")
        final = self.judgment.finalize("C-SYNTHETIC")
        self.assertEqual(final["machine_recommendation"], "GO")
        self.assertFalse(final["assessment_required"])
        self.assertEqual(final["approval_status"], "pending_human")
        self.assertIsNone(final["human_decision"])
        self.assertEqual(self.ledger.get(decision["id"])["data"]["human_decision"], "GO")

    def test_expected_head_rejects_an_append_based_on_a_concurrently_changed_ledger(self):
        first = self.ledger.append("project.init", {"name": "SYNTHETIC concurrent fixture"}, expected_head="")
        accepted = self.ledger.append("claim.add", {"text": "SYNTHETIC first writer"},
            actor="model", trust="T2", expected_head=first["sha256"])
        with self.assertRaisesRegex(LedgerError, "ledger changed"):
            self.ledger.append("claim.add", {"text": "SYNTHETIC stale second writer"},
                actor="model", trust="T2", expected_head=first["sha256"])
        events = self.ledger.read()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["id"], accepted["id"])
        self.assertTrue(self.ledger.verify()["valid"])
        self.assertFalse((Path(self.temporary.name) / "ledger.lock").exists())

    def test_local_source_without_preassigned_paper_can_be_confirmed_and_assessed(self):
        core, _, evidence_id = self.bounded_workflow(prebound_paper=False)
        evidence = next(e for e in self.ledger.read() if e["type"] == "evidence.anchor" and e["data"]["id"] == evidence_id)
        source = self.ledger.get(evidence["data"]["source_event"])
        self.assertIsNone(source["data"]["paper_id"])
        confirmations = [e for e in self.ledger.read() if e["type"] == "source.identity.confirm"]
        self.assertEqual(len(confirmations), 1)
        self.assertEqual(confirmations[0]["data"]["source_event"], source["id"])
        self.assertTrue(core.verify_artifacts()["valid"])
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC source identity confirmed after local acquisition")
        self.assertEqual(result["machine_recommendation"], "GO", result["missing"])

    def test_model_cannot_assert_confirmed_user_resources(self):
        with self.assertRaises(LedgerError):
            self.ledger.append("project.update", {"constraints": {"gpu": {
                "status": "confirmed", "value": 0, "source": "SYNTHETIC invented user statement"}}},
                actor="model", trust="T2")
        self.assertEqual(self.ledger.read(), [])

    def test_confirmed_zero_or_false_resource_can_kill_only_within_current_constraints(self):
        for value in (0, False):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory(prefix="mentor-zero-constraint-") as project:
                    ledger = Ledger(project)
                    judgment = Judgment(ledger)
                    ledger.append("project.update", {"constraints": {"gpu": {
                        "status": "confirmed", "value": value,
                        "source": "SYNTHETIC actual user confirms unavailable resource"}}}, actor="user", trust="T1")
                    judgment.upsert_candidate(candidate(feasibility={"status": "blocked", "reason": "SYNTHETIC GPU absent",
                        "dependencies": [{"name": "GPU availability", "mandatory": True, "status": "failed",
                                          "basis": "SYNTHETIC user constraint", "constraint_keys": ["gpu"]}]}))
                    scoped = judgment.assess("C-SYNTHETIC", recommendation="KILL", reason="SYNTHETIC blocked required dependency",
                        kill_type="constraints", scope="current_constraints")
                    self.assertEqual(scoped["machine_recommendation"], "KILL", scoped["missing"])
                    self.assertEqual(scoped["scope"], "current_constraints")
                    scientific = judgment.assess("C-SYNTHETIC", recommendation="KILL", reason="SYNTHETIC resource failure is not a scientific refutation",
                        kill_type="constraints", scope="scientific_framing")
                    self.assertEqual(scientific["machine_recommendation"], "HOLD")

    def test_schema_and_runtime_agree_on_known_event_roles(self):
        schema_path = REPO / "skills" / "ai-research-mentor" / "schemas" / "ledger-event.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        declared_types = schema["properties"]["type"]["enum"]
        self.assertEqual(set(declared_types), set(EVENT_ACTORS))
        self.assertEqual(len(declared_types), len(EVENT_ACTORS))
        self.assertTrue({"result.record", "result.invalidate"} <= EVENT_ACTORS.keys())
        self.assertNotIn("reading.retract", EVENT_ACTORS)
        typed_roles = {}
        global_pairs = {("tool", "T0"), ("tool", "TL"), ("user", "T1"), ("model", "T2")}
        for rule in schema["allOf"]:
            if "if" not in rule:
                continue
            condition = rule["if"]["properties"]["type"]
            event_types = condition.get("enum", [condition.get("const")])
            properties = rule["then"]["properties"]
            actor_rule, trust_rule = properties["actor"], properties["trust"]
            actors = actor_rule.get("enum", [actor_rule.get("const")])
            trusts = trust_rule.get("enum", [trust_rule.get("const")])
            roles = {(actor, trust) for actor in actors for trust in trusts} & global_pairs
            for event_type in event_types:
                typed_roles[event_type] = roles
        self.assertEqual(typed_roles, EVENT_ACTORS)


class TransportDeadlineTests(unittest.TestCase):
    def fixed_response(self, body, *, clock=None, seconds_per_byte=0):
        """Use real HTTPResponse buffering over one-byte synthetic raw reads."""
        header = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n"
        payload = header + body

        class Raw(io.RawIOBase):
            def __init__(self):
                self.position = 0

            def readable(self):
                return True

            def readinto(self, buffer):
                if self.position == len(payload):
                    return 0
                if clock is not None and self.position >= len(header):
                    clock[0] += seconds_per_byte
                buffer[0] = payload[self.position]
                self.position += 1
                return 1

        class Sock:
            def makefile(self, *args):
                return io.BufferedReader(Raw())

            def settimeout(self, timeout):
                pass

            def shutdown(self, how):
                pass

        class Connection:
            def __init__(self, *args):
                self.sock = Sock()

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                response = http.client.HTTPResponse(self.sock)
                response.begin()
                return response

            def close(self):
                pass

        return Connection

    def test_slow_body_cannot_extend_absolute_deadline_by_delivering_small_chunks(self):
        clock = [0.0]
        connection = self.fixed_response(b"x" * 100, clock=clock, seconds_per_byte=0.25)
        with mock.patch("research_mentor.transport.time.monotonic", side_effect=lambda: clock[0]), \
             mock.patch("research_mentor.transport._bounded_lookup", return_value=[(2, 1, 6, "", ("1.1.1.1", 443))]), \
             mock.patch("research_mentor.transport._PinnedHTTPS", connection), \
             mock.patch("socket.create_connection", side_effect=AssertionError("No network in regression")):
            transport = Transport(timeout=1, max_bytes=100, byte_budget=100)
            with self.assertRaisesRegex(TransportError, "timeout"):
                transport.get("https://example.org/source", allowed_hosts={"example.org"})
        # A buffered read(100) used to consume all bytes and reach 25 seconds.
        self.assertLessEqual(clock[0], 1.0)
        self.assertLessEqual(transport.bytes_received, 4)

    def test_stalled_response_headers_return_at_deadline_and_interrupt_socket(self):
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()

        class Sock:
            def shutdown(self, how):
                release.set()

        class Connection:
            def __init__(self, *args):
                self.sock = Sock()

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                entered.set()
                release.wait(5)
                raise OSError("SYNTHETIC socket interrupted")

            def close(self):
                closed.set()

        with mock.patch("research_mentor.transport._bounded_lookup", return_value=[(2, 1, 6, "", ("1.1.1.1", 443))]), \
             mock.patch("research_mentor.transport._PinnedHTTPS", Connection), \
             mock.patch("socket.create_connection", side_effect=AssertionError("No network in regression")):
            started = time.monotonic()
            try:
                with self.assertRaisesRegex(TransportError, "timeout"):
                    Transport(timeout=1).get("https://example.org/source", allowed_hosts={"example.org"})
                self.assertTrue(entered.is_set())
                self.assertLess(time.monotonic() - started, 3)
                self.assertTrue(release.is_set(), "The timeout must interrupt the active socket")
            finally:
                release.set()
                self.assertTrue(closed.wait(2), "The observation worker must close its connection")

    def test_deadline_reader_preserves_exact_response_and_byte_budget(self):
        with mock.patch("research_mentor.transport._bounded_lookup", return_value=[(2, 1, 6, "", ("1.1.1.1", 443))]), \
             mock.patch("research_mentor.transport._PinnedHTTPS", self.fixed_response(b"abc")), \
             mock.patch("socket.create_connection", side_effect=AssertionError("No network in regression")):
            transport = Transport(max_bytes=3, byte_budget=3)
            response = transport.get("https://example.org/source", allowed_hosts={"example.org"})
            self.assertEqual(response.body, b"abc")
            self.assertEqual(transport.bytes_received, 3)
        with mock.patch("research_mentor.transport._bounded_lookup", return_value=[(2, 1, 6, "", ("1.1.1.1", 443))]), \
             mock.patch("research_mentor.transport._PinnedHTTPS", self.fixed_response(b"abcd")), \
             mock.patch("socket.create_connection", side_effect=AssertionError("No network in regression")):
            transport = Transport(max_bytes=3, byte_budget=3)
            with self.assertRaisesRegex(TransportError, "byte budget"):
                transport.get("https://example.org/source", allowed_hosts={"example.org"})
            self.assertEqual(transport.bytes_received, 4)

    def test_late_proxy_response_is_closed_without_becoming_a_successful_request(self):
        release, closed = threading.Event(), threading.Event()

        class LateResponse:
            code, headers = 200, {}

            def close(self):
                closed.set()

            def read1(self, amount):
                raise AssertionError("A response delivered after the deadline must not be read")

        class Opener:
            def open(self, request, timeout):
                release.wait(5)
                return LateResponse()

        with mock.patch("research_mentor.transport.urllib.request.build_opener", return_value=Opener()), \
             mock.patch("socket.create_connection", side_effect=AssertionError("No network in regression")):
            transport = Transport(timeout=1, trusted_provider_transport=True)
            try:
                with self.assertRaisesRegex(TransportError, "timeout"):
                    transport.get("https://api.crossref.org/works", allowed_hosts={"api.crossref.org"},
                                  trusted_provider=True)
                self.assertEqual(transport.requests[0]["status"], None)
            finally:
                release.set()
                self.assertTrue(closed.wait(2), "A late response must be closed by the worker")
            self.assertEqual(transport.requests[0]["status"], None)
            self.assertEqual(transport.bytes_received, 0)


if __name__ == "__main__":
    unittest.main()
