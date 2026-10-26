"""verify-artifacts replays source.fetch receipt and IR metadata, not only hashes.

Every duplicated field is re-derived from the retained raw artifact and the
fetched URL contract, so forging a receipt/IR field and recomputing the event
hash chain plus external anchor still reports an invalid artifact report.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills/ai-research-mentor/runtime"))
from research_mentor.core import ResearchCore
from research_mentor.ledger import Ledger, canonical_json, digest
from research_mentor.transport import Response


class ProtocolTransport:
    """Injected synthetic provider protocol; never opens a network connection."""

    def __init__(self, body=b"", headers=None):
        self.body, self.headers, self.calls = body, headers or {}, []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return Response(url, 200, self.headers, self.body, "synthetic_protocol")


def rewrite(project, event_type, mutate):
    """Rewrite one event and re-sign it plus the anchor, simulating forged history."""
    ledger = Ledger(project)
    events = ledger.read()
    target = next(event for event in reversed(events) if event["type"] == event_type)
    mutate(target)
    target["sha256"] = digest({key: value for key, value in target.items() if key != "sha256"})
    ledger.path.write_text("".join(canonical_json(event) + "\n" for event in events), encoding="utf-8")
    anchor = json.loads(ledger.anchor_path.read_text(encoding="utf-8"))
    anchor["head"] = events[-1]["sha256"]
    ledger.anchor_path.write_text(canonical_json(anchor) + "\n", encoding="utf-8")


class FetchReceiptReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-verify-fetch-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def test_valid_local_fetch_passes_and_every_forged_receipt_field_fails(self):
        forged = {"url": "local:forged", "provider": "public_url", "http_status": 500}
        for field, value in forged.items():
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory(prefix="mentor-verify-local-") as project:
                    core = ResearchCore(project)
                    original = Path(project) / "local-source.txt"
                    original.write_text("SYNTHETIC local source bytes.", encoding="utf-8")
                    result = core.fetch(local_path=original)
                    self.assertTrue(result.ok, result.errors)
                    self.assertTrue(core.verify_artifacts()["valid"])
                    rewrite(project, "source.fetch", lambda event, field=field, value=value: event["data"]["receipt"].update({field: value}))
                    report = core.verify_artifacts()
                    self.assertFalse(report["valid"])
                    self.assertTrue(report["errors"])
        with tempfile.TemporaryDirectory(prefix="mentor-verify-local-") as project:
            core = ResearchCore(project)
            original = Path(project) / "local-source.txt"
            original.write_text("SYNTHETIC local source bytes.", encoding="utf-8")
            self.assertTrue(core.fetch(local_path=original).ok)
            rewrite(project, "source.fetch", lambda event: event["data"].update(source_url="https://forged.example/local"))
            self.assertFalse(core.verify_artifacts()["valid"])

    def test_forged_ir_metadata_fails_even_with_a_recomputed_chain(self):
        for field, value in (("block_count", 99), ("extractor", "forged-extractor"), ("text_sha256", "0" * 64),
                             ("needs_host_review", False), ("limitations", ["FORGED limitation"])):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory(prefix="mentor-verify-ir-") as project:
                    core = ResearchCore(project)
                    original = Path(project) / "local-source.txt"
                    original.write_text("SYNTHETIC local source bytes.", encoding="utf-8")
                    self.assertTrue(core.fetch(local_path=original).ok)
                    self.assertTrue(core.verify_artifacts()["valid"])
                    rewrite(project, "source.fetch", lambda event, field=field, value=value: event["data"].update({field: value}))
                    self.assertFalse(core.verify_artifacts()["valid"])

    def test_public_url_fetch_replays_provider_and_final_url(self):
        transport = ProtocolTransport(b"<p>SYNTHETIC fetched body.</p>", {"content-type": "text/html; charset=utf-8"})
        core = ResearchCore(self.project, transport=transport)
        # The URL path's outbound classifier is exercised by the source-tool CLI
        # tests; this fixture isolates receipt replay from the network gate.
        with mock.patch("research_mentor.core.check_outbound"):
            result = core.fetch(url="https://example.org/paper", sensitivity="public")
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(transport.calls, ["https://example.org/paper"])
        self.assertEqual(result.data["receipt"]["provider"], "public_url")
        self.assertEqual(result.data["source_url"], result.data["receipt"]["url"])
        self.assertTrue(core.verify_artifacts()["valid"])
        rewrite(self.project, "source.fetch", lambda event: event["data"]["receipt"].update(url="https://forged.example/paper"))
        self.assertFalse(core.verify_artifacts()["valid"])

    def test_public_url_receipt_and_source_url_cannot_be_forged_as_a_pair(self):
        transport = ProtocolTransport(b"<p>SYNTHETIC fetched body.</p>", {"content-type": "text/html; charset=utf-8"})
        core = ResearchCore(self.project, transport=transport)
        with mock.patch("research_mentor.core.check_outbound"):
            self.assertTrue(core.fetch(url="https://example.org/paper", sensitivity="public").ok)
        self.assertTrue(core.verify_artifacts()["valid"])

        def forge_pair(event):
            event["data"]["receipt"]["url"] = "https://forged.example/paper"
            event["data"]["source_url"] = "https://forged.example/paper"

        rewrite(self.project, "source.fetch", forge_pair)
        self.assertFalse(core.verify_artifacts()["valid"])

    def test_identifier_fetch_replays_the_fixed_arxiv_resource_url(self):
        transport = ProtocolTransport(b"<p>SYNTHETIC arXiv body.</p>", {"content-type": "text/html; charset=utf-8"})
        core = ResearchCore(self.project, transport=transport)
        with mock.patch("research_mentor.core.check_outbound"):
            result = core.fetch(identifier="2401.12345v2", sensitivity="public")
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.data["receipt"]["provider"], "arxiv")
        self.assertEqual(result.data["receipt"]["url"], "https://arxiv.org/html/2401.12345v2")
        self.assertTrue(core.verify_artifacts()["valid"])
        rewrite(self.project, "source.fetch",
                lambda event: event["data"]["receipt"]["request"].update(url="https://example.org/paper"))
        self.assertFalse(core.verify_artifacts()["valid"])

    def test_search_result_replay_remains_rejected_as_a_control(self):
        item = {"DOI": "10.1234/a", "title": ["SYNTHETIC paper"], "published": {"date-parts": [[2024]]}}
        transport = ProtocolTransport(json.dumps({"message": {"total-results": 1, "items": [item]}}).encode(),
                                      {"content-type": "application/json"})
        core = ResearchCore(self.project, transport=transport)
        result = core.search("SYNTHETIC protocol query", provider="crossref", sensitivity="public")
        self.assertTrue(result.ok, result.errors)
        self.assertTrue(core.verify_artifacts()["valid"])
        rewrite(self.project, "search.result", lambda event: event["data"]["receipt"].update(url="https://forged.example/works"))
        self.assertFalse(core.verify_artifacts()["valid"])


if __name__ == "__main__":
    unittest.main()
