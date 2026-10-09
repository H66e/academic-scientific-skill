"""Bounded offline regression cases for the Python acquisition core."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

RUNTIME = Path(__file__).resolve().parents[2] / "runtime"
sys.path.insert(0, str(RUNTIME))
from research_mentor.anchors import AnchorError, normalize_text, quote_text
from research_mentor.core import ResearchCore
from research_mentor.judgment import Judgment
from research_mentor.ledger import Ledger, LedgerError, canonical_json, digest
from research_mentor.privacy import PrivacyError, check_outbound
from research_mentor.providers import ProviderError, crossref_papers, normalize_identifier
from research_mentor.transport import Response, Transport, TransportError, checked_url, public_address

class FakeTransport:
    def __init__(self, body=b"", status=200, headers=None, failure=None):
        self.body, self.status, self.headers, self.failure = body, status, headers or {}, failure
        self.calls = []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.failure:
            raise TransportError(self.failure)
        return Response(url, self.status, self.headers, self.body, "fixture")

class PythonCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
    def tearDown(self):
        self.temp.cleanup()

    def _replace_last_event_type(self, ledger, event_type):
        """Simulate a legacy writer, retaining correct hashes and a matching anchor."""
        events = ledger.read()
        events[-1]["type"] = event_type
        events[-1]["sha256"] = digest({key: value for key, value in events[-1].items() if key != "sha256"})
        ledger.path.write_text("".join(canonical_json(event) + "\n" for event in events), encoding="utf-8")
        anchor = json.loads(ledger.anchor_path.read_text(encoding="utf-8"))
        anchor["head"] = events[-1]["sha256"]
        ledger.anchor_path.write_text(canonical_json(anchor) + "\n", encoding="utf-8")
        return ledger.path.read_bytes(), ledger.anchor_path.read_bytes()

    def test_append_chain_detects_modified_history(self):
        ledger = Ledger(self.project, clock=lambda: "2026-01-01T00:00:00Z")
        first = ledger.append("project.init", {"name": "中文"})
        second = ledger.append("claim.add", {"text": "hypothesis"}, actor="model", trust="T2")
        self.assertEqual(first["id"], "EV-000001")
        self.assertEqual(second["prev"], first["sha256"])
        self.assertTrue(ledger.verify()["valid"])
        contents = ledger.path.read_text(encoding="utf-8").replace("hypothesis", "claimed result")
        ledger.path.write_text(contents, encoding="utf-8")
        self.assertFalse(ledger.verify()["valid"])
        with self.assertRaisesRegex(LedgerError, "event hash mismatch"):
            ledger.append("project.init", {})

    def test_incomplete_final_line_and_lock_never_silently_discard(self):
        ledger = Ledger(self.project)
        ledger.append("project.init", {})
        with ledger.path.open("ab") as stream:
            stream.write(b'{"partial":')
        self.assertFalse(ledger.verify()["valid"])
        with self.assertRaisesRegex(LedgerError, "incomplete final line"):
            ledger.append("project.init", {})
        self.assertTrue(ledger.path.read_bytes().endswith(b'{"partial":'))
        (self.project / "ledger.lock").write_text("active", encoding="utf-8")
        with self.assertRaisesRegex(LedgerError, "writer lock already exists"):
            ledger.append("project.init", {})

    def test_unregistered_types_cannot_append_or_change_existing_history(self):
        ledger = Ledger(self.project)
        ledger.append("project.init", {"name": "SYNTHETIC vocabulary fixture"})
        before = ledger.path.read_bytes(), ledger.anchor_path.read_bytes()
        for event_type in ["project.innit", "claim.record", "result.record", "result.invalidate", "reading.retract"]:
            with self.subTest(event_type=event_type):
                with self.assertRaisesRegex(LedgerError, "unregistered event type"):
                    ledger.append(event_type, {})
                self.assertEqual((ledger.path.read_bytes(), ledger.anchor_path.read_bytes()), before)
                self.assertFalse((self.project / "ledger.lock").exists())
        self.assertTrue(ledger.verify()["valid"])

    def test_legacy_unknown_types_fail_even_with_valid_hashes_and_anchor(self):
        ledger = Ledger(self.project)
        ledger.append("project.init", {})
        ledger.append("claim.add", {"text": "SYNTHETIC hypothesis"}, actor="model", trust="T2")
        for event_type in ["project.innit", "result.record", "result.invalidate", "reading.retract"]:
            with self.subTest(event_type=event_type):
                before = self._replace_last_event_type(ledger, event_type)
                report = ledger.verify()
                self.assertFalse(report["valid"])
                self.assertEqual(report["event_count"], 2)
                self.assertEqual(report["anchor"], "matched")
                self.assertEqual(report["errors"], [f"unregistered event type at line 2: {event_type!r}"])
                with self.assertRaisesRegex(LedgerError, "refusing append.*unregistered event type"):
                    ledger.append("project.init", {})
                with self.assertRaisesRegex(LedgerError, "refusing to anchor.*unregistered event type"):
                    ledger.anchor()
                self.assertEqual((ledger.path.read_bytes(), ledger.anchor_path.read_bytes()), before)

    def test_malformed_event_types_are_rejected_without_type_errors(self):
        ledger = Ledger(self.project)
        ledger.append("project.init", {})
        for event_type in [None, "", True, 42, ["project.init"], {"type": "project.init"}]:
            with self.subTest(event_type=event_type):
                before = ledger.path.read_bytes(), ledger.anchor_path.read_bytes()
                with self.assertRaisesRegex(LedgerError, "event type and object data are required"):
                    ledger.append(event_type, {})
                self.assertEqual((ledger.path.read_bytes(), ledger.anchor_path.read_bytes()), before)
                before = self._replace_last_event_type(ledger, event_type)
                report = ledger.verify()
                self.assertFalse(report["valid"])
                self.assertEqual(report["anchor"], "matched")
                self.assertIn("event contract mismatch at line 1", report["errors"])
                self.assertFalse(any("hash mismatch" in error for error in report["errors"]))
                self.assertEqual((ledger.path.read_bytes(), ledger.anchor_path.read_bytes()), before)

    def test_tail_truncation_is_detected_by_the_anchor(self):
        # The chain alone cannot see its own tail removed: every surviving event
        # still points at its predecessor. Negative control for the anchor file.
        ledger = Ledger(self.project)
        for number in range(4):
            ledger.append("project.init", {"name": f"SYNTHETIC fixture {number}"})
        intact = ledger.verify()
        self.assertTrue(intact["valid"])
        self.assertEqual(intact["anchor"], "matched")
        self.assertEqual(intact["event_count"], 4)
        lines = ledger.path.read_bytes().splitlines(keepends=True)
        ledger.path.write_bytes(b"".join(lines[:-1]))
        truncated = ledger.verify()
        self.assertFalse(truncated["valid"], "removing the final event must not verify clean")
        self.assertEqual(truncated["anchor"], "mismatch")
        self.assertEqual(truncated["event_count"], 3)
        self.assertTrue(any("event count mismatch" in error for error in truncated["errors"]))

    def test_a_ledger_without_an_anchor_is_readable_but_reports_absent(self):
        # Projects created before anchoring must keep working; the state is
        # reported so a caller can tell "checked and matched" from "not checked".
        ledger = Ledger(self.project)
        ledger.append("project.init", {"name": "SYNTHETIC unanchored fixture"})
        ledger.anchor_path.unlink()
        report = ledger.verify()
        self.assertTrue(report["valid"])
        self.assertEqual(report["anchor"], "absent")

    def test_anchor_adopts_the_current_state_and_then_matches(self):
        ledger = Ledger(self.project)
        ledger.append("project.init", {"name": "SYNTHETIC adoption fixture"})
        ledger.anchor_path.unlink()
        self.assertEqual(ledger.verify()["anchor"], "absent")
        recorded = ledger.anchor()
        self.assertEqual(recorded["event_count"], 1)
        self.assertEqual(ledger.verify()["anchor"], "matched")
        ledger.append("project.init", {"name": "SYNTHETIC second fixture"})
        self.assertEqual(ledger.verify()["anchor"], "matched")

    def test_append_refuses_a_ledger_whose_anchor_mismatches(self):
        ledger = Ledger(self.project)
        for number in range(3):
            ledger.append("project.init", {"name": f"SYNTHETIC fixture {number}"})
        lines = ledger.path.read_bytes().splitlines(keepends=True)
        ledger.path.write_bytes(b"".join(lines[:-1]))
        with self.assertRaises(LedgerError):
            ledger.append("project.init", {"name": "SYNTHETIC after truncation"})
        self.assertEqual(ledger.verify()["event_count"], 2)

    def test_hash_contract_rejects_floats(self):
        with self.assertRaises(LedgerError):
            canonical_json({"value": 1.0})
        self.assertEqual(canonical_json({"中文": "α", "n": 1}), '{"n":1,"中文":"α"}')

    def test_known_event_roles_cannot_upgrade_model_to_human_or_tool(self):
        ledger = Ledger(self.project)
        for event_type in ["decision.record", "source.identity.confirm", "paper.resolve"]:
            with self.assertRaises(LedgerError):
                ledger.append(event_type, {}, actor="model", trust="T2")
        self.assertEqual(ledger.read(), [])

    def test_public_skill_tree_is_never_project_output(self):
        with self.assertRaises(LedgerError):
            Ledger(RUNTIME / "should-not-exist")

    def test_private_and_credential_queries_do_not_request(self):
        transport = FakeTransport()
        core = ResearchCore(self.project, transport=transport)
        result = core.search("private idea")
        self.assertEqual(result.status, "blocked")
        self.assertEqual(transport.calls, [])
        self.assertEqual(core.ledger.read(), [])
        for text in ["api_key=secret", r"C:\Users\private\idea.md", "C:/Users/private/idea.md", r"\\server\share\private.md", "Bearer abcdefghijklmnop"]:
            with self.assertRaises(PrivacyError):
                check_outbound(text, sensitivity="public")

    def test_offline_records_no_external_search_as_offline(self):
        transport = FakeTransport()
        result = ResearchCore(self.project, transport=transport).search("private idea", offline=True)
        self.assertEqual(result.status, "offline")
        self.assertFalse(result.data["executed"])
        self.assertEqual(result.data["result_paper_ids"], [])
        self.assertEqual(transport.calls, [])

    def test_failed_search_is_preserved_in_denominator(self):
        core = ResearchCore(self.project, transport=FakeTransport(failure="timeout"))
        result = core.search("public query", sensitivity="public")
        self.assertFalse(result.ok)
        self.assertEqual(core.ledger.read()[0]["data"]["status"], "failed")
        self.assertTrue(core.ledger.read()[0]["data"]["executed"])

    def test_crossref_acquisition_receipt_replays_metadata(self):
        body = json.dumps({"message": {"total-results": 1, "items": [{"DOI": "10.1234/A", "title": ["Paper A"], "published": {"date-parts": [[2024]]}}]}}).encode()
        core = ResearchCore(self.project, transport=FakeTransport(body))
        result = core.search("mechanism", provider="crossref", sensitivity="public", family="nearest")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.data["papers"][0]["read_scope"], "not_read")
        self.assertTrue(core.verify_artifacts()["valid"])
        raw = self.project / result.data["receipt"]["artifact"]
        raw.write_bytes(b"changed provider response")
        self.assertFalse(core.verify_artifacts()["valid"])

    def test_malformed_crossref_metadata_stays_unknown(self):
        body = json.dumps({"message": {"total-results": True, "items": [{"DOI": "10.1234/a", "title": ["A"], "published": ["bad"], "author": 1}]}}).encode()
        papers, total = crossref_papers(body)
        self.assertIsNone(papers[0]["year"])
        self.assertIsNone(total)
        with self.assertRaises(ProviderError):
            crossref_papers(b"[]")

    def test_arxiv_query_papers_and_versions(self):
        body = b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>4</o:totalResults><entry><id>http://arxiv.org/abs/2305.13245v3</id><title>A model</title><published>2023-05-01</published><author><name>Ada</name></author></entry></feed>'''
        core = ResearchCore(self.project, transport=FakeTransport(body))
        result = core.search("all:attention", sensitivity="public", limit=1)
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.data["papers"][0]["version"], "v3")
        self.assertTrue(core.verify_artifacts()["valid"])

    def test_local_source_exact_anchor_not_reading_or_approval(self):
        original = Path(self.temp.name) / "private.txt"
        original.write_text("The measured benefit is 12 percent.\nThis is a synthetic fixture.", encoding="utf-8")
        core = ResearchCore(self.project)
        fetched = core.fetch(local_path=original)
        result = core.quote(fetched.data["id"], "measured benefit is 12 percent")
        self.assertTrue(result.ok)
        self.assertEqual(result.data["read_scope"], "not_read")
        self.assertEqual(fetched.data["receipt"]["transport_mode"], "local")
        self.assertTrue(core.verify_artifacts()["valid"])
        self.assertNotIn(str(original), core.ledger.path.read_text(encoding="utf-8"))
        self.assertFalse(core.quote(fetched.data["id"], "measured benefit is 99 percent").ok)
        self.assertEqual(len(core.ledger.read()), 2)

    def test_quote_preserves_case_math_and_requires_unambiguous_excerpt(self):
        self.assertEqual(normalize_text("A\n ≤ B"), "A ≤ B")
        with self.assertRaises(AnchorError):
            quote_text("s", "A versus a is distinct", "a versus a")
        with self.assertRaises(AnchorError):
            quote_text("s", "repeat phrase and repeat phrase", "repeat phrase")
        with self.assertRaises(AnchorError):
            quote_text("s", "value is A", "A")

    def test_pdf_byte_acquisition_never_creates_text_anchor(self):
        pdf = Path(self.temp.name) / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.7 synthetic bytes")
        core = ResearchCore(self.project)
        result = core.fetch(local_path=pdf)
        self.assertEqual(result.status, "needs_host_extraction")
        self.assertFalse(core.quote(result.data["id"], "synthetic bytes").ok)

    def test_local_publication_identity_requires_explicit_human_check(self):
        body = json.dumps({"message": {"DOI": "10.1234/a", "title": ["Paper A"], "published": {"date-parts": [[2024]]}}}).encode()
        core = ResearchCore(self.project, transport=FakeTransport(body))
        paper = core.resolve("doi:10.1234/a")
        self.assertTrue(paper.ok)
        original = Path(self.temp.name) / "paper.txt"
        original.write_text("This source is a synthetic local copy.", encoding="utf-8")
        source = core.fetch(local_path=original, paper_id=paper.data["id"])
        self.assertEqual(source.data["source_identity"]["status"], "unconfirmed")
        self.assertFalse(core.confirm_source_identity(source.data["id"], paper.data["id"], "published", "Manually checked metadata").ok)
        confirmed = core.confirm_source_identity(source.data["id"], paper.data["id"], "published", "Manually checked metadata", human=True)
        self.assertTrue(confirmed.ok)
        self.assertEqual(core.ledger.read()[-1]["trust"], "T1")
        self.assertTrue(core.verify_artifacts()["valid"])

    def test_html_skips_executable_content_marks_lossy(self):
        html = Path(self.temp.name) / "paper.html"
        html.write_text("<h2>Method</h2><p>The method shares one key tensor.</p><script>private prompt</script><math>x</math>", encoding="utf-8")
        core = ResearchCore(self.project)
        result = core.fetch(local_path=html)
        source = core.inspect_source(result.data["id"])
        self.assertNotIn("private prompt", source.data["document"]["text"])
        quote = core.quote(result.data["id"], "shares one key tensor")
        self.assertTrue(quote.data["lossy"])
        self.assertTrue(core.verify_artifacts()["valid"])

    def test_network_guard_blocks_private_ips_urls_and_credential_urls(self):
        for address in ["127.0.0.1", "10.0.0.1", "100.64.0.1", "::1", "2001:db8::1"]:
            self.assertFalse(public_address(address))
        self.assertTrue(public_address("1.1.1.1"))
        for url in ["http://example.org", "https://127.0.0.1", "https://user:pass@example.org", "https://example.org/?api_key=secret"]:
            with self.assertRaises(TransportError):
                checked_url(url)

    def test_transport_checks_dns_and_fixed_proxy_paths_before_request(self):
        transport = Transport()
        with mock.patch("research_mentor.transport.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(TransportError):
                transport.get("https://example.org/paper", allowed_hosts={"example.org"})
        proxy = Transport(trusted_provider_transport=True)
        with self.assertRaises(TransportError):
            proxy.get("https://example.org/paper", allowed_hosts={"example.org"}, trusted_provider=True)


class PythonJudgmentKillTests(unittest.TestCase):
    """Synthetic user workflows that separate scientific claims from labels/context."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-kill-regression-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def workflow(self):
        item = {"DOI": "10.5555/synthetic-kill-regression", "title": ["SYNTHETIC method fixture"],
                "published": {"date-parts": [[2026]]}}
        class ProtocolTransport:
            def get(self, url, **kwargs):
                message = item if "/works/" in url else {"total-results": 1, "items": [item]}
                return Response(url, 200, {"content-type": "application/json"},
                                json.dumps({"message": message}).encode("utf-8"), "synthetic_protocol")
        core = ResearchCore(self.project, transport=ProtocolTransport())
        searches = [core.search("SYNTHETIC " + family, provider="crossref", sensitivity="public", family=family)
                    for family in ("problem", "reverse")]
        resolved = core.resolve(item["DOI"])
        self.assertTrue(resolved.ok, resolved.errors)
        paper_id = resolved.data["id"]
        path = self.project / "synthetic-method.txt"
        excerpt = "the candidate mechanism and assumptions match the reference mechanism exactly"
        path.write_text("SYNTHETIC method: " + excerpt + ". No measured results are asserted.", encoding="utf-8")
        source = core.fetch(local_path=path, paper_id=paper_id)
        self.assertTrue(source.ok, source.errors)
        self.assertTrue(core.confirm_source_identity(source.data["id"], paper_id, "unknown",
                        "SYNTHETIC human checked the local fixture identity", human=True).ok)
        quote = core.quote(source.data["id"], excerpt)
        self.assertTrue(quote.ok, quote.errors)
        data = {"id": "C-SYNTHETIC", "title": "SYNTHETIC candidate", "question": "Can the synthetic hypothesis be tested?",
                "research_type": "empirical", "hypothesis": "SYNTHETIC untested core hypothesis",
                "contribution": "SYNTHETIC structural workflow", "search_ids": [r.data["id"] for r in searches],
                "nearest_work": [{"paper_id": paper_id, "evidence_ids": [quote.data["id"]], "decisive": True,
                                  "delta": "SYNTHETIC comparison needs a claim-level equivalence argument"}],
                "novelty": {"status": "incremental", "reason": "SYNTHETIC scoped baseline"},
                "feasibility": {"status": "ready", "dependencies": []},
                "validation": {"status": "specified", **{key: "SYNTHETIC bounded check" for key in
                               ("prediction", "falsifier", "design", "metric", "resource_estimate", "stop_rule")}}}
        judgment = Judgment(core.ledger)
        judgment.upsert_candidate(data)
        claim = judgment.add_claim("SYNTHETIC pilot checks the current hypothesis", data["id"])
        judgment.link_claim(claim["id"], quote.data["id"], target="validation")
        judgment.confirm_read(quote.data["id"], "section", "SYNTHETIC method section actually inspected")
        self.assertEqual(judgment.assess(data["id"], reason="SYNTHETIC baseline", record=False)["machine_recommendation"], "GO")
        return core, judgment, data, quote.data["id"]

    def duplicate_version(self, judgment, data):
        data["novelty"] = {"status": "duplicate", "reason": "SYNTHETIC label; still requires current equivalence evidence"}
        judgment.upsert_candidate(data)

    def assess_duplicate(self, judgment):
        return judgment.assess("C-SYNTHETIC", "KILL", reason="SYNTHETIC duplicate review",
                               kill_type="duplicate", scope="scientific_framing", record=False)

    def test_duplicate_label_cannot_reuse_prior_version_claims(self):
        _, judgment, data, _ = self.workflow()
        self.duplicate_version(judgment, data)
        result = self.assess_duplicate(judgment)
        self.assertEqual(result["coverage"]["claims"], 0)
        self.assertEqual(result["coverage"]["links"], 0)
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(any("current load-bearing equivalence/duplicate claim" in gap for gap in result["missing"]))

    def test_duplicate_needs_explicit_equivalence_claim_kind(self):
        _, judgment, data, eid = self.workflow()
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC generic hypothesis; no equivalence assertion", data["id"])
        judgment.link_claim(claim["id"], eid, target="nearest_work")
        self.assertEqual(self.assess_duplicate(judgment)["machine_recommendation"], "HOLD")

    def test_explicit_current_equivalence_with_deep_support_can_recommend_duplicate_kill(self):
        _, judgment, data, eid = self.workflow()
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC candidate mechanism and assumptions are equivalent to the decisive reference",
                                   data["id"], kind="mechanism_equivalence")
        judgment.link_claim(claim["id"], eid, target="nearest_work")
        result = self.assess_duplicate(judgment)
        self.assertEqual(result["machine_recommendation"], "KILL")
        self.assertEqual(result["approval_status"], "pending_human")

    def test_non_load_bearing_equivalence_is_background_not_duplicate_basis(self):
        _, judgment, data, eid = self.workflow()
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC contextual equivalence about an unrelated mechanism", data["id"],
                                   kind="duplicate", load_bearing=False)
        judgment.link_claim(claim["id"], eid, target="nearest_work")
        self.assertEqual(self.assess_duplicate(judgment)["machine_recommendation"], "HOLD")

    def test_context_relation_cannot_support_duplicate_claim(self):
        _, judgment, data, eid = self.workflow()
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC core duplication assertion", data["id"], kind="duplicate")
        judgment.link_claim(claim["id"], eid, relation="context", target="nearest_work")
        self.assertEqual(self.assess_duplicate(judgment)["machine_recommendation"], "HOLD")

    def test_duplicate_claim_support_must_target_nearest_work(self):
        _, judgment, data, eid = self.workflow()
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC core duplication assertion", data["id"], kind="duplicate")
        judgment.link_claim(claim["id"], eid, target="validation")
        self.assertEqual(self.assess_duplicate(judgment)["machine_recommendation"], "HOLD")

    def test_duplicate_support_must_use_the_decisive_comparison_anchor(self):
        core, judgment, data, _ = self.workflow()
        source = next(e["data"]["id"] for e in core.ledger.read() if e["type"] == "source.fetch")
        unrelated = core.quote(source, "No measured results are asserted.")
        self.assertTrue(unrelated.ok, unrelated.errors)
        judgment.confirm_read(unrelated.data["id"], "section", "SYNTHETIC unrelated sentence actually inspected")
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC equivalence assertion with an unrelated sentence", data["id"], kind="duplicate")
        judgment.link_claim(claim["id"], unrelated.data["id"], target="nearest_work")
        self.assertEqual(self.assess_duplicate(judgment)["machine_recommendation"], "HOLD")

    def test_duplicate_equivalence_with_only_current_abstract_reading_stays_hold(self):
        _, judgment, data, eid = self.workflow()
        self.duplicate_version(judgment, data)
        claim = judgment.add_claim("SYNTHETIC core duplication assertion", data["id"], kind="duplicate")
        judgment.link_claim(claim["id"], eid, target="nearest_work")
        judgment.confirm_read(eid, "abstract", "SYNTHETIC reader corrected the reading scope to abstract only")
        result = self.assess_duplicate(judgment)
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(any("lacks explicit relevant-section reading" in gap for gap in result["missing"]))

    def test_background_contradiction_cannot_refute_core_or_block_go(self):
        _, judgment, data, eid = self.workflow()
        context = judgment.add_claim("SYNTHETIC observation about an unrelated earlier approach", data["id"], load_bearing=False)
        judgment.link_claim(context["id"], eid, relation="contradicts", target="hypothesis")
        result = judgment.assess(data["id"], "KILL", reason="SYNTHETIC contextual contradiction",
                                 kill_type="scientific_refutation", record=False)
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertNotIn("Decision-relevant evidence contradicts a core condition", result["missing"])
        self.assertEqual(judgment.assess(data["id"], reason="SYNTHETIC unchanged core", record=False)["machine_recommendation"], "GO")

    def test_current_load_bearing_core_contradiction_can_recommend_refutation_kill(self):
        _, judgment, data, eid = self.workflow()
        core_claim = judgment.add_claim("SYNTHETIC current core condition falsified in the fixture", data["id"])
        judgment.link_claim(core_claim["id"], eid, relation="contradicts", target="hypothesis")
        result = judgment.assess(data["id"], "KILL", reason="SYNTHETIC explicit current core refutation",
                                 kill_type="scientific_refutation", record=False)
        self.assertEqual(result["machine_recommendation"], "KILL")
        self.assertEqual(result["approval_status"], "pending_human")

if __name__ == "__main__":
    unittest.main()
