"""Frozen SYNTHETIC parity cases for native tools and the actual Node oracle.

No network or model call is made. Existing public examples are read unchanged.
The tests establish contract compatibility, not research quality or recall.
RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE=1 makes a missing oracle a failure.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "ai-research-mentor"
sys.path.insert(0, str(SKILL / "runtime"))
from research_mentor import audit, outputs, sources

NODE = shutil.which("node")
STAMP = "2026-10-10T00:00:00.000Z"
NODE_BRIDGE = r"""
import fs from 'node:fs';
const audit = await import(AUDIT_URI);
const outputs = await import(OUTPUTS_URI);
const sources = await import(SOURCES_URI);
const OriginalDate = Date;
globalThis.Date = class extends OriginalDate {
  constructor(...args) { super(...(args.length ? args : [STAMP])); }
  static now() { return new OriginalDate(STAMP).getTime(); }
};
const requests = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = [];
for (const request of requests) {
  const value = request.value;
  try {
    let answer;
    switch (request.action) {
      case 'validate': answer = audit.validateDossier(value); break;
      case 'fingerprint': answer = audit.fingerprintIdea(value, request.id); break;
      case 'weights': answer = audit.rankingConfigHash(value); break;
      case 'rank': answer = audit.rankDossier(value); break;
      case 'migrate': answer = audit.migrateDossier(value); break;
      case 'canonical': answer = audit.canonicalStringify(value); break;
      case 'notes': answer = outputs.validateNotes(value); break;
      case 'card': answer = outputs.renderCard(value); break;
      case 'draft': answer = outputs.draftDossier(value, {name:request.name}); break;
      case 'bibtex': answer = outputs.exportBibtex(value); break;
      case 'html': answer = sources.extractHtml(value, request.url); break;
      case 'doi': answer = sources.normalizeDoi(value); break;
      case 'arxiv': answer = sources.normalizeArxiv(value); break;
      case 'address': answer = sources.isPublicAddress(value); break;
      case 'receipt': {
        const report = await audit.verifyIndependentReceipts(value, {root:request.root});
        answer = {report, ranking:audit.rankDossier(value, {receiptVerification:report}),
          cloned:audit.rankDossier(value, {receiptVerification:structuredClone(report)}),
          forged:audit.rankDossier(value, {receiptVerification:{verified:report.verified}})};
        if (request.after) {
          value.reviews.at(-1).reason = request.after;
          answer.after = audit.rankDossier(value, {receiptVerification:report});
        }
        break;
      }
      case 'source': {
        let index = 0;
        const dependencies = {lookup:async()=>request.addresses ?? [{address:'1.1.1.1', family:4}],
          pause:async()=>{}, fetch:async()=>{
            const response = request.responses[index++];
            if (!response) throw new Error('SYNTHETIC response budget exhausted');
            const bytes = response.byte_body ? new Uint8Array(response.byte_body) : response.body ?? '';
            return new Response(bytes, {status:response.status ?? 200, headers:response.headers ?? {}});
          }};
        answer = await sources[request.function](value, dependencies);
        break;
      }
      default: throw new Error('Unknown oracle action');
    }
    result.push({value:answer});
  } catch (error) { result.push({error:error.message}); }
}
console.log(JSON.stringify(result));
"""
for marker, module in (("AUDIT_URI", "research_audit.mjs"), ("OUTPUTS_URI", "research_outputs.mjs"),
                       ("SOURCES_URI", "research_sources.mjs")):
    NODE_BRIDGE = NODE_BRIDGE.replace(marker, json.dumps((SKILL / "scripts" / module).as_uri()))
NODE_BRIDGE = NODE_BRIDGE.replace("STAMP", json.dumps(STAMP))


def example(name="empirical"):
    return json.loads((REPO / "examples" / f"{name}-example" / "dossier.json").read_text(encoding="utf-8"))


def python_answer(request):
    value = deepcopy(request.get("value"))
    action = request["action"]
    try:
        if action == "validate":
            result = audit.validate_dossier(value)
        elif action == "fingerprint":
            result = audit.fingerprint_idea(value, request["id"])
        elif action == "weights":
            result = audit.ranking_config_hash(value)
        elif action == "rank":
            result = audit.rank_dossier(value)
        elif action == "migrate":
            result = audit.migrate_dossier(value)
        elif action == "canonical":
            result = audit.canonical_stringify(value)
        elif action == "notes":
            result = outputs.validate_notes(value)
        elif action == "card":
            result = outputs.render_card(value)
        elif action == "draft":
            result = outputs.draft_dossier(value, name=request["name"])
        elif action == "bibtex":
            result = outputs.export_bibtex(value)
        elif action == "html":
            result = sources.extract_html(value, request["url"])
        elif action == "doi":
            result = sources.normalize_doi(value)
        elif action == "arxiv":
            result = sources.normalize_arxiv(value)
        elif action == "address":
            result = sources.is_public_address(value)
        elif action == "receipt":
            report = audit.verify_independent_receipts(value, root=request["root"])
            result = {"report": report, "ranking": audit.rank_dossier(value, receipt_verification=report),
                      "cloned": audit.rank_dossier(value, receipt_verification=deepcopy(report)),
                      "forged": audit.rank_dossier(value, receipt_verification={"verified": report["verified"]})}
            if request.get("after"):
                value["reviews"][-1]["reason"] = request["after"]
                result["after"] = audit.rank_dossier(value, receipt_verification=report)
        elif action == "source":
            raw_responses = deepcopy(request["responses"])
            for response in raw_responses:
                response.setdefault("status", 200)
                if "byte_body" in response:
                    response["body"] = bytes(response.pop("byte_body"))
            responses = iter(raw_responses)
            dependencies = {"now": lambda: STAMP, "pause": lambda _: None,
                            "lookup": lambda *_: request.get("addresses", [{"address": "1.1.1.1", "family": 4}]),
                            "fetch": lambda *_: next(responses)}
            result = {"searchCrossref": sources.search_crossref, "verifyIdentifier": sources.verify_identifier,
                      "acquireFulltext": sources.acquire_fulltext}[request["function"]](value, dependencies)
        else:
            raise AssertionError("Unknown native action")
        return {"value": result}
    except (ValueError, TypeError, OSError, KeyError, OverflowError) as error:
        return {"error": str(error)}


class ToolchainNodeConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            if os.environ.get("RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE") == "1":
                raise AssertionError("Node is required by RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE=1")
            raise unittest.SkipTest("Actual Node oracle unavailable; no conformance result claimed")

    def assert_cases(self, requests):
        # Native runs receive separate copies. Neither side edits public fixtures.
        before = deepcopy(requests)
        native = [python_answer(request) for request in requests]
        result = subprocess.run([NODE, "--input-type=module", "-e", NODE_BRIDGE],
                                input=json.dumps(requests, ensure_ascii=True), capture_output=True,
                                text=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        oracle = json.loads(result.stdout)
        self.assertEqual(len(oracle), len(native))
        for index, (expected, actual) in enumerate(zip(oracle, native)):
            with self.subTest(index=index, action=requests[index]["action"], label=requests[index].get("label")):
                self.assertEqual(actual, expected)
        self.assertEqual(requests, before)

    def test_immutable_examples_validation_fingerprints_rankings_and_migrations(self):
        requests = []
        for name in ("empirical", "theoretical", "measurement"):
            dossier = example(name)
            for action in ("validate", "fingerprint", "weights", "rank", "migrate"):
                requests.append({"action": action, "value": dossier, "id": dossier["ideas"][0]["id"], "label": name})
        self.assert_cases(requests)

    def test_binary64_serialization_utf16_pairs_and_numeric_property_order(self):
        randomizer = random.Random(20261010)
        values = [0.0, -0.0, 1e-7, 1e-6, 1e20, 1e21, 9007199254740993,
                  1000000000000000128, 5e-324, 2.2250738585072014e-308]
        for _ in range(256):
            number = struct.unpack("!d", randomizer.getrandbits(64).to_bytes(8, "big"))[0]
            if math.isfinite(number):
                values.append(number)
        self.assert_cases([{"action": "canonical", "value": values, "label": "seeded-binary64"},
                           {"action": "canonical", "value": {"2": "two", "10": "ten", "01": "leading", "4294967295": "nonindex",
                                                               "\ue000": "bmp", "\U0001f9ea": "supplementary"}},
                           {"action": "canonical", "value": [chr(0xd83e) + chr(0xddea), chr(0xd800), chr(0xdc00), "\ufeff\u0085"]}])

    def test_scientific_input_changes_weight_preferences_and_typed_kill_gates(self):
        requests = []

        def case(label, mutate, refresh=False):
            dossier = example()
            mutate(dossier)
            if refresh:
                for review in dossier["reviews"]:
                    review["review_basis_hash"] = audit.fingerprint_idea(dossier, review["idea_id"])
            for action in ("validate", "fingerprint", "weights", "rank"):
                requests.append({"action": action, "value": dossier, "id": "I1", "label": label})

        case("changed-question", lambda d: d["ideas"][0].update(question="SYNTHETIC changed mechanism"))
        case("weights", lambda d: d["config"].update(ranking_weights={"scientific_value": 80, "differentiation": 10, "testability": 10}))
        case("context-reading", lambda d: d["evidence"][0].update(read_scope="abstract"), True)
        case("unknown-score", lambda d: d["reviews"][0]["scores"].update(testability=None))
        case("missing-dependency", lambda d: d["ideas"][0]["feasibility"]["dependencies"][0].update(status="unknown"), True)
        case("new-novelty", lambda d: d["ideas"][0]["novelty"].update(status="unclear"), True)
        case("duplicate-kill", lambda d: (d["ideas"][0]["novelty"].update(status="duplicate"),
                                           d["reviews"][0].update(decision="KILL"),
                                           d["reviews"][0]["decision_basis"].update(type="duplicate")), True)
        case("unjustified-refutation", lambda d: (d["reviews"][0].update(decision="KILL"),
                                                 d["reviews"][0]["decision_basis"].update(type="scientific_refutation")), True)
        case("deep-refutation", lambda d: (d["ideas"][0]["evidence_links"][0].update(target="hypothesis", relation="contradicts"),
                                          d["reviews"][0].update(decision="KILL"),
                                          d["reviews"][0]["decision_basis"].update(type="scientific_refutation")), True)
        self.assert_cases(requests)

    def test_legacy_and_mixed_contract_migrations_never_restore_hidden_approvals(self):
        requests = []
        for schema in (1, 2):
            dossier = example()
            dossier["schema_version"] = schema
            if schema == 1:
                dossier.pop("decision_contract_version")
                dossier.pop("screening")
                for idea in dossier["ideas"]:
                    idea.pop("evidence_links")
                for review in dossier["reviews"]:
                    for key in ("review_basis_hash", "decision_scope", "recommended_stage", "decision_basis", "decision_contract_version"):
                        review.pop(key)
                    review["basis_hash"] = "0" * 64
            else:
                dossier["decision_contract_version"] = 2
                dossier["reviews"][0]["decision_contract_version"] = 2
            for action in ("validate", "fingerprint", "rank", "migrate"):
                requests.append({"action": action, "value": dossier, "id": "I1", "label": f"schema-{schema}"})
        for later in (True, False):
            dossier = example()
            newer = deepcopy(dossier["reviews"][0])
            newer.update(id="R-LEGACY", decision="HOLD", decision_contract_version=1,
                         reviewed_at="2026-10-05T10:00:00Z" if later else "2026-10-05T07:00:00Z")
            dossier["reviews"].append(newer)
            for action in ("rank", "migrate"):
                requests.append({"action": action, "value": dossier, "label": f"legacy-later-{later}"})
        dossier = example()
        dossier["decision_contract_version"] = 4
        dossier["reviews"][0]["decision_contract_version"] = 4
        requests.extend({"action": action, "value": dossier, "label": "future-contract"} for action in ("rank", "migrate"))
        self.assert_cases(requests)

    def test_invalid_references_types_dates_weights_and_untrusted_declarations(self):
        requests = []
        mutations = [lambda d: d.update(schema_version=True),
                     lambda d: d["ideas"][0].update(version=True),
                     lambda d: d["evidence"][0].update(paper_id="DOES-NOT-EXIST"),
                     lambda d: d["reviews"][0]["scores"].update(testability=5),
                     lambda d: d["reviews"][0].update(reviewed_at="2026-02-30T00:00:00Z"),
                     lambda d: d["config"].update(ranking_weights={"scientific_value": 0, "differentiation": 0, "testability": 0}),
                     lambda d: d["reviews"][0].update(kind="independent", author_context="same", evaluator_context="same", artifact="peer.json"),
                     lambda d: d["searches"][0].update(result_paper_ids=["UNRESOLVED"])]
        for index, mutate in enumerate(mutations):
            dossier = example()
            mutate(dossier)
            requests.append({"action": "validate", "value": dossier, "label": f"invalid-{index}"})
        self.assert_cases(requests)

    def test_receipt_full_stage_current_forged_cloned_stale_and_complete_binding(self):
        with tempfile.TemporaryDirectory(prefix="mentor-native-receipts-") as temporary:
            requests = []
            for label in ("full", "pilot", "bad-stage", "bad-context", "bad-score", "stale-hash", "too-large"):
                dossier = example()
                peer = deepcopy(dossier["reviews"][0])
                peer.update(id="PEER", kind="independent", author_context="SYNTHETIC author",
                            evaluator_context="SYNTHETIC independent", artifact=f"{label}.json",
                            recommended_stage="pilot" if label == "pilot" else "full_validation",
                            reviewed_at="2026-10-05T09:00:00Z")
                latest = deepcopy(dossier["reviews"][0])
                latest.update(id="SELF", recommended_stage="full_validation", reviewed_at="2026-10-05T10:00:00Z")
                dossier["reviews"] = [peer, latest]
                receipt = audit.create_review_receipt(peer)
                if label == "bad-stage":
                    receipt["review"]["recommended_stage"] = "pilot"
                elif label == "bad-context":
                    receipt["review"]["evaluator_context"] = "SYNTHETIC replaced context"
                elif label == "bad-score":
                    receipt["review"]["scores"]["testability"] = 0
                data = json.dumps(receipt, ensure_ascii=False, indent=2).encode("utf-8")
                if label == "too-large":
                    data += b" " * (1024 * 1024)
                (Path(temporary) / peer["artifact"]).write_bytes(data)
                peer["artifact_sha256"] = "0" * 64 if label == "stale-hash" else hashlib.sha256(data).hexdigest()
                requests.append({"action": "receipt", "value": dossier, "root": temporary,
                                 "after": "SYNTHETIC review changed after verification", "label": label})
            self.assert_cases(requests)

    def test_cards_drafts_and_bibliography_identity_bridges_preserve_unknowns(self):
        requests = []
        notes = json.loads((REPO / "examples" / "lightweight-example" / "notes.json").read_text(encoding="utf-8"))
        for value in (notes, {"question": "SYNTHETIC minimal"}, {"question": "SYNTHETIC", "decision": "GO"},
                      {"question": "SYNTHETIC", "known": []}, {"question": "", "type": "magic", "alternatives": [None]}):
            requests.extend({"action": action, "value": value, "name": "synthetic-native"} for action in ("notes", "card", "draft"))
        paper = {"id": "DOI", "title": "SYNTHETIC source } \\input{data} & 50%", "year": None,
                 "identifiers": {"doi": "10.1234/SYNTHETIC"}, "authors": []}
        arxiv = {**paper, "id": "ARXIV", "identifiers": {"arxiv": "2401.00001v1"}}
        bridge = {**paper, "id": "BRIDGE", "year": 2024, "authors": [{"family": "Synthetic", "given": "Author"}],
                  "identifiers": {"doi": "https://doi.org/10.1234/synthetic", "arxiv": "2401.00001v1"}}
        for records in ([paper], [dict(paper, year=2024.0)], [dict(paper, year=True)],
                        [paper, arxiv, bridge], [bridge, arxiv, paper],
                        [paper, dict(arxiv, title="SYNTHETIC conflicting title"), bridge],
                        [bridge, dict(bridge, id="OTHER", identifiers={"doi": "10.1234/other", "arxiv": "2401.00001v1"})],
                        [paper, dict(paper, id="BAD", citation_key="bad}\\input{x}")]):
            requests.append({"action": "bibtex", "value": records})
        self.assert_cases(requests)

    def test_ecmascript_whitespace_is_preserved_in_source_text_and_notes(self):
        requests = []
        for value in ({"question": "\u0085"}, {"question": "\ufeff"},
                      {"question": "\ufeff SYNTHETIC \u0085", "known": "\u0085observed\ufefftext\u001c"}):
            requests.extend({"action": action, "value": value, "name": "synthetic-whitespace"}
                            for action in ("notes", "card", "draft"))
        requests.append({"action": "html", "value": "<p>\u0085observed\ufefftext\u001c</p>",
                         "url": "https://example.org/synthetic"})
        requests.append({"action": "bibtex", "value": [{"id": "P", "title": "\u0085observed\ufefftext\u001c", "year": None}]})
        self.assert_cases(requests)

    def test_identifiers_public_address_policy_and_html_utf16_offsets(self):
        requests = []
        for value in ("doi:10.1234/ABC", "https://doi.org/10.1234/a?b#c", "10.12/bad", "10.1234/white space"):
            requests.append({"action": "doi", "value": value})
        for value in ("2401.00001v2", "https://arxiv.org/pdf/2401.00001v1.pdf", "cs.AI/9901001", "2401.00001v0"):
            requests.append({"action": "arxiv", "value": value})
        for value in ("1.1.1.1", "8.8.8.8", "127.0.0.1", "10.0.0.1", "100.64.0.1", "192.0.2.1", "198.18.0.1",
                      "2001:4860:4860::8888", "::1", "::ffff:127.0.0.1", "2001:db8::1", "2002::1", "not-an-address"):
            requests.append({"action": "address", "value": value})
        for value in ('🧪<section id="sec"><h2>Heading</h2><p>A &gt; B; x².</p></section>',
                      '<div id="s"><p>outer<span>inside</span><p>inner</p>after</p></div>',
                      '<p id="eq">x<sup>2</sup> &ne; y</p><script>invented instruction</script>',
                      '<table><tr><td>甲</td><td>🧪 &amp; text</td></tr></table>',
                      '<template><p>ignored</p></template><p>unclosed', '<p>x < y &unknown;</p>'):
            requests.append({"action": "html", "value": value, "url": "https://example.org/synthetic"})
        self.assert_cases(requests)

    def test_source_offline_metadata_partial_and_protocol_failure_outputs(self):
        requests = []

        def source(function, options, responses, label, addresses=None):
            request = {"action": "source", "function": function, "value": options,
                       "responses": responses, "label": label}
            if addresses is not None:
                request["addresses"] = addresses
            requests.append(request)

        for function, options in (("searchCrossref", {"query": "SYNTHETIC public", "offline": True}),
                                  ("verifyIdentifier", {"doi": "10.1234/synthetic", "offline": True}),
                                  ("acquireFulltext", {"arxiv": "2401.00001v1", "offline": True})):
            source(function, options, [], "offline")
        record = {"DOI": "10.1234/synthetic", "title": ["SYNTHETIC A > B: x²"],
                  "published": {"date-parts": [[2024, 3]]}, "type": "journal-article",
                  "author": [{"given": "Synthetic", "family": "Author"}]}
        def response(value, status=200):
            return {"status": status, "headers": {"content-type": "application/json"},
                    "body": json.dumps(value, ensure_ascii=False, separators=(",", ":"))}
        for total, items in ((1, [record]), (100, [record]), (0, [])):
            source("searchCrossref", {"query": "SYNTHETIC public", "rows": 1, "searchId": "S-SYNTHETIC", "sensitivity": "public"},
                   [response({"status": "ok", "message": {"items": items, "total-results": total, "next-cursor": "next"}})], f"search-{total}")
        source("verifyIdentifier", {"doi": "10.1234/synthetic", "expectTitle": "synthetic A > B: x²", "expectYear": 2024},
               [response({"status": "ok", "message": record})], "identity-match")
        source("verifyIdentifier", {"doi": "10.1234/synthetic"},
               [response({"status": "ok", "message": dict(record, DOI="10.1234/other")})], "wrong-identity")
        source("verifyIdentifier", {"doi": "10.1234/synthetic"}, [{"status": 404, "body": ""}], "identity-404")
        source("verifyIdentifier", {"doi": "10.1234/synthetic"}, [response({})], "private-dns", [{"address": "127.0.0.1", "family": 4}])
        source("searchCrossref", {"query": "SYNTHETIC public", "rows": 1, "sensitivity": "public", "maxBytes": 10},
               [response({"status": "ok", "message": {"items": [record]}})], "byte-budget")
        self.assert_cases(requests)

    def test_acquired_fulltext_bytes_never_manufacture_reading_or_pdf_extraction(self):
        requests = []
        for label, options, response in (
            ("html", {"arxiv": "2401.00001v1"}, {"headers": {"content-type": "text/html;charset=utf-8"}, "body": '<p id="s">🧪SYNTHETIC x &gt; y</p>'}),
            ("pdf", {"arxiv": "2401.00001v1", "format": "pdf"}, {"headers": {"content-type": "application/pdf"}, "body": "%PDF-1.7\nSYNTHETIC fake bytes; no actual PDF"}),
            ("unversioned", {"arxiv": "2401.00001"}, {"headers": {"content-type": "text/html"}, "body": "<p>SYNTHETIC unversioned</p>"}),
            ("404", {"arxiv": "2401.00001v1"}, {"status": 404, "body": ""}),
            ("nonbody", {"arxiv": "2401.00001v1"}, {"headers": {"content-type": "text/html"}, "body": "<script>SYNTHETIC instruction data</script>"}),
            ("invalid-signature", {"arxiv": "2401.00001v1", "format": "pdf"}, {"headers": {"content-type": "application/pdf"}, "body": "SYNTHETIC not a PDF"}),
            ("unsupported-charset", {"arxiv": "2401.00001v1"}, {"headers": {"content-type": "text/html;charset=utf-7"}, "body": "<p>SYNTHETIC</p>"}),
            ("invalid-utf8", {"arxiv": "2401.00001v1"}, {"headers": {"content-type": "text/html;charset=utf-8"}, "byte_body": [60, 112, 62, 255, 60, 47, 112, 62]}),
            ("bom", {"arxiv": "2401.00001v1"}, {"headers": {"content-type": "text/html;charset=utf-8"}, "body": "\ufeff<p>SYNTHETIC</p>"}),
        ):
            requests.append({"action": "source", "function": "acquireFulltext", "value": options,
                             "responses": [response], "label": label})
        self.assert_cases(requests)
