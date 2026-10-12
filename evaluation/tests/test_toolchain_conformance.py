"""Full-output regression against frozen historical SYNTHETIC responses.

The reference responses were captured from the previous implementation before
its removal; the implementation under test did not generate expected values.
No network, model, historical runtime, or external executable is needed.
See evaluation/fixtures/README.md for provenance and limits.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "ai-research-mentor"
sys.path.insert(0, str(SKILL / "runtime"))
from research_mentor import audit, outputs, sources

FIXTURES = REPO / "evaluation" / "fixtures"
FIXTURE_SHA256 = "f0c5011e22be25775c56c863adcd80c12196865508a9d6f528affc85879a6aba"
STAMP = "2026-10-10T00:00:00.000Z"

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

class ToolchainFrozenRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (FIXTURES / "toolchain-regression.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
            raise AssertionError("Frozen historical responses changed; do not regenerate expectations from the tested runtime")
        fixture = json.loads(raw)
        if not fixture["synthetic"] or fixture["fixture_version"] != 1:
            raise AssertionError("Unknown regression fixture contract")
        cls.groups = {group["test"]: group for group in fixture["groups"]}
        if len(cls.groups) != 11 or sum(len(group["requests"]) for group in cls.groups.values()) != 164:
            raise AssertionError("Historical coverage was removed")

    def assert_fixture(self, name):
        group = self.groups[name]
        requests = deepcopy(group["requests"])
        frozen = deepcopy(group)
        with tempfile.TemporaryDirectory(prefix="mentor-frozen-receipts-") as temporary:
            for filename, artifact in group.get("receipt_files", {}).items():
                self.assertEqual(Path(filename).name, filename)
                data = base64.b64decode(artifact["base64"], validate=True) + b" " * artifact["trailing_spaces"]
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["sha256"])
                (Path(temporary) / filename).write_bytes(data)
            self.assertEqual(len(requests), len(group["expected"]))
            for index, (request, expected) in enumerate(zip(requests, group["expected"])):
                if request["action"] == "receipt":
                    self.assertEqual(request["root"], "$RECEIPT_ROOT")
                    request["root"] = temporary
                with self.subTest(index=index, action=request["action"], label=request.get("label")):
                    self.assertEqual(python_answer(request), expected)
        self.assertEqual(group, frozen)

    def test_acquired_fulltext_bytes_never_manufacture_reading_or_pdf_extraction(self):
        self.assert_fixture("test_acquired_fulltext_bytes_never_manufacture_reading_or_pdf_extraction")

    def test_binary64_serialization_utf16_pairs_and_numeric_property_order(self):
        self.assert_fixture("test_binary64_serialization_utf16_pairs_and_numeric_property_order")

    def test_cards_drafts_and_bibliography_identity_bridges_preserve_unknowns(self):
        self.assert_fixture("test_cards_drafts_and_bibliography_identity_bridges_preserve_unknowns")

    def test_ecmascript_whitespace_is_preserved_in_source_text_and_notes(self):
        self.assert_fixture("test_ecmascript_whitespace_is_preserved_in_source_text_and_notes")

    def test_identifiers_public_address_policy_and_html_utf16_offsets(self):
        self.assert_fixture("test_identifiers_public_address_policy_and_html_utf16_offsets")

    def test_immutable_examples_validation_fingerprints_rankings_and_migrations(self):
        self.assert_fixture("test_immutable_examples_validation_fingerprints_rankings_and_migrations")

    def test_invalid_references_types_dates_weights_and_untrusted_declarations(self):
        self.assert_fixture("test_invalid_references_types_dates_weights_and_untrusted_declarations")

    def test_legacy_and_mixed_contract_migrations_never_restore_hidden_approvals(self):
        self.assert_fixture("test_legacy_and_mixed_contract_migrations_never_restore_hidden_approvals")

    def test_receipt_full_stage_current_forged_cloned_stale_and_complete_binding(self):
        self.assert_fixture("test_receipt_full_stage_current_forged_cloned_stale_and_complete_binding")

    def test_scientific_input_changes_weight_preferences_and_typed_kill_gates(self):
        self.assert_fixture("test_scientific_input_changes_weight_preferences_and_typed_kill_gates")

    def test_source_offline_metadata_partial_and_protocol_failure_outputs(self):
        self.assert_fixture("test_source_offline_metadata_partial_and_protocol_failure_outputs")
