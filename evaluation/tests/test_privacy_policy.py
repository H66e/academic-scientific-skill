"""Outbound privacy policy regression tests.

The pattern gate is shared by the ledger fetch/search commands and the standalone
source tools.  It must block local paths, credentials and e-mail addresses while
not treating every HTTPS URL as a Windows drive path (the "s:/" in "https://"),
which would make public acquisition impossible.
"""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills/ai-research-mentor/runtime"))
from research_mentor.core import ResearchCore  # noqa: E402
from research_mentor.privacy import PrivacyError, check_outbound  # noqa: E402
from research_mentor.transport import Response  # noqa: E402


class ProtocolTransport:
    """Injected synthetic provider protocol; never opens a network connection."""

    def __init__(self, body=b"<html><body><h1>Title</h1><p>Public text about attention.</p></body></html>"):
        self.body, self.calls = body, []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return Response(url, 200, {"content-type": "text/html"}, self.body, "synthetic_protocol")


class OutboundPolicyTests(unittest.TestCase):
    def test_public_https_urls_are_not_mistaken_for_local_paths(self):
        for value in ("https://arxiv.org/html/2305.13245v1",
                      "https://api.crossref.org/works?query.bibliographic=grouped+query+attention",
                      "https://aclanthology.org/2023.emnlp-main.298/",
                      "https://doi.org/10.18653/v1/2023.emnlp-main.298"):
            with self.subTest(value=value):
                self.assertEqual(check_outbound(value, sensitivity="public").sensitivity, "public")

    def test_private_classification_blocks_before_any_pattern(self):
        with self.assertRaisesRegex(PrivacyError, "private material"):
            check_outbound("grouped query attention", sensitivity="private")

    def test_local_paths_credentials_and_addresses_are_blocked(self):
        blocked = [
            r"C:\Users\someone\private-ideas.md",
            "C:/Users/someone/private-ideas.md",
            r"\\server\share\private.md",
            "/root/.ssh/id_rsa",
            "/etc/shadow",
            "/home/someone/paper.pdf",
            "api key: sk-live-abc123",
            "API_KEY=secret-value",
            "Bearer abcdefghijklmnop",
            "ghp_abcdefghijklmnopqrstuvwxyz",
            "someone@example.org",
            "file:///home/someone/notes.md",
        ]
        for value in blocked:
            with self.subTest(value=value), self.assertRaises(PrivacyError):
                check_outbound(value, sensitivity="deidentified")

    def test_full_width_credentials_are_normalized_before_matching(self):
        with self.assertRaises(PrivacyError):
            check_outbound("ａｐｉ　ｋｅｙ＝ｓｅｃｒｅｔ", sensitivity="public")

    def test_ledger_public_url_fetch_acquires_and_replays(self):
        transport = ProtocolTransport()
        core = ResearchCore(Path(tempfile.mkdtemp()) / "proj", transport=transport)
        envelope = core.fetch(url="https://example.org/public-page", sensitivity="public")
        self.assertTrue(envelope.ok, envelope.errors)
        self.assertEqual(transport.calls, ["https://example.org/public-page"])
        self.assertTrue(core.ledger.verify()["valid"])
        report = core.verify_artifacts()
        self.assertTrue(report["valid"], report["errors"])

    def test_ledger_fetch_blocks_private_material_before_transport(self):
        transport = ProtocolTransport()
        core = ResearchCore(Path(tempfile.mkdtemp()) / "proj", transport=transport)
        envelope = core.fetch(url="https://example.org/private-notes", sensitivity="private")
        self.assertFalse(envelope.ok)
        self.assertEqual(envelope.status, "blocked")
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
